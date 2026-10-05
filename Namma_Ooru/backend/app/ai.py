"""AI provider contracts, grounded Bedrock implementation, and local mock."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Protocol, TypeVar
from urllib.parse import urlparse

from pydantic import TypeAdapter, ValidationError

from app.errors import DependencyUnavailableError
from app.itinerary.models import (
    Itinerary,
    ItineraryConstraints,
    ItineraryOperation,
    ItineraryOperationEnvelope,
)
from app.models import GroundedAnswer, RetrievalFilters, RetrievedSource, SearchIntent
from app.reviews.models import Review, ReviewSummary

UNAVAILABLE_ANSWER = "Information unavailable in the Namma Ooru travel data for this question."
_GROUNDED_SYSTEM_PROMPT = (
    "You are Namma Ooru's travel assistant. Answer using only the supplied retrieved "
    "Namma Ooru travel-data excerpts. Do not infer or invent facts, including hours, fees, "
    "history, distances, or coordinates. If the excerpts do not support an answer, state that "
    "information is unavailable in the Namma Ooru travel data."
)
_URL_PATTERN = re.compile(r"https?://[^\s)>\]}]+", re.IGNORECASE)
_OPERATION_ADAPTER = TypeAdapter(ItineraryOperationEnvelope)
_Result = TypeVar("_Result")
logger = logging.getLogger(__name__)


def _safe_bedrock_error_code(error: Exception) -> str:
    """Return an AWS error code or exception class without logging request content."""
    response = getattr(error, "response", None)
    if isinstance(response, Mapping):
        details = response.get("Error")
        if isinstance(details, Mapping):
            code = details.get("Code")
            if isinstance(code, str) and code:
                return code
    return type(error).__name__


class AIProvider(Protocol):
    """Boundary between domain handlers and AI implementations."""

    def extract_search_intent(self, query: str) -> SearchIntent:
        """Return structured intent for a validated natural-language query."""

    def answer(self, question: str, filters: RetrievalFilters) -> GroundedAnswer:
        """Return a grounded answer with sources separate from generated text."""

    def select_itinerary_candidates(
        self, destination_context: str, candidate_ids: list[str]
    ) -> list[str]:
        """Return an ordered, schema-validated subset of catalog candidate identifiers."""

    def parse_itinerary_edit(self, request: str, itinerary: Itinerary) -> ItineraryOperation:
        """Translate a validated edit request into a validated structured operation."""

    def summarize_reviews(self, reviews: list[Review]) -> ReviewSummary:
        """Return labelled themes derived only from the supplied destination reviews."""


class BedrockRuntimeClient(Protocol):
    """Minimal Bedrock Runtime client surface used for synchronous generation."""

    def converse(self, **kwargs: object) -> Mapping[str, object]: ...


class BedrockAgentRuntimeClient(Protocol):
    """Minimal Bedrock Agent Runtime surface used for Knowledge Base retrieval."""

    def retrieve(self, **kwargs: object) -> Mapping[str, object]: ...


class BedrockAIProvider:
    """Retrieve source-attributed KB content before bounded Bedrock generation.

    The provider intentionally performs retrieval and generation as separate calls so
    generated text never substitutes for provenance in the API response.
    """

    def __init__(
        self,
        *,
        knowledge_base_id: str,
        primary_model_id: str,
        fallback_model_id: str | None,
        agent_runtime_client: BedrockAgentRuntimeClient,
        runtime_client: BedrockRuntimeClient,
        timeout_seconds: float = 10.0,
        max_results: int = 5,
    ) -> None:
        if not knowledge_base_id.strip() or not primary_model_id.strip():
            raise ValueError("Bedrock Knowledge Base and primary model identifiers are required.")
        if timeout_seconds <= 0:
            raise ValueError("Bedrock timeout must be positive.")
        if max_results < 1:
            raise ValueError("Bedrock retrieval result count must be positive.")
        self._knowledge_base_id = knowledge_base_id
        self._primary_model_id = primary_model_id
        self._fallback_model_id = fallback_model_id.strip() if fallback_model_id else None
        self._agent_runtime_client = agent_runtime_client
        self._runtime_client = runtime_client
        self._timeout_seconds = timeout_seconds
        self._max_results = max_results

    def extract_search_intent(self, query: str) -> SearchIntent:
        """Bedrock search-intent parsing is introduced separately from chat retrieval."""
        del query
        raise DependencyUnavailableError()

    def answer(self, question: str, filters: RetrievalFilters) -> GroundedAnswer:
        """Retrieve first, then generate strictly from returned excerpts.

        Dependency errors and deadline overruns are translated to the public,
        structured ``AI_UNAVAILABLE`` error by the centralized FastAPI mapper.
        """
        try:
            retrieval_response = self._run_bounded(
                lambda: self._agent_runtime_client.retrieve(
                    **self._retrieval_request(question, filters)
                )
            )
            excerpts = self._retrieved_excerpts(retrieval_response)
            if not excerpts:
                return GroundedAnswer(answer=UNAVAILABLE_ANSWER, sources=[], unavailable=True)

            generated_response = self._generate_with_fallback(question, excerpts)
            answer = self._generated_text(generated_response)
            if not answer:
                raise DependencyUnavailableError()
            return GroundedAnswer(
                answer=answer,
                sources=self._sources_from_excerpts(excerpts),
                unavailable=False,
            )
        except DependencyUnavailableError as error:
            logger.warning("Bedrock AI request unavailable: %s", _safe_bedrock_error_code(error))
            raise
        except Exception as error:
            logger.warning("Bedrock AI request failed: %s", _safe_bedrock_error_code(error))
            raise DependencyUnavailableError() from error

    def select_itinerary_candidates(
        self, destination_context: str, candidate_ids: list[str]
    ) -> list[str]:
        """Keep structural itinerary selection outside this chat-focused provider task."""
        del destination_context
        return validate_itinerary_candidates(candidate_ids, set(candidate_ids))

    def parse_itinerary_edit(self, request: str, itinerary: Itinerary) -> ItineraryOperation:
        """Bedrock edit parsing is introduced separately from chat retrieval."""
        del request, itinerary
        raise DependencyUnavailableError()

    def summarize_reviews(self, reviews: list[Review]) -> ReviewSummary:
        """Summarize only the reviews supplied by the review service."""
        return _rating_based_review_summary(reviews)

    def _run_bounded(self, operation: Callable[[], _Result]) -> _Result:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(operation)
        try:
            return future.result(timeout=self._timeout_seconds)
        except TimeoutError as error:
            future.cancel()
            raise DependencyUnavailableError() from error
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _retrieval_request(self, question: str, filters: RetrievalFilters) -> dict[str, object]:
        vector_search: dict[str, object] = {"numberOfResults": self._max_results}
        metadata_filter = self._metadata_filter(filters)
        if metadata_filter:
            vector_search["filter"] = metadata_filter
        return {
            "knowledgeBaseId": self._knowledge_base_id,
            "retrievalQuery": {"text": question},
            "retrievalConfiguration": {"vectorSearchConfiguration": vector_search},
        }

    @staticmethod
    def _metadata_filter(filters: RetrievalFilters) -> dict[str, object] | None:
        clauses: list[dict[str, object]] = [
            {"equals": {"key": key, "value": value}}
            for key, value in filters.model_dump(exclude_none=True).items()
        ]
        if not clauses:
            return None
        return clauses[0] if len(clauses) == 1 else {"andAll": clauses}

    def _generate_with_fallback(
        self, question: str, excerpts: Sequence[Mapping[str, object]]
    ) -> Mapping[str, object]:
        """Use the primary inference profile, retrying once with the configured fallback."""
        try:
            return self._run_bounded(
                lambda: self._runtime_client.converse(
                    **self._generation_request(question, excerpts, self._primary_model_id)
                )
            )
        except Exception:
            fallback_model_id = self._fallback_model_id
            if fallback_model_id is None:
                raise
            return self._run_bounded(
                lambda: self._runtime_client.converse(
                    **self._generation_request(question, excerpts, fallback_model_id)
                )
            )

    def _generation_request(
        self, question: str, excerpts: Sequence[Mapping[str, object]], model_id: str
    ) -> dict[str, object]:
        context = "\n\n---\n\n".join(self._excerpt_text(excerpt) for excerpt in excerpts)
        return {
            "modelId": model_id,
            "system": [{"text": _GROUNDED_SYSTEM_PROMPT}],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": (
                                f"Retrieved Namma Ooru travel data:\n{context}\n\n"
                                f"Traveler question: {question}"
                            )
                        }
                    ],
                }
            ],
        }

    @staticmethod
    def _retrieved_excerpts(response: Mapping[str, object]) -> list[Mapping[str, object]]:
        results = response.get("retrievalResults", [])
        if not isinstance(results, list):
            raise DependencyUnavailableError()
        return [
            result
            for result in results
            if isinstance(result, Mapping) and BedrockAIProvider._excerpt_text(result)
        ]

    @staticmethod
    def _excerpt_text(excerpt: Mapping[str, object]) -> str:
        content = excerpt.get("content")
        if not isinstance(content, Mapping):
            return ""
        text = content.get("text")
        return text.strip() if isinstance(text, str) else ""

    @staticmethod
    def _generated_text(response: Mapping[str, object]) -> str:
        output = response.get("output")
        if not isinstance(output, Mapping):
            return ""
        message = output.get("message")
        if not isinstance(message, Mapping):
            return ""
        content = message.get("content")
        if not isinstance(content, list):
            return ""
        texts = [item.get("text", "").strip() for item in content if isinstance(item, Mapping)]
        return "\n".join(text for text in texts if isinstance(text, str) and text).strip()

    @staticmethod
    def _sources_from_excerpts(excerpts: Sequence[Mapping[str, object]]) -> list[RetrievedSource]:
        sources: list[RetrievedSource] = []
        seen: set[tuple[str, str]] = set()
        for excerpt in excerpts:
            text = BedrockAIProvider._excerpt_text(excerpt)
            metadata = excerpt.get("metadata")
            metadata_values = metadata if isinstance(metadata, Mapping) else {}
            destination_id = metadata_values.get("destination_id")
            if not isinstance(destination_id, str) or not destination_id.strip():
                location = excerpt.get("location")
                location_values = location if isinstance(location, Mapping) else {}
                s3_location = location_values.get("s3Location")
                s3_values = s3_location if isinstance(s3_location, Mapping) else {}
                uri = s3_values.get("uri")
                destination_id = (
                    BedrockAIProvider._id_from_uri(uri) if isinstance(uri, str) else None
                )
            if not destination_id:
                continue
            name = metadata_values.get("name")
            source_name = name.strip() if isinstance(name, str) and name.strip() else destination_id
            for url in _URL_PATTERN.findall(text):
                normalized_url = url.rstrip(".,;:")
                parsed = urlparse(normalized_url)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    continue
                key = (destination_id, normalized_url)
                if key in seen:
                    continue
                seen.add(key)
                sources.append(
                    RetrievedSource(
                        destination_id=destination_id,
                        name=source_name,
                        url=normalized_url,
                    )
                )
                break
        return sources

    @staticmethod
    def _id_from_uri(uri: str) -> str | None:
        filename = uri.rsplit("/", maxsplit=1)[-1]
        if filename.endswith(".md") and len(filename) > 3:
            return filename[:-3]
        return None


def create_bedrock_provider(
    *,
    knowledge_base_id: str,
    primary_model_id: str,
    fallback_model_id: str | None = None,
    region_name: str | None = None,
) -> BedrockAIProvider:
    """Build production clients through the standard AWS credential chain."""
    try:
        import boto3  # type: ignore[import-untyped]
        from botocore.config import Config  # type: ignore[import-untyped]

        config = Config(
            connect_timeout=3, read_timeout=8, retries={"max_attempts": 1, "mode": "standard"}
        )
        return BedrockAIProvider(
            knowledge_base_id=knowledge_base_id,
            primary_model_id=primary_model_id,
            fallback_model_id=fallback_model_id,
            agent_runtime_client=boto3.client(
                "bedrock-agent-runtime", region_name=region_name, config=config
            ),
            runtime_client=boto3.client("bedrock-runtime", region_name=region_name, config=config),
        )
    except Exception as error:
        raise DependencyUnavailableError() from error


def _rating_based_review_summary(reviews: list[Review]) -> ReviewSummary:
    """Create conservative themes from review ratings without introducing outside facts."""
    if not reviews:
        raise ValueError("Review summaries require at least one review.")
    positive_count = sum(review.rating >= 4 for review in reviews)
    concern_count = sum(review.rating <= 3 for review in reviews)
    positives = [f"{positive_count} review(s) gave a positive rating."] if positive_count else []
    concerns = [f"{concern_count} review(s) noted a lower rating."] if concern_count else []
    return ReviewSummary(positives=positives, concerns=concerns, review_count=len(reviews))


def validate_itinerary_candidates(raw: object, allowed_ids: set[str]) -> list[str]:
    """Validate AI candidate output is an ordered, de-duplicated catalog subset."""
    if not isinstance(raw, list) or not all(isinstance(item, str) and item for item in raw):
        raise ValueError("AI itinerary candidates must be a list of destination identifiers.")
    selected: list[str] = []
    for destination_id in raw:
        if destination_id not in allowed_ids:
            raise ValueError("AI selected a destination that is not in the catalog.")
        if destination_id not in selected:
            selected.append(destination_id)
    return selected


def validate_itinerary_operation(raw: object) -> ItineraryOperation:
    """Parse only the documented structured edit-operation schema."""
    try:
        return _OPERATION_ADAPTER.validate_python({"operation": raw}).operation
    except ValidationError as error:
        raise ValueError("AI returned an invalid itinerary edit operation.") from error


class LocalMockAIProvider:
    """Deterministic, network-free AI provider for local development and tests."""

    def extract_search_intent(self, query: str) -> SearchIntent:
        normalized_query = query.strip()
        lowered_query = normalized_query.lower()
        known_locations = ("chennai", "madurai", "coimbatore", "ooty", "thanjavur")
        known_categories = ("temples", "heritage", "beaches", "hills", "food", "nature")

        location = next(
            (place.title() for place in known_locations if place in lowered_query), None
        )
        category = next(
            (value.title() for value in known_categories if value in lowered_query),
            None,
        )
        interests = [category.lower()] if category else []
        return SearchIntent(location=location, category=category, interests=interests)

    def answer(self, question: str, filters: RetrievalFilters) -> GroundedAnswer:
        """Never fabricate travel facts when local retrieval has no knowledge base."""
        del question, filters
        return GroundedAnswer(answer=UNAVAILABLE_ANSWER, unavailable=True)

    def select_itinerary_candidates(
        self, destination_context: str, candidate_ids: list[str]
    ) -> list[str]:
        """Select catalog candidates deterministically; never introduce an identifier."""
        del destination_context
        return validate_itinerary_candidates(candidate_ids, set(candidate_ids))

    def summarize_reviews(self, reviews: list[Review]) -> ReviewSummary:
        """Derive deterministic, review-only feedback themes for local demos and tests."""
        return _rating_based_review_summary(reviews)

    def parse_itinerary_edit(self, request: str, itinerary: Itinerary) -> ItineraryOperation:
        """Parse concise local edit commands into the documented operation schema.

        The mock deliberately supports predictable command forms while accepting
        natural phrasing around them: ``remove <id>``, ``add <id>``,
        ``replace <old> with <new>``, and ``reorder day N: id, id``.
        """
        normalized = " ".join(request.casefold().strip().split())
        day_match = re.search(r"(?:on )?day\s+(\d+)", normalized)
        day_number = int(day_match.group(1)) if day_match else 1

        replace = re.search(r"replace\s+([\w-]+)\s+with\s+([\w-]+)", normalized)
        if replace:
            raw: object = {
                "op": "replace",
                "day_number": day_number,
                "target_destination_id": replace.group(1),
                "replacement_destination_id": replace.group(2),
            }
        else:
            add = re.search(r"add\s+([\w-]+)", normalized)
            remove = re.search(r"remove\s+([\w-]+)", normalized)
            reorder = re.search(r"reorder(?:\s+day\s+\d+)?\s*:\s*(.+)", normalized)
            if add:
                raw = {"op": "add", "destination_id": add.group(1), "day_number": day_number}
            elif remove:
                raw = {
                    "op": "remove",
                    "destination_id": remove.group(1),
                    "day_number": day_number,
                }
            elif reorder:
                raw = {
                    "op": "reorder",
                    "day_number": day_number,
                    "ordered_destination_ids": [
                        item.strip() for item in reorder.group(1).split(",") if item.strip()
                    ],
                }
            elif "slow" in normalized or "constraint" in normalized:
                raw = {
                    "op": "constrain",
                    "constraints": ItineraryConstraints(max_activities_per_day=2).model_dump(),
                }
            else:
                activity = next(
                    (activity for day in itinerary.days for activity in day.activities), None
                )
                if activity is None:
                    raw = {"op": "constrain", "constraints": {}}
                else:
                    raw = {
                        "op": "remove",
                        "day_number": 1,
                        "destination_id": activity.destination_id,
                    }
        return validate_itinerary_operation(raw)

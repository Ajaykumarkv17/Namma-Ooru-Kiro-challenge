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
_SEARCH_INTENT_ADAPTER = TypeAdapter(SearchIntent)
_Result = TypeVar("_Result")
logger = logging.getLogger(__name__)

# --- Structured-output prompts -------------------------------------------------
# Each prompt drives one single-responsibility Bedrock Converse call. This mirrors
# the Strands "Agents as Tools" multi-agent pattern (an orchestrator delegating to
# focused specialists): here the itinerary router is the orchestrator and these
# prompts are the specialist stages — intent extraction, candidate selection &
# geographic sequencing, and conversational-edit parsing. Every stage must return
# ONLY strict JSON matching a documented schema; the backend validates the JSON
# with Pydantic before use and falls back deterministically on any mismatch
# (AI/RAG steering: "require strict JSON ... validate before use and reject/repair
# on mismatch"). Structural assembly stays in the deterministic ItineraryService
# (architecture steering), so these stages only interpret, select, order, and
# narrate — they never fabricate catalog ids or schedule times themselves.

_SEARCH_INTENT_SYSTEM_PROMPT = (
    "You convert a traveler's natural-language search query about Tamil Nadu, India into a "
    "structured JSON search intent. Return ONLY a single JSON object, no prose, no code fences. "
    "Schema (all fields optional; omit a field or use null when the query does not state it): "
    '{"location": string|null, "duration_days": integer 1-14|null, "category": string|null, '
    '"interests": string[], "travel_style": string|null, "budget": string|null, '
    '"group_context": string|null}. '
    "location is a Tamil Nadu city or district named in the query. category is one of: "
    "temples, heritage, beaches, hills, waterfalls, nature, wildlife, food, culture, adventure, "
    "photography, hidden-gems (pick the closest, else null). interests are short free-text "
    "themes (e.g. 'architecture', 'photography'). Do not invent a location or category the "
    "query does not imply; prefer null over a guess."
)

_ITINERARY_SELECT_SYSTEM_PROMPT = (
    "You are the planning stage of a Tamil Nadu trip planner. You are given a trip context and a "
    "list of candidate destination ids already scoped to the requested location. Choose which "
    "candidates to include and the order to visit them so that geographically close places are "
    "grouped together and the sequence flows sensibly across the trip. Reason about travel "
    "between places, but DO NOT invent ids: every id you return MUST be one of the provided "
    "candidate ids, each at most once. Return ONLY a single JSON object, no prose, no code "
    'fences: {"ordered_destination_ids": string[]}. Prefer including enough places to fill the '
    "requested days; order best-first by your plan."
)

_ITINERARY_EDIT_SYSTEM_PROMPT = (
    "You translate a traveler's natural-language request to edit an existing itinerary into ONE "
    "structured operation. Return ONLY a single JSON object, no prose, no code fences, matching "
    "exactly one of these shapes: "
    '{"op":"add","destination_id":id,"day_number":n} | '
    '{"op":"remove","day_number":n,"destination_id":id} | '
    '{"op":"replace","day_number":n,"target_destination_id":id,"replacement_destination_id":id} | '
    '{"op":"reorder","day_number":n,"ordered_destination_ids":[id,...]} | '
    '{"op":"constrain","constraints":{...}}. '
    "Use only destination ids present in the supplied itinerary (except an added id, which must "
    "be a real catalog id). day_number is 1-based. If the request maps to no single supported "
    'operation, return {"op":"none"} so the caller can decline gracefully. Do not invent fields.'
)

# Low-temperature inference so structured JSON output is stable and parseable.
_STRUCTURED_INFERENCE_CONFIG: dict[str, object] = {"temperature": 0.0, "maxTokens": 1024}


def _extract_json_object(text: str) -> object:
    """Extract and parse the first balanced top-level JSON object from model text.

    Models sometimes wrap JSON in prose or ```json fences despite instructions.
    This finds the first ``{`` and its matching ``}`` (brace-depth aware, string
    and escape sensitive) and parses that span. Raises ``ValueError`` when no
    parseable JSON object is present so callers fail soft rather than trusting
    malformed output.
    """
    if not text:
        raise ValueError("Empty model response; no JSON object to parse.")
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response.")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                import json

                return json.loads(text[start : index + 1])
    raise ValueError("Unterminated JSON object in model response.")




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
        """Interpret a natural-language query into a validated ``SearchIntent``.

        Runs one bounded, low-temperature Converse call that must return strict
        JSON matching the ``SearchIntent`` schema, then validates it with Pydantic
        (AI/RAG steering: strict JSON, validate before use). Any failure — Bedrock
        error, deadline overrun, non-JSON output, or schema mismatch — is raised as
        ``DependencyUnavailableError`` so the search router falls back to its
        deterministic keyword/tag path and flags the fallback to the client
        (fail-soft on optional AI enrichment, Requirement 4.3).
        """
        cleaned = query.strip()
        if not cleaned:
            raise DependencyUnavailableError()
        try:
            response = self._generate_structured(
                _SEARCH_INTENT_SYSTEM_PROMPT,
                f"Traveler search query: {cleaned}",
            )
            payload = _extract_json_object(self._generated_text(response))
            return _SEARCH_INTENT_ADAPTER.validate_python(payload)
        except DependencyUnavailableError as error:
            logger.warning("Bedrock intent unavailable: %s", _safe_bedrock_error_code(error))
            raise
        except Exception as error:
            logger.warning("Bedrock intent parse failed: %s", _safe_bedrock_error_code(error))
            raise DependencyUnavailableError() from error

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
        """Select and order candidates with reasoning about geography and flow.

        This is the planning stage of the agentic itinerary workflow (Strands
        "Agents as Tools" pattern): one bounded Converse call reasons over the
        location-scoped candidate ids and returns an ordered subset that groups
        nearby places and sequences the trip sensibly. The model never invents an
        id — the result is validated to be a subset of ``candidate_ids`` via
        ``validate_itinerary_candidates``. On any failure the deterministic order
        (the input list) is returned unchanged, so generation never breaks and the
        deterministic ``ItineraryService`` still performs all scoring, scheduling,
        travel-gap insertion, and invariant enforcement (architecture steering).
        """
        allowed = set(candidate_ids)
        if not candidate_ids:
            return []
        try:
            response = self._generate_structured(
                _ITINERARY_SELECT_SYSTEM_PROMPT,
                (
                    f"Trip context: {destination_context}\n"
                    f"Candidate destination ids: {', '.join(candidate_ids)}"
                ),
            )
            payload = _extract_json_object(self._generated_text(response))
            ordered = payload.get("ordered_destination_ids") if isinstance(payload, dict) else None
            selected = validate_itinerary_candidates(ordered, allowed)
            # Append any candidates the model omitted so the deterministic core
            # still has the full pool to fill the requested days (it decides how
            # many to actually schedule). The model's order leads; the rest follow.
            tail = [cid for cid in candidate_ids if cid not in set(selected)]
            return selected + tail
        except Exception as error:
            logger.warning(
                "Bedrock itinerary selection fell back to deterministic order: %s",
                _safe_bedrock_error_code(error),
            )
            return validate_itinerary_candidates(candidate_ids, allowed)

    def parse_itinerary_edit(self, request: str, itinerary: Itinerary) -> ItineraryOperation:
        """Translate a natural-language edit into one validated structured operation.

        Runs one bounded Converse call that must return strict JSON for exactly one
        of the five supported operations (add, remove, replace, reorder, constrain),
        then validates it with ``validate_itinerary_operation``. The itinerary's
        current day/activity ids are supplied so the model targets real activities.

        When the request maps to no single supported operation (e.g. "add day 2 and
        day 3 plans", which is a regeneration, not an edit), the model returns
        ``{"op":"none"}``; this method then returns a benign no-op (a remove targeting
        a non-existent activity) that the deterministic ``ItineraryService`` rejects,
        so the router responds with ``EditUnavailable`` and a clear explanation
        instead of a 503. Bedrock/deadline failures still raise
        ``DependencyUnavailableError`` (a genuine outage, correctly surfaced).
        """
        cleaned = request.strip()
        if not cleaned:
            return self._declinable_edit(itinerary)
        try:
            response = self._generate_structured(
                _ITINERARY_EDIT_SYSTEM_PROMPT,
                self._edit_user_prompt(cleaned, itinerary),
            )
            payload = _extract_json_object(self._generated_text(response))
        except DependencyUnavailableError:
            raise
        except Exception as error:
            logger.warning("Bedrock edit parse failed: %s", _safe_bedrock_error_code(error))
            raise DependencyUnavailableError() from error

        # A sentinel {"op":"none"} (or anything that is not a supported op) means the
        # request is not a single structured edit; decline gracefully, don't 503.
        if not isinstance(payload, dict) or payload.get("op") in (None, "none"):
            return self._declinable_edit(itinerary)
        try:
            return validate_itinerary_operation(payload)
        except ValueError:
            return self._declinable_edit(itinerary)

    @staticmethod
    def _edit_user_prompt(request: str, itinerary: Itinerary) -> str:
        """Describe the current itinerary ids so the model targets real activities."""
        lines: list[str] = []
        for day in itinerary.days:
            ids = ", ".join(activity.destination_id for activity in day.activities) or "(empty)"
            lines.append(f"Day {day.day_number}: {ids}")
        current = "\n".join(lines) if lines else "(no days)"
        return (
            f"Current itinerary ({itinerary.destination_context}):\n{current}\n\n"
            f"Edit request: {request}"
        )

    @staticmethod
    def _declinable_edit(itinerary: Itinerary) -> ItineraryOperation:
        """Return an operation the deterministic core will reject (so router declines).

        A remove targeting a day/destination guaranteed absent produces
        ``changed=False`` in ``ItineraryService.apply_operation``, which the router
        maps to ``EditUnavailable`` — a 200 response with a safe explanation —
        rather than an error. Uses an out-of-range day number so it never matches.
        """
        return validate_itinerary_operation(
            {"op": "remove", "day_number": 999, "destination_id": "no-op-unmapped-edit"}
        )

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

    def _generate_structured(
        self, system_prompt: str, user_text: str
    ) -> Mapping[str, object]:
        """Run one bounded, low-temperature Converse call for strict JSON output.

        Shared by the structured-output stages (search intent, candidate selection,
        edit parsing). Uses the primary inference profile and retries once with the
        configured fallback, mirroring ``_generate_with_fallback`` but with a
        caller-supplied single-responsibility system prompt and a deterministic
        ``inferenceConfig`` (temperature 0) so JSON output is stable. Timeouts and
        Bedrock errors propagate as ``DependencyUnavailableError`` via
        ``_run_bounded`` / the caller's handler.
        """
        request = {
            "system": [{"text": system_prompt}],
            "messages": [{"role": "user", "content": [{"text": user_text}]}],
            "inferenceConfig": _STRUCTURED_INFERENCE_CONFIG,
        }
        try:
            return self._run_bounded(
                lambda: self._runtime_client.converse(
                    modelId=self._primary_model_id, **request
                )
            )
        except Exception:
            fallback_model_id = self._fallback_model_id
            if fallback_model_id is None:
                raise
            return self._run_bounded(
                lambda: self._runtime_client.converse(
                    modelId=fallback_model_id, **request
                )
            )

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

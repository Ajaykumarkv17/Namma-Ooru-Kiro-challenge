"""AI provider contracts and deterministic local development implementation."""

from __future__ import annotations

import re
from typing import Protocol

from pydantic import TypeAdapter, ValidationError

from app.itinerary.models import (
    Itinerary,
    ItineraryConstraints,
    ItineraryOperation,
    ItineraryOperationEnvelope,
)
from app.models import GroundedAnswer, RetrievalFilters, SearchIntent

UNAVAILABLE_ANSWER = "Information unavailable in the Namma Ooru travel data for this question."
_OPERATION_ADAPTER = TypeAdapter(ItineraryOperationEnvelope)


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

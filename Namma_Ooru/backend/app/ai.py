"""AI provider contracts and deterministic local development implementation."""

from __future__ import annotations

from typing import Protocol

from app.models import GroundedAnswer, RetrievalFilters, SearchIntent

UNAVAILABLE_ANSWER = "Information unavailable in the Namma Ooru travel data for this question."


class AIProvider(Protocol):
    """Boundary between domain handlers and AI implementations."""

    def extract_search_intent(self, query: str) -> SearchIntent:
        """Return structured intent for a validated natural-language query."""

    def answer(self, question: str, filters: RetrievalFilters) -> GroundedAnswer:
        """Return a grounded answer with sources separate from generated text."""


class LocalMockAIProvider:
    """Deterministic, network-free AI provider for local development and tests."""

    def extract_search_intent(self, query: str) -> SearchIntent:
        normalized_query = query.strip()
        lowered_query = normalized_query.lower()
        known_locations = ("chennai", "madurai", "coimbatore", "ooty", "thanjavur")
        known_categories = (
            "temples",
            "heritage",
            "beaches",
            "hills",
            "food",
            "nature",
        )

        location = next(
            (place.title() for place in known_locations if place in lowered_query), None
        )
        category = next(
            (value.title() for value in known_categories if value in lowered_query), None
        )
        interests = [category.lower()] if category else []
        return SearchIntent(location=location, category=category, interests=interests)

    def answer(self, question: str, filters: RetrievalFilters) -> GroundedAnswer:
        """Never fabricate travel facts when local retrieval has no knowledge base."""
        del question, filters
        return GroundedAnswer(answer=UNAVAILABLE_ANSWER, unavailable=True)

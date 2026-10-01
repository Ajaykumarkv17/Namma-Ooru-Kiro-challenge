"""Integration and unit tests for the search endpoint and services (task 4.1).

These exercise ``POST /api/search`` with FastAPI's ``TestClient`` and a
fixture-backed ``JsonDestinationRepository`` injected via dependency override so
the tests never touch the shipped dataset. Coverage:

* the AI happy path with ``LocalMockAIProvider`` (Requirements 4.1, 4.2),
* the AI-unavailable keyword/tag fallback path and its response signal
  (Requirement 4.3),
* filter intersection soundness at the endpoint (Requirement 4.4),
* input validation edge cases returning structured errors (Requirement 11.1).

Also included are focused unit tests for the deterministic ``SearchService``
intent-mapping and keyword-fallback cores.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.ai import AIProvider, LocalMockAIProvider
from app.catalog.models import Destination
from app.catalog.repository import JsonDestinationRepository
from app.catalog.vocabularies import DestinationCategory, TamilNaduDistrict
from app.dependencies import (
    get_ai_provider,
    get_destination_repository,
    get_search_service,
)
from app.errors import DependencyUnavailableError
from app.main import create_app
from app.models import RetrievalFilters, SearchIntent
from app.search.service import (
    SearchService,
    intent_to_filters,
    keyword_filters_from_query,
)


def _destination(
    id_: str,
    *,
    city: str = "Madurai",
    district: TamilNaduDistrict = TamilNaduDistrict.MADURAI,
    category: DestinationCategory = DestinationCategory.TEMPLES,
    tags: list[str] | None = None,
    family_friendly: bool = False,
    is_hidden_gem: bool = False,
    **overrides: Any,
) -> Destination:
    data: dict[str, Any] = {
        "id": id_,
        "name": id_.replace("-", " ").title(),
        "city": city,
        "district": district.value,
        "region": "South Tamil Nadu",
        "category": category.value,
        "description": f"Test destination {id_}.",
        "tags": tags or [],
        "family_friendly": family_friendly,
        "is_hidden_gem": is_hidden_gem,
        "source_urls": ["https://www.tamilnadutourism.tn.gov.in/"],
    }
    data.update(overrides)
    return Destination.model_validate(data)


def _catalog() -> list[Destination]:
    return [
        _destination(
            "madurai-meenakshi-temple",
            category=DestinationCategory.TEMPLES,
            tags=["temple", "heritage"],
            family_friendly=True,
        ),
        _destination(
            "madurai-street-food-walk",
            category=DestinationCategory.FOOD,
            tags=["food", "evening"],
            family_friendly=True,
        ),
        _destination(
            "ooty-botanical-garden",
            city="Ooty",
            district=TamilNaduDistrict.NILGIRIS,
            category=DestinationCategory.NATURE,
            tags=["garden", "family"],
            family_friendly=True,
        ),
    ]


class _UnavailableAIProvider:
    """AI provider double whose intent extraction is always unavailable."""

    def extract_search_intent(self, query: str) -> SearchIntent:
        del query
        raise DependencyUnavailableError("AI provider offline for test.")

    def answer(self, question: str, filters: RetrievalFilters) -> Any:
        del question, filters
        raise DependencyUnavailableError("AI provider offline for test.")

    def select_itinerary_candidates(
        self, destination_context: str, candidate_ids: list[str]
    ) -> list[str]:
        del destination_context, candidate_ids
        raise DependencyUnavailableError("AI provider offline for test.")

    def parse_itinerary_edit(self, request: str, itinerary: Any) -> Any:
        del request, itinerary
        raise DependencyUnavailableError("AI provider offline for test.")

    def summarize_reviews(self, reviews: list[Any]) -> Any:
        del reviews
        raise DependencyUnavailableError("AI provider offline for test.")


def _client(ai_provider: AIProvider | None = None) -> TestClient:
    app = create_app()
    repo = JsonDestinationRepository(destinations=_catalog())
    app.dependency_overrides[get_destination_repository] = lambda: repo
    app.dependency_overrides[get_search_service] = lambda: SearchService()
    app.dependency_overrides[get_ai_provider] = lambda: ai_provider or LocalMockAIProvider()
    return TestClient(app)


# --- POST /api/search: AI happy path ------------------------------------------


def test_search_with_ai_returns_structured_results_for_recognized_intent() -> None:
    response = _client().post("/api/search", json={"query": "temples in Madurai"})
    assert response.status_code == 200
    body = response.json()
    assert body["used_fallback"] is False
    assert body["fallback_reason"] is None
    # LocalMockAIProvider recognizes location "Madurai" and category "temples".
    assert body["intent"]["location"] == "Madurai"
    assert body["intent"]["category"] == "Temples"
    assert body["filters"]["city"] == "Madurai"
    assert body["filters"]["category"] == "temples"
    ids = [d["id"] for d in body["destinations"]]
    assert ids == ["madurai-meenakshi-temple"]
    assert body["result_count"] == 1


def test_search_with_unrecognized_query_returns_whole_catalog() -> None:
    response = _client().post("/api/search", json={"query": "something wonderful"})
    assert response.status_code == 200
    body = response.json()
    assert body["used_fallback"] is False
    # No recognized intent -> no active filters -> whole catalog returned.
    assert body["result_count"] == 3


# --- POST /api/search: intersection soundness at the endpoint (Req 4.4) -------


def test_search_results_satisfy_every_active_filter() -> None:
    response = _client().post("/api/search", json={"query": "food in Madurai"})
    assert response.status_code == 200
    body = response.json()
    filters = body["filters"]
    for destination in body["destinations"]:
        if filters["city"] is not None:
            assert destination["city"].casefold() == filters["city"].casefold()
        if filters["category"] is not None:
            assert destination["category"] == filters["category"]


# --- POST /api/search: AI-unavailable fallback (Req 4.3) ----------------------


def test_search_falls_back_to_keyword_matching_when_ai_unavailable() -> None:
    response = _client(_UnavailableAIProvider()).post("/api/search", json={"query": "temple"})
    assert response.status_code == 200
    body = response.json()
    assert body["used_fallback"] is True
    assert body["fallback_reason"]
    # Fallback keyword matching recognized the "temple" category keyword.
    assert body["filters"]["category"] == "temples"
    assert [d["id"] for d in body["destinations"]] == ["madurai-meenakshi-temple"]


def test_search_fallback_matches_catalog_tags() -> None:
    response = _client(_UnavailableAIProvider()).post("/api/search", json={"query": "evening food"})
    assert response.status_code == 200
    body = response.json()
    assert body["used_fallback"] is True
    # "food" is both a category keyword and a tag; "evening" is a catalog tag.
    assert body["filters"]["category"] == "food"
    assert "evening" in body["filters"]["tags"]
    assert [d["id"] for d in body["destinations"]] == ["madurai-street-food-walk"]


def test_search_fallback_with_only_stopwords_returns_whole_catalog() -> None:
    response = _client(_UnavailableAIProvider()).post(
        "/api/search", json={"query": "please show me the best"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["used_fallback"] is True
    assert body["result_count"] == 3


# --- POST /api/search: input validation (Req 11.1) ----------------------------


def test_search_rejects_empty_query_with_structured_error() -> None:
    response = _client().post("/api/search", json={"query": ""})
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "VALIDATION_ERROR"
    assert any(item["field"].endswith("query") for item in body["detail"])


def test_search_rejects_missing_query_with_structured_error() -> None:
    response = _client().post("/api/search", json={})
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_search_rejects_unknown_fields() -> None:
    response = _client().post("/api/search", json={"query": "temples", "unexpected": "x"})
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_search_rejects_overlong_query() -> None:
    response = _client().post("/api/search", json={"query": "a" * 2_001})
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


# --- Unit tests for the deterministic search cores ----------------------------


def test_intent_to_filters_maps_location_and_category() -> None:
    filters = intent_to_filters(
        SearchIntent(location="Madurai", category="Temples", interests=["sunrise"])
    )
    assert filters.city == "Madurai"
    assert filters.category is DestinationCategory.TEMPLES
    # A non-category interest becomes a tag; category-named interests do not.
    assert filters.tags == ["sunrise"]


def test_intent_to_filters_ignores_unknown_category() -> None:
    filters = intent_to_filters(SearchIntent(category="spaceship"))
    assert filters.category is None


def test_intent_to_filters_promotes_interest_to_category() -> None:
    filters = intent_to_filters(SearchIntent(interests=["food"]))
    assert filters.category is DestinationCategory.FOOD
    # A category-named interest informs the category, not a restrictive tag.
    assert filters.tags == []


def test_intent_to_filters_maps_district_slug_location() -> None:
    filters = intent_to_filters(SearchIntent(location="nilgiris"))
    assert filters.district is TamilNaduDistrict.NILGIRIS


def test_keyword_filters_recognizes_city_category_and_tags() -> None:
    catalog = _catalog()
    filters = keyword_filters_from_query("temple heritage in madurai", catalog)
    assert filters.city == "Madurai"
    assert filters.category is DestinationCategory.TEMPLES
    assert "heritage" in filters.tags


def test_keyword_filters_empty_for_unrecognized_query() -> None:
    catalog = _catalog()
    filters = keyword_filters_from_query("please help me plan", catalog)
    assert filters.city is None
    assert filters.category is None
    assert filters.district is None
    assert filters.tags == []

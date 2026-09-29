"""Integration tests for the catalog endpoints (task 2.3).

These exercise the endpoint contracts with FastAPI's ``TestClient`` and a
fixture-backed ``JsonDestinationRepository`` injected via dependency override so
the tests never touch the shipped dataset. They cover: list with/without filters,
filter intersection, filter query-param validation, ``get_by_id`` found (200) and
not-found (404 with structured ``{error, detail}``), nearby resolution, and
``city_view`` for a known city and an empty/unknown city.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.catalog.models import Destination
from app.catalog.repository import JsonDestinationRepository
from app.catalog.vocabularies import DestinationCategory, TamilNaduDistrict
from app.dependencies import get_destination_repository
from app.main import create_app


def _destination(
    id_: str,
    *,
    city: str = "Madurai",
    district: TamilNaduDistrict = TamilNaduDistrict.MADURAI,
    category: DestinationCategory = DestinationCategory.TEMPLES,
    tags: list[str] | None = None,
    family_friendly: bool = False,
    is_hidden_gem: bool = False,
    nearby_place_ids: list[str] | None = None,
    popularity_score: float = 0.0,
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
        "nearby_place_ids": nearby_place_ids or [],
        "source_urls": ["https://www.tamilnadutourism.tn.gov.in/"],
        "popularity": {"popularity_score": popularity_score},
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
            nearby_place_ids=["madurai-street-food-walk", "does-not-exist"],
            popularity_score=0.95,
        ),
        _destination(
            "madurai-street-food-walk",
            category=DestinationCategory.FOOD,
            tags=["food", "evening"],
            family_friendly=True,
            popularity_score=0.4,
        ),
        _destination(
            "ooty-botanical-garden",
            city="Ooty",
            district=TamilNaduDistrict.NILGIRIS,
            category=DestinationCategory.NATURE,
            tags=["garden", "family"],
            family_friendly=True,
            popularity_score=0.8,
        ),
    ]


def _client() -> TestClient:
    app = create_app()
    repo = JsonDestinationRepository(destinations=_catalog())
    app.dependency_overrides[get_destination_repository] = lambda: repo
    return TestClient(app)


# --- GET /api/destinations ----------------------------------------------------


def test_list_destinations_without_filters_returns_all() -> None:
    response = _client().get("/api/destinations")
    assert response.status_code == 200
    ids = [d["id"] for d in response.json()]
    assert ids == [
        "madurai-meenakshi-temple",
        "madurai-street-food-walk",
        "ooty-botanical-garden",
    ]


def test_list_destinations_filters_by_city() -> None:
    response = _client().get("/api/destinations", params={"city": "ooty"})
    assert response.status_code == 200
    assert [d["id"] for d in response.json()] == ["ooty-botanical-garden"]


def test_list_destinations_intersecting_filters_narrow_results() -> None:
    response = _client().get(
        "/api/destinations",
        params={"city": "Madurai", "category": "temples", "family_friendly": "true"},
    )
    assert response.status_code == 200
    assert [d["id"] for d in response.json()] == ["madurai-meenakshi-temple"]


def test_list_destinations_tag_filter_is_and_intersection() -> None:
    response = _client().get("/api/destinations", params=[("tags", "temple"), ("tags", "heritage")])
    assert response.status_code == 200
    assert [d["id"] for d in response.json()] == ["madurai-meenakshi-temple"]


def test_list_destinations_rejects_invalid_category_with_structured_error() -> None:
    response = _client().get("/api/destinations", params={"category": "not-a-category"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "VALIDATION_ERROR"
    assert any(item["field"].endswith("category") for item in body["detail"])


# --- GET /api/destinations/{id} -----------------------------------------------


def test_get_destination_found_returns_detail_with_resolved_nearby() -> None:
    response = _client().get("/api/destinations/madurai-meenakshi-temple")
    assert response.status_code == 200
    body = response.json()
    assert body["destination"]["id"] == "madurai-meenakshi-temple"
    # Only the real nearby id resolves; the dangling id is dropped (Req 2.4).
    assert [d["id"] for d in body["nearby"]] == ["madurai-street-food-walk"]


def test_get_destination_not_found_returns_structured_404() -> None:
    response = _client().get("/api/destinations/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {
        "error": "DESTINATION_NOT_FOUND",
        "detail": "No destination exists with id 'does-not-exist'.",
    }


# --- GET /api/cities/{city} ---------------------------------------------------


def test_get_city_returns_grouped_view_for_known_city() -> None:
    response = _client().get("/api/cities/Madurai")
    assert response.status_code == 200
    body = response.json()
    assert body["city"] == "Madurai"
    assert body["destination_count"] == 2
    assert [section["key"] for section in body["sections"]] == [
        "popular",
        "temples",
        "food",
    ]


def test_get_city_unknown_city_returns_empty_view_not_404() -> None:
    response = _client().get("/api/cities/Chennai")
    assert response.status_code == 200
    body = response.json()
    assert body["city"] == "Chennai"
    assert body["destination_count"] == 0
    assert body["sections"] == []

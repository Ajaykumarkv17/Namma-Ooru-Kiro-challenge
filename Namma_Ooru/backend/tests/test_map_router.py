"""Integration tests for the map-marker endpoint (task 3.3).

These exercise ``GET /api/map/markers`` with FastAPI's ``TestClient`` and a
fixture-backed ``JsonDestinationRepository`` injected via dependency override, so
the tests never touch the shipped dataset. They cover: markers for all
coordinate-verified destinations, only coordinate-verified destinations returned
(Requirement 9.1), city/category filters (Requirement 9.2), filter intersection,
the marker preview shape (Requirement 9.3 preview fields), and structured
validation errors on bad query input.
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
    latitude: float | None = 9.9195,
    longitude: float | None = 78.1193,
    tags: list[str] | None = None,
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
        "latitude": latitude,
        "longitude": longitude,
        "tags": tags or [],
        "source_urls": ["https://www.tamilnadutourism.tn.gov.in/"],
    }
    data.update(overrides)
    return Destination.model_validate(data)


def _catalog() -> list[Destination]:
    return [
        _destination(
            "madurai-meenakshi-temple",
            category=DestinationCategory.TEMPLES,
            image_reference="https://cdn.example.com/meenakshi.jpg",
        ),
        _destination(
            "madurai-street-food-walk",
            category=DestinationCategory.FOOD,
            tags=["food"],
        ),
        # No verified coordinates: excluded from markers (Requirement 9.1).
        _destination("madurai-mystery-lane", latitude=None, longitude=None),
        _destination(
            "ooty-botanical-garden",
            city="Ooty",
            district=TamilNaduDistrict.NILGIRIS,
            category=DestinationCategory.NATURE,
            latitude=11.4102,
            longitude=76.7028,
        ),
    ]


def _client() -> TestClient:
    app = create_app()
    repo = JsonDestinationRepository(destinations=_catalog())
    app.dependency_overrides[get_destination_repository] = lambda: repo
    return TestClient(app)


def test_markers_without_filters_returns_only_coordinate_verified() -> None:
    response = _client().get("/api/map/markers")
    assert response.status_code == 200
    ids = [m["id"] for m in response.json()]
    assert ids == [
        "madurai-meenakshi-temple",
        "madurai-street-food-walk",
        "ooty-botanical-garden",
    ]
    assert "madurai-mystery-lane" not in ids


def test_markers_filter_by_city() -> None:
    response = _client().get("/api/map/markers", params={"city": "ooty"})
    assert response.status_code == 200
    assert [m["id"] for m in response.json()] == ["ooty-botanical-garden"]


def test_markers_filter_by_category() -> None:
    response = _client().get("/api/map/markers", params={"category": "food"})
    assert response.status_code == 200
    assert [m["id"] for m in response.json()] == ["madurai-street-food-walk"]


def test_markers_intersecting_filters_narrow_results() -> None:
    response = _client().get(
        "/api/map/markers",
        params={"city": "Madurai", "category": "temples"},
    )
    assert response.status_code == 200
    assert [m["id"] for m in response.json()] == ["madurai-meenakshi-temple"]


def test_marker_preview_shape_includes_navigation_fields() -> None:
    response = _client().get("/api/map/markers", params={"category": "temples"})
    assert response.status_code == 200
    marker = response.json()[0]
    assert marker == {
        "id": "madurai-meenakshi-temple",
        "name": "Madurai Meenakshi Temple",
        "latitude": 9.9195,
        "longitude": 78.1193,
        "category": "temples",
        "city": "Madurai",
        "district": "madurai",
        "description": "Test destination madurai-meenakshi-temple.",
        "image_reference": "https://cdn.example.com/meenakshi.jpg",
        "is_hidden_gem": False,
    }


def test_markers_reject_invalid_category_with_structured_error() -> None:
    response = _client().get("/api/map/markers", params={"category": "not-a-category"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "VALIDATION_ERROR"
    assert any(item["field"].endswith("category") for item in body["detail"])

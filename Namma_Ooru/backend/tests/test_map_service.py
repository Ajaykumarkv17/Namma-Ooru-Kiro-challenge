"""Unit tests for the pure map-marker service (task 3.3).

These exercise ``app.map.service`` directly with in-memory Destination records
(no I/O, no TestClient). They cover: only coordinate-verified destinations become
markers (Requirement 9.1), every active map filter narrows the markers
(Requirement 9.2), marker shaping preserves preview fields, and the guard when a
coordinate-less destination is shaped directly.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.catalog.models import Destination
from app.catalog.vocabularies import DestinationCategory, TamilNaduDistrict
from app.map.models import MapFilters
from app.map.service import MapMarkerService, build_markers, to_marker


def _destination(
    id_: str,
    *,
    city: str = "Madurai",
    district: TamilNaduDistrict = TamilNaduDistrict.MADURAI,
    category: DestinationCategory = DestinationCategory.TEMPLES,
    latitude: float | None = 9.9195,
    longitude: float | None = 78.1193,
    tags: list[str] | None = None,
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
        "latitude": latitude,
        "longitude": longitude,
        "tags": tags or [],
        "is_hidden_gem": is_hidden_gem,
        "source_urls": ["https://www.tamilnadutourism.tn.gov.in/"],
    }
    data.update(overrides)
    return Destination.model_validate(data)


def _catalog() -> list[Destination]:
    return [
        _destination("madurai-meenakshi-temple", category=DestinationCategory.TEMPLES),
        _destination(
            "madurai-street-food-walk",
            category=DestinationCategory.FOOD,
            tags=["food"],
        ),
        # No verified coordinates: must never become a marker (Requirement 9.1).
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


def test_markers_include_only_coordinate_verified_destinations() -> None:
    markers = MapMarkerService().markers(_catalog(), MapFilters())
    ids = [m.id for m in markers]
    assert ids == [
        "madurai-meenakshi-temple",
        "madurai-street-food-walk",
        "ooty-botanical-garden",
    ]
    assert "madurai-mystery-lane" not in ids


def test_markers_drop_destinations_with_out_of_range_coordinates() -> None:
    # A destination outside Tamil Nadu's bounds is not coordinate-verified.
    catalog = [_destination("elsewhere", latitude=28.6, longitude=77.2)]
    assert build_markers(catalog, MapFilters()) == []


def test_city_filter_narrows_markers() -> None:
    markers = build_markers(_catalog(), MapFilters(city="ooty"))
    assert [m.id for m in markers] == ["ooty-botanical-garden"]


def test_category_filter_narrows_markers() -> None:
    markers = build_markers(_catalog(), MapFilters(category=DestinationCategory.FOOD))
    assert [m.id for m in markers] == ["madurai-street-food-walk"]


def test_combined_filters_intersect() -> None:
    markers = build_markers(
        _catalog(),
        MapFilters(city="Madurai", category=DestinationCategory.TEMPLES),
    )
    assert [m.id for m in markers] == ["madurai-meenakshi-temple"]


def test_to_marker_preserves_preview_fields() -> None:
    destination = _destination(
        "madurai-meenakshi-temple",
        image_reference="https://cdn.example.com/meenakshi.jpg",
        is_hidden_gem=True,
    )
    marker = to_marker(destination)
    assert marker.name == "Madurai Meenakshi Temple"
    assert marker.latitude == pytest.approx(9.9195)
    assert marker.longitude == pytest.approx(78.1193)
    assert marker.category is DestinationCategory.TEMPLES
    assert marker.city == "Madurai"
    assert marker.district is TamilNaduDistrict.MADURAI
    assert marker.image_reference == "https://cdn.example.com/meenakshi.jpg"
    assert marker.is_hidden_gem is True


def test_to_marker_rejects_destination_without_coordinates() -> None:
    destination = _destination("madurai-mystery-lane", latitude=None, longitude=None)
    with pytest.raises(ValueError):
        to_marker(destination)

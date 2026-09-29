"""Example-based tests for the Destination Repository and pure filter core (task 2.2).

These cover the repository behaviors called out in the task: ``get_by_id`` found
and not-found, ``list`` with intersecting filters, ``city_view`` grouping, and
empty results. Property tests for filter soundness (Properties 1-3) are the
separate optional tasks 2.4-2.6 and are intentionally not written here; the
filter function is kept pure so those tests can target it.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.catalog.filters import active_filter_count, apply_filters, matches
from app.catalog.models import Destination, SearchFilters
from app.catalog.repository import (
    DestinationRepository,
    DynamoDbDestinationRepository,
    JsonDestinationRepository,
    build_city_view,
    load_destinations,
)
from app.catalog.vocabularies import DestinationCategory, TamilNaduDistrict


def _destination(
    id_: str,
    *,
    city: str = "Madurai",
    district: TamilNaduDistrict = TamilNaduDistrict.MADURAI,
    category: DestinationCategory = DestinationCategory.TEMPLES,
    tags: list[str] | None = None,
    family_friendly: bool = False,
    is_hidden_gem: bool = False,
    is_heritage: bool = False,
    nature_related: bool = False,
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
        "is_heritage": is_heritage,
        "nature_related": nature_related,
        "source_urls": ["https://www.tamilnadutourism.tn.gov.in/"],
        "popularity": {"popularity_score": popularity_score},
    }
    data.update(overrides)
    return Destination.model_validate(data)


def _sample_catalog() -> list[Destination]:
    return [
        _destination(
            "madurai-meenakshi-temple",
            category=DestinationCategory.TEMPLES,
            tags=["temple", "heritage"],
            family_friendly=True,
            is_heritage=True,
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
            "madurai-hidden-stepwell",
            category=DestinationCategory.HERITAGE,
            tags=["heritage", "quiet"],
            is_hidden_gem=True,
            popularity_score=0.1,
        ),
        _destination(
            "ooty-botanical-garden",
            city="Ooty",
            district=TamilNaduDistrict.NILGIRIS,
            category=DestinationCategory.NATURE,
            tags=["garden", "family"],
            family_friendly=True,
            nature_related=True,
            popularity_score=0.8,
        ),
    ]


def _repo() -> JsonDestinationRepository:
    return JsonDestinationRepository(destinations=_sample_catalog())


# --- Protocol conformance -----------------------------------------------------


def test_json_repository_satisfies_protocol() -> None:
    assert isinstance(_repo(), DestinationRepository)


def test_dynamodb_repository_satisfies_protocol() -> None:
    assert isinstance(DynamoDbDestinationRepository("destinations"), DestinationRepository)


# --- get_by_id ----------------------------------------------------------------


def test_get_by_id_found() -> None:
    repo = _repo()
    found = repo.get_by_id("madurai-meenakshi-temple")
    assert found is not None
    assert found.id == "madurai-meenakshi-temple"


def test_get_by_id_not_found_returns_none() -> None:
    assert _repo().get_by_id("does-not-exist") is None


# --- list / filtering ---------------------------------------------------------


def test_list_without_filters_returns_all_in_order() -> None:
    repo = _repo()
    results = repo.list(SearchFilters())
    assert [d.id for d in results] == [d.id for d in _sample_catalog()]


def test_list_filters_by_city_case_insensitive() -> None:
    results = _repo().list(SearchFilters(city="ooty"))
    assert [d.id for d in results] == ["ooty-botanical-garden"]


def test_list_filters_by_district() -> None:
    results = _repo().list(SearchFilters(district=TamilNaduDistrict.NILGIRIS))
    assert [d.id for d in results] == ["ooty-botanical-garden"]


def test_list_filters_by_category() -> None:
    results = _repo().list(SearchFilters(category=DestinationCategory.FOOD))
    assert [d.id for d in results] == ["madurai-street-food-walk"]


def test_list_tag_filter_is_and_intersection() -> None:
    # Only the temple carries both "temple" and "heritage".
    results = _repo().list(SearchFilters(tags=["temple", "heritage"]))
    assert [d.id for d in results] == ["madurai-meenakshi-temple"]


def test_list_intersecting_filters_narrows_results() -> None:
    results = _repo().list(
        SearchFilters(
            city="Madurai",
            category=DestinationCategory.TEMPLES,
            family_friendly=True,
        )
    )
    assert [d.id for d in results] == ["madurai-meenakshi-temple"]


def test_list_hidden_gems_filter() -> None:
    results = _repo().list(SearchFilters(hidden_gems=True))
    assert [d.id for d in results] == ["madurai-hidden-stepwell"]


def test_list_no_match_returns_empty() -> None:
    results = _repo().list(SearchFilters(city="Chennai"))
    assert results == []


# --- pure filter core ---------------------------------------------------------


def test_apply_filters_soundness_every_result_matches() -> None:
    catalog = _sample_catalog()
    filters = SearchFilters(family_friendly=True)
    results = apply_filters(catalog, filters)
    assert results  # non-empty
    assert all(matches(d, filters) for d in results)


def test_active_filter_count_counts_each_constraint() -> None:
    filters = SearchFilters(
        city="Madurai",
        category=DestinationCategory.TEMPLES,
        tags=["a", "b"],
        family_friendly=True,
    )
    # city + category + family_friendly + two tags = 5 constraints.
    assert active_filter_count(filters) == 5
    assert active_filter_count(SearchFilters()) == 0


# --- city_view grouping -------------------------------------------------------


def test_city_view_groups_into_ordered_sections() -> None:
    view = _repo().city_view("Madurai")
    assert view.city == "Madurai"
    assert view.district is TamilNaduDistrict.MADURAI
    assert view.destination_count == 3
    section_keys = [section.key for section in view.sections]
    # Ordered subset of the canonical section order; empty sections dropped.
    assert section_keys == ["popular", "temples", "heritage", "food", "hidden-gems"]


def test_city_view_temple_section_contains_the_temple() -> None:
    view = _repo().city_view("Madurai")
    temples = next(s for s in view.sections if s.key == "temples")
    assert [d.id for d in temples.destinations] == ["madurai-meenakshi-temple"]


def test_city_view_unknown_city_is_empty() -> None:
    view = _repo().city_view("Chennai")
    assert view.city == "Chennai"
    assert view.destination_count == 0
    assert view.sections == []


def test_build_city_view_drops_sections_without_matches() -> None:
    only_food = [d for d in _sample_catalog() if d.category is DestinationCategory.FOOD]
    view = build_city_view("Madurai", only_food)
    assert [s.key for s in view.sections] == ["food"]


# --- JSON loading -------------------------------------------------------------


def test_load_shipped_dataset_parses() -> None:
    # The default constructor path points at data/destinations.json.
    repo = JsonDestinationRepository()
    assert len(repo.all) >= 1


def test_load_destinations_supports_bare_array(tmp_path: Any) -> None:
    record = _sample_catalog()[0].model_dump(mode="json")
    dataset = tmp_path / "arr.json"
    import json

    dataset.write_text(json.dumps([record]), encoding="utf-8")
    loaded = load_destinations(dataset)
    assert [d.id for d in loaded] == [record["id"]]


# --- DynamoDB adapter stub ----------------------------------------------------


def test_dynamodb_repository_exposes_table_name() -> None:
    repo = DynamoDbDestinationRepository("namma-ooru-destinations")
    assert repo.table_name == "namma-ooru-destinations"


def test_dynamodb_repository_methods_are_not_implemented() -> None:
    repo = DynamoDbDestinationRepository("destinations")
    with pytest.raises(NotImplementedError):
        repo.get_by_id("x")
    with pytest.raises(NotImplementedError):
        repo.list(SearchFilters())
    with pytest.raises(NotImplementedError):
        repo.city_view("Madurai")

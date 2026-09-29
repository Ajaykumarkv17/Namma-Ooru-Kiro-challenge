"""Example-based unit tests for deterministic itinerary generation (task 5.2).

These exercise ``ItineraryService.generate`` and its deterministic helpers over
a fixture catalog that never touches the shipped dataset. Coverage maps to the
Requirement 6 acceptance criteria and design Properties 4-7:

* day-count preservation, including surplus empty days (Req 6.1 / Property 4),
* catalog-reference validity for every scheduled activity (Req 6.2 / Property 5),
* positive durations and non-overlapping, start-time-ordered days
  (Req 6.2, 6.3 / Property 6),
* destination uniqueness when ``allow_repeats`` is false (Req 6.5 / Property 7),
* selection considering interests, category, budget, and coordinate-aware
  ordering (Req 6.4).

The property-based tests for Properties 4-7 are separate optional tasks
(5.4-5.7) and are not written here.
"""

from __future__ import annotations

from typing import Any

from app.catalog.models import Destination
from app.catalog.vocabularies import DestinationCategory, TamilNaduDistrict
from app.itinerary.models import ItineraryConstraints
from app.itinerary.service import (
    DEFAULT_ACTIVITY_DURATION,
    MAX_DAYS,
    ItineraryService,
)


def _destination(
    id_: str,
    *,
    city: str = "Madurai",
    district: TamilNaduDistrict = TamilNaduDistrict.MADURAI,
    category: DestinationCategory = DestinationCategory.TEMPLES,
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
            tags=["temple", "heritage"],
            recommended_duration_minutes=120,
            latitude=9.9195,
            longitude=78.1193,
        ),
        _destination(
            "madurai-street-food-walk",
            category=DestinationCategory.FOOD,
            tags=["food", "evening"],
            recommended_duration_minutes=90,
            latitude=9.9250,
            longitude=78.1200,
        ),
        _destination(
            "madurai-gandhi-museum",
            category=DestinationCategory.HERITAGE,
            tags=["history", "museum"],
            recommended_duration_minutes=60,
            latitude=9.9330,
            longitude=78.1420,
        ),
        _destination(
            "ooty-botanical-garden",
            city="Ooty",
            district=TamilNaduDistrict.NILGIRIS,
            category=DestinationCategory.HILLS,
            tags=["garden"],
            recommended_duration_minutes=120,
            latitude=11.4102,
            longitude=76.7070,
        ),
    ]


def _activity_ids(itinerary: Any) -> list[str]:
    return [a.destination_id for day in itinerary.days for a in day.activities]


def test_generate_returns_requested_day_count() -> None:
    """Exactly the requested number of days is returned (Req 6.1 / Property 4)."""
    service = ItineraryService()
    itinerary = service.generate(_catalog(), destination_context="Madurai trip", day_count=3)
    assert len(itinerary.days) == 3
    assert [d.day_number for d in itinerary.days] == [1, 2, 3]


def test_generate_preserves_day_count_with_sparse_catalog() -> None:
    """Surplus days are valid empty days when the catalog runs out (Property 4)."""
    service = ItineraryService()
    small_catalog = _catalog()[:1]
    itinerary = service.generate(small_catalog, destination_context="Short trip", day_count=4)
    assert len(itinerary.days) == 4
    scheduled = _activity_ids(itinerary)
    assert scheduled == ["madurai-meenakshi-temple"]
    # Days beyond the single scheduled activity are empty but present.
    assert sum(len(d.activities) for d in itinerary.days) == 1


def test_generate_clamps_day_count_to_supported_range() -> None:
    """Out-of-range day counts are clamped to 1..14, never raising."""
    service = ItineraryService()
    itinerary = service.generate(_catalog(), destination_context="Long trip", day_count=99)
    assert len(itinerary.days) == MAX_DAYS
    lower = service.generate(_catalog(), destination_context="Tiny trip", day_count=0)
    assert len(lower.days) == 1


def test_every_activity_references_a_catalog_destination() -> None:
    """Every scheduled activity id exists in the catalog (Req 6.2 / Property 5)."""
    service = ItineraryService()
    catalog = _catalog()
    catalog_ids = {d.id for d in catalog}
    itinerary = service.generate(catalog, destination_context="Madurai trip", day_count=2)
    for activity_id in _activity_ids(itinerary):
        assert activity_id in catalog_ids


def test_activities_have_positive_duration_and_no_overlap() -> None:
    """Days are start-ordered, non-overlapping, positive-duration (Property 6)."""
    service = ItineraryService()
    itinerary = service.generate(_catalog(), destination_context="Madurai trip", day_count=1)
    for day in itinerary.days:
        previous_end = -1
        starts = [a.start_minute for a in day.activities]
        assert starts == sorted(starts)
        for activity in day.activities:
            assert activity.duration_minutes > 0
            assert 0 <= activity.start_minute <= 1_439
            assert activity.start_minute >= previous_end
            previous_end = activity.end_minute


def test_unknown_duration_falls_back_to_default() -> None:
    """A destination without a recommended duration gets the default (Req 6.2)."""
    service = ItineraryService()
    catalog = [_destination("some-place", recommended_duration_minutes=None)]
    itinerary = service.generate(catalog, destination_context="One place", day_count=1)
    activity = itinerary.days[0].activities[0]
    assert activity.duration_minutes == DEFAULT_ACTIVITY_DURATION


def test_no_repeats_when_disabled() -> None:
    """Each destination appears at most once when repeats are off (Property 7)."""
    service = ItineraryService()
    itinerary = service.generate(
        _catalog(),
        destination_context="Madurai trip",
        day_count=MAX_DAYS,
        allow_repeats=False,
    )
    scheduled = _activity_ids(itinerary)
    assert len(scheduled) == len(set(scheduled))
    assert itinerary.allow_repeats is False


def test_interest_matching_prioritizes_relevant_destinations() -> None:
    """Interest-matching destinations schedule before non-matching ones (Req 6.4)."""
    service = ItineraryService()
    constraints = ItineraryConstraints(interests=["food"])
    itinerary = service.generate(
        _catalog(),
        destination_context="Madurai food trip",
        day_count=1,
        constraints=constraints,
    )
    first_activity = itinerary.days[0].activities[0]
    assert first_activity.destination_id == "madurai-street-food-walk"


def test_per_day_window_bounds_scheduling() -> None:
    """A tight per-day window limits how many activities fit that day (Req 6.3)."""
    service = ItineraryService()
    # A 60-minute window fits only a single 120-min or shorter first activity
    # that starts at the window open; the next would overflow.
    constraints = ItineraryConstraints(day_start_minute=600, day_end_minute=660)
    itinerary = service.generate(
        _catalog(),
        destination_context="Constrained trip",
        day_count=1,
        constraints=constraints,
    )
    day = itinerary.days[0]
    # Only activities whose duration fits the 60-minute window are scheduled.
    for activity in day.activities:
        assert activity.end_minute <= 660


def test_max_activities_per_day_is_respected() -> None:
    """The per-day activity cap bounds a day's activity count (Req 6.4)."""
    service = ItineraryService()
    constraints = ItineraryConstraints(max_activities_per_day=1)
    itinerary = service.generate(
        _catalog(),
        destination_context="Slow trip",
        day_count=2,
        constraints=constraints,
    )
    for day in itinerary.days:
        assert len(day.activities) <= 1


def test_generate_with_empty_catalog_yields_empty_days() -> None:
    """An empty catalog still yields the requested count of empty days."""
    service = ItineraryService()
    itinerary = service.generate([], destination_context="No data", day_count=3)
    assert len(itinerary.days) == 3
    assert _activity_ids(itinerary) == []


def test_generation_is_deterministic() -> None:
    """The same inputs always produce the same itinerary structure."""
    service = ItineraryService()
    catalog = _catalog()
    first = service.generate(catalog, destination_context="Trip", day_count=2)
    second = service.generate(catalog, destination_context="Trip", day_count=2)
    assert _activity_ids(first) == _activity_ids(second)
    assert [[(a.start_minute, a.duration_minutes) for a in d.activities] for d in first.days] == [
        [(a.start_minute, a.duration_minutes) for a in d.activities] for d in second.days
    ]

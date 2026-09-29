"""Example-based unit tests for deterministic itinerary edits (task 5.3).

These exercise ``ItineraryService.apply_operation`` and its per-operation
helpers over a fixture catalog that never touches the shipped dataset. Coverage
maps to the Requirement 7 acceptance criteria and design Properties 8-10:

* every operation's success path (add, remove, replace, reorder, constrain),
* remove locality - removing one activity changes no other (Req 7.2 / Property 9),
* replace validity - exactly one destination changes and the replacement exists
  in the catalog (Req 7.2 / Property 10),
* edit invariant preservation - after any applied op the itinerary keeps valid
  catalog references, positive durations, and non-overlapping start-ordered days
  (Req 7.3 / Property 8),
* unchanged-on-failure - an invalid edit returns the original itinerary with an
  explanation and ``changed=False`` (Req 7.4).

The property-based tests for Properties 8-10 are separate optional tasks and are
not written here.
"""

from __future__ import annotations

from typing import Any

from app.catalog.models import Destination
from app.catalog.vocabularies import DestinationCategory, TamilNaduDistrict
from app.itinerary.models import (
    AddOperation,
    ConstrainOperation,
    Itinerary,
    ItineraryConstraints,
    RemoveOperation,
    ReorderOperation,
    ReplaceOperation,
)
from app.itinerary.service import ItineraryService


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
            recommended_duration_minutes=120,
        ),
        _destination(
            "madurai-street-food-walk",
            category=DestinationCategory.FOOD,
            recommended_duration_minutes=90,
        ),
        _destination(
            "madurai-gandhi-museum",
            category=DestinationCategory.HERITAGE,
            recommended_duration_minutes=60,
        ),
        _destination(
            "madurai-thirumalai-palace",
            category=DestinationCategory.HERITAGE,
            recommended_duration_minutes=75,
        ),
    ]


def _base_itinerary(day_count: int = 1, **kwargs: Any) -> Itinerary:
    service = ItineraryService()
    return service.generate(
        _catalog(),
        destination_context="Madurai trip",
        day_count=day_count,
        **kwargs,
    )


def _all_activities(itinerary: Itinerary) -> list[Any]:
    return [a for day in itinerary.days for a in day.activities]


def _assert_invariants(itinerary: Itinerary, catalog_ids: set[str]) -> None:
    """Assert Property 8: references valid, durations positive, days non-overlap."""
    for day in itinerary.days:
        previous_end = -1
        starts = [a.start_minute for a in day.activities]
        assert starts == sorted(starts), "activities must be start-time ordered"
        for activity in day.activities:
            assert activity.destination_id in catalog_ids
            assert activity.duration_minutes > 0
            assert 0 <= activity.start_minute <= 1_439
            assert activity.start_minute >= previous_end, "activities must not overlap"
            previous_end = activity.end_minute


# --- Add -----------------------------------------------------------------


def test_add_schedules_new_activity_and_preserves_invariants() -> None:
    """Add inserts a catalog destination and reschedules the day (Property 8)."""
    service = ItineraryService()
    catalog = _catalog()
    # Start from a one-activity day so we have room to add.
    itinerary = service.generate(
        catalog,
        destination_context="Madurai trip",
        day_count=1,
        constraints=ItineraryConstraints(max_activities_per_day=1),
    )
    present = {a.destination_id for a in _all_activities(itinerary)}
    to_add = next(d.id for d in catalog if d.id not in present)
    result = service.apply_operation(itinerary, AddOperation(destination_id=to_add), catalog)
    assert result.changed is True
    added_ids = {a.destination_id for a in _all_activities(result.itinerary)}
    assert to_add in added_ids
    _assert_invariants(result.itinerary, {d.id for d in catalog})


def test_add_unknown_destination_returns_unchanged() -> None:
    """Adding a destination absent from the catalog is rejected (Req 7.4)."""
    service = ItineraryService()
    catalog = _catalog()
    itinerary = _base_itinerary()
    result = service.apply_operation(
        itinerary, AddOperation(destination_id="not-a-real-place"), catalog
    )
    assert result.changed is False
    assert result.itinerary == itinerary
    assert "catalog" in result.explanation.lower()


def test_add_unknown_day_returns_unchanged() -> None:
    """Adding to a day that does not exist is rejected unchanged (Req 7.4)."""
    service = ItineraryService()
    catalog = _catalog()
    itinerary = _base_itinerary(day_count=1)
    result = service.apply_operation(
        itinerary,
        AddOperation(destination_id="madurai-thirumalai-palace", day_number=9),
        catalog,
    )
    assert result.changed is False
    assert result.itinerary == itinerary


# --- Remove --------------------------------------------------------------


def test_remove_by_destination_id_changes_only_target() -> None:
    """Remove drops only the target activity (Req 7.2 / Property 9)."""
    service = ItineraryService()
    catalog = _catalog()
    itinerary = _base_itinerary()
    day = itinerary.days[0]
    assert len(day.activities) >= 2
    target = day.activities[0]
    others = [a for a in day.activities if a is not day.activities[0]]
    result = service.apply_operation(
        itinerary,
        RemoveOperation(day_number=1, destination_id=target.destination_id),
        catalog,
    )
    assert result.changed is True
    remaining = result.itinerary.days[0].activities
    assert target.destination_id not in {a.destination_id for a in remaining}
    # Every surviving activity is byte-for-byte unchanged (locality).
    assert remaining == others


def test_remove_by_index_changes_only_target() -> None:
    """Remove by zero-based index drops that activity only (Property 9)."""
    service = ItineraryService()
    catalog = _catalog()
    itinerary = _base_itinerary()
    original = list(itinerary.days[0].activities)
    assert len(original) >= 2
    result = service.apply_operation(
        itinerary, RemoveOperation(day_number=1, activity_index=1), catalog
    )
    assert result.changed is True
    expected = [a for i, a in enumerate(original) if i != 1]
    assert result.itinerary.days[0].activities == expected


def test_remove_missing_target_returns_unchanged() -> None:
    """Removing an activity that is not present is rejected unchanged (Req 7.4)."""
    service = ItineraryService()
    catalog = _catalog()
    itinerary = _base_itinerary()
    result = service.apply_operation(
        itinerary,
        RemoveOperation(day_number=1, destination_id="madurai-thirumalai-palace"),
        catalog,
    )
    # The palace may or may not be scheduled; force a guaranteed miss instead.
    absent = RemoveOperation(day_number=1, activity_index=999)
    result = service.apply_operation(itinerary, absent, catalog)
    assert result.changed is False
    assert result.itinerary == itinerary


# --- Replace -------------------------------------------------------------


def test_replace_changes_exactly_one_destination() -> None:
    """A successful replace changes exactly one destination id (Property 10)."""
    service = ItineraryService()
    catalog = _catalog()
    # Cap activities so at least one catalog destination stays unscheduled and is
    # available as a replacement target.
    itinerary = service.generate(
        catalog,
        destination_context="Madurai trip",
        day_count=1,
        constraints=ItineraryConstraints(max_activities_per_day=2),
    )
    day = itinerary.days[0]
    scheduled = {a.destination_id for a in _all_activities(itinerary)}
    target = day.activities[0].destination_id
    replacement = next(d.id for d in catalog if d.id not in scheduled)
    before_ids = [a.destination_id for a in _all_activities(itinerary)]
    result = service.apply_operation(
        itinerary,
        ReplaceOperation(
            day_number=1,
            target_destination_id=target,
            replacement_destination_id=replacement,
        ),
        catalog,
    )
    assert result.changed is True
    after_ids = [a.destination_id for a in _all_activities(result.itinerary)]
    # Exactly one id differs, and the replacement is present.
    diffs = [(b, a) for b, a in zip(before_ids, after_ids, strict=True) if b != a]
    assert diffs == [(target, replacement)]
    assert replacement in {d.id for d in catalog}
    _assert_invariants(result.itinerary, {d.id for d in catalog})


def test_replace_with_unknown_replacement_returns_unchanged() -> None:
    """Replacement not in the catalog is rejected unchanged (Req 7.4 / Property 10)."""
    service = ItineraryService()
    catalog = _catalog()
    itinerary = _base_itinerary()
    target = itinerary.days[0].activities[0].destination_id
    result = service.apply_operation(
        itinerary,
        ReplaceOperation(
            day_number=1,
            target_destination_id=target,
            replacement_destination_id="ghost-place",
        ),
        catalog,
    )
    assert result.changed is False
    assert result.itinerary == itinerary
    assert "catalog" in result.explanation.lower()


def test_replace_missing_target_returns_unchanged() -> None:
    """Replacing an activity not on the day is rejected unchanged (Req 7.4)."""
    service = ItineraryService()
    catalog = _catalog()
    itinerary = service.generate(
        catalog,
        destination_context="Madurai trip",
        day_count=1,
        constraints=ItineraryConstraints(max_activities_per_day=2),
    )
    scheduled = {a.destination_id for a in _all_activities(itinerary)}
    replacement = next(d.id for d in catalog if d.id not in scheduled)
    result = service.apply_operation(
        itinerary,
        ReplaceOperation(
            day_number=1,
            target_destination_id="madurai-not-scheduled-here",
            replacement_destination_id=replacement,
        ),
        catalog,
    )
    assert result.changed is False
    assert result.itinerary == itinerary


# --- Reorder -------------------------------------------------------------


def test_reorder_reverses_day_and_preserves_invariants() -> None:
    """Reorder re-times activities in the requested order (Req 7.1 / Property 8)."""
    service = ItineraryService()
    catalog = _catalog()
    itinerary = _base_itinerary()
    day = itinerary.days[0]
    assert len(day.activities) >= 2
    reversed_ids = [a.destination_id for a in reversed(day.activities)]
    result = service.apply_operation(
        itinerary,
        ReorderOperation(day_number=1, ordered_destination_ids=reversed_ids),
        catalog,
    )
    assert result.changed is True
    after_ids = [a.destination_id for a in result.itinerary.days[0].activities]
    assert after_ids == reversed_ids
    _assert_invariants(result.itinerary, {d.id for d in catalog})


def test_reorder_mismatched_ids_returns_unchanged() -> None:
    """A reorder list not matching the day's activities is rejected (Req 7.4)."""
    service = ItineraryService()
    catalog = _catalog()
    itinerary = _base_itinerary()
    result = service.apply_operation(
        itinerary,
        ReorderOperation(day_number=1, ordered_destination_ids=["madurai-meenakshi-temple"]),
        catalog,
    )
    # Unless the day happens to hold exactly that one activity, this mismatches.
    if len(itinerary.days[0].activities) != 1:
        assert result.changed is False
        assert result.itinerary == itinerary


# --- Constrain -----------------------------------------------------------


def test_constrain_reshapes_within_new_window() -> None:
    """Constrain re-times activities under new bounds (Req 7.1 / Property 8)."""
    service = ItineraryService()
    catalog = _catalog()
    itinerary = _base_itinerary()
    new_constraints = ItineraryConstraints(day_start_minute=600, day_end_minute=1_200)
    result = service.apply_operation(
        itinerary, ConstrainOperation(constraints=new_constraints), catalog
    )
    assert result.itinerary.constraints == new_constraints
    # First activity of each non-empty day starts at the new window open.
    for day in result.itinerary.days:
        if day.activities:
            assert day.activities[0].start_minute == 600
    _assert_invariants(result.itinerary, {d.id for d in catalog})


def test_constrain_activity_cap_drops_trailing_activities() -> None:
    """A tighter per-day activity cap drops trailing activities (Req 7.1)."""
    service = ItineraryService()
    catalog = _catalog()
    itinerary = _base_itinerary()
    assert len(itinerary.days[0].activities) >= 2
    new_constraints = ItineraryConstraints(max_activities_per_day=1)
    result = service.apply_operation(
        itinerary, ConstrainOperation(constraints=new_constraints), catalog
    )
    assert result.changed is True
    for day in result.itinerary.days:
        assert len(day.activities) <= 1
    _assert_invariants(result.itinerary, {d.id for d in catalog})


def test_apply_operation_never_mutates_input() -> None:
    """A failed edit leaves the original itinerary object untouched (Req 7.4)."""
    service = ItineraryService()
    catalog = _catalog()
    itinerary = _base_itinerary()
    snapshot = itinerary.model_copy(deep=True)
    service.apply_operation(itinerary, AddOperation(destination_id="unknown-place"), catalog)
    assert itinerary == snapshot

"""Example-based unit tests for the itinerary domain models (task 5.1).

These verify the field-level validation the models can guarantee on their own:
in-range start minutes, positive durations, positive day numbers, unambiguous
edit-op targeting, and correct discriminated-union parsing of structured edit
operations (Requirements 6.1, 6.2, 6.3, 7.1). Cross-activity ordering and catalog
membership belong to ``ItineraryService`` (tasks 5.2/5.3) and are covered there.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import TypeAdapter, ValidationError

from app.catalog.vocabularies import DestinationCategory, TamilNaduDistrict
from app.itinerary.models import (
    AddOperation,
    ConstrainOperation,
    Itinerary,
    ItineraryActivity,
    ItineraryConstraints,
    ItineraryDay,
    ItineraryOperation,
    ItineraryOperationEnvelope,
    OperationType,
    RemoveOperation,
    ReorderOperation,
    ReplaceOperation,
)

_OP_ADAPTER: TypeAdapter[ItineraryOperation] = TypeAdapter(ItineraryOperation)


def test_activity_accepts_valid_fields_and_computes_end_minute() -> None:
    activity = ItineraryActivity(
        destination_id="madurai-meenakshi-temple",
        start_minute=540,
        duration_minutes=120,
        rationale="Iconic temple to start the day.",
        travel_context="10 minutes from the hotel.",
        break_suggestion="Filter coffee nearby afterwards.",
    )
    assert activity.end_minute == 660


def test_activity_narrative_fields_default_empty() -> None:
    activity = ItineraryActivity(
        destination_id="madurai-meenakshi-temple",
        start_minute=0,
        duration_minutes=60,
    )
    assert activity.rationale == ""
    assert activity.travel_context == ""
    assert activity.break_suggestion == ""


@pytest.mark.parametrize("start_minute", [-1, 1_440])
def test_activity_rejects_out_of_range_start_minute(start_minute: int) -> None:
    with pytest.raises(ValidationError):
        ItineraryActivity(
            destination_id="madurai-meenakshi-temple",
            start_minute=start_minute,
            duration_minutes=60,
        )


@pytest.mark.parametrize("duration", [0, -30, 1_441])
def test_activity_rejects_non_positive_or_overlong_duration(duration: int) -> None:
    with pytest.raises(ValidationError):
        ItineraryActivity(
            destination_id="madurai-meenakshi-temple",
            start_minute=540,
            duration_minutes=duration,
        )


def test_activity_rejects_invalid_slug_destination_id() -> None:
    with pytest.raises(ValidationError):
        ItineraryActivity(
            destination_id="Not A Slug",
            start_minute=540,
            duration_minutes=60,
        )


def test_day_rejects_non_positive_day_number() -> None:
    with pytest.raises(ValidationError):
        ItineraryDay(day_number=0)


def test_itinerary_defaults_id_and_uniqueness_flag() -> None:
    itinerary = Itinerary(destination_context="Madurai temples and food")
    assert isinstance(itinerary.id, UUID)
    assert itinerary.allow_repeats is False
    assert itinerary.days == []
    assert isinstance(itinerary.constraints, ItineraryConstraints)


def test_itinerary_requires_non_empty_context() -> None:
    with pytest.raises(ValidationError):
        Itinerary(destination_context="")


def test_itinerary_preserves_supplied_days() -> None:
    itinerary = Itinerary(
        destination_context="Madurai temples",
        days=[
            ItineraryDay(
                day_number=1,
                activities=[
                    ItineraryActivity(
                        destination_id="madurai-meenakshi-temple",
                        start_minute=540,
                        duration_minutes=120,
                    )
                ],
            )
        ],
    )
    assert len(itinerary.days) == 1
    assert itinerary.days[0].activities[0].destination_id == "madurai-meenakshi-temple"


def test_constraints_accepts_vocabulary_values_and_window() -> None:
    constraints = ItineraryConstraints(
        interests=["temples", "food"],
        travel_style="relaxed",
        budget="moderate",
        starting_point="Madurai Junction",
        category=DestinationCategory.TEMPLES,
        district=TamilNaduDistrict.MADURAI,
        day_start_minute=540,
        day_end_minute=1_080,
        max_activities_per_day=4,
    )
    assert constraints.category is DestinationCategory.TEMPLES
    assert constraints.district is TamilNaduDistrict.MADURAI


def test_constraints_rejects_inverted_time_window() -> None:
    with pytest.raises(ValidationError):
        ItineraryConstraints(day_start_minute=1_080, day_end_minute=540)


def test_constraints_defaults_are_unconstrained() -> None:
    constraints = ItineraryConstraints()
    assert constraints.interests == []
    assert constraints.category is None
    assert constraints.day_start_minute is None


def test_add_operation_defaults_to_first_day() -> None:
    op = AddOperation(destination_id="madurai-meenakshi-temple")
    assert op.op is OperationType.ADD
    assert op.day_number == 1
    assert op.start_minute is None


def test_remove_operation_requires_exactly_one_target() -> None:
    with_index = RemoveOperation(day_number=1, activity_index=0)
    assert with_index.destination_id is None

    with_id = RemoveOperation(day_number=1, destination_id="madurai-meenakshi-temple")
    assert with_id.activity_index is None


def test_remove_operation_rejects_zero_or_both_targets() -> None:
    with pytest.raises(ValidationError):
        RemoveOperation(day_number=1)
    with pytest.raises(ValidationError):
        RemoveOperation(
            day_number=1,
            destination_id="madurai-meenakshi-temple",
            activity_index=0,
        )


def test_reorder_operation_requires_at_least_one_destination() -> None:
    with pytest.raises(ValidationError):
        ReorderOperation(day_number=1, ordered_destination_ids=[])


def test_replace_operation_holds_both_destinations() -> None:
    op = ReplaceOperation(
        day_number=2,
        target_destination_id="madurai-meenakshi-temple",
        replacement_destination_id="madurai-thirumalai-nayakkar-mahal",
    )
    assert op.op is OperationType.REPLACE


def test_constrain_operation_wraps_constraints() -> None:
    op = ConstrainOperation(constraints=ItineraryConstraints(interests=["food"]))
    assert op.op is OperationType.CONSTRAIN
    assert op.constraints.interests == ["food"]


def test_operation_union_parses_by_discriminator() -> None:
    parsed = _OP_ADAPTER.validate_python(
        {
            "op": "replace",
            "day_number": 1,
            "target_destination_id": "a-b",
            "replacement_destination_id": "c-d",
        }
    )
    assert isinstance(parsed, ReplaceOperation)

    added = _OP_ADAPTER.validate_python({"op": "add", "destination_id": "a-b"})
    assert isinstance(added, AddOperation)


def test_operation_union_rejects_unknown_op() -> None:
    with pytest.raises(ValidationError):
        _OP_ADAPTER.validate_python({"op": "delete", "day_number": 1})


def test_operation_envelope_validates_nested_operation() -> None:
    envelope = ItineraryOperationEnvelope.model_validate(
        {"operation": {"op": "remove", "day_number": 1, "activity_index": 0}}
    )
    assert isinstance(envelope.operation, RemoveOperation)

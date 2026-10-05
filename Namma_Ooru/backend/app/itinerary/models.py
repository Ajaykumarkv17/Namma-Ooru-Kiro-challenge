"""Pydantic models for the deterministic itinerary domain (Requirements 6, 7).

These models describe an ``Itinerary`` and the structured edit operations that a
traveler's natural-language request is translated into. They are pure data
contracts with validation only: no I/O, no AWS calls, no scheduling logic. The
deterministic ``ItineraryService`` (tasks 5.2, 5.3) consumes and produces these
models so its invariants stay property-testable (design Properties 4-10).

Design (design.md "Search, itinerary, and review models"):

``Itinerary`` groups ordered ``ItineraryDay`` plans. Each ``ItineraryDay`` holds
ordered ``ItineraryActivity`` entries. Each activity references a catalog
``DestinationId`` and carries a start minute (0..1439), a positive duration, and
the traveler-facing narrative fields (rationale, travel context, break
suggestion) that Requirement 6.6 renders. The activity narrative fields are
AI-generated prose kept in clearly named fields, separate from the source
``destination_id`` (AI/RAG steering).

``ItineraryConstraints`` captures the trip inputs from Requirement 6.1/6.4 that
shape generation and the ``Constrain`` edit op. ``ItineraryOperation`` is the
discriminated union of the five structured edit ops (add, remove, replace,
reorder, constrain) an AI Provider emits (Requirement 7.1); the deterministic
core applies them (task 5.3). Field-level validation here enforces the invariants
the models can guarantee on their own (positive durations, in-range start
minutes, positive day numbers); cross-activity ordering and catalog membership
are enforced by ``ItineraryService`` because they need the surrounding itinerary
and catalog.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.catalog.models import DestinationId
from app.catalog.vocabularies import DestinationCategory, TamilNaduDistrict

# A day spans minutes 0 (00:00) through 1439 (23:59); durations are positive and
# cannot exceed a single day. Reused by activities and by the reschedule/add ops.
StartMinute = Annotated[int, Field(ge=0, le=1_439)]
DurationMinutes = Annotated[int, Field(ge=1, le=1_440)]
DayNumber = Annotated[int, Field(ge=1)]
NarrativeText = Annotated[str, Field(default="", max_length=2_000)]


class ItineraryActivity(BaseModel):
    """A single scheduled visit within a day (Requirements 6.2, 6.3, 6.6).

    ``destination_id`` is a source catalog reference; ``ItineraryService``
    guarantees it resolves to a real Destination (Property 5). ``start_minute``
    and ``duration_minutes`` place the visit on the day's timeline and are
    validated to be in range and positive here; the service additionally
    guarantees per-day activities do not overlap (Property 6). ``rationale``,
    ``travel_context``, and ``break_suggestion`` are the traveler-facing
    narrative fields Requirement 6.6 displays; they are AI-generated prose kept
    separate from the source ``destination_id`` (AI/RAG steering) and default to
    empty so a deterministic-only itinerary is still valid without AI enrichment.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    destination_id: DestinationId
    start_minute: StartMinute
    duration_minutes: DurationMinutes
    rationale: NarrativeText = ""
    travel_context: NarrativeText = ""
    break_suggestion: NarrativeText = ""

    @property
    def end_minute(self) -> int:
        """Exclusive end of the visit on the day's timeline, in minutes.

        May exceed 1439 when a visit runs to the end of the day; callers that
        schedule the next activity use this to keep activities non-overlapping.
        """
        return self.start_minute + self.duration_minutes


class ItineraryDay(BaseModel):
    """One day plan: a positive day number and its ordered activities (6.3).

    ``day_number`` is 1-based. ``activities`` are stored in the order they occur;
    ``ItineraryService`` guarantees they are sorted by ``start_minute`` without
    temporal overlap (Property 6). The model permits an empty day so a freshly
    constructed or fully-edited-down day is representable.
    """

    model_config = ConfigDict(extra="forbid")

    day_number: DayNumber
    activities: list[ItineraryActivity] = Field(default_factory=list)


class ItineraryConstraints(BaseModel):
    """Trip inputs that shape generation and the ``Constrain`` edit op (6.1, 6.4).

    These are the traveler preferences from Requirement 6.1 that
    ``ItineraryService`` considers when selecting and ordering activities
    (Requirement 6.4): interests, travel style, budget, the starting point, and
    optional per-day time bounds. Every field is optional so a minimal request
    (destination + day count) is valid; absent fields impose no constraint
    (fail-soft). ``category`` and ``district`` are drawn from the controlled
    vocabularies so an unknown value cannot enter the domain.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    interests: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list
    )
    travel_style: str | None = Field(default=None, min_length=1, max_length=100)
    budget: str | None = Field(default=None, min_length=1, max_length=100)
    starting_point: str | None = Field(default=None, min_length=1, max_length=200)
    category: DestinationCategory | None = None
    district: TamilNaduDistrict | None = None
    day_start_minute: StartMinute | None = None
    day_end_minute: StartMinute | None = None
    max_activities_per_day: int | None = Field(default=None, ge=1, le=24)

    def model_post_init(self, __context: object) -> None:
        """Reject an inverted per-day window at the boundary (fail closed)."""
        if (
            self.day_start_minute is not None
            and self.day_end_minute is not None
            and self.day_end_minute <= self.day_start_minute
        ):
            raise ValueError("day_end_minute must be greater than day_start_minute.")


class Itinerary(BaseModel):
    """A generated multi-day trip plan (Requirements 6.1, 6.5).

    ``days`` is ordered by day number and, for a valid itinerary, has exactly the
    requested day count (Property 4). ``allow_repeats`` records the traveler's
    uniqueness preference: when ``False`` the service includes each Destination at
    most once across the whole itinerary (Requirement 6.5 / Property 7).
    ``destination_context`` is the free-text trip context (e.g. "Madurai temples
    and food") used for display and AI narrative; ``constraints`` retains the trip
    inputs so a later ``Constrain`` edit can re-apply them. ``id`` defaults to a
    fresh UUID so a freshly generated itinerary is addressable.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: UUID = Field(default_factory=uuid4)
    destination_context: str = Field(min_length=1, max_length=500)
    days: list[ItineraryDay] = Field(default_factory=list)
    allow_repeats: bool = False
    constraints: ItineraryConstraints = Field(default_factory=ItineraryConstraints)
    no_data_reason: str | None = Field(default=None, max_length=500)


class OperationType(str, Enum):
    """The five structured itinerary edit operations (Requirement 7.1)."""

    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"
    REORDER = "reorder"
    CONSTRAIN = "constrain"


class AddOperation(BaseModel):
    """Add a Destination to a day (Requirement 7.1).

    ``destination_id`` is the catalog place to insert; ``ItineraryService``
    validates its membership before applying (Property 8). ``day_number`` targets
    the day (defaulting to the first day when omitted). Optional ``start_minute``
    and ``duration_minutes`` request a placement; when omitted the service
    schedules the activity without overlapping existing activities (Property 6).
    """

    model_config = ConfigDict(extra="forbid")

    op: Literal[OperationType.ADD] = OperationType.ADD
    destination_id: DestinationId
    day_number: DayNumber = 1
    start_minute: StartMinute | None = None
    duration_minutes: DurationMinutes | None = None


class RemoveOperation(BaseModel):
    """Remove one activity, changing nothing else (Requirement 7.2 / Property 9).

    The target is addressed by ``day_number`` plus either the activity's
    ``destination_id`` or its zero-based ``activity_index`` within the day. Exactly
    one targeting field must be provided so the operation is unambiguous.
    """

    model_config = ConfigDict(extra="forbid")

    op: Literal[OperationType.REMOVE] = OperationType.REMOVE
    day_number: DayNumber
    destination_id: DestinationId | None = None
    activity_index: int | None = Field(default=None, ge=0)

    def model_post_init(self, __context: object) -> None:
        """Require exactly one activity target so removal is unambiguous."""
        targets = [self.destination_id is not None, self.activity_index is not None]
        if sum(targets) != 1:
            raise ValueError(
                "Provide exactly one of destination_id or activity_index to target the activity."
            )


class ReplaceOperation(BaseModel):
    """Swap one activity's Destination for another (Requirements 7.1, 7.2).

    ``target_destination_id`` selects the activity to replace within
    ``day_number``; ``replacement_destination_id`` is the new catalog place. The
    service validates that the replacement exists in the catalog and that exactly
    one activity's destination changes (Property 10).
    """

    model_config = ConfigDict(extra="forbid")

    op: Literal[OperationType.REPLACE] = OperationType.REPLACE
    day_number: DayNumber
    target_destination_id: DestinationId
    replacement_destination_id: DestinationId


class ReorderOperation(BaseModel):
    """Reorder the activities within a day (Requirement 7.1).

    ``ordered_destination_ids`` lists the day's destinations in the desired
    order. The service re-times the activities to preserve non-overlapping start
    ordering (Property 8) and rejects the operation if the ids do not match the
    day's current activities exactly.
    """

    model_config = ConfigDict(extra="forbid")

    op: Literal[OperationType.REORDER] = OperationType.REORDER
    day_number: DayNumber
    ordered_destination_ids: list[DestinationId] = Field(min_length=1)


class ConstrainOperation(BaseModel):
    """Re-apply updated trip constraints (Requirements 7.1, 6.4).

    Carries the new ``ItineraryConstraints`` the service uses to re-shape the
    itinerary (e.g. tighten the daily time window or change interests) while
    keeping every invariant (Property 8).
    """

    model_config = ConfigDict(extra="forbid")

    op: Literal[OperationType.CONSTRAIN] = OperationType.CONSTRAIN
    constraints: ItineraryConstraints


# The discriminated union of structured edit operations an AI Provider emits and
# the deterministic ``ItineraryService`` applies (Requirement 7.1). Pydantic uses
# the ``op`` literal on each member as the discriminator so a raw
# ``{"op": "remove", ...}`` payload parses into the correct concrete operation.
ItineraryOperation = Annotated[
    AddOperation | RemoveOperation | ReplaceOperation | ReorderOperation | ConstrainOperation,
    Field(discriminator="op"),
]


class ItineraryOperationEnvelope(BaseModel):
    """Wrapper so a bare structured operation can be parsed and validated alone.

    The AI Provider returns a single ``{op, ...}`` object; wrapping it lets the
    backend validate that object against the ``ItineraryOperation`` union before
    it reaches ``ItineraryService`` (design: reject/repair structured AI output on
    mismatch), without requiring a surrounding request model at this task.
    """

    model_config = ConfigDict(extra="forbid")

    operation: ItineraryOperation


class ItineraryRequest(BaseModel):
    """Validated request for a generated multi-day itinerary (Requirement 6.1)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    destination_context: str = Field(min_length=1, max_length=500)
    day_count: int = Field(ge=1, le=14)
    constraints: ItineraryConstraints = Field(default_factory=ItineraryConstraints)
    allow_repeats: bool = False


class ItineraryEditRequest(BaseModel):
    """Validated conversational edit request (Requirement 7.1)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request: str = Field(min_length=1, max_length=2_000)


class EditUnavailable(BaseModel):
    """Unchanged itinerary and safe explanation when an edit cannot apply (7.4)."""

    model_config = ConfigDict(extra="forbid")

    itinerary: Itinerary
    changed: Literal[False] = False
    explanation: str = Field(min_length=1, max_length=2_000)


class ItineraryEditSuccess(BaseModel):
    """Successful conversational edit result with its parsed operation."""

    model_config = ConfigDict(extra="forbid")

    itinerary: Itinerary
    changed: Literal[True] = True
    explanation: str = Field(min_length=1, max_length=2_000)
    operation: ItineraryOperation

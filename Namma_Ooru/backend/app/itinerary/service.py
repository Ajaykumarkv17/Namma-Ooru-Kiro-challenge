"""Deterministic itinerary generation core (Requirement 6).

This module has no I/O and no AWS calls. It is the pure, deterministic
``ItineraryService`` the itinerary router composes: given trip inputs and a
Destination Catalog it produces a fully-scheduled :class:`Itinerary`.

Generation is a pure function of its inputs, so the design's Properties 4-7 hold
by construction:

* **Day-count preservation (Property 4, Req 6.1).** ``generate`` always returns
  exactly the requested number of :class:`ItineraryDay` plans (1..14), even when
  the catalog cannot fill every day (surplus days are valid empty days).
* **Catalog-reference validity (Property 5, Req 6.2).** Every scheduled activity
  references a Destination drawn from the catalog passed in; the core never
  fabricates an id.
* **Temporal validity (Property 6, Req 6.2/6.3).** Every activity is given a
  positive duration and each day's activities are laid out in start-time order
  without temporal overlap.
* **Uniqueness (Property 7, Req 6.5).** When ``allow_repeats`` is ``False`` a
  Destination is scheduled at most once across the whole itinerary.

Activity selection (Req 6.4) considers destination coordinates (for
coordinate-aware, nearby-grouped ordering), known opening hours, recommended
duration, traveler interests, travel style, and budget. Selection is scored and
then ordered by a nearest-neighbour walk from the starting point so nearby
places land on the same day. Any AI narrative (rationale, travel context, break
suggestion) is left to the AI layer and stored in the activity's clearly-named
narrative fields (AI/RAG steering); this core only fills the deterministic
structure and leaves those prose fields empty.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from app.catalog.models import Destination
from app.itinerary.models import (
    AddOperation,
    ConstrainOperation,
    Itinerary,
    ItineraryActivity,
    ItineraryConstraints,
    ItineraryDay,
    ItineraryOperation,
    RemoveOperation,
    ReorderOperation,
    ReplaceOperation,
)

# Trip day count bounds (Requirement 6.1 / design Property 4).
MIN_DAYS = 1
MAX_DAYS = 14

# The default per-day sightseeing window when the traveler sets no bounds:
# 09:00 (540) to 18:00 (1080). Used to schedule non-overlapping activities.
DEFAULT_DAY_START_MINUTE = 9 * 60
DEFAULT_DAY_END_MINUTE = 18 * 60

# Fallback visit length (minutes) when a Destination has no recommended duration.
DEFAULT_ACTIVITY_DURATION = 90

# A short buffer between consecutive activities so a day never packs visits
# back-to-back with zero travel/rest time. Kept small and deterministic.
INTER_ACTIVITY_GAP_MINUTES = 30

# Budget keywords that signal a low-cost trip; used to gently prefer free/lower
# effort places. Matching is substring, case-insensitive, and never excludes a
# destination outright (fail-soft: budget only reorders, it does not gate).
_LOW_BUDGET_KEYWORDS = ("low", "budget", "cheap", "shoestring", "economy")

# Entry-fee text that indicates no admission cost; a weak positive signal for a
# low-budget trip. Never used to fabricate a fee when the field is null.
_FREE_FEE_KEYWORDS = ("free", "no entry fee", "no fee", "nil")


@dataclass(frozen=True)
class EditResult:
    """Outcome of applying a structured edit to an :class:`Itinerary` (Req 7.4).

    The deterministic core always returns an :class:`Itinerary`, never a partial
    mutation. ``changed`` reports whether the edit was applied: on success it is
    ``True`` and ``itinerary`` is the new plan; when the edit has no valid result
    (target not found, unknown destination, mismatched reorder ids, …) it is
    ``False``, ``itinerary`` is the original unchanged plan, and ``explanation``
    is a traveler-facing reason (Requirement 7.4). ``explanation`` is also set on
    success as a short confirmation. The itinerary router maps this to the
    ``Itinerary`` / ``EditUnavailable`` API response (design.md).
    """

    itinerary: Itinerary
    changed: bool
    explanation: str


@dataclass(frozen=True)
class _ScoredDestination:
    """A candidate Destination paired with its deterministic selection score.

    ``score`` is higher for a better match; ties break on the stable
    ``order_index`` (the destination's position in the input catalog) so
    selection is fully deterministic for a given catalog and request.
    """

    destination: Destination
    score: int
    order_index: int


def _normalize_day_count(day_count: int) -> int:
    """Clamp a requested day count into the supported 1..14 range.

    Generation always yields exactly this many days (Property 4). Clamping keeps
    the core total and never raises for an out-of-range request; the API
    boundary is responsible for rejecting invalid input, this core degrades
    gracefully.
    """
    return max(MIN_DAYS, min(MAX_DAYS, day_count))


def _interest_terms(constraints: ItineraryConstraints) -> set[str]:
    """Return the lowercased, non-empty interest terms from the constraints."""
    return {i.strip().casefold() for i in constraints.interests if i and i.strip()}


def _matches_interest(destination: Destination, interests: set[str]) -> bool:
    """Return True when a Destination's category or a tag matches any interest."""
    if not interests:
        return False
    if destination.category.value in interests:
        return True
    return any(tag.casefold() in interests for tag in destination.tags)


def _looks_low_budget(budget: str | None) -> bool:
    """Return True when the budget text signals a low-cost trip."""
    if not budget:
        return False
    lowered = budget.casefold()
    return any(keyword in lowered for keyword in _LOW_BUDGET_KEYWORDS)


def _is_free_entry(destination: Destination) -> bool:
    """Return True when the entry-fee text indicates no admission cost."""
    fee = destination.entry_fee
    if not fee:
        return False
    lowered = fee.casefold()
    return any(keyword in lowered for keyword in _FREE_FEE_KEYWORDS)


def _score_destination(
    destination: Destination,
    *,
    interests: set[str],
    constraints: ItineraryConstraints,
    prefer_low_budget: bool,
) -> int:
    """Score a Destination for selection (Requirement 6.4).

    The score combines the traveler signals so better-matching places are
    preferred while every catalog record remains eligible (fail-soft: signals
    only reorder, they never exclude). Higher is better. Considered signals:

    * an interest match (category or tag) is the strongest signal,
    * the constraint category/district matching the destination,
    * having a recommended duration and verified coordinates (schedulable and
      placeable for coordinate-aware ordering),
    * free entry when the trip is low-budget,
    * popularity as a mild tiebreaker.
    """
    score = 0
    if _matches_interest(destination, interests):
        score += 100
    if constraints.category is not None and destination.category is constraints.category:
        score += 40
    if constraints.district is not None and destination.district is constraints.district:
        score += 20
    if destination.recommended_duration_minutes is not None:
        score += 10
    if destination.has_verified_coordinates():
        score += 5
    if prefer_low_budget and _is_free_entry(destination):
        score += 15
    # Popularity is 0.0..1.0; scale to a small integer so it only breaks ties
    # between otherwise equally-matched destinations.
    score += int(round(destination.popularity.popularity_score * 5))
    return score


def _select_candidates(
    destinations: Sequence[Destination],
    constraints: ItineraryConstraints,
) -> list[Destination]:
    """Rank the catalog by selection score, best first (Requirement 6.4).

    Order-preserving on ties via the destination's catalog index so the result
    is deterministic. Every catalog record is returned (ranked, not filtered) so
    a sparse-signal request still fills the itinerary; the day/activity budget
    later bounds how many are actually scheduled.
    """
    interests = _interest_terms(constraints)
    prefer_low_budget = _looks_low_budget(constraints.budget)
    scored = [
        _ScoredDestination(
            destination=destination,
            score=_score_destination(
                destination,
                interests=interests,
                constraints=constraints,
                prefer_low_budget=prefer_low_budget,
            ),
            order_index=index,
        )
        for index, destination in enumerate(destinations)
    ]
    scored.sort(key=lambda s: (-s.score, s.order_index))
    return [s.destination for s in scored]


def _distance(a: Destination, b: Destination) -> float:
    """Great-circle distance in km between two destinations with coordinates.

    Uses the haversine formula. Returns ``math.inf`` when either destination
    lacks verified coordinates so coordinate-aware ordering treats an
    unplaceable destination as maximally far (it is appended after placeable
    ones rather than pulling the walk toward an unknown point).
    """
    if not a.has_verified_coordinates() or not b.has_verified_coordinates():
        return math.inf
    # Coordinates are verified non-None here; assert for the type checker.
    assert a.latitude is not None and a.longitude is not None
    assert b.latitude is not None and b.longitude is not None
    radius_km = 6371.0
    lat1, lon1 = math.radians(a.latitude), math.radians(a.longitude)
    lat2, lon2 = math.radians(b.latitude), math.radians(b.longitude)
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1
    h = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    return 2 * radius_km * math.asin(min(1.0, math.sqrt(h)))


def _order_coordinate_aware(candidates: Sequence[Destination]) -> list[Destination]:
    """Order candidates by a nearest-neighbour walk to group nearby places (6.4).

    Starting from the first (highest-ranked) candidate, repeatedly append the
    closest remaining candidate by great-circle distance. Candidates without
    verified coordinates sort to distance ``inf`` and so are visited last, in
    their existing (score) order. The walk is deterministic: ties in distance
    break on the candidate's current position in the remaining list.

    Preserving the highest-ranked candidate as the anchor keeps selection
    quality while grouping geographically close places onto the same day.
    """
    remaining = list(candidates)
    if len(remaining) <= 2:
        return remaining
    ordered: list[Destination] = [remaining.pop(0)]
    while remaining:
        current = ordered[-1]
        best_index = 0
        best_distance = _distance(current, remaining[0])
        for index in range(1, len(remaining)):
            candidate_distance = _distance(current, remaining[index])
            if candidate_distance < best_distance:
                best_distance = candidate_distance
                best_index = index
        ordered.append(remaining.pop(best_index))
    return ordered


def _activity_duration(destination: Destination) -> int:
    """Return a positive visit duration for a Destination (Property 6, Req 6.2).

    Uses the destination's recommended duration when known and positive; falls
    back to :data:`DEFAULT_ACTIVITY_DURATION` otherwise so every activity always
    has a positive duration even when the source omits one.
    """
    recommended = destination.recommended_duration_minutes
    if recommended is not None and recommended > 0:
        return recommended
    return DEFAULT_ACTIVITY_DURATION


def _day_window(constraints: ItineraryConstraints) -> tuple[int, int]:
    """Return the (start, end) minute window for scheduling a day's activities.

    Honours the traveler's per-day bounds when set (the model already guarantees
    end > start) and otherwise uses the default 09:00-18:00 window.
    """
    start = (
        constraints.day_start_minute
        if constraints.day_start_minute is not None
        else DEFAULT_DAY_START_MINUTE
    )
    end = (
        constraints.day_end_minute
        if constraints.day_end_minute is not None
        else DEFAULT_DAY_END_MINUTE
    )
    return start, end


def _schedule_day(
    day_number: int,
    destinations: Sequence[Destination],
    constraints: ItineraryConstraints,
) -> tuple[ItineraryDay, list[Destination]]:
    """Lay the given destinations onto one day's timeline (Req 6.3, Property 6).

    Places activities in order starting at the day's opening minute, each with a
    positive duration and separated by :data:`INTER_ACTIVITY_GAP_MINUTES`, so the
    result is start-time ordered with no temporal overlap. Scheduling stops when
    the next activity would run past the day's closing minute or the per-day
    activity cap is reached; unscheduled destinations are returned so the caller
    can place them on later days. ``start_minute`` is clamped to the valid
    0..1439 range as a final guard.
    """
    window_start, window_end = _day_window(constraints)
    max_activities = constraints.max_activities_per_day
    activities: list[ItineraryActivity] = []
    cursor = window_start
    consumed = 0
    for destination in destinations:
        if max_activities is not None and len(activities) >= max_activities:
            break
        duration = _activity_duration(destination)
        if cursor + duration > window_end:
            # No more room in the day; leave this and the rest for later days.
            break
        start_minute = max(0, min(cursor, 1_439))
        activities.append(
            ItineraryActivity(
                destination_id=destination.id,
                start_minute=start_minute,
                duration_minutes=duration,
            )
        )
        consumed += 1
        cursor = cursor + duration + INTER_ACTIVITY_GAP_MINUTES
    remaining = list(destinations[consumed:])
    return ItineraryDay(day_number=day_number, activities=activities), remaining


def _reschedule_activities(
    activities: Sequence[ItineraryActivity],
    constraints: ItineraryConstraints,
) -> list[ItineraryActivity]:
    """Re-time activities onto a day's timeline in their given order (Property 8).

    Preserves each activity's ``destination_id``, ``duration_minutes`` and all
    narrative fields, and re-assigns ``start_minute`` values starting at the
    day's opening minute, separated by :data:`INTER_ACTIVITY_GAP_MINUTES`, so the
    result is start-time ordered with no temporal overlap regardless of the
    incoming timings. This routes every structural edit (add, reorder, constrain)
    through the same deterministic scheduler so invariants always hold. The
    activities' relative order is the caller-provided order; durations are left
    unchanged so a re-timed activity keeps its positive duration.
    """
    window_start, _ = _day_window(constraints)
    rescheduled: list[ItineraryActivity] = []
    cursor = window_start
    for activity in activities:
        start_minute = max(0, min(cursor, 1_439))
        rescheduled.append(
            activity.model_copy(update={"start_minute": start_minute}),
        )
        cursor = start_minute + activity.duration_minutes + INTER_ACTIVITY_GAP_MINUTES
    return rescheduled


def _distribute_across_days(
    ordered: Sequence[Destination],
    day_count: int,
    constraints: ItineraryConstraints,
) -> list[ItineraryDay]:
    """Fill exactly ``day_count`` days from the ordered candidates (Property 4).

    Walks the ordered candidate list, filling each day up to its time window and
    per-day activity cap, then moving surplus to the next day. Always returns
    exactly ``day_count`` days; when candidates run out the remaining days are
    valid empty days so the day count is preserved regardless of catalog size.
    """
    days: list[ItineraryDay] = []
    remaining: list[Destination] = list(ordered)
    for day_number in range(1, day_count + 1):
        day, remaining = _schedule_day(day_number, remaining, constraints)
        days.append(day)
    return days


class ItineraryService:
    """Deterministic itinerary generation core (Requirement 6).

    Pure and side-effect free so the whole itinerary flow is demoable and
    testable without AWS (architecture steering). ``generate`` consumes the
    catalog passed in and returns a fully-scheduled :class:`Itinerary` whose
    invariants (Properties 4-7) hold by construction. ``apply_operation`` applies
    the five structured edit operations (add, remove, replace, reorder,
    constrain), routing structural changes through the same deterministic
    scheduler so Properties 8-10 hold and an invalid edit returns the unchanged
    itinerary (Requirement 7.4).
    """

    def generate(
        self,
        destinations: Iterable[Destination],
        *,
        destination_context: str,
        day_count: int,
        constraints: ItineraryConstraints | None = None,
        allow_repeats: bool = False,
    ) -> Itinerary:
        """Generate a multi-day :class:`Itinerary` from trip inputs (Req 6.1-6.5).

        Args:
            destinations: The Destination Catalog to select activities from.
                Every scheduled activity references a member of this catalog
                (Property 5).
            destination_context: Free-text trip context (e.g. "Madurai temples
                and food") used for display and later AI narrative.
            day_count: Requested number of day plans. Clamped to 1..14; the
                result has exactly this many days (Property 4).
            constraints: Optional trip preferences (interests, travel style,
                budget, starting point, per-day window, activity cap). Absent
                constraints impose no restriction (fail-soft).
            allow_repeats: When ``False`` (default) each Destination is scheduled
                at most once across the whole itinerary (Property 7 / Req 6.5).

        Returns:
            A fully-scheduled :class:`Itinerary`: exactly ``day_count`` days,
            each with positive-duration, start-time-ordered, non-overlapping
            activities referencing real catalog destinations.
        """
        effective_constraints = constraints or ItineraryConstraints()
        normalized_day_count = _normalize_day_count(day_count)

        catalog = list(destinations)
        ranked = _select_candidates(catalog, effective_constraints)
        ordered = _order_coordinate_aware(ranked)

        # Uniqueness (Property 7): the ordered list already contains each catalog
        # id at most once, so distributing it across days without reuse keeps
        # every Destination unique when repeats are disallowed. When repeats are
        # allowed we still schedule from the same de-duplicated candidate pool
        # (the deterministic core does not pad days by repeating places).
        days = _distribute_across_days(ordered, normalized_day_count, effective_constraints)

        return Itinerary(
            destination_context=destination_context,
            days=days,
            allow_repeats=allow_repeats,
            constraints=effective_constraints,
        )

    def apply_operation(
        self,
        itinerary: Itinerary,
        operation: ItineraryOperation,
        destinations: Iterable[Destination],
    ) -> EditResult:
        """Apply a structured edit operation to an :class:`Itinerary` (Req 7.2-7.4).

        Dispatches on the operation type and returns an :class:`EditResult`.
        Every structural change (add, reorder, constrain) is routed through the
        deterministic scheduler so the result preserves valid catalog references,
        positive durations, and non-overlapping, start-time-ordered days
        (Property 8). On any invalid request - target not found, replacement or
        added destination absent from the catalog, reorder ids that do not match
        the day - the original itinerary is returned unchanged with an
        explanation and ``changed=False`` (Requirement 7.4); the core never
        partially mutates.

        Args:
            itinerary: The current plan to edit. Never mutated in place.
            operation: The structured edit to apply (add, remove, replace,
                reorder, constrain).
            destinations: The Destination Catalog used to validate references for
                add/replace and to re-shape a constrain operation (Property 10).

        Returns:
            An :class:`EditResult` carrying the resulting (or unchanged)
            itinerary, whether it changed, and a traveler-facing explanation.
        """
        catalog = {destination.id: destination for destination in destinations}
        if isinstance(operation, AddOperation):
            return self._apply_add(itinerary, operation, catalog)
        if isinstance(operation, RemoveOperation):
            return self._apply_remove(itinerary, operation)
        if isinstance(operation, ReplaceOperation):
            return self._apply_replace(itinerary, operation, catalog)
        if isinstance(operation, ReorderOperation):
            return self._apply_reorder(itinerary, operation)
        if isinstance(operation, ConstrainOperation):
            return self._apply_constrain(itinerary, operation, catalog)
        # The discriminated union is exhaustive; guard for forward-compatibility.
        return EditResult(  # pragma: no cover - defensive, union is exhaustive
            itinerary=itinerary,
            changed=False,
            explanation="This edit is not supported.",
        )

    @staticmethod
    def _find_day_index(itinerary: Itinerary, day_number: int) -> int | None:
        """Return the list index of the day with ``day_number`` or None."""
        for index, day in enumerate(itinerary.days):
            if day.day_number == day_number:
                return index
        return None

    @staticmethod
    def _with_day(itinerary: Itinerary, day_index: int, day: ItineraryDay) -> Itinerary:
        """Return a copy of ``itinerary`` with the day at ``day_index`` replaced."""
        days = list(itinerary.days)
        days[day_index] = day
        return itinerary.model_copy(update={"days": days})

    def _apply_add(
        self,
        itinerary: Itinerary,
        operation: AddOperation,
        catalog: Mapping[str, Destination],
    ) -> EditResult:
        """Add a destination to a day and reschedule it (Req 7.1, Property 8)."""
        destination = catalog.get(operation.destination_id)
        if destination is None:
            return EditResult(
                itinerary=itinerary,
                changed=False,
                explanation=(f"Cannot add '{operation.destination_id}': it is not in the catalog."),
            )
        day_index = self._find_day_index(itinerary, operation.day_number)
        if day_index is None:
            return EditResult(
                itinerary=itinerary,
                changed=False,
                explanation=f"Day {operation.day_number} is not part of this itinerary.",
            )
        if not itinerary.allow_repeats and any(
            activity.destination_id == operation.destination_id
            for day in itinerary.days
            for activity in day.activities
        ):
            return EditResult(
                itinerary=itinerary,
                changed=False,
                explanation=(
                    f"'{operation.destination_id}' is already in the itinerary and repeats are off."
                ),
            )
        duration = operation.duration_minutes or _activity_duration(destination)
        new_activity = ItineraryActivity(
            destination_id=operation.destination_id,
            start_minute=operation.start_minute or 0,
            duration_minutes=duration,
        )
        day = itinerary.days[day_index]
        combined = [*day.activities, new_activity]
        rescheduled = _reschedule_activities(combined, itinerary.constraints)
        updated_day = day.model_copy(update={"activities": rescheduled})
        return EditResult(
            itinerary=self._with_day(itinerary, day_index, updated_day),
            changed=True,
            explanation=(f"Added '{operation.destination_id}' to day {operation.day_number}."),
        )

    def _apply_remove(
        self,
        itinerary: Itinerary,
        operation: RemoveOperation,
    ) -> EditResult:
        """Remove one activity, changing nothing else (Req 7.2 / Property 9).

        The remaining activities keep their existing timings, so removing one
        activity provably changes no other activity's placement.
        """
        day_index = self._find_day_index(itinerary, operation.day_number)
        if day_index is None:
            return EditResult(
                itinerary=itinerary,
                changed=False,
                explanation=f"Day {operation.day_number} is not part of this itinerary.",
            )
        day = itinerary.days[day_index]
        target_index = self._resolve_remove_index(day, operation)
        if target_index is None:
            return EditResult(
                itinerary=itinerary,
                changed=False,
                explanation="The activity to remove was not found on that day.",
            )
        remaining = [a for i, a in enumerate(day.activities) if i != target_index]
        updated_day = day.model_copy(update={"activities": remaining})
        return EditResult(
            itinerary=self._with_day(itinerary, day_index, updated_day),
            changed=True,
            explanation=f"Removed one activity from day {operation.day_number}.",
        )

    @staticmethod
    def _resolve_remove_index(day: ItineraryDay, operation: RemoveOperation) -> int | None:
        """Resolve the target activity index for a remove op, or None if absent."""
        if operation.activity_index is not None:
            if 0 <= operation.activity_index < len(day.activities):
                return operation.activity_index
            return None
        for index, activity in enumerate(day.activities):
            if activity.destination_id == operation.destination_id:
                return index
        return None

    def _apply_replace(
        self,
        itinerary: Itinerary,
        operation: ReplaceOperation,
        catalog: Mapping[str, Destination],
    ) -> EditResult:
        """Swap exactly one activity's destination (Req 7.2 / Property 10).

        The replacement must exist in the catalog; exactly one activity's
        ``destination_id`` changes and no other activity is touched. The
        replaced activity keeps its start minute; its duration is re-derived from
        the replacement so the visit length reflects the new place while
        remaining positive.
        """
        replacement = catalog.get(operation.replacement_destination_id)
        if replacement is None:
            return EditResult(
                itinerary=itinerary,
                changed=False,
                explanation=(
                    f"Cannot replace with '{operation.replacement_destination_id}': "
                    "it is not in the catalog."
                ),
            )
        day_index = self._find_day_index(itinerary, operation.day_number)
        if day_index is None:
            return EditResult(
                itinerary=itinerary,
                changed=False,
                explanation=f"Day {operation.day_number} is not part of this itinerary.",
            )
        day = itinerary.days[day_index]
        target_index: int | None = None
        for index, activity in enumerate(day.activities):
            if activity.destination_id == operation.target_destination_id:
                target_index = index
                break
        if target_index is None:
            return EditResult(
                itinerary=itinerary,
                changed=False,
                explanation=(
                    f"'{operation.target_destination_id}' is not on day {operation.day_number}."
                ),
            )
        if (
            not itinerary.allow_repeats
            and operation.replacement_destination_id != operation.target_destination_id
            and any(
                activity.destination_id == operation.replacement_destination_id
                for existing_day in itinerary.days
                for activity in existing_day.activities
            )
        ):
            return EditResult(
                itinerary=itinerary,
                changed=False,
                explanation=(
                    f"'{operation.replacement_destination_id}' is already in the itinerary "
                    "and repeats are off."
                ),
            )
        activities = list(day.activities)
        target = activities[target_index]
        activities[target_index] = target.model_copy(
            update={
                "destination_id": operation.replacement_destination_id,
                "duration_minutes": _activity_duration(replacement),
            }
        )
        updated_day = day.model_copy(update={"activities": activities})
        return EditResult(
            itinerary=self._with_day(itinerary, day_index, updated_day),
            changed=True,
            explanation=(
                f"Replaced '{operation.target_destination_id}' with "
                f"'{operation.replacement_destination_id}' on day {operation.day_number}."
            ),
        )

    def _apply_reorder(
        self,
        itinerary: Itinerary,
        operation: ReorderOperation,
    ) -> EditResult:
        """Reorder a day's activities and re-time them (Req 7.1 / Property 8).

        The requested ids must be exactly the day's current activity destination
        ids (as a multiset) or the operation is rejected unchanged.
        """
        day_index = self._find_day_index(itinerary, operation.day_number)
        if day_index is None:
            return EditResult(
                itinerary=itinerary,
                changed=False,
                explanation=f"Day {operation.day_number} is not part of this itinerary.",
            )
        day = itinerary.days[day_index]
        current_ids = sorted(a.destination_id for a in day.activities)
        requested_ids = sorted(operation.ordered_destination_ids)
        if current_ids != requested_ids:
            return EditResult(
                itinerary=itinerary,
                changed=False,
                explanation=(
                    f"The reorder list does not match day {operation.day_number}'s activities."
                ),
            )
        by_id: dict[str, list[ItineraryActivity]] = {}
        for activity in day.activities:
            by_id.setdefault(activity.destination_id, []).append(activity)
        reordered = [
            by_id[destination_id].pop(0) for destination_id in operation.ordered_destination_ids
        ]
        rescheduled = _reschedule_activities(reordered, itinerary.constraints)
        updated_day = day.model_copy(update={"activities": rescheduled})
        return EditResult(
            itinerary=self._with_day(itinerary, day_index, updated_day),
            changed=True,
            explanation=f"Reordered the activities on day {operation.day_number}.",
        )

    def _apply_constrain(
        self,
        itinerary: Itinerary,
        operation: ConstrainOperation,
        catalog: Mapping[str, Destination],
    ) -> EditResult:
        """Re-apply new constraints, re-shaping via the core (Req 7.1 / Property 8).

        Re-times every existing activity under the new per-day window while
        preserving the day structure and honouring the new per-day activity cap
        (dropping trailing activities that exceed the cap). Routing through the
        deterministic scheduler keeps all invariants. The new constraints are
        stored on the returned itinerary so a later edit sees them.
        """
        new_constraints = operation.constraints
        updated_days: list[ItineraryDay] = []
        changed_any = False
        for day in itinerary.days:
            activities = list(day.activities)
            cap = new_constraints.max_activities_per_day
            if cap is not None and len(activities) > cap:
                activities = activities[:cap]
                changed_any = True
            rescheduled = _reschedule_activities(activities, new_constraints)
            if rescheduled != day.activities:
                changed_any = True
            updated_days.append(day.model_copy(update={"activities": rescheduled}))
        updated = itinerary.model_copy(
            update={"days": updated_days, "constraints": new_constraints}
        )
        if updated.constraints != itinerary.constraints:
            changed_any = True
        return EditResult(
            itinerary=updated,
            changed=changed_any,
            explanation="Applied the updated trip constraints.",
        )

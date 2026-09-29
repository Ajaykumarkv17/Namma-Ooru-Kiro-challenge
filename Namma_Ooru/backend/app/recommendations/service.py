"""Deterministic recommendation selection core (Requirement 8).

This module has no I/O and no AWS calls. It is the pure, deterministic core that
the recommendation router composes. Given a catalog and a recommendation request
it selects catalog candidates for three modes:

* **interests** (Requirement 8.1): return every Destination whose category or a
  tag matches one of the selected interests.
* **themed journey** (Requirement 8.3): return every Destination that matches the
  explicit criteria for one of the eight named journeys (Spiritual Journey, Hill
  Escape, Coastal Escape, Food Trail, Heritage Journey, Nature Escape,
  Photography Trip, Hidden Gems).
* **surprise me** (Requirement 8.2): deterministically select exactly one
  Destination from the catalog.

Every selection is drawn from the catalog passed in, so Property 11
(recommendation catalog membership, Requirement 8.4) holds by construction: the
core never fabricates a Destination, it only ever returns records already in the
catalog. Any AI narrative (e.g. a Surprise Me rationale) is produced by the
router through the ``AIProvider`` interface and kept in clearly named fields
separate from the source catalog record; the selection itself is deterministic.

The themed-journey vocabulary is defined here explicitly so it is reviewable
(architecture steering) and maps each journey to concrete category/flag/tag
criteria over the controlled vocabulary.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import Enum

from app.catalog.models import Destination
from app.catalog.vocabularies import DestinationCategory

# Type alias for a per-Destination predicate used by themed journeys.
_JourneyPredicate = Callable[[Destination], bool]


class ThemedJourney(str, Enum):
    """The eight named themed journeys (Requirement 8.3).

    Values are lower-kebab-case slugs so they are stable in API requests and
    URLs; ``label`` returns the display name written in the requirements.
    """

    SPIRITUAL_JOURNEY = "spiritual-journey"
    HILL_ESCAPE = "hill-escape"
    COASTAL_ESCAPE = "coastal-escape"
    FOOD_TRAIL = "food-trail"
    HERITAGE_JOURNEY = "heritage-journey"
    NATURE_ESCAPE = "nature-escape"
    PHOTOGRAPHY_TRIP = "photography-trip"
    HIDDEN_GEMS = "hidden-gems"

    @property
    def label(self) -> str:
        """Human-readable journey label as written in the requirements."""
        return _JOURNEY_LABELS[self]


_JOURNEY_LABELS: dict[ThemedJourney, str] = {
    ThemedJourney.SPIRITUAL_JOURNEY: "Spiritual Journey",
    ThemedJourney.HILL_ESCAPE: "Hill Escape",
    ThemedJourney.COASTAL_ESCAPE: "Coastal Escape",
    ThemedJourney.FOOD_TRAIL: "Food Trail",
    ThemedJourney.HERITAGE_JOURNEY: "Heritage Journey",
    ThemedJourney.NATURE_ESCAPE: "Nature Escape",
    ThemedJourney.PHOTOGRAPHY_TRIP: "Photography Trip",
    ThemedJourney.HIDDEN_GEMS: "Hidden Gems",
}


def _spiritual(destination: Destination) -> bool:
    return destination.category is DestinationCategory.TEMPLES


def _hill(destination: Destination) -> bool:
    return destination.category in {DestinationCategory.HILLS, DestinationCategory.WATERFALLS}


def _coastal(destination: Destination) -> bool:
    return destination.category is DestinationCategory.BEACHES


def _food(destination: Destination) -> bool:
    return destination.category is DestinationCategory.FOOD


def _heritage(destination: Destination) -> bool:
    return (
        destination.category is DestinationCategory.HERITAGE
        or destination.is_heritage
        or destination.is_unesco
    )


def _nature(destination: Destination) -> bool:
    return destination.nature_related or destination.category in {
        DestinationCategory.NATURE,
        DestinationCategory.WILDLIFE,
        DestinationCategory.WATERFALLS,
        DestinationCategory.HILLS,
    }


def _photography(destination: Destination) -> bool:
    return destination.category is DestinationCategory.PHOTOGRAPHY


def _hidden_gems(destination: Destination) -> bool:
    return destination.is_hidden_gem or destination.category is DestinationCategory.HIDDEN_GEMS


# Explicit, reviewable mapping of each themed journey to its selection predicate
# over the controlled vocabulary (Requirement 8.3).
_JOURNEY_PREDICATES: dict[ThemedJourney, _JourneyPredicate] = {
    ThemedJourney.SPIRITUAL_JOURNEY: _spiritual,
    ThemedJourney.HILL_ESCAPE: _hill,
    ThemedJourney.COASTAL_ESCAPE: _coastal,
    ThemedJourney.FOOD_TRAIL: _food,
    ThemedJourney.HERITAGE_JOURNEY: _heritage,
    ThemedJourney.NATURE_ESCAPE: _nature,
    ThemedJourney.PHOTOGRAPHY_TRIP: _photography,
    ThemedJourney.HIDDEN_GEMS: _hidden_gems,
}

# Human-readable interest words -> category, so an interest that names a category
# (e.g. "temple", "beach") matches destinations of that category even when the
# destination does not carry a literal matching tag. Kept explicit and small so
# interest matching stays deterministic and reviewable.
_INTEREST_CATEGORY_KEYWORDS: dict[str, DestinationCategory] = {
    "temple": DestinationCategory.TEMPLES,
    "temples": DestinationCategory.TEMPLES,
    "spiritual": DestinationCategory.TEMPLES,
    "heritage": DestinationCategory.HERITAGE,
    "history": DestinationCategory.HERITAGE,
    "historical": DestinationCategory.HERITAGE,
    "beach": DestinationCategory.BEACHES,
    "beaches": DestinationCategory.BEACHES,
    "coastal": DestinationCategory.BEACHES,
    "hill": DestinationCategory.HILLS,
    "hills": DestinationCategory.HILLS,
    "waterfall": DestinationCategory.WATERFALLS,
    "waterfalls": DestinationCategory.WATERFALLS,
    "nature": DestinationCategory.NATURE,
    "wildlife": DestinationCategory.WILDLIFE,
    "food": DestinationCategory.FOOD,
    "culture": DestinationCategory.CULTURE,
    "cultural": DestinationCategory.CULTURE,
    "adventure": DestinationCategory.ADVENTURE,
    "photography": DestinationCategory.PHOTOGRAPHY,
    "hidden": DestinationCategory.HIDDEN_GEMS,
}


@dataclass(frozen=True)
class SurpriseSelection:
    """A single deterministically-selected Destination for Surprise Me.

    ``destination`` is the source catalog record. ``suggested_duration_minutes``
    is the record's own recommended duration when known (never fabricated); the
    router pairs this with an AI-generated rationale kept in a separate field so
    generated prose is never conflated with source facts (Requirement 8.2).
    """

    destination: Destination
    suggested_duration_minutes: int | None


def _matches_interest(destination: Destination, interest: str) -> bool:
    """Return True when a Destination matches a single normalized interest.

    An interest matches when it names the Destination's category (via the
    keyword map) or equals one of the Destination's tags (case-insensitive).
    """
    normalized = interest.strip().casefold()
    if not normalized:
        return False
    mapped_category = _INTEREST_CATEGORY_KEYWORDS.get(normalized)
    if mapped_category is not None and destination.category is mapped_category:
        return True
    if normalized == destination.category.value:
        return True
    return any(normalized == tag.casefold() for tag in destination.tags)


def recommend_by_interests(
    destinations: Iterable[Destination], interests: Sequence[str]
) -> list[Destination]:
    """Return catalog records whose category or a tag matches any interest.

    Order-preserving and side-effect free (Requirement 8.1). A Destination is
    included when it matches at least one of the selected interests (OR across
    interests). Empty or whitespace-only interests impose no match and are
    ignored; if no usable interest remains the result is empty.
    """
    usable = [i for i in interests if i and i.strip()]
    if not usable:
        return []
    return [d for d in destinations if any(_matches_interest(d, i) for i in usable)]


def recommend_by_journey(
    destinations: Iterable[Destination], journey: ThemedJourney
) -> list[Destination]:
    """Return catalog records matching a themed journey (Requirement 8.3).

    Order-preserving and side-effect free. Selection uses the explicit
    per-journey predicate defined in ``_JOURNEY_PREDICATES``.
    """
    predicate = _JOURNEY_PREDICATES[journey]
    return [d for d in destinations if predicate(d)]


def surprise_me(
    destinations: Sequence[Destination], *, seed: int | None = None
) -> SurpriseSelection | None:
    """Deterministically select exactly one catalog Destination (Requirement 8.2).

    Returns ``None`` when the catalog is empty. Selection is deterministic for a
    given catalog and ``seed``: the index is ``seed % len(catalog)`` (defaulting
    to the first record when no seed is given), so the same inputs always yield
    the same Destination and the result is always a catalog member.
    """
    if not destinations:
        return None
    index = 0 if seed is None else seed % len(destinations)
    chosen = destinations[index]
    return SurpriseSelection(
        destination=chosen,
        suggested_duration_minutes=chosen.recommended_duration_minutes,
    )


class RecommendationService:
    """Deterministic recommendation core composing the three selection modes.

    Pure and side-effect free so the whole recommendation flow is demoable and
    testable without AWS (architecture steering). Every method returns records
    drawn from the catalog passed in, guaranteeing catalog membership
    (Requirement 8.4 / Property 11) without any AI involvement.
    """

    def by_interests(
        self, destinations: Iterable[Destination], interests: Sequence[str]
    ) -> list[Destination]:
        """Return catalog records matching the selected interests (Requirement 8.1)."""
        return recommend_by_interests(destinations, interests)

    def by_journey(
        self, destinations: Iterable[Destination], journey: ThemedJourney
    ) -> list[Destination]:
        """Return catalog records matching a themed journey (Requirement 8.3)."""
        return recommend_by_journey(destinations, journey)

    def surprise(
        self, destinations: Sequence[Destination], *, seed: int | None = None
    ) -> SurpriseSelection | None:
        """Deterministically select one catalog Destination (Requirement 8.2)."""
        return surprise_me(destinations, seed=seed)

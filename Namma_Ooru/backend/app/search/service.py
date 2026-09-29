"""Deterministic search services: FilterService and keyword/tag fallback.

This module has no I/O and no AWS calls. It contains two pure, deterministic
cores that the search router composes:

* ``FilterService`` is the design-named deterministic filter core
  (design: ``FilterService.apply``). It is a thin, injectable wrapper over the
  pure ``app.catalog.filters.apply_filters`` function so the router has an
  importable service object while the underlying logic stays a free function
  that Properties 1-3 (intersection soundness, removal preservation,
  monotonicity) exercise directly. It never re-implements filter logic.

* ``SearchService`` turns a structured ``SearchIntent`` into ``SearchFilters``
  and, when the AI Provider is unavailable, performs deterministic keyword and
  tag matching over the catalog instead (Requirement 4.3). Both paths end in
  ``FilterService.apply`` so filtering behavior is identical regardless of how
  the filters were derived.

Keeping these pure keeps the search endpoint demoable and testable without live
AWS (architecture steering) and keeps the deterministic core property-testable.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from app.catalog.filters import apply_filters
from app.catalog.models import Destination, SearchFilters
from app.catalog.vocabularies import (
    CATEGORY_SLUGS,
    DISTRICT_SLUGS,
    DestinationCategory,
    TamilNaduDistrict,
)
from app.models import SearchIntent

# Human-readable category words -> category slug, used to recognize a category
# from free-text intent (e.g. "temple" -> "temples"). Kept small and explicit so
# mapping stays deterministic and reviewable; unknown words simply map to no
# category rather than guessing.
_CATEGORY_KEYWORDS: dict[str, DestinationCategory] = {
    "temple": DestinationCategory.TEMPLES,
    "temples": DestinationCategory.TEMPLES,
    "heritage": DestinationCategory.HERITAGE,
    "beach": DestinationCategory.BEACHES,
    "beaches": DestinationCategory.BEACHES,
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


class FilterService:
    """Deterministic filter core used by the search and catalog features.

    ``apply`` is the design's named entry point (Properties 1-3). It delegates to
    the pure, order-preserving ``apply_filters`` free function so the map,
    catalog, and search features share one implementation of filter semantics.
    """

    def apply(
        self, destinations: Iterable[Destination], filters: SearchFilters
    ) -> list[Destination]:
        """Return the catalog subset satisfying every active filter, order-preserved."""
        return apply_filters(destinations, filters)


def _tokenize(text: str) -> list[str]:
    """Split query text into lowercase alphanumeric tokens.

    Punctuation is treated as a separator so words like "temples," or
    "food-trail" tokenize cleanly. Purely deterministic and side-effect free.
    """
    tokens: list[str] = []
    current: list[str] = []
    for char in text.casefold():
        if char.isalnum():
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def _category_from_slug(slug: str) -> DestinationCategory | None:
    return DestinationCategory(slug) if slug in CATEGORY_SLUGS else None


def _district_from_slug(slug: str) -> TamilNaduDistrict | None:
    return TamilNaduDistrict(slug) if slug in DISTRICT_SLUGS else None


def intent_to_filters(intent: SearchIntent) -> SearchFilters:
    """Map a structured ``SearchIntent`` to deterministic ``SearchFilters``.

    Only recognized, controlled-vocabulary values become filters; free-text
    intent fields that do not map to a known city/district/category impose no
    constraint (fail-soft), so an intent the model could not fully classify
    still yields a usable, non-empty result set. Interests become tags so they
    AND-intersect against destination tags.

    * ``location`` is treated as a city constraint (case-insensitive match is
      handled by the filter core) and, when it is also a known district slug, as
      a district constraint.
    * ``category`` maps to a category slug when it names a known category.
    * ``interests`` become lowercased tags; any interest that names a category is
      also promoted to the category filter when no explicit category was given.
    """
    city: str | None = None
    district: TamilNaduDistrict | None = None
    category: DestinationCategory | None = None
    tags: list[str] = []

    if intent.location:
        location = intent.location.strip()
        if location:
            slug = location.casefold().replace(" ", "-")
            district = _district_from_slug(slug)
            # Location always narrows by city name; the filter core matches city
            # case-insensitively so a display name or slug both work.
            city = location

    if intent.category:
        category = _category_from_slug(intent.category.strip().casefold())
        if category is None:
            category = _CATEGORY_KEYWORDS.get(intent.category.strip().casefold())

    for interest in intent.interests:
        normalized = interest.strip().casefold()
        if not normalized:
            continue
        interest_category = _CATEGORY_KEYWORDS.get(normalized)
        if interest_category is not None:
            # An interest that names a category informs the category filter
            # rather than becoming a restrictive tag (tags AND-intersect and
            # would otherwise exclude records that lack a literal matching tag).
            if category is None:
                category = interest_category
            continue
        tags.append(normalized)

    # De-duplicate tags while preserving first-seen order.
    seen: set[str] = set()
    unique_tags: list[str] = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)

    return SearchFilters(city=city, district=district, category=category, tags=unique_tags)


def keyword_filters_from_query(query: str, catalog: Sequence[Destination]) -> SearchFilters:
    """Derive ``SearchFilters`` from raw query text without any AI (Requirement 4.3).

    Deterministic keyword and tag matching for the AI-unavailable fallback path:

    * A query token that equals a known category word sets the category filter.
    * A query token that equals a known district slug sets the district filter.
    * A query token that equals a catalog city name (case-insensitive) sets the
      city filter.
    * Query tokens that match tags actually present in the catalog become tag
      filters (AND-intersected by the filter core).

    Only vocabulary-backed or catalog-backed tokens become constraints, so a
    query full of stop words yields an empty ``SearchFilters`` (the whole catalog)
    rather than an over-constrained empty result.
    """
    tokens = _tokenize(query)
    token_set = set(tokens)

    category: DestinationCategory | None = None
    district: TamilNaduDistrict | None = None
    city: str | None = None

    known_cities = {d.city.casefold(): d.city for d in catalog}
    known_tags = {tag.casefold() for d in catalog for tag in d.tags}

    for token in tokens:
        if category is None and token in _CATEGORY_KEYWORDS:
            category = _CATEGORY_KEYWORDS[token]
        if district is None and token in DISTRICT_SLUGS:
            district = TamilNaduDistrict(token)
        if city is None and token in known_cities:
            city = known_cities[token]

    matched_tags = sorted(token_set & known_tags)

    return SearchFilters(city=city, district=district, category=category, tags=matched_tags)


class SearchService:
    """Deterministic search core composing intent mapping and filtering.

    The router calls ``filters_from_intent`` on the AI-happy path and
    ``fallback_filters`` when the AI Provider is unavailable; both return a
    ``SearchFilters`` that the router applies through ``FilterService.apply``.
    Pure and side-effect free so the whole search flow is demoable/testable
    without AWS (architecture steering).
    """

    def __init__(self, filter_service: FilterService | None = None) -> None:
        self._filters = filter_service or FilterService()

    def filters_from_intent(self, intent: SearchIntent) -> SearchFilters:
        """Map structured AI intent to deterministic filters."""
        return intent_to_filters(intent)

    def fallback_filters(self, query: str, catalog: Sequence[Destination]) -> SearchFilters:
        """Derive filters by deterministic keyword/tag matching (Requirement 4.3)."""
        return keyword_filters_from_query(query, catalog)

    def apply(
        self, destinations: Iterable[Destination], filters: SearchFilters
    ) -> list[Destination]:
        """Filter destinations through the shared deterministic filter core."""
        return self._filters.apply(destinations, filters)

"""Pure, deterministic Destination filtering.

This module has no I/O and no AWS calls. Given a catalog and a set of
``SearchFilters`` it returns the subset of Destinations that satisfy *every*
active filter (an unset filter imposes no constraint). Because it is pure and
order-preserving it is the deterministic core that both the repository's
``list`` method and the later ``FilterService`` (task 4.1) build on, and it is
the target of Properties 1-3:

* Property 1 (intersection soundness): every returned Destination satisfies
  every active filter.
* Property 2 (removal preservation): dropping one filter cannot exclude a
  Destination that still satisfies the remaining filters.
* Property 3 (monotonicity): adding a filter never grows the result set.

Tag matching is AND-intersection and case-insensitive; city matching is
case-insensitive so a city slug or display name both work.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from app.catalog.models import Destination, SearchFilters


def _matches(destination: Destination, filters: SearchFilters) -> bool:
    """Return True when ``destination`` satisfies every active filter."""
    if filters.city is not None and destination.city.casefold() != filters.city.casefold():
        return False
    if filters.district is not None and destination.district != filters.district:
        return False
    if filters.category is not None and destination.category != filters.category:
        return False
    if (
        filters.family_friendly is not None
        and destination.family_friendly != filters.family_friendly
    ):
        return False
    if filters.hidden_gems is not None and destination.is_hidden_gem != filters.hidden_gems:
        return False
    if filters.tags:
        available = {tag.casefold() for tag in destination.tags}
        if not all(tag.casefold() in available for tag in filters.tags):
            return False
    return True


def apply_filters(destinations: Iterable[Destination], filters: SearchFilters) -> list[Destination]:
    """Return the catalog subset satisfying every active filter, order-preserved.

    An empty ``SearchFilters`` returns every Destination (in input order). The
    function never mutates its inputs and is fully deterministic for a given
    catalog and filter set.
    """
    return [d for d in destinations if _matches(d, filters)]


def active_filter_count(filters: SearchFilters) -> int:
    """Count how many constraints ``filters`` imposes (for diagnostics/tests)."""
    count = 0
    for value in (
        filters.city,
        filters.district,
        filters.category,
        filters.family_friendly,
        filters.hidden_gems,
    ):
        if value is not None:
            count += 1
    count += len(filters.tags)
    return count


def matches(destination: Destination, filters: SearchFilters) -> bool:
    """Public wrapper around the per-record predicate (used by other services)."""
    return _matches(destination, filters)


def unique_cities(destinations: Sequence[Destination]) -> list[str]:
    """Return the distinct city names in first-seen order (for discovery)."""
    seen: set[str] = set()
    ordered: list[str] = []
    for destination in destinations:
        key = destination.city.casefold()
        if key not in seen:
            seen.add(key)
            ordered.append(destination.city)
    return ordered

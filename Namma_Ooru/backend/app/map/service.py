"""Pure, deterministic map-marker shaping (Requirement 9.1, 9.2).

This module has no I/O and no AWS calls. Given a catalog and a set of
``MapFilters`` it returns the ``MapMarker`` list for every Destination that

* satisfies *every* active map filter, and
* has verified coordinates (``Destination.has_verified_coordinates``).

Filtering delegates to the shared deterministic core (``apply_filters``) via
``MapFilters.to_search_filters`` so the map never re-implements filter logic.
Being pure and order-preserving makes this the target of Property 12 (map marker
filter soundness): every marker references a Destination satisfying every active
filter and having verified coordinates.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.catalog.filters import apply_filters
from app.catalog.models import Destination
from app.map.models import MapFilters, MapMarker


def to_marker(destination: Destination) -> MapMarker:
    """Shape a Destination with verified coordinates into a ``MapMarker``.

    The caller is responsible for only passing destinations that have verified
    coordinates; ``latitude``/``longitude`` are asserted non-null here so the
    non-nullable marker fields hold and a programming error surfaces loudly
    rather than emitting a malformed marker.
    """
    if destination.latitude is None or destination.longitude is None:  # pragma: no cover - guard
        raise ValueError(
            f"Destination '{destination.id}' has no verified coordinates and cannot be a marker."
        )
    return MapMarker(
        id=destination.id,
        name=destination.name,
        latitude=destination.latitude,
        longitude=destination.longitude,
        category=destination.category,
        city=destination.city,
        district=destination.district,
        description=destination.description,
        image_reference=destination.image_reference,
        is_hidden_gem=destination.is_hidden_gem,
    )


def build_markers(destinations: Iterable[Destination], filters: MapFilters) -> list[MapMarker]:
    """Return markers for every filter-matching destination with coordinates.

    Order-preserving and side-effect free. First the shared filter core narrows
    the catalog to records satisfying every active map filter, then records
    without verified coordinates are dropped, then each survivor is shaped into
    a ``MapMarker``.
    """
    matching = apply_filters(destinations, filters.to_search_filters())
    return [to_marker(d) for d in matching if d.has_verified_coordinates()]


class MapMarkerService:
    """Deterministic marker service used by the map router.

    Thin wrapper over the pure ``build_markers`` function so the router has an
    injectable, importable service object while the underlying logic stays a
    free function that Property 12 can exercise directly.
    """

    def markers(self, destinations: Iterable[Destination], filters: MapFilters) -> list[MapMarker]:
        """Return the filtered, coordinate-verified markers for ``destinations``."""
        return build_markers(destinations, filters)

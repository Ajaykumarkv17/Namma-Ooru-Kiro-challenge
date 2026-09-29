"""Map HTTP endpoint backing the interactive Tamil Nadu map (Requirement 9).

The route is deliberately thin (Coding/Architecture steering): it binds and
validates ``MapFilters`` at the boundary, asks the repository for the destinations
matching every active filter (reusing the shared deterministic filter core rather
than duplicating it), and delegates marker shaping to the pure ``MapMarkerService``.
Only destinations with verified coordinates become markers (Requirement 9.1).

* ``GET /api/map/markers`` returns ``MapMarker[]`` for every matching Destination
  with verified coordinates, honoring every active map filter (Requirements
  9.1, 9.2).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.catalog.repository import DestinationRepository
from app.dependencies import get_destination_repository, get_map_marker_service
from app.map.models import MapFilters, MapMarker
from app.map.service import MapMarkerService

router = APIRouter(prefix="/api/map", tags=["map"])

RepositoryDep = Annotated[DestinationRepository, Depends(get_destination_repository)]
ServiceDep = Annotated[MapMarkerService, Depends(get_map_marker_service)]
# Bind MapFilters as individual query parameters (repeated ``tags`` supported),
# matching the catalog router's Query() convention.
FiltersDep = Annotated[MapFilters, Query()]


@router.get("/markers", response_model=list[MapMarker])
def list_map_markers(
    filters: FiltersDep,
    repository: RepositoryDep,
    service: ServiceDep,
) -> list[MapMarker]:
    """Return a marker for every filter-matching Destination with coordinates."""
    # The repository applies the active filters through the shared filter core;
    # the service then drops records without verified coordinates and shapes the
    # survivors into markers. Passing an empty ``MapFilters`` returns markers for
    # every coordinate-verified destination.
    matching = repository.list(filters.to_search_filters())
    return service.markers(matching, MapFilters())

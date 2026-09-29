"""Catalog HTTP endpoints backing the discovery, city, and detail pages.

These routes are deliberately thin (Coding/Architecture steering): they bind and
validate input at the boundary, delegate all logic to the injected
``DestinationRepository``, and translate a missing Destination into a domain
error so the central FastAPI exception mapper (``app.errors``) is the sole place
that produces HTTP error responses. No I/O or data shaping lives here.

* ``GET /api/destinations`` filters the catalog with ``SearchFilters`` query
  parameters (Requirement 1.5).
* ``GET /api/destinations/{destination_id}`` returns the Destination detail with
  resolved nearby places (Requirements 2.2, 2.4); an unknown id raises
  ``DestinationNotFoundError`` -> ``404 DESTINATION_NOT_FOUND`` (Requirement 11.3).
* ``GET /api/cities/{city}`` returns the grouped ``CityView`` (Requirement 2.1);
  an unknown or empty city returns an empty ``CityView`` (sections appear only
  when matching records exist), never a 404.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.catalog.models import CityView, Destination, DestinationDetail, SearchFilters
from app.catalog.repository import DestinationRepository
from app.dependencies import get_destination_repository
from app.errors import DestinationNotFoundError

router = APIRouter(prefix="/api", tags=["catalog"])

RepositoryDep = Annotated[DestinationRepository, Depends(get_destination_repository)]
# Bind SearchFilters as query parameters. Query() (rather than Depends()) is used
# so FastAPI treats the model's fields as individual query params; the list-valued
# ``tags`` field is provided as a repeated query parameter (?tags=a&tags=b).
FiltersDep = Annotated[SearchFilters, Query()]


@router.get("/destinations", response_model=list[Destination])
def list_destinations(
    filters: FiltersDep,
    repository: RepositoryDep,
) -> list[Destination]:
    """Return every Destination satisfying the active ``SearchFilters``."""
    return repository.list(filters)


@router.get("/destinations/{destination_id}", response_model=DestinationDetail)
def get_destination(
    destination_id: str,
    repository: RepositoryDep,
) -> DestinationDetail:
    """Return the Destination detail; 404 when the id is unknown."""
    detail = repository.detail(destination_id)
    if detail is None:
        raise DestinationNotFoundError(f"No destination exists with id '{destination_id}'.")
    return detail


@router.get("/cities/{city}", response_model=CityView)
def get_city(
    city: str,
    repository: RepositoryDep,
) -> CityView:
    """Return the grouped city overview; empty CityView for a city with no matches."""
    return repository.city_view(city)

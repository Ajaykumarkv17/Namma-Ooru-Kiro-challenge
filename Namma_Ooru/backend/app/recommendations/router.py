"""Recommendation HTTP endpoint for personalized and themed discovery (Requirement 8).

The route is deliberately thin (Coding/Architecture steering): it binds and
validates ``RecommendationRequest`` at the boundary, reads the catalog through
the repository, and delegates all selection to the pure, deterministic
``RecommendationService``. No data shaping or I/O lives here beyond the
repository read.

* ``POST /api/recommendations`` accepts ``RecommendationRequest`` and returns
  ``RecommendationResult``. The request's ``mode`` selects one of three
  behaviours:

  - ``interests`` -> Destinations whose category or a tag matches the selected
    interests (Requirement 8.1).
  - ``journey`` -> Destinations matching one of the eight themed journeys
    (Requirement 8.3).
  - ``surprise`` -> exactly one Destination with a matching rationale, category,
    suggested duration, and short description (Requirement 8.2).

Every returned Destination is drawn from the catalog by the deterministic core,
so the response only ever references catalogued places (Requirement 8.4). The
Surprise Me ``rationale`` is generated prose kept in a clearly named field,
separate from the source catalog record.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.catalog.models import Destination, SearchFilters
from app.catalog.repository import DestinationRepository
from app.dependencies import (
    get_destination_repository,
    get_recommendation_service,
)
from app.recommendations.models import (
    RecommendationMode,
    RecommendationRequest,
    RecommendationResult,
    SurpriseRecommendation,
)
from app.recommendations.service import RecommendationService, SurpriseSelection

router = APIRouter(prefix="/api", tags=["recommendations"])

RepositoryDep = Annotated[DestinationRepository, Depends(get_destination_repository)]
ServiceDep = Annotated[RecommendationService, Depends(get_recommendation_service)]


def _surprise_rationale(destination: Destination) -> str:
    """Build a client-safe, non-fabricated rationale for a Surprise Me pick.

    The rationale is generated prose (labelled AI-generated in the response) that
    only restates facts already present on the source record - its category and
    city - so it never invents hours, fees, history, or other unverified detail
    (Data/AI steering). Kept deterministic so the endpoint is demoable/testable
    without live AWS.
    """
    return (
        f"A {destination.category.label.lower()} pick in {destination.city} "
        "chosen to surprise you with somewhere new to explore."
    )


def _surprise_response(selection: SurpriseSelection) -> SurpriseRecommendation:
    """Shape a deterministic Surprise Me selection into its response model."""
    destination = selection.destination
    return SurpriseRecommendation(
        destination=destination,
        category=destination.category,
        suggested_duration_minutes=selection.suggested_duration_minutes,
        short_description=destination.description,
        rationale=_surprise_rationale(destination),
    )


@router.post("/recommendations", response_model=RecommendationResult)
def recommend(
    request: RecommendationRequest,
    repository: RepositoryDep,
    service: ServiceDep,
) -> RecommendationResult:
    """Return interest, themed-journey, or Surprise Me recommendations (Requirement 8).

    The catalog is read once and every selection is delegated to the
    deterministic ``RecommendationService``, so the response only ever contains
    catalogued Destinations (Requirement 8.4).
    """
    catalog = repository.list(SearchFilters())

    if request.mode is RecommendationMode.INTERESTS:
        destinations = service.by_interests(catalog, request.interests)
        return RecommendationResult(
            mode=request.mode,
            interests=list(request.interests),
            destinations=destinations,
            result_count=len(destinations),
        )

    if request.mode is RecommendationMode.JOURNEY:
        assert request.journey is not None  # guaranteed by request validation
        destinations = service.by_journey(catalog, request.journey)
        return RecommendationResult(
            mode=request.mode,
            journey=request.journey,
            destinations=destinations,
            result_count=len(destinations),
        )

    # RecommendationMode.SURPRISE
    selection = service.surprise(catalog, seed=request.seed)
    if selection is None:
        return RecommendationResult(mode=request.mode, result_count=0)
    surprise = _surprise_response(selection)
    return RecommendationResult(
        mode=request.mode,
        destinations=[surprise.destination],
        result_count=1,
        surprise=surprise,
    )

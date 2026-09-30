"""Validated itinerary generation and conversational edit HTTP endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.ai import AIProvider, validate_itinerary_candidates
from app.catalog.models import SearchFilters
from app.catalog.repository import DestinationRepository
from app.dependencies import get_ai_provider, get_destination_repository, get_itinerary_service
from app.errors import NotFoundError
from app.itinerary.models import (
    EditUnavailable,
    Itinerary,
    ItineraryEditRequest,
    ItineraryEditSuccess,
    ItineraryRequest,
)
from app.itinerary.service import ItineraryService

router = APIRouter(prefix="/api/itineraries", tags=["itineraries"])

AiProviderDep = Annotated[AIProvider, Depends(get_ai_provider)]
RepositoryDep = Annotated[DestinationRepository, Depends(get_destination_repository)]
ServiceDep = Annotated[ItineraryService, Depends(get_itinerary_service)]

# The local demo is intentionally stateless; this bounded in-process store lets a
# generated itinerary be edited by id without letting AI own the itinerary structure.
_itineraries: dict[UUID, Itinerary] = {}


@router.post("", response_model=Itinerary)
def create_itinerary(
    request: ItineraryRequest,
    ai_provider: AiProviderDep,
    repository: RepositoryDep,
    service: ServiceDep,
) -> Itinerary:
    """Generate a scheduled itinerary from catalog-only AI candidate selection."""
    catalog = repository.list(SearchFilters())
    allowed_ids = {destination.id for destination in catalog}
    selected_ids = validate_itinerary_candidates(
        ai_provider.select_itinerary_candidates(
            request.destination_context, [destination.id for destination in catalog]
        ),
        allowed_ids,
    )
    selected = [destination for destination in catalog if destination.id in set(selected_ids)]
    # Preserve the AI ordering only as candidate preference; the deterministic
    # service performs all actual scoring, ordering, durations, and scheduling.
    selected.sort(key=lambda destination: selected_ids.index(destination.id))
    itinerary = service.generate(
        selected,
        destination_context=request.destination_context,
        day_count=request.day_count,
        constraints=request.constraints,
        allow_repeats=request.allow_repeats,
    )
    _itineraries[itinerary.id] = itinerary
    return itinerary


@router.post("/{itinerary_id}/edits", response_model=ItineraryEditSuccess | EditUnavailable)
def edit_itinerary(
    itinerary_id: UUID,
    request: ItineraryEditRequest,
    ai_provider: AiProviderDep,
    repository: RepositoryDep,
    service: ServiceDep,
) -> ItineraryEditSuccess | EditUnavailable:
    """Parse an edit, then apply it exclusively through ``ItineraryService``."""
    itinerary = _itineraries.get(itinerary_id)
    if itinerary is None:
        raise NotFoundError("The requested itinerary was not found.")
    operation = ai_provider.parse_itinerary_edit(request.request, itinerary)
    result = service.apply_operation(
        itinerary,
        operation,
        repository.list(SearchFilters()),
    )
    if not result.changed:
        return EditUnavailable(itinerary=result.itinerary, explanation=result.explanation)
    _itineraries[itinerary_id] = result.itinerary
    return ItineraryEditSuccess(
        itinerary=result.itinerary,
        explanation=result.explanation,
        operation=operation,
    )

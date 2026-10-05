"""Validated itinerary generation and conversational edit HTTP endpoints."""

from __future__ import annotations

import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.ai import AIProvider, validate_itinerary_candidates
from app.catalog.models import Destination, SearchFilters
from app.catalog.repository import DestinationRepository
from app.catalog.vocabularies import TamilNaduDistrict
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


def _location_candidates(context: str, catalog: list[Destination]) -> list[Destination] | None:
    """Apply an explicit city or district named in context as a hard constraint.

    A named location must never degrade to an unrelated catalog entry. ``None``
    means no known location was named; an empty list means a known district was
    named but this catalog has no matching records.
    """
    normalized = re.sub(r"[^a-z0-9]+", " ", context.casefold()).strip()
    known_cities = {destination.city.casefold() for destination in catalog}
    named_cities = [
        city for city in known_cities if re.search(rf"\b{re.escape(city)}\b", normalized)
    ]
    if named_cities:
        return [
            destination for destination in catalog if destination.city.casefold() in named_cities
        ]

    named_districts = [
        district
        for district in TamilNaduDistrict
        if re.search(rf"\b{re.escape(district.value.replace('-', ' '))}\b", normalized)
    ]
    if named_districts:
        return [destination for destination in catalog if destination.district in named_districts]
    return None


@router.post("", response_model=Itinerary)
def create_itinerary(
    request: ItineraryRequest,
    ai_provider: AiProviderDep,
    repository: RepositoryDep,
    service: ServiceDep,
) -> Itinerary:
    """Generate a scheduled itinerary from location-safe catalog candidates."""
    catalog = repository.list(SearchFilters())
    location_limited = _location_candidates(request.destination_context, catalog)
    candidates = catalog if location_limited is None else location_limited
    if not candidates:
        itinerary = service.generate(
            [],
            destination_context=request.destination_context,
            day_count=request.day_count,
            constraints=request.constraints,
            allow_repeats=request.allow_repeats,
        ).model_copy(
            update={
                "no_data_reason": (
                    "No destination data is available for the location in this trip request. "
                    "No places from another location were added."
                )
            }
        )
        _itineraries[itinerary.id] = itinerary
        return itinerary

    allowed_ids = {destination.id for destination in candidates}
    selected_ids = validate_itinerary_candidates(
        ai_provider.select_itinerary_candidates(
            request.destination_context, [destination.id for destination in candidates]
        ),
        allowed_ids,
    )
    selected = [destination for destination in candidates if destination.id in set(selected_ids)]
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

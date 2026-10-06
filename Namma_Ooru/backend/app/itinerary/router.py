"""Validated itinerary generation and conversational edit HTTP endpoints."""

from __future__ import annotations

import math
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

# A single multi-day trip anchored on one city needs more candidates than that
# city alone usually offers, or later days come back empty. When a city is named
# we therefore widen the pool to nearby places within this radius (km), ranked so
# the named city's own places always lead. The named location is never dropped or
# replaced — nearby places are only appended — so the location-safety guarantee
# (a named place never degrades to an unrelated entry) still holds.
_NEARBY_RADIUS_KM = 120.0

# The local demo is intentionally stateless; this bounded in-process store lets a
# generated itinerary be edited by id without letting AI own the itinerary structure.
_itineraries: dict[UUID, Itinerary] = {}


def _haversine_km(a: Destination, b: Destination) -> float:
    """Great-circle distance (km) between two destinations, or inf if unplaceable."""
    if not a.has_verified_coordinates() or not b.has_verified_coordinates():
        return math.inf
    assert a.latitude is not None and a.longitude is not None
    assert b.latitude is not None and b.longitude is not None
    radius_km = 6371.0
    lat1, lon1 = math.radians(a.latitude), math.radians(a.longitude)
    lat2, lon2 = math.radians(b.latitude), math.radians(b.longitude)
    d_lat, d_lon = lat2 - lat1, lon2 - lon1
    h = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    return 2 * radius_km * math.asin(min(1.0, math.sqrt(h)))


def _expand_with_nearby(
    anchors: list[Destination], catalog: list[Destination]
) -> list[Destination]:
    """Append places near the anchor set so multi-day trips have enough candidates.

    ``anchors`` are the places explicitly matched by the named city/district and
    always come first (location safety). Catalog places within
    :data:`_NEARBY_RADIUS_KM` of any anchor are appended in ascending distance
    order; places sharing an anchor's district are also appended (so a named city
    with no coordinates still broadens to its district). Anchors are never dropped
    or reordered; nearby places only extend the pool for the deterministic core to
    draw from.
    """
    anchor_ids = {d.id for d in anchors}
    anchor_districts = {d.district for d in anchors}
    scored: list[tuple[float, int, Destination]] = []
    for index, destination in enumerate(catalog):
        if destination.id in anchor_ids:
            continue
        nearest = min((_haversine_km(destination, a) for a in anchors), default=math.inf)
        in_district = destination.district in anchor_districts
        if nearest <= _NEARBY_RADIUS_KM or in_district:
            # District matches with no coordinates sort after measured distances.
            sort_key = nearest if nearest != math.inf else _NEARBY_RADIUS_KM + 1
            scored.append((sort_key, index, destination))
    scored.sort(key=lambda item: (item[0], item[1]))
    return anchors + [destination for _, _, destination in scored]


def _location_candidates(context: str, catalog: list[Destination]) -> list[Destination] | None:
    """Apply an explicit city or district named in context as a hard constraint.

    A named location must never degrade to an unrelated catalog entry. ``None``
    means no known location was named; an empty list means a known district was
    named but this catalog has no matching records. When a location IS matched,
    the pool is widened with nearby places (same/adjacent area) so a multi-day
    trip can fill every day — the named places still lead the list.
    """
    normalized = re.sub(r"[^a-z0-9]+", " ", context.casefold()).strip()
    known_cities = {destination.city.casefold() for destination in catalog}
    named_cities = [
        city for city in known_cities if re.search(rf"\b{re.escape(city)}\b", normalized)
    ]
    if named_cities:
        anchors = [
            destination for destination in catalog if destination.city.casefold() in named_cities
        ]
        return _expand_with_nearby(anchors, catalog)

    named_districts = [
        district
        for district in TamilNaduDistrict
        if re.search(rf"\b{re.escape(district.value.replace('-', ' '))}\b", normalized)
    ]
    if named_districts:
        anchors = [
            destination for destination in catalog if destination.district in named_districts
        ]
        return _expand_with_nearby(anchors, catalog) if anchors else []
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

    # Balance activities across the requested days when the traveler set no cap,
    # so a multi-day trip spreads evenly instead of packing the first day and
    # leaving later days empty. Honour an explicit cap unchanged (traveler intent
    # wins). The deterministic ItineraryService still owns all scheduling.
    constraints = request.constraints
    if constraints.max_activities_per_day is None and request.day_count > 1 and selected:
        balanced_cap = max(2, math.ceil(len(selected) / request.day_count))
        constraints = constraints.model_copy(update={"max_activities_per_day": balanced_cap})

    itinerary = service.generate(
        selected,
        destination_context=request.destination_context,
        day_count=request.day_count,
        constraints=constraints,
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

"""Search HTTP endpoint backing natural-language destination search (Requirement 4).

The route is deliberately thin (Coding/Architecture steering): it binds and
validates ``TravelQueryRequest`` at the boundary, asks the ``AIProvider`` to
extract structured intent, maps that intent to deterministic ``SearchFilters``,
and applies them through the shared filter core. When the AI Provider is
unavailable it falls back to deterministic keyword and tag matching and marks the
fallback in the response so the frontend can identify it (Requirement 4.3). No
data shaping or I/O lives here beyond the repository read.

* ``POST /api/search`` accepts ``TravelQueryRequest`` and returns ``SearchResult``
  with the AI-derived intent, the deterministic filters, the matching catalog
  records, and a fallback indicator kept in clearly separated fields.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai import AIProvider
from app.catalog.models import SearchFilters
from app.catalog.repository import DestinationRepository
from app.dependencies import (
    get_ai_provider,
    get_destination_repository,
    get_search_service,
)
from app.errors import DependencyUnavailableError
from app.models import SearchIntent, TravelQueryRequest
from app.search.models import SearchResult
from app.search.service import SearchService

router = APIRouter(prefix="/api", tags=["search"])

AiProviderDep = Annotated[AIProvider, Depends(get_ai_provider)]
RepositoryDep = Annotated[DestinationRepository, Depends(get_destination_repository)]
ServiceDep = Annotated[SearchService, Depends(get_search_service)]

_FALLBACK_REASON = (
    "AI interpretation is temporarily unavailable; showing keyword and tag matches instead."
)


@router.post("/search", response_model=SearchResult)
def search_destinations(
    request: TravelQueryRequest,
    ai_provider: AiProviderDep,
    repository: RepositoryDep,
    service: ServiceDep,
) -> SearchResult:
    """Return structured destination results for a natural-language Travel Query.

    Happy path: the AI Provider extracts structured intent (Requirement 4.1),
    the service maps it to deterministic filters, and the repository returns the
    matching records (Requirement 4.2). If the AI Provider is unavailable the
    handler falls back to deterministic keyword/tag matching over the catalog and
    sets ``used_fallback`` so the frontend can surface it (Requirement 4.3).
    """
    catalog = repository.list(SearchFilters())

    used_fallback = False
    fallback_reason: str | None = None
    try:
        intent = ai_provider.extract_search_intent(request.query)
        filters = service.filters_from_intent(intent)
    except DependencyUnavailableError:
        # Fail soft on the optional AI enrichment (coding steering): interpret the
        # query deterministically and flag the fallback for the client.
        used_fallback = True
        fallback_reason = _FALLBACK_REASON
        intent = SearchIntent()
        filters = service.fallback_filters(request.query, catalog)

    destinations = service.apply(catalog, filters)

    return SearchResult(
        query=request.query,
        intent=intent,
        filters=filters,
        destinations=destinations,
        result_count=len(destinations),
        used_fallback=used_fallback,
        fallback_reason=fallback_reason,
    )

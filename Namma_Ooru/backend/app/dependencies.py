"""Dependency providers used by FastAPI routers."""

from __future__ import annotations

from functools import lru_cache

from app.ai import AIProvider, LocalMockAIProvider
from app.catalog.repository import DestinationRepository, JsonDestinationRepository
from app.map.service import MapMarkerService


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    """Supply the deterministic local provider until a runtime provider is configured."""
    return LocalMockAIProvider()


@lru_cache(maxsize=1)
def get_destination_repository() -> DestinationRepository:
    """Supply the JSON-backed catalog repository loaded from the shipped dataset."""
    return JsonDestinationRepository()


@lru_cache(maxsize=1)
def get_map_marker_service() -> MapMarkerService:
    """Supply the pure, stateless map-marker service (Requirement 9.1, 9.2)."""
    return MapMarkerService()

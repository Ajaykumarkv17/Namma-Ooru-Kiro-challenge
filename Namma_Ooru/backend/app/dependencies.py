"""Dependency providers used by FastAPI routers."""

from __future__ import annotations

import os
from functools import lru_cache

from app.ai import AIProvider, LocalMockAIProvider, create_bedrock_provider
from app.catalog.repository import DestinationRepository, JsonDestinationRepository
from app.itinerary.service import ItineraryService
from app.map.service import MapMarkerService
from app.recommendations.service import RecommendationService
from app.reviews.repository import InMemoryReviewRepository
from app.reviews.service import ReviewService
from app.search.service import SearchService


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    """Select the local mock or configured Bedrock provider without credentials in code."""
    provider_name = os.getenv("AI_PROVIDER", "mock").strip().casefold()
    if provider_name in {"", "mock"}:
        return LocalMockAIProvider()
    if provider_name == "bedrock":
        return create_bedrock_provider(
            knowledge_base_id=os.getenv("BEDROCK_KB_ID", ""),
            primary_model_id=os.getenv("BEDROCK_PRIMARY_MODEL_ID", ""),
            fallback_model_id=os.getenv("BEDROCK_FALLBACK_MODEL_ID", ""),
            region_name=os.getenv("AWS_REGION") or None,
        )
    return LocalMockAIProvider()


@lru_cache(maxsize=1)
def get_destination_repository() -> DestinationRepository:
    """Supply the JSON-backed catalog repository loaded from the shipped dataset."""
    return JsonDestinationRepository()


@lru_cache(maxsize=1)
def get_map_marker_service() -> MapMarkerService:
    """Supply the pure, stateless map-marker service (Requirement 9.1, 9.2)."""
    return MapMarkerService()


@lru_cache(maxsize=1)
def get_search_service() -> SearchService:
    """Supply the pure, stateless deterministic search service (Requirement 4)."""
    return SearchService()


@lru_cache(maxsize=1)
def get_recommendation_service() -> RecommendationService:
    """Supply the pure, stateless deterministic recommendation service (Requirement 8)."""
    return RecommendationService()


@lru_cache(maxsize=1)
def get_itinerary_service() -> ItineraryService:
    """Supply the pure itinerary scheduling and edit service."""
    return ItineraryService()


@lru_cache(maxsize=1)
def get_review_service() -> ReviewService:
    """Supply the development review service backed by process-local storage."""
    return ReviewService(get_destination_repository(), InMemoryReviewRepository())

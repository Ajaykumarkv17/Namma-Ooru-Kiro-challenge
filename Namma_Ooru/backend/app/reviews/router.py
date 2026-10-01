"""HTTP endpoints for destination review creation and rating aggregates."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.ai import AIProvider
from app.dependencies import get_ai_provider, get_review_service
from app.reviews.models import Review, ReviewAggregate, ReviewCreateRequest
from app.reviews.service import ReviewService

router = APIRouter(prefix="/api/destinations", tags=["reviews"])
ServiceDep = Annotated[ReviewService, Depends(get_review_service)]
AiProviderDep = Annotated[AIProvider, Depends(get_ai_provider)]
MINIMUM_REVIEW_SUMMARY_COUNT = 2


@router.get("/{destination_id}/reviews", response_model=ReviewAggregate)
def get_reviews(
    destination_id: str, service: ServiceDep, ai_provider: AiProviderDep
) -> ReviewAggregate:
    """Return aggregate data plus a clearly separate review-only AI summary when eligible."""
    aggregate = service.get_aggregate(destination_id)
    if aggregate.review_count < MINIMUM_REVIEW_SUMMARY_COUNT:
        return aggregate
    return aggregate.model_copy(
        update={"ai_summary": ai_provider.summarize_reviews(aggregate.reviews)}
    )


@router.post(
    "/{destination_id}/reviews", response_model=Review, status_code=status.HTTP_201_CREATED
)
def create_review(
    destination_id: str,
    request: ReviewCreateRequest,
    service: ServiceDep,
) -> Review:
    """Validate and persist a review against an existing destination."""
    return service.create(destination_id, request)

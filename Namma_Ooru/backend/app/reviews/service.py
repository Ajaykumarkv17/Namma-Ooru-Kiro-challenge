"""Deterministic review validation, persistence orchestration, and aggregation."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.catalog.repository import DestinationRepository
from app.errors import DestinationNotFoundError
from app.reviews.models import Review, ReviewAggregate, ReviewCreateRequest
from app.reviews.repository import ReviewRepository


def calculate_aggregate(destination_id: str, reviews: list[Review]) -> ReviewAggregate:
    """Calculate a stable aggregate from one destination's persisted reviews."""
    ordered = sorted(reviews, key=lambda review: review.created_at, reverse=True)
    distribution = Counter(review.rating for review in reviews)
    review_count = len(reviews)
    average_rating = (
        round(sum(review.rating for review in reviews) / review_count, 2) if review_count else None
    )
    return ReviewAggregate(
        destination_id=destination_id,
        review_count=review_count,
        average_rating=average_rating,
        rating_distribution={rating: distribution[rating] for rating in range(1, 6)},
        reviews=ordered,
    )


class ReviewService:
    """Coordinates catalog validation, review storage, and pure aggregate calculation."""

    def __init__(
        self,
        destination_repository: DestinationRepository,
        review_repository: ReviewRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._destination_repository = destination_repository
        self._review_repository = review_repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory

    def create(self, destination_id: str, request: ReviewCreateRequest) -> Review:
        """Persist a valid review only after confirming its destination exists."""
        if self._destination_repository.get_by_id(destination_id) is None:
            raise DestinationNotFoundError(f"No destination exists with id '{destination_id}'.")
        review = Review(
            id=self._id_factory(),
            destination_id=destination_id,
            rating=request.rating,
            text=request.text or None,
            tags=request.tags,
            created_at=self._clock(),
        )
        return self._review_repository.add(review)

    def get_aggregate(self, destination_id: str) -> ReviewAggregate:
        """Return current aggregate data, rejecting unknown destinations consistently."""
        if self._destination_repository.get_by_id(destination_id) is None:
            raise DestinationNotFoundError(f"No destination exists with id '{destination_id}'.")
        return calculate_aggregate(
            destination_id,
            self._review_repository.list_for_destination(destination_id),
        )

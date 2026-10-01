"""Review persistence boundary and development in-memory implementation."""

from __future__ import annotations

from typing import Protocol

from app.reviews.models import Review


class ReviewRepository(Protocol):
    """Persistence interface a production DynamoDB adapter can implement."""

    def add(self, review: Review) -> Review:
        """Persist one review and return the stored value."""

    def list_for_destination(self, destination_id: str) -> list[Review]:
        """Return every review stored for the given destination."""


class InMemoryReviewRepository:
    """Process-local development repository with no external dependencies."""

    def __init__(self, reviews: list[Review] | None = None) -> None:
        self._reviews = list(reviews or [])

    def add(self, review: Review) -> Review:
        self._reviews.append(review)
        return review

    def list_for_destination(self, destination_id: str) -> list[Review]:
        return [review for review in self._reviews if review.destination_id == destination_id]

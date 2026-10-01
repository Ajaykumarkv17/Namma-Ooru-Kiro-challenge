"""Pydantic contracts for destination reviews and rating aggregates."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from app.catalog.models import DestinationId

ReviewRating = StrictInt


class ReviewCreateRequest(BaseModel):
    """Validated user input for a destination review (Requirements 10.1, 10.2)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    rating: ReviewRating = Field(ge=1, le=5)
    text: str | None = Field(default=None, max_length=2_000)
    tags: list[str] = Field(default_factory=list, max_length=10)


class Review(BaseModel):
    """A persisted visitor review, kept independent from HTTP and storage details."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: UUID = Field(default_factory=uuid4)
    destination_id: DestinationId
    rating: ReviewRating = Field(ge=1, le=5)
    text: str | None = Field(default=None, max_length=2_000)
    tags: list[str] = Field(default_factory=list, max_length=10)
    created_at: datetime


class ReviewSummary(BaseModel):
    """AI-generated themes derived solely from a destination's persisted reviews."""

    model_config = ConfigDict(extra="forbid")

    positives: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    review_count: int = Field(gt=0)


class ReviewAggregate(BaseModel):
    """Deterministic aggregate and newest-first review list for one destination."""

    model_config = ConfigDict(extra="forbid")

    destination_id: DestinationId
    review_count: int = Field(ge=0)
    average_rating: float | None = Field(default=None, ge=1, le=5)
    rating_distribution: dict[int, int]
    reviews: list[Review]
    ai_summary: ReviewSummary | None = None

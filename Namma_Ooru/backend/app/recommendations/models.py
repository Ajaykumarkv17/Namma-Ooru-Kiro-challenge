"""Pydantic contracts for personalized and themed discovery (Requirement 8).

``RecommendationRequest`` is the single validated input for
``POST /api/recommendations``. It expresses one of three mutually-exclusive
modes through its ``mode`` discriminator: ``interests`` (Requirement 8.1),
``journey`` (Requirement 8.3), or ``surprise`` (Requirement 8.2). Input is
validated and constrained at the boundary (Requirement 11.1): the mode is a
closed enum, interests are length-bounded non-empty strings, the journey is one
of the eight named themed journeys, and the optional Surprise Me seed is a
non-negative integer.

``RecommendationResult`` keeps the selection mode, the matching catalog records,
and (for Surprise Me only) a ``SurpriseRecommendation`` in clearly separated
fields. The Surprise Me ``rationale`` is AI-generated prose and is named and
kept apart from the source catalog ``destination`` so generated text is never
conflated with source facts (AI/RAG steering).
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.catalog.models import Destination
from app.catalog.vocabularies import DestinationCategory
from app.recommendations.service import ThemedJourney

Interest = Annotated[str, Field(min_length=1, max_length=100)]


class RecommendationMode(str, Enum):
    """The three recommendation modes served by ``POST /api/recommendations``."""

    INTERESTS = "interests"
    JOURNEY = "journey"
    SURPRISE = "surprise"


class RecommendationRequest(BaseModel):
    """Validated recommendation input across the three modes (Requirement 8).

    Exactly one mode is expressed at a time. ``interests`` is required and
    non-empty for the ``interests`` mode; ``journey`` is required for the
    ``journey`` mode; ``surprise`` mode uses only the optional ``seed``. The
    model validates cross-field consistency so an inconsistent request is
    rejected at the boundary with a structured 400 (Requirement 11.1) rather
    than silently doing nothing.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mode: RecommendationMode
    interests: list[Interest] = Field(default_factory=list)
    journey: ThemedJourney | None = None
    seed: int | None = Field(default=None, ge=0, le=1_000_000)

    def model_post_init(self, __context: object) -> None:
        """Enforce that the fields present match the selected mode."""
        if self.mode is RecommendationMode.INTERESTS:
            usable = [i for i in self.interests if i and i.strip()]
            if not usable:
                raise ValueError("At least one interest is required for interests mode.")
            if self.journey is not None:
                raise ValueError("journey must be omitted for interests mode.")
        elif self.mode is RecommendationMode.JOURNEY:
            if self.journey is None:
                raise ValueError("journey is required for journey mode.")
            if self.interests:
                raise ValueError("interests must be omitted for journey mode.")
        else:  # RecommendationMode.SURPRISE
            if self.interests:
                raise ValueError("interests must be omitted for surprise mode.")
            if self.journey is not None:
                raise ValueError("journey must be omitted for surprise mode.")


class SurpriseRecommendation(BaseModel):
    """A single Surprise Me pick with generated rationale (Requirement 8.2).

    ``destination`` and ``category`` are source catalog facts;
    ``suggested_duration_minutes`` and ``short_description`` come from the record
    (never fabricated). ``rationale`` is AI-generated prose, named and kept
    separate from the source fields so grounding stays auditable.
    """

    model_config = ConfigDict(extra="forbid")

    destination: Destination
    category: DestinationCategory
    suggested_duration_minutes: int | None = None
    short_description: str
    rationale: str
    rationale_is_ai_generated: bool = True


class RecommendationResult(BaseModel):
    """Structured recommendation response (Requirements 8.1, 8.2, 8.3).

    ``mode`` echoes the request mode; ``journey`` is set for journey mode.
    ``destinations`` holds the matching catalog records for interests/journey
    modes. ``surprise`` holds the single pick for surprise mode. Every returned
    Destination is a catalog member (Requirement 8.4 / Property 11).
    """

    model_config = ConfigDict(extra="forbid")

    mode: RecommendationMode
    journey: ThemedJourney | None = None
    interests: list[str] = Field(default_factory=list)
    destinations: list[Destination] = Field(default_factory=list)
    result_count: int = 0
    surprise: SurpriseRecommendation | None = None

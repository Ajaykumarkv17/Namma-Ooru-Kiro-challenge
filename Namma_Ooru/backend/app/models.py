"""Pydantic API contracts shared by the backend foundation."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

NonEmptyText = Annotated[str, Field(min_length=1, max_length=2_000)]


class TravelQueryRequest(BaseModel):
    """Validated natural-language destination search input."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: NonEmptyText


class RetrievalFilters(BaseModel):
    """Optional metadata constraints applied during knowledge retrieval."""

    model_config = ConfigDict(extra="forbid")

    city: str | None = Field(default=None, min_length=1, max_length=100)
    district: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, min_length=1, max_length=100)


class ChatRequest(BaseModel):
    """Validated chatbot input before retrieval or prompt construction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: NonEmptyText
    filters: RetrievalFilters = Field(default_factory=RetrievalFilters)


class SearchIntent(BaseModel):
    """Structured interpretation of a travel query."""

    model_config = ConfigDict(extra="forbid")

    location: str | None = None
    duration_days: int | None = Field(default=None, ge=1, le=14)
    category: str | None = None
    interests: list[str] = Field(default_factory=list)
    travel_style: str | None = None
    budget: str | None = None
    group_context: str | None = None


class RetrievedSource(BaseModel):
    """A source returned independently from AI-generated answer text."""

    model_config = ConfigDict(extra="forbid")

    destination_id: str
    name: str
    url: HttpUrl


class GroundedAnswer(BaseModel):
    """Generated answer and its auditable retrieved source references."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    sources: list[RetrievedSource] = Field(default_factory=list)
    unavailable: bool = False

"""Pydantic models for natural-language search (Requirement 4).

``SearchResult`` is the response contract for ``POST /api/search``. It keeps the
AI-derived interpretation of the query (``intent``), the deterministic filters
those were mapped to (``filters``), and the retrieved catalog records
(``destinations``) in clearly separated fields so AI-generated interpretation is
never conflated with source catalog data (AI/RAG steering).

``used_fallback`` signals that the AI Provider was unavailable and the backend
answered with deterministic keyword and tag matching instead (Requirement 4.3);
``fallback_reason`` is a short, client-safe explanation the frontend can surface.
No stack traces or internal detail ever reach this field.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.catalog.models import Destination, SearchFilters
from app.models import SearchIntent


class SearchResult(BaseModel):
    """Structured natural-language search response (Requirements 4.1, 4.2, 4.3).

    Fields are deliberately separated so the frontend can render the active
    filters, badge AI-derived interpretation distinctly from catalog records,
    and show a fallback notice when ``used_fallback`` is true.
    """

    model_config = ConfigDict(extra="forbid")

    query: str
    intent: SearchIntent
    filters: SearchFilters
    destinations: list[Destination] = Field(default_factory=list)
    result_count: int = 0
    used_fallback: bool = False
    fallback_reason: str | None = None

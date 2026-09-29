"""Pydantic models for the interactive map feature (Requirement 9).

``MapFilters`` is the boundary input for ``GET /api/map/markers``. It intentionally
mirrors the subset of ``SearchFilters`` that the map exposes (city and category
plus the same boolean/tag refinements) so the deterministic filter core can be
reused rather than duplicated. ``MapMarker`` is the response record: it carries
only the minimal fields the frontend needs to plot a marker and render a preview
with a navigation action to the Destination page (Requirement 9.3).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.catalog.models import SearchFilters
from app.catalog.vocabularies import DestinationCategory, TamilNaduDistrict

NonEmptyText = Annotated[str, Field(min_length=1, max_length=100)]


class MapFilters(BaseModel):
    """Active map filters bound from query parameters (Requirement 9.2).

    Every field is optional; an absent field imposes no constraint, so empty
    ``MapFilters`` match every destination that has verified coordinates. The
    field set is the map-relevant subset of ``SearchFilters`` (city, category,
    district, tags, family_friendly, hidden_gems); ``to_search_filters`` adapts
    it to the catalog filter core so filter logic is never duplicated.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    city: str | None = Field(default=None, min_length=1, max_length=100)
    district: TamilNaduDistrict | None = None
    category: DestinationCategory | None = None
    tags: list[NonEmptyText] = Field(default_factory=list)
    family_friendly: bool | None = None
    hidden_gems: bool | None = None

    def to_search_filters(self) -> SearchFilters:
        """Adapt to a ``SearchFilters`` so ``apply_filters`` can be reused."""
        return SearchFilters(
            city=self.city,
            district=self.district,
            category=self.category,
            tags=list(self.tags),
            family_friendly=self.family_friendly,
            hidden_gems=self.hidden_gems,
        )


class MapMarker(BaseModel):
    """A single plottable destination marker plus minimal preview fields.

    Emitted only for destinations with verified coordinates (Requirement 9.1),
    so ``latitude`` and ``longitude`` are non-nullable here even though they are
    nullable on ``Destination``. The preview fields (``category``, ``city``,
    ``description``, ``image_reference``) let the frontend render a marker
    preview and a link to ``/destinations/{id}`` without a second request.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    latitude: float
    longitude: float
    category: DestinationCategory
    city: str
    district: TamilNaduDistrict
    description: str
    image_reference: str | None = None
    is_hidden_gem: bool = False

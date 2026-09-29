"""Pydantic models for the source-attributed Destination Catalog.

Factual fields that a source has not verified are nullable so the pipeline can
persist ``null`` (Requirement 3.6) and the UI can render "Information unavailable"
rather than a fabricated value. Structural fields (id, name, city, district,
region, category, description) are required.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.catalog.vocabularies import (
    DestinationCategory,
    TamilNaduDistrict,
    is_valid_latitude,
    is_valid_longitude,
)

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

DestinationId = Annotated[
    str,
    Field(min_length=1, max_length=120, pattern=SLUG_PATTERN.pattern),
]
NonEmptyText = Annotated[str, Field(min_length=1, max_length=100)]
Description = Annotated[str, Field(min_length=1, max_length=5_000)]


class SourceAttribution(BaseModel):
    """Provenance for a factual Destination record (Requirement 3.5).

    ``notes`` records conflict resolution and the authoritative-source preference
    when sources disagree.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: NonEmptyText
    type: NonEmptyText
    url: HttpUrl
    retrieved_on: date
    notes: str | None = Field(default=None, max_length=2_000)


class PopularityMetadata(BaseModel):
    """Discovery ranking signals kept separate from source-verified facts."""

    model_config = ConfigDict(extra="forbid")

    popularity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rating_average: float | None = Field(default=None, ge=1.0, le=5.0)
    rating_count: int = Field(default=0, ge=0)


class Destination(BaseModel):
    """A catalogued Tamil Nadu place (Requirement 3.2).

    Nullable factual fields hold ``null`` until a source verifies them
    (Requirement 3.6). District and category are constrained to the controlled
    vocabularies so unknown values cannot enter the catalog.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Identity and classification (required, structural).
    id: DestinationId
    name: NonEmptyText
    alternate_names: list[NonEmptyText] = Field(default_factory=list)
    city: NonEmptyText
    district: TamilNaduDistrict
    region: NonEmptyText
    category: DestinationCategory
    subcategory: str | None = Field(default=None, max_length=100)
    description: Description

    # Nullable factual narrative fields.
    detailed_description: str | None = Field(default=None, max_length=10_000)
    historical_significance: str | None = Field(default=None, max_length=10_000)
    cultural_significance: str | None = Field(default=None, max_length=10_000)

    # Coordinates: present only when a source verifies them (Requirement 3.6).
    latitude: float | None = None
    longitude: float | None = None

    # Nullable dynamic and contact fields.
    address: str | None = Field(default=None, max_length=1_000)
    best_time_to_visit: str | None = Field(default=None, max_length=500)
    recommended_duration_minutes: int | None = Field(default=None, ge=1, le=1_440)
    opening_hours: str | None = Field(default=None, max_length=1_000)
    entry_fee: str | None = Field(default=None, max_length=1_000)
    official_website: HttpUrl | None = None

    # Source attribution (Requirement 3.5). At least one reference is required by
    # the validator; the model allows an empty list only so validation can emit a
    # precise "missing source" issue rather than a raw Pydantic error.
    source_urls: list[HttpUrl] = Field(default_factory=list)
    sources: list[SourceAttribution] = Field(default_factory=list)

    # Discovery data.
    image_reference: str | None = Field(default=None, max_length=500)
    tags: list[NonEmptyText] = Field(default_factory=list)
    nearby_place_ids: list[DestinationId] = Field(default_factory=list)
    is_hidden_gem: bool = False
    is_heritage: bool = False
    is_unesco: bool = False
    family_friendly: bool = False
    nature_related: bool = False
    adventure_related: bool = False
    popularity: PopularityMetadata = Field(default_factory=PopularityMetadata)

    # Human-review flags (Requirement 3.5). Set when sources conflict about a
    # fact; the validator surfaces these as review warnings.
    has_source_conflict: bool = False
    needs_review: bool = False

    def has_verified_coordinates(self) -> bool:
        """Return True when both coordinates exist and fall within Tamil Nadu."""
        if self.latitude is None or self.longitude is None:
            return False
        return is_valid_latitude(self.latitude) and is_valid_longitude(self.longitude)


class SearchFilters(BaseModel):
    """Deterministic catalog filter selection (design: SearchFilters).

    Every field is optional. Absent fields (``None`` / empty ``tags``) impose no
    constraint, so an empty ``SearchFilters`` matches the whole catalog. ``tags``
    are AND-intersected: a Destination must carry every requested tag. Keeping
    this model I/O-free lets the pure filter function underpin Properties 1-3
    (intersection soundness, removal preservation, monotonicity).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    city: str | None = Field(default=None, min_length=1, max_length=100)
    district: TamilNaduDistrict | None = None
    category: DestinationCategory | None = None
    tags: list[NonEmptyText] = Field(default_factory=list)
    family_friendly: bool | None = None
    hidden_gems: bool | None = None


class CitySection(BaseModel):
    """A titled, grouped slice of a city's destinations (Requirement 2.1)."""

    model_config = ConfigDict(extra="forbid")

    key: str
    title: str
    destinations: list[Destination] = Field(default_factory=list)


class DestinationDetail(BaseModel):
    """A Destination plus its resolved nearby places (Requirements 2.2, 2.4).

    ``destination`` is the source-verified record; ``nearby`` holds the real
    Destination records that ``destination.nearby_place_ids`` point at, in the
    order the ids are listed. Ids that do not resolve to a catalogued place are
    silently dropped so the detail page's nearby navigation only ever links to
    destinations that exist (Requirement 2.4).
    """

    model_config = ConfigDict(extra="forbid")

    destination: Destination
    nearby: list[Destination] = Field(default_factory=list)


class CityView(BaseModel):
    """A city overview plus its grouped Destination sections (Requirement 2.1).

    ``sections`` only ever contains groups that have at least one matching
    record, so the UI can render an empty state when ``destination_count`` is 0
    instead of showing empty section headers.
    """

    model_config = ConfigDict(extra="forbid")

    city: str
    district: TamilNaduDistrict | None = None
    region: str | None = None
    destination_count: int = 0
    sections: list[CitySection] = Field(default_factory=list)

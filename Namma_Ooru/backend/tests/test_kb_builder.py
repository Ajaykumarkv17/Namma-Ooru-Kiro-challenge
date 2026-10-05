"""Example-based tests for the Knowledge Base document builder (task 8.1).

These verify the RAG-flow guarantees from design "Knowledge Base documents" and
the Data/AI-RAG steering: one document + one sidecar per Destination, correct
filterable metadata keys/values (aligned with the S3 Vectors index), source URLs
present in the narrative, no fabrication of unknown fields, and fail-closed
behavior on invalid datasets. Document/metadata shaping is deterministic, so
these are example-based unit tests, not property-based tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.catalog.kb_builder import (
    FILTERABLE_METADATA_KEYS,
    METADATA_SUFFIX,
    UNAVAILABLE,
    DatasetInvalidError,
    build_document,
    build_kb,
    build_metadata,
    travel_types,
)
from app.catalog.models import Destination


def _valid_record() -> dict[str, Any]:
    return {
        "id": "madurai-meenakshi-amman-temple",
        "name": "Meenakshi Amman Temple",
        "alternate_names": ["Meenakshi Sundareswarar Temple"],
        "city": "Madurai",
        "district": "madurai",
        "region": "South Tamil Nadu",
        "category": "temples",
        "subcategory": "Dravidian temple complex",
        "description": "A historic Dravidian temple in the heart of Madurai.",
        "detailed_description": None,
        "historical_significance": None,
        "cultural_significance": None,
        "latitude": 9.9195,
        "longitude": 78.1193,
        "recommended_duration_minutes": 120,
        "source_urls": ["https://www.tamilnadutourism.tn.gov.in/destinations/madurai"],
        "sources": [
            {
                "name": "Tamil Nadu Tourism",
                "type": "government-tourism",
                "url": "https://www.tamilnadutourism.tn.gov.in/destinations/madurai",
                "retrieved_on": "2024-01-15",
            }
        ],
        "tags": ["temple", "heritage", "madurai"],
        "is_heritage": True,
        "family_friendly": True,
    }


def _destination(record: dict[str, Any] | None = None) -> Destination:
    return Destination.model_validate(record or _valid_record())


def _attributes(destination: Destination) -> dict[str, Any]:
    envelope = build_metadata(destination)
    attributes = envelope["metadataAttributes"]
    assert isinstance(attributes, dict)
    return attributes


def test_build_emits_document_and_sidecar_per_destination(tmp_path: Path) -> None:
    record_a = _valid_record()
    record_b = _valid_record()
    record_b["id"] = "chennai-marina-beach"
    record_b["name"] = "Marina Beach"
    record_b["alternate_names"] = []
    record_b["city"] = "Chennai"
    record_b["district"] = "chennai"
    record_b["category"] = "beaches"

    result = build_kb([record_a, record_b], tmp_path)

    assert result.destination_count == 2
    for dest_id in ("madurai-meenakshi-amman-temple", "chennai-marina-beach"):
        document = tmp_path / f"{dest_id}.md"
        sidecar = tmp_path / f"{dest_id}.md{METADATA_SUFFIX}"
        assert document.exists()
        assert sidecar.exists()
    assert sorted(result.document_paths) == sorted(tmp_path.glob("*.md"))
    assert len(result.metadata_paths) == 2


def test_metadata_keys_and_values_match_index_schema(tmp_path: Path) -> None:
    build_kb([_valid_record()], tmp_path)
    sidecar = tmp_path / f"madurai-meenakshi-amman-temple.md{METADATA_SUFFIX}"

    attributes = json.loads(sidecar.read_text(encoding="utf-8"))["metadataAttributes"]

    # Every filterable index key is present, except travel_type which is
    # conditional (omitted when empty — see the empty-travel_type regression
    # test). The sample record has family_friendly=True, so it is present here.
    for key in FILTERABLE_METADATA_KEYS:
        if key == "travel_type":
            continue
        assert key in attributes, f"missing filterable metadata key: {key}"
    assert attributes["district"] == "madurai"
    assert attributes["city"] == "Madurai"
    assert attributes["category"] == "temples"
    assert attributes["region"] == "South Tamil Nadu"
    assert attributes["heritage"] is True
    assert attributes["unesco"] is False
    assert "family" in attributes["travel_type"]
    assert "heritage" in attributes["travel_type"]
    # subcategory is emitted as extra document context.
    assert attributes["subcategory"] == "Dravidian temple complex"


def test_travel_types_are_derived_and_sorted() -> None:
    record = _valid_record()
    record["family_friendly"] = True
    record["nature_related"] = True
    record["adventure_related"] = True
    record["is_hidden_gem"] = True
    record["is_unesco"] = True

    types = travel_types(_destination(record))

    assert types == sorted(types)
    assert set(types) == {
        "family",
        "nature",
        "adventure",
        "hidden-gem",
        "heritage",
        "unesco",
    }


def test_document_contains_source_urls_and_attribution() -> None:
    document = build_document(_destination())

    assert "https://www.tamilnadutourism.tn.gov.in/destinations/madurai" in document
    assert "Tamil Nadu Tourism" in document
    assert "2024-01-15" in document
    assert "## Sources" in document


def test_document_does_not_fabricate_unknown_fields() -> None:
    record = _valid_record()
    record["opening_hours"] = None
    record["entry_fee"] = None
    record["best_time_to_visit"] = None
    record["address"] = None
    record["detailed_description"] = None
    record["historical_significance"] = None

    document = build_document(_destination(record))

    # Unknown visitor fields render as the unavailable marker, never invented.
    assert f"**Opening hours:** {UNAVAILABLE}" in document
    assert f"**Entry fee:** {UNAVAILABLE}" in document
    assert f"**Best time to visit:** {UNAVAILABLE}" in document
    # Optional narrative sections for unverified fields are omitted entirely.
    assert "## Historical Significance" not in document
    assert "## Detailed Description" not in document


def test_document_omits_coordinates_when_unverified() -> None:
    record = _valid_record()
    record["latitude"] = None
    record["longitude"] = None

    document = build_document(_destination(record))

    assert f"**Coordinates:** {UNAVAILABLE}" in document


def test_build_fails_closed_on_invalid_dataset(tmp_path: Path) -> None:
    invalid = _valid_record()
    invalid["district"] = "delhi"  # not a Tamil Nadu district

    with pytest.raises(DatasetInvalidError):
        build_kb([invalid], tmp_path)

    # Fail closed: no document or sidecar was written.
    assert list(tmp_path.iterdir()) == []


def test_build_fails_closed_on_missing_source(tmp_path: Path) -> None:
    invalid = _valid_record()
    invalid["source_urls"] = []
    invalid["sources"] = []

    with pytest.raises(DatasetInvalidError):
        build_kb([invalid], tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_metadata_heritage_true_for_unesco_only() -> None:
    record = _valid_record()
    record["is_heritage"] = False
    record["is_unesco"] = True

    attributes = _attributes(_destination(record))

    assert attributes["heritage"] is True
    assert attributes["unesco"] is True


def test_metadata_subcategory_unavailable_when_null() -> None:
    record = _valid_record()
    record["subcategory"] = None

    attributes = _attributes(_destination(record))

    assert attributes["subcategory"] == UNAVAILABLE


def test_metadata_omits_travel_type_when_empty() -> None:
    """Regression: Bedrock KB rejects an empty-array metadata attribute.

    A Destination with no derived travel-style tags must NOT emit
    ``"travel_type": []`` — Bedrock treats the empty list as an invalid
    attribute and ignores the whole document on sync. The key must be absent.
    """
    record = _valid_record()
    # Clear every flag that derives a travel_type tag.
    record["family_friendly"] = False
    record["nature_related"] = False
    record["adventure_related"] = False
    record["is_hidden_gem"] = False
    record["is_heritage"] = False
    record["is_unesco"] = False

    destination = _destination(record)
    assert travel_types(destination) == []

    attributes = _attributes(destination)
    assert "travel_type" not in attributes
    # No attribute value may be an empty list (Bedrock-invalid).
    assert [] not in attributes.values()

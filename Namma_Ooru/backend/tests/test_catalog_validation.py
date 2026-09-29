"""Example-based tests for the Destination Catalog validator (task 2.1).

These cover the rejection cases required by Requirement 3.4, the human-review
flag for conflicting sources (3.5), the null-for-unverified rule (3.6), and the
controlled-vocabulary completeness (3.2, 3.3). Dataset schema validation uses
schema/unit tests, not property-based tests, per the testing steering.
"""

from __future__ import annotations

import copy
from typing import Any

from app.catalog.models import Destination
from app.catalog.validation import (
    IssueCode,
    Severity,
    validate_dataset,
)
from app.catalog.vocabularies import (
    CATEGORY_SLUGS,
    DISTRICT_SLUGS,
    DestinationCategory,
    TamilNaduDistrict,
)


def _valid_record() -> dict[str, Any]:
    return {
        "id": "madurai-meenakshi-amman-temple",
        "name": "Meenakshi Amman Temple",
        "alternate_names": ["Meenakshi Sundareswarar Temple"],
        "city": "Madurai",
        "district": "madurai",
        "region": "South Tamil Nadu",
        "category": "temples",
        "description": "A historic Dravidian temple in the heart of Madurai.",
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
                "notes": None,
            }
        ],
        "tags": ["temple", "heritage"],
        "nearby_place_ids": [],
        "is_heritage": True,
        "popularity": {
            "popularity_score": 0.95,
            "rating_average": 4.7,
            "rating_count": 120,
        },
    }


def _codes(report: Any) -> set[IssueCode]:
    return {issue.code for issue in report.issues}


# --- Vocabulary completeness (Requirements 3.2, 3.3) --------------------------


def test_all_thirty_eight_districts_present() -> None:
    assert len(TamilNaduDistrict) == 38
    assert len(DISTRICT_SLUGS) == 38


def test_all_twelve_categories_present() -> None:
    assert len(DestinationCategory) == 12
    assert len(CATEGORY_SLUGS) == 12
    labels = {category.label for category in DestinationCategory}
    assert labels == {
        "Temples",
        "Heritage",
        "Beaches",
        "Hills",
        "Waterfalls",
        "Nature",
        "Wildlife",
        "Food",
        "Culture",
        "Adventure",
        "Photography",
        "Hidden Gems",
    }


# --- Happy path ---------------------------------------------------------------


def test_valid_record_passes_and_parses() -> None:
    report = validate_dataset([_valid_record()])

    assert report.is_valid
    assert report.errors == []
    assert len(report.validated) == 1
    assert isinstance(report.validated[0], Destination)


def test_null_unverified_coordinates_are_accepted() -> None:
    record = _valid_record()
    record["latitude"] = None
    record["longitude"] = None

    report = validate_dataset([record])

    assert report.is_valid
    assert not report.validated[0].has_verified_coordinates()


# --- Requirement 3.4 rejection cases -----------------------------------------


def test_duplicate_identifier_is_rejected() -> None:
    report = validate_dataset([_valid_record(), copy.deepcopy(_valid_record())])

    assert not report.is_valid
    assert IssueCode.DUPLICATE_ID in _codes(report)


def test_invalid_district_is_rejected() -> None:
    record = _valid_record()
    record["district"] = "bengaluru"

    report = validate_dataset([record])

    assert not report.is_valid
    assert IssueCode.INVALID_DISTRICT in _codes(report)


def test_invalid_category_is_rejected() -> None:
    record = _valid_record()
    record["category"] = "shopping"

    report = validate_dataset([record])

    assert not report.is_valid
    assert IssueCode.INVALID_CATEGORY in _codes(report)


def test_out_of_state_coordinates_are_rejected() -> None:
    record = _valid_record()
    record["latitude"] = 28.6
    record["longitude"] = 77.2

    report = validate_dataset([record])

    assert not report.is_valid
    assert IssueCode.INVALID_COORDINATES in _codes(report)


def test_half_specified_coordinates_are_rejected() -> None:
    record = _valid_record()
    record["longitude"] = None

    report = validate_dataset([record])

    assert not report.is_valid
    assert IssueCode.INVALID_COORDINATES in _codes(report)


def test_empty_description_is_rejected() -> None:
    record = _valid_record()
    record["description"] = "   "

    report = validate_dataset([record])

    assert not report.is_valid
    assert IssueCode.EMPTY_DESCRIPTION in _codes(report)


def test_missing_source_reference_is_rejected() -> None:
    record = _valid_record()
    record["sources"] = []
    record["source_urls"] = []

    report = validate_dataset([record])

    assert not report.is_valid
    assert IssueCode.MISSING_SOURCE in _codes(report)


# --- Additional data-steering rejection cases --------------------------------


def test_duplicate_alias_is_rejected() -> None:
    first = _valid_record()
    second = _valid_record()
    second["id"] = "madurai-thirumalai-nayakkar-mahal"
    second["name"] = "Thirumalai Nayakkar Mahal"
    second["category"] = "heritage"
    second["alternate_names"] = ["Meenakshi Sundareswarar Temple"]

    report = validate_dataset([first, second])

    assert not report.is_valid
    assert IssueCode.DUPLICATE_ALIAS in _codes(report)


def test_invalid_rating_is_rejected() -> None:
    record = _valid_record()
    record["popularity"]["rating_average"] = 6.2

    report = validate_dataset([record])

    assert not report.is_valid
    assert IssueCode.INVALID_RATING in _codes(report)


def test_unknown_nearby_relationship_is_rejected() -> None:
    record = _valid_record()
    record["nearby_place_ids"] = ["nonexistent-place"]

    report = validate_dataset([record])

    assert not report.is_valid
    assert IssueCode.INVALID_RELATIONSHIP in _codes(report)


def test_missing_required_field_is_rejected() -> None:
    record = _valid_record()
    del record["city"]

    report = validate_dataset([record])

    assert not report.is_valid
    assert IssueCode.MISSING_FIELD in _codes(report)


# --- Requirement 3.5 human-review flag ---------------------------------------


def test_source_conflict_emits_review_warning_not_error() -> None:
    record = _valid_record()
    record["has_source_conflict"] = True
    record["sources"][0]["notes"] = "TN Tourism preferred over blog on opening hours."

    report = validate_dataset([record])

    assert report.is_valid  # warnings do not fail validation
    conflict_issues = [i for i in report.issues if i.code is IssueCode.SOURCE_CONFLICT]
    assert len(conflict_issues) == 1
    assert conflict_issues[0].severity is Severity.WARNING

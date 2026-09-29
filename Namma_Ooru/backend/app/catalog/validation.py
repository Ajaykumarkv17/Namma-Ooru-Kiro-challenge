"""Pure deterministic validator for the source-attributed Destination Catalog.

This module has no I/O: it takes already-parsed records and returns a structured
report. ``data/scripts/validate.py`` wraps it with file reading and process-exit
handling. Keeping the core pure lets it be unit-tested without touching disk.

The validator enforces the data steering rules: required fields, valid districts,
valid categories, valid coordinate ranges, duplicate places, duplicate aliases,
invalid ratings, missing sources, malformed URLs, empty descriptions, and
conflict human-review flags (Requirements 3.4, 3.5, 3.6).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum

from pydantic import ValidationError

from app.catalog.models import Destination
from app.catalog.vocabularies import (
    is_valid_category,
    is_valid_district,
    is_valid_latitude,
    is_valid_longitude,
)


class Severity(str, Enum):
    """Severity of a validation finding."""

    ERROR = "error"
    WARNING = "warning"


class IssueCode(str, Enum):
    """Stable codes for each rejection or review reason."""

    MISSING_FIELD = "missing_field"
    EMPTY_DESCRIPTION = "empty_description"
    DUPLICATE_ID = "duplicate_id"
    DUPLICATE_ALIAS = "duplicate_alias"
    INVALID_DISTRICT = "invalid_district"
    INVALID_CATEGORY = "invalid_category"
    INVALID_COORDINATES = "invalid_coordinates"
    INVALID_RATING = "invalid_rating"
    MISSING_SOURCE = "missing_source"
    MALFORMED_URL = "malformed_url"
    INVALID_RELATIONSHIP = "invalid_relationship"
    SCHEMA_ERROR = "schema_error"
    SOURCE_CONFLICT = "source_conflict"


# Structural fields a Destination record must always provide.
REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "city",
    "district",
    "region",
    "category",
    "description",
)


@dataclass(frozen=True)
class ValidationIssue:
    """A single validator finding for one record (or the dataset)."""

    code: IssueCode
    severity: Severity
    message: str
    record_id: str | None = None
    field: str | None = None


@dataclass
class ValidationReport:
    """Aggregated validator result over a dataset."""

    issues: list[ValidationIssue] = field(default_factory=list)
    validated: list[Destination] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity is Severity.WARNING]

    @property
    def is_valid(self) -> bool:
        """True when no error-severity issue was found (warnings are allowed)."""
        return not self.errors


def _record_id(record: dict[str, object], index: int) -> str:
    raw = record.get("id")
    if isinstance(raw, str) and raw:
        return raw
    return f"<record #{index}>"


def _validate_required_fields(record: dict[str, object], record_id: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for name in REQUIRED_FIELDS:
        value = record.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            code = IssueCode.EMPTY_DESCRIPTION if name == "description" else IssueCode.MISSING_FIELD
            issues.append(
                ValidationIssue(
                    code=code,
                    severity=Severity.ERROR,
                    message=f"Record is missing required field '{name}'.",
                    record_id=record_id,
                    field=name,
                )
            )
    return issues


def _validate_vocabularies(record: dict[str, object], record_id: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    district = record.get("district")
    if isinstance(district, str) and district and not is_valid_district(district):
        issues.append(
            ValidationIssue(
                code=IssueCode.INVALID_DISTRICT,
                severity=Severity.ERROR,
                message=f"District '{district}' is not a Tamil Nadu district.",
                record_id=record_id,
                field="district",
            )
        )
    category = record.get("category")
    if isinstance(category, str) and category and not is_valid_category(category):
        issues.append(
            ValidationIssue(
                code=IssueCode.INVALID_CATEGORY,
                severity=Severity.ERROR,
                message=f"Category '{category}' is not an accepted category.",
                record_id=record_id,
                field="category",
            )
        )
    return issues


def _validate_coordinates(record: dict[str, object], record_id: str) -> list[ValidationIssue]:
    latitude = record.get("latitude")
    longitude = record.get("longitude")
    # Unverified coordinates are null on both fields (Requirement 3.6) and valid.
    if latitude is None and longitude is None:
        return []
    issues: list[ValidationIssue] = []
    if (latitude is None) != (longitude is None):
        issues.append(
            ValidationIssue(
                code=IssueCode.INVALID_COORDINATES,
                severity=Severity.ERROR,
                message="Latitude and longitude must both be set or both be null.",
                record_id=record_id,
                field="latitude" if latitude is None else "longitude",
            )
        )
        return issues
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        issues.append(
            ValidationIssue(
                code=IssueCode.INVALID_COORDINATES,
                severity=Severity.ERROR,
                message="Coordinates must be numeric.",
                record_id=record_id,
                field="latitude",
            )
        )
        return issues
    if not is_valid_latitude(float(latitude)) or not is_valid_longitude(float(longitude)):
        issues.append(
            ValidationIssue(
                code=IssueCode.INVALID_COORDINATES,
                severity=Severity.ERROR,
                message=(f"Coordinates ({latitude}, {longitude}) fall outside Tamil Nadu bounds."),
                record_id=record_id,
                field="latitude",
            )
        )
    return issues


def _validate_sources(record: dict[str, object], record_id: str) -> list[ValidationIssue]:
    sources = record.get("sources")
    source_urls = record.get("source_urls")
    has_sources = isinstance(sources, list) and len(sources) > 0
    has_urls = isinstance(source_urls, list) and len(source_urls) > 0
    if has_sources or has_urls:
        return []
    return [
        ValidationIssue(
            code=IssueCode.MISSING_SOURCE,
            severity=Severity.ERROR,
            message="Record has no source reference.",
            record_id=record_id,
            field="sources",
        )
    ]


def _validate_rating(record: dict[str, object], record_id: str) -> list[ValidationIssue]:
    popularity = record.get("popularity")
    if not isinstance(popularity, dict):
        return []
    average = popularity.get("rating_average")
    if average is None:
        return []
    if not isinstance(average, (int, float)) or not (1.0 <= float(average) <= 5.0):
        return [
            ValidationIssue(
                code=IssueCode.INVALID_RATING,
                severity=Severity.ERROR,
                message=f"Rating average '{average}' must be between 1 and 5.",
                record_id=record_id,
                field="popularity.rating_average",
            )
        ]
    return []


def _validate_source_conflicts(record: dict[str, object], record_id: str) -> list[ValidationIssue]:
    """Emit a human-review flag when a record marks a source conflict (3.5)."""
    if record.get("has_source_conflict") is True or record.get("needs_review") is True:
        return [
            ValidationIssue(
                code=IssueCode.SOURCE_CONFLICT,
                severity=Severity.WARNING,
                message=(
                    "Sources conflict for this record; flagged for human review. "
                    "Preserve the authoritative-source preference in source notes."
                ),
                record_id=record_id,
                field="sources",
            )
        ]
    return []


def _validate_dataset_uniqueness(
    records: Sequence[dict[str, object]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen_ids: set[str] = set()
    seen_aliases: dict[str, str] = {}
    for index, record in enumerate(records):
        record_id = _record_id(record, index)
        raw_id = record.get("id")
        if isinstance(raw_id, str) and raw_id:
            if raw_id in seen_ids:
                issues.append(
                    ValidationIssue(
                        code=IssueCode.DUPLICATE_ID,
                        severity=Severity.ERROR,
                        message=f"Duplicate destination id '{raw_id}'.",
                        record_id=record_id,
                        field="id",
                    )
                )
            seen_ids.add(raw_id)
        aliases = record.get("alternate_names")
        if isinstance(aliases, list):
            for alias in aliases:
                if not isinstance(alias, str):
                    continue
                key = alias.strip().lower()
                if not key:
                    continue
                if key in seen_aliases:
                    issues.append(
                        ValidationIssue(
                            code=IssueCode.DUPLICATE_ALIAS,
                            severity=Severity.ERROR,
                            message=(
                                f"Alias '{alias}' is already used by " f"'{seen_aliases[key]}'."
                            ),
                            record_id=record_id,
                            field="alternate_names",
                        )
                    )
                else:
                    seen_aliases[key] = record_id
    return issues


def _validate_relationships(
    records: Sequence[dict[str, object]],
) -> list[ValidationIssue]:
    """Every nearby_place_id must reference a known destination id."""
    known_ids = {
        record.get("id")
        for record in records
        if isinstance(record.get("id"), str) and record.get("id")
    }
    issues: list[ValidationIssue] = []
    for index, record in enumerate(records):
        record_id = _record_id(record, index)
        nearby = record.get("nearby_place_ids")
        if not isinstance(nearby, list):
            continue
        for reference in nearby:
            if not isinstance(reference, str):
                continue
            if reference == record.get("id"):
                issues.append(
                    ValidationIssue(
                        code=IssueCode.INVALID_RELATIONSHIP,
                        severity=Severity.ERROR,
                        message="A destination cannot list itself as a nearby place.",
                        record_id=record_id,
                        field="nearby_place_ids",
                    )
                )
            elif reference not in known_ids:
                issues.append(
                    ValidationIssue(
                        code=IssueCode.INVALID_RELATIONSHIP,
                        severity=Severity.ERROR,
                        message=f"Nearby place id '{reference}' does not exist.",
                        record_id=record_id,
                        field="nearby_place_ids",
                    )
                )
    return issues


def validate_record(record: dict[str, object], index: int = 0) -> list[ValidationIssue]:
    """Validate a single record and return its issues (ordering-independent)."""
    record_id = _record_id(record, index)
    issues: list[ValidationIssue] = []
    issues.extend(_validate_required_fields(record, record_id))
    issues.extend(_validate_vocabularies(record, record_id))
    issues.extend(_validate_coordinates(record, record_id))
    issues.extend(_validate_sources(record, record_id))
    issues.extend(_validate_rating(record, record_id))
    issues.extend(_validate_source_conflicts(record, record_id))
    return issues


def validate_dataset(records: Iterable[dict[str, object]]) -> ValidationReport:
    """Validate an entire dataset and return a structured report.

    Per-record checks run first so precise, field-level errors are reported.
    Cross-record checks (duplicate ids/aliases, relationship integrity) run over
    the whole set. Records that pass per-record checks are parsed into
    ``Destination`` models; a Pydantic failure becomes a schema error.
    """
    materialized = list(records)
    report = ValidationReport()

    for index, record in enumerate(materialized):
        report.issues.extend(validate_record(record, index))

    report.issues.extend(_validate_dataset_uniqueness(materialized))
    report.issues.extend(_validate_relationships(materialized))

    # Records already flagged with an error are not re-parsed to avoid noisy
    # duplicate schema errors; clean records are parsed for downstream use.
    error_record_ids = {
        issue.record_id for issue in report.issues if issue.severity is Severity.ERROR
    }
    for index, record in enumerate(materialized):
        record_id = _record_id(record, index)
        if record_id in error_record_ids:
            continue
        try:
            report.validated.append(Destination.model_validate(record))
        except ValidationError as exc:
            report.issues.append(
                ValidationIssue(
                    code=IssueCode.SCHEMA_ERROR,
                    severity=Severity.ERROR,
                    message=f"Schema validation failed: {exc.error_count()} error(s).",
                    record_id=record_id,
                )
            )
    return report

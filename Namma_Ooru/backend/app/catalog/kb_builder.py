"""Data-to-Knowledge-Base document builder (task 8.1, Requirements 3.2, 5.1).

Turns the validated, source-attributed Destination Catalog into the two files the
Bedrock Knowledge Base ingests, per Destination:

* ``<destination-id>.md`` — a grounded narrative document that includes the
  Destination's source URLs so answers can cite provenance.
* ``<destination-id>.md.metadata.json`` — the S3 sidecar metadata document that
  stores the retrieval metadata used by the S3 Vectors index (district, city,
  category, subcategory, region, heritage, unesco, travel_type). The filterable
  keys mirror ``infra/.../constructs/vector_store.py``'s
  ``FILTERABLE_METADATA_KEYS`` so metadata-scoped retrieval works end to end.

Grounding rules (Data / AI-RAG steering):
* Never invent facts. A nullable field that a source has not verified is rendered
  as "Information unavailable" or omitted from the narrative; it is never
  fabricated.
* Source attribution (source URLs, source name/type/retrieval date) is preserved
  in the output so the Knowledge Base answer can be traced back to a source.

Purity and layering (Architecture / Coding steering):
* The document/sidecar rendering functions are pure: given a ``Destination`` they
  return strings / JSON-serializable dicts with no I/O.
* ``build_kb`` is the only function that touches the filesystem, and it makes no
  AWS calls — uploading the emitted files to S3 is a separate concern (the CDK
  data source / deployment step).
* ``build_kb`` fails closed: it runs the dataset validator first and refuses to
  emit any document when the dataset is invalid.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from app.catalog.models import Destination
from app.catalog.validation import validate_dataset

# Rendered when a nullable factual field has not been verified by a source. Kept
# identical to the UI copy (Requirement 2.3) so the grounded narrative and the UI
# agree on how "unknown" reads.
UNAVAILABLE = "Information unavailable"

# The metadata sidecar filename Bedrock expects: "<source-file>.metadata.json".
METADATA_SUFFIX = ".metadata.json"

# Filterable retrieval-metadata keys. These MUST match the S3 Vectors index in
# ``infra/namma_ooru_infra/constructs/vector_store.py`` (FILTERABLE_METADATA_KEYS)
# so a value written here can be used as a retrieval filter. ``subcategory`` is
# emitted in addition to the index keys (task 8.1 scope) for document context.
FILTERABLE_METADATA_KEYS: tuple[str, ...] = (
    "district",
    "city",
    "category",
    "region",
    "heritage",
    "unesco",
    "travel_type",
)


class DatasetInvalidError(ValueError):
    """Raised when ``build_kb`` is asked to build from an invalid dataset.

    The builder fails closed on this error so no Knowledge Base document is ever
    emitted from data that has not passed the validator (design "RAG flow").
    """

    def __init__(self, error_messages: Sequence[str]) -> None:
        self.error_messages = list(error_messages)
        preview = "; ".join(self.error_messages[:5])
        super().__init__(
            f"Dataset failed validation ({len(self.error_messages)} error(s)); "
            f"refusing to build Knowledge Base documents. {preview}"
        )


@dataclass(frozen=True)
class KbBuildResult:
    """Summary of a Knowledge Base build for reporting and tests."""

    document_paths: list[Path]
    metadata_paths: list[Path]

    @property
    def destination_count(self) -> int:
        return len(self.document_paths)


def travel_types(destination: Destination) -> list[str]:
    """Derive the ``travel_type`` retrieval metadata for a Destination.

    Travel type is a small, deterministic set of travel-style tags derived from
    the Destination's discovery flags. It is filterable metadata (it appears in
    the S3 Vectors index), so it must be stable and derived only from verified
    catalog data — never fabricated. Returned sorted for deterministic output.
    """
    types: set[str] = set()
    if destination.family_friendly:
        types.add("family")
    if destination.nature_related:
        types.add("nature")
    if destination.adventure_related:
        types.add("adventure")
    if destination.is_hidden_gem:
        types.add("hidden-gem")
    if destination.is_heritage:
        types.add("heritage")
    if destination.is_unesco:
        types.add("unesco")
    return sorted(types)


def build_metadata(destination: Destination) -> dict[str, object]:
    """Build the S3 sidecar metadata document for one Destination.

    The returned dict is JSON-serializable and wraps the filterable retrieval
    keys under Bedrock's ``metadataAttributes`` envelope. ``subcategory`` is
    included as additional (non-index) context.

    Bedrock Knowledge Base rejects a metadata sidecar whose attribute values are
    not ``String`` / ``Number`` / ``Boolean`` / non-empty ``StringList``. An
    EMPTY list has no element type and is treated as an invalid attribute, which
    makes Bedrock ignore the whole document on sync. ``travel_type`` is derived
    and can legitimately be empty, so it is OMITTED entirely when it has no
    values rather than written as ``[]``. Metadata-filtered retrieval still works
    for documents that do have the key; absence simply means "no travel tags".
    """
    attributes: dict[str, object] = {
        "district": destination.district.value,
        "city": destination.city,
        "category": destination.category.value,
        "region": destination.region,
        "heritage": destination.is_heritage or destination.is_unesco,
        "unesco": destination.is_unesco,
        # Not an index key, but useful document context for downstream tooling.
        "subcategory": (
            destination.subcategory if destination.subcategory is not None else UNAVAILABLE
        ),
    }
    # Omit the StringList key when empty: Bedrock rejects an empty-array value.
    tags = travel_types(destination)
    if tags:
        attributes["travel_type"] = tags
    return {"metadataAttributes": attributes}


def _optional_line(label: str, value: str | None) -> str | None:
    """Render a ``**Label:** value`` line, or ``None`` when the value is unknown.

    An unverified (``None`` / blank) factual field is dropped so it is never
    fabricated; the caller decides whether to show an explicit
    "Information unavailable" instead of omitting it.
    """
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return f"**{label}:** {text}"


def build_document(destination: Destination) -> str:
    """Render the grounded Markdown narrative for one Destination.

    The narrative uses only source-verified catalog data. Nullable factual fields
    that have not been verified are either omitted or shown as
    "Information unavailable" — they are never invented. Source URLs and source
    attribution are always included so the Knowledge Base answer stays traceable.
    """
    d = destination
    lines: list[str] = [f"# {d.name}", ""]

    if d.alternate_names:
        lines.append(f"*Also known as: {', '.join(d.alternate_names)}*")
        lines.append("")

    # Classification block — all values are required/controlled catalog fields.
    lines.append(f"**City:** {d.city}")
    lines.append(f"**District:** {d.district.value}")
    lines.append(f"**Region:** {d.region}")
    lines.append(f"**Category:** {d.category.value}")
    subcategory_line = _optional_line("Subcategory", d.subcategory)
    if subcategory_line:
        lines.append(subcategory_line)
    lines.append("")

    # Description is required and always present.
    lines.append("## Overview")
    lines.append(d.description)
    lines.append("")

    # Optional narrative sections: only rendered when a source has verified them.
    for heading, value in (
        ("Detailed Description", d.detailed_description),
        ("Historical Significance", d.historical_significance),
        ("Cultural Significance", d.cultural_significance),
    ):
        if value is not None and value.strip():
            lines.append(f"## {heading}")
            lines.append(value.strip())
            lines.append("")

    # Visitor information. Unknown fields are shown as "Information unavailable"
    # rather than a fabricated value, matching the UI's null-field behavior.
    lines.append("## Visitor Information")
    visitor_fields: tuple[tuple[str, str | None], ...] = (
        ("Best time to visit", d.best_time_to_visit),
        ("Opening hours", d.opening_hours),
        ("Entry fee", d.entry_fee),
        ("Address", d.address),
    )
    for label, value in visitor_fields:
        rendered = value.strip() if value and value.strip() else UNAVAILABLE
        lines.append(f"**{label}:** {rendered}")
    if d.recommended_duration_minutes is not None:
        lines.append(f"**Recommended duration:** {d.recommended_duration_minutes} minutes")
    else:
        lines.append(f"**Recommended duration:** {UNAVAILABLE}")
    if d.has_verified_coordinates():
        lines.append(f"**Coordinates:** {d.latitude}, {d.longitude}")
    else:
        lines.append(f"**Coordinates:** {UNAVAILABLE}")
    lines.append("")

    if d.tags:
        lines.append(f"**Tags:** {', '.join(d.tags)}")
        lines.append("")

    # Source attribution — always present so answers are traceable to a source.
    lines.append("## Sources")
    if d.official_website is not None:
        lines.append(f"- Official website: {d.official_website}")
    for source in d.sources:
        note = f" — {source.notes}" if source.notes else ""
        lines.append(
            f"- {source.name} ({source.type}, retrieved {source.retrieved_on.isoformat()}): "
            f"{source.url}{note}"
        )
    # Include the raw source URLs so provenance is present even if a URL has no
    # structured attribution entry.
    for url in d.source_urls:
        lines.append(f"- Source URL: {url}")

    return "\n".join(lines).rstrip() + "\n"


def _validate_or_raise(records: Sequence[dict[str, object]]) -> list[Destination]:
    """Run the dataset validator; return validated models or fail closed."""
    report = validate_dataset(records)
    if not report.is_valid:
        raise DatasetInvalidError([issue.message for issue in report.errors])
    return report.validated


def build_kb(
    records: Iterable[dict[str, object]],
    output_dir: Path,
) -> KbBuildResult:
    """Validate ``records`` and emit KB documents + sidecars into ``output_dir``.

    Fails closed: the dataset validator runs first and, on any error-severity
    issue, no file is written (``DatasetInvalidError`` is raised). On success,
    exactly one ``<id>.md`` and one ``<id>.md.metadata.json`` are written per
    Destination. Writing files is the only side effect — no AWS calls are made.
    """
    validated = _validate_or_raise(list(records))

    output_dir.mkdir(parents=True, exist_ok=True)
    document_paths: list[Path] = []
    metadata_paths: list[Path] = []

    for destination in validated:
        document_path = output_dir / f"{destination.id}.md"
        metadata_path = output_dir / f"{destination.id}.md{METADATA_SUFFIX}"

        document_path.write_text(build_document(destination), encoding="utf-8")
        metadata_path.write_text(
            json.dumps(build_metadata(destination), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        document_paths.append(document_path)
        metadata_paths.append(metadata_path)

    return KbBuildResult(document_paths=document_paths, metadata_paths=metadata_paths)

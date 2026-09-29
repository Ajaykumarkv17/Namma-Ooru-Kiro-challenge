#!/usr/bin/env python3
"""Dataset validator CLI for the Namma Ooru Destination Catalog.

Reads one or more JSON dataset files, runs the deterministic validator from
``app.catalog.validation``, prints a human-readable report, and exits non-zero
when any error-severity issue is found (data steering: failure => non-zero exit).

Usage:
    python data/scripts/validate.py data/destinations.json
    python data/scripts/validate.py            # defaults to data/destinations.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Make the backend package importable when this script is run directly, without
# requiring an editable install of the backend.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = _REPO_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.catalog.validation import (  # noqa: E402  (path set up above)
    Severity,
    ValidationReport,
    validate_dataset,
)

DEFAULT_DATASET = Path("data/destinations.json")

EXIT_OK = 0
EXIT_VALIDATION_FAILED = 1
EXIT_USAGE_ERROR = 2


def _load_records(path: Path) -> list[dict[str, Any]]:
    """Load a dataset file as a list of record dicts.

    Accepts either a top-level JSON array or an object with a ``destinations``
    array. Raises ``ValueError`` with a safe message on malformed input.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path}: invalid JSON ({exc.msg} at line {exc.lineno})."
        ) from exc

    if isinstance(raw, dict) and isinstance(raw.get("destinations"), list):
        raw = raw["destinations"]
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected a JSON array of destination records.")
    records: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: record #{index} is not a JSON object.")
        records.append(item)
    return records


def _print_report(report: ValidationReport, dataset_count: int) -> None:
    for issue in report.issues:
        marker = "ERROR" if issue.severity is Severity.ERROR else "WARN "
        location = issue.record_id or "<dataset>"
        field = f" [{issue.field}]" if issue.field else ""
        print(f"{marker} {issue.code.value} ({location}){field}: {issue.message}")

    error_count = len(report.errors)
    warning_count = len(report.warnings)
    print(
        f"\nChecked {dataset_count} record(s): "
        f"{len(report.validated)} valid, {error_count} error(s), {warning_count} warning(s)."
    )


def run(paths: list[Path]) -> int:
    """Validate each dataset path and return the process exit code."""
    all_records: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            print(f"ERROR usage: dataset file not found: {path}", file=sys.stderr)
            return EXIT_USAGE_ERROR
        try:
            all_records.extend(_load_records(path))
        except ValueError as exc:
            print(f"ERROR usage: {exc}", file=sys.stderr)
            return EXIT_USAGE_ERROR

    report = validate_dataset(all_records)
    _print_report(report, len(all_records))
    return EXIT_OK if report.is_valid else EXIT_VALIDATION_FAILED


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Namma Ooru destination dataset."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_DATASET],
        help="Dataset JSON file(s) to validate (default: data/destinations.json).",
    )
    args = parser.parse_args(argv)
    paths = args.paths or [DEFAULT_DATASET]
    return run(paths)


if __name__ == "__main__":
    raise SystemExit(main())

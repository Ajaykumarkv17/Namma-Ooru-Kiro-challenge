#!/usr/bin/env python3
"""Knowledge Base document builder CLI for the Namma Ooru catalog (task 8.1).

Reads the validated, source-attributed Destination dataset and emits, per
Destination, a grounded ``data/kb/<id>.md`` narrative (including source URLs) and
a ``data/kb/<id>.md.metadata.json`` S3 sidecar with the retrieval metadata used by
the S3 Vectors index.

The build is gated by the dataset validator: if validation fails, no document is
written and the process exits non-zero (data steering: fail closed). No AWS call
is made here — uploading the emitted files to S3 is a separate deployment step.

Usage:
    python data/scripts/build_kb.py
    python data/scripts/build_kb.py data/destinations.json --out data/kb
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Make the backend package importable when this script is run directly, without
# requiring an editable install of the backend (mirrors validate.py).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = _REPO_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.catalog.kb_builder import (  # noqa: E402  (path set up above)
    DatasetInvalidError,
    build_kb,
)

DEFAULT_DATASET = Path("data/destinations.json")
DEFAULT_OUTPUT_DIR = Path("data/kb")

EXIT_OK = 0
EXIT_BUILD_FAILED = 1
EXIT_USAGE_ERROR = 2


def _load_records(path: Path) -> list[dict[str, Any]]:
    """Load a dataset file as a list of record dicts (mirrors validate.py)."""
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


def run(dataset_path: Path, output_dir: Path) -> int:
    """Build KB documents from ``dataset_path`` and return the process exit code."""
    if not dataset_path.exists():
        print(f"ERROR usage: dataset file not found: {dataset_path}", file=sys.stderr)
        return EXIT_USAGE_ERROR
    try:
        records = _load_records(dataset_path)
    except ValueError as exc:
        print(f"ERROR usage: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    try:
        result = build_kb(records, output_dir)
    except DatasetInvalidError as exc:
        print(f"ERROR build: {exc}", file=sys.stderr)
        return EXIT_BUILD_FAILED

    print(
        f"Built {result.destination_count} Knowledge Base document(s) into {output_dir} "
        f"({len(result.metadata_paths)} metadata sidecar(s))."
    )
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build Namma Ooru Knowledge Base documents from the dataset."
    )
    parser.add_argument(
        "dataset",
        nargs="?",
        type=Path,
        default=DEFAULT_DATASET,
        help="Dataset JSON file to build from (default: data/destinations.json).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for KB documents (default: data/kb).",
    )
    args = parser.parse_args(argv)
    return run(args.dataset, args.out)


if __name__ == "__main__":
    raise SystemExit(main())

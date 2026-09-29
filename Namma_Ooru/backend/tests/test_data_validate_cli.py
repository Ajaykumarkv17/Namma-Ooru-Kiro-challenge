"""Tests for the data/scripts/validate.py CLI exit-code behavior (task 2.1).

The validator must exit non-zero on failure (data steering) and zero on a clean
dataset. The CLI lives outside the backend package, so it is imported by path.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

_CLI_PATH = Path(__file__).resolve().parents[2] / "data" / "scripts" / "validate.py"


def _load_cli() -> ModuleType:
    spec = importlib.util.spec_from_file_location("nammaooru_validate_cli", _CLI_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _valid_record() -> dict[str, Any]:
    return {
        "id": "chennai-marina-beach",
        "name": "Marina Beach",
        "city": "Chennai",
        "district": "chennai",
        "region": "North Tamil Nadu",
        "category": "beaches",
        "description": "One of the longest urban beaches, along the Bay of Bengal.",
        "latitude": 13.05,
        "longitude": 80.28,
        "source_urls": ["https://www.tamilnadutourism.tn.gov.in/destinations/chennai"],
        "sources": [
            {
                "name": "Tamil Nadu Tourism",
                "type": "government-tourism",
                "url": "https://www.tamilnadutourism.tn.gov.in/destinations/chennai",
                "retrieved_on": "2024-02-01",
            }
        ],
    }


def _write_dataset(path: Path, records: list[dict[str, Any]]) -> Path:
    path.write_text(json.dumps({"destinations": records}), encoding="utf-8")
    return path


def test_cli_exits_zero_on_valid_dataset(tmp_path: Path) -> None:
    cli = _load_cli()
    dataset = _write_dataset(tmp_path / "ok.json", [_valid_record()])

    assert cli.run([dataset]) == cli.EXIT_OK


def test_cli_exits_nonzero_on_invalid_record(tmp_path: Path) -> None:
    cli = _load_cli()
    bad = _valid_record()
    bad["district"] = "delhi"
    dataset = _write_dataset(tmp_path / "bad.json", [bad])

    assert cli.run([dataset]) == cli.EXIT_VALIDATION_FAILED


def test_cli_exits_usage_error_on_missing_file(tmp_path: Path) -> None:
    cli = _load_cli()

    assert cli.run([tmp_path / "does-not-exist.json"]) == cli.EXIT_USAGE_ERROR


def test_cli_exits_usage_error_on_malformed_json(tmp_path: Path) -> None:
    cli = _load_cli()
    dataset = tmp_path / "malformed.json"
    dataset.write_text("{ not valid json", encoding="utf-8")

    assert cli.run([dataset]) == cli.EXIT_USAGE_ERROR


def test_shipped_default_dataset_is_valid() -> None:
    cli = _load_cli()
    default = _CLI_PATH.resolve().parents[1] / "destinations.json"

    assert cli.run([default]) == cli.EXIT_OK

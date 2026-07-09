#!/usr/bin/env python3
"""Validate one committed dataset-onboarding manifest against local reports.

The validator is intentionally metadata-only: it reads the committed manifest
and the dataset's adapter_report.json, checks paths and expected counts/hashes,
and does not inspect raw parquet rows or processed trace JSONL content.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_DATA_ROOT = "C:/pneuma-data"
DEFAULT_REGISTRY_ROOT = Path("docs/data/registry")
SUPPORTED_DATASETS = {
    "swe-gym-openhands-sampled": "openhands-sampled.json",
}

REQUIRED_FIELDS = (
    "manifest_schema_version",
    "dataset_id",
    "dataset_status",
    "registry_status",
    "human_name",
    "data_root_variable",
    "default_observed_data_root",
    "raw_path_relative",
    "processed_path_relative",
    "source_of_truth_report_relative",
    "adapter",
    "schema",
    "source",
    "expected_from_adapter_report",
    "privacy_status",
    "allowed_uses",
    "blocked_uses",
)


class ValidationError(ValueError):
    """Raised for a manifest/report mismatch."""


def _load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ValidationError(f"missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {path}: {exc}") from exc


def _data_root(cli_value: str | None) -> Path:
    value = cli_value or os.environ.get("PNEUMA_DATA_ROOT") or DEFAULT_DATA_ROOT
    return Path(value)


def _manifest_path(dataset: str, registry_root: Path) -> Path:
    name = SUPPORTED_DATASETS.get(dataset)
    if name is None:
        supported = ", ".join(sorted(SUPPORTED_DATASETS))
        raise ValidationError(f"unsupported dataset {dataset!r}; supported: {supported}")
    return registry_root / name


def _require_fields(manifest: dict) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in manifest]
    if missing:
        raise ValidationError(f"manifest missing required fields: {', '.join(missing)}")
    if manifest["manifest_schema_version"] != "0.1.0":
        raise ValidationError(
            "unsupported manifest_schema_version: "
            f"{manifest['manifest_schema_version']!r}"
        )
    if manifest["data_root_variable"] != "PNEUMA_DATA_ROOT":
        raise ValidationError("data_root_variable must be PNEUMA_DATA_ROOT")


def _compare(expected, actual, label: str, errors: list[str]) -> None:
    if expected != actual:
        errors.append(f"{label}: expected {expected!r}, got {actual!r}")


def _compare_block(expected: dict, actual: dict, prefix: str, errors: list[str]) -> None:
    for key, value in expected.items():
        if isinstance(value, dict):
            _compare_block(value, actual.get(key, {}), f"{prefix}.{key}", errors)
        else:
            _compare(value, actual.get(key), f"{prefix}.{key}", errors)


def validate(dataset: str, data_root: Path, registry_root: Path) -> list[str]:
    manifest_file = _manifest_path(dataset, registry_root)
    manifest = _load_json(manifest_file)
    _require_fields(manifest)

    if manifest["dataset_id"] != dataset:
        raise ValidationError(
            f"dataset_id mismatch: manifest has {manifest['dataset_id']!r}, "
            f"requested {dataset!r}"
        )

    raw_path = data_root / manifest["raw_path_relative"]
    processed_path = data_root / manifest["processed_path_relative"]
    report_path = data_root / manifest["source_of_truth_report_relative"]

    errors: list[str] = []
    if not raw_path.is_dir():
        errors.append(f"raw path missing or not a directory: {raw_path}")
    if not processed_path.is_dir():
        errors.append(f"processed path missing or not a directory: {processed_path}")

    report = _load_json(report_path)
    expected = manifest["expected_from_adapter_report"]

    _compare(
        expected.get("adapter_report_schema_version"),
        report.get("adapter_report_schema_version"),
        "adapter_report_schema_version",
        errors,
    )
    _compare(manifest["adapter"]["name"], report.get("adapter", {}).get("name"), "adapter.name", errors)
    _compare(manifest["adapter"]["version"], report.get("adapter", {}).get("version"), "adapter.version", errors)
    _compare(manifest["source"]["hf_repo"], report.get("hf_repo"), "source.hf_repo", errors)
    _compare(
        manifest["source"]["hf_revision"],
        report.get("hf_revision"),
        "source.hf_revision",
        errors,
    )
    _compare(
        manifest["source"]["task_join_hf_repo"],
        report.get("task_join_hf_repo"),
        "source.task_join_hf_repo",
        errors,
    )
    _compare_block(expected.get("counts", {}), report.get("counts", {}), "counts", errors)
    _compare_block(
        expected.get("trajectory", {}),
        report.get("trajectory", {}),
        "trajectory",
        errors,
    )
    _compare(
        expected.get("privacy", {}).get("redaction_totals", []),
        report.get("privacy", {}).get("redaction_totals", []),
        "privacy.redaction_totals",
        errors,
    )
    hashes = expected.get("hashes", {})
    for key, value in hashes.items():
        _compare(value, report.get(key), key, errors)

    for name in (
        "pneuma_traces.jsonl",
        "pneuma_traces.invalid.jsonl",
        "trace_index.jsonl",
        "adapter_report.json",
    ):
        path = processed_path / name
        if not path.is_file():
            errors.append(f"processed output missing: {path}")

    if errors:
        raise ValidationError("; ".join(errors))
    return [
        f"dataset={dataset}",
        f"manifest={manifest_file}",
        f"data_root={data_root}",
        f"adapter_report={report_path}",
        f"valid_traces={report['counts']['valid']}",
        f"invalid_traces={report['counts']['invalid']}",
        f"agent_steps={report['trajectory']['total_agent_steps']}",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a dataset onboarding manifest against local metadata."
    )
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--registry-root", default=str(DEFAULT_REGISTRY_ROOT))
    args = parser.parse_args(argv)

    try:
        lines = validate(
            args.dataset,
            _data_root(args.data_root),
            Path(args.registry_root),
        )
    except ValidationError as exc:
        print(f"FAIL: {exc}")
        return 1

    print("PASS: dataset onboarding manifest matches adapter report.")
    for line in lines:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

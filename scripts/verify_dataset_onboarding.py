#!/usr/bin/env python3
"""Validate one committed dataset-onboarding manifest against local metadata.

The validator is intentionally metadata-only: it reads the committed manifest
and the dataset's metadata reports, checks paths and expected counts/hashes,
and does not inspect raw parquet rows, dialogue content, or processed trace JSONL
content.
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
    "open-swe-traces": "open-swe-traces.json",
}

COMMON_REQUIRED_FIELDS = (
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
        raise ValidationError(
            f"unsupported dataset {dataset!r}; supported: {supported}"
        )
    return registry_root / name


def _require_fields(
    manifest: dict, required: tuple[str, ...] = COMMON_REQUIRED_FIELDS
) -> None:
    missing = [field for field in required if field not in manifest]
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


def _compare_block(
    expected: dict, actual: dict, prefix: str, errors: list[str]
) -> None:
    for key, value in expected.items():
        if isinstance(value, dict):
            _compare_block(value, actual.get(key, {}), f"{prefix}.{key}", errors)
        else:
            _compare(value, actual.get(key), f"{prefix}.{key}", errors)


def _relative_to_data_root(path_value: str, data_root: Path) -> str:
    path = Path(path_value)
    try:
        return path.relative_to(data_root).as_posix()
    except ValueError:
        return path.as_posix()


def _validate_adapter_report(
    manifest: dict,
    data_root: Path,
    processed_path: Path,
    report_path: Path,
    errors: list[str],
) -> list[str]:
    if "expected_from_adapter_report" not in manifest:
        raise ValidationError(
            "adapter_report validation requires expected_from_adapter_report"
        )

    report = _load_json(report_path)
    expected = manifest["expected_from_adapter_report"]

    _compare(
        expected.get("adapter_report_schema_version"),
        report.get("adapter_report_schema_version"),
        "adapter_report_schema_version",
        errors,
    )
    _compare(
        manifest["adapter"]["name"],
        report.get("adapter", {}).get("name"),
        "adapter.name",
        errors,
    )
    _compare(
        manifest["adapter"]["version"],
        report.get("adapter", {}).get("version"),
        "adapter.version",
        errors,
    )
    _compare(
        manifest["source"]["hf_repo"], report.get("hf_repo"), "source.hf_repo", errors
    )
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
    _compare_block(
        expected.get("counts", {}), report.get("counts", {}), "counts", errors
    )
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

    return [
        f"adapter_report={report_path}",
        f"valid_traces={report['counts']['valid']}",
        f"invalid_traces={report['counts']['invalid']}",
        f"agent_steps={report['trajectory']['total_agent_steps']}",
    ]


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValidationError(
                        f"invalid JSONL in {path} on line {line_number}: {exc}"
                    ) from exc
    except FileNotFoundError as exc:
        raise ValidationError(f"missing JSONL file: {path}") from exc
    return rows


def _validate_metadata_inventory(
    manifest: dict,
    data_root: Path,
    errors: list[str],
) -> list[str]:
    for field in ("metadata_inventory", "expected_from_metadata_files"):
        if field not in manifest:
            raise ValidationError(f"metadata_inventory validation requires {field}")

    inventory = manifest["metadata_inventory"]
    expected = manifest["expected_from_metadata_files"]
    expected_files = expected.get("raw_files", [])

    row_counts_path = data_root / inventory["row_counts_relative"]
    file_index_path = data_root / inventory["file_index_relative"]
    provenance_path = data_root / inventory["provenance_relative"]
    normalized_metadata_path = data_root / inventory["normalized_metadata_relative"]

    row_counts = _load_json(row_counts_path)
    provenance = _load_json(provenance_path)
    file_index_rows = _load_jsonl(file_index_path)
    normalized_metadata_rows = _load_jsonl(normalized_metadata_path)

    _compare(
        expected.get("total_rows"),
        row_counts.get("total_rows"),
        "row_counts.total_rows",
        errors,
    )
    _compare(expected.get("files"), row_counts.get("files"), "row_counts.files", errors)
    _compare(
        expected.get("metadata_rows"),
        len(normalized_metadata_rows),
        "normalized_metadata.row_count",
        errors,
    )

    expected_by_file = {
        item["path_relative"]: {
            "rows": item["rows"],
            "bytes": item["bytes"],
            "sha256": item["sha256"],
        }
        for item in expected_files
    }
    actual_by_file = {
        _relative_to_data_root(item["path"], data_root): {
            "rows": item.get("rows"),
            "bytes": item.get("bytes"),
            "sha256": item.get("sha256"),
        }
        for item in file_index_rows
    }
    _compare(expected_by_file, actual_by_file, "file_index.raw_files", errors)

    actual_row_counts = {
        _relative_to_data_root(path, data_root): count
        for path, count in row_counts.get("by_file", {}).items()
    }
    expected_row_counts = {
        item["path_relative"]: item["rows"] for item in expected_files
    }
    _compare(expected_row_counts, actual_row_counts, "row_counts.by_file", errors)

    expected_hf = expected.get("huggingface_snapshot", {})
    actual_hf = (provenance.get("huggingface_snapshots") or [{}])[0]
    _compare(
        expected_hf.get("repo_id"),
        actual_hf.get("repo_id"),
        "provenance.hf_repo_id",
        errors,
    )
    _compare(
        expected_hf.get("revision"),
        actual_hf.get("revision"),
        "provenance.hf_revision",
        errors,
    )

    expected_git = expected.get("git_repo", {})
    actual_git = (provenance.get("git_repos") or [{}])[0]
    _compare(
        expected_git.get("url"), actual_git.get("url"), "provenance.git_url", errors
    )
    _compare(
        expected_git.get("commit_sha"),
        actual_git.get("commit_sha"),
        "provenance.git_commit_sha",
        errors,
    )

    expected_keys = sorted(expected.get("normalized_metadata_keys", []))
    actual_keys = sorted({key for row in normalized_metadata_rows for key in row})
    _compare(expected_keys, actual_keys, "normalized_metadata.keys", errors)

    return [
        f"metadata_source={row_counts_path}",
        f"metadata_rows={len(normalized_metadata_rows)}",
        f"source_files={len(file_index_rows)}",
    ]


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

    validation_profile = manifest.get("validation_profile", "adapter_report")
    if validation_profile == "adapter_report":
        summary = _validate_adapter_report(
            manifest, data_root, processed_path, report_path, errors
        )
    elif validation_profile == "metadata_inventory":
        summary = _validate_metadata_inventory(manifest, data_root, errors)
    else:
        raise ValidationError(f"unsupported validation_profile: {validation_profile!r}")

    if errors:
        raise ValidationError("; ".join(errors))
    return [
        f"dataset={dataset}",
        f"manifest={manifest_file}",
        f"data_root={data_root}",
        f"validation_profile={validation_profile}",
        *summary,
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

    print("PASS: dataset onboarding manifest matches local metadata.")
    for line in lines:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

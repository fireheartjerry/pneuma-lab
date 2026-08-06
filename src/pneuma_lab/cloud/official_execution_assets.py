"""Frozen task payloads used by the official two-benchmark executor.

The public task registry intentionally contains only opaque task identities.
This module creates the separate controller-only execution payload without
copying the SWE gold patch.  It also binds every selected image to the exact
OCI manifest admitted by the roster audit.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

from .errors import CloudManifestError


SWE_DATASET_REPOSITORY = "SWE-bench-Live/MultiLang"
SWE_DATASET_REVISION = "608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b"
SWE_SPLITS = ("c", "cpp", "cs", "go", "java", "js", "rust", "ts")
_EXECUTION_FIELDS = (
    "repo",
    "instance_id",
    "base_commit",
    "problem_statement",
    "test_patch",
    "rebuild_cmds",
    "test_cmds",
    "print_cmds",
    "log_parser",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
)


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _load(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudManifestError(f"invalid execution-asset input: {path}") from exc
    # The Step-5B roster audit is hash-bound but predates the repository-wide
    # canonical-newline convention.  Its exact bytes remain authoritative;
    # this reader only decodes them and emits a new canonical execution asset.
    if not isinstance(value, dict):
        raise CloudManifestError(f"execution-asset input is not an object: {path}")
    return value


def build_swe_execution_assets(
    *,
    task_registry_path: Path,
    selection_path: Path,
    dataset_rows: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Return the exact 120 selected SWE task payloads, excluding gold patches."""

    registry = _load(task_registry_path)
    selection = _load(selection_path)
    tasks = registry.get("tasks")
    selection_rows = selection.get("rows")
    if not isinstance(tasks, list) or not isinstance(selection_rows, list):
        raise CloudManifestError("task registry or SWE selection is malformed")
    selected_ids = [
        str(row["task_id"]).split(":", 1)[1]
        for row in tasks
        if isinstance(row, Mapping) and row.get("benchmark") == "SWE"
    ]
    if len(selected_ids) != 120 or len(set(selected_ids)) != 120:
        raise CloudManifestError("execution assets require exactly 120 SWE tasks")
    admitted: dict[str, Mapping[str, object]] = {}
    for row in selection_rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("instance_id"), str):
            raise CloudManifestError("SWE selection row is malformed")
        admitted[str(row["instance_id"])] = row
    if not set(selected_ids).issubset(admitted):
        raise CloudManifestError("task registry is not covered by the SWE selection")
    by_id: dict[str, Mapping[str, object]] = {}
    for row in dataset_rows:
        instance_id = row.get("instance_id")
        if isinstance(instance_id, str) and instance_id in selected_ids:
            if instance_id in by_id:
                raise CloudManifestError("SWE dataset contains a duplicate selected task")
            by_id[instance_id] = row
    if set(by_id) != set(selected_ids):
        raise CloudManifestError("pinned SWE dataset lacks a selected task")

    output_rows: list[dict[str, object]] = []
    for instance_id in selected_ids:
        source = by_id[instance_id]
        audit = admitted[instance_id]
        oci = audit.get("oci")
        if not isinstance(oci, Mapping):
            raise CloudManifestError("selected SWE task lacks OCI admission")
        digest = oci.get("manifest_digest")
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise CloudManifestError("selected SWE task lacks an immutable image digest")
        if source.get("base_commit") != audit.get("base_commit"):
            raise CloudManifestError("SWE dataset base commit differs from the audit")
        missing = [field for field in _EXECUTION_FIELDS if field not in source]
        if missing:
            raise CloudManifestError("SWE execution row lacks registered fields")
        row = {field: source[field] for field in _EXECUTION_FIELDS}
        # The solution patch is deliberately absent.  The trusted grader needs
        # only the test patch and registered endpoint definitions.
        if "patch" in row:
            raise AssertionError("gold patch entered the execution payload")
        row.update(
            {
                "task_id": f"swe:{instance_id}",
                "language": audit["language"],
                "image_ref": f"docker.io/{audit['docker_image']}@{digest}",
                "dataset_revision": SWE_DATASET_REVISION,
            }
        )
        output_rows.append(row)
    value: dict[str, object] = {
        "record_kind": "cloud_official_swe_execution_assets",
        "schema_version": "0.1.0",
        "dataset_repository": SWE_DATASET_REPOSITORY,
        "dataset_revision": SWE_DATASET_REVISION,
        "task_count": 120,
        "gold_solution_patch_present": False,
        "tasks": output_rows,
    }
    validate_swe_execution_assets(value)
    return value


def validate_swe_execution_assets(value: Mapping[str, object]) -> None:
    if (
        value.get("record_kind") != "cloud_official_swe_execution_assets"
        or value.get("schema_version") != "0.1.0"
        or value.get("dataset_repository") != SWE_DATASET_REPOSITORY
        or value.get("dataset_revision") != SWE_DATASET_REVISION
        or value.get("task_count") != 120
        or value.get("gold_solution_patch_present") is not False
    ):
        raise CloudManifestError("official SWE execution assets have wrong identity")
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 120:
        raise CloudManifestError("official SWE execution assets require 120 tasks")
    ids: set[str] = set()
    for task in tasks:
        if not isinstance(task, Mapping):
            raise CloudManifestError("official SWE execution task is malformed")
        task_id = task.get("task_id")
        image_ref = task.get("image_ref")
        if (
            not isinstance(task_id, str)
            or not task_id.startswith("swe:")
            or task_id in ids
            or not isinstance(image_ref, str)
            or "@sha256:" not in image_ref
            or "patch" in task
        ):
            raise CloudManifestError("official SWE execution task is not closed")
        ids.add(task_id)


def write_swe_execution_assets(
    *,
    task_registry_path: Path,
    selection_path: Path,
    output_path: Path,
) -> dict[str, object]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise CloudManifestError("the datasets package is required") from exc
    rows: list[Mapping[str, object]] = []
    for split in SWE_SPLITS:
        dataset = load_dataset(
            SWE_DATASET_REPOSITORY,
            revision=SWE_DATASET_REVISION,
            split=split,
            trust_remote_code=False,
        )
        rows.extend(dataset)
    value = build_swe_execution_assets(
        task_registry_path=task_registry_path,
        selection_path=selection_path,
        dataset_rows=rows,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value)
    output_path.write_bytes(payload)
    return {
        "path": str(output_path),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_count": len(payload),
        "task_count": 120,
    }


__all__ = [
    "SWE_DATASET_REPOSITORY",
    "SWE_DATASET_REVISION",
    "build_swe_execution_assets",
    "canonical_bytes",
    "validate_swe_execution_assets",
    "write_swe_execution_assets",
]

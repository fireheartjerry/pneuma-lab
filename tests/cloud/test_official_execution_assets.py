from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.official_execution_assets import (
    build_swe_execution_assets,
    canonical_bytes,
)


def _write(path: Path, value: object) -> None:
    path.write_bytes(canonical_bytes(value))


def _fixture(tmp_path: Path) -> tuple[Path, Path, list[dict[str, object]]]:
    tasks = [
        {"task_id": f"swe:repo__task-{index}", "benchmark": "SWE"}
        for index in range(120)
    ]
    registry = tmp_path / "tasks.json"
    _write(registry, {"tasks": tasks})
    rows = []
    dataset = []
    for index in range(120):
        instance_id = f"repo__task-{index}"
        rows.append(
            {
                "instance_id": instance_id,
                "base_commit": hashlib.sha1(str(index).encode()).hexdigest(),
                "language": "c",
                "docker_image": f"example/{instance_id}",
                "oci": {"manifest_digest": "sha256:" + f"{index:064x}"},
            }
        )
        dataset.append(
            {
                "repo": "example/repo",
                "instance_id": instance_id,
                "base_commit": rows[-1]["base_commit"],
                "problem_statement": "repair it",
                "test_patch": "diff --git a/t b/t",
                "rebuild_cmds": [],
                "test_cmds": ["true"],
                "print_cmds": ["true"],
                "log_parser": "pytest",
                "FAIL_TO_PASS": ["x"],
                "PASS_TO_PASS": [],
                "patch": "SECRET GOLD",
            }
        )
    selection = tmp_path / "selection.json"
    _write(selection, {"rows": rows})
    return registry, selection, dataset


def test_builds_exact_gold_free_execution_payload(tmp_path: Path) -> None:
    registry, selection, rows = _fixture(tmp_path)
    value = build_swe_execution_assets(
        task_registry_path=registry,
        selection_path=selection,
        dataset_rows=rows,
    )
    assert value["task_count"] == 120
    assert all("patch" not in row for row in value["tasks"])
    assert all("@sha256:" in row["image_ref"] for row in value["tasks"])


def test_rejects_dataset_base_commit_drift(tmp_path: Path) -> None:
    registry, selection, rows = _fixture(tmp_path)
    rows[0]["base_commit"] = "0" * 40
    with pytest.raises(CloudManifestError, match="base commit"):
        build_swe_execution_assets(
            task_registry_path=registry,
            selection_path=selection,
            dataset_rows=rows,
        )

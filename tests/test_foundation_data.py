"""Dataset-role, deduplication, inventory, and immutable-corpus tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.foundation.data import (
    ACTIVE_DATASET_GROUPS,
    DataAuthorizationError,
    build_content_addressed_shard,
    build_diversity_inventory,
    deduplicate_examples,
    governed_dataset_groups,
)


ROOT = Path(__file__).resolve().parents[1]


def _example(example_id: str = "ex-1", **overrides) -> dict:
    value = {
        "example_id": example_id,
        "dataset_group": "open-swe-traces",
        "training_authorization": "authorized",
        "training_weight": 1.0,
        "repo": "org/repo",
        "issue_or_pr": "123",
        "task_id": "task-123",
        "base_commit": "abc",
        "patch": "diff --git a/x b/x",
        "test_patch": "test x",
        "text": "Use the tool and verify the result",
        "language": "python",
        "tools": ["shell", "pytest"],
        "trajectory_length": 8,
        "label": "resolved",
    }
    value.update(overrides)
    return value


def test_all_ten_active_dataset_groups_are_governed_by_registry() -> None:
    registry = json.loads(
        (ROOT / "docs/data/training-readiness/dataset-registry.json").read_text(
            encoding="utf-8"
        )
    )
    assert ACTIVE_DATASET_GROUPS == (
        "multi-swe-bench",
        "open-swe-traces",
        "sec-bench-pro",
        "swe-bench",
        "swe-bench-pro",
        "swe-chat",
        "swe-evo",
        "swe-gym",
        "swe-mera",
        "swe-polybench",
    )
    governed = governed_dataset_groups(registry)
    assert set(governed) == set(ACTIVE_DATASET_GROUPS)
    assert governed["sec-bench-pro"].training_authorized is False
    assert governed["swe-bench"].training_authorized is False


def test_deduplication_uses_repo_issue_commit_patch_test_and_fuzzy_text() -> None:
    original = _example()
    fuzzy_duplicate = _example(
        "ex-2",
        text="  use   THE tool and VERIFY the result ",
    )
    distinct = _example("ex-3", issue_or_pr="124", task_id="task-124")
    unique, duplicate_ids = deduplicate_examples((original, fuzzy_duplicate, distinct))
    assert [item["example_id"] for item in unique] == ["ex-1", "ex-3"]
    assert duplicate_ids == ("ex-2",)


def test_inventory_reports_required_diversity_dimensions() -> None:
    inventory = build_diversity_inventory(
        (
            _example(),
            _example(
                "ex-2",
                repo="org/second",
                issue_or_pr="9",
                task_id="task-9",
                language="rust",
                tools=["shell"],
                trajectory_length=3,
                label="unresolved",
            ),
        )
    )
    assert inventory["example_count"] == 2
    assert inventory["token_count"] > 0
    assert inventory["repository_count"] == 2
    assert inventory["issue_count"] == 2
    assert inventory["languages"] == {"python": 1, "rust": 1}
    assert inventory["tools"] == {"pytest": 1, "shell": 2}
    assert inventory["trajectory_length"]["max"] == 8
    assert inventory["labels"] == {"resolved": 1, "unresolved": 1}


def test_content_addressed_shard_never_writes_to_data_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    output_root = repo_root / "build" / "foundation" / "shards"
    data_root = tmp_path / "pneuma-data"
    data_root.mkdir()
    sentinel = data_root / "sentinel.txt"
    sentinel.write_text("immutable", encoding="utf-8")
    result = build_content_addressed_shard(
        (_example(),),
        repo_root=repo_root,
        output_root=output_root,
        data_root=data_root,
    )
    assert result.shard_path.parent == output_root
    assert result.shard_path.name == f"{result.sha256}.jsonl"
    assert result.manifest_path.is_file()
    assert sentinel.read_text(encoding="utf-8") == "immutable"


def test_shard_rejects_blocked_positive_weight_and_unsafe_output(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    data_root = tmp_path / "pneuma-data"
    data_root.mkdir()
    with pytest.raises(DataAuthorizationError, match="zero-weight"):
        build_content_addressed_shard(
            (
                _example(
                    dataset_group="sec-bench-pro",
                    training_authorization="blocked",
                    training_weight=1.0,
                ),
            ),
            repo_root=repo_root,
            output_root=repo_root / "build" / "shards",
            data_root=data_root,
        )
    with pytest.raises(DataAuthorizationError, match="pneuma-data"):
        build_content_addressed_shard(
            (_example(),),
            repo_root=repo_root,
            output_root=data_root / "bad",
            data_root=data_root,
        )


def test_security_records_cannot_request_exploit_execution(tmp_path: Path) -> None:
    with pytest.raises(DataAuthorizationError, match="functioning exploit"):
        build_content_addressed_shard(
            (
                _example(
                    dataset_group="sec-bench-pro",
                    training_authorization="blocked",
                    training_weight=0.0,
                    functioning_exploit=True,
                ),
            ),
            repo_root=tmp_path / "repo",
            output_root=tmp_path / "repo" / "build" / "shards",
            data_root=tmp_path / "pneuma-data",
        )

"""Dataset-role, deduplication, inventory, and immutable-corpus tests."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from pneuma_lab.foundation import data as foundation_data
from pneuma_lab.foundation.data import (
    ACTIVE_DATASET_GROUPS,
    DataAuthorizationError,
    build_content_addressed_shard,
    build_diversity_inventory,
    dedup_fingerprint,
    deduplicate_examples,
    governed_dataset_groups,
)
from pneuma_lab.foundation.preparation import select_complete_records


ROOT = Path(__file__).resolve().parents[1]


def _make_directory_alias(link: Path, target: Path) -> None:
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            pytest.skip(f"directory junctions unavailable: {result.stderr.strip()}")
        return
    try:
        link.symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")


def _example(example_id: str = "ex-1", **overrides) -> dict:
    value = {
        "record_kind": "pneuma_foundation_training_record",
        "record_schema_version": "0.1.0",
        "record_id": "ftr:" + hashlib.sha256(example_id.encode()).hexdigest(),
        "source": {
            "dataset_family": "open-swe-traces",
            "lane_id": "open-swe-traces",
            "source_record_id": example_id,
            "source_revision": None,
            "receipt_hashes": [],
        },
        "disposition": {
            "terminal_role": "train",
            "gradient_eligibility": "later",
            "license_disposition": "reviewed",
            "privacy_disposition": "reviewed",
            "dual_use_disposition": "not_flagged",
            "oracle_disposition": "target_only",
        },
        "identity": {
            "repo": "org/repo",
            "issue_or_pr": "123",
            "task_id": "task-123",
            "base_commit": "abc",
            "patch_sha256": "sha256:" + "a" * 64,
            "test_patch_sha256": "b" * 64,
            "fuzzy_text_sha256": "c" * 64,
        },
        "split": {"split_id": "train", "quarantine_id": None},
        "rendered": {"prompt_text": "prompt", "target_text": "target"},
        "tokenization": {
            "tokenizer_id": "Qwen/Qwen3.5-2B",
            "tokenizer_revision": "d" * 40,
            "prompt_tokens": 4,
            "target_tokens": 2,
            "total_tokens": 6,
        },
        "training_weight": 0.0,
        "forecast_targets": {
            "action_success": {
                "applicable": True,
                "value": 1.0,
                "provenance": "observed_outcome",
            },
            "expected_error": {
                "applicable": True,
                "value": 0.0,
                "provenance": "observed_outcome",
            },
            **{
                name: {"applicable": False, "value": None, "provenance": None}
                for name in (
                    "verifier_outcome",
                    "tool_cost",
                    "token_cost",
                    "latency_cost",
                    "retrieval_usefulness",
                    "intervention_response",
                )
            },
        },
        "observations": {
            "language": "python",
            "tools": ["shell", "pytest"],
            "trajectory_length": 8,
            "labels": {"resolved": True},
        },
    }
    for key, override in overrides.items():
        if key in value["identity"]:
            value["identity"][key] = override
        elif key in value["observations"]:
            value["observations"][key] = override
        elif key == "resolved":
            value["observations"]["labels"]["resolved"] = override
        elif key == "total_tokens":
            value["tokenization"]["total_tokens"] = override
        elif key == "dataset_family":
            value["source"]["dataset_family"] = override
        elif key == "training_weight":
            value["training_weight"] = override
        else:
            value[key] = override
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
        patch_sha256="a" * 64,
    )
    distinct = _example("ex-3", issue_or_pr="124", task_id="task-124")
    unique, duplicate_ids = deduplicate_examples((original, fuzzy_duplicate, distinct))
    assert [item["source"]["source_record_id"] for item in unique] == [
        "ex-1",
        "ex-3",
    ]
    assert duplicate_ids == ("ex-2",)


def test_dedup_fingerprint_preserves_valid_prefixed_digest() -> None:
    prefixed = _example(patch_sha256="sha256:" + "a" * 64)
    bare = _example(patch_sha256="a" * 64)
    assert dedup_fingerprint(prefixed) == dedup_fingerprint(bare)


def test_identity_digest_canonicalization_is_shared_and_case_insensitive() -> None:
    normalization = importlib.import_module(
        "pneuma_lab.foundation.identity_normalization"
    )
    lowercase = "sha256:" + "a" * 64
    uppercase = "SHA256:" + "A" * 64
    assert normalization.normalize_identity_digest(lowercase) == lowercase
    assert normalization.normalize_identity_digest(uppercase) == lowercase
    assert dedup_fingerprint(
        _example(patch_sha256=lowercase)
    ) == dedup_fingerprint(_example(patch_sha256=uppercase))


def test_dedup_fingerprint_hashes_normalized_malformed_digest_text() -> None:
    malformed = "  SHA256:" + "G" * 64 + "  "
    normalized_raw = "sha256:" + "g" * 64
    canonical_digest = "sha256:" + hashlib.sha256(
        normalized_raw.encode("utf-8")
    ).hexdigest()
    assert dedup_fingerprint(
        _example(patch_sha256=malformed)
    ) == dedup_fingerprint(_example(patch_sha256=canonical_digest))


def test_dedup_fingerprint_hashes_malformed_prefixed_digest_as_raw_text() -> None:
    malformed = "sha256:" + "g" * 64
    malformed_record = _example(patch_sha256=malformed)
    equivalent_digest = _example(
        patch_sha256=hashlib.sha256(malformed.encode("utf-8")).hexdigest()
    )
    assert dedup_fingerprint(malformed_record) == dedup_fingerprint(
        equivalent_digest
    )


def test_dedup_fingerprint_requires_persisted_zero_weight() -> None:
    with pytest.raises(DataAuthorizationError, match="zero-weight"):
        dedup_fingerprint(_example(training_weight=None))


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
                resolved=False,
                total_tokens=9,
            ),
        )
    )
    assert inventory["example_count"] == 2
    assert inventory["token_count"] == 15
    assert inventory["repository_count"] == 2
    assert inventory["issue_count"] == 2
    assert inventory["languages"] == {"python": 1, "rust": 1}
    assert inventory["tools"] == {"pytest": 1, "shell": 2}
    assert inventory["trajectory_length"]["max"] == 8
    assert inventory["labels"] == {"resolved": 1, "unresolved": 1}
    assert inventory["dataset_families"] == {"open-swe-traces": 2}
    assert inventory["forecast_targets"] == {
        "action_success": 2,
        "expected_error": 2,
    }


def test_inventory_canonicalizes_repo_and_issue_case_and_whitespace() -> None:
    inventory = build_diversity_inventory(
        (
            _example(repo="Org/Repo", issue_or_pr="Issue  123"),
            _example(
                "ex-2",
                repo="  org/repo  ",
                issue_or_pr=" issue 123 ",
            ),
        )
    )
    assert inventory["repository_count"] == 1
    assert inventory["issue_count"] == 1


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


def test_shard_rejects_build_alias_escaping_repo_before_write(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    _make_directory_alias(repo_root / "build", outside)

    with pytest.raises(DataAuthorizationError, match="link|reparse|junction"):
        build_content_addressed_shard(
            (_example(),),
            repo_root=repo_root,
            output_root=repo_root / "build/foundation/shards",
            data_root=tmp_path / "pneuma-data",
        )
    assert tuple(outside.iterdir()) == ()


def test_shard_rejects_nested_build_alias_before_write(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    build_root = repo_root / "build"
    alias_target = build_root / "physical-target"
    alias_target.mkdir(parents=True)
    _make_directory_alias(build_root / "foundation", alias_target)

    with pytest.raises(DataAuthorizationError, match="link|reparse|junction"):
        build_content_addressed_shard(
            (_example(),),
            repo_root=repo_root,
            output_root=repo_root / "build/foundation/shards",
            data_root=tmp_path / "pneuma-data",
        )
    assert tuple(alias_target.iterdir()) == ()


def test_shard_rejects_aliased_repo_root_before_write(tmp_path: Path) -> None:
    physical_repo = tmp_path / "physical-repo"
    physical_repo.mkdir()
    repo_alias = tmp_path / "repo-alias"
    _make_directory_alias(repo_alias, physical_repo)

    with pytest.raises(DataAuthorizationError, match="link|reparse|junction"):
        build_content_addressed_shard(
            (_example(),),
            repo_root=repo_alias,
            output_root=repo_alias / "build/foundation/shards",
            data_root=tmp_path / "pneuma-data",
        )
    assert not (physical_repo / "build").exists()


@pytest.mark.parametrize("initially_missing", (False, True))
def test_shard_binds_output_ancestry_during_publication(
    tmp_path: Path,
    monkeypatch,
    initially_missing: bool,
) -> None:
    repo_root = tmp_path / "repo"
    output_root = repo_root / "build/foundation/shards"
    output_root.parent.mkdir(parents=True)
    if not initially_missing:
        output_root.mkdir()
    saved_output = output_root.with_name("shards-before-race")
    data_root = tmp_path / "pneuma-data"
    data_root.mkdir()
    sentinel = data_root / "sentinel.txt"
    sentinel.write_text("immutable", encoding="utf-8")
    before = tuple(path.name for path in data_root.iterdir())
    real_write = foundation_data.write_atomic_bytes

    def swap_output_ancestry(path: Path, payload: bytes, **kwargs) -> None:
        if output_root.exists():
            if initially_missing:
                output_root.rmdir()
            else:
                output_root.rename(saved_output)
        _make_directory_alias(output_root, data_root)
        real_write(path, payload, **kwargs)

    monkeypatch.setattr(
        foundation_data,
        "write_atomic_bytes",
        swap_output_ancestry,
    )
    result = None
    with pytest.raises(DataAuthorizationError, match="publication|output"):
        result = build_content_addressed_shard(
            (_example(),),
            repo_root=repo_root,
            output_root=output_root,
            data_root=data_root,
        )
    assert result is None
    assert tuple(path.name for path in data_root.iterdir()) == before
    assert sentinel.read_text(encoding="utf-8") == "immutable"


def test_shard_rolls_back_if_ancestry_changes_between_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    output_root = repo_root / "build/foundation/shards"
    output_root.mkdir(parents=True)
    saved_output = output_root.with_name("shards-before-race")
    data_root = tmp_path / "pneuma-data"
    data_root.mkdir()
    sentinel = data_root / "sentinel.txt"
    sentinel.write_text("immutable", encoding="utf-8")
    before = tuple(path.name for path in data_root.iterdir())
    real_write = foundation_data.write_atomic_json

    def swap_after_shard(path: Path, value, **kwargs) -> None:
        output_root.rename(saved_output)
        _make_directory_alias(output_root, data_root)
        real_write(path, value, **kwargs)

    monkeypatch.setattr(foundation_data, "write_atomic_json", swap_after_shard)
    result = None
    with pytest.raises(DataAuthorizationError, match="publication|output"):
        result = build_content_addressed_shard(
            (_example(),),
            repo_root=repo_root,
            output_root=output_root,
            data_root=data_root,
        )
    assert result is None
    assert tuple(path.name for path in data_root.iterdir()) == before
    assert not saved_output.exists() or tuple(saved_output.iterdir()) == ()
    assert sentinel.read_text(encoding="utf-8") == "immutable"


def test_shard_requires_output_lexically_below_repo_build(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    detour = repo_root / "detour"
    detour.mkdir(parents=True)
    output_root = detour / "../build/foundation/shards"

    with pytest.raises(DataAuthorizationError, match="build storage"):
        build_content_addressed_shard(
            (_example(),),
            repo_root=repo_root,
            output_root=output_root,
            data_root=tmp_path / "pneuma-data",
        )
    assert not (repo_root / "build").exists()


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
                    dataset_family="sec-bench-pro",
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


def test_shard_requires_exact_persisted_zero_weight_and_record_shape(
    tmp_path: Path,
) -> None:
    with pytest.raises(DataAuthorizationError, match="zero-weight"):
        build_content_addressed_shard(
            (_example(training_weight=None),),
            repo_root=tmp_path / "repo",
            output_root=tmp_path / "repo" / "build" / "shards",
            data_root=tmp_path / "pneuma-data",
        )
    malformed = _example()
    malformed["observations"]["unknown"] = True
    with pytest.raises(DataAuthorizationError, match="Additional properties"):
        build_content_addressed_shard(
            (malformed,),
            repo_root=tmp_path / "repo",
            output_root=tmp_path / "repo" / "build" / "shards",
            data_root=tmp_path / "pneuma-data",
        )


@pytest.mark.parametrize("training_weight", (0, -0.0, False, float("nan")))
def test_shard_requires_positive_zero_float_training_weight(
    tmp_path: Path,
    training_weight,
) -> None:
    with pytest.raises(DataAuthorizationError, match="zero-weight"):
        build_content_addressed_shard(
            (_example(training_weight=training_weight),),
            repo_root=tmp_path / "repo",
            output_root=tmp_path / "repo" / "build" / "shards",
            data_root=tmp_path / "pneuma-data",
        )


def test_shard_rejects_non_mapping_before_dict_coercion(tmp_path: Path) -> None:
    record_as_pairs = list(_example().items())
    output_root = tmp_path / "repo" / "build" / "shards"
    with pytest.raises(DataAuthorizationError, match="mapping"):
        build_content_addressed_shard(
            (record_as_pairs,),
            repo_root=tmp_path / "repo",
            output_root=output_root,
            data_root=tmp_path / "pneuma-data",
        )
    assert not output_root.exists()


def test_selected_smoke_records_remain_exact_zero_weight_in_shard(
    tmp_path: Path,
) -> None:
    resolved = _example("resolved", repo="org/resolved", resolved=True)
    unresolved = _example(
        "unresolved",
        repo="org/unresolved",
        issue_or_pr="456",
        task_id="task-456",
        resolved=False,
    )
    selected = select_complete_records(
        (unresolved, resolved),
        token_ceiling=12,
    )
    result = build_content_addressed_shard(
        selected,
        repo_root=tmp_path / "repo",
        output_root=tmp_path / "repo/build/foundation/shards",
        data_root=tmp_path / "pneuma-data",
    )
    persisted = [
        json.loads(line)
        for line in result.shard_path.read_text(encoding="utf-8").splitlines()
    ]

    assert len(persisted) == 2
    assert all(record["training_weight"] == 0.0 for record in persisted)
    assert sum(record["tokenization"]["total_tokens"] for record in persisted) == 12

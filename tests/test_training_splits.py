from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.training import splits


DATASET_ID = "swe-gym-openhands-sampled"


def _example(repo: str | None, index: int, resolved: bool, task: str | None = None) -> dict:
    return {
        "example_id": f"pte:{DATASET_ID}:synthetic-{index}:risk:full",
        "dataset_id": DATASET_ID,
        "split_group": {
            "repo": repo,
            "task_id": task or f"{repo or 'missing'}-{index}",
            "session_or_user": None,
            "era": None,
        },
        "target": {"resolved": resolved},
    }


def _synthetic_examples() -> list[dict]:
    examples: list[dict] = []
    index = 0
    for repo, count, resolved_every in [
        ("alpha/repo", 4, 3),
        ("beta/repo", 3, 2),
        ("gamma/repo", 2, 2),
        ("delta/repo", 2, 10),
        ("epsilon/repo", 1, 1),
    ]:
        for offset in range(count):
            index += 1
            examples.append(_example(repo, index, offset % resolved_every == 0))
    return examples


def _write_examples(path: Path, examples: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(example, sort_keys=True) + "\n" for example in examples),
        encoding="utf-8",
    )


def _output_paths(tmp_path: Path, name: str = "run") -> tuple[Path, Path, Path]:
    root = tmp_path / "build" / name
    return (
        root / "split_manifest.json",
        root / "split_report.json",
        root / "hash_manifest.json",
    )


def _manifest_self_hash(manifest: dict) -> str:
    value = copy.deepcopy(manifest)
    value["hashes"]["hash_manifest_json_sha256"] = None
    text = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _run(tmp_path: Path, name: str = "run") -> dict:
    input_path = tmp_path / "examples.jsonl"
    _write_examples(input_path, _synthetic_examples())
    output, report, hash_manifest = _output_paths(tmp_path, name)
    return splits.run_split_generation(
        input_path=input_path,
        output_path=output,
        report_path=report,
        hash_manifest_path=hash_manifest,
        dataset_id=DATASET_ID,
        train_ratio=0.60,
        validation_ratio=0.20,
        test_ratio=0.20,
    )


def test_split_assignment_is_deterministic_across_runs(tmp_path: Path) -> None:
    result1 = _run(tmp_path, "run1")
    result2 = _run(tmp_path, "run2")

    assert result1["split_manifest"] == result2["split_manifest"]
    assert result1["split_report"] == result2["split_report"]
    assert result1["hash_manifest"] == result2["hash_manifest"]


def test_same_repo_stays_in_one_split_when_grouping_is_feasible(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assignments = result["split_manifest"]["assignments"]
    repo_splits: dict[str, set[str]] = {}
    for assignment in assignments:
        repo_splits.setdefault(assignment["repo"], set()).add(assignment["split"])

    assert all(len(values) == 1 for values in repo_splits.values())
    assert result["split_report"]["grouping"]["same_repo_in_multiple_splits"] is False


def test_split_manifest_includes_every_example_once_and_counts_balance(tmp_path: Path) -> None:
    examples = _synthetic_examples()
    result = _run(tmp_path)
    manifest = result["split_manifest"]
    report = result["split_report"]
    assignment_ids = [item["example_id"] for item in manifest["assignments"]]

    assert len(assignment_ids) == len(examples)
    assert len(set(assignment_ids)) == len(examples)
    assert report["counts"]["examples"] == len(examples)
    assert report["counts"]["assigned_once"] is True

    expected_resolved = sum(1 for example in examples if example["target"]["resolved"])
    expected_unresolved = len(examples) - expected_resolved
    observed_resolved = sum(
        split_count["resolved"] for split_count in report["split_counts"].values()
    )
    observed_unresolved = sum(
        split_count["unresolved"] for split_count in report["split_counts"].values()
    )

    assert observed_resolved == expected_resolved
    assert observed_unresolved == expected_unresolved
    assert report["class_balance"]["resolved"] == expected_resolved
    assert report["class_balance"]["unresolved"] == expected_unresolved
    assert any("target ratio" in caveat for caveat in report["caveats"])


def test_invalid_ratio_sum_fails(tmp_path: Path) -> None:
    input_path = tmp_path / "examples.jsonl"
    _write_examples(input_path, _synthetic_examples())
    output, report, hash_manifest = _output_paths(tmp_path)

    with pytest.raises(ValueError, match="sum to 1.0"):
        splits.run_split_generation(
            input_path=input_path,
            output_path=output,
            report_path=report,
            hash_manifest_path=hash_manifest,
            dataset_id=DATASET_ID,
            train_ratio=0.60,
            validation_ratio=0.30,
            test_ratio=0.30,
        )


def test_output_under_pneuma_data_is_rejected(tmp_path: Path) -> None:
    input_path = tmp_path / "examples.jsonl"
    _write_examples(input_path, _synthetic_examples())
    _, report, hash_manifest = _output_paths(tmp_path)

    with pytest.raises(ValueError, match="pneuma-data"):
        splits.run_split_generation(
            input_path=input_path,
            output_path="C:/pneuma-data/processed/splits/split_manifest.json",
            report_path=report,
            hash_manifest_path=hash_manifest,
            dataset_id=DATASET_ID,
        )


def test_wrong_dataset_id_fails(tmp_path: Path) -> None:
    input_path = tmp_path / "examples.jsonl"
    examples = _synthetic_examples()
    examples[0]["dataset_id"] = "wrong-dataset"
    _write_examples(input_path, examples)
    output, report, hash_manifest = _output_paths(tmp_path)

    with pytest.raises(ValueError, match="expected"):
        splits.run_split_generation(
            input_path=input_path,
            output_path=output,
            report_path=report,
            hash_manifest_path=hash_manifest,
            dataset_id=DATASET_ID,
        )


def test_missing_split_group_repo_fails_clearly(tmp_path: Path) -> None:
    input_path = tmp_path / "examples.jsonl"
    examples = _synthetic_examples()
    examples[0]["split_group"]["repo"] = None
    _write_examples(input_path, examples)
    output, report, hash_manifest = _output_paths(tmp_path)

    with pytest.raises(ValueError, match="split_group.repo"):
        splits.run_split_generation(
            input_path=input_path,
            output_path=output,
            report_path=report,
            hash_manifest_path=hash_manifest,
            dataset_id=DATASET_ID,
        )


def test_hash_manifest_is_recomputable(tmp_path: Path) -> None:
    input_path = tmp_path / "examples.jsonl"
    _write_examples(input_path, _synthetic_examples())
    output, report, hash_manifest = _output_paths(tmp_path)

    result = splits.run_split_generation(
        input_path=input_path,
        output_path=output,
        report_path=report,
        hash_manifest_path=hash_manifest,
        dataset_id=DATASET_ID,
    )
    manifest = json.loads(hash_manifest.read_text(encoding="utf-8"))

    assert manifest == result["hash_manifest"]
    assert manifest["hashes"]["split_manifest_json_sha256"] == hashlib.sha256(
        output.read_bytes()
    ).hexdigest()
    assert manifest["hashes"]["split_report_json_sha256"] == hashlib.sha256(
        report.read_bytes()
    ).hexdigest()
    assert manifest["hashes"]["hash_manifest_json_sha256"] == _manifest_self_hash(
        manifest
    )


def test_split_tests_use_synthetic_examples_only(tmp_path: Path) -> None:
    input_path = tmp_path / "examples.jsonl"
    _write_examples(input_path, _synthetic_examples())

    assert "C:/pneuma-data" not in str(input_path)
    assert "C:\\pneuma-data" not in str(input_path)

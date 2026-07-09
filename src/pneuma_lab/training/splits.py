"""Deterministic split manifests for converted training examples.

This module consumes already-converted ``PneumaTrainingExample`` JSONL records.
It does not read raw datasets, train models, run E1/E2, calibrate, mutate
processed data, or authorize training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Iterable
from pathlib import Path

SPLIT_MANIFEST_SCHEMA_VERSION = "0.1.0"
SPLIT_REPORT_SCHEMA_VERSION = "0.1.0"
HASH_MANIFEST_SCHEMA_VERSION = "0.1.0"
SPLIT_GENERATOR_VERSION = "pneuma-training-splits/0.1.0"
DEFAULT_POLICY = "repo_grouped"
DEFAULT_TRAIN_RATIO = 0.70
DEFAULT_VALIDATION_RATIO = 0.15
DEFAULT_TEST_RATIO = 0.15
FORBIDDEN_OUTPUT_ROOT = Path("C:/pneuma-data")
SPLITS = ("train", "validation", "test")


def _canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_text(value: dict) -> str:
    return _canonical_json(value) + "\n"


def reject_forbidden_output_path(path: str | os.PathLike[str]) -> None:
    resolved = Path(path).resolve()
    forbidden = FORBIDDEN_OUTPUT_ROOT.resolve()
    if resolved == forbidden or forbidden in resolved.parents:
        raise ValueError(f"refusing to write split output under {FORBIDDEN_OUTPUT_ROOT}")
    if resolved.name == "build" or not any(part.lower() == "build" for part in resolved.parts):
        raise ValueError("refusing to write split output outside a build/ directory")


def validate_ratios(train_ratio: float, validation_ratio: float, test_ratio: float) -> dict[str, float]:
    ratios = {
        "train": train_ratio,
        "validation": validation_ratio,
        "test": test_ratio,
    }
    for name, value in ratios.items():
        if value < 0:
            raise ValueError(f"{name} ratio must be non-negative")
    total = sum(ratios.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError("split ratios must sum to 1.0")
    return ratios


def load_examples_jsonl(path: str | os.PathLike[str], *, dataset_id: str) -> list[dict]:
    examples: list[dict] = []
    seen: set[str] = set()
    with open(path, encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            example = json.loads(line)
            if example.get("dataset_id") != dataset_id:
                raise ValueError(
                    f"line {line_number} has dataset_id {example.get('dataset_id')!r}, "
                    f"expected {dataset_id!r}"
                )
            example_id = example.get("example_id")
            if not isinstance(example_id, str) or not example_id:
                raise ValueError(f"line {line_number} is missing example_id")
            if example_id in seen:
                raise ValueError(f"duplicate example_id: {example_id}")
            seen.add(example_id)
            examples.append(example)
    if not examples:
        raise ValueError("no examples loaded")
    return examples


def _required_split_group(example: dict) -> tuple[str, str | None]:
    group = example.get("split_group") or {}
    repo = group.get("repo")
    if not isinstance(repo, str) or not repo:
        raise ValueError(f"example {example.get('example_id')} is missing split_group.repo")
    task_id = group.get("task_id")
    if task_id is not None and not isinstance(task_id, str):
        raise ValueError(f"example {example.get('example_id')} has non-string task_id")
    return repo, task_id


def _resolved(example: dict) -> bool:
    target = example.get("target") or {}
    value = target.get("resolved")
    if value is True:
        return True
    if value is False:
        return False
    raise ValueError(f"example {example.get('example_id')} is missing boolean target.resolved")


def _group_examples(examples: Iterable[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for example in examples:
        repo, _ = _required_split_group(example)
        groups.setdefault(repo, []).append(example)
    for repo in groups:
        groups[repo] = sorted(groups[repo], key=lambda item: item["example_id"])
    return dict(sorted(groups.items()))


def _group_order_key(dataset_id: str, repo: str) -> str:
    return hashlib.sha256(f"{dataset_id}|repo|{repo}".encode("utf-8")).hexdigest()


def _target_counts(total: int, ratios: dict[str, float]) -> dict[str, int]:
    train_target = round(total * ratios["train"])
    validation_target = round(total * ratios["validation"])
    test_target = total - train_target - validation_target
    return {
        "train": train_target,
        "validation": validation_target,
        "test": test_target,
    }


def _assign_groups(
    *,
    dataset_id: str,
    groups: dict[str, list[dict]],
    ratios: dict[str, float],
) -> dict[str, str]:
    total = sum(len(items) for items in groups.values())
    targets = _target_counts(total, ratios)
    counts = {split: 0 for split in SPLITS}
    assignments: dict[str, str] = {}
    ordered_repos = sorted(groups, key=lambda repo: (_group_order_key(dataset_id, repo), repo))

    for repo in ordered_repos:
        group_size = len(groups[repo])
        best_split = min(
            SPLITS,
            key=lambda split: (
                counts[split] + group_size - targets[split],
                abs((counts[split] + group_size) - targets[split]),
                SPLITS.index(split),
            ),
        )
        assignments[repo] = best_split
        counts[best_split] += group_size
    return assignments


def _empty_split_counts() -> dict[str, dict]:
    return {
        split: {
            "examples": 0,
            "resolved": 0,
            "unresolved": 0,
            "resolved_rate": None,
            "repos": 0,
            "tasks": 0,
        }
        for split in SPLITS
    }


def _split_counts(assignments: list[dict]) -> dict[str, dict]:
    counts = _empty_split_counts()
    repos: dict[str, set[str]] = {split: set() for split in SPLITS}
    tasks: dict[str, set[str]] = {split: set() for split in SPLITS}
    for assignment in assignments:
        split = assignment["split"]
        counts[split]["examples"] += 1
        if assignment["resolved"]:
            counts[split]["resolved"] += 1
        else:
            counts[split]["unresolved"] += 1
        repos[split].add(assignment["repo"])
        if assignment.get("task_id"):
            tasks[split].add(assignment["task_id"])
    for split in SPLITS:
        examples = counts[split]["examples"]
        counts[split]["repos"] = len(repos[split])
        counts[split]["tasks"] = len(tasks[split])
        if examples:
            counts[split]["resolved_rate"] = counts[split]["resolved"] / examples
    return counts


def _repo_overlap(assignments: list[dict]) -> dict[str, list[str]]:
    repo_splits: dict[str, set[str]] = {}
    for assignment in assignments:
        repo_splits.setdefault(assignment["repo"], set()).add(assignment["split"])
    return {
        repo: sorted(splits)
        for repo, splits in sorted(repo_splits.items())
        if len(splits) > 1
    }


def _group_stats(groups: dict[str, list[dict]], repo_assignments: dict[str, str]) -> dict:
    sizes = [len(items) for items in groups.values()]
    largest_repo = max(sizes) if sizes else 0
    return {
        "group_field": "split_group.repo",
        "repo_groups": len(groups),
        "largest_repo_examples": largest_repo,
        "largest_repo_fraction": largest_repo / sum(sizes) if sizes else None,
        "assignments_by_repo": {
            repo: {
                "split": repo_assignments[repo],
                "examples": len(items),
                "resolved": sum(1 for item in items if _resolved(item)),
                "unresolved": sum(1 for item in items if not _resolved(item)),
            }
            for repo, items in sorted(groups.items())
        },
    }


def _caveats(
    *,
    total: int,
    groups: dict[str, list[dict]],
    split_counts: dict[str, dict],
    repo_overlap: dict[str, list[str]],
    targets: dict[str, int],
) -> list[str]:
    caveats: list[str] = []
    if len(groups) < len(SPLITS):
        caveats.append("repo groups are fewer than requested splits; some splits may be empty")
    if repo_overlap:
        caveats.append("at least one repo appears in multiple splits")
    largest_group = max((len(items) for items in groups.values()), default=0)
    if total and largest_group / total > 0.25:
        caveats.append("largest repo group is large enough to make target ratios imperfect")
    for split in SPLITS:
        observed = split_counts[split]["examples"]
        target = targets[split]
        if total and abs(observed - target) / total > 0.05:
            caveats.append(f"{split} split count differs from target ratio by more than 5 percent")
    if any(split_counts[split]["resolved"] == 0 for split in SPLITS if split_counts[split]["examples"]):
        caveats.append("one or more non-empty splits has zero resolved examples")
    caveats.append("split assignment did not use outcome labels except for post-hoc balance reporting")
    caveats.append("split manifest is readiness infrastructure only and does not authorize training")
    return caveats


def build_split_artifacts(
    *,
    examples: list[dict],
    dataset_id: str,
    policy: str,
    ratios: dict[str, float],
    input_path: str | os.PathLike[str],
) -> tuple[dict, dict]:
    if policy != DEFAULT_POLICY:
        raise ValueError(f"unsupported split policy: {policy}")
    groups = _group_examples(examples)
    repo_assignments = _assign_groups(
        dataset_id=dataset_id,
        groups=groups,
        ratios=ratios,
    )
    assignments: list[dict] = []
    for repo, group_examples in groups.items():
        split = repo_assignments[repo]
        for example in group_examples:
            _, task_id = _required_split_group(example)
            assignments.append(
                {
                    "example_id": example["example_id"],
                    "split": split,
                    "repo": repo,
                    "task_id": task_id,
                    "resolved": _resolved(example),
                }
            )
    assignments = sorted(assignments, key=lambda item: item["example_id"])
    manifest_assignments = [
        {
            "example_id": item["example_id"],
            "split": item["split"],
            "repo": item["repo"],
            "task_id": item["task_id"],
        }
        for item in assignments
    ]
    split_counts = _split_counts(assignments)
    total = len(assignments)
    targets = _target_counts(total, ratios)
    repo_overlap = _repo_overlap(assignments)
    source_file_sha256 = _sha256_file(input_path)
    manifest = {
        "split_manifest_schema_version": SPLIT_MANIFEST_SCHEMA_VERSION,
        "generator_version": SPLIT_GENERATOR_VERSION,
        "dataset_id": dataset_id,
        "policy": policy,
        "ratios": ratios,
        "source": {
            "examples_jsonl": str(input_path),
            "examples_jsonl_sha256": source_file_sha256,
        },
        "counts": {
            "examples": total,
            "assignments": len(manifest_assignments),
            "repo_groups": len(groups),
        },
        "split_counts": split_counts,
        "assignments": manifest_assignments,
    }
    report = {
        "split_report_schema_version": SPLIT_REPORT_SCHEMA_VERSION,
        "generator_version": SPLIT_GENERATOR_VERSION,
        "dataset_id": dataset_id,
        "policy": policy,
        "ratios": ratios,
        "target_counts": targets,
        "counts": {
            "examples": total,
            "assigned_once": len({item["example_id"] for item in assignments}) == total,
            "repo_groups": len(groups),
        },
        "split_counts": split_counts,
        "class_balance": {
            "resolved": sum(1 for item in assignments if item["resolved"]),
            "unresolved": sum(1 for item in assignments if not item["resolved"]),
            "resolved_rate": (
                sum(1 for item in assignments if item["resolved"]) / total
                if total
                else None
            ),
        },
        "grouping": {
            "repo_overlap": repo_overlap,
            "same_repo_in_multiple_splits": bool(repo_overlap),
            **_group_stats(groups, repo_assignments),
        },
        "source_hashes": {
            "examples_jsonl_sha256": source_file_sha256,
        },
        "caveats": _caveats(
            total=total,
            groups=groups,
            split_counts=split_counts,
            repo_overlap=repo_overlap,
            targets=targets,
        ),
        "training_authorization": {
            "status": "not_authorized",
            "training_weight": 0.0,
        },
    }
    return manifest, report


def build_hash_manifest(
    *,
    split_manifest_text: str,
    split_report_text: str,
    input_path: str | os.PathLike[str],
    dataset_id: str,
) -> dict:
    return {
        "hash_manifest_schema_version": HASH_MANIFEST_SCHEMA_VERSION,
        "generator_version": SPLIT_GENERATOR_VERSION,
        "dataset_id": dataset_id,
        "hash_manifest_hash_convention": (
            "hash_manifest_json_sha256 is the sha256 of canonical manifest JSON "
            "with hashes.hash_manifest_json_sha256 set to null"
        ),
        "source": {
            "examples_jsonl": str(input_path),
            "examples_jsonl_sha256": _sha256_file(input_path),
        },
        "hashes": {
            "split_manifest_json_sha256": _sha256_text(split_manifest_text),
            "split_report_json_sha256": _sha256_text(split_report_text),
            "hash_manifest_json_sha256": None,
        },
    }


def _write_atomic(path: str | os.PathLike[str], text: str) -> None:
    reject_forbidden_output_path(path)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, target)


def run_split_generation(
    *,
    input_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
    report_path: str | os.PathLike[str],
    hash_manifest_path: str | os.PathLike[str],
    dataset_id: str,
    policy: str = DEFAULT_POLICY,
    train_ratio: float = DEFAULT_TRAIN_RATIO,
    validation_ratio: float = DEFAULT_VALIDATION_RATIO,
    test_ratio: float = DEFAULT_TEST_RATIO,
) -> dict:
    ratios = validate_ratios(train_ratio, validation_ratio, test_ratio)
    for path in (output_path, report_path, hash_manifest_path):
        reject_forbidden_output_path(path)
    examples = load_examples_jsonl(input_path, dataset_id=dataset_id)
    manifest, report = build_split_artifacts(
        examples=examples,
        dataset_id=dataset_id,
        policy=policy,
        ratios=ratios,
        input_path=input_path,
    )
    manifest_text = _json_text(manifest)
    report_text = _json_text(report)
    hash_manifest = build_hash_manifest(
        split_manifest_text=manifest_text,
        split_report_text=report_text,
        input_path=input_path,
        dataset_id=dataset_id,
    )
    hash_manifest["hashes"]["hash_manifest_json_sha256"] = _sha256_text(
        _json_text(hash_manifest)
    )
    hash_manifest_text = _json_text(hash_manifest)

    _write_atomic(output_path, manifest_text)
    _write_atomic(report_path, report_text)
    _write_atomic(hash_manifest_path, hash_manifest_text)

    return {
        "split_manifest": manifest,
        "split_report": report,
        "hash_manifest": hash_manifest,
        "paths": {
            "split_manifest": str(output_path),
            "split_report": str(report_path),
            "hash_manifest": str(hash_manifest_path),
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m pneuma_lab.training.splits")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--hash-manifest", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--policy", default=DEFAULT_POLICY)
    parser.add_argument("--train-ratio", type=float, default=DEFAULT_TRAIN_RATIO)
    parser.add_argument("--validation-ratio", type=float, default=DEFAULT_VALIDATION_RATIO)
    parser.add_argument("--test-ratio", type=float, default=DEFAULT_TEST_RATIO)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = run_split_generation(
            input_path=args.input,
            output_path=args.output,
            report_path=args.report,
            hash_manifest_path=args.hash_manifest,
            dataset_id=args.dataset_id,
            policy=args.policy,
            train_ratio=args.train_ratio,
            validation_ratio=args.validation_ratio,
            test_ratio=args.test_ratio,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    report = result["split_report"]
    print(
        f"wrote split manifest for {report['counts']['examples']} examples to "
        f"{result['paths']['split_manifest']}"
    )
    return 0


__all__ = [
    "DEFAULT_POLICY",
    "SPLIT_GENERATOR_VERSION",
    "build_hash_manifest",
    "build_split_artifacts",
    "load_examples_jsonl",
    "main",
    "run_split_generation",
    "validate_ratios",
]


if __name__ == "__main__":
    raise SystemExit(main())

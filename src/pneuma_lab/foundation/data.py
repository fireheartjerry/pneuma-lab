"""Immutable, authorized, content-addressed local training shard utilities."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Iterable, Mapping


ACTIVE_DATASET_GROUPS = (
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


class DataAuthorizationError(ValueError):
    """Raised before writing when data role or path policy is violated."""


@dataclass(frozen=True)
class DatasetRole:
    dataset_group: str
    training_authorized: bool
    lane_ids: tuple[str, ...]
    readiness: tuple[str, ...]


@dataclass(frozen=True)
class ShardResult:
    shard_path: Path
    manifest_path: Path
    sha256: str
    example_count: int
    duplicate_ids: tuple[str, ...]


def governed_dataset_groups(registry: Mapping) -> dict[str, DatasetRole]:
    lanes = registry.get("lanes")
    if not isinstance(lanes, list):
        raise DataAuthorizationError("dataset registry must contain a lanes list")
    result: dict[str, DatasetRole] = {}
    for group in ACTIVE_DATASET_GROUPS:
        matches = [lane for lane in lanes if lane.get("source_family") == group]
        if not matches:
            raise DataAuthorizationError(f"active dataset group is ungoverned: {group}")
        result[group] = DatasetRole(
            dataset_group=group,
            training_authorized=any(
                bool((lane.get("authorization") or {}).get("training_authorized"))
                for lane in matches
            ),
            lane_ids=tuple(sorted(str(lane.get("lane_id")) for lane in matches)),
            readiness=tuple(
                sorted({str(lane.get("training_readiness")) for lane in matches})
            ),
        )
    return result


def _normalized_text(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def _digest(value: object) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def dedup_fingerprint(example: Mapping) -> str:
    canonical = {
        "repo": _normalized_text(example.get("repo")),
        "issue_or_pr": _normalized_text(example.get("issue_or_pr")),
        "task_id": _normalized_text(example.get("task_id")),
        "base_commit": _normalized_text(example.get("base_commit")),
        "patch_sha256": _digest(example.get("patch")),
        "test_patch_sha256": _digest(example.get("test_patch")),
        "fuzzy_text_sha256": _digest(_normalized_text(example.get("text"))),
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def deduplicate_examples(
    examples: Iterable[Mapping],
) -> tuple[list[dict], tuple[str, ...]]:
    seen: set[str] = set()
    unique: list[dict] = []
    duplicate_ids: list[str] = []
    for example in examples:
        fingerprint = dedup_fingerprint(example)
        if fingerprint in seen:
            duplicate_ids.append(str(example.get("example_id", "<missing>")))
            continue
        seen.add(fingerprint)
        unique.append(dict(example))
    return unique, tuple(duplicate_ids)


def build_diversity_inventory(examples: Iterable[Mapping]) -> dict:
    values = tuple(examples)
    languages: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    repos: set[str] = set()
    issues: set[tuple[str, str]] = set()
    lengths: list[int] = []
    token_count = 0
    for example in values:
        repo = str(example.get("repo") or "unknown")
        issue = str(example.get("issue_or_pr") or example.get("task_id") or "unknown")
        repos.add(repo)
        issues.add((repo, issue))
        languages[str(example.get("language") or "unknown")] += 1
        for tool in example.get("tools") or ():
            tools[str(tool)] += 1
        labels[str(example.get("label") or "unknown")] += 1
        lengths.append(int(example.get("trajectory_length") or 0))
        token_count += len(re.findall(r"\S+", str(example.get("text") or "")))
    return {
        "example_count": len(values),
        "token_count": token_count,
        "repository_count": len(repos),
        "issue_count": len(issues),
        "languages": dict(sorted(languages.items())),
        "tools": dict(sorted(tools.items())),
        "trajectory_length": {
            "min": min(lengths, default=0),
            "max": max(lengths, default=0),
            "mean": fmean(lengths) if lengths else 0.0,
        },
        "labels": dict(sorted(labels.items())),
    }


def _is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _validate_output_path(
    *, repo_root: Path, output_root: Path, data_root: Path
) -> None:
    output = output_root.resolve()
    data = data_root.resolve()
    build = (repo_root.resolve() / "build").resolve()
    if _is_within(output, data):
        raise DataAuthorizationError("output may never be written under pneuma-data")
    if not _is_within(output, build):
        raise DataAuthorizationError(
            "training shards must remain under repo build storage"
        )


def _validate_example(example: Mapping) -> None:
    group = str(example.get("dataset_group") or "")
    if group not in ACTIVE_DATASET_GROUPS:
        raise DataAuthorizationError(f"unknown active dataset group: {group!r}")
    weight = float(example.get("training_weight") or 0.0)
    authorization = str(example.get("training_authorization") or "blocked")
    if authorization != "authorized" and weight > 0.0:
        raise DataAuthorizationError(
            f"blocked/eval/privacy dataset {group} must remain zero-weight"
        )
    if group == "sec-bench-pro" and (
        example.get("functioning_exploit") or example.get("execution_requested")
    ):
        raise DataAuthorizationError(
            "security governance forbids functioning exploit generation or execution"
        )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def build_content_addressed_shard(
    examples: Iterable[Mapping],
    *,
    repo_root: Path,
    output_root: Path,
    data_root: Path,
) -> ShardResult:
    """Build one deterministic shard without ever mutating the corpus root."""

    repo_root = Path(repo_root)
    output_root = Path(output_root)
    data_root = Path(data_root)
    _validate_output_path(
        repo_root=repo_root,
        output_root=output_root,
        data_root=data_root,
    )
    values = tuple(dict(example) for example in examples)
    for example in values:
        _validate_example(example)
    unique, duplicate_ids = deduplicate_examples(values)
    lines = [
        json.dumps(example, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        for example in unique
    ]
    payload = (("\n".join(lines) + "\n") if lines else "").encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    shard_path = output_root / f"{digest}.jsonl"
    manifest_path = output_root / f"{digest}.manifest.json"
    manifest = {
        "manifest_kind": "pneuma_foundation_shard",
        "schema_version": "0.1.0",
        "sha256": digest,
        "example_count": len(unique),
        "duplicate_example_ids": list(duplicate_ids),
        "inventory": build_diversity_inventory(unique),
        "source_policy": "read_only_external_corpus",
    }
    _write_atomic(shard_path, payload)
    _write_atomic(
        manifest_path,
        (json.dumps(manifest, indent=4, sort_keys=True) + "\n").encode("utf-8"),
    )
    return ShardResult(
        shard_path=shard_path,
        manifest_path=manifest_path,
        sha256=digest,
        example_count=len(unique),
        duplicate_ids=duplicate_ids,
    )

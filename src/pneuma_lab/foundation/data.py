"""Immutable, authorized, content-addressed local training shard utilities."""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat as stat_module
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Iterable, Mapping

from pneuma_lab.foundation.artifacts import (
    ArtifactPublicationError,
    bind_artifact_publication,
    write_atomic_bytes,
    write_atomic_json,
)
from pneuma_lab.foundation.eval_identities import (
    IdentityRecordError,
    identity_from_foundation_record,
)
from pneuma_lab.foundation.identity_normalization import (
    normalize_identity_digest,
    normalize_identity_text,
)
from pneuma_lab.foundation.records import (
    FoundationRecordError,
    validate_foundation_record,
)


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
    try:
        return normalize_identity_text(value) or ""
    except TypeError:
        raise DataAuthorizationError("identity values must be strings or null")


def _digest(value: str | None) -> str | None:
    return normalize_identity_digest(value)


def dedup_fingerprint(example: Mapping) -> str:
    _validate_example(example)
    try:
        identity = identity_from_foundation_record(example)
    except IdentityRecordError as exc:
        raise DataAuthorizationError(f"invalid foundation identity: {exc}") from exc
    canonical = {
        "repo": _normalized_text(identity.repo),
        "issue_or_pr": _normalized_text(identity.issue_or_pr),
        "task_id": _normalized_text(identity.task_id),
        "base_commit": _normalized_text(identity.base_commit),
        "patch_sha256": _digest(identity.patch_sha256),
        "test_patch_sha256": _digest(identity.test_patch_sha256),
        "fuzzy_text_sha256": _digest(identity.fuzzy_text_sha256),
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
            source = example.get("source")
            source_id = (
                source.get("source_record_id")
                if isinstance(source, Mapping)
                else None
            )
            duplicate_ids.append(
                source_id if isinstance(source_id, str) else "<missing>"
            )
            continue
        seen.add(fingerprint)
        unique.append(dict(example))
    return unique, tuple(duplicate_ids)


def build_diversity_inventory(examples: Iterable[Mapping]) -> dict:
    values = tuple(examples)
    dataset_families: Counter[str] = Counter()
    lanes: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    forecast_targets: Counter[str] = Counter()
    repos: set[str] = set()
    issues: set[tuple[str, str]] = set()
    lengths: list[int] = []
    token_count = 0
    for example in values:
        _validate_example(example)
        source = example["source"]
        identity = example["identity"]
        tokenization = example["tokenization"]
        observations = example["observations"]
        targets = example["forecast_targets"]
        dataset_families[source["dataset_family"]] += 1
        lanes[source["lane_id"]] += 1
        repo = normalize_identity_text(identity["repo"]) or "unknown"
        issue = (
            normalize_identity_text(identity["issue_or_pr"])
            or normalize_identity_text(identity["task_id"])
            or "unknown"
        )
        repos.add(repo)
        issues.add((repo, issue))
        languages[observations["language"]] += 1
        for tool in observations["tools"]:
            tools[tool] += 1
        labels[
            "resolved" if observations["labels"]["resolved"] else "unresolved"
        ] += 1
        lengths.append(observations["trajectory_length"])
        token_count += tokenization["total_tokens"]
        for name, target in targets.items():
            if target["applicable"]:
                forecast_targets[name] += 1
    return {
        "example_count": len(values),
        "token_count": token_count,
        "repository_count": len(repos),
        "issue_count": len(issues),
        "dataset_families": dict(sorted(dataset_families.items())),
        "lanes": dict(sorted(lanes.items())),
        "languages": dict(sorted(languages.items())),
        "tools": dict(sorted(tools.items())),
        "trajectory_length": {
            "min": min(lengths, default=0),
            "max": max(lengths, default=0),
            "mean": fmean(lengths) if lengths else 0.0,
        },
        "labels": dict(sorted(labels.items())),
        "forecast_targets": dict(sorted(forecast_targets.items())),
    }


def _is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _validate_output_path(
    *, repo_root: Path, output_root: Path, data_root: Path
) -> None:
    repo = Path(repo_root)
    output = Path(output_root)
    data = Path(data_root)
    if ".." in repo.parts or ".." in output.parts:
        raise DataAuthorizationError(
            "training shards must remain lexically under repo build storage"
        )
    if not repo.is_absolute():
        repo = Path.cwd() / repo
    if not output.is_absolute():
        output = Path.cwd() / output
    if not data.is_absolute():
        data = Path.cwd() / data
    try:
        resolved_data = data.resolve(strict=False)
        resolved_output_for_data = output.resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise DataAuthorizationError(
            "training shard storage paths cannot be resolved"
        ) from exc
    if _is_within(resolved_output_for_data, resolved_data):
        raise DataAuthorizationError("output may never be written under pneuma-data")
    build = repo / "build"
    try:
        relative_output = output.relative_to(build)
    except ValueError as exc:
        raise DataAuthorizationError(
            "training shards must remain lexically under repo build storage"
        ) from exc

    components = [repo, build]
    current = build
    for part in relative_output.parts:
        current /= part
        components.append(current)
    for component in components:
        try:
            metadata = component.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise DataAuthorizationError(
                f"build storage metadata cannot be inspected: {component}"
            ) from exc
        is_junction = getattr(component, "is_junction", None)
        try:
            junction = bool(callable(is_junction) and is_junction())
        except OSError as exc:
            raise DataAuthorizationError(
                f"build storage junction cannot be inspected: {component}"
            ) from exc
        reparse_flag = getattr(
            stat_module,
            "FILE_ATTRIBUTE_REPARSE_POINT",
            0x400,
        )
        if (
            stat_module.S_ISLNK(metadata.st_mode)
            or junction
            or bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)
        ):
            raise DataAuthorizationError(
                f"build storage contains a link, junction, or reparse point: {component}"
            )
        if not stat_module.S_ISDIR(metadata.st_mode):
            raise DataAuthorizationError(
                f"build storage component must be a directory: {component}"
            )

    try:
        resolved_repo = repo.resolve(strict=False)
        resolved_build = build.resolve(strict=False)
        resolved_output = output.resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise DataAuthorizationError(
            "training shard storage paths cannot be resolved"
        ) from exc
    if (
        not _is_within(resolved_build, resolved_repo)
        or not _is_within(resolved_output, resolved_build)
    ):
        raise DataAuthorizationError(
            "training shards must remain under repo build storage"
        )


def _validate_example(example: Mapping) -> None:
    if not isinstance(example, Mapping):
        raise DataAuthorizationError("foundation record must be a mapping")
    training_weight = example.get("training_weight")
    if (
        type(training_weight) is not float
        or training_weight != 0.0
        or math.copysign(1.0, training_weight) < 0.0
    ):
        raise DataAuthorizationError(
            "persisted foundation records must remain exact zero-weight"
        )
    source = example.get("source")
    if not isinstance(source, Mapping):
        raise DataAuthorizationError("foundation record source must be a mapping")
    group = source.get("dataset_family")
    if group not in ACTIVE_DATASET_GROUPS:
        raise DataAuthorizationError(f"unknown active dataset group: {group!r}")
    try:
        validate_foundation_record(example)
    except FoundationRecordError as exc:
        raise DataAuthorizationError(str(exc)) from exc


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
    values = []
    for example in examples:
        _validate_example(example)
        values.append(dict(example))
    values = tuple(values)
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
    try:
        with bind_artifact_publication(
            output_root,
            anchor_root=repo_root,
            allowed_root=repo_root / "build",
            forbidden_roots=(data_root,),
        ) as publication:
            write_atomic_bytes(
                shard_path,
                payload,
                publication=publication,
            )
            write_atomic_json(
                manifest_path,
                manifest,
                publication=publication,
            )
    except ArtifactPublicationError as exc:
        raise DataAuthorizationError(
            f"training shard output publication failed: {exc}"
        ) from exc
    return ShardResult(
        shard_path=shard_path,
        manifest_path=manifest_path,
        sha256=digest,
        example_count=len(unique),
        duplicate_ids=duplicate_ids,
    )

"""Cross-split contamination checks beyond label-level separation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Mapping

from pneuma_lab.foundation.eval_identities import (
    ContaminationIndexError,
    IdentityRecord,
)
from pneuma_lab.foundation.identity_normalization import (
    normalize_identity_digest,
    normalize_identity_text,
)


@dataclass(frozen=True)
class ContaminationFinding:
    dimension: str
    value: str


@dataclass(frozen=True)
class _NormalizedIdentity:
    family: str
    lane_id: str
    values: tuple[tuple[str, str | None], ...]
    sort_key: tuple[str, ...]


def _norm(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def _digest(value: object) -> str:
    normalized = _norm(value)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""


def _dimensions(record: Mapping) -> dict[str, str]:
    repo = _norm(record.get("repo"))
    issue = _norm(record.get("issue_or_pr"))
    return {
        "repo": repo,
        "repo_issue_or_pr": f"{repo}#{issue}" if repo and issue else "",
        "task": _norm(record.get("task_id")),
        "base_commit": _norm(record.get("base_commit")),
        "patch": _digest(record.get("patch")),
        "test_patch": _digest(record.get("test_patch")),
        "fuzzy_text": _digest(record.get("text")),
    }


def contamination_findings(
    training_records: Iterable[Mapping],
    evaluation_records: Iterable[Mapping],
) -> tuple[ContaminationFinding, ...]:
    train_values: dict[str, set[str]] = {}
    eval_values: dict[str, set[str]] = {}
    for record in training_records:
        for dimension, value in _dimensions(record).items():
            if value:
                train_values.setdefault(dimension, set()).add(value)
    for record in evaluation_records:
        for dimension, value in _dimensions(record).items():
            if value:
                eval_values.setdefault(dimension, set()).add(value)
    findings = []
    for dimension in sorted(set(train_values) | set(eval_values)):
        for value in sorted(
            train_values.get(dimension, set()) & eval_values.get(dimension, set())
        ):
            findings.append(ContaminationFinding(dimension=dimension, value=value))
    return tuple(findings)


def _identity_value(value: str | None) -> str | None:
    return normalize_identity_text(value)


def _normalize_identity(identity: IdentityRecord) -> _NormalizedIdentity:
    repo = _identity_value(identity.repo)
    issue = _identity_value(identity.issue_or_pr)
    task = _identity_value(identity.task_id)
    base_commit = _identity_value(identity.base_commit)
    patch = normalize_identity_digest(identity.patch_sha256)
    test_patch = normalize_identity_digest(identity.test_patch_sha256)
    fuzzy_text = normalize_identity_digest(identity.fuzzy_text_sha256)
    values = (
        ("repository", repo),
        (
            "repo_issue_or_pr",
            f"{repo}#{issue}" if repo is not None and issue is not None else None,
        ),
        ("task", task),
        ("base_commit", base_commit),
        ("patch", patch),
        ("test_patch", test_patch),
        ("fuzzy_text", fuzzy_text),
    )
    return _NormalizedIdentity(
        family=identity.family,
        lane_id=identity.lane_id,
        values=values,
        sort_key=(
            identity.family,
            identity.lane_id,
            repo or "",
            issue or "",
            task or "",
            base_commit or "",
            patch or "",
            test_patch or "",
            fuzzy_text or "",
        ),
    )


def build_contamination_receipt(
    training: Iterable[IdentityRecord],
    evaluation: Iterable[IdentityRecord],
    *,
    suite_policy: Mapping,
) -> dict:
    """Compare every canonical training/evaluation identity pair."""

    training_values = tuple(training)
    evaluation_values = tuple(evaluation)
    if not all(isinstance(value, IdentityRecord) for value in training_values):
        raise TypeError("training identities must be IdentityRecord values")
    if not all(isinstance(value, IdentityRecord) for value in evaluation_values):
        raise TypeError("evaluation identities must be IdentityRecord values")
    from pneuma_lab.foundation.suite import (
        SuitePolicyError,
        evaluation_identity_scope,
    )

    try:
        required_families, blocked_families = evaluation_identity_scope(
            suite_policy
        )
    except SuitePolicyError as exc:
        raise ContaminationIndexError(
            f"suite evaluation identity policy is invalid: {exc}"
        ) from exc
    family_counts = {
        family: sum(
            identity.family == family for identity in evaluation_values
        )
        for family in required_families
    }
    evaluation_families = {identity.family for identity in evaluation_values}
    if evaluation_families != set(required_families) or not all(
        family_counts.values()
    ):
        raise ContaminationIndexError(
            "evaluation families must contain at least one identity for every "
            "required family and no extra or blocked families"
        )
    normalized_training = tuple(
        _normalize_identity(identity) for identity in training_values
    )
    normalized_evaluation = tuple(
        _normalize_identity(identity) for identity in evaluation_values
    )
    evaluation_index: dict[str, dict[str, set[int]]] = {}
    for index, identity in enumerate(normalized_evaluation):
        for dimension, value in identity.values:
            if value is not None:
                evaluation_index.setdefault(dimension, {}).setdefault(
                    value,
                    set(),
                ).add(index)

    sortable_findings = []
    for training_identity in normalized_training:
        candidate_indices: set[int] = set()
        for dimension, value in training_identity.values:
            if value is not None:
                candidate_indices.update(
                    evaluation_index.get(dimension, {}).get(value, ())
                )
        for index in candidate_indices:
            evaluation_identity = normalized_evaluation[index]
            evaluation_dimensions = dict(evaluation_identity.values)
            dimensions = [
                dimension
                for dimension, value in training_identity.values
                if value is not None and value == evaluation_dimensions[dimension]
            ]
            if dimensions:
                sortable_findings.append(
                    (
                        training_identity.sort_key,
                        evaluation_identity.sort_key,
                        {
                            "training_lane": training_identity.lane_id,
                            "evaluation_lane": evaluation_identity.lane_id,
                            "dimensions": dimensions,
                        },
                    )
                )
    sortable_findings.sort(key=lambda item: (item[0], item[1]))
    findings = [
        finding
        for _training_key, _evaluation_key, finding in sortable_findings
    ]
    return {
        "manifest_kind": "pneuma_foundation_contamination_receipt",
        "manifest_schema_version": "0.1.0",
        "training_identity_count": len(training_values),
        "evaluation_identity_count": len(evaluation_values),
        "required_evaluation_families": list(required_families),
        "evaluation_family_counts": family_counts,
        "blocked_evaluation_family_status": {
            family: "blocked_unavailable" for family in blocked_families
        },
        "evaluation_coverage_complete": True,
        "finding_count": len(findings),
        "findings": findings,
        "repo_issue_disjoint": not findings,
    }

"""Cross-split contamination checks beyond label-level separation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Mapping

from pneuma_lab.foundation.eval_identities import IdentityRecord


@dataclass(frozen=True)
class ContaminationFinding:
    dimension: str
    value: str


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
    if value is None:
        return None
    normalized = " ".join(value.casefold().split())
    if not normalized:
        return None
    if normalized.startswith("sha256:"):
        suffix = normalized.removeprefix("sha256:")
        if len(suffix) == 64 and all(
            character in "0123456789abcdef" for character in suffix
        ):
            return suffix
    return normalized


def _overlap_dimensions(
    training: IdentityRecord,
    evaluation: IdentityRecord,
) -> list[str]:
    training_repo = _identity_value(training.repo)
    evaluation_repo = _identity_value(evaluation.repo)
    training_issue = _identity_value(training.issue_or_pr)
    evaluation_issue = _identity_value(evaluation.issue_or_pr)
    dimensions = []
    if training_repo is not None and training_repo == evaluation_repo:
        dimensions.append("repository")
        if (
            training_issue is not None
            and training_issue == evaluation_issue
        ):
            dimensions.append("repo_issue_or_pr")
    for field, dimension in (
        ("task_id", "task"),
        ("base_commit", "base_commit"),
        ("patch_sha256", "patch"),
        ("test_patch_sha256", "test_patch"),
        ("fuzzy_text_sha256", "fuzzy_text"),
    ):
        training_value = _identity_value(getattr(training, field))
        evaluation_value = _identity_value(getattr(evaluation, field))
        if training_value is not None and training_value == evaluation_value:
            dimensions.append(dimension)
    return dimensions


def _identity_sort_key(identity: IdentityRecord) -> tuple[str, ...]:
    return (
        identity.family,
        identity.lane_id,
        *(_identity_value(getattr(identity, field)) or "" for field in (
            "repo",
            "issue_or_pr",
            "task_id",
            "base_commit",
            "patch_sha256",
            "test_patch_sha256",
            "fuzzy_text_sha256",
        )),
    )


def build_contamination_receipt(
    training: Iterable[IdentityRecord],
    evaluation: Iterable[IdentityRecord],
) -> dict:
    """Compare every canonical training/evaluation identity pair."""

    training_values = tuple(training)
    evaluation_values = tuple(evaluation)
    if not all(isinstance(value, IdentityRecord) for value in training_values):
        raise TypeError("training identities must be IdentityRecord values")
    if not all(isinstance(value, IdentityRecord) for value in evaluation_values):
        raise TypeError("evaluation identities must be IdentityRecord values")
    findings = []
    for training_identity in sorted(training_values, key=_identity_sort_key):
        for evaluation_identity in sorted(
            evaluation_values,
            key=_identity_sort_key,
        ):
            dimensions = _overlap_dimensions(
                training_identity,
                evaluation_identity,
            )
            if dimensions:
                findings.append(
                    {
                        "training_lane": training_identity.lane_id,
                        "evaluation_lane": evaluation_identity.lane_id,
                        "dimensions": dimensions,
                    }
                )
    return {
        "manifest_kind": "pneuma_foundation_contamination_receipt",
        "manifest_schema_version": "0.1.0",
        "training_identity_count": len(training_values),
        "evaluation_identity_count": len(evaluation_values),
        "finding_count": len(findings),
        "findings": findings,
        "repo_issue_disjoint": not findings,
    }

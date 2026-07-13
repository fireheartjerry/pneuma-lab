"""Cross-split contamination checks beyond label-level separation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Mapping


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

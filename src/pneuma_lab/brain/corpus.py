"""Load PneumaTrainingExample corpora and derive per-task supervision."""

from __future__ import annotations

import json
from pathlib import Path


def load_examples(path: str | Path) -> list[dict]:
    """Read a PneumaTrainingExample JSONL file into a list of dicts."""
    examples: list[dict] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                examples.append(json.loads(line))
    return examples


def examples_for_task(examples: list[dict], task_type: str) -> list[dict]:
    """Examples whose task_mask includes task_type and that carry a target."""
    selected = []
    for example in examples:
        if task_type in (example.get("task_mask") or []) and example.get("target"):
            selected.append(example)
    return selected


def risk_label(example: dict) -> int:
    """RISK_PREDICTION label: failure=1. resolved=True -> 0, else 1."""
    resolved = (example.get("target") or {}).get("resolved")
    if resolved is None:
        raise ValueError("RISK_PREDICTION example is missing target.resolved")
    return 0 if bool(resolved) else 1


def repo_of(example: dict) -> str:
    """Repository used for the grouped split."""
    return (example.get("split_group") or {}).get("repo") or ""


__all__ = ["load_examples", "examples_for_task", "risk_label", "repo_of"]

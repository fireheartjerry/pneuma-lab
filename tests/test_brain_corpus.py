from __future__ import annotations

from pathlib import Path

import pytest

from pneuma_lab.brain import corpus

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "brain"
    / "synthetic_corpus.jsonl"
)


def test_load_examples_reads_all_rows() -> None:
    examples = corpus.load_examples(FIXTURE)
    assert len(examples) == 12
    assert all("task_mask" in e for e in examples)


def test_examples_for_task_selects_by_mask_and_target() -> None:
    examples = corpus.load_examples(FIXTURE)
    risk = corpus.examples_for_task(examples, "RISK_PREDICTION")
    assert len(risk) == 12
    assert corpus.examples_for_task(examples, "FAILURE_SHAPE") == []


def test_risk_label_is_failure_is_one() -> None:
    resolved = {"target": {"resolved": True}}
    failed = {"target": {"resolved": False}}
    assert corpus.risk_label(resolved) == 0
    assert corpus.risk_label(failed) == 1


def test_repo_of_reads_split_group() -> None:
    examples = corpus.load_examples(FIXTURE)
    assert corpus.repo_of(examples[0]) in {
        "org/alpha",
        "org/beta",
        "org/gamma",
        "org/delta",
    }

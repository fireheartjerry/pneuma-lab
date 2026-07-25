"""Tests for the model-selection preflight.

The selection rule is the thing under test. It must pick the largest ELIGIBLE model
rather than the best-performing one, because picking on performance is picking on a
quantity downstream of the treatment.
"""

from __future__ import annotations

import json

import pytest

from pneuma_lab.placebo.preflight import (
    MODEL_LADDER,
    CandidateStats,
    extractCode,
    selectModel,
    wilsonLower,
    writeReceipt,
)


def stats(
    model: str, *, eligible: bool = True, uplift: float = 0.5, reasons=None
) -> CandidateStats:
    return CandidateStats(
        model=model,
        n_calibration=60,
        initial_failures=30,
        initial_pass_rate=0.5,
        plain_retry_successes=5,
        plain_retry_rate=0.17,
        oracle_successes=20,
        oracle_rate=0.17 + uplift,
        oracle_uplift=uplift,
        oracle_uplift_lower_90=max(uplift - 0.1, 0.0),
        parse_failures=0,
        mean_latency_s=1.0,
        tokens_per_second=180.0,
        eligible=eligible,
        ineligibility_reasons=reasons or [],
    )


def test_extractCodeHandlesFencedOutput() -> None:
    fenced = "here you go:\n```python\ndef add(a, b):\n    return a + b\n```"
    assert "def add" in extractCode(fenced)


def test_extractCodeHandlesBareOutput() -> None:
    assert "def add" in extractCode("def add(a, b):\n    return a + b")


def test_extractCodeSkipsFencesWithoutFunctions() -> None:
    mixed = "```\nsome notes\n```\n```python\ndef f():\n    return 1\n```"
    assert "def f" in extractCode(mixed)


def test_wilsonLowerIsZeroWithNoSuccesses() -> None:
    assert wilsonLower(0, 10) == 0.0


def test_wilsonLowerIsConservativeAndMonotone() -> None:
    assert 0.0 < wilsonLower(5, 10) < 0.5
    assert wilsonLower(9, 10) > wilsonLower(5, 10)
    # More trials at the same rate give a tighter, higher lower bound.
    assert wilsonLower(50, 100) > wilsonLower(5, 10)


def test_wilsonLowerHandlesZeroTrials() -> None:
    assert wilsonLower(0, 0) == 0.0


def test_selectionPrefersLargestEligibleNotLargestUplift() -> None:
    """The load-bearing rule. A smaller model with a bigger uplift must not win."""
    small = stats("qwen2.5-coder:1.5b", uplift=0.50)
    large = stats("qwen2.5-coder:7b", uplift=0.25)
    chosen, rationale = selectModel([small, large])
    assert chosen == "qwen2.5-coder:7b"
    assert "largest eligible" in rationale


def test_selectionFallsBackWhenLargestIsIneligible() -> None:
    small = stats("qwen2.5-coder:1.5b")
    large = stats(
        "qwen2.5-coder:7b", eligible=False, reasons=["projected yield below n_min"]
    )
    chosen, _ = selectModel([small, large])
    assert chosen == "qwen2.5-coder:1.5b"


def test_selectionDeclaresNoGoWhenNoneEligible() -> None:
    only = stats("qwen2.5-coder:7b", eligible=False, reasons=["oracle uplift too low"])
    chosen, rationale = selectModel([only])
    assert chosen is None
    assert "no-go" in rationale


def test_ladderOrderIsCapabilityOrder() -> None:
    assert MODEL_LADDER.index("qwen2.5-coder:1.5b") < MODEL_LADDER.index(
        "qwen2.5-coder:7b"
    )


def test_receiptRecordsThatNoTreatmentContrastWasRun(tmp_path) -> None:
    path = tmp_path / "preflight.json"
    writeReceipt(
        [stats("qwen2.5-coder:7b")], ("qwen2.5-coder:7b", "largest eligible"), path
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["selected_model"] == "qwen2.5-coder:7b"
    assert "placebo reflections were not generated" in payload["note"]
    assert payload["candidates"][0]["oracle_uplift"] == pytest.approx(0.5)


def test_receiptIsDeterministic(tmp_path) -> None:
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    payload = [stats("qwen2.5-coder:1.5b"), stats("qwen2.5-coder:7b")]
    writeReceipt(payload, ("qwen2.5-coder:7b", "largest eligible"), a)
    writeReceipt(payload, ("qwen2.5-coder:7b", "largest eligible"), b)
    assert a.read_text(encoding="utf-8") == b.read_text(encoding="utf-8")

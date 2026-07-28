"""The reference bank's labels are established by execution, so the tests execute them."""

from __future__ import annotations

import pytest

from pneuma_lab.gauge.bank import FAULT_CLASSES, SPECS, bankItems
from pneuma_lab.gauge.elicit import (
    ARMS,
    SCALES,
    SHAM_BLOCK,
    TREATED_BLOCK,
    WORDINGS,
    buildForeignMessages,
    buildSelfAuthoredMessages,
    extractCode,
    parseValue,
    promptDigest,
)
from pneuma_lab.gauge.items import loadItems, runHiddenTests, truthLabels, verifyBank


def test_bank_shape():
    items = loadItems()
    assert len(items) == 48
    assert len({i["spec_id"] for i in items}) == 24
    assert sum(i["label"] for i in items) == 24
    assert {i["variant"] for i in items} == {"correct", "buggy"}


def test_every_spec_declares_a_known_fault_class_and_enough_tests():
    for spec in SPECS:
        assert spec.fault_class in FAULT_CLASSES, spec.spec_id
        assert len(spec.hidden_tests) >= 5, spec.spec_id
        assert spec.correct != spec.buggy, spec.spec_id


def test_bank_labels_agree_with_execution():
    """The load-bearing check: correct items pass, buggy items fail, by running them."""
    disagreements = [row for row in verifyBank() if not row["agrees"]]
    assert disagreements == [], disagreements


def test_hidden_tests_terminate_a_runaway_candidate():
    outcome = runHiddenTests(
        "def f(n):\n    while True:\n        pass\n", "f", [[[1], 1]], timeout=3.0
    )
    assert outcome.passed is False
    assert "timed out" in outcome.detail


def test_hidden_tests_report_missing_entry_point():
    outcome = runHiddenTests("x = 1\n", "f", [[[1], 1]], timeout=5.0)
    assert outcome.passed is False
    assert "missing entry point" in outcome.detail


def test_truth_labels_cover_every_item():
    items = loadItems()
    labels = truthLabels(items)
    assert len(labels) == len(items)
    assert set(labels.values()) == {0, 1}


# --------------------------------------------------------------- elicitation


def test_scales_parse_and_normalize_their_own_format():
    by_id = {s.scale_id: s for s in SCALES}
    assert parseValue("0.85", by_id["p2"]) == pytest.approx(0.85)
    assert parseValue("85", by_id["pct"]) == pytest.approx(0.85)
    assert parseValue("9", by_id["ten"]) == pytest.approx(0.9)
    assert parseValue("5", by_id["five"]) == pytest.approx(1.0)
    assert parseValue("1", by_id["five"]) == pytest.approx(0.0)


def test_parser_refuses_to_guess():
    by_id = {s.scale_id: s for s in SCALES}
    assert parseValue("I'm not sure", by_id["p2"]) is None
    assert parseValue("", by_id["p2"]) is None
    assert parseValue("1.5", by_id["p2"]) is None
    # Non-integral answers on an integer scale are scale non-compliance, not data.
    assert parseValue("0.85", by_id["pct"]) is None
    assert parseValue("7.5", by_id["ten"]) is None


def test_reverse_keyed_wordings_are_inverted():
    by_id = {s.scale_id: s for s in SCALES}
    assert parseValue("0.10", by_id["p2"], reverse=True) == pytest.approx(0.90)
    assert {w.wording_id for w in WORDINGS if w.reverse} == {"w5", "w6"}
    assert len(WORDINGS) == 8


def test_sham_and_treated_blocks_are_length_matched():
    # Length matching is what makes the sham a placebo rather than a shorter prompt.
    assert abs(len(SHAM_BLOCK) - len(TREATED_BLOCK)) / len(TREATED_BLOCK) < 0.05
    assert len(SHAM_BLOCK.split()) == pytest.approx(len(TREATED_BLOCK.split()), abs=4)


def test_arms_change_the_prompt_and_the_digest():
    item = loadItems()[0]
    wording, scale = WORDINGS[0], SCALES[0]
    digests = {arm: promptDigest(item, wording, scale, arm, "foreign") for arm in ARMS}
    assert len(set(digests.values())) == len(ARMS)
    base = buildForeignMessages(item, wording, scale, "base")[0]["content"]
    sham = buildForeignMessages(item, wording, scale, "sham")[0]["content"]
    assert SHAM_BLOCK in sham and SHAM_BLOCK not in base


def test_self_authored_prompt_puts_the_models_own_code_in_its_own_turn():
    item = loadItems()[0]
    messages = buildSelfAuthoredMessages(
        item, WORDINGS[0], SCALES[0], "base", "def f():\n    pass"
    )
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert "def f()" in messages[1]["content"]
    assert "You wrote" in messages[2]["content"]


def test_extract_code_prefers_the_fenced_block():
    assert extractCode("blah\n```python\ndef f():\n    return 1\n```\ntrailing") == (
        "def f():\n    return 1"
    )
    assert extractCode("def g():\n    return 2") == "def g():\n    return 2"

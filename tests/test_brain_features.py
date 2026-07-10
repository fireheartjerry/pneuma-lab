from __future__ import annotations

import math

import pytest

from pneuma_lab.brain import features as feat


def _summary() -> dict:
    return {
        "tool_call_count": 10,
        "tool_counts": {"read_file": 6, "edit_file": 3, "run_tests": 1},
        "retry_count_max": 4,
        "retry_count_mean": 1.5,
        "steps_retry_ge2": 3,
        "strategy_switches_final": 2,
        "error_observation_count": 4,
        "observation_count": 20,
        "error_density": 0.2,
        "assistant_text_length_mean": 430.0,
        "assistant_text_length_max": 1800,
        "observation_length_mean": 900.0,
        "observation_length_max": 12000,
    }


def test_scalar_features_are_named_and_log1p_scaled() -> None:
    row = feat.scalar_features(_summary())
    assert row["retry_count_max"] == 4.0
    assert row["error_density"] == pytest.approx(0.2)
    assert row["log1p_tool_call_count"] == pytest.approx(math.log1p(10))


def test_freeze_tool_vocab_is_deterministic_top_n() -> None:
    vocab = feat.freeze_tool_vocab([_summary(), _summary()], n=2)
    assert vocab == ["read_file", "edit_file"]


def test_feature_row_matches_feature_names_length() -> None:
    vocab = feat.freeze_tool_vocab([_summary()], n=2)
    names = feat.feature_names(vocab)
    row = feat.feature_row(_summary(), vocab)
    assert len(row) == len(names)
    assert names[-2:] == ["tool_count__read_file", "tool_count__edit_file"]
    assert row[-2:] == [6.0, 3.0]


def test_assert_no_leakage_rejects_target_keys() -> None:
    with pytest.raises(ValueError):
        feat.assert_no_leakage({"input": {"nested": {"resolved": True}}})
    feat.assert_no_leakage({"input": _summary()})

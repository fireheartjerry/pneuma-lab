"""Estimator feature extraction: scrub-invariance, determinism, prefix math,
known-vector spot checks. Hermetic — synthetic traces only, no dataset reads."""

import copy
import math

import pytest

from pneuma_lab.adapters.envelope import canonical_json
from pneuma_lab.estimators import features as feat

TOOL_VOCAB = ["A", "B"]


def makeFrame(step_index, tools, retry_count, switches, observations, assistant_len):
    return {
        "frame_kind": "agent_trace",
        "step_index": step_index,
        "tool_calls": [
            {"tool": t, "args_digest": f"digest{step_index}-{i}", "args_length": 8}
            for i, t in enumerate(tools)
        ],
        "observations": [
            {"content_sha256": "s", "content_length": length, "error_marker": err}
            for length, err in observations
        ],
        "retry_count": retry_count,
        "strategy_switches": switches,
        "assistant_text_length": assistant_len,
    }


def makeTrace(frames, resolved=False):
    return {
        "labels": {"resolved": resolved, "repo": "org/repo", "has_trajectory": True},
        "outcome": {
            "resolved": resolved,
            "report": {"error_eval": False, "test_timeout": False},
        },
        "oracle": {"kind": "test-based", "fail_to_pass": ["t.py::test_x"]},
        "reference_supervision": {"gold_patch_sha256": "aa", "test_patch_sha256": "bb"},
        "trajectory": {"num_agent_steps": len(frames), "present": True},
        "frames": [{"frame_kind": "world", "objective": {"text": "fix bug"}}] + frames,
    }


def sampleTrace():
    return makeTrace(
        [
            makeFrame(0, ["A"], 0, 0, [(100, False)], 10),
            makeFrame(1, ["A"], 1, 0, [(200, True)], 0),
            makeFrame(2, ["B"], 0, 1, [], 20),
            makeFrame(3, [], 0, 2, [], 5),
        ]
    )


def test_scrubInvariance():
    trace = sampleTrace()
    baseline = {
        name: canonical_json(feat.extractFeatures(trace, name, TOOL_VOCAB))
        for name, _, _ in feat.PREFIX_FRACTIONS
    }
    perturbed = copy.deepcopy(trace)
    perturbed["labels"]["resolved"] = True
    perturbed["outcome"] = {"resolved": True, "report": {"error_eval": True}}
    perturbed["oracle"] = {"kind": "junk", "fail_to_pass": ["other"]}
    perturbed["reference_supervision"] = {"gold_patch_sha256": "zz", "extra": 1}
    for name, expected in baseline.items():
        assert (
            canonical_json(feat.extractFeatures(perturbed, name, TOOL_VOCAB))
            == expected
        )
    deleted = copy.deepcopy(trace)
    del deleted["outcome"]
    del deleted["oracle"]
    del deleted["reference_supervision"]
    del deleted["labels"]["resolved"]
    for name, expected in baseline.items():
        assert (
            canonical_json(feat.extractFeatures(deleted, name, TOOL_VOCAB)) == expected
        )


def test_scrubDoesNotMutateInput():
    trace = sampleTrace()
    snapshot = canonical_json(trace)
    feat.extractFeatures(trace, "full", TOOL_VOCAB)
    assert canonical_json(trace) == snapshot


def test_extractionDeterminism():
    trace = sampleTrace()
    for name, _, _ in feat.PREFIX_FRACTIONS:
        a = canonical_json(feat.extractFeatures(trace, name, TOOL_VOCAB))
        b = canonical_json(feat.extractFeatures(trace, name, TOOL_VOCAB))
        assert a == b


def test_prefixMath():
    assert feat.prefixLength(1, 1, 4) == 1
    assert feat.prefixLength(1, 1, 2) == 1
    assert feat.prefixLength(4, 1, 4) == 1
    assert feat.prefixLength(4, 1, 2) == 2
    assert feat.prefixLength(4, 1, 1) == 4
    assert feat.prefixLength(5, 1, 4) == 2
    assert feat.prefixLength(5, 1, 2) == 3
    assert feat.prefixLength(7, 1, 4) == 2
    assert feat.prefixLength(7, 1, 2) == 4
    assert feat.prefixLength(10, 1, 4) == 3


def test_knownVectorFull():
    values = feat.extractFeatures(sampleTrace(), "full", TOOL_VOCAB)
    assert values["n_steps_prefix"] == 4.0
    assert values["log1p_num_agent_steps"] == pytest.approx(math.log(5.0))
    assert values["tool_count__A"] == 2.0
    assert values["tool_count__B"] == 1.0
    # flattened tools A,A,B -> unique bigrams {(A,A),(A,B)} -> 2/4
    assert values["tool_bigram_diversity"] == pytest.approx(0.5)
    assert values["max_retry"] == 1.0
    assert values["mean_retry"] == pytest.approx(0.25)
    assert values["n_steps_retry_ge2"] == 0.0
    assert values["strategy_switches_final"] == 2.0
    assert values["switches_per_step"] == pytest.approx(0.5)
    assert values["error_density"] == pytest.approx(0.5)
    assert values["last3_error_density"] == pytest.approx(1.0)
    assert values["mean_obs_len_log1p"] == pytest.approx(
        (math.log1p(100) + math.log1p(200)) / 2
    )
    assert values["max_obs_len_log1p"] == pytest.approx(math.log1p(200))
    assert values["mean_assistant_len_log1p"] == pytest.approx(
        (math.log1p(10) + math.log1p(0) + math.log1p(20) + math.log1p(5)) / 4
    )
    assert values["n_tool_calls_total"] == 3.0
    assert values["frac_steps_no_tool"] == pytest.approx(0.25)


def test_knownVectorPrefix25():
    values = feat.extractFeatures(sampleTrace(), "prefix_25", TOOL_VOCAB)
    assert values["n_steps_prefix"] == 1.0
    assert "log1p_num_agent_steps" not in values
    assert values["tool_count__A"] == 1.0
    assert values["tool_count__B"] == 0.0
    assert values["tool_bigram_diversity"] == 0.0
    assert values["max_retry"] == 0.0
    assert values["error_density"] == 0.0
    assert values["last3_error_density"] == 0.0
    assert values["frac_steps_no_tool"] == 0.0
    assert values["n_tool_calls_total"] == 1.0


def test_noLengthVariantExcludesCountFeatures():
    names = feat.featureNames(TOOL_VOCAB, "full", no_length=True)
    assert "n_steps_prefix" not in names
    assert "log1p_num_agent_steps" not in names
    assert "n_tool_calls_total" not in names
    assert not any(n.startswith(feat.TOOL_COUNT_PREFIX) for n in names)
    assert "error_density" in names
    full_names = feat.featureNames(TOOL_VOCAB, "full", no_length=False)
    assert set(names) < set(full_names)
    values = feat.extractFeatures(sampleTrace(), "full", TOOL_VOCAB, no_length=True)
    assert list(values.keys()) == names


def test_featureNameOrderIsStable():
    names = feat.featureNames(TOOL_VOCAB, "full")
    values = feat.extractFeatures(sampleTrace(), "full", TOOL_VOCAB)
    assert list(values.keys()) == names


def test_readLabelAndQcFlags():
    trace = sampleTrace()
    trace["outcome"]["report"]["error_eval"] = True
    label = feat.readLabel(trace)
    assert label["resolved"] is False
    assert label["repo"] == "org/repo"
    assert label["error_eval"] is True
    assert label["test_timeout"] is False


def test_emptyTraceRaises():
    with pytest.raises(ValueError):
        feat.extractFeatures(makeTrace([]), "full", TOOL_VOCAB)

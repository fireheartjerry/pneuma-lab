from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from pneuma_lab.converters.openhands_sampled_training import convert_traces
from pneuma_lab.schemas import load_schema

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "adapters"
    / "openhands_sampled"
    / "golden"
    / "pneuma_traces.jsonl"
)
SCHEMA_NAME = "pneuma-training-example.schema.json"
FORBIDDEN_INPUT_KEYS = {
    "resolved",
    "outcome",
    "labels",
    "gold",
    "oracle",
    "fail_to_pass",
    "pass_to_pass",
    "patch",
    "verdict",
}


def _fixture_traces() -> list[dict]:
    with FIXTURE.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _walk_keys(value) -> list[str]:
    if isinstance(value, dict):
        keys = list(value)
        for child in value.values():
            keys.extend(_walk_keys(child))
        return keys
    if isinstance(value, list):
        keys: list[str] = []
        for child in value:
            keys.extend(_walk_keys(child))
        return keys
    return []


def test_fixture_traces_convert_to_valid_training_examples() -> None:
    validator = Draft202012Validator(load_schema(SCHEMA_NAME))
    examples = convert_traces(
        _fixture_traces(),
        synthetic_fixture_ref="fixtures/adapters/openhands_sampled/golden/pneuma_traces.jsonl",
    )

    assert len(examples) == len(_fixture_traces()) == 3
    for example in examples:
        assert list(validator.iter_errors(example)) == []
        assert example["dataset_id"] == "swe-gym-openhands-sampled"
        assert example["dataset_family"] == "swe-gym"
        assert example["example_type"] == "TrajectoryExample"
        assert example["input_modality"] == "structured_features"
        assert example["task_type"] == "RISK_PREDICTION"
        assert example["task_mask"] == ["RISK_PREDICTION"]
        assert example["label_provenance"]["kind"] == "harness_outcome"
        assert example["privacy_status"] == "redaction_verified"
        assert example["model_use_tier"] == "train_after_adapter"
        assert example["training_weight"] == 0.0
        assert example["split_policy"] == "repo_grouped"
        assert example["target"].keys() == {"resolved"}
        assert example["evidence_refs"]
        assert example["canonical_feature_refs"]


def test_conversion_is_deterministic() -> None:
    traces = _fixture_traces()
    assert convert_traces(traces) == convert_traces(copy.deepcopy(traces))


def test_one_trace_produces_one_full_trace_example() -> None:
    traces = _fixture_traces()
    examples = convert_traces(traces)

    assert len(examples) == len(traces)
    assert {example["input"]["prefix"] for example in examples} == {"full"}
    assert all(
        example["input"]["trajectory"]["num_agent_steps"]
        == trace["trajectory"]["num_agent_steps"]
        for example, trace in zip(examples, traces)
    )


def test_target_resolved_comes_from_harness_outcome() -> None:
    traces = _fixture_traces()
    examples = convert_traces(traces)

    assert [example["target"]["resolved"] for example in examples] == [
        trace["labels"]["resolved"] for trace in traces
    ]
    assert [example["target"]["resolved"] for example in examples] == [
        trace["outcome"]["resolved"] for trace in traces
    ]


def test_input_has_no_forbidden_leakage_keys() -> None:
    examples = convert_traces(_fixture_traces())

    for example in examples:
        input_keys = {key.lower() for key in _walk_keys(example["input"])}
        assert FORBIDDEN_INPUT_KEYS.isdisjoint(input_keys)
        input_blob = json.dumps(example["input"], sort_keys=True)
        assert "C:/pneuma-data" not in input_blob
        assert "C:\\pneuma-data" not in input_blob
        assert "fail_to_pass" not in input_blob
        assert "pass_to_pass" not in input_blob


def test_outcome_oracle_and_label_resolved_do_not_affect_input() -> None:
    trace = _fixture_traces()[0]
    mutated = copy.deepcopy(trace)
    mutated["labels"]["resolved"] = trace["labels"]["resolved"]
    mutated["outcome"]["resolved"] = trace["outcome"]["resolved"]
    mutated["oracle"]["fail_to_pass"] = ["leaky-test"]
    mutated["oracle"]["pass_to_pass"] = ["leaky-test"]
    mutated["reference_supervision"] = {"gold_patch_sha256": "leaky"}
    mutated["outcome"]["git_patch_sha256"] = "leaky"

    assert convert_traces([trace])[0]["input"] == convert_traces([mutated])[0]["input"]


def test_converter_tests_use_committed_fixture_only() -> None:
    assert "fixtures" in str(FIXTURE)
    assert "C:\\pneuma-data" not in str(FIXTURE)
    assert "C:/pneuma-data" not in str(FIXTURE)

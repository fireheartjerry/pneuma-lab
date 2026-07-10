from __future__ import annotations

import copy
import json
import os

import pytest
from jsonschema import Draft202012Validator

from pneuma_lab.converters import open_swe_traces_training as c
from pneuma_lab.schemas import load_schema

GOLDEN = os.path.join("fixtures", "adapters", "open_swe_traces", "golden")
SCHEMA_NAME = "pneuma-training-example.schema.json"


def _traces() -> list[dict]:
    with open(os.path.join(GOLDEN, "pneuma_traces.jsonl"), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _examples() -> list[dict]:
    return c.convert_traces(_traces())


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


def test_traces_convert_to_valid_training_examples() -> None:
    validator = Draft202012Validator(load_schema(SCHEMA_NAME))
    examples = _examples()
    assert len(examples) == 2
    c.validate_training_examples(examples)
    for example in examples:
        assert list(validator.iter_errors(example)) == []
        assert example["dataset_id"] == "open-swe-traces"
        assert example["dataset_family"] == "open-swe-traces"
        assert example["task_type"] == "RISK_PREDICTION"
        assert example["example_type"] == "TrajectoryExample"
        assert example["model_use_tier"] == "train_after_adapter"
        assert example["training_weight"] == 0.0
        assert example["evidence_refs"]


def test_label_provenance_is_constructed_never_harness_outcome() -> None:
    for example in _examples():
        assert example["label_provenance"]["kind"] == "constructed_label"
        assert example["label_provenance"]["kind"] != "harness_outcome"
        assert example["label_provenance"]["confidence"] == "medium"


def test_resolved_target_is_never_placed_in_input() -> None:
    for example in _examples():
        assert "resolved" in example["target"]
        assert "resolved" not in {k.lower() for k in _walk_keys(example["input"])}
        assert '"resolved"' not in json.dumps(example["input"], sort_keys=True)


def test_input_is_digest_only_no_raw_text_or_identifiers() -> None:
    for example in _examples():
        blob = json.dumps(example["input"], sort_keys=True)
        for raw in (
            "demo/alpha",
            "demo__alpha-1",
            "traj-alpha-0001",
            "diff --git",
            "pytest -x",
        ):
            assert raw not in blob
        input_keys = {k.lower() for k in _walk_keys(example["input"])}
        for blocked in ("trajectory", "tool_calls", "tools", "metadata", "patch"):
            assert blocked not in input_keys


def test_blocked_uses_carry_minimax_qwen_tos_caveat() -> None:
    from pneuma_lab.governance import open_swe_traces as gov

    for example in _examples():
        assert gov.MINIMAX_QWEN_TOS_CAVEAT in example["blocked_training_uses"]


def test_split_group_uses_repo_digest() -> None:
    for example in _examples():
        assert example["split_policy"] == "repo_grouped"
        assert example["split_group"]["repo"].startswith("sha256:")
        assert example["split_group"]["task_id"].startswith("sha256:")


def test_forbidden_key_scan_rejects_target_bearing_input() -> None:
    example = _examples()[0]
    poisoned = copy.deepcopy(example)
    poisoned["input"]["resolved"] = True
    with pytest.raises(ValueError):
        c.validate_no_forbidden_input_keys(poisoned)


def test_conversion_is_deterministic() -> None:
    traces = _traces()
    assert c.convert_traces(traces) == c.convert_traces(copy.deepcopy(traces))


def test_conflicting_resolved_labels_raise() -> None:
    trace = copy.deepcopy(_traces()[0])
    trace["outcome"]["resolved"] = not trace["labels"]["resolved"]
    with pytest.raises(ValueError):
        c.convert_trace(trace)


def test_bounded_conversion_writes_to_build(tmp_path) -> None:
    out = tmp_path / "build" / "ost" / "examples.jsonl"
    report = tmp_path / "build" / "ost" / "conversion_report.json"
    manifest = tmp_path / "build" / "ost" / "hash_manifest.json"
    result = c.run_bounded_sample_conversion(
        input_path=os.path.join(GOLDEN, "pneuma_traces.jsonl"),
        adapter_report_path=os.path.join(GOLDEN, "adapter_report.json"),
        examples_path=out,
        report_path=report,
        hash_manifest_path=manifest,
        limit=2,
    )
    assert out.is_file()
    assert len(result["examples"]) == 2
    assert (
        result["report"]["training_authorization"]["training_authorization"]
        == "not_authorized"
    )
    assert result["report"]["output"]["schema_validation_passed"] is True


def test_bounded_conversion_refuses_pneuma_data_output() -> None:
    with pytest.raises(ValueError):
        c.reject_forbidden_output_path("C:/pneuma-data/processed/x.jsonl")


def test_bounded_conversion_refuses_raw_input_path() -> None:
    with pytest.raises(ValueError):
        c.reject_forbidden_input_path("C:/pneuma-data/raw/open-swe-traces/x.parquet")


def test_full_conversion_requires_confirmation() -> None:
    with pytest.raises(ValueError):
        c.run_full_conversion(
            input_path=os.path.join(GOLDEN, "pneuma_traces.jsonl"),
            adapter_report_path=os.path.join(GOLDEN, "adapter_report.json"),
            confirm_full_conversion=False,
        )

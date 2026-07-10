from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from pneuma_lab.adapters import open_swe_traces as adapter
from pneuma_lab.schemas import load_schema

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "adapters"
    / "open_swe_traces"
    / "synthetic_source.json"
)
SCHEMA_NAME = "pneuma-training-example.schema.json"
FORBIDDEN_TEXT = {
    "reference_patch",
    "model_patch",
    "tool_calls",
    ".parquet",
    "C:/pneuma-data",
    "C:\\pneuma-data",
}


def _records() -> list[dict]:
    return adapter.load_synthetic_records(FIXTURE)


def _examples() -> list[dict]:
    return adapter.convert_records(_records())


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


def test_synthetic_fixture_converts_to_valid_training_examples() -> None:
    validator = Draft202012Validator(load_schema(SCHEMA_NAME))
    examples = _examples()

    assert len(_records()) == 2
    assert len(examples) == 2
    adapter.validate_training_examples(examples)
    for example in examples:
        assert list(validator.iter_errors(example)) == []
        assert example["dataset_id"] == "open-swe-traces"
        assert example["dataset_family"] == "open-swe-traces"
        assert example["task_type"] == "RISK_PREDICTION"
        assert example["model_use_tier"] == "train_after_adapter"
        assert example["training_weight"] == 0.0
        assert example["evidence_refs"]
        assert example["canonical_feature_refs"]


def test_conversion_is_deterministic() -> None:
    records = _records()
    assert adapter.convert_records(records) == adapter.convert_records(
        copy.deepcopy(records)
    )


def test_resolved_target_is_not_placed_in_input() -> None:
    for example in _examples():
        assert "resolved" in example["target"]
        assert "resolved" not in _walk_keys(example["input"])
        input_blob = json.dumps(example["input"], sort_keys=True)
        assert '"resolved"' not in input_blob


def test_label_provenance_is_never_harness_outcome() -> None:
    for example in _examples():
        assert example["label_provenance"]["kind"] in {
            "constructed_label",
            "simulated_label",
        }
        assert example["label_provenance"]["kind"] != "harness_outcome"
        assert example["label_provenance"]["confidence"] in {"low", "medium"}


def test_training_weight_remains_zero() -> None:
    for example in _examples():
        assert example["training_weight"] == 0.0
        assert example["model_use_tier"] != "train_ok"


def test_input_has_no_raw_patch_trajectory_or_tool_payload_text() -> None:
    for example in _examples():
        input_keys = {key.lower() for key in _walk_keys(example["input"])}
        assert "trajectory" not in input_keys
        assert "tool_calls" not in input_keys
        assert "tools" not in input_keys
        assert "metadata" not in input_keys
        input_blob = json.dumps(example["input"], sort_keys=True)
        for forbidden in FORBIDDEN_TEXT:
            assert forbidden not in input_blob


def test_report_declares_fixture_only_no_real_data_conversion() -> None:
    report = adapter.build_conversion_report(records=_records(), examples=_examples())

    assert report["mode"] == "synthetic-fixture-only"
    assert report["source"]["real_data_conversion"] is False
    assert report["source"]["bounded_conversion"] is False
    assert report["source"]["raw_trajectory_rows_inspected"] is False
    assert report["leakage_controls"]["raw_trajectory_text_included"] is False
    assert report["leakage_controls"]["raw_tool_payload_included"] is False
    assert report["leakage_controls"]["raw_patch_text_included"] is False
    assert report["leakage_controls"]["oracle_lists_included"] is False
    assert report["leakage_controls"]["final_outcomes_in_input"] is False
    assert report["leakage_controls"]["cross_dataset_leakage_registry_exists"] is False
    assert (
        report["training_authorization"]["training_authorization"] == "not_authorized"
    )
    assert report["training_authorization"]["training_weight"] == 0.0
    assert set(report["output"]["source_groups_seen"]) == {
        "minimax_m25_openhands_trajectories",
        "qwen35_sweagent_trajectories",
    }


def test_tests_use_committed_synthetic_fixture_only() -> None:
    fixture_text = FIXTURE.read_text(encoding="utf-8")

    assert "fixtures" in str(FIXTURE)
    assert "C:/pneuma-data" not in str(FIXTURE)
    assert "C:\\pneuma-data" not in str(FIXTURE)
    assert ".parquet" not in fixture_text
    assert "trajectory" not in fixture_text.replace("trajectory_summary", "").replace(
        "trajectory_id_digest", ""
    )
    assert "tool_calls" not in fixture_text
    assert "reference_patch" not in fixture_text
    assert "model_patch" not in fixture_text

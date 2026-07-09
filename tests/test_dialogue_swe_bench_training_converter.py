from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from pneuma_lab.converters import dialogue_swe_bench_training as converter
from pneuma_lab.schemas import load_schema

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "training_examples"
    / "dialogue_swe_bench_synthetic_source.json"
)
SCHEMA_NAME = "pneuma-training-example.schema.json"
FORBIDDEN_INPUT_KEYS = {
    "problem_statement",
    "draft_problem_statement",
    "full_problem_statement",
    "dialogue_text",
    "raw_dialogue",
    "patch",
    "test_patch",
    "fail_to_pass",
    "pass_to_pass",
    "outcome",
    "resolved",
    "labels",
    "oracle",
    "gold",
    "verdict",
}
FORBIDDEN_TEXT = {
    "raw dialogue",
    "problem_statement",
    "draft_problem_statement",
    "full_problem_statement",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "C:/pneuma-data",
    "C:\\pneuma-data",
}


def _records() -> list[dict]:
    return converter.load_synthetic_records(FIXTURE)


def _examples() -> list[dict]:
    return converter.convert_records(_records())


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
    assert len(examples) == 3
    converter.validate_training_examples(examples)
    for example in examples:
        assert list(validator.iter_errors(example)) == []
        assert example["dataset_id"] == "dialogue-swe-bench"
        assert example["dataset_family"] == "dialogue-swe-bench"
        assert example["privacy_status"] == "public_or_benchmark"
        assert example["model_use_tier"] == "blocked"
        assert example["training_weight"] == 0.0
        assert example["evidence_refs"]
        assert example["canonical_feature_refs"]


def test_conversion_is_deterministic() -> None:
    records = _records()
    assert converter.convert_records(records) == converter.convert_records(
        copy.deepcopy(records)
    )


def test_task_difficulty_example_has_conservative_fields() -> None:
    example = next(item for item in _examples() if item["task_type"] == "TASK_DIFFICULTY")

    assert example["example_type"] == "TaskExample"
    assert example["input_modality"] == "dialogue"
    assert example["task_mask"] == ["TASK_DIFFICULTY"]
    assert example["target"] == {"difficulty": "medium"}
    assert example["label_provenance"]["kind"] == "source_label"
    assert example["label_provenance"]["confidence"] == "medium"
    assert example["split_policy"] == "task_grouped"
    assert example["split_group"]["task_id"] == "synthetic-dialogue-task-001"
    assert "difficulty" not in json.dumps(example["input"]["task"], sort_keys=True)


def test_simulated_operator_pushback_is_never_human_label() -> None:
    example = next(
        item for item in _examples() if item["task_type"] == "OPERATOR_PUSHBACK"
    )

    assert example["example_type"] == "TaskExample"
    assert example["target"] == {"simulated_pushback": True}
    assert example["label_provenance"]["kind"] in {"simulated_label", "proxy_label"}
    assert example["label_provenance"]["kind"] != "human_label"
    assert "not a real-human operator behavior" in example["label_provenance"][
        "description"
    ]
    assert "simulated_correction_count" not in example["input"]["dialogue_summary"]


def test_license_caveat_blocks_training() -> None:
    report = converter.build_conversion_report(records=_records(), examples=_examples())

    for example in _examples():
        blocked_uses = " ".join(example["blocked_training_uses"]).lower()
        assert "license review" in blocked_uses
        assert example["input"]["dataset"]["license_status"] is None
        assert example["input"]["dataset"]["license_review_required"] is True
        assert example["model_use_tier"] == "blocked"
        assert example["training_weight"] == 0.0

    assert report["license"]["local_status"] is None
    assert report["license"]["review_required_before_training_oriented_use"] is True
    assert report["training_authorization"]["model_use_tier"] == "blocked"
    assert report["training_authorization"]["training_weight"] == 0.0


def test_input_has_no_forbidden_leakage_keys_or_raw_text() -> None:
    for example in _examples():
        input_keys = {key.lower() for key in _walk_keys(example["input"])}
        assert FORBIDDEN_INPUT_KEYS.isdisjoint(input_keys)
        input_blob = json.dumps(example["input"], sort_keys=True)
        for forbidden in FORBIDDEN_TEXT:
            assert forbidden not in input_blob
        assert example["input"]["code_change_summary"]["text_included"] is False
        assert example["input"]["code_change_summary"]["oracle_lists_included"] is False


def test_report_declares_fixture_only_no_real_data_conversion() -> None:
    report = converter.build_conversion_report(records=_records(), examples=_examples())

    assert report["mode"] == "synthetic-fixture-only"
    assert report["source"]["real_data_conversion"] is False
    assert report["source"]["bounded_conversion"] is False
    assert report["source"]["raw_dialogue_rows_inspected"] is False
    assert report["leakage_controls"]["raw_dialogue_text_included"] is False
    assert report["leakage_controls"]["raw_issue_text_included"] is False
    assert report["leakage_controls"]["raw_patch_text_included"] is False
    assert report["leakage_controls"]["oracle_lists_included"] is False
    assert report["leakage_controls"]["final_outcomes_in_input"] is False


def test_tests_use_committed_synthetic_fixture_only() -> None:
    fixture_text = FIXTURE.read_text(encoding="utf-8")

    assert "fixtures" in str(FIXTURE)
    assert "C:/pneuma-data" not in str(FIXTURE)
    assert "C:\\pneuma-data" not in str(FIXTURE)
    assert ".parquet" not in fixture_text
    assert "problem_statement" not in fixture_text
    assert "full_problem_statement" not in fixture_text
    assert "FAIL_TO_PASS" not in fixture_text
    assert "PASS_TO_PASS" not in fixture_text

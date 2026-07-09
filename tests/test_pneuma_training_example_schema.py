"""Synthetic-only tests for the PneumaTrainingExample contract.

These tests intentionally validate hand-authored fixtures, not real dataset
rows. They prove the schema gates future training examples before any conversion
work touches local corpora.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pneuma_lab.schemas import SCHEMA_DIR, load_schema

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "training_examples"
VALID_FIXTURES = FIXTURE_DIR / "valid_examples.json"
INVALID_FIXTURES = FIXTURE_DIR / "invalid_examples.json"
SCHEMA_NAME = "pneuma-training-example.schema.json"


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = load_schema(SCHEMA_NAME)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture(scope="module")
def valid_examples() -> list[dict]:
    return json.loads(VALID_FIXTURES.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def invalid_examples() -> dict[str, dict]:
    return json.loads(INVALID_FIXTURES.read_text(encoding="utf-8"))


def validation_errors(validator: Draft202012Validator, example: dict) -> list[str]:
    return [err.message for err in validator.iter_errors(example)]


def validation_error_paths(validator: Draft202012Validator, example: dict) -> list[str]:
    return [".".join(str(part) for part in err.path) for err in validator.iter_errors(example)]


def test_training_example_schema_lives_in_schema_dir() -> None:
    assert (SCHEMA_DIR / SCHEMA_NAME).is_file()


def test_valid_synthetic_examples_pass(
    validator: Draft202012Validator, valid_examples: list[dict]
) -> None:
    assert len(valid_examples) >= 5
    for example in valid_examples:
        assert validation_errors(validator, example) == []


def test_valid_fixture_covers_required_example_shapes(valid_examples: list[dict]) -> None:
    seen = {(example["dataset_family"], example["example_type"], example["task_type"]) for example in valid_examples}
    assert ("swe-gym", "TrajectoryExample", "RISK_PREDICTION") in seen
    assert ("swe-gym", "VerifierExample", "VERIFIER_VALUE") in seen
    assert ("dialogue-swe-bench", "TaskExample", "TASK_DIFFICULTY") in seen


def test_invalid_task_enum_fails(
    validator: Draft202012Validator, invalid_examples: dict[str, dict]
) -> None:
    errors = validation_errors(validator, invalid_examples["unknown_task_type"])
    assert errors
    assert any("UNKNOWN_TASK" in message for message in errors)


def test_missing_required_field_fails(
    validator: Draft202012Validator, invalid_examples: dict[str, dict]
) -> None:
    errors = validation_errors(validator, invalid_examples["missing_required_field"])
    assert errors
    assert any("dataset_id" in message for message in errors)


def test_blocked_privacy_examples_cannot_train(
    validator: Draft202012Validator, valid_examples: list[dict]
) -> None:
    blocked = next(example for example in valid_examples if example["dataset_family"] == "swe-chat")
    assert blocked["privacy_status"] == "pii_blocked"
    assert blocked["model_use_tier"] == "blocked"
    assert blocked["training_weight"] == 0
    assert validation_errors(validator, blocked) == []

    mutated = dict(blocked)
    mutated["training_weight"] = 0.01
    assert validation_errors(validator, mutated)


def test_eval_only_examples_cannot_train(
    validator: Draft202012Validator, valid_examples: list[dict]
) -> None:
    eval_only = next(example for example in valid_examples if example["dataset_family"] == "swe-mera")
    assert eval_only["privacy_status"] == "eval_only"
    assert eval_only["model_use_tier"] == "eval_only"
    assert eval_only["training_weight"] == 0
    assert validation_errors(validator, eval_only) == []

    mutated = dict(eval_only)
    mutated["training_weight"] = 0.01
    assert validation_errors(validator, mutated)


def test_invalid_blocked_example_with_positive_weight_fails(
    validator: Draft202012Validator, invalid_examples: dict[str, dict]
) -> None:
    example = invalid_examples["blocked_positive_weight"]
    assert validation_errors(validator, example)
    assert "training_weight" in validation_error_paths(validator, example)


def test_missing_task_labels_are_masked_not_negative(
    validator: Draft202012Validator, valid_examples: list[dict]
) -> None:
    example = next(
        item
        for item in valid_examples
        if item["dataset_family"] == "dialogue-swe-bench"
    )
    assert example["task_mask"] == ["TASK_DIFFICULTY"]
    assert set(example["target"]) == {"difficulty"}
    assert "RISK_PREDICTION" not in example["task_mask"]
    assert "resolved" not in example["target"]
    assert validation_errors(validator, example) == []


def test_trainable_examples_need_targets_and_evidence(
    validator: Draft202012Validator, valid_examples: list[dict]
) -> None:
    trainable = next(example for example in valid_examples if example["model_use_tier"] == "train_ok")

    without_target = dict(trainable)
    without_target["target"] = {}
    assert validation_errors(validator, without_target)

    without_evidence = dict(trainable)
    without_evidence["evidence_refs"] = []
    assert validation_errors(validator, without_evidence)


def test_schema_validation_does_not_reference_raw_data() -> None:
    for path in (VALID_FIXTURES, INVALID_FIXTURES):
        text = path.read_text(encoding="utf-8")
        assert "C:\\pneuma-data" not in text
        assert "raw/" not in text
        assert "raw\\" not in text

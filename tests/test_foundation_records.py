"""Canonical zero-weight foundation records remain deterministic and leakage-safe."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from types import MappingProxyType

import pytest
from jsonschema import Draft202012Validator

from pneuma_lab.foundation.core import FORECAST_TARGETS
from pneuma_lab.foundation.records import (
    EffectiveTrainingRecord,
    FoundationRecordError,
    GradientEligibility,
    LaneDisposition,
    TerminalRole,
    foundation_identity,
    render_foundation_record,
    render_prompt_payload,
    validate_derived_foundation_record,
    validate_foundation_record,
)
from pneuma_lab.schemas import load_schema


class DeterministicTokenizer:
    """Small tokenizer test double with stable, inspectable token counts."""

    def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
        assert add_special_tokens is False
        return list(text.encode("utf-8"))


@pytest.fixture
def tokenizer() -> DeterministicTokenizer:
    return DeterministicTokenizer()


def _canonical_openhands_example(*, resolved: bool) -> dict:
    return {
        "example_id": "pte:swe-gym-openhands-sampled:example-1:risk:full",
        "dataset_id": "swe-gym-openhands-sampled",
        "dataset_family": "swe-gym",
        "source_revision": None,
        "split_group": {
            "repo": "private/repository-name",
            "task_id": "private-task-id",
        },
        "input": {
            "prefix": "full",
            "trace_id": "private-trace-id",
            "run_id": "private-run-id",
            "repo": "private/repository-name",
            "task_id": "private-task-id",
            "issue_or_pr": "private-issue-id",
            "base_commit": "c" * 40,
            "patch_sha256": "d" * 64,
            "test_patch_sha256": "e" * 64,
            "language": "python",
            "trajectory": {
                "num_agent_steps": 3,
                "num_messages": 5,
                "timestamp_provenance": "synthetic-ordinal",
            },
            "observable_summary": {
                "tool_call_count": 3,
                "tool_counts": {"run_tests": 1, "read_file": 2},
            },
            "objective": {
                "mode": "digest_only",
                "present": True,
                "text_length": 97,
                "text_sha256": "sha256:" + "f" * 64,
            },
            "feature_refs": [
                "pneuma-estimators-features/0.1.0",
                "openhands-sampled-training/0.1.0",
            ],
            "source_path": "C:/forbidden/source/path.jsonl",
            "resolved": not resolved,
        },
        "target": {"resolved": resolved},
    }


def _lane_disposition() -> LaneDisposition:
    return LaneDisposition(
        terminal_role=TerminalRole.TRAIN,
        gradient_eligibility=GradientEligibility.FIRST_STAGE,
        license_disposition="local_research_candidate_no_redistribution",
        privacy_disposition="redaction_verified",
        dual_use_disposition="not_flagged",
        oracle_disposition="target_only",
    )


def _render_example(
    tokenizer: DeterministicTokenizer,
    example: dict,
    *,
    split_assignment: dict | None = None,
    tokenizer_revision: object = "1" * 40,
) -> dict:
    return render_foundation_record(
        example,
        lane_disposition=_lane_disposition(),
        split_assignment=(
            split_assignment
            if split_assignment is not None
            else {"split_id": "train", "quarantine_id": None}
        ),
        tokenizer=tokenizer,
        tokenizer_revision=tokenizer_revision,
        source_receipt_hashes=("a" * 64, "b" * 64),
    )


def _render(tokenizer: DeterministicTokenizer, *, resolved: bool = True) -> dict:
    return _render_example(
        tokenizer,
        _canonical_openhands_example(resolved=resolved),
    )


def test_openhands_example_renders_zero_weight_record(tokenizer) -> None:
    record = _render(tokenizer)
    assert record["source"]["dataset_family"] == "swe-gym"
    assert record["source"]["lane_id"] == "swe-gym-openhands-sampled"
    assert record["training_weight"] == 0.0
    assert record["rendered"]["target_text"] == '{"resolved":true}'
    assert record["forecast_targets"]["action_success"] == {
        "applicable": True,
        "value": 1.0,
        "provenance": "observed_outcome",
    }
    assert record["forecast_targets"]["expected_error"] == {
        "applicable": True,
        "value": 0.0,
        "provenance": "observed_outcome",
    }
    assert record["forecast_targets"]["verifier_outcome"]["applicable"] is False
    assert record["forecast_targets"]["tool_cost"]["applicable"] is False
    assert record["forecast_targets"]["token_cost"]["applicable"] is False
    assert record["forecast_targets"]["latency_cost"] == {
        "applicable": False,
        "value": None,
        "provenance": None,
    }
    assert record["forecast_targets"]["retrieval_usefulness"]["applicable"] is False
    assert record["forecast_targets"]["intervention_response"]["applicable"] is False
    schema = load_schema("foundation-training-record.schema.json")
    Draft202012Validator(schema).validate(record)


def test_prompt_renderer_is_an_explicit_allowlist(tokenizer) -> None:
    example = _canonical_openhands_example(resolved=True)
    record = _render(tokenizer)

    assert json.loads(record["rendered"]["prompt_text"]) == {
        "feature_refs": [
            "openhands-sampled-training/0.1.0",
            "pneuma-estimators-features/0.1.0",
        ],
        "objective": {"present": True, "text_length": 97},
        "observable_summary": {"tool_call_count": 3},
        "prefix": "full",
        "trajectory": {
            "num_agent_steps": 3,
            "num_messages": 5,
            "timestamp_provenance": "synthetic-ordinal",
        },
    }
    assert record["observations"]["tools"] == ["read_file", "run_tests"]
    prompt_text = record["rendered"]["prompt_text"]
    excluded_values = (
        example["input"]["trace_id"],
        example["input"]["run_id"],
        example["input"]["repo"],
        example["input"]["task_id"],
        example["input"]["issue_or_pr"],
        example["input"]["objective"]["text_sha256"],
        example["input"]["source_path"],
    )
    assert all(value not in prompt_text for value in excluded_values)
    assert "resolved" not in prompt_text


def test_prompt_renderer_defaults_missing_objective_metadata() -> None:
    example = _canonical_openhands_example(resolved=True)
    example["input"].pop("objective")

    assert render_prompt_payload(example)["objective"] == {
        "present": False,
        "text_length": 0,
    }


@pytest.mark.parametrize("value", ("true", 1))
def test_prompt_renderer_rejects_non_boolean_objective_presence(value) -> None:
    example = _canonical_openhands_example(resolved=True)
    example["input"]["objective"]["present"] = value

    with pytest.raises(FoundationRecordError, match="objective.present"):
        render_prompt_payload(example)


@pytest.mark.parametrize(
    "value",
    (True, "97", 97.0, -1, math.nan, math.inf),
)
def test_prompt_renderer_rejects_invalid_objective_text_length(value) -> None:
    example = _canonical_openhands_example(resolved=True)
    example["input"]["objective"]["text_length"] = value

    with pytest.raises(FoundationRecordError, match="objective.text_length"):
        render_prompt_payload(example)


def test_prompt_renderer_excludes_nested_leakage_keys(tokenizer) -> None:
    example = _canonical_openhands_example(resolved=True)
    example["input"]["prefix"] = {"run_id": "nested-prefix-run-id"}
    example["input"]["feature_refs"].append(
        {"source_path": "C:/nested/private/feature.json"}
    )
    example["input"]["trajectory"]["metadata"] = {
        "run_id": "nested-private-run-id",
        "source_path": "C:/nested/private/trajectory.json",
    }
    example["input"]["observable_summary"]["details"] = {
        "repo": "nested/private-repository",
        "target": {"resolved": True},
    }
    example["input"]["observable_summary"]["tool_counts"]["metadata"] = {
        "source_path": "C:/nested/private/tool.json"
    }
    example["input"]["observable_summary"]["gold_patch_sha256"] = "9" * 64

    record = render_foundation_record(
        example,
        lane_disposition=_lane_disposition(),
        split_assignment={"split_id": "train", "quarantine_id": None},
        tokenizer=tokenizer,
        tokenizer_revision="1" * 40,
        source_receipt_hashes=("a" * 64, "b" * 64),
    )

    prompt_text = record["rendered"]["prompt_text"]
    assert "nested-prefix-run-id" not in prompt_text
    assert "C:/nested/private/feature.json" not in prompt_text
    assert "nested-private-run-id" not in prompt_text
    assert "C:/nested/private/trajectory.json" not in prompt_text
    assert "nested/private-repository" not in prompt_text
    assert "C:/nested/private/tool.json" not in prompt_text
    assert "resolved" not in prompt_text
    assert "9" * 64 not in prompt_text


def test_prompt_renderer_rejects_identifier_path_and_target_like_values(
    tokenizer,
) -> None:
    example = _canonical_openhands_example(resolved=True)
    example["input"]["prefix"] = "private-task-id"
    example["input"]["trajectory"]["timestamp_provenance"] = "private-run-id"
    example["input"]["trajectory"]["resolved"] = 1
    example["input"]["observable_summary"]["tool_counts"] = {
        "private-trace-id": 2,
        "resolved": 1,
    }
    example["input"]["observable_summary"]["resolved"] = 1
    example["input"]["feature_refs"] = [
        "private/source/file.json",
        "resolved",
        "sha256:" + "a" * 64,
        "pneuma-estimators-features/9.9.9",
    ]

    record = render_foundation_record(
        example,
        lane_disposition=_lane_disposition(),
        split_assignment={"split_id": "train", "quarantine_id": None},
        tokenizer=tokenizer,
        tokenizer_revision="1" * 40,
        source_receipt_hashes=("a" * 64, "b" * 64),
    )

    prompt = json.loads(record["rendered"]["prompt_text"])
    assert prompt == {
        "feature_refs": [],
        "objective": {"present": True, "text_length": 97},
        "observable_summary": {"tool_call_count": 3},
        "prefix": None,
        "trajectory": {"num_agent_steps": 3, "num_messages": 5},
    }
    prompt_text = record["rendered"]["prompt_text"]
    for forbidden in (
        "private-task-id",
        "private-run-id",
        "private-trace-id",
        "private/source/file.json",
        "resolved",
        "sha256:",
        "9.9.9",
        "tool_counts",
    ):
        assert forbidden not in prompt_text


@pytest.mark.parametrize("suffix", ("a" * 64, "A" * 64))
def test_foundation_identity_normalizes_valid_prefixed_sha256(suffix: str) -> None:
    identity = foundation_identity(
        {"input": {"objective": {"text_sha256": "sha256:" + suffix}}},
        prompt_text="ignored",
    )
    assert identity["fuzzy_text_sha256"] == suffix.lower()


@pytest.mark.parametrize(
    "value",
    (
        "sha256:" + "g" * 64,
        "sha256:" + "a" * 63,
        "sha256:" + "a" * 65,
    ),
)
def test_foundation_identity_hashes_malformed_prefixed_digest_as_text(
    value: str,
) -> None:
    identity = foundation_identity(
        {"input": {"objective": {"text_sha256": value}}},
        prompt_text="ignored",
    )
    assert identity["fuzzy_text_sha256"] == hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def test_record_identity_is_outside_tokens_and_rendering_is_deterministic(
    tokenizer,
) -> None:
    record = _render(tokenizer)
    repeated = render_foundation_record(
        copy.deepcopy(_canonical_openhands_example(resolved=True)),
        lane_disposition=_lane_disposition(),
        split_assignment={"split_id": "train", "quarantine_id": None},
        tokenizer=tokenizer,
        tokenizer_revision="1" * 40,
        source_receipt_hashes=("b" * 64, "a" * 64),
    )

    assert repeated == record
    assert record["identity"] == {
        "repo": "private/repository-name",
        "issue_or_pr": "private-issue-id",
        "task_id": "private-task-id",
        "base_commit": "c" * 40,
        "patch_sha256": "d" * 64,
        "test_patch_sha256": "e" * 64,
        "fuzzy_text_sha256": "f" * 64,
    }
    assert record["source"]["receipt_hashes"] == ["a" * 64, "b" * 64]
    assert record["tokenization"]["prompt_tokens"] == len(
        record["rendered"]["prompt_text"].encode("utf-8")
    )
    assert record["tokenization"]["target_tokens"] == len(
        record["rendered"]["target_text"].encode("utf-8")
    )
    assert record["tokenization"]["total_tokens"] == (
        record["tokenization"]["prompt_tokens"]
        + record["tokenization"]["target_tokens"]
    )


def test_effective_training_record_requires_positive_in_memory_weight(tokenizer) -> None:
    record = _render(tokenizer)
    effective = EffectiveTrainingRecord(record=record, effective_weight=1.0)
    assert effective.record is not record
    assert effective.record["rendered"]["target_text"] == record["rendered"][
        "target_text"
    ]
    assert tuple(effective.record["observations"]["tools"]) == tuple(
        record["observations"]["tools"]
    )
    assert effective.effective_weight == 1.0
    record["rendered"]["target_text"] = "caller mutation"
    assert effective.record["rendered"]["target_text"] == '{"resolved":true}'
    with pytest.raises(TypeError):
        effective.record["rendered"]["target_text"] = "direct mutation"
    with pytest.raises((AttributeError, TypeError)):
        effective.record["observations"]["tools"].append("mutation")
    for invalid in (0.0, -1.0, float("nan"), float("inf"), True):
        with pytest.raises(FoundationRecordError, match="effective_weight"):
            EffectiveTrainingRecord(record=record, effective_weight=invalid)


def test_derived_record_validator_accepts_exact_converter_derivation(tokenizer) -> None:
    example = _canonical_openhands_example(resolved=True)
    record = _render_example(tokenizer, example)

    validate_derived_foundation_record(
        record,
        example=example,
        split_assignment={"split_id": "train", "quarantine_id": None},
        lane_disposition=_lane_disposition(),
        source_receipt_hashes=("a" * 64, "b" * 64),
        tokenizer_id="Qwen/Qwen3.5-2B",
        tokenizer_revision="1" * 40,
    )


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value["rendered"].update(prompt_text="changed"),
        lambda value: value["rendered"].update(target_text='{"resolved":false}'),
        lambda value: value["observations"]["labels"].update(resolved=False),
        lambda value: value["forecast_targets"]["action_success"].update(value=0.0),
        lambda value: value["identity"].update(repo="changed/repo"),
        lambda value: value.update(record_id="ftr:" + "0" * 64),
        lambda value: value["source"].update(source_record_id="changed-source"),
    ),
)
def test_derived_record_validator_rejects_changed_derived_fields(
    tokenizer,
    mutation,
) -> None:
    example = _canonical_openhands_example(resolved=True)
    record = _render_example(tokenizer, example)
    mutation(record)

    with pytest.raises(FoundationRecordError, match="deriv|record|source|render|identity"):
        validate_derived_foundation_record(
            record,
            example=example,
            split_assignment={"split_id": "train", "quarantine_id": None},
            lane_disposition=_lane_disposition(),
            source_receipt_hashes=("a" * 64, "b" * 64),
            tokenizer_id="Qwen/Qwen3.5-2B",
            tokenizer_revision="1" * 40,
        )


@pytest.mark.parametrize("missing", ("input", "target", "dataset_family", "dataset_id"))
def test_derived_record_validator_rejects_incomplete_conversion_example(
    tokenizer,
    missing: str,
) -> None:
    example = _canonical_openhands_example(resolved=True)
    record = _render_example(tokenizer, example)
    example.pop(missing)

    with pytest.raises(FoundationRecordError):
        validate_derived_foundation_record(
            record,
            example=example,
            split_assignment={"split_id": "train", "quarantine_id": None},
            lane_disposition=_lane_disposition(),
            source_receipt_hashes=("a" * 64, "b" * 64),
            tokenizer_id="Qwen/Qwen3.5-2B",
            tokenizer_revision="1" * 40,
        )


def test_record_validation_rejects_extra_properties(tokenizer) -> None:
    record = _render(tokenizer)
    record["forecast_targets"]["action_success"]["leaked"] = True
    with pytest.raises(FoundationRecordError, match="Additional properties"):
        validate_foundation_record(record)


@pytest.mark.parametrize(
    "target",
    (
        None,
        "resolved",
        [True],
        {},
        {"resolved": None},
        {"resolved": "true"},
        {"resolved": 1},
        {"resolved": [True]},
    ),
)
def test_record_rendering_rejects_missing_or_malformed_resolved_target(
    tokenizer,
    target,
) -> None:
    example = _canonical_openhands_example(resolved=True)
    example["target"] = target

    with pytest.raises(FoundationRecordError, match="target(?:.resolved)?"):
        _render_example(tokenizer, example)


def test_record_rendering_rejects_missing_target(tokenizer) -> None:
    example = _canonical_openhands_example(resolved=True)
    example.pop("target")

    with pytest.raises(FoundationRecordError, match="target"):
        _render_example(tokenizer, example)


def test_record_rendering_accepts_a_json_native_target_mapping(tokenizer) -> None:
    example = _canonical_openhands_example(resolved=True)
    example["target"] = MappingProxyType({"resolved": True})

    record = _render_example(tokenizer, example)

    assert record["rendered"]["target_text"] == '{"resolved":true}'


@pytest.mark.parametrize("value", (math.nan, math.inf, -math.inf))
def test_record_rendering_rejects_non_finite_target_values(tokenizer, value) -> None:
    example = _canonical_openhands_example(resolved=True)
    example["target"]["score"] = value

    with pytest.raises(FoundationRecordError, match="target.*canonical JSON"):
        _render_example(tokenizer, example)


@pytest.mark.parametrize(
    ("field", "value"),
    tuple(
        (field, value)
        for field in ("dataset_family", "dataset_id", "example_id")
        for value in (None, 1, "")
    ),
)
def test_record_rendering_rejects_invalid_source_provenance_ids(
    tokenizer,
    field,
    value,
) -> None:
    example = _canonical_openhands_example(resolved=True)
    example[field] = value

    with pytest.raises(FoundationRecordError, match=field):
        _render_example(tokenizer, example)


@pytest.mark.parametrize("value", (None, 1, ""))
def test_record_rendering_rejects_invalid_split_id(tokenizer, value) -> None:
    with pytest.raises(FoundationRecordError, match="split_id"):
        _render_example(
            tokenizer,
            _canonical_openhands_example(resolved=True),
            split_assignment={"split_id": value, "quarantine_id": None},
        )


@pytest.mark.parametrize("value", (None, 1, "A" * 40, "1" * 39))
def test_record_rendering_enforces_tokenizer_revision_schema(tokenizer, value) -> None:
    with pytest.raises(FoundationRecordError, match="tokenizer_revision"):
        _render_example(
            tokenizer,
            _canonical_openhands_example(resolved=True),
            tokenizer_revision=value,
        )


def test_record_rendering_rejects_non_string_source_revision(tokenizer) -> None:
    example = _canonical_openhands_example(resolved=True)
    example["source_revision"] = 1

    with pytest.raises(FoundationRecordError, match="source_revision"):
        _render_example(tokenizer, example)


def test_record_validation_rejects_non_json_native_values(tokenizer) -> None:
    record = _render(tokenizer)
    record["observations"]["tools"] = {"read_file"}

    with pytest.raises(FoundationRecordError, match="canonical JSON"):
        validate_foundation_record(record)


@pytest.mark.parametrize("value", (math.nan, math.inf, -math.inf))
def test_record_validation_rejects_non_finite_values(tokenizer, value) -> None:
    record = _render(tokenizer)
    record["forecast_targets"]["action_success"]["value"] = value

    with pytest.raises(FoundationRecordError, match="canonical JSON"):
        validate_foundation_record(record)


def test_forecast_contract_enumerates_all_targets(tokenizer) -> None:
    record = _render(tokenizer, resolved=False)
    assert tuple(record["forecast_targets"]) == FORECAST_TARGETS
    assert record["forecast_targets"]["action_success"]["value"] == 0.0
    assert record["forecast_targets"]["expected_error"]["value"] == 1.0
    assert record["observations"]["labels"]["resolved"] is False
    for name in FORECAST_TARGETS[2:]:
        assert record["forecast_targets"][name] == {
            "applicable": False,
            "value": None,
            "provenance": None,
        }

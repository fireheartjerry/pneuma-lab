"""Deterministic, zero-weight records for guarded foundation training."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any

from jsonschema import Draft202012Validator

from pneuma_lab.foundation.core import FORECAST_TARGETS
from pneuma_lab.schemas import load_schema


_TRAJECTORY_PROMPT_FIELDS = (
    "num_messages",
    "num_agent_steps",
)
_OBSERVABLE_NUMERIC_PROMPT_FIELDS = (
    "tool_call_count",
    "retry_count_max",
    "retry_count_mean",
    "steps_retry_ge2",
    "strategy_switches_final",
    "error_observation_count",
    "observation_count",
    "error_density",
    "assistant_text_length_mean",
    "assistant_text_length_max",
    "observation_length_mean",
    "observation_length_max",
)
_REVIEWED_FEATURE_REFS = frozenset(
    {
        "openhands-sampled-training/0.1.0",
        "pneuma-estimators-features/0.1.0",
    }
)
_MISSING = object()


class FoundationRecordError(ValueError):
    """Raised when a rendered foundation record violates its contract."""


class TerminalRole(str, Enum):
    TRAIN = "train"
    EVAL = "eval"
    GOVERNANCE = "governance"


class GradientEligibility(str, Enum):
    FIRST_STAGE = "first_stage"
    LATER = "later"
    NEVER = "never"


@dataclass(frozen=True)
class LaneDisposition:
    terminal_role: TerminalRole
    gradient_eligibility: GradientEligibility
    license_disposition: str
    privacy_disposition: str
    dual_use_disposition: str
    oracle_disposition: str


@dataclass(frozen=True)
class EffectiveTrainingRecord:
    record: Mapping
    effective_weight: float

    def __post_init__(self) -> None:
        if not isinstance(self.record, Mapping):
            raise FoundationRecordError("effective record must be a mapping")
        if (
            type(self.effective_weight) is not float
            or not math.isfinite(self.effective_weight)
            or self.effective_weight <= 0.0
        ):
            raise FoundationRecordError(
                "effective_weight must be a finite positive float"
            )
        detached = _canonical_json_copy(self.record)
        object.__setattr__(self, "record", _freeze_json_value(detached))


def _json_native_copy(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _json_native_copy(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_native_copy(item) for item in value]
    return value


def _canonical_json_copy(value: Mapping) -> dict:
    try:
        payload = json.dumps(
            _json_native_copy(value),
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        detached = json.loads(payload)
    except (TypeError, ValueError, OverflowError) as exc:
        raise FoundationRecordError(
            f"effective record must be canonical JSON: {exc}"
        ) from exc
    if not isinstance(detached, dict):
        raise FoundationRecordError("effective record must be a JSON object")
    return detached


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_json_value(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_json_value(item) for item in value)
    return value


def _validated_resolved_target(example: Mapping) -> bool:
    target = example.get("target")
    if not isinstance(target, Mapping):
        raise FoundationRecordError("target must be a mapping")
    if "resolved" not in target or type(target["resolved"]) is not bool:
        raise FoundationRecordError("target.resolved must be a bool")
    return target["resolved"]


def _required_nonempty_string(value, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise FoundationRecordError(f"{field} must be a nonempty string")
    return value


def _validated_tokenizer_revision(value) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise FoundationRecordError(
            "tokenizer_revision must be a lowercase 40-character hex string"
        )
    return value


def _validated_source_revision(value):
    if value is not None and not isinstance(value, str):
        raise FoundationRecordError("source_revision must be a string or null")
    return value


def _forecast_targets(resolved: bool) -> dict[str, dict]:
    values = {
        "action_success": resolved,
        "expected_error": not resolved,
    }
    return {
        name: {
            "applicable": name in values,
            "value": float(values[name]) if name in values else None,
            "provenance": "observed_outcome" if name in values else None,
        }
        for name in FORECAST_TARGETS
    }


def _digest_text(value: str) -> str:
    prefix = "sha256:"
    if value.startswith(prefix):
        suffix = value.removeprefix(prefix)
        normalized = suffix.casefold()
        if len(normalized) == 64 and all(
            character in "0123456789abcdef" for character in normalized
        ):
            return normalized
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def foundation_identity(example: Mapping, *, prompt_text: str) -> dict:
    input_value = example.get("input") or {}
    split_group = example.get("split_group") or {}
    objective = input_value.get("objective") or {}
    fuzzy_source = str(objective.get("text_sha256") or prompt_text)
    task_id = split_group.get("task_id") or input_value.get("task_id")
    return {
        "repo": split_group.get("repo") or input_value.get("repo"),
        "issue_or_pr": input_value.get("issue_or_pr") or task_id,
        "task_id": task_id,
        "base_commit": input_value.get("base_commit"),
        "patch_sha256": input_value.get("patch_sha256"),
        "test_patch_sha256": input_value.get("test_patch_sha256"),
        "fuzzy_text_sha256": _digest_text(fuzzy_source),
    }


def foundation_observations(example: Mapping, *, resolved=_MISSING) -> dict:
    if resolved is _MISSING:
        resolved = _validated_resolved_target(example)
    elif type(resolved) is not bool:
        raise FoundationRecordError("target.resolved must be a bool")
    input_value = example.get("input") or {}
    summary = input_value.get("observable_summary") or {}
    trajectory = input_value.get("trajectory") or {}
    return {
        "language": str(input_value.get("language") or "unknown"),
        "tools": sorted(str(name) for name in (summary.get("tool_counts") or {})),
        "trajectory_length": int(trajectory.get("num_agent_steps") or 0),
        "labels": {"resolved": resolved},
    }


def validate_foundation_record(record: Mapping) -> None:
    try:
        payload = dict(record)
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise FoundationRecordError(
            f"foundation record must be canonical JSON: {exc}"
        ) from exc
    validator = Draft202012Validator(
        load_schema("foundation-training-record.schema.json")
    )
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: list(error.path),
    )
    if errors:
        detail = "; ".join(error.message for error in errors)
        raise FoundationRecordError(detail)


def _is_safe_numeric_feature(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def _render_trajectory_payload(value) -> dict:
    if not isinstance(value, Mapping):
        return {}
    payload = {
        name: value[name]
        for name in _TRAJECTORY_PROMPT_FIELDS
        if name in value and _is_safe_numeric_feature(value[name])
    }
    if value.get("timestamp_provenance") == "synthetic-ordinal":
        payload["timestamp_provenance"] = "synthetic-ordinal"
    return payload


def _render_observable_summary(value) -> dict:
    if not isinstance(value, Mapping):
        return {}
    payload = {
        name: value[name]
        for name in _OBSERVABLE_NUMERIC_PROMPT_FIELDS
        if name in value and _is_safe_numeric_feature(value[name])
    }
    return payload


def _render_feature_refs(value) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return sorted(
        item
        for item in value
        if isinstance(item, str) and item in _REVIEWED_FEATURE_REFS
    )


def _render_objective_payload(value) -> dict:
    if value is _MISSING:
        return {"present": False, "text_length": 0}
    if not isinstance(value, Mapping):
        raise FoundationRecordError("objective must be a mapping")
    present = value.get("present", False)
    text_length = value.get("text_length", 0)
    if type(present) is not bool:
        raise FoundationRecordError("objective.present must be a bool")
    if type(text_length) is not int or text_length < 0:
        raise FoundationRecordError(
            "objective.text_length must be a nonnegative integer"
        )
    return {"present": present, "text_length": text_length}


def render_prompt_payload(example: Mapping) -> dict:
    input_value = example.get("input") or {}
    return {
        "prefix": "full" if input_value.get("prefix") == "full" else None,
        "trajectory": _render_trajectory_payload(input_value.get("trajectory")),
        "observable_summary": _render_observable_summary(
            input_value.get("observable_summary")
        ),
        "objective": _render_objective_payload(
            input_value.get("objective", _MISSING)
        ),
        "feature_refs": _render_feature_refs(input_value.get("feature_refs")),
    }


def render_foundation_record(
    example: Mapping,
    *,
    lane_disposition: LaneDisposition,
    split_assignment: Mapping,
    tokenizer,
    tokenizer_revision: str,
    source_receipt_hashes: tuple[str, ...],
) -> dict:
    resolved = _validated_resolved_target(example)
    dataset_family = _required_nonempty_string(
        example.get("dataset_family"),
        field="dataset_family",
    )
    dataset_id = _required_nonempty_string(
        example.get("dataset_id"),
        field="dataset_id",
    )
    example_id = _required_nonempty_string(
        example.get("example_id"),
        field="example_id",
    )
    if not isinstance(split_assignment, Mapping):
        raise FoundationRecordError("split_assignment must be a mapping")
    split_id = _required_nonempty_string(
        split_assignment.get("split_id"),
        field="split_id",
    )
    source_revision = _validated_source_revision(example.get("source_revision"))
    tokenizer_revision = _validated_tokenizer_revision(tokenizer_revision)
    prompt_text = json.dumps(
        render_prompt_payload(example),
        sort_keys=True,
        separators=(",", ":"),
    )
    try:
        target_text = json.dumps(
            dict(example["target"]),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise FoundationRecordError(
            f"target must be canonical JSON: {exc}"
        ) from exc
    prompt_tokens = len(tokenizer.encode(prompt_text, add_special_tokens=False))
    target_tokens = len(tokenizer.encode(target_text, add_special_tokens=False))
    source = {
        "dataset_family": dataset_family,
        "lane_id": dataset_id,
        "source_record_id": example_id,
        "source_revision": source_revision,
        "receipt_hashes": sorted(source_receipt_hashes),
    }
    identity = foundation_identity(example, prompt_text=prompt_text)
    payload = {
        "record_kind": "pneuma_foundation_training_record",
        "record_schema_version": "0.1.0",
        "record_id": "ftr:"
        + hashlib.sha256(
            json.dumps(source, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "source": source,
        "disposition": asdict(lane_disposition),
        "identity": identity,
        "split": {
            "split_id": split_id,
            "quarantine_id": split_assignment.get("quarantine_id"),
        },
        "rendered": {"prompt_text": prompt_text, "target_text": target_text},
        "tokenization": {
            "tokenizer_id": "Qwen/Qwen3.5-2B",
            "tokenizer_revision": tokenizer_revision,
            "prompt_tokens": prompt_tokens,
            "target_tokens": target_tokens,
            "total_tokens": prompt_tokens + target_tokens,
        },
        "training_weight": 0.0,
        "forecast_targets": _forecast_targets(resolved),
        "observations": foundation_observations(example, resolved=resolved),
    }
    validate_foundation_record(payload)
    return payload


def validate_derived_foundation_record(
    record: Mapping,
    *,
    example: Mapping,
    split_assignment: Mapping,
    lane_disposition: LaneDisposition,
    source_receipt_hashes: tuple[str, ...],
    tokenizer_id: str,
    tokenizer_revision: str,
) -> None:
    """Prove one record is the deterministic rendering of one source example."""

    validate_foundation_record(record)
    if not isinstance(example, Mapping):
        raise FoundationRecordError("conversion example must be a mapping")
    if not isinstance(example.get("input"), Mapping):
        raise FoundationRecordError("conversion example input must be a mapping")
    resolved = _validated_resolved_target(example)
    dataset_family = _required_nonempty_string(
        example.get("dataset_family"),
        field="dataset_family",
    )
    dataset_id = _required_nonempty_string(
        example.get("dataset_id"),
        field="dataset_id",
    )
    example_id = _required_nonempty_string(
        example.get("example_id"),
        field="example_id",
    )
    source_revision = _validated_source_revision(example.get("source_revision"))
    if not isinstance(split_assignment, Mapping):
        raise FoundationRecordError("split_assignment must be a mapping")
    split_id = _required_nonempty_string(
        split_assignment.get("split_id"),
        field="split_id",
    )
    if not isinstance(lane_disposition, LaneDisposition):
        raise FoundationRecordError("lane_disposition must be a LaneDisposition")
    tokenizer_revision = _validated_tokenizer_revision(tokenizer_revision)
    if not isinstance(tokenizer_id, str) or not tokenizer_id:
        raise FoundationRecordError("tokenizer_id must be a nonempty string")

    prompt_text = json.dumps(
        render_prompt_payload(example),
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    try:
        target_text = json.dumps(
            dict(example["target"]),
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise FoundationRecordError(
            f"target must be canonical JSON: {exc}"
        ) from exc
    receipt_hashes = sorted(source_receipt_hashes)
    source = {
        "dataset_family": dataset_family,
        "lane_id": dataset_id,
        "source_record_id": example_id,
        "source_revision": source_revision,
        "receipt_hashes": receipt_hashes,
    }
    tokenization = record.get("tokenization")
    if not isinstance(tokenization, Mapping):
        raise FoundationRecordError("record tokenization is missing")
    prompt_tokens = tokenization.get("prompt_tokens")
    target_tokens = tokenization.get("target_tokens")
    total_tokens = tokenization.get("total_tokens")
    if (
        type(prompt_tokens) is not int
        or prompt_tokens <= 0
        or type(target_tokens) is not int
        or target_tokens <= 0
        or type(total_tokens) is not int
        or total_tokens != prompt_tokens + target_tokens
    ):
        raise FoundationRecordError(
            "record token counts must be positive and sum exactly"
        )
    expected = {
        "record_kind": "pneuma_foundation_training_record",
        "record_schema_version": "0.1.0",
        "record_id": "ftr:"
        + hashlib.sha256(
            json.dumps(source, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "source": source,
        "disposition": asdict(lane_disposition),
        "identity": foundation_identity(example, prompt_text=prompt_text),
        "split": {
            "split_id": split_id,
            "quarantine_id": split_assignment.get("quarantine_id"),
        },
        "rendered": {
            "prompt_text": prompt_text,
            "target_text": target_text,
        },
        "tokenization": {
            "tokenizer_id": tokenizer_id,
            "tokenizer_revision": tokenizer_revision,
            "prompt_tokens": prompt_tokens,
            "target_tokens": target_tokens,
            "total_tokens": total_tokens,
        },
        "training_weight": 0.0,
        "forecast_targets": _forecast_targets(resolved),
        "observations": foundation_observations(example, resolved=resolved),
    }
    if dict(record) != expected:
        raise FoundationRecordError(
            "foundation record differs from its deterministic conversion derivation"
        )


__all__ = [
    "EffectiveTrainingRecord",
    "FoundationRecordError",
    "GradientEligibility",
    "LaneDisposition",
    "TerminalRole",
    "foundation_identity",
    "foundation_observations",
    "render_foundation_record",
    "render_prompt_payload",
    "validate_derived_foundation_record",
    "validate_foundation_record",
]

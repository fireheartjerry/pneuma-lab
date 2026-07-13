"""Deterministic, zero-weight records for guarded foundation training."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import math

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


def _forecast_targets(example: Mapping) -> dict[str, dict]:
    resolved = bool((example.get("target") or {}).get("resolved"))
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


def foundation_observations(example: Mapping) -> dict:
    input_value = example.get("input") or {}
    summary = input_value.get("observable_summary") or {}
    trajectory = input_value.get("trajectory") or {}
    target = example.get("target") or {}
    return {
        "language": str(input_value.get("language") or "unknown"),
        "tools": sorted(str(name) for name in (summary.get("tool_counts") or {})),
        "trajectory_length": int(trajectory.get("num_agent_steps") or 0),
        "labels": {"resolved": bool(target.get("resolved"))},
    }


def validate_foundation_record(record: Mapping) -> None:
    validator = Draft202012Validator(
        load_schema("foundation-training-record.schema.json")
    )
    errors = sorted(
        validator.iter_errors(dict(record)),
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


def render_prompt_payload(example: Mapping) -> dict:
    input_value = example.get("input") or {}
    objective = input_value.get("objective") or {}
    return {
        "prefix": "full" if input_value.get("prefix") == "full" else None,
        "trajectory": _render_trajectory_payload(input_value.get("trajectory")),
        "observable_summary": _render_observable_summary(
            input_value.get("observable_summary")
        ),
        "objective": {
            "present": bool(objective.get("present")),
            "text_length": int(objective.get("text_length") or 0),
        },
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
    prompt_text = json.dumps(
        render_prompt_payload(example),
        sort_keys=True,
        separators=(",", ":"),
    )
    target_text = json.dumps(example["target"], sort_keys=True, separators=(",", ":"))
    prompt_tokens = len(tokenizer.encode(prompt_text, add_special_tokens=False))
    target_tokens = len(tokenizer.encode(target_text, add_special_tokens=False))
    source = {
        "dataset_family": str(example["dataset_family"]),
        "lane_id": str(example["dataset_id"]),
        "source_record_id": str(example["example_id"]),
        "source_revision": example.get("source_revision"),
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
            "split_id": str(split_assignment["split_id"]),
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
        "forecast_targets": _forecast_targets(example),
        "observations": foundation_observations(example),
    }
    validate_foundation_record(payload)
    return payload


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
    "validate_foundation_record",
]

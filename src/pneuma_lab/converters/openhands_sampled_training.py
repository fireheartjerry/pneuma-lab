"""Fixture-first OpenHands sampled PneumaTrainingExample conversion.

This module converts already-built ``PneumaTrace`` dictionaries into
observable-only, conservative ``PneumaTrainingExample`` records. It does not
read raw datasets, write processed outputs, train models, or authorize training.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from pneuma_lab.estimators.features import FEATURE_EXTRACTOR_VERSION, agentFrames

DATASET_ID = "swe-gym-openhands-sampled"
DATASET_FAMILY = "swe-gym"
SOURCE_REVISION = "baf3a4e4bff514d48ddc08a93a2ade5c126212c7"
TASK_TYPE = "RISK_PREDICTION"
CONVERTER_VERSION = "openhands-sampled-training/0.1.0"
DEFAULT_ADAPTER_REPORT_REF = (
    "fixtures/adapters/openhands_sampled/golden/adapter_report.json"
)


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _resolved_label(trace: dict) -> bool:
    labels = trace.get("labels") or {}
    outcome = trace.get("outcome") or {}
    label_resolved = labels.get("resolved")
    outcome_resolved = outcome.get("resolved")
    report_resolved = (outcome.get("report") or {}).get("resolved")

    observed = [
        bool(value)
        for value in (label_resolved, outcome_resolved, report_resolved)
        if value is not None
    ]
    if not observed:
        raise ValueError("trace is missing resolved outcome")
    if any(value != observed[0] for value in observed):
        raise ValueError("trace has conflicting resolved labels")
    return observed[0]


def _tool_counts(frames: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for frame in frames:
        for call in frame.get("tool_calls") or []:
            tool = str(call.get("tool") or "unknown")
            counts[tool] = counts.get(tool, 0) + 1
    return dict(sorted(counts.items()))


def _observable_summary(frames: list[dict]) -> dict:
    tool_counts = _tool_counts(frames)
    retries = [int(frame.get("retry_count") or 0) for frame in frames]
    assistant_lengths = [
        int(frame.get("assistant_text_length") or 0) for frame in frames
    ]
    observation_lengths: list[int] = []
    error_count = 0
    observation_count = 0

    for frame in frames:
        for observation in frame.get("observations") or []:
            observation_count += 1
            observation_lengths.append(int(observation.get("content_length") or 0))
            if observation.get("error_marker"):
                error_count += 1

    step_count = len(frames)
    return {
        "tool_call_count": sum(tool_counts.values()),
        "tool_counts": tool_counts,
        "retry_count_max": max(retries) if retries else 0,
        "retry_count_mean": (sum(retries) / step_count) if step_count else 0.0,
        "steps_retry_ge2": sum(1 for retry in retries if retry >= 2),
        "strategy_switches_final": (
            int(frames[-1].get("strategy_switches") or 0) if frames else 0
        ),
        "error_observation_count": error_count,
        "observation_count": observation_count,
        "error_density": (
            error_count / observation_count if observation_count else 0.0
        ),
        "assistant_text_length_mean": (
            sum(assistant_lengths) / step_count if step_count else 0.0
        ),
        "assistant_text_length_max": (
            max(assistant_lengths) if assistant_lengths else 0
        ),
        "observation_length_mean": (
            sum(observation_lengths) / observation_count
            if observation_count
            else 0.0
        ),
        "observation_length_max": (
            max(observation_lengths) if observation_lengths else 0
        ),
    }


def _input_payload(trace: dict) -> dict:
    frames = agentFrames(trace)
    labels = trace.get("labels") or {}
    provenance = trace.get("provenance") or {}
    trajectory = trace.get("trajectory") or {}
    first_world = next(
        (
            frame
            for frame in trace.get("frames") or []
            if frame.get("frame_kind") == "world"
        ),
        {},
    )
    objective = first_world.get("objective") or {}
    objective_text = objective.get("text")
    objective_meta = {"present": bool(objective_text), "mode": "digest_only"}
    if isinstance(objective_text, str):
        objective_meta["text_sha256"] = "sha256:" + hashlib.sha256(
            objective_text.encode("utf-8")
        ).hexdigest()
        objective_meta["text_length"] = len(objective_text)

    return {
        "trace_id": trace.get("trace_id"),
        "run_id": trace.get("run_id"),
        "task_id": labels.get("instance_id") or provenance.get("source_id"),
        "repo": labels.get("repo"),
        "prefix": "full",
        "trajectory": {
            "num_messages": trajectory.get("num_messages", 0),
            "num_agent_steps": trajectory.get("num_agent_steps", len(frames)),
            "timestamp_provenance": trajectory.get("timestamp_provenance"),
        },
        "observable_summary": _observable_summary(frames),
        "objective": objective_meta,
        "feature_refs": [FEATURE_EXTRACTOR_VERSION, CONVERTER_VERSION],
    }


def convert_trace(
    trace: dict,
    *,
    adapter_report_ref: str = DEFAULT_ADAPTER_REPORT_REF,
    synthetic_fixture_ref: str | None = None,
) -> dict:
    """Convert one processed OpenHands sampled PneumaTrace into one example."""
    resolved = _resolved_label(trace)
    trace_id = str(trace.get("trace_id") or "")
    if not trace_id:
        raise ValueError("trace is missing trace_id")
    labels = trace.get("labels") or {}
    provenance = trace.get("provenance") or {}
    build = trace.get("build") or {}
    source_hash = build.get("content_hash") or _short_hash(trace_id)
    task_id = labels.get("instance_id") or provenance.get("source_id")

    evidence_refs = [
        {"kind": "trace_id", "ref": trace_id},
        {"kind": "adapter_report", "ref": adapter_report_ref},
        {"kind": "schema", "ref": "schemas/pneuma-training-example.schema.json"},
    ]
    if synthetic_fixture_ref:
        evidence_refs.append({"kind": "synthetic_fixture", "ref": synthetic_fixture_ref})

    return {
        "example_id": f"pte:{DATASET_ID}:{source_hash}:risk:full",
        "dataset_id": DATASET_ID,
        "dataset_family": DATASET_FAMILY,
        "source_path_or_hash": f"sha256:{source_hash}",
        "source_revision": provenance.get("hf_revision") or SOURCE_REVISION,
        "example_type": "TrajectoryExample",
        "input_modality": "structured_features",
        "task_type": TASK_TYPE,
        "task_mask": [TASK_TYPE],
        "input": _input_payload(trace),
        "target": {"resolved": resolved},
        "label_provenance": {
            "kind": "harness_outcome",
            "description": (
                "SWE-Gym/OpenHands sampled harness outcome carried through "
                "the PneumaTrace envelope."
            ),
            "confidence": "high",
        },
        "privacy_status": "redaction_verified",
        "redaction_receipt": {
            "status": "verified",
            "report_ref": adapter_report_ref + "#privacy.redaction_totals",
        },
        "leakage_risk": "medium",
        "allowed_training_uses": [
            "schema validation",
            "feature extraction planning",
            "later modeling only after separate approval",
        ],
        "blocked_training_uses": [
            "current-pass training",
            "E1/E2 execution",
            "calibration",
            "runtime integration",
            "J-space/Jacobian Lens work",
            "SWE-chat processing",
            "consciousness claims",
        ],
        "model_use_tier": "train_after_adapter",
        "training_weight": 0.0,
        "split_policy": "repo_grouped",
        "split_group": {
            "repo": labels.get("repo"),
            "task_id": task_id,
            "session_or_user": None,
            "era": None,
        },
        "canonical_feature_refs": [FEATURE_EXTRACTOR_VERSION, CONVERTER_VERSION],
        "evidence_refs": evidence_refs,
    }


def convert_traces(
    traces: Iterable[dict],
    *,
    adapter_report_ref: str = DEFAULT_ADAPTER_REPORT_REF,
    synthetic_fixture_ref: str | None = None,
) -> list[dict]:
    """Convert traces in input order, one full-trace example per trace."""
    return [
        convert_trace(
            trace,
            adapter_report_ref=adapter_report_ref,
            synthetic_fixture_ref=synthetic_fixture_ref,
        )
        for trace in traces
    ]


__all__ = [
    "CONVERTER_VERSION",
    "DATASET_FAMILY",
    "DATASET_ID",
    "TASK_TYPE",
    "convert_trace",
    "convert_traces",
]

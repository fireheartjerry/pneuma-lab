"""Fixture-first OpenHands sampled PneumaTrainingExample conversion.

This module converts already-built ``PneumaTrace`` dictionaries into
observable-only, conservative ``PneumaTrainingExample`` records. It does not
read raw datasets, write processed outputs, train models, or authorize training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Iterable
from pathlib import Path

from pneuma_lab.estimators.features import FEATURE_EXTRACTOR_VERSION, agentFrames
from pneuma_lab.schemas import load_schema

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - pyproject requires jsonschema.
    Draft202012Validator = None

DATASET_ID = "swe-gym-openhands-sampled"
DATASET_FAMILY = "swe-gym"
SOURCE_REVISION = "baf3a4e4bff514d48ddc08a93a2ade5c126212c7"
TASK_TYPE = "RISK_PREDICTION"
CONVERTER_VERSION = "openhands-sampled-training/0.1.0"
TRAINING_EXAMPLE_SCHEMA = "pneuma-training-example.schema.json"
BOUNDED_SAMPLE_MODE = "bounded-sample"
RECOMMENDED_BOUNDED_LIMIT = 10
MAX_BOUNDED_LIMIT = 25
DEFAULT_ADAPTER_REPORT_REF = (
    "fixtures/adapters/openhands_sampled/golden/adapter_report.json"
)
DEFAULT_BUILD_DIR = Path("build") / "training_examples" / "openhands-sampled" / "bounded-sample"
DEFAULT_EXAMPLES_OUT = DEFAULT_BUILD_DIR / "examples.jsonl"
DEFAULT_REPORT_OUT = DEFAULT_BUILD_DIR / "conversion_report.json"
DEFAULT_HASH_MANIFEST_OUT = DEFAULT_BUILD_DIR / "hash_manifest.json"
FORBIDDEN_INPUT_PATH_PARTS = ("swe-chat", "/raw/", "\\raw\\")
FORBIDDEN_OUTPUT_ROOT = Path("C:/pneuma-data")


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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
    manifest_ref: str | None = None,
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
    if manifest_ref:
        evidence_refs.append({"kind": "manifest", "ref": manifest_ref})

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
    manifest_ref: str | None = None,
) -> list[dict]:
    """Convert traces in input order, one full-trace example per trace."""
    return [
        convert_trace(
            trace,
            adapter_report_ref=adapter_report_ref,
            synthetic_fixture_ref=synthetic_fixture_ref,
            manifest_ref=manifest_ref,
        )
        for trace in traces
    ]


def validate_limit(limit: int) -> None:
    """Reject missing, non-positive, or too-large bounded sample limits."""
    if limit <= 0:
        raise ValueError("--limit must be positive")
    if limit > MAX_BOUNDED_LIMIT:
        raise ValueError(f"--limit must be <= {MAX_BOUNDED_LIMIT}")


def reject_forbidden_input_path(path: str | os.PathLike[str]) -> None:
    """Fail closed for paths outside the processed OpenHands sampled surface."""
    normalized = str(path).replace("\\", "/").lower()
    for part in FORBIDDEN_INPUT_PATH_PARTS:
        if part.replace("\\", "/") in normalized:
            raise ValueError(f"forbidden input path for bounded conversion: {path}")


def reject_forbidden_output_path(path: str | os.PathLike[str]) -> None:
    """Prevent bounded conversion from writing into C:/pneuma-data."""
    resolved = Path(path).resolve()
    forbidden = FORBIDDEN_OUTPUT_ROOT.resolve()
    if resolved == forbidden or forbidden in resolved.parents:
        raise ValueError(f"refusing to write bounded output under {FORBIDDEN_OUTPUT_ROOT}")


def read_bounded_trace_lines(lines: Iterable[str], limit: int) -> list[dict]:
    """Parse at most ``limit`` JSONL records from an iterable, then stop."""
    validate_limit(limit)
    traces: list[dict] = []
    iterator = iter(lines)
    while len(traces) < limit:
        try:
            line = next(iterator)
        except StopIteration:
            break
        if line.strip():
            traces.append(json.loads(line))
    if len(traces) < limit:
        raise ValueError(f"requested {limit} traces, found {len(traces)}")
    return traces


def read_bounded_traces(path: str | os.PathLike[str], limit: int) -> list[dict]:
    """Read only the first ``limit`` processed trace JSONL records."""
    reject_forbidden_input_path(path)
    with open(path, encoding="utf-8") as fh:
        return read_bounded_trace_lines(fh, limit)


def load_adapter_report(path: str | os.PathLike[str]) -> dict:
    """Load adapter report metadata without touching trace content."""
    reject_forbidden_input_path(path)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def validate_training_examples(examples: list[dict]) -> None:
    """Validate every emitted example against the training-example schema."""
    if Draft202012Validator is None:
        raise RuntimeError("jsonschema is required for training example validation")
    schema = load_schema(TRAINING_EXAMPLE_SCHEMA)
    validator = Draft202012Validator(schema)
    for index, example in enumerate(examples):
        errors = sorted(validator.iter_errors(example), key=lambda err: list(err.path))
        if errors:
            message = "; ".join(error.message for error in errors)
            raise ValueError(f"example {index} failed schema validation: {message}")


def _jsonl_bytes(examples: list[dict]) -> str:
    return "".join(_canonical_json(example) + "\n" for example in examples)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_atomic(path: str | os.PathLike[str], text: str) -> None:
    reject_forbidden_output_path(path)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, target)


def build_conversion_report(
    *,
    input_path: str | os.PathLike[str],
    adapter_report_path: str | os.PathLike[str],
    adapter_report: dict,
    limit: int,
    traces: list[dict],
    examples: list[dict],
) -> dict:
    """Build deterministic bounded conversion metadata."""
    return {
        "conversion_report_schema_version": "0.1.0",
        "mode": BOUNDED_SAMPLE_MODE,
        "converter": {
            "name": "openhands-sampled-training",
            "version": CONVERTER_VERSION,
        },
        "dataset_id": DATASET_ID,
        "dataset_family": DATASET_FAMILY,
        "input": {
            "trace_jsonl": str(input_path),
            "adapter_report": str(adapter_report_path),
            "requested_limit": limit,
            "loaded_traces": len(traces),
            "selection": "first_n_adapter_emission_order",
        },
        "output": {
            "examples_emitted": len(examples),
            "invalid_examples": 0,
            "quarantined_examples": 0,
        },
        "source_hashes": {
            "traces_file_sha256": adapter_report.get("traces_file_sha256"),
            "trace_index_file_sha256": adapter_report.get("trace_index_file_sha256"),
            "invalid_traces_file_sha256": adapter_report.get(
                "invalid_traces_file_sha256"
            ),
        },
        "source_counts": adapter_report.get("counts", {}),
        "privacy": adapter_report.get("privacy", {}),
        "schema": {
            "training_example": TRAINING_EXAMPLE_SCHEMA,
        },
        "training_authorization": {
            "model_use_tier": "train_after_adapter",
            "training_weight": 0.0,
        },
        "warnings": [],
    }


def build_hash_manifest(
    *,
    examples_text: str,
    report_text: str,
    limit: int,
    input_path: str | os.PathLike[str],
    adapter_report_path: str | os.PathLike[str],
) -> dict:
    """Build deterministic content hashes for bounded outputs."""
    return {
        "hash_manifest_schema_version": "0.1.0",
        "mode": BOUNDED_SAMPLE_MODE,
        "dataset_id": DATASET_ID,
        "converter_version": CONVERTER_VERSION,
        "input": {
            "trace_jsonl": str(input_path),
            "adapter_report": str(adapter_report_path),
            "requested_limit": limit,
        },
        "hashes": {
            "examples_jsonl_sha256": _sha256_text(examples_text),
            "conversion_report_json_sha256": _sha256_text(report_text),
        },
    }


def run_bounded_sample_conversion(
    *,
    input_path: str | os.PathLike[str],
    adapter_report_path: str | os.PathLike[str],
    examples_path: str | os.PathLike[str] = DEFAULT_EXAMPLES_OUT,
    report_path: str | os.PathLike[str] = DEFAULT_REPORT_OUT,
    hash_manifest_path: str | os.PathLike[str] = DEFAULT_HASH_MANIFEST_OUT,
    limit: int,
) -> dict:
    """Run the bounded processed-sample conversion and write repo-local outputs."""
    validate_limit(limit)
    for output_path in (examples_path, report_path, hash_manifest_path):
        reject_forbidden_output_path(output_path)

    adapter_report = load_adapter_report(adapter_report_path)
    traces = read_bounded_traces(input_path, limit)
    manifest_ref = "bounded-sample/hash_manifest.json"
    examples = convert_traces(
        traces,
        adapter_report_ref=str(adapter_report_path),
        manifest_ref=manifest_ref,
    )
    validate_training_examples(examples)

    examples_text = _jsonl_bytes(examples)
    report = build_conversion_report(
        input_path=input_path,
        adapter_report_path=adapter_report_path,
        adapter_report=adapter_report,
        limit=limit,
        traces=traces,
        examples=examples,
    )
    report_text = _canonical_json(report) + "\n"
    manifest = build_hash_manifest(
        examples_text=examples_text,
        report_text=report_text,
        limit=limit,
        input_path=input_path,
        adapter_report_path=adapter_report_path,
    )
    manifest_text = _canonical_json(manifest) + "\n"
    manifest["hashes"]["hash_manifest_json_sha256"] = _sha256_text(manifest_text)
    manifest_text = _canonical_json(manifest) + "\n"

    _write_atomic(examples_path, examples_text)
    _write_atomic(report_path, report_text)
    _write_atomic(hash_manifest_path, manifest_text)

    return {
        "examples": examples,
        "report": report,
        "hash_manifest": manifest,
        "paths": {
            "examples": str(examples_path),
            "report": str(report_path),
            "hash_manifest": str(hash_manifest_path),
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pneuma_lab.converters.openhands_sampled_training"
    )
    parser.add_argument("--mode", required=True, choices=[BOUNDED_SAMPLE_MODE])
    parser.add_argument("--input", required=True)
    parser.add_argument("--adapter-report", required=True)
    parser.add_argument("--limit", required=True, type=int)
    parser.add_argument("--output", default=str(DEFAULT_EXAMPLES_OUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT_OUT))
    parser.add_argument("--hash-manifest", default=str(DEFAULT_HASH_MANIFEST_OUT))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = run_bounded_sample_conversion(
            input_path=args.input,
            adapter_report_path=args.adapter_report,
            examples_path=args.output,
            report_path=args.report,
            hash_manifest_path=args.hash_manifest,
            limit=args.limit,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        f"wrote {len(result['examples'])} bounded examples to {result['paths']['examples']}"
    )
    return 0


__all__ = [
    "BOUNDED_SAMPLE_MODE",
    "CONVERTER_VERSION",
    "DATASET_FAMILY",
    "DATASET_ID",
    "MAX_BOUNDED_LIMIT",
    "RECOMMENDED_BOUNDED_LIMIT",
    "TASK_TYPE",
    "build_conversion_report",
    "build_hash_manifest",
    "convert_trace",
    "convert_traces",
    "main",
    "read_bounded_trace_lines",
    "read_bounded_traces",
    "run_bounded_sample_conversion",
    "validate_training_examples",
]


if __name__ == "__main__":
    raise SystemExit(main())

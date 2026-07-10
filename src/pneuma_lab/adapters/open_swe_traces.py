"""Synthetic fixture-first Open-SWE-Traces training-example conversion.

This module converts tiny synthetic source dictionaries -- shaped like the
safe scalar surface a future stage-1 ``PneumaTrace`` adapter would also
expose (see ``docs/data/conversion/open-swe-traces-to-pneuma-trace.md``) --
into conservative ``PneumaTrainingExample`` records. It does not read real
parquet rows, run bounded/full conversion, write processed outputs, train
models, or authorize training.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from pneuma_lab.governance import open_swe_traces as governance
from pneuma_lab.schemas import load_schema

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - pyproject requires jsonschema.
    Draft202012Validator = None

DATASET_ID = governance.DATASET_ID
DATASET_FAMILY = governance.DATASET_FAMILY
SOURCE_REVISION = "474d016b4a35a0411a7f57183579eab8924e9ea5"
CONVERTER_VERSION = "open-swe-traces-adapter/0.1.0"
TRAINING_EXAMPLE_SCHEMA = "pneuma-training-example.schema.json"
SYNTHETIC_FIXTURE_REF = "fixtures/adapters/open_swe_traces/synthetic_source.json"
REGISTRY_REF = "docs/data/registry/open-swe-traces.json"
CONVERSION_PLAN_REF = "docs/data/conversion/open-swe-traces-to-pneuma-trace.md"


def _canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _short_hash(value: dict) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()[:16]


def _source_hash(record: dict) -> str:
    digest = (record.get("source") or {}).get("instance_id_digest")
    if isinstance(digest, str) and digest.startswith("sha256:"):
        return digest.removeprefix("sha256:")
    if isinstance(digest, str) and digest:
        return digest
    return _short_hash(record)


def _base_evidence_refs() -> list[dict]:
    return [
        {"kind": "synthetic_fixture", "ref": SYNTHETIC_FIXTURE_REF},
        {"kind": "manifest", "ref": REGISTRY_REF},
        {"kind": "manifest", "ref": CONVERSION_PLAN_REF},
        {"kind": "schema", "ref": f"schemas/{TRAINING_EXAMPLE_SCHEMA}"},
    ]


def _input_payload(record: dict) -> dict:
    dataset = record.get("dataset") or {}
    source = record.get("source") or {}
    trajectory_summary = record.get("trajectory_summary") or {}
    tool_summary = record.get("tool_summary") or {}
    return {
        "dataset": {
            "dataset_id": dataset.get("dataset_id", DATASET_ID),
            "dataset_family": dataset.get("dataset_family", DATASET_FAMILY),
            "source_group": dataset.get("source_group"),
            "hf_revision": dataset.get("hf_revision", SOURCE_REVISION),
        },
        "language": record.get("language"),
        "source": {
            "instance_id_digest": source.get("instance_id_digest"),
            "repo_digest": source.get("repo_digest"),
            "trajectory_id_digest": source.get("trajectory_id_digest"),
            "license": source.get("license"),
        },
        "trajectory_summary": {
            "num_messages": trajectory_summary.get("num_messages"),
            "num_agent_steps": trajectory_summary.get("num_agent_steps"),
        },
        "tool_summary": {
            "tool_call_count": tool_summary.get("tool_call_count"),
            "tool_counts": dict(tool_summary.get("tool_counts") or {}),
        },
        "feature_refs": [CONVERTER_VERSION],
    }


def convert_record(record: dict) -> list[dict]:
    """Convert one synthetic Open-SWE-Traces source record to training examples."""
    if record.get("resolved") is None:
        raise ValueError("synthetic record is missing resolved label")

    source_hash = _source_hash(record)
    source = record.get("source") or {}
    dataset = record.get("dataset") or {}
    input_payload = _input_payload(record)

    leakage = governance.check_example_input_leakage(
        {"task_type": "RISK_PREDICTION", "input": input_payload}
    )
    if leakage:
        raise ValueError(f"input payload failed leakage scan: {leakage}")

    example = {
        "example_id": f"pte:{DATASET_ID}:{source_hash}:risk-prediction",
        "dataset_id": DATASET_ID,
        "dataset_family": DATASET_FAMILY,
        "source_path_or_hash": f"sha256:{source_hash}",
        "source_revision": dataset.get("hf_revision") or SOURCE_REVISION,
        "example_type": "TrajectoryExample",
        "input_modality": "structured_features",
        "task_type": "RISK_PREDICTION",
        "task_mask": ["RISK_PREDICTION"],
        "input": input_payload,
        "target": {"resolved": bool(record["resolved"])},
        "label_provenance": {
            "kind": "constructed_label",
            "description": (
                "Open-SWE-Traces resolved is an automated verifier outcome over "
                "synthetic Minimax-M2.5/Qwen3.5 trajectories, not a human-graded "
                "judgment and not a Pneuma/9to5 harness result."
            ),
            "confidence": "medium",
        },
        "privacy_status": "public_or_benchmark",
        "redaction_receipt": {"status": "not_needed", "report_ref": None},
        "leakage_risk": "medium",
        "allowed_training_uses": [
            "synthetic schema validation",
            "fixture-first adapter validation",
        ],
        "blocked_training_uses": governance.blocked_training_uses(),
        "model_use_tier": governance.TRAINING_AUTHORIZATION_DEFAULTS["model_use_tier"],
        "training_weight": governance.TRAINING_AUTHORIZATION_DEFAULTS[
            "training_weight"
        ],
        "split_policy": "repo_grouped",
        "split_group": {
            "repo": source.get("repo_digest"),
            "task_id": source.get("instance_id_digest"),
            "session_or_user": None,
            "era": None,
        },
        "canonical_feature_refs": [CONVERTER_VERSION],
        "evidence_refs": _base_evidence_refs(),
    }

    label_findings = governance.validate_label_provenance(example["label_provenance"])
    if label_findings:
        raise ValueError(f"label provenance failed policy check: {label_findings}")

    return [example]


def convert_records(records: Iterable[dict]) -> list[dict]:
    """Convert synthetic records in input order."""
    examples: list[dict] = []
    for record in records:
        examples.extend(convert_record(record))
    return examples


def load_synthetic_records(path: str | Path) -> list[dict]:
    """Load committed synthetic fixtures, not real data."""
    fixture_path = Path(path)
    text = fixture_path.read_text(encoding="utf-8")
    if "C:/pneuma-data" in text or "C:\\pneuma-data" in text:
        raise ValueError("synthetic fixture must not reference C:/pneuma-data")
    return json.loads(text)


def build_conversion_report(*, records: list[dict], examples: list[dict]) -> dict:
    """Build metadata for the synthetic fixture-first conversion."""
    return {
        "conversion_report_schema_version": "0.1.0",
        "converter": {"name": "open-swe-traces-adapter", "version": CONVERTER_VERSION},
        "dataset_id": DATASET_ID,
        "dataset_family": DATASET_FAMILY,
        "mode": "synthetic-fixture-only",
        "source": {
            "fixture": SYNTHETIC_FIXTURE_REF,
            "records_loaded": len(records),
            "real_data_conversion": False,
            "bounded_conversion": False,
            "raw_trajectory_rows_inspected": False,
        },
        "output": {
            "examples_emitted": len(examples),
            "task_types": sorted({example["task_type"] for example in examples}),
            "source_groups_seen": sorted(
                {
                    (record.get("dataset") or {}).get("source_group")
                    for record in records
                    if (record.get("dataset") or {}).get("source_group")
                }
            ),
        },
        "license": {
            "artifact_license": "cc-by-4.0",
            "third_party_model_output_tos_reviewed": False,
            "review_required_before_training_authorization": True,
        },
        "training_authorization": dict(governance.TRAINING_AUTHORIZATION_DEFAULTS),
        "leakage_controls": {
            "raw_trajectory_text_included": False,
            "raw_tool_payload_included": False,
            "raw_patch_text_included": False,
            "oracle_lists_included": False,
            "final_outcomes_in_input": False,
            "cross_dataset_leakage_registry_exists": False,
        },
    }


def validate_training_examples(examples: list[dict]) -> None:
    """Validate emitted examples against the training-example schema."""
    if Draft202012Validator is None:
        raise RuntimeError("jsonschema is required for training example validation")
    validator = Draft202012Validator(load_schema(TRAINING_EXAMPLE_SCHEMA))
    for index, example in enumerate(examples):
        errors = sorted(validator.iter_errors(example), key=lambda err: list(err.path))
        if errors:
            message = "; ".join(error.message for error in errors)
            raise ValueError(f"example {index} failed schema validation: {message}")


__all__ = [
    "CONVERTER_VERSION",
    "DATASET_FAMILY",
    "DATASET_ID",
    "SOURCE_REVISION",
    "SYNTHETIC_FIXTURE_REF",
    "build_conversion_report",
    "convert_record",
    "convert_records",
    "load_synthetic_records",
    "validate_training_examples",
]

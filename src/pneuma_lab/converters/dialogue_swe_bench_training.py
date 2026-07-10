"""Synthetic fixture-first Dialogue SWE-Bench training example conversion.

This module converts tiny synthetic source dictionaries into conservative
``PneumaTrainingExample`` records. It does not read real parquet rows, run
bounded/full conversion, write processed outputs, train models, or authorize
training.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from pneuma_lab.schemas import load_schema

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - pyproject requires jsonschema.
    Draft202012Validator = None

DATASET_ID = "dialogue-swe-bench"
DATASET_FAMILY = "dialogue-swe-bench"
SOURCE_REVISION = "88f083e830d9cd48e19470aa887a9df2914d3547"
CONVERTER_VERSION = "dialogue-swe-bench-training/0.1.0"
TRAINING_EXAMPLE_SCHEMA = "pneuma-training-example.schema.json"
SYNTHETIC_FIXTURE_REF = (
    "fixtures/training_examples/dialogue_swe_bench_synthetic_source.json"
)
REGISTRY_REF = "docs/data/archive/dialogue-swe-bench/registry.json"
CONVERSION_PLAN_REF = "docs/data/archive/dialogue-swe-bench/conversion.md"
LICENSE_BLOCKED_USE = (
    "training blocked until upstream license review resolves local null license"
)
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


def _canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _short_hash(value: dict) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()[:16]


def _source_hash(record: dict) -> str:
    source = record.get("source") or {}
    digest = source.get("source_record_digest")
    if isinstance(digest, str) and digest.startswith("sha256:"):
        return digest.removeprefix("sha256:")
    if isinstance(digest, str) and digest:
        return digest
    return _short_hash(record)


def _blocked_training_uses() -> list[str]:
    return [
        LICENSE_BLOCKED_USE,
        "real model training",
        "E1/E2 execution",
        "calibration",
        "runtime integration",
        "J-space/Jacobian Lens work",
        "SWE-chat processing",
        "raw dialogue row content inspection",
        "real-human operator behavior claims",
        "consciousness or Level 4/5 claims",
    ]


def _base_evidence_refs() -> list[dict]:
    return [
        {"kind": "synthetic_fixture", "ref": SYNTHETIC_FIXTURE_REF},
        {"kind": "manifest", "ref": REGISTRY_REF},
        {"kind": "manifest", "ref": CONVERSION_PLAN_REF},
        {"kind": "schema", "ref": "schemas/pneuma-training-example.schema.json"},
    ]


def _input_payload(record: dict, *, task_type: str) -> dict:
    dataset = record.get("dataset") or {}
    source = record.get("source") or {}
    task = record.get("task") or {}
    dialogue = record.get("dialogue_structure") or {}
    change = record.get("change_structure") or {}
    dialogue_summary = {
        "turn_count": dialogue.get("turn_count"),
        "role_sequence": list(dialogue.get("role_sequence") or []),
        "turn_length_summary": dict(dialogue.get("turn_length_summary") or {}),
    }
    if task_type != "OPERATOR_PUSHBACK":
        dialogue_summary["simulated_correction_count"] = dialogue.get(
            "simulated_correction_count"
        )

    return {
        "dataset": {
            "dataset_id": DATASET_ID,
            "dataset_family": DATASET_FAMILY,
            "source_split": source.get("split"),
            "source_file_sha256": source.get("source_file_sha256"),
            "source_row": source.get("source_row"),
            "license_status": dataset.get("license_status"),
            "license_review_required": bool(
                dataset.get("license_review_required", True)
            ),
        },
        "task": {
            "instance_id": task.get("instance_id"),
            "repo": task.get("repo"),
            "base_commit": task.get("base_commit"),
            "persona": task.get("persona"),
        },
        "dialogue_summary": dialogue_summary,
        "code_change_summary": {
            "has_change": bool(change.get("has_change")),
            "has_tests": bool(change.get("has_tests")),
            "code_change_sha256": change.get("change_sha256"),
            "test_change_sha256": change.get("test_change_sha256"),
            "text_included": False,
            "oracle_lists_included": False,
        },
        "feature_refs": [CONVERTER_VERSION],
    }


def _base_example(
    record: dict, *, task_type: str, example_type: str, target: dict
) -> dict:
    source_hash = _source_hash(record)
    task = record.get("task") or {}
    source = record.get("source") or {}
    return {
        "dataset_id": DATASET_ID,
        "dataset_family": DATASET_FAMILY,
        "source_path_or_hash": f"sha256:{source_hash}",
        "source_revision": (
            (record.get("dataset") or {}).get("source_revision") or SOURCE_REVISION
        ),
        "example_type": example_type,
        "input_modality": "dialogue",
        "task_type": task_type,
        "task_mask": [task_type],
        "input": _input_payload(record, task_type=task_type),
        "target": target,
        "privacy_status": "public_or_benchmark",
        "redaction_receipt": {
            "status": "not_needed",
            "report_ref": None,
        },
        "leakage_risk": "medium",
        "allowed_training_uses": [
            "synthetic schema validation",
            "fixture-first converter validation",
        ],
        "blocked_training_uses": _blocked_training_uses(),
        "model_use_tier": "blocked",
        "training_weight": 0.0,
        "split_policy": "task_grouped",
        "split_group": {
            "repo": task.get("repo"),
            "task_id": task.get("instance_id"),
            "session_or_user": None,
            "era": source.get("split"),
        },
        "canonical_feature_refs": [CONVERTER_VERSION],
        "evidence_refs": _base_evidence_refs(),
    }


def convert_record(record: dict) -> list[dict]:
    """Convert one synthetic Dialogue SWE-Bench source record."""
    source_hash = _source_hash(record)
    task = record.get("task") or {}
    difficulty = task.get("difficulty")
    if not difficulty:
        raise ValueError("synthetic record is missing difficulty label")

    difficulty_example = _base_example(
        record,
        task_type="TASK_DIFFICULTY",
        example_type="TaskExample",
        target={"difficulty": difficulty},
    )
    difficulty_example.update(
        {
            "example_id": f"pte:{DATASET_ID}:{source_hash}:task-difficulty",
            "label_provenance": {
                "kind": "source_label",
                "description": (
                    "Synthetic fixture carries a Dialogue SWE-Bench difficulty "
                    "source label; training remains blocked until upstream "
                    "license review resolves the local null license."
                ),
                "confidence": "medium",
            },
        }
    )

    examples = [difficulty_example]
    simulated_labels = record.get("simulated_labels") or {}
    if "operator_pushback" in simulated_labels:
        pushback_example = _base_example(
            record,
            task_type="OPERATOR_PUSHBACK",
            example_type="TaskExample",
            target={"simulated_pushback": bool(simulated_labels["operator_pushback"])},
        )
        pushback_example.update(
            {
                "example_id": f"pte:{DATASET_ID}:{source_hash}:operator-pushback",
                "label_provenance": {
                    "kind": "simulated_label",
                    "description": (
                        "Explicit synthetic simulated operator-pushback label; "
                        "not a real-human operator behavior label and not "
                        "training-authorized while license review is unresolved."
                    ),
                    "confidence": "low",
                },
            }
        )
        examples.append(pushback_example)

    return examples


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
        "converter": {
            "name": "dialogue-swe-bench-training",
            "version": CONVERTER_VERSION,
        },
        "dataset_id": DATASET_ID,
        "dataset_family": DATASET_FAMILY,
        "mode": "synthetic-fixture-only",
        "source": {
            "fixture": SYNTHETIC_FIXTURE_REF,
            "records_loaded": len(records),
            "real_data_conversion": False,
            "bounded_conversion": False,
            "raw_dialogue_rows_inspected": False,
        },
        "output": {
            "examples_emitted": len(examples),
            "task_types": sorted({example["task_type"] for example in examples}),
        },
        "license": {
            "local_status": None,
            "review_required_before_training_oriented_use": True,
        },
        "training_authorization": {
            "model_use_tier": "blocked",
            "training_weight": 0.0,
        },
        "leakage_controls": {
            "raw_dialogue_text_included": False,
            "raw_issue_text_included": False,
            "raw_patch_text_included": False,
            "oracle_lists_included": False,
            "final_outcomes_in_input": False,
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
    "FORBIDDEN_INPUT_KEYS",
    "LICENSE_BLOCKED_USE",
    "SYNTHETIC_FIXTURE_REF",
    "build_conversion_report",
    "convert_record",
    "convert_records",
    "load_synthetic_records",
    "validate_training_examples",
]

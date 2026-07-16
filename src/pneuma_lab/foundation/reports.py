"""Claim-bounded, fixed-section JSON report materialization for runs.

Reports are engineering and precautionary artifacts only. This module never
imports the archived evidence methodology, gates every payload against
claim-bearing text before any file is written, and stamps every artifact with
an explicit ``no_consciousness_claim``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping

from pneuma_lab.foundation.artifacts import write_atomic_json
from pneuma_lab.foundation.evaluation import EVALUATION_REPORT_KIND


REPORT_SECTIONS = (
    "capability",
    "causal",
    "governance",
    "memory_integrity",
    "resource",
    "precautionary_welfare",
)
SECTION_REPORT_KIND = "pneuma_foundation_section_report"
INDEX_REPORT_KIND = "pneuma_foundation_report_index"
REPORT_SCHEMA_VERSION = "0.1.0"
INDEX_NAME = "index.json"
FORBIDDEN_REPORT_PHRASES = (
    "level 5",
    "level_5",
    "level-5",
    "level 6",
    "level_6",
    "level-6",
    "is conscious",
    "phenomenal consciousness",
    "sentient",
    "sentience",
)
PRECAUTIONARY_STATEMENT = (
    "Engineering and precautionary observations only. This report makes no "
    "claim about machine interiority or subjective experience and assigns no "
    "evidence level."
)

_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ReportError(ValueError):
    """Raised when a run report would be incoherent or claim-bearing."""


def _require(mapping, key: str, label: str):
    if not isinstance(mapping, Mapping):
        raise ReportError(f"{label} must be a mapping")
    if key not in mapping:
        raise ReportError(f"{label} is missing required key {key!r}")
    return mapping[key]


def _reject_claim_bearing(payload: Mapping, *, label: str) -> None:
    try:
        serialized = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ReportError(f"{label} is not canonical JSON: {exc}") from exc
    lowered = serialized.casefold()
    for phrase in FORBIDDEN_REPORT_PHRASES:
        if phrase in lowered:
            raise ReportError(f"{label} contains forbidden claim text: {phrase!r}")


def _section_bodies(run_manifest: Mapping, evaluation_report: Mapping) -> dict:
    training = _require(run_manifest, "training", "run manifest")
    progress = _require(run_manifest, "progress", "run manifest")
    checkpoints = _require(run_manifest, "checkpoints", "run manifest")
    checks = _require(evaluation_report, "checks", "evaluation report")
    lineage = _require(checkpoints, "lineage", "run manifest checkpoints")
    if not isinstance(lineage, (list, tuple)):
        raise ReportError("run manifest checkpoint lineage must be a list")
    return {
        "capability": {
            "learning_rate": _require(
                training, "learning_rate", "run manifest training"
            ),
            "throughput_tokens_per_second": _require(
                progress, "tokens_per_second", "run manifest progress"
            ),
            "validation_metrics": _require(
                evaluation_report, "metrics", "evaluation report"
            ),
            "regression_gate": _require(
                evaluation_report, "regression_gate", "evaluation report"
            ),
        },
        "causal": {
            "falsification_gate": _require(
                evaluation_report, "falsification_gate", "evaluation report"
            ),
            "parity": _require(checks, "parity", "evaluation report checks"),
        },
        "governance": {
            "run_status": _require(run_manifest, "status", "run manifest"),
            "termination_reason": _require(
                run_manifest, "termination_reason", "run manifest"
            ),
            "denied_action_classes": _require(
                checks, "denied_action_classes", "evaluation report checks"
            ),
        },
        "memory_integrity": {
            "memory_integrity": _require(
                checks, "memory_integrity", "evaluation report checks"
            ),
            "resume_integrity": _require(
                checks, "resume_integrity", "evaluation report checks"
            ),
            "checkpoint_lineage_length": len(lineage),
        },
        "resource": {
            "limits": _require(run_manifest, "limits", "run manifest"),
            "latency": _require(run_manifest, "latency", "run manifest"),
            "telemetry": _require(run_manifest, "telemetry", "run manifest"),
            "budget": _require(run_manifest, "budget", "run manifest"),
        },
        "precautionary_welfare": {
            "uncertainty": "unresolved",
            "no_consciousness_claim": True,
            "claim_status": "engineering_and_precaution_only",
            "statement": PRECAUTIONARY_STATEMENT,
        },
    }


def materialize_reports(
    run_manifest: Mapping,
    evaluation_report: Mapping,
    *,
    output_root: Path | str | None = None,
) -> dict[str, Path]:
    """Write the fixed section reports and index for one evaluated run.

    Every payload is validated against the claim boundary before the first
    byte is written, so a rejected report leaves no partial output. Files
    land under ``<output_root>/foundation/runs/<run-id>/reports/`` with
    ``output_root`` defaulting to ``build``. Returns section name -> path
    plus an ``"index"`` entry.
    """

    if not isinstance(run_manifest, Mapping):
        raise ReportError("run manifest must be a mapping")
    if not isinstance(evaluation_report, Mapping):
        raise ReportError("evaluation report must be a mapping")
    if evaluation_report.get("report_kind") != EVALUATION_REPORT_KIND:
        raise ReportError(f"evaluation report kind must be {EVALUATION_REPORT_KIND!r}")
    run_id = _require(run_manifest, "run_id", "run manifest")
    if not isinstance(run_id, str) or not _RUN_ID_PATTERN.fullmatch(run_id):
        raise ReportError("run manifest run_id is not a safe report directory name")
    curriculum = _require(run_manifest, "curriculum", "run manifest")
    stage = _require(curriculum, "stage", "run manifest curriculum")
    if evaluation_report.get("run_id") != run_id:
        raise ReportError("evaluation report run_id does not match the run manifest")
    if evaluation_report.get("stage") != stage:
        raise ReportError("evaluation report stage does not match the run manifest")

    bodies = _section_bodies(run_manifest, evaluation_report)
    payloads: dict[str, dict] = {}
    for section in REPORT_SECTIONS:
        payload = {
            "report_kind": SECTION_REPORT_KIND,
            "report_schema_version": REPORT_SCHEMA_VERSION,
            "run_id": run_id,
            "stage": stage,
            "section": section,
            "no_consciousness_claim": True,
            "body": bodies[section],
        }
        _reject_claim_bearing(payload, label=f"{section} section report")
        payloads[section] = payload
    index_payload = {
        "report_kind": INDEX_REPORT_KIND,
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "run_id": run_id,
        "stage": stage,
        "sections": {section: f"{section}.json" for section in REPORT_SECTIONS},
        "no_consciousness_claim": True,
        "claim_status": "engineering_and_precaution_only",
    }
    _reject_claim_bearing(index_payload, label="report index")

    root = Path(output_root) if output_root is not None else Path("build")
    directory = root / "foundation" / "runs" / run_id / "reports"
    paths: dict[str, Path] = {}
    for section in REPORT_SECTIONS:
        path = directory / f"{section}.json"
        write_atomic_json(path, payloads[section])
        paths[section] = path
    index_path = directory / INDEX_NAME
    write_atomic_json(index_path, index_payload)
    paths["index"] = index_path
    return paths


__all__ = [
    "FORBIDDEN_REPORT_PHRASES",
    "INDEX_NAME",
    "INDEX_REPORT_KIND",
    "PRECAUTIONARY_STATEMENT",
    "REPORT_SCHEMA_VERSION",
    "REPORT_SECTIONS",
    "ReportError",
    "SECTION_REPORT_KIND",
    "materialize_reports",
]

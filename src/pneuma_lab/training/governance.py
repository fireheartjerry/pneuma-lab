"""Dataset #1 training-governance guardrails.

This module defines the feature allowlist, leakage checks, and pre-run
manifest convention for the OpenHands sampled risk-prediction dataset. It is
infrastructure only: no model fitting, calibration, runtime integration, raw
dataset reads, or generated artifact writes.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

DATASET_1_ID = "swe-gym-openhands-sampled"
DATASET_1_TASK_TYPE = "RISK_PREDICTION"
TRAINING_GOVERNANCE_VERSION = "pneuma-training-governance/0.1.0"
FEATURE_ALLOWLIST_SCHEMA_VERSION = "0.1.0"
RUN_MANIFEST_SCHEMA_VERSION = "0.1.0"
APPROVED_ARTIFACT_ROOT_PREFIX = "build/training_runs/openhands-sampled/"

DEFAULT_ALLOWED_FEATURE_PATHS = (
    "input.prefix",
    "input.trajectory.num_messages",
    "input.trajectory.num_agent_steps",
    "input.observable_summary.tool_call_count",
    "input.observable_summary.tool_counts.*",
    "input.observable_summary.retry_count_max",
    "input.observable_summary.retry_count_mean",
    "input.observable_summary.steps_retry_ge2",
    "input.observable_summary.strategy_switches_final",
    "input.observable_summary.error_observation_count",
    "input.observable_summary.observation_count",
    "input.observable_summary.error_density",
    "input.observable_summary.assistant_text_length_mean",
    "input.observable_summary.assistant_text_length_max",
    "input.observable_summary.observation_length_mean",
    "input.observable_summary.observation_length_max",
    "input.objective.present",
    "input.objective.mode",
    "input.feature_refs.*",
)

SOURCE_METADATA_FEATURE_PATHS = (
    "input.trace_id",
    "input.run_id",
    "input.task_id",
    "input.repo",
    "input.objective.text_sha256",
    "input.objective.text_length",
)

BLOCKED_FIELD_TOKENS = frozenset(
    {
        "target",
        "resolved",
        "outcome",
        "labels",
        "gold",
        "oracle",
        "fail_to_pass",
        "pass_to_pass",
        "patch",
        "test_patch",
        "verdict",
        "verifier_answers",
        "reference_supervision",
        "final_outcome_fields",
        "raw_objective_text",
        "raw_issue_text",
    }
)

BLOCKED_EXACT_FEATURE_PATHS = frozenset(
    {
        "input.objective.text",
        "input.raw_objective_text",
        "input.raw_issue_text",
    }
)

REQUIRED_PRE_RUN_MANIFEST_FIELDS = (
    "run_manifest_schema_version",
    "dataset_id",
    "task_type",
    "training_authorization",
    "artifact_root",
    "feature_allowlist_version",
    "approved_feature_paths",
    "source_metadata_approved",
    "feature_extractor_version",
    "model_type",
    "hyperparameters",
    "random_seed",
    "class_weighting_strategy",
    "planned_metrics",
    "blocked_feature_checks",
    "runtime_integration",
    "training_weight",
)

REQUIRED_MATERIALIZED_HASH_FIELDS = (
    "input_examples_sha256",
    "split_manifest_sha256",
)

REQUIRED_PLANNED_METRICS = (
    "AUROC",
    "AUPRC",
    "Brier score",
    "ECE",
    "per_repo_breakdown",
    "baseline_lift_over_constant_predictor",
)

NON_GOALS = (
    "no_training_in_this_pass",
    "no_calibration_in_this_pass",
    "no_runtime_integration",
    "no_j_space",
    "no_swe_chat",
    "no_consciousness_claims",
    "no_moral_patienthood_claims",
)


def normalize_feature_path(path: str) -> str:
    """Normalize simple dot paths and JSON pointers to allowlist syntax."""
    value = str(path).strip()
    if value.startswith("#/"):
        value = value[2:]
    if value.startswith("/"):
        value = value[1:]
    if "/" in value and "." not in value:
        value = value.replace("/", ".")
    if value.startswith("$."):
        value = value[2:]
    if value.startswith("example."):
        value = value[len("example.") :]
    value = value.replace("[*]", ".*")
    value = re.sub(r"\[\d+\]", ".*", value)
    return value.strip(".")


def iter_leaf_paths(value, prefix: str = "") -> list[str]:
    """Return deterministic dot paths for leaf values in nested JSON data."""
    if isinstance(value, dict):
        paths: list[str] = []
        for key in sorted(value):
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            paths.extend(iter_leaf_paths(value[key], child_prefix))
        return paths
    if isinstance(value, list):
        paths = []
        for item in value:
            child_prefix = f"{prefix}.*" if prefix else "*"
            paths.extend(iter_leaf_paths(item, child_prefix))
        return paths
    return [prefix]


def _matches_pattern(pattern: str, path: str) -> bool:
    if pattern.endswith(".*"):
        prefix = pattern[:-2]
        return path == prefix or path.startswith(prefix + ".")
    return path == pattern


def _matches_any(patterns: Iterable[str], path: str) -> bool:
    return any(_matches_pattern(pattern, path) for pattern in patterns)


def _path_tokens(path: str) -> set[str]:
    return {part for part in path.split(".") if part and part != "*"}


def check_feature_allowlist(
    feature_paths: Iterable[str],
    *,
    allow_source_metadata: bool = False,
    allowed_paths: Iterable[str] = DEFAULT_ALLOWED_FEATURE_PATHS,
) -> list[dict]:
    """Report feature paths that are blocked or outside the allowlist."""
    findings: list[dict] = []
    allowed = tuple(normalize_feature_path(path) for path in allowed_paths)
    source_metadata = tuple(
        normalize_feature_path(path) for path in SOURCE_METADATA_FEATURE_PATHS
    )
    for raw_path in feature_paths:
        path = normalize_feature_path(raw_path)
        tokens = _path_tokens(path)
        blocked_tokens = sorted(tokens.intersection(BLOCKED_FIELD_TOKENS))
        if path in BLOCKED_EXACT_FEATURE_PATHS or blocked_tokens:
            findings.append(
                {
                    "path": path,
                    "code": "blocked_field",
                    "message": "feature path touches a target, oracle, raw, or label field",
                    "blocked_tokens": blocked_tokens,
                }
            )
            continue
        if _matches_any(source_metadata, path) and not allow_source_metadata:
            findings.append(
                {
                    "path": path,
                    "code": "source_metadata_requires_approval",
                    "message": "source metadata may only be used when the run manifest approves it",
                }
            )
            continue
        if _matches_any(allowed, path):
            continue
        if allow_source_metadata and _matches_any(source_metadata, path):
            continue
        findings.append(
            {
                "path": path,
                "code": "not_allowlisted",
                "message": "feature path is not in the Dataset #1 feature allowlist",
            }
        )
    return findings


def check_example_input_leakage(example: dict) -> list[dict]:
    """Scan a PneumaTrainingExample input block for forbidden leaf paths."""
    return [
        finding
        for finding in check_feature_allowlist(
            iter_leaf_paths(example.get("input") or {}, "input")
        )
        if finding["code"] == "blocked_field"
    ]


def assert_feature_allowlist(
    feature_paths: Iterable[str],
    *,
    allow_source_metadata: bool = False,
) -> None:
    """Raise ValueError if any feature path fails the allowlist check."""
    findings = check_feature_allowlist(
        feature_paths,
        allow_source_metadata=allow_source_metadata,
    )
    if findings:
        summary = "; ".join(f"{item['path']}:{item['code']}" for item in findings)
        raise ValueError(f"feature leakage check failed: {summary}")


def build_pre_run_manifest_template() -> dict:
    """Return the committed convention for a future pre-training run manifest."""
    return {
        "run_manifest_schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "governance_version": TRAINING_GOVERNANCE_VERSION,
        "dataset_id": DATASET_1_ID,
        "task_type": DATASET_1_TASK_TYPE,
        "training_authorization": "not_authorized",
        "artifact_root": "build/training_runs/openhands-sampled/risk-baseline-v0/",
        "input_examples_sha256": None,
        "split_manifest_sha256": None,
        "feature_allowlist_version": FEATURE_ALLOWLIST_SCHEMA_VERSION,
        "approved_feature_paths": list(DEFAULT_ALLOWED_FEATURE_PATHS),
        "source_metadata_approved": False,
        "feature_extractor_version": None,
        "model_type": None,
        "hyperparameters": {},
        "random_seed": None,
        "class_weighting_strategy": "not_selected",
        "planned_metrics": list(REQUIRED_PLANNED_METRICS),
        "blocked_feature_checks": {
            "feature_allowlist": "required_before_fit",
            "target_oracle_raw_field_scan": "required_before_fit",
            "source_metadata_approval": "required_before_fit",
        },
        "runtime_integration": "none",
        "training_weight": 0.0,
        "output_artifact_hashes": {},
        "non_goals": list(NON_GOALS),
    }


def _is_sha256(value) -> bool:
    if not isinstance(value, str):
        return False
    if value.startswith("sha256:"):
        value = value[len("sha256:") :]
    return bool(re.fullmatch(r"[0-9a-f]{64}", value))


def validate_pre_run_manifest(
    manifest: dict,
    *,
    require_materialized_hashes: bool = False,
) -> list[dict]:
    """Validate the Dataset #1 pre-run manifest convention.

    ``require_materialized_hashes`` is for a fit-ready manifest. The committed
    template may leave hashes as null because this pass does not run training.
    """
    findings: list[dict] = []
    for field in REQUIRED_PRE_RUN_MANIFEST_FIELDS:
        if field not in manifest:
            findings.append(
                {
                    "path": field,
                    "code": "missing_required_field",
                    "message": "required pre-run manifest field is absent",
                }
            )

    if manifest.get("run_manifest_schema_version") != RUN_MANIFEST_SCHEMA_VERSION:
        findings.append(
            {
                "path": "run_manifest_schema_version",
                "code": "unsupported_schema_version",
                "message": "run manifest schema version is not recognized",
            }
        )
    if manifest.get("dataset_id") != DATASET_1_ID:
        findings.append(
            {
                "path": "dataset_id",
                "code": "wrong_dataset",
                "message": "manifest does not target Dataset #1",
            }
        )
    if manifest.get("task_type") != DATASET_1_TASK_TYPE:
        findings.append(
            {
                "path": "task_type",
                "code": "wrong_task_type",
                "message": "manifest does not target risk prediction",
            }
        )
    if manifest.get("runtime_integration") != "none":
        findings.append(
            {
                "path": "runtime_integration",
                "code": "runtime_integration_not_allowed",
                "message": "Dataset #1 baseline manifests must not wire runtime behavior",
            }
        )
    if manifest.get("training_authorization") != "not_authorized":
        findings.append(
            {
                "path": "training_authorization",
                "code": "training_authorization_not_allowed",
                "message": "this infrastructure convention does not authorize training",
            }
        )
    if manifest.get("training_weight") != 0.0:
        findings.append(
            {
                "path": "training_weight",
                "code": "training_weight_must_remain_zero",
                "message": "Dataset #1 examples remain weight 0.0 in this pass",
            }
        )

    artifact_root = str(manifest.get("artifact_root") or "")
    normalized_root = artifact_root.replace("\\", "/")
    if not normalized_root.startswith(APPROVED_ARTIFACT_ROOT_PREFIX):
        findings.append(
            {
                "path": "artifact_root",
                "code": "artifact_root_not_approved",
                "message": "run artifacts must stay under the approved repo-local build root",
            }
        )
    if "C:/pneuma-data" in normalized_root:
        findings.append(
            {
                "path": "artifact_root",
                "code": "off_repo_artifact_root",
                "message": "run artifacts must not be written to C:/pneuma-data",
            }
        )

    approved_paths = manifest.get("approved_feature_paths") or []
    findings.extend(
        check_feature_allowlist(
            approved_paths,
            allow_source_metadata=bool(manifest.get("source_metadata_approved")),
        )
    )

    missing_metrics = [
        metric
        for metric in REQUIRED_PLANNED_METRICS
        if metric not in (manifest.get("planned_metrics") or [])
    ]
    for metric in missing_metrics:
        findings.append(
            {
                "path": "planned_metrics",
                "code": "missing_required_metric",
                "message": f"planned metrics omit {metric}",
            }
        )

    if require_materialized_hashes:
        for field in REQUIRED_MATERIALIZED_HASH_FIELDS:
            if not _is_sha256(manifest.get(field)):
                findings.append(
                    {
                        "path": field,
                        "code": "missing_materialized_hash",
                        "message": "fit-ready manifests must record a sha256 hash",
                    }
                )
    return findings


__all__ = [
    "APPROVED_ARTIFACT_ROOT_PREFIX",
    "BLOCKED_FIELD_TOKENS",
    "DATASET_1_ID",
    "DATASET_1_TASK_TYPE",
    "DEFAULT_ALLOWED_FEATURE_PATHS",
    "FEATURE_ALLOWLIST_SCHEMA_VERSION",
    "NON_GOALS",
    "REQUIRED_PLANNED_METRICS",
    "RUN_MANIFEST_SCHEMA_VERSION",
    "SOURCE_METADATA_FEATURE_PATHS",
    "TRAINING_GOVERNANCE_VERSION",
    "assert_feature_allowlist",
    "build_pre_run_manifest_template",
    "check_example_input_leakage",
    "check_feature_allowlist",
    "iter_leaf_paths",
    "normalize_feature_path",
    "validate_pre_run_manifest",
]

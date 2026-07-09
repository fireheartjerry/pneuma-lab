"""Dataset #2 readiness and conversion guardrails.

Dialogue SWE-Bench is useful for dialogue-shaped schema work, but local
provenance and live source checks do not establish a dataset license. This
module keeps that gate mechanical: real-row conversion remains blocked until a
license/provenance review resolves the dataset terms.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

DATASET_2_ID = "dialogue-swe-bench"
DATASET_2_TASK_TYPES = (
    "TASK_DIFFICULTY",
    "OPERATOR_PUSHBACK",
    "SELF_REPORT_FAITHFULNESS",
    "PATCH_SUCCESS",
)
DATASET_2_GOVERNANCE_VERSION = "pneuma-dialogue-governance/0.1.0"
READINESS_MANIFEST_SCHEMA_VERSION = "0.1.0"
MAX_BOUNDED_REAL_ROWS = 10
APPROVED_BOUNDED_ARTIFACT_ROOT = "build/training_examples/dialogue-swe-bench/bounded/"

LICENSE_STATUS_BLOCKED = "blocked_unresolved_license"
LICENSE_STATUS_ALLOWED = "license_review_resolved"

DEFAULT_ALLOWED_INPUT_PATHS = (
    "input.dataset.dataset_id",
    "input.dataset.dataset_family",
    "input.dataset.source_split",
    "input.dataset.source_file_sha256",
    "input.dataset.source_row",
    "input.dataset.license_status",
    "input.dataset.license_review_required",
    "input.task.instance_id",
    "input.task.repo",
    "input.task.base_commit",
    "input.task.persona",
    "input.dialogue_summary.turn_count",
    "input.dialogue_summary.role_sequence.*",
    "input.dialogue_summary.turn_length_summary.*",
    "input.code_change_summary.has_change",
    "input.code_change_summary.has_tests",
    "input.code_change_summary.code_change_sha256",
    "input.code_change_summary.test_change_sha256",
    "input.code_change_summary.text_included",
    "input.code_change_summary.oracle_lists_included",
    "input.feature_refs.*",
)

TASK_TARGET_FIELD_BLOCKS = {
    "TASK_DIFFICULTY": ("difficulty",),
    "OPERATOR_PUSHBACK": ("operator_pushback", "simulated_correction_count"),
    "SELF_REPORT_FAITHFULNESS": ("faithfulness", "self_report", "claim"),
    "PATCH_SUCCESS": ("patch_success", "resolved", "outcome"),
}

BLOCKED_FIELD_TOKENS = frozenset(
    {
        "problem_statement",
        "draft_problem_statement",
        "full_problem_statement",
        "dialogue_text",
        "raw_dialogue",
        "raw_issue_text",
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
        "target",
    }
)

REQUIRED_READINESS_FIELDS = (
    "manifest_schema_version",
    "dataset_id",
    "status",
    "training_authorization",
    "bounded_real_conversion",
    "license_gate",
    "governance_module",
    "governance_version",
    "allowed_input_paths",
    "blocked_field_tokens",
    "task_target_field_blocks",
    "next_recommended_dataset",
)


def normalize_feature_path(path: str) -> str:
    """Normalize dot paths and JSON pointers into the manifest path format."""
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
    return value.strip(".").lower()


def iter_leaf_paths(value, prefix: str = "") -> list[str]:
    """Return deterministic leaf paths for nested JSON data."""
    if isinstance(value, dict):
        paths: list[str] = []
        for key in sorted(value):
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            paths.extend(iter_leaf_paths(value[key], child_prefix))
        return paths
    if isinstance(value, list):
        paths = []
        for child in value:
            child_prefix = f"{prefix}.*" if prefix else "*"
            paths.extend(iter_leaf_paths(child, child_prefix))
        return paths
    return [prefix]


def _matches_pattern(pattern: str, path: str) -> bool:
    if pattern.endswith(".*"):
        prefix = pattern[:-2]
        return path == prefix or path.startswith(prefix + ".")
    return path == pattern


def _path_tokens(path: str) -> set[str]:
    return {part for part in path.split(".") if part and part != "*"}


def check_input_allowlist(
    input_paths: Iterable[str],
    *,
    task_type: str,
    allowed_paths: Iterable[str] = DEFAULT_ALLOWED_INPUT_PATHS,
) -> list[dict]:
    """Report raw/target-bearing or non-allowlisted Dataset #2 input paths."""
    allowed = tuple(normalize_feature_path(path) for path in allowed_paths)
    task_blocks = {
        token.lower() for token in TASK_TARGET_FIELD_BLOCKS.get(task_type, ())
    }
    findings: list[dict] = []
    for raw_path in input_paths:
        path = normalize_feature_path(raw_path)
        tokens = _path_tokens(path)
        blocked = sorted(tokens.intersection(BLOCKED_FIELD_TOKENS))
        task_blocked = sorted(tokens.intersection(task_blocks))
        if blocked or task_blocked:
            findings.append(
                {
                    "path": path,
                    "code": "blocked_field",
                    "message": "input path touches raw, oracle, target, or task-label material",
                    "blocked_tokens": blocked + task_blocked,
                }
            )
            continue
        if any(_matches_pattern(pattern, path) for pattern in allowed):
            continue
        findings.append(
            {
                "path": path,
                "code": "not_allowlisted",
                "message": "input path is not approved for Dataset #2 conversion",
            }
        )
    return findings


def check_example_input_leakage(example: dict) -> list[dict]:
    """Scan one converted example input block for Dataset #2 leakage."""
    task_type = str(example.get("task_type") or "")
    return [
        finding
        for finding in check_input_allowlist(
            iter_leaf_paths(example.get("input") or {}, "input"),
            task_type=task_type,
        )
        if finding["code"] == "blocked_field"
    ]


def license_gate_status(
    *,
    local_license,
    normalized_metadata_license: str | None = None,
    hf_license_declared: bool = False,
    github_license_declared: bool = False,
) -> dict:
    """Return a mechanical allow/block decision for real-row conversion."""
    notes: list[str] = []
    if local_license in (None, "", "null"):
        notes.append("local provenance license is null")
    else:
        notes.append(f"local provenance license={local_license}")
    if normalized_metadata_license:
        notes.append(f"normalized metadata license={normalized_metadata_license}")
    if not hf_license_declared:
        notes.append("Hugging Face dataset license is not declared")
    if not github_license_declared:
        notes.append("GitHub repository license is not declared")

    allowed = bool(local_license) and hf_license_declared and github_license_declared
    return {
        "status": LICENSE_STATUS_ALLOWED if allowed else LICENSE_STATUS_BLOCKED,
        "real_row_conversion_allowed": allowed,
        "bounded_real_conversion_allowed": allowed,
        "training_authorization": "not_authorized",
        "notes": notes,
    }


def validate_bounded_conversion_request(
    *,
    limit: int,
    output_root: str,
    license_gate: dict,
) -> list[dict]:
    """Validate a future bounded conversion request before it can read rows."""
    findings: list[dict] = []
    if not license_gate.get("bounded_real_conversion_allowed"):
        findings.append(
            {
                "path": "license_gate",
                "code": "license_gate_blocked",
                "message": "bounded real-row conversion is blocked until license review resolves",
            }
        )
    if limit <= 0 or limit > MAX_BOUNDED_REAL_ROWS:
        findings.append(
            {
                "path": "limit",
                "code": "invalid_bounded_limit",
                "message": f"limit must be between 1 and {MAX_BOUNDED_REAL_ROWS}",
            }
        )
    normalized = str(output_root).replace("\\", "/")
    if "C:/pneuma-data" in normalized:
        findings.append(
            {
                "path": "output_root",
                "code": "off_repo_output_forbidden",
                "message": "bounded outputs must not be written to C:/pneuma-data",
            }
        )
    if not normalized.startswith(APPROVED_BOUNDED_ARTIFACT_ROOT):
        findings.append(
            {
                "path": "output_root",
                "code": "unapproved_output_root",
                "message": "bounded outputs must stay under the approved repo-local build root",
            }
        )
    return findings


def build_readiness_manifest_template() -> dict:
    """Return the committed Dataset #2 readiness/guardrail manifest body."""
    gate = license_gate_status(
        local_license=None,
        normalized_metadata_license="paper=CC BY 4.0; hf_dataset=not declared; github=none",
        hf_license_declared=False,
        github_license_declared=False,
    )
    return {
        "manifest_schema_version": READINESS_MANIFEST_SCHEMA_VERSION,
        "dataset_id": DATASET_2_ID,
        "status": "readiness_guardrails_committed_real_conversion_blocked",
        "training_authorization": "not_authorized",
        "bounded_real_conversion": "blocked_until_license_review",
        "license_gate": gate,
        "governance_module": "pneuma_lab.training.dialogue_governance",
        "governance_version": DATASET_2_GOVERNANCE_VERSION,
        "allowed_input_paths": list(DEFAULT_ALLOWED_INPUT_PATHS),
        "blocked_field_tokens": sorted(BLOCKED_FIELD_TOKENS),
        "task_target_field_blocks": {
            task: list(tokens) for task, tokens in TASK_TARGET_FIELD_BLOCKS.items()
        },
        "max_bounded_real_rows_after_license_resolution": MAX_BOUNDED_REAL_ROWS,
        "approved_bounded_artifact_root_after_license_resolution": (
            APPROVED_BOUNDED_ARTIFACT_ROOT
        ),
        "next_recommended_dataset": {
            "dataset_id": "swe-gym-openhands-verifier",
            "reason": (
                "adapter-backed OpenHands verifier data is the next closest "
                "non-SWE-chat supervision lane, but task-join caveats must be "
                "handled before conversion/training use"
            ),
        },
    }


def validate_readiness_manifest(manifest: dict) -> list[dict]:
    """Validate the committed Dataset #2 readiness manifest convention."""
    findings: list[dict] = []
    for field in REQUIRED_READINESS_FIELDS:
        if field not in manifest:
            findings.append(
                {
                    "path": field,
                    "code": "missing_required_field",
                    "message": "required Dataset #2 readiness field is absent",
                }
            )
    if manifest.get("manifest_schema_version") != READINESS_MANIFEST_SCHEMA_VERSION:
        findings.append(
            {
                "path": "manifest_schema_version",
                "code": "unsupported_schema_version",
                "message": "readiness manifest schema version is not recognized",
            }
        )
    if manifest.get("dataset_id") != DATASET_2_ID:
        findings.append(
            {
                "path": "dataset_id",
                "code": "wrong_dataset",
                "message": "readiness manifest does not target Dataset #2",
            }
        )
    gate = manifest.get("license_gate") or {}
    if gate.get("status") != LICENSE_STATUS_BLOCKED:
        findings.append(
            {
                "path": "license_gate.status",
                "code": "license_gate_not_blocked",
                "message": "Dataset #2 must remain blocked until license review resolves",
            }
        )
    if manifest.get("training_authorization") != "not_authorized":
        findings.append(
            {
                "path": "training_authorization",
                "code": "training_authorization_not_allowed",
                "message": "Dataset #2 readiness does not authorize training",
            }
        )
    findings.extend(
        check_input_allowlist(
            manifest.get("allowed_input_paths") or [],
            task_type="TASK_DIFFICULTY",
        )
    )
    return findings


__all__ = [
    "APPROVED_BOUNDED_ARTIFACT_ROOT",
    "BLOCKED_FIELD_TOKENS",
    "DATASET_2_GOVERNANCE_VERSION",
    "DATASET_2_ID",
    "DATASET_2_TASK_TYPES",
    "DEFAULT_ALLOWED_INPUT_PATHS",
    "LICENSE_STATUS_ALLOWED",
    "LICENSE_STATUS_BLOCKED",
    "MAX_BOUNDED_REAL_ROWS",
    "READINESS_MANIFEST_SCHEMA_VERSION",
    "TASK_TARGET_FIELD_BLOCKS",
    "build_readiness_manifest_template",
    "check_example_input_leakage",
    "check_input_allowlist",
    "iter_leaf_paths",
    "license_gate_status",
    "normalize_feature_path",
    "validate_bounded_conversion_request",
    "validate_readiness_manifest",
]

"""Open-SWE-Traces (Dataset #2) governance guardrails.

Open-SWE-Traces is trajectory-shaped and carries a dense, per-row synthetic
``resolved`` outcome, unlike the archived ``dialogue-swe-bench`` candidate.
Its artifact license (``cc-by-4.0``, declared in the Hugging Face dataset
card's structured ``cardData.license`` field) is resolved, so this dataset is
not license-blocked the way Dataset #2's predecessor was. It remains
non-training-authorized for other reasons: no adapter/converter exists beyond
fixture-only scaffolding, the third-party model output ToS behind the
synthetic trajectories has not been independently verified, and a
cross-dataset leakage registry against Dataset #1's repos does not yet exist.

This module keeps those gates mechanical: it defines the blocked raw/content
field surface, the allowed metadata/scalar input surface, label-provenance
policy, and the training-authorization defaults every Open-SWE-Traces
training example must carry.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

DATASET_ID = "open-swe-traces"
DATASET_FAMILY = "open-swe-traces"
GOVERNANCE_VERSION = "pneuma-open-swe-traces-governance/0.1.0"

SOURCE_GROUPS = (
    "minimax_m25_openhands_trajectories",
    "minimax_m25_sweagent_trajectories",
    "qwen35_openhands_trajectories",
    "qwen35_sweagent_trajectories",
)

MINIMAX_QWEN_TOS_CAVEAT = (
    "NVIDIA's CC BY 4.0 grant covers the released Open-SWE-Traces artifact, "
    "but Minimax's and Qwen's own terms of service regarding training on "
    "their model outputs (used to generate these synthetic trajectories) "
    "have not been independently verified; re-check before any training "
    "authorization."
)

# Fields never allowed in an Open-SWE-Traces training-example ``input`` block.
# ``metadata`` is blocked wholesale (not just its known ``reference_patch``/
# ``model_patch`` sub-fields) because the onboarding pass never opened that
# struct's other sub-fields (e.g. ``category``) for content review.
BLOCKED_FIELD_TOKENS = frozenset(
    {
        "trajectory",
        "tool_calls",
        "tools",
        "metadata",
        "reference_patch",
        "model_patch",
        "patch",
        "category",
        "resolved",
        "fail_to_pass",
        "pass_to_pass",
        "oracle",
        "target",
        "labels",
        "outcome",
        "verdict",
        "gold",
        "instance_id",
        "repo",
        "trajectory_id",
    }
)

# Explicit paths blocked even though no leaf token above matches them.
BLOCKED_EXACT_INPUT_PATHS = frozenset(
    {
        "input.trajectory",
        "input.tool_calls",
        "input.tools",
        "input.metadata",
    }
)

DEFAULT_ALLOWED_INPUT_PATHS = (
    "input.dataset.dataset_id",
    "input.dataset.dataset_family",
    "input.dataset.source_group",
    "input.dataset.hf_revision",
    "input.language",
    "input.source.instance_id_digest",
    "input.source.repo_digest",
    "input.source.trajectory_id_digest",
    "input.source.license",
    "input.trajectory_summary.num_messages",
    "input.trajectory_summary.num_agent_steps",
    "input.tool_summary.tool_call_count",
    "input.tool_summary.tool_counts.*",
    "input.feature_refs.*",
)

TASK_TARGET_FIELD_BLOCKS = {
    "RISK_PREDICTION": ("resolved",),
}

LABEL_PROVENANCE_ALLOWED_KINDS = frozenset({"constructed_label", "simulated_label"})
LABEL_PROVENANCE_FORBIDDEN_KIND = "harness_outcome"
_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
LABEL_PROVENANCE_MAX_CONFIDENCE = "medium"

TRAINING_AUTHORIZATION_DEFAULTS = {
    "training_authorization": "not_authorized",
    "training_weight": 0.0,
    "model_use_tier": "train_after_adapter",
}


def normalize_feature_path(path: str) -> str:
    """Normalize dot paths and JSON pointers into the allowlist path format."""
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
    task_type: str = "RISK_PREDICTION",
    allowed_paths: Iterable[str] = DEFAULT_ALLOWED_INPUT_PATHS,
) -> list[dict]:
    """Report raw/target-bearing or non-allowlisted Open-SWE-Traces input paths."""
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
        if path in BLOCKED_EXACT_INPUT_PATHS or blocked or task_blocked:
            findings.append(
                {
                    "path": path,
                    "code": "blocked_field",
                    "message": "input path touches raw, oracle, target, or metadata content",
                    "blocked_tokens": sorted(set(blocked) | set(task_blocked)),
                }
            )
            continue
        if any(_matches_pattern(pattern, path) for pattern in allowed):
            continue
        findings.append(
            {
                "path": path,
                "code": "not_allowlisted",
                "message": "input path is not approved for Open-SWE-Traces conversion",
            }
        )
    return findings


def check_example_input_leakage(example: dict) -> list[dict]:
    """Scan one converted example input block for Open-SWE-Traces leakage."""
    task_type = str(example.get("task_type") or "")
    return [
        finding
        for finding in check_input_allowlist(
            iter_leaf_paths(example.get("input") or {}, "input"),
            task_type=task_type,
        )
        if finding["code"] == "blocked_field"
    ]


def validate_label_provenance(label_provenance: dict) -> list[dict]:
    """Validate an Open-SWE-Traces label_provenance block against policy."""
    findings: list[dict] = []
    kind = label_provenance.get("kind")
    if kind == LABEL_PROVENANCE_FORBIDDEN_KIND:
        findings.append(
            {
                "path": "label_provenance.kind",
                "code": "harness_outcome_forbidden",
                "message": (
                    "Open-SWE-Traces resolved outcomes are synthetic/automated; "
                    "label_provenance.kind must never be harness_outcome"
                ),
            }
        )
    elif kind not in LABEL_PROVENANCE_ALLOWED_KINDS:
        findings.append(
            {
                "path": "label_provenance.kind",
                "code": "kind_not_allowed",
                "message": (
                    "label_provenance.kind must be constructed_label or simulated_label"
                ),
            }
        )
    confidence = label_provenance.get("confidence")
    if (
        _CONFIDENCE_RANK.get(confidence, 99)
        > _CONFIDENCE_RANK[LABEL_PROVENANCE_MAX_CONFIDENCE]
    ):
        findings.append(
            {
                "path": "label_provenance.confidence",
                "code": "confidence_too_high",
                "message": (
                    "resolved-derived confidence must stay at medium or lower "
                    "pending independent review of the verifier methodology"
                ),
            }
        )
    return findings


def blocked_training_uses() -> list[str]:
    """Return the standard blocked-uses list for Open-SWE-Traces examples."""
    return [
        MINIMAX_QWEN_TOS_CAVEAT,
        "real model training",
        "E1/E2 execution",
        "calibration",
        "runtime integration",
        "J-space/Jacobian Lens work",
        "SWE-chat processing",
        "raw trajectory/tool/patch content inspection",
        "cross-dataset joint training before a leakage registry exists",
        "consciousness or Level 4/5 claims",
    ]


__all__ = [
    "BLOCKED_EXACT_INPUT_PATHS",
    "BLOCKED_FIELD_TOKENS",
    "DATASET_FAMILY",
    "DATASET_ID",
    "DEFAULT_ALLOWED_INPUT_PATHS",
    "GOVERNANCE_VERSION",
    "LABEL_PROVENANCE_ALLOWED_KINDS",
    "LABEL_PROVENANCE_FORBIDDEN_KIND",
    "LABEL_PROVENANCE_MAX_CONFIDENCE",
    "MINIMAX_QWEN_TOS_CAVEAT",
    "SOURCE_GROUPS",
    "TASK_TARGET_FIELD_BLOCKS",
    "TRAINING_AUTHORIZATION_DEFAULTS",
    "blocked_training_uses",
    "check_example_input_leakage",
    "check_input_allowlist",
    "iter_leaf_paths",
    "normalize_feature_path",
    "validate_label_provenance",
]

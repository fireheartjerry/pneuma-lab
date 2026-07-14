"""All-family foundation suite policy and payload-access guards."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pneuma_lab.foundation.data import (
    ACTIVE_DATASET_GROUPS,
    DataAuthorizationError,
    governed_dataset_groups,
)
from pneuma_lab.foundation.source_presence import probe_family_presence


class SuitePolicyError(ValueError):
    """Raised when suite policy cannot safely authorize the requested access."""


_EXPECTED_FAMILY_MATRIX = (
    ("multi-swe-bench", "train", "later", "metadata_only", None),
    ("open-swe-traces", "train", "later", "metadata_only", None),
    ("sec-bench-pro", "governance", "never", "metadata_only", None),
    (
        "swe-bench",
        "eval",
        "never",
        "identity_metadata_only",
        "processed/swe-bench/normalized_metadata.jsonl",
    ),
    ("swe-bench-pro", "eval", "never", "metadata_only", None),
    ("swe-chat", "governance", "never", "metadata_only", None),
    ("swe-evo", "train", "later", "metadata_only", None),
    (
        "swe-gym",
        "train",
        "first_stage",
        "approved_processed_lane_only",
        None,
    ),
    (
        "swe-mera",
        "eval",
        "never",
        "identity_metadata_only",
        "processed/swe-mera/normalized_metadata.jsonl",
    ),
    (
        "swe-polybench",
        "eval",
        "later",
        "identity_metadata_only",
        "processed/swe-polybench/normalized_metadata.jsonl",
    ),
)


def load_suite_policy(path: Path) -> dict[str, Any]:
    """Load a suite policy as a JSON object with domain-specific failures."""

    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SuitePolicyError(f"suite policy must be valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SuitePolicyError("suite policy must be a JSON object")
    return value


def _policy_entries(policy: Mapping) -> tuple[Mapping, ...]:
    if not isinstance(policy, Mapping):
        raise SuitePolicyError("suite policy must be a mapping")
    entries = policy.get("families")
    if not isinstance(entries, list):
        raise SuitePolicyError("suite policy families must be a list")
    if not all(isinstance(item, Mapping) for item in entries):
        raise SuitePolicyError("suite policy family entries must be objects")
    return tuple(entries)


def _validated_family_map(policy: Mapping) -> dict[str, Mapping]:
    entries = _policy_entries(policy)
    families: list[str] = []
    for item in entries:
        family = item.get("family")
        if not isinstance(family, str) or not family:
            raise SuitePolicyError("suite policy family names must be non-empty strings")
        families.append(family)
    if len(families) != 10 or set(families) != set(ACTIVE_DATASET_GROUPS):
        raise SuitePolicyError("suite policy must contain each active family exactly once")
    if tuple(families) != ACTIVE_DATASET_GROUPS:
        raise SuitePolicyError("suite policy families must use documented order")

    for item, expected in zip(entries, _EXPECTED_FAMILY_MATRIX, strict=True):
        family, role, gradient, access, identity_path = expected
        expected_item = {
            "family": family,
            "terminal_role": role,
            "gradient_eligibility": gradient,
            "payload_access_100k": access,
        }
        if identity_path is not None:
            expected_item["identity_metadata_relative_path"] = identity_path
        if dict(item) != expected_item or not all(
            isinstance(value, str) for value in item.values()
        ):
            raise SuitePolicyError(
                f"{family} must match the exact policy matrix"
            )

    first_stage = policy.get("first_stage")
    if not isinstance(first_stage, Mapping):
        raise SuitePolicyError("suite policy first stage must be an object")
    if set(first_stage) != {"stage", "authorized_lane_candidates"}:
        raise SuitePolicyError(
            "suite policy first-stage authorized lane candidates or stage are missing"
        )
    if not isinstance(first_stage.get("stage"), str) or (
        first_stage.get("stage") != "100k"
    ):
        raise SuitePolicyError("suite policy first stage must be 100k")
    candidates = first_stage.get("authorized_lane_candidates")
    if not isinstance(candidates, list) or not all(
        isinstance(candidate, str) for candidate in candidates
    ) or candidates != ["swe-gym-openhands-sampled"]:
        raise SuitePolicyError(
            "suite first-stage authorized lane candidates may nominate only "
            "the OpenHands Sampled lane"
        )
    return dict(zip(families, entries, strict=True))


def _lexical_data_relative_parts(path: object) -> tuple[str, ...] | None:
    try:
        raw_path = os.fspath(path)
    except TypeError:
        return None
    if not isinstance(raw_path, str) or not raw_path:
        return None
    raw_parts = tuple(
        part for part in re.split(r"[\\/]", raw_path) if part
    )
    if not raw_parts or any(part in {".", ".."} for part in raw_parts):
        return None
    if raw_parts.count("processed") != 1:
        return None
    processed_index = raw_parts.index("processed")
    try:
        is_absolute = Path(raw_path).is_absolute()
    except (OSError, TypeError, ValueError):
        return None
    if processed_index > 0 and not is_absolute:
        return None
    return raw_parts[processed_index:]


def validate_suite_policy(policy: Mapping, registry: Mapping) -> tuple[str, ...]:
    """Require exact all-family coverage coherent with the readiness registry."""

    family_map = _validated_family_map(policy)
    if not isinstance(registry, Mapping):
        raise SuitePolicyError("dataset registry must be a mapping")
    try:
        governed = governed_dataset_groups(registry)
    except (DataAuthorizationError, AttributeError, TypeError, ValueError) as exc:
        raise SuitePolicyError(f"invalid dataset registry: {exc}") from exc
    if set(governed) != set(family_map):
        raise SuitePolicyError("suite and registry families differ")
    return ACTIVE_DATASET_GROUPS


def assert_payload_read_allowed(
    policy: Mapping,
    *,
    stage: str,
    family: str,
    lane_id: str | None,
    path: Path,
) -> None:
    """Fail before opening unless the path is explicitly allowed for the stage."""

    family_map = _validated_family_map(policy)
    if not isinstance(stage, str) or not stage:
        raise SuitePolicyError("stage must be a non-empty string")
    if not isinstance(family, str) or not family:
        raise SuitePolicyError("family must be a non-empty string")
    item = family_map.get(family)
    if item is None:
        raise SuitePolicyError(f"unknown suite family: {family!r}")
    access_key = f"payload_access_{stage}"
    access = item.get(access_key)
    if not isinstance(access, str):
        raise SuitePolicyError(f"unknown or unsupported suite stage: {stage!r}")
    relative_parts = _lexical_data_relative_parts(path)

    approved_root = ("processed", "swe-gym", "openhands-sampled")
    approved_lane = (
        access == "approved_processed_lane_only"
        and family == "swe-gym"
        and lane_id == "swe-gym-openhands-sampled"
        and relative_parts is not None
        and relative_parts[:3] == approved_root
    )
    identity_path = item.get("identity_metadata_relative_path")
    identity_metadata = (
        access == "identity_metadata_only"
        and isinstance(identity_path, str)
        and relative_parts is not None
        and relative_parts == tuple(identity_path.split("/"))
    )
    if not (approved_lane or identity_metadata):
        raise SuitePolicyError(f"{family} is metadata-only for stage {stage}")


def build_suite_completeness_report(policy: Mapping, data_root: Path) -> dict:
    """Build a schema-ready report without reading any dataset payload."""

    family_map = _validated_family_map(policy)
    first_stage = policy["first_stage"]
    families = []
    for family in ACTIVE_DATASET_GROUPS:
        item = family_map[family]
        report_item = {
            "family": family,
            "terminal_role": item.get("terminal_role"),
            "gradient_eligibility": item.get("gradient_eligibility"),
            "payload_access_100k": item.get("payload_access_100k"),
            **asdict(probe_family_presence(data_root, family)),
        }
        identity_path = item.get("identity_metadata_relative_path")
        if identity_path is not None:
            report_item["identity_metadata_relative_path"] = identity_path
        families.append(report_item)
    return {
        "manifest_kind": "pneuma_foundation_suite_report",
        "manifest_schema_version": "0.1.0",
        "first_stage": {
            "stage": first_stage["stage"],
            "authorized_lane_candidates": list(
                first_stage["authorized_lane_candidates"]
            ),
        },
        "families": families,
    }


__all__ = [
    "SuitePolicyError",
    "assert_payload_read_allowed",
    "build_suite_completeness_report",
    "load_suite_policy",
    "validate_suite_policy",
]

"""All-family foundation suite policy and payload-access guards."""

from __future__ import annotations

import json
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
    if not isinstance(entries, (list, tuple)):
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

    first_stage = policy.get("first_stage")
    if not isinstance(first_stage, Mapping) or first_stage.get("stage") != "100k":
        raise SuitePolicyError("suite policy first stage must be 100k")
    candidates = first_stage.get("authorized_lane_candidates")
    if candidates != ["swe-gym-openhands-sampled"]:
        raise SuitePolicyError(
            "suite first-stage authorized lane candidates may nominate only "
            "the OpenHands Sampled lane"
        )
    return {str(item["family"]): item for item in entries}


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
    item = family_map.get(family)
    if item is None:
        raise SuitePolicyError(f"unknown suite family: {family!r}")
    access_key = f"payload_access_{stage}"
    access = item.get(access_key)
    if not isinstance(access, str):
        raise SuitePolicyError(f"unknown or unsupported suite stage: {stage!r}")
    try:
        normalized_path = Path(path).as_posix().casefold()
    except (TypeError, ValueError) as exc:
        raise SuitePolicyError("payload path must be path-like") from exc

    approved_root = "processed/swe-gym/openhands-sampled"
    approved_lane = (
        access == "approved_processed_lane_only"
        and family == "swe-gym"
        and lane_id == "swe-gym-openhands-sampled"
        and f"{approved_root}/" in normalized_path
    )
    identity_path = item.get("identity_metadata_relative_path")
    identity_metadata = (
        access == "identity_metadata_only"
        and isinstance(identity_path, str)
        and normalized_path.endswith(identity_path.casefold())
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

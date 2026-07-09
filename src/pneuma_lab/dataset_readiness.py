"""Canonical dataset-lane readiness registry and validation.

The registry is metadata-only.  Validation checks committed references and
governance claims; it never reads external dataset artifacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "docs" / "data" / "training-readiness" / "dataset-registry.json"
REGISTRY_SCHEMA_VERSION = "0.1.0"

READINESS_STAGES = {
    "planned",
    "fixture-only",
    "adapter-only",
    "preflight-only",
    "local-research-candidate",
    "eval-only",
    "provenance-blocked",
    "license-blocked-for-release",
    "join-blocked",
    "label-blocked",
    "leakage-blocked",
    "split-blocked",
    "authorization-blocked",
    "training-authorized",
}
TRAINING_READINESS = {
    "ready-for-controlled-training",
    "close-but-needs-human-authorization",
    "local-research-only",
    "eval-only",
    "preflight-only",
    "fixture-only",
    "blocked",
}
REQUIRED_LANE_FIELDS = {
    "lane_id",
    "name",
    "source_family",
    "current_stage",
    "training_readiness",
    "authorization",
    "references",
    "blockers",
    "advancement_criteria",
}
REFERENCE_KINDS = {"docs", "manifests", "fixtures", "adapters", "converters", "tests"}
AUTHORIZED_FIELDS = {
    "authorization_manifest",
    "source_hash",
    "split_hash",
    "code_commit",
    "output_root",
    "training_constants",
    "clean_code_state",
}


class DatasetReadinessError(ValueError):
    """Raised when the canonical registry is incomplete or contradictory."""


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_path(raw: str) -> Path:
    value = Path(raw)
    if value.is_absolute() or "C:/pneuma-data" in raw or "C:\\pneuma-data" in raw:
        raise DatasetReadinessError(f"external or absolute reference is forbidden: {raw}")
    resolved = (ROOT / value).resolve()
    if ROOT not in resolved.parents and resolved != ROOT:
        raise DatasetReadinessError(f"reference escapes repository: {raw}")
    return resolved


def validate_registry(registry: dict[str, Any], *, root: Path = ROOT) -> tuple[str, ...]:
    """Return deterministic validation findings; an empty tuple means valid."""
    findings: list[str] = []
    if registry.get("registry_schema_version") != REGISTRY_SCHEMA_VERSION:
        findings.append("registry_schema_version: unsupported or missing")
    lanes = registry.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        return ("lanes: must be a non-empty list",)

    seen: set[str] = set()
    for index, lane in enumerate(lanes):
        prefix = f"lanes[{index}]"
        if not isinstance(lane, dict):
            findings.append(f"{prefix}: must be an object")
            continue
        missing = sorted(REQUIRED_LANE_FIELDS - lane.keys())
        findings.extend(f"{prefix}.{field}: missing" for field in missing)
        lane_id = lane.get("lane_id")
        if not isinstance(lane_id, str) or not lane_id:
            findings.append(f"{prefix}.lane_id: must be non-empty")
            lane_id = f"<lane-{index}>"
        elif lane_id in seen:
            findings.append(f"{prefix}.lane_id: duplicate {lane_id}")
        seen.add(lane_id)

        if lane.get("current_stage") not in READINESS_STAGES:
            findings.append(f"{prefix}.current_stage: invalid value")
        if lane.get("training_readiness") not in TRAINING_READINESS:
            findings.append(f"{prefix}.training_readiness: invalid value")

        authorization = lane.get("authorization")
        if not isinstance(authorization, dict):
            findings.append(f"{prefix}.authorization: must be an object")
            authorization = {}
        authorized = authorization.get("training_authorized") is True
        if authorized:
            missing_auth = sorted(AUTHORIZED_FIELDS - authorization.keys())
            findings.extend(
                f"{prefix}.authorization.{field}: required for authorization"
                for field in missing_auth
            )
            if lane.get("current_stage") != "training-authorized":
                findings.append(f"{prefix}: authorized lane must be training-authorized")
            if lane.get("training_readiness") != "ready-for-controlled-training":
                findings.append(f"{prefix}: authorized lane must be ready-for-controlled-training")
        elif lane.get("current_stage") == "training-authorized":
            findings.append(f"{prefix}: training-authorized requires training_authorized=true")

        if lane_id == "dialogue-swe-bench":
            license_status = (lane.get("artifact_license") or {}).get("status")
            if license_status != "declared" and authorized:
                findings.append(f"{prefix}: undeclared artifact license cannot authorize training")
        if lane_id == "swe-gym-openhands-verifier" and authorized:
            validation = lane.get("validation") or {}
            if not validation.get("task_joins_validated") or not validation.get("labels_validated"):
                findings.append(f"{prefix}: verifier joins and labels must be validated before authorization")

        references = lane.get("references")
        if not isinstance(references, dict):
            findings.append(f"{prefix}.references: must be an object")
            continue
        for kind, refs in references.items():
            if kind not in REFERENCE_KINDS:
                findings.append(f"{prefix}.references.{kind}: unknown reference kind")
                continue
            if not isinstance(refs, list):
                findings.append(f"{prefix}.references.{kind}: must be a list")
                continue
            for ref_index, ref in enumerate(refs):
                if not isinstance(ref, dict) or "path" not in ref:
                    findings.append(f"{prefix}.references.{kind}[{ref_index}]: path object required")
                    continue
                if ref.get("planned") is True:
                    continue
                try:
                    raw_path = str(ref["path"])
                    ref_path = Path(raw_path)
                    if ref_path.is_absolute() or "C:/pneuma-data" in raw_path or "C:\\pneuma-data" in raw_path:
                        findings.append(f"{prefix}.references.{kind}[{ref_index}]: external reference {raw_path}")
                        continue
                    target = (root / ref_path).resolve()
                    if root.resolve() not in target.parents and target != root.resolve():
                        findings.append(f"{prefix}.references.{kind}[{ref_index}]: reference escapes repository")
                        continue
                    if not target.is_file():
                        findings.append(f"{prefix}.references.{kind}[{ref_index}]: missing {raw_path}")
                except (OSError, TypeError, ValueError) as exc:
                    findings.append(f"{prefix}.references.{kind}[{ref_index}]: {exc}")
    return tuple(sorted(findings))


def check_registry(path: Path = REGISTRY_PATH) -> None:
    findings = validate_registry(load_registry(path))
    if findings:
        raise DatasetReadinessError("; ".join(findings))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the dataset readiness registry")
    parser.add_argument("--check", action="store_true", help="validate the canonical registry")
    args = parser.parse_args()
    if args.check:
        check_registry()
        print("PASS: dataset readiness registry is valid and repository-coherent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

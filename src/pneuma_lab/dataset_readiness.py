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

CORPUS_PATH = (
    ROOT / "docs" / "data" / "training-readiness" / "pneuma-brain-v0-corpus.json"
)
LEAKAGE_REGISTRY_PATH = (
    ROOT
    / "docs"
    / "data"
    / "training-readiness"
    / "cross-dataset-leakage-registry.json"
)
CORPUS_SCHEMA_VERSION = "0.1.0"
CORPUS_ID = "pneuma-brain-v0"
CORPUS_ROLES = {
    "v0_1_train",
    "expansion_train_later",
    "eval_only",
    "blocked",
}
# A v0_1_train member must be a genuine training lane: never eval-only or blocked.
NON_TRAINABLE_READINESS = {"eval-only", "blocked"}

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
        raise DatasetReadinessError(
            f"external or absolute reference is forbidden: {raw}"
        )
    resolved = (ROOT / value).resolve()
    if ROOT not in resolved.parents and resolved != ROOT:
        raise DatasetReadinessError(f"reference escapes repository: {raw}")
    return resolved


def validate_registry(
    registry: dict[str, Any], *, root: Path = ROOT
) -> tuple[str, ...]:
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
                findings.append(
                    f"{prefix}: authorized lane must be training-authorized"
                )
            if lane.get("training_readiness") != "ready-for-controlled-training":
                findings.append(
                    f"{prefix}: authorized lane must be ready-for-controlled-training"
                )
        elif lane.get("current_stage") == "training-authorized":
            findings.append(
                f"{prefix}: training-authorized requires training_authorized=true"
            )

        if lane_id == "dialogue-swe-bench":
            license_status = (lane.get("artifact_license") or {}).get("status")
            if license_status != "declared" and authorized:
                findings.append(
                    f"{prefix}: undeclared artifact license cannot authorize training"
                )
        if lane_id == "swe-gym-openhands-verifier" and authorized:
            validation = lane.get("validation") or {}
            if not validation.get("task_joins_validated") or not validation.get(
                "labels_validated"
            ):
                findings.append(
                    f"{prefix}: verifier joins and labels must be validated before authorization"
                )

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
                    findings.append(
                        f"{prefix}.references.{kind}[{ref_index}]: path object required"
                    )
                    continue
                if ref.get("planned") is True:
                    continue
                try:
                    raw_path = str(ref["path"])
                    ref_path = Path(raw_path)
                    if (
                        ref_path.is_absolute()
                        or "C:/pneuma-data" in raw_path
                        or "C:\\pneuma-data" in raw_path
                    ):
                        findings.append(
                            f"{prefix}.references.{kind}[{ref_index}]: external reference {raw_path}"
                        )
                        continue
                    target = (root / ref_path).resolve()
                    if (
                        root.resolve() not in target.parents
                        and target != root.resolve()
                    ):
                        findings.append(
                            f"{prefix}.references.{kind}[{ref_index}]: reference escapes repository"
                        )
                        continue
                    if not target.is_file():
                        findings.append(
                            f"{prefix}.references.{kind}[{ref_index}]: missing {raw_path}"
                        )
                except (OSError, TypeError, ValueError) as exc:
                    findings.append(f"{prefix}.references.{kind}[{ref_index}]: {exc}")
    return tuple(sorted(findings))


def check_registry(path: Path = REGISTRY_PATH) -> None:
    findings = validate_registry(load_registry(path))
    if findings:
        raise DatasetReadinessError("; ".join(findings))


def _existing_repo_file(raw: object, *, root: Path, label: str) -> str | None:
    """Return a finding string if a repo-relative reference is missing/unsafe."""
    text = str(raw or "")
    if not text:
        return f"{label}: missing reference"
    path = Path(text)
    if path.is_absolute() or "C:/pneuma-data" in text or "C:\\pneuma-data" in text:
        return f"{label}: external or absolute reference {text}"
    target = (root / path).resolve()
    if root.resolve() not in target.parents and target != root.resolve():
        return f"{label}: reference escapes repository"
    if not target.is_file():
        return f"{label}: missing {text}"
    return None


def validate_corpus(
    corpus: dict[str, Any],
    registry: dict[str, Any],
    leakage: dict[str, Any],
    *,
    root: Path = ROOT,
) -> tuple[str, ...]:
    """Validate the unified PneumaBrain-v0 corpus manifest against the registry.

    Enforces that every registry lane is resolved to exactly one legal role,
    that v0_1_train members are genuine training lanes (never eval-only or
    blocked), that eval-only/blocked roles agree with the registry, that the
    quarantine repos equal the cross-dataset leakage overlap set, and that the
    corpus is still gated behind an unsigned human authorization. An empty tuple
    means valid; findings are deterministically sorted.
    """
    findings: list[str] = []
    if corpus.get("corpus_schema_version") != CORPUS_SCHEMA_VERSION:
        findings.append("corpus_schema_version: unsupported or missing")
    if corpus.get("corpus_id") != CORPUS_ID:
        findings.append("corpus_id: must be pneuma-brain-v0")

    lanes_by_id: dict[str, dict] = {}
    for lane in registry.get("lanes") or []:
        if isinstance(lane, dict) and isinstance(lane.get("lane_id"), str):
            lanes_by_id[lane["lane_id"]] = lane
    registry_ids = set(lanes_by_id)

    lane_roles = corpus.get("lane_roles")
    if not isinstance(lane_roles, dict) or not lane_roles:
        return tuple(sorted(findings + ["lane_roles: must be a non-empty object"]))

    role_ids = set(lane_roles)
    for missing in sorted(registry_ids - role_ids):
        findings.append(f"lane_roles: registry lane {missing} has no assigned role")
    for extra in sorted(role_ids - registry_ids):
        findings.append(f"lane_roles: {extra} is not a registry lane")

    for lane_id in sorted(role_ids):
        role = lane_roles[lane_id]
        if role not in CORPUS_ROLES:
            findings.append(f"lane_roles.{lane_id}: invalid role {role!r}")
            continue
        lane = lanes_by_id.get(lane_id)
        if lane is None:
            continue
        readiness = lane.get("training_readiness")
        if role == "v0_1_train" and readiness in NON_TRAINABLE_READINESS:
            findings.append(
                f"lane_roles.{lane_id}: v0_1_train member cannot be {readiness}"
            )
        if role == "eval_only" and readiness != "eval-only":
            findings.append(
                f"lane_roles.{lane_id}: eval_only role requires training_readiness eval-only"
            )
        if role == "blocked":
            if readiness != "blocked":
                findings.append(
                    f"lane_roles.{lane_id}: blocked role requires training_readiness blocked"
                )
            if (lane.get("authorization") or {}).get(
                "training_authorized"
            ) is not False:
                findings.append(
                    f"lane_roles.{lane_id}: blocked lane must not be training_authorized"
                )

    expected_members = {
        lane_id for lane_id, role in lane_roles.items() if role == "v0_1_train"
    }
    members = corpus.get("members")
    if not isinstance(members, list) or not members:
        findings.append("members: must be a non-empty list")
    else:
        member_ids = set()
        for index, member in enumerate(members):
            if not isinstance(member, dict) or not member.get("lane_id"):
                findings.append(f"members[{index}]: lane_id required")
                continue
            member_ids.add(member["lane_id"])
        for missing in sorted(expected_members - member_ids):
            findings.append(f"members: v0_1_train lane {missing} is not listed")
        for extra in sorted(member_ids - expected_members):
            findings.append(f"members: {extra} is listed but not role v0_1_train")

    overlap = ((leakage.get("pairs") or [{}])[0]).get("overlapping_repos") or []
    quarantine = (corpus.get("quarantine") or {}).get("repos") or []
    if sorted(quarantine) != sorted(overlap):
        findings.append(
            "quarantine.repos: must equal the cross-dataset leakage overlap set"
        )

    if corpus.get("training_authorized") is not False:
        findings.append("training_authorized: must be false")
    authorization = corpus.get("authorization") or {}
    if authorization.get("status") != "not_authorized":
        findings.append("authorization.status: must be not_authorized")

    for label, ref in (
        ("roadmap_ref", corpus.get("roadmap_ref")),
        ("registry_ref", corpus.get("registry_ref")),
        ("leakage_registry_ref", corpus.get("leakage_registry_ref")),
        ("training_example_schema", corpus.get("training_example_schema")),
        ("authorization.schema", authorization.get("schema")),
        ("authorization.pending_template", authorization.get("pending_template")),
    ):
        problem = _existing_repo_file(ref, root=root, label=label)
        if problem:
            findings.append(problem)

    template_ref = authorization.get("pending_template")
    if template_ref and not _existing_repo_file(
        template_ref, root=root, label="authorization.pending_template"
    ):
        template = json.loads((root / str(template_ref)).read_text(encoding="utf-8"))
        if template.get("decision") != "not_authorized":
            findings.append(
                "authorization.pending_template: decision must be not_authorized"
            )
        if template.get("corpus_id") != CORPUS_ID:
            findings.append(
                "authorization.pending_template: corpus_id must be pneuma-brain-v0"
            )

    return tuple(sorted(findings))


def check_corpus(
    corpus_path: Path = CORPUS_PATH,
    registry_path: Path = REGISTRY_PATH,
    leakage_path: Path = LEAKAGE_REGISTRY_PATH,
) -> None:
    findings = validate_corpus(
        load_registry(corpus_path),
        load_registry(registry_path),
        load_registry(leakage_path),
    )
    if findings:
        raise DatasetReadinessError("; ".join(findings))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the dataset readiness registry and unified corpus"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the canonical registry and corpus manifest",
    )
    args = parser.parse_args()
    if args.check:
        check_registry()
        check_corpus()
        print(
            "PASS: dataset readiness registry and PneumaBrain-v0 corpus are valid "
            "and repository-coherent."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Prepare the prospective, outcome-blind C120 power run from sealed inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

from pneuma_lab.cloud.production_run import canonical_bytes
from pneuma_lab.resampling_null.artifacts import validate_record, write_record
from pneuma_lab.resampling_null.power import (
    grid_content_sha256,
    load_power_authority,
    load_power_config,
    seal_roster_bound_power_authority,
)
from pneuma_lab.resampling_null.types import ArtifactRef


ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md"
AMENDMENT = ROOT / "docs/research/neurips-2026-workshop/67-minimal-prelaunch-protocol-amendment-20260805.md"
GRID = ROOT / "fixtures/resampling_null/p0-power-grid.json"
TOPOLOGY = ROOT / "fixtures/resampling_null/p0-power-screen-topology.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _ref(root: Path, path: Path, role: str, media_type: str = "application/json") -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "role": role,
        "relative_path": path.resolve().relative_to(root.resolve()).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "media_type": media_type,
    }


def _artifact(value: dict[str, object]) -> ArtifactRef:
    return ArtifactRef(
        role=str(value["role"]),
        relative_path=str(value["relative_path"]),
        sha256=str(value["sha256"]),
        byte_count=int(value["byte_count"]),
        media_type=str(value["media_type"]),
    )


def _secret(path: Path, size: int) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raw = path.read_bytes()
        if len(raw) != size:
            raise ValueError(f"secret has wrong size: {path}")
        return raw
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        raw = os.urandom(size)
        os.write(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return raw


def _seal_c160_feasibility(
    power: Path,
    *,
    authority_ref: ArtifactRef,
    grid_ref: ArtifactRef,
    topology_ref: ArtifactRef,
    counts: dict[str, int],
) -> Path:
    authority = load_power_authority(authority_ref, run_root=power)
    config = load_power_config(
        authority_ref,
        grid_ref,
        topology_ref,
        run_root=power,
        tier=120,
    )
    grid_digest = grid_content_sha256(
        grid_ref,
        run_root=power,
        authority_kind=authority.authority_kind,
    )
    if authority.prelaunch_protocol_amendment_ref is None:
        raise ValueError("prospective C120 authority lacks the registered prelaunch amendment")
    c160_path = power / "c160-roster-feasibility.json"
    _write(
        c160_path,
        {
            "contract_id": "official-power-tier-feasibility-v1",
            "schema_version": "1",
            "study_id": "neurips-2026-resampling-null",
            "tier": 160,
            "decision": "FEASIBILITY_NO_GO",
            "reason": "frozen_eligible_roster_has_no_c160_extension",
            "authority_ref_sha256": authority_ref.sha256,
            "roster_ref_sha256": authority.roster_ref.sha256,
            "tier_membership_sha256": authority.tier_membership_sha256,
            "rng_contract_sha256": config.rng_contract_sha256,
            "grid_content_sha256": grid_digest,
            "amendment_ref_sha256": authority.prelaunch_protocol_amendment_ref.sha256,
            "task_counts": counts,
        },
    )
    return c160_path


def prepare(package: Path, secret_dir: Path) -> dict[str, str]:
    package = package.resolve()
    power = package / "power"
    inputs = power / "sources"
    task_registry_path = package / "inputs/task-registry.json"
    task_registry = json.loads(task_registry_path.read_text(encoding="utf-8"))
    tasks = task_registry.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("task registry lacks tasks")
    counts = {
        benchmark: sum(isinstance(task, dict) and task.get("benchmark") == benchmark for task in tasks)
        for benchmark in ("SWE", "TAU")
    }
    if counts != {"SWE": 120, "TAU": 120}:
        raise ValueError(f"C120 requires 120 tasks per benchmark, observed {counts}")

    root_key = _secret(secret_dir / "official-study-root-key.bin", 32)
    derived = {
        label: hashlib.sha256(b"official-study-seed-v1\0" + label.encode("ascii") + b"\0" + root_key).digest()
        for label in ("roster", "schedule", "assignment", "packet", "model", "benchmark", "unblind")
    }
    for label, raw in derived.items():
        target = secret_dir / f"{label}-seed.bin"
        if not target.exists():
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                os.write(descriptor, raw)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    copied_task_registry = inputs / "task-registry.json"
    copied_task_registry.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(task_registry_path, copied_task_registry)
    commitments_path = inputs / "deterministic-seed-commitments.json"
    commitments = {
        "record_kind": "official_study_seed_commitments",
        "schema_version": "1",
        "study_id": "neurips-2026-resampling-null",
        "commitment_scheme": "sha256-domain-separated-secret-v1",
        "commitments": {
            label: hashlib.sha256(b"official-study-commitment-v1\0" + label.encode("ascii") + b"\0" + raw).hexdigest()
            for label, raw in derived.items()
        },
    }
    _write(commitments_path, commitments)

    roster_tasks = []
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("task registry contains a non-object task")
        roster_tasks.append({**task, "tiers": [120]})
    roster_tasks.sort(key=lambda task: (str(task["benchmark"]), str(task["task_id"])))
    roster_path = inputs / "c120-roster.json"
    _write(
        roster_path,
        {
            "record_kind": "resampling_roster_v1",
            "schema_version": "1",
            "roster_kind": "prospective_frozen",
            "supported_tiers": [120],
            "tasks": roster_tasks,
        },
    )

    copied = {
        "grid": (GRID, inputs / GRID.name),
        "topology": (TOPOLOGY, inputs / TOPOLOGY.name),
        "design": (DESIGN, inputs / DESIGN.name),
        "amendment": (AMENDMENT, inputs / AMENDMENT.name),
    }
    for name, (source, target) in copied.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        if name in {"grid", "topology"}:
            _write(target, json.loads(source.read_text(encoding="utf-8")))
        else:
            shutil.copyfile(source, target)

    source_names = {
        "assignment": "assignment-pending.json",
        "provider": "provider-binding.json",
        "adapter": "benchmark-adapter-manifest.json",
        "lock": "input-lock.json",
        "analysis": "analysis-graph.json",
    }
    copied_sources: dict[str, Path] = {}
    for name, filename in source_names.items():
        source = package / "inputs" / filename
        target = inputs / filename
        shutil.copyfile(source, target)
        copied_sources[name] = target

    task_ref = _ref(power, copied_task_registry, "task_registry")
    roster_ref = _ref(power, roster_path, "roster")
    assignment_ref = _ref(power, copied_sources["assignment"], "assignment_program")
    provider_ref = _ref(power, copied_sources["provider"], "provider_lane_plan")
    adapter_ref = _ref(power, copied_sources["adapter"], "branch_program_registry")
    lock_ref = _ref(power, copied_sources["lock"], "storage_policy_contract")
    grid_ref = _ref(power, copied["grid"][1], "power_grid")
    topology_ref = _ref(power, copied["topology"][1], "power_screen_topology")
    analysis_ref = _ref(power, copied_sources["analysis"], "packet_policy")
    commitments_ref = _ref(power, commitments_path, "required_document_kinds")
    design_ref = _ref(power, copied["design"][1], "source_revision", "text/markdown")
    amendment_ref = _ref(power, copied["amendment"][1], "prelaunch_protocol_amendment", "text/markdown")

    manifest_path = power / "study-manifest.json"
    manifest = {
        "record_kind": "resampling_study_manifest",
        "schema_version": "0.1.0",
        "study_id": "neurips-2026-resampling-null",
        "frozen_created_at": "2026-08-06T05:30:00Z",
        "provenance": {"design_sha256": _sha(DESIGN), "code_sha256": _sha(ROOT / "src/pneuma_lab/resampling_null/power.py")},
        "payload": {
            "task_registry_ref": task_ref,
            "roster_ref": roster_ref,
            "eligibility_manifest_ref": None,
            "roster_ceremony_policy_ref": None,
            "roster_ceremony_receipt_ref": None,
            "prelaunch_protocol_amendment_ref": amendment_ref,
            "assignment_program_ref": assignment_ref,
            "provider_lane_plan_ref": provider_ref,
            "branch_program_registry_ref": adapter_ref,
            "storage_policy_contract_ref": lock_ref,
            "power_grid_ref": grid_ref,
            "power_screen_topology_ref": topology_ref,
            "tokenizer_ref": lock_ref,
            "packet_template_ref": adapter_ref,
            "packet_policy_ref": analysis_ref,
            "pad_unit_set_ref": adapter_ref,
            "source_revision_refs": [design_ref, amendment_ref],
            "commitment_scheme": "official-study-deterministic-commitments-v1",
            "roster_local_nonce_commitment_sha256": commitments["commitments"]["roster"],
            "schedule_seed_commitment_sha256": commitments["commitments"]["schedule"],
            "assignment_master_key_commitment_sha256": commitments["commitments"]["assignment"],
            "required_document_kinds_ref": commitments_ref,
        },
    }
    validate_record(manifest)
    if manifest_path.exists():
        if manifest_path.read_bytes() != canonical_bytes(manifest):
            raise FileExistsError("existing power study manifest differs")
        manifest_ref = _artifact(_ref(power, manifest_path, "study_manifest"))
    else:
        manifest_ref = write_record(manifest_path, manifest, run_root=power, role="study_manifest")

    authority_path = power / "authority.json"
    if authority_path.exists():
        authority_ref = _artifact(_ref(power, authority_path, "power_authority", "application/vnd.pneuma.power-authority+json"))
    else:
        authority_ref = seal_roster_bound_power_authority(manifest_ref, run_root=power, out=authority_path)

    grid_artifact = _artifact(grid_ref)
    topology_artifact = _artifact(topology_ref)
    c160_path = _seal_c160_feasibility(
        power,
        authority_ref=authority_ref,
        grid_ref=grid_artifact,
        topology_ref=topology_artifact,
        counts=counts,
    )
    return {
        "manifest": manifest_ref.relative_path,
        "authority": authority_ref.relative_path,
        "grid": str(grid_ref["relative_path"]),
        "topology": str(topology_ref["relative_path"]),
        "c160_feasibility": c160_path.relative_to(power).as_posix(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--secret-dir", type=Path, default=Path.home() / ".pneuma-lab" / "official-study-20260806")
    parser.add_argument("--refresh-c160-only", action="store_true")
    args = parser.parse_args()
    if args.refresh_c160_only:
        power = args.package.resolve() / "power"
        registry = json.loads((args.package.resolve() / "inputs/task-registry.json").read_text(encoding="utf-8"))
        tasks = registry.get("tasks")
        if not isinstance(tasks, list):
            raise ValueError("task registry lacks tasks")
        counts = {
            benchmark: sum(isinstance(task, dict) and task.get("benchmark") == benchmark for task in tasks)
            for benchmark in ("SWE", "TAU")
        }
        if counts != {"SWE": 120, "TAU": 120}:
            raise ValueError(f"C120 requires 120 tasks per benchmark, observed {counts}")
        authority_ref = _artifact(
            _ref(
                power,
                power / "authority.json",
                "power_authority",
                "application/vnd.pneuma.power-authority+json",
            )
        )
        grid_ref = _artifact(_ref(power, power / "sources/p0-power-grid.json", "power_grid"))
        topology_ref = _artifact(
            _ref(power, power / "sources/p0-power-screen-topology.json", "power_screen_topology")
        )
        c160 = _seal_c160_feasibility(
            power,
            authority_ref=authority_ref,
            grid_ref=grid_ref,
            topology_ref=topology_ref,
            counts=counts,
        )
        print(json.dumps({"c160_feasibility": c160.relative_to(power).as_posix()}, sort_keys=True))
        return 0
    print(json.dumps(prepare(args.package, args.secret_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

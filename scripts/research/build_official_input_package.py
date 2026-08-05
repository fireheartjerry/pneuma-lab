"""Build the digest-bound, non-authorizing official-study input candidate.

This command only seals already-retained real input evidence and the registered
design contracts.  It never performs the roster ceremony, reveals a seed,
selects a power tier, creates an assignment, or authorizes execution.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.inputs import verify_input_lock, verify_input_receipts
from pneuma_lab.cloud.manifests import (
    validate_official_analysis_graph,
    validate_official_assignment_pending,
    validate_official_input_package,
    validate_official_rng_commitment,
    validate_official_roster_candidate,
    validate_registered_benchmark_adapter_manifest,
    validate_production_provider_binding,
)
from pneuma_lab.cloud.production_run import ProductionRunSpec, canonical_bytes
from pneuma_lab.resampling_null.preflight import validate_task_registry


ROOT = Path(__file__).resolve().parents[2]
INPUT_EVIDENCE = ROOT / "docs/research/neurips-2026-workshop/evidence/step5b-real-input-lock-20260801"
ROSTER_EVIDENCE = ROOT / "docs/research/neurips-2026-workshop/evidence/step5b-c120-g-roster-final-20260801"
DESIGN = ROOT / "docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md"
FREEZE = ROOT / "docs/research/neurips-2026-workshop/38-experiment-design-freeze.md"
CODE_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
IMAGE_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudManifestError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CloudManifestError(f"JSON object required: {path}")
    return value


def _write(path: Path, value: object) -> str:
    raw = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(package: Path, path: Path, *, role: str, media_type: str = "application/json") -> dict[str, object]:
    relative = path.resolve().relative_to(package.resolve()).as_posix()
    raw = path.read_bytes()
    return {
        "role": role,
        "relative_path": relative,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "media_type": media_type,
    }


def _copy(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return destination


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    commit = result.stdout.strip()
    if result.returncode != 0 or not CODE_SHA_RE.fullmatch(commit):
        raise CloudManifestError("cannot resolve a full source commit")
    return commit


def _build_task_registry(package: Path, *, swe_source: Path, tau_source: Path) -> Path:
    swe = _load(swe_source)
    tau = _load(tau_source)
    tasks: list[dict[str, object]] = []
    for row in swe.get("rows", []):
        if not isinstance(row, dict):
            raise CloudManifestError("SWE selection contains a non-object row")
        instance_id = row.get("instance_id")
        language = row.get("language")
        repo = row.get("repo")
        base_commit = row.get("base_commit")
        if not all(isinstance(value, str) and value for value in (instance_id, language, repo, base_commit)):
            raise CloudManifestError("SWE selection row lacks immutable task identity")
        tasks.append(
            {
                "task_id": f"swe:{instance_id}",
                "benchmark": "SWE",
                "stratum": f"language:{language}",
                "lineage": f"{repo}@{base_commit}",
                "groups": [
                    {"kind": "language", "value": language},
                    {"kind": "domain", "value": repo},
                ],
            }
        )
    for row in tau.get("rows", []):
        if not isinstance(row, dict):
            raise CloudManifestError("tau2 selection contains a non-object row")
        domain = row.get("domain")
        task_id = row.get("task_id")
        if not isinstance(domain, str) or not domain or not isinstance(task_id, str) or not task_id:
            raise CloudManifestError("tau2 selection row lacks immutable task identity")
        tasks.append(
            {
                "task_id": f"tau:{domain}:{task_id}",
                "benchmark": "TAU",
                "stratum": f"domain:{domain}",
                "lineage": f"tau2:{domain}:{task_id}",
                "groups": [{"kind": "domain", "value": domain}],
            }
        )
    registry: dict[str, object] = {
        "record_kind": "resampling_task_registry_v1",
        "schema_version": "1",
        "tasks": tasks,
    }
    validate_task_registry(registry)
    target = package / "inputs/task-registry.json"
    _write(target, registry)
    return target


def _copy_input_lock(package: Path, task_manifest: Path, *, frozen_timestamp: str) -> Path:
    lock = deepcopy(_load(INPUT_EVIDENCE / "input-lock.json"))
    receipt_refs: list[dict[str, object]] = []
    for section in ("model_pins", "tokenizer_pin", "benchmark_pins", "verifier_sources"):
        values = lock[section] if section != "tokenizer_pin" else [lock[section]]
        for pin in values:
            receipt_refs.append(pin["snapshot_receipt"])
    receipt_refs.extend(lock["contamination_receipts"])
    receipt_refs.extend(lock["license_receipts"])
    copied: dict[str, str] = {}
    for receipt in receipt_refs:
        old_relative = str(receipt["relative_path"])
        source = INPUT_EVIDENCE / old_relative
        destination = package / "inputs/receipts" / Path(old_relative).name
        if old_relative in copied and copied[old_relative] != destination.as_posix():
            raise CloudManifestError("input receipt is copied to conflicting destinations")
        _copy(source, destination)
        copied[old_relative] = destination.relative_to(package).as_posix()
        receipt["relative_path"] = copied[old_relative]
        receipt["size_bytes"] = destination.stat().st_size
        receipt["sha256"] = _sha(destination)
    lock["frozen_timestamp"] = frozen_timestamp
    lock["provenance"] = {
        "design_sha256": _sha(DESIGN),
        "code_sha256": _sha(Path(__file__)),
    }
    task_digest = _sha(task_manifest)
    task_size = task_manifest.stat().st_size
    for pin in lock["benchmark_pins"]:
        pin["task_manifest_sha256"] = task_digest
        pin["task_manifest_size_bytes"] = task_size
    target = package / "inputs/input-lock.json"
    _write(target, lock)
    verify_input_receipts(lock, package)
    if not verify_input_lock(lock):
        raise CloudManifestError("input lock semantic digest could not be computed")
    return target


def _build_roster_candidate(package: Path, input_lock: Path) -> Path:
    source_files = {
        "swe": "swe-selection.json",
        "tau": "tau2-selection.json",
        "closure": "closure.json",
        "isolation": "isolation-receipt.json",
    }
    refs: dict[str, dict[str, object]] = {}
    for key, name in source_files.items():
        destination = _copy(ROSTER_EVIDENCE / name, package / "inputs/roster-sources" / name)
        refs[key] = _ref(package, destination, role=f"roster_{key}")
    swe = _load(ROSTER_EVIDENCE / "swe-selection.json")
    tau = _load(ROSTER_EVIDENCE / "tau2-selection.json")
    if swe.get("authority_sha256") != tau.get("authority_sha256"):
        raise CloudManifestError("SWE and tau2 selections have different authority digests")
    candidate = {
        "record_kind": "cloud_official_roster_candidate",
        "schema_version": "0.1.0",
        "study_id": "neurips-2026-resampling-null",
        "status": "candidate_prelaunch",
        "synthetic_authority": False,
        "ceremony_status": "not_performed",
        "authority_sha256": swe["authority_sha256"],
        "input_lock_sha256": _sha(input_lock),
        "selection_refs": [refs["swe"], refs["tau"]],
        "closure_ref": refs["closure"],
        "isolation_ref": refs["isolation"],
        "eligible_confirmation_ref": None,
        "power_selection_status": "pending_c120_c160_validation",
    }
    validate_official_roster_candidate(candidate)
    target = package / "inputs/roster-candidate.json"
    _write(target, candidate)
    return target


def _build_rng(package: Path) -> Path:
    record = {
        "record_kind": "cloud_official_rng_commitment",
        "schema_version": "0.1.0",
        "study_id": "neurips-2026-resampling-null",
        "status": "pending_commitments",
        "contract_id": "official-study-rng-v1",
        "frame_contract": {
            "frame_id": "pneuma-resampling-null-frame-v1",
            "commitment_frame": "commitment-v1",
            "derivation_domains": ["roster", "schedule", "assignment", "model", "benchmark", "unblind"],
            "root_status": "revealed_only_after_external_authority",
        },
        "commitments": [
            {"label": "roster-local-nonce", "representation": "bytes32", "commitment_status": "pending_external_precommit"},
            {"label": "schedule-seed", "representation": "u64", "commitment_status": "pending_external_precommit"},
            {"label": "assignment-master-key", "representation": "bytes32", "commitment_status": "pending_external_precommit"},
        ],
        "reveals": None,
    }
    validate_official_rng_commitment(record)
    target = package / "inputs/rng-commitment.json"
    _write(target, record)
    return target


def _build_analysis_graph(package: Path) -> Path:
    source_paths = [
        FREEZE,
        DESIGN,
        ROOT / "src/pneuma_lab/resampling_null/analysis.py",
        ROOT / "src/pneuma_lab/resampling_null/freeze.py",
        ROOT / "src/pneuma_lab/resampling_null/blinding.py",
        ROOT / "src/pneuma_lab/resampling_null/types.py",
        ROOT / "src/pneuma_lab/resampling_null/cli.py",
    ]
    graph = {
        "record_kind": "cloud_official_analysis_graph",
        "schema_version": "0.1.0",
        "study_id": "neurips-2026-resampling-null",
        "status": "frozen_candidate_no_results",
        "graph_id": "resampling-null-registered-analysis-graph-v1",
        "sources": [{"path": path.relative_to(ROOT).as_posix(), "sha256": _sha(path)} for path in source_paths],
    }
    validate_official_analysis_graph(graph)
    target = package / "inputs/analysis-graph.json"
    _write(target, graph)
    return target


def _build_provider_binding(package: Path) -> Path:
    binding = {
        "record_kind": "cloud_production_provider_binding",
        "schema_version": "0.1.0",
        "provider": "aws",
        "region": "us-east-1",
        "production_deployment": {
            "deployment_id": "aws-batch-two-independent-g6e-spot-workers-v1",
            "instance_type": "g6e.2xlarge",
            "worker_count": 2,
            "spot_only": True,
            "max_attempts": 1,
            "official_topology": "two-independent-8-vcpu-one-l40s-workers",
        },
        "bounded_surface_deployment": {
            "deployment_id": "aws-ec2-ssm-cpu-production-role-surface-v1",
            "instance_type": "m7i.large",
            "capacity_type": "on-demand",
            "max_duration_seconds": 900,
            "max_usd": 3.0,
            "network": "no-inbound-egress-ssm-ecr-only",
            "metadata_options": "IMDSv2-required",
            "role_sandbox": "network-none-read-only-cap-drop-all-no-new-privileges",
        },
        "forbidden_actions": ["official_model", "approved_benchmark", "pilot", "canonical_p0_grid", "scientific_analysis", "unblind"],
        "teardown": {"required": True, "active_resource_absence": True, "retained_artifacts": ["immutable_ecr_images", "sbom_records", "compact_receipts"]},
        "image_registry": {"repository_prefix": "pneuma-official-production", "tag_mutability": "IMMUTABLE", "scan_on_push": True, "encryption": "AES256"},
    }
    validate_production_provider_binding(binding)
    target = package / "inputs/provider-binding.json"
    _write(target, binding)
    return target


def _build_benchmark_adapter_manifest(package: Path, input_lock: Path) -> Path:
    lock = _load(input_lock)
    swe_pin = lock["benchmark_pins"][0]
    tau_pin = next(pin for pin in lock["verifier_sources"] if pin["repository"] == "sierra-research/tau2-bench")
    record = {
        "record_kind": "cloud_registered_benchmark_adapter_manifest",
        "schema_version": "0.1.0",
        "status": "prelaunch_source_binding",
        "adapters": {
            "swe_multilang": {
                "argv": ["/opt/pneuma/benchmark-adapters/swe-live/adapter"],
                "source_repository": swe_pin["repository"],
                "source_revision": swe_pin["revision"],
                "source_snapshot_sha256": swe_pin["snapshot_receipt"]["sha256"],
                "executable_relative_path": "benchmark-adapters/swe-live/adapter",
            },
            "tau2": {
                "argv": ["/opt/pneuma/benchmark-adapters/tau2/adapter"],
                "source_repository": tau_pin["repository"],
                "source_revision": tau_pin["revision"],
                "source_snapshot_sha256": tau_pin["snapshot_receipt"]["sha256"],
                "executable_relative_path": "benchmark-adapters/tau2/adapter",
            },
        },
    }
    validate_registered_benchmark_adapter_manifest(record)
    target = package / "inputs/benchmark-adapter-manifest.json"
    _write(target, record)
    return target


def _build_assignment(package: Path, input_lock: Path, roster: Path) -> Path:
    record = {
        "record_kind": "cloud_official_assignment_pending",
        "schema_version": "0.1.0",
        "study_id": "neurips-2026-resampling-null",
        "status": "pending_live_authority",
        "synthetic_substitute_forbidden": True,
        "input_lock_sha256": _sha(input_lock),
        "roster_candidate_sha256": _sha(roster),
        "assignment_program": {
            "contract_id": "registered-assignment-program-v1",
            "matching_algorithm": "frozen-prefix-paired-matching-v1",
            "domains": ["swe_multilang", "tau2"],
            "draw_contract": "assignment-master-key-derived-frame-v1",
        },
        "assignment_master_key_status": "unrevealed",
        "sealed_assignment_ref": None,
    }
    validate_official_assignment_pending(record)
    target = package / "inputs/assignment-pending.json"
    _write(target, record)
    return target


def build_inputs(package: Path, *, frozen_timestamp: str) -> dict[str, Path]:
    package.mkdir(parents=True, exist_ok=True)
    task_manifest = _build_task_registry(
        package,
        swe_source=ROSTER_EVIDENCE / "swe-selection.json",
        tau_source=ROSTER_EVIDENCE / "tau2-selection.json",
    )
    input_lock = _copy_input_lock(package, task_manifest, frozen_timestamp=frozen_timestamp)
    roster = _build_roster_candidate(package, input_lock)
    assignment = _build_assignment(package, input_lock, roster)
    rng = _build_rng(package)
    analysis = _build_analysis_graph(package)
    provider = _build_provider_binding(package)
    adapter = _build_benchmark_adapter_manifest(package, input_lock)
    return {
        "input_lock": input_lock,
        "task_manifest": task_manifest,
        "roster": roster,
        "assignment": assignment,
        "rng": rng,
        "analysis": analysis,
        "provider": provider,
        "adapter": adapter,
    }


def _parse_images(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        role, separator, digest = value.partition("=")
        if separator != "=" or role in result or not IMAGE_RE.fullmatch(digest):
            raise CloudManifestError("images must be role=sha256:<64 lowercase hex>")
        result[role] = digest
    if set(result) != {"controller", "model-server", "benchmark-worker"}:
        raise CloudManifestError("images must bind all three production roles")
    return result


def build_run_spec(
    package: Path,
    inputs: dict[str, Path],
    *,
    surface: Path,
    source_commit: str,
    images: dict[str, str],
    action_id: str = "official-study-repair-candidate-20260804",
) -> Path:
    if not CODE_SHA_RE.fullmatch(source_commit):
        raise CloudManifestError("source commit must be a full lowercase commit")
    surface_destination = _copy(surface, package / "evidence/production-surface.json")
    surface_value = _load(surface_destination)
    if surface_value.get("input_lock_sha256") != _sha(inputs["input_lock"]):
        raise CloudManifestError("surface is not bound to this input lock")
    refs = {key: _ref(package, path, role=key) for key, path in inputs.items()}
    task_digest = _sha(inputs["task_manifest"])
    task_size = inputs["task_manifest"].stat().st_size
    run_spec: dict[str, object] = {
        "record_kind": "cloud_production_run_spec",
        "schema_version": "0.1.0",
        "action_id": action_id,
        "study_id": "neurips-2026-resampling-null",
        "run_mode": "official_candidate",
        "code_commit": source_commit,
        "image_bindings": [{"role": role, "image_digest": images[role]} for role in ("controller", "model-server", "benchmark-worker")],
        "execution_surface_ref": _ref(package, surface_destination, role="execution_surface"),
        "provider_binding_ref": refs["provider"],
        "input_lock_ref": refs["input_lock"],
        "model": {
            "repository": "Qwen/Qwen3.6-35B-A3B-FP8",
            "revision": "95a723d08a9490559dae23d0cff1d9466213d989",
            "tokenizer_revision": "95a723d08a9490559dae23d0cff1d9466213d989",
            "serving_engine": "vllm",
            "serving_engine_version": "0.19.0",
            "sampling": {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "presence_penalty": 0.0, "repetition_penalty": 1.0, "thinking_mode": True, "reasoning_parser": "qwen3", "tool_call_parser": "qwen3_coder"},
            "sampling_by_benchmark": {
                "swe_multilang": {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "presence_penalty": 0.0, "repetition_penalty": 1.0, "thinking_mode": True, "reasoning_parser": "qwen3", "tool_call_parser": "qwen3_coder"},
                "tau2": {"temperature": 1.0, "top_p": 0.95, "top_k": 20, "presence_penalty": 1.5, "repetition_penalty": 1.0, "thinking_mode": True, "reasoning_parser": "qwen3", "tool_call_parser": "qwen3_coder"},
            },
        },
        "benchmarks": [
            {"benchmark_id": "swe_multilang", "repository": "microsoft/SWE-bench-Live", "revision": "70ec57e852e3f2d195790fe71f553e272c691833", "dataset_repository": "SWE-bench-Live/MultiLang", "dataset_revision": "608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b", "task_manifest_sha256": task_digest, "task_manifest_size_bytes": task_size},
            {"benchmark_id": "tau2", "repository": "sierra-research/tau2-bench", "revision": "fc0055dc4e0a316c3f83133267fbd6faaa770992", "dataset_repository": "sierra-research/tau2-bench", "dataset_revision": "fc0055dc4e0a316c3f83133267fbd6faaa770992", "task_manifest_sha256": task_digest, "task_manifest_size_bytes": task_size},
        ],
        "task_manifest_ref": refs["task_manifest"],
        "roster_ref": refs["roster"],
        "assignment_ref": refs["assignment"],
        "rng": {"contract_id": "official-study-rng-v1", "root_u64": None, "draw_domains": ["roster", "schedule", "assignment", "model", "benchmark", "unblind"], "seeds": {}, "status": "pending_commitments", "commitment_ref": refs["rng"]},
        "worker_topology": {"worker_ids": ["worker-0", "worker-1"], "instance_type": "g6e.2xlarge", "vcpus_per_worker": 8, "gpus_per_worker": 1, "allocation_contract_id": "canonical-round-robin-two-worker-v1"},
        "budget": {"max_usd": 6400.0, "max_duration_seconds": 1200000, "max_attempts": 1, "spot_only": True},
        "output": {"root": "outputs/official-study", "worker_evidence_template": "outputs/official-study/{worker_id}.evidence.json", "controller_state_path": "outputs/official-study/controller.json"},
        "analysis_graph_ref": refs["analysis"],
        "power_report_ref": None,
        "power_tier": None,
        "official_authorization_ref": None,
        "official_key_registry_ref": None,
        "model_server": {"endpoint": "http://model-server.internal:8000", "launch_argv": ["python3", "-m", "vllm.entrypoints.openai.api_server", "--model", "Qwen/Qwen3.6-35B-A3B-FP8", "--revision", "95a723d08a9490559dae23d0cff1d9466213d989", "--tokenizer", "Qwen/Qwen3.6-35B-A3B-FP8", "--tokenizer-revision", "95a723d08a9490559dae23d0cff1d9466213d989", "--reasoning-parser", "qwen3", "--tool-call-parser", "qwen3_coder"], "readiness_timeout_seconds": 900, "request_timeout_seconds": 900},
        "benchmark_adapter": {"adapter_id": "registered-swe-live-tau2-v1", "entrypoint": ["python3", "-m", "pneuma_lab.cloud.registered_benchmark_adapter"], "timeout_seconds": 1800, "adapter_manifest_ref": refs["adapter"]},
    }
    spec_path = package / "run-spec-candidate.json"
    _write(spec_path, run_spec)
    ProductionRunSpec.load(spec_path, expected_sha256=_sha(spec_path))
    package_record = {
        "record_kind": "cloud_official_input_package",
        "schema_version": "0.1.0",
        "study_id": "neurips-2026-resampling-null",
        "status": "pre_launch_candidate",
        "authorizing": False,
        "input_lock_ref": refs["input_lock"],
        "task_manifest_ref": refs["task_manifest"],
        "roster_ref": refs["roster"],
        "assignment_ref": refs["assignment"],
        "rng_ref": refs["rng"],
        "analysis_graph_ref": refs["analysis"],
        "provider_binding_ref": refs["provider"],
        "benchmark_adapter_ref": refs["adapter"],
        "run_spec_candidate_ref": _ref(package, spec_path, role="run_spec_candidate"),
    }
    validate_official_input_package(package_record)
    _write(package / "input-package.json", package_record)
    return spec_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frozen-timestamp", default="2026-08-04T12:00:00Z")
    parser.add_argument("--inputs-only", action="store_true")
    parser.add_argument("--surface", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--image", action="append", default=[])
    parser.add_argument("--action-id", default="official-study-repair-candidate-20260804")
    args = parser.parse_args(argv)
    package = args.output_dir.resolve()
    inputs = build_inputs(package, frozen_timestamp=args.frozen_timestamp)
    if args.inputs_only:
        print(json.dumps({key: path.as_posix() for key, path in inputs.items()}, sort_keys=True))
        return 0
    if args.surface is None or args.source_commit is None:
        parser.error("--surface and --source-commit are required unless --inputs-only is set")
    images = _parse_images(args.image)
    spec = build_run_spec(
        package,
        inputs,
        surface=args.surface.resolve(),
        source_commit=args.source_commit,
        images=images,
        action_id=args.action_id,
    )
    print(json.dumps({"run_spec": spec.as_posix(), "run_spec_sha256": _sha(spec), "input_lock_sha256": _sha(inputs["input_lock"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run exactly one fresh FIXTURE-NONSCI v2 AWS surface attempt.

This is infrastructure admission evidence only.  The harness and provider
contain no model, benchmark, roster, assignment, packet, or official
authorization input.  Every action directory is immutable once written.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Mapping, cast

from pneuma_lab.cloud.aws_surface_provider import AwsSurfaceConfig, AwsSurfaceProvider, collect_preflight, validate_action_id
from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.manifests import (
    validate_production_image_receipt,
    validate_production_provider_binding,
    validate_production_role_receipt,
    validate_production_surface_e2e_receipt,
)
from pneuma_lab.cloud.production_controller import ProductionOrchestrator, ProductionStateStore
from pneuma_lab.cloud.production_run import canonical_bytes
from pneuma_lab.cloud.production_surface import require_production_execution_surface
from scripts.research.run_production_surface_e2e import ROLES, build_surface_record


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CloudManifestError(f"JSON object required: {path}")
    return value


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _write_once(path: Path, value: object) -> str:
    raw = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o644)
    except FileExistsError:
        if path.is_symlink() or not path.is_file() or path.read_bytes() != raw:
            raise CloudManifestError(f"immutable evidence path already contains different bytes: {path}")
        return _sha_bytes(raw)
    try:
        view = memoryview(raw)
        while view:
            view = view[os.write(descriptor, view):]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return _sha_bytes(raw)


def _ref(package: Path, path: Path, *, role: str) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "role": role,
        "relative_path": path.resolve().relative_to(package.resolve()).as_posix(),
        "sha256": _sha_bytes(raw),
        "byte_count": len(raw),
        "media_type": "application/json",
    }


def _action_evidence_root(package: Path, action_id: str) -> Path:
    if not action_id or any(separator in action_id for separator in ("/", "\\")) or action_id in {".", ".."}:
        raise CloudManifestError("action_id must be a single safe path component")
    return package / "evidence/production-surface-e2e" / action_id


def _validate_action_id(action_id: str) -> None:
    validate_action_id(action_id)


class _FailOnceObservation:
    def __init__(self, provider: AwsSurfaceProvider) -> None:
        self.provider = provider
        self.injected = False

    def observe(self, submission):
        if not self.injected:
            self.injected = True
            raise RuntimeError("injected_non_mutating_observation_error")
        return self.provider.observe(submission)


def _image_receipts(images_path: Path) -> tuple[dict[str, Any], ...]:
    images = _load(images_path)
    receipts = tuple(images.get("roles", []))
    if {item.get("role") for item in receipts} != set(ROLES):
        raise CloudManifestError("images.json must contain one receipt per production role")
    for receipt in receipts:
        validate_production_image_receipt(receipt)
    return receipts


def _immutable_image_receipt_refs(package: Path, images_path: Path, image_receipts: tuple[dict[str, Any], ...]) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = []
    for receipt in image_receipts:
        receipt_path = images_path.parent / f"{receipt['role']}.receipt.json"
        if _sha(receipt_path) != _sha_bytes(canonical_bytes(receipt)):
            raise CloudManifestError(f"immutable image receipt does not match images.json: {receipt['role']}")
        refs.append(_ref(package, receipt_path, role=f"{receipt['role']}_image"))
    return refs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--max-observations", type=int, default=180)
    args = parser.parse_args(argv)
    _validate_action_id(args.action_id)
    if args.max_observations < 1 or args.max_observations > 180:
        parser.error("--max-observations must be between 1 and 180")
    package = args.package_dir.resolve()
    e2e_root = _action_evidence_root(package, args.action_id)
    provider_binding_path = package / "inputs/provider-binding.json"
    provider_binding = validate_production_provider_binding(_load(provider_binding_path))
    input_lock = package / "inputs/input-lock.json"
    input_lock_sha256 = _sha(input_lock)
    image_receipts = _image_receipts(args.images.resolve())
    image_refs = {receipt["role"]: receipt["image_ref"] for receipt in image_receipts}
    image_digests = {receipt["role"]: receipt["image_digest"] for receipt in image_receipts}
    e2e_root.mkdir(parents=True, exist_ok=False)
    harness = {
        "record_kind": "cloud_production_e2e_harness",
        "schema_version": "0.1.0",
        "action_id": args.action_id,
        "input_lock_sha256": input_lock_sha256,
        "execution_class": "non_scientific_bounded_surface",
        "authority": "none",
        "fixture_mode": "FIXTURE-NONSCI",
        "request": {"request_id": f"{args.action_id}-request", "prompt": "NON-SCIENTIFIC ROLE HANDSHAKE; NO MODEL OR BENCHMARK", "max_tokens": 4, "temperature": 0.0},
    }
    harness_raw = canonical_bytes(harness)
    harness_sha256 = _sha_bytes(harness_raw)
    _write_once(e2e_root / "harness.json", harness)
    preflight = collect_preflight(region="us-east-1", action_id=args.action_id)
    if preflight["fresh_resource_absence_before"] is not True:
        raise CloudManifestError("bounded surface action tag already has active AWS resources")
    preflight.update({"action_id": args.action_id, "input_lock_sha256": input_lock_sha256, "provider_binding_sha256": _sha(provider_binding_path)})
    _write_once(e2e_root / "preflight.json", preflight)
    config = AwsSurfaceConfig(
        action_id=args.action_id,
        region="us-east-1",
        input_lock_sha256=input_lock_sha256,
        harness_sha256=harness_sha256,
        harness_bytes_b64=base64.b64encode(harness_raw).decode("ascii"),
        image_refs=cast(Mapping[str, str], image_refs),
        image_digests=cast(Mapping[str, str], image_digests),
        provider_binding_sha256=_sha(provider_binding_path),
        source_commit=args.source_commit,
        evidence_dir=e2e_root,
    )
    provider = AwsSurfaceProvider(config)
    state_path = e2e_root / "controller-state.json"
    binding = {"action_id": args.action_id, "run_spec_sha256": "0" * 64, "provider_binding_sha256": config.provider_binding_sha256, "evidence_class": "production_surface_non_scientific", "fixture_mode": "FIXTURE-NONSCI", "authority": "none"}
    run_binding_digest = hashlib.sha256(canonical_bytes(binding)).hexdigest()
    state = ProductionStateStore(state_path, action_id=args.action_id, run_spec_sha256=run_binding_digest, binding={**binding, "run_spec_sha256": run_binding_digest})
    allocation = {"worker-0": ("surface-controller",), "worker-1": ("surface-worker",)}
    orchestrator = ProductionOrchestrator(state, action_id=args.action_id, run_spec_sha256=run_binding_digest, allocation=allocation)
    teardown_record: Mapping[str, Any] | None = None
    try:
        submitted = orchestrator.submit(provider)
        parent_id = submitted.parent_job_id
        restarted_provider = AwsSurfaceProvider(config)
        restarted = ProductionOrchestrator(ProductionStateStore(state_path, action_id=args.action_id, run_spec_sha256=run_binding_digest, binding={**binding, "run_spec_sha256": run_binding_digest}), action_id=args.action_id, run_spec_sha256=run_binding_digest, allocation=allocation)
        if restarted.submit(restarted_provider).parent_job_id != parent_id:
            raise CloudManifestError("provider restart did not reconcile the original submission")
        try:
            restarted.observe(_FailOnceObservation(restarted_provider))  # type: ignore[arg-type]
        except RuntimeError as exc:
            if str(exc) != "injected_non_mutating_observation_error":
                raise
        if restarted.store.snapshot().phase != "observation_error":
            raise CloudManifestError("observation-error preservation was not recorded")
        terminal = False
        for _ in range(args.max_observations):
            snapshot = restarted.observe(restarted_provider)
            terminal = snapshot.phase == "workload_terminal"
            if terminal:
                break
            time.sleep(5)
        if not terminal or restarted_provider.last_status is None:
            raise CloudManifestError("bounded surface E2E did not reach a terminal provider status")
        status = dict(restarted_provider.last_status)
        if status.get("state") != "SUCCEEDED":
            raise CloudManifestError(f"bounded surface provider status was {status.get('state')!r}")
        receipts = status.get("receipts")
        if not isinstance(receipts, Mapping):
            raise CloudManifestError("provider status lacks role receipts")
        failure_receipts = status.get("failure_receipts")
        if not isinstance(failure_receipts, Mapping) or any(
            not isinstance(failure_receipts.get(role), Mapping)
            or cast(Mapping[str, Any], failure_receipts[role]).get("record", {}).get("reason") != "harness_sha256_mismatch"
            for role in ROLES
        ):
            raise CloudManifestError("provider status lacks fail-closed wrong-hash receipts")
        receipt_paths: dict[str, Path] = {}
        for role in ROLES:
            item = receipts.get(role)
            if not isinstance(item, Mapping) or not isinstance(item.get("record"), Mapping):
                raise CloudManifestError(f"provider status lacks {role} receipt")
            record = validate_production_role_receipt(cast(Mapping[str, Any], item["record"]))
            expected = {"controller": "DISPATCHED", "model-server": "RESPONDED", "benchmark-worker": "COMPLETE"}[role]
            if record["state"] != expected or record["harness_sha256"] != harness_sha256:
                raise CloudManifestError(f"{role} receipt does not bind the bounded harness")
            receipt_path = e2e_root / f"{role}.json"
            _write_once(receipt_path, record)
            receipt_paths[role] = receipt_path
        restarted_provider.close_attempt()
        restarted.teardown(restarted_provider)
        teardown_record = restarted_provider.last_teardown
        if teardown_record is None or teardown_record.get("fresh_provider_absence") is not True:
            raise CloudManifestError("provider teardown did not prove fresh absence")
        teardown_sha256 = _write_once(e2e_root / "teardown.json", teardown_record)
        runtime_path = Path(__file__).resolve().parents[2] / "src/pneuma_lab/cloud/production_runtime.py"
        surface = build_surface_record(input_lock_sha256=input_lock_sha256, source_commit=args.source_commit, runtime_sha256=_sha(runtime_path), image_digests=cast(dict[str, str], image_digests), receipt_paths=receipt_paths, provider_binding_sha256=config.provider_binding_sha256, e2e_class="non_scientific_bounded_surface", deployment_id=provider_binding["bounded_surface_deployment"]["deployment_id"], teardown_ref=teardown_sha256)
        surface_sha256 = _write_once(e2e_root / "surface.json", surface)
        require_production_execution_surface(surface)
        image_receipt_refs = _immutable_image_receipt_refs(package, args.images.resolve(), image_receipts)
        e2e_receipt = {
            "record_kind": "cloud_production_surface_e2e_receipt",
            "schema_version": "0.2.0",
            "evidence_class": "production_surface_non_scientific",
            "fixture_mode": "FIXTURE-NONSCI",
            "authority": "none",
            "action_id": args.action_id,
            "provider": "aws",
            "region": "us-east-1",
            "provider_binding_sha256": config.provider_binding_sha256,
            "image_receipt_refs": image_receipt_refs,
            "surface_sha256": surface_sha256,
            "controller": {"submitted_once": True, "restart_reconciled": True, "observation_error_preserved_submission": True, "terminal_observed": True, "explicit_teardown_phase": True},
            "admission": {"instance_type": "m7i.large", "ami_id": "ami-0b416d150bdde5ea2", "ami_owner_id": "591542846629", "availability_zone": "us-east-1a", "capacity_type": "on-demand", "max_duration_seconds": 900, "max_attempts": 1, "public_ipv4": False, "global_ipv6": False, "general_internet_egress": False, "custom_ssm_document": True, "ssm_document_version": "1", "model_download": False, "benchmark_execution": False, "official_study": False, "canonical_p0_grid": False, "roster_ceremony": False, "unblind": False, "analysis": False},
            "cost": {"projected_max_usd": float(preflight["cost"]["projected_max_usd"]), "actual_billing": {"status": "delayed_not_available", "usd": None}, "currency": "USD", "price_source_sha256": preflight["price"]["price_response_sha256"]},
            "teardown": {"status": "COMPLETE", "terminated": True, "network_deleted": True, "iam_deleted": True, "custom_ssm_document_deleted": True, "fresh_provider_absence": True, "retained_ecr_images": True, "provider_response_hashes_sha256": _sha(teardown_record["provider_response_hashes"])},
        }
        validate_production_surface_e2e_receipt(e2e_receipt)
        _write_once(e2e_root / "receipt.json", e2e_receipt)
        _write_once(e2e_root / "status.json", {"status": "COMPLETE", "evidence_class": "production_surface_non_scientific", "fixture_mode": "FIXTURE-NONSCI", "authority": "none", "surface_sha256": surface_sha256, "teardown_sha256": teardown_sha256, "projected_max_usd": preflight["cost"]["projected_max_usd"], "actual_billing": {"status": "delayed_not_available", "usd": None}, "parent_job_id": parent_id, "scientific_workload": False})
        print(json.dumps({"status": "COMPLETE", "action_id": args.action_id, "surface_sha256": surface_sha256, "projected_max_usd": preflight["cost"]["projected_max_usd"], "actual_billing": "delayed_not_available", "parent_job_id": parent_id}, sort_keys=True))
        return 0
    finally:
        if teardown_record is None:
            provider.close_attempt()
            provider.teardown(provider.submission)


if __name__ == "__main__":
    raise SystemExit(main())

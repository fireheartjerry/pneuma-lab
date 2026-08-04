"""Run the bounded AWS production-role surface E2E and tear it down.

This action is infrastructure admission evidence only.  Its harness is
explicitly non-scientific and the provider user-data path has no model,
benchmark, roster, assignment, or analysis inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Mapping, cast

from pneuma_lab.cloud.aws_surface_provider import AwsSurfaceConfig, AwsSurfaceProvider, collect_preflight
from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.manifests import (
    validate_production_image_receipt,
    validate_production_surface_e2e_receipt,
    validate_production_role_receipt,
    validate_production_provider_binding,
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


def _write(path: Path, value: object) -> str:
    raw = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return _sha_bytes(raw)


def _ref(package: Path, path: Path, *, role: str) -> dict[str, object]:
    raw = path.read_bytes()
    return {"role": role, "relative_path": path.resolve().relative_to(package.resolve()).as_posix(), "sha256": _sha_bytes(raw), "byte_count": len(raw), "media_type": "application/json"}


class _FailOnceObservation:
    def __init__(self, provider: AwsSurfaceProvider) -> None:
        self.provider = provider
        self.injected = False

    def observe(self, submission):
        if not self.injected:
            self.injected = True
            raise RuntimeError("injected_non_mutating_observation_error")
        return self.provider.observe(submission)


def _image_receipts(package: Path, images_path: Path) -> tuple[dict[str, Any], ...]:
    images = _load(images_path)
    receipts = tuple(images.get("roles", []))
    if {item.get("role") for item in receipts} != set(ROLES):
        raise CloudManifestError("images.json must contain one receipt per production role")
    for receipt in receipts:
        validate_production_image_receipt(receipt)
    return receipts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--max-observations", type=int, default=180)
    args = parser.parse_args(argv)
    package = args.package_dir.resolve()
    provider_binding_path = package / "inputs/provider-binding.json"
    provider_binding = validate_production_provider_binding(_load(provider_binding_path))
    input_lock = package / "inputs/input-lock.json"
    input_lock_sha256 = _sha(input_lock)
    image_receipts = _image_receipts(package, args.images.resolve())
    image_refs = {receipt["role"]: receipt["image_ref"] for receipt in image_receipts}
    image_digests = {receipt["role"]: receipt["image_digest"] for receipt in image_receipts}
    harness = {
        "record_kind": "cloud_production_e2e_harness",
        "schema_version": "0.1.0",
        "action_id": args.action_id,
        "input_lock_sha256": input_lock_sha256,
        "execution_class": "non_scientific_bounded_surface",
        "request": {"request_id": f"{args.action_id}-request", "prompt": "NON-SCIENTIFIC ROLE HANDSHAKE; NO MODEL OR BENCHMARK", "max_tokens": 4, "temperature": 0.0},
    }
    harness_raw = canonical_bytes(harness)
    harness_sha256 = _sha_bytes(harness_raw)
    harness_path = package / "evidence/production-surface-e2e/harness.json"
    harness_path.parent.mkdir(parents=True, exist_ok=True)
    harness_path.write_bytes(harness_raw)
    preflight = collect_preflight(region="us-east-1", action_id=args.action_id)
    if preflight["fresh_resource_absence_before"] is not True:
        raise CloudManifestError("bounded surface action tag already has active AWS resources")
    preflight["action_id"] = args.action_id
    preflight["input_lock_sha256"] = input_lock_sha256
    preflight["provider_binding_sha256"] = _sha(provider_binding_path)
    preflight_path = package / "evidence/production-surface-e2e/preflight.json"
    _write(preflight_path, preflight)
    config = AwsSurfaceConfig(
        action_id=args.action_id,
        region="us-east-1",
        input_lock_sha256=input_lock_sha256,
        harness_sha256=harness_sha256,
        harness_bytes_b64=__import__("base64").b64encode(harness_raw).decode("ascii"),
        image_refs=cast(Mapping[str, str], image_refs),
        image_digests=cast(Mapping[str, str], image_digests),
        provider_binding_sha256=_sha(provider_binding_path),
        source_commit=args.source_commit,
    )
    provider = AwsSurfaceProvider(config)
    state_path = package / "evidence/production-surface-e2e/controller-state.json"
    binding = {"action_id": args.action_id, "run_spec_sha256": "0" * 64, "provider_binding_sha256": config.provider_binding_sha256, "evidence_class": "production_surface_non_scientific"}
    # The bounded fixture has no executable run-spec; the controller still
    # binds a stable content address for its own non-scientific action.
    run_binding_digest = hashlib.sha256(canonical_bytes(binding)).hexdigest()
    state = ProductionStateStore(state_path, action_id=args.action_id, run_spec_sha256=run_binding_digest, binding={"action_id": args.action_id, "run_spec_sha256": run_binding_digest, "provider_binding_sha256": config.provider_binding_sha256, "evidence_class": "production_surface_non_scientific"})
    allocation = {"worker-0": ("surface-controller",), "worker-1": ("surface-worker",)}
    orchestrator = ProductionOrchestrator(state, action_id=args.action_id, run_spec_sha256=run_binding_digest, allocation=allocation)
    teardown_record: Mapping[str, Any] | None = None
    try:
        submitted = orchestrator.submit(provider)
        parent_id = submitted.parent_job_id
        restarted_provider = AwsSurfaceProvider(config)
        restarted = ProductionOrchestrator(ProductionStateStore(state_path, action_id=args.action_id, run_spec_sha256=run_binding_digest, binding={"action_id": args.action_id, "run_spec_sha256": run_binding_digest, "provider_binding_sha256": config.provider_binding_sha256, "evidence_class": "production_surface_non_scientific"}), action_id=args.action_id, run_spec_sha256=run_binding_digest, allocation=allocation)
        if restarted.submit(restarted_provider).parent_job_id != parent_id:
            raise CloudManifestError("provider restart did not reconcile the original submission")
        errored = False
        try:
            restarted.observe(_FailOnceObservation(restarted_provider))  # type: ignore[arg-type]
        except RuntimeError as exc:
            if str(exc) != "injected_non_mutating_observation_error":
                raise
            errored = True
        if not errored or restarted.store.snapshot().phase != "observation_error":
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
            record = dict(cast(Mapping[str, Any], item["record"]))
            validated = validate_production_role_receipt(record)
            expected = {"controller": "DISPATCHED", "model-server": "RESPONDED", "benchmark-worker": "COMPLETE"}[role]
            if validated["state"] != expected or validated["harness_sha256"] != harness_sha256:
                raise CloudManifestError(f"{role} receipt does not bind the bounded harness")
            receipt_path = package / f"evidence/production-surface-e2e/{role}.json"
            _write(receipt_path, validated)
            receipt_paths[role] = receipt_path
        restarted.teardown(restarted_provider)
        teardown_record = restarted_provider.last_teardown
        if teardown_record is None or teardown_record.get("fresh_provider_absence") is not True:
            raise CloudManifestError("provider teardown did not prove fresh absence")
        teardown_path = package / "evidence/production-surface-e2e/teardown.json"
        teardown_sha256 = _write(teardown_path, teardown_record)
        runtime_path = Path(__file__).resolve().parents[2] / "src/pneuma_lab/cloud/production_runtime.py"
        surface = build_surface_record(
            input_lock_sha256=input_lock_sha256,
            source_commit=args.source_commit,
            runtime_sha256=_sha(runtime_path),
            image_digests=cast(dict[str, str], image_digests),
            receipt_paths=receipt_paths,
            provider_binding_sha256=config.provider_binding_sha256,
            e2e_class="non_scientific_bounded_surface",
            deployment_id=provider_binding["bounded_surface_deployment"]["deployment_id"],
            teardown_ref=teardown_sha256,
        )
        surface_path = package / "evidence/production-surface-e2e/surface.json"
        surface_sha256 = _write(surface_path, surface)
        require_production_execution_surface(surface)
        for receipt in image_receipts:
            receipt["surface_e2e_status"] = "complete"
            validate_production_image_receipt(receipt)
            _write(package / "evidence/images" / f"{receipt['role']}.receipt.json", receipt)
        _write(args.images.resolve(), {"record_kind": "cloud_production_image_set", "schema_version": "0.1.0", "evidence_class": "production_surface_non_scientific", "source_commit": args.source_commit, "roles": list(image_receipts)})
        e2e_receipt = {
            "record_kind": "cloud_production_surface_e2e_receipt",
            "schema_version": "0.1.0",
            "evidence_class": "production_surface_non_scientific",
            "action_id": args.action_id,
            "provider": "aws",
            "region": "us-east-1",
            "provider_binding_sha256": config.provider_binding_sha256,
            "image_receipt_refs": [_ref(package, package / "evidence/images" / f"{role}.receipt.json", role=f"{role}_image") for role in ROLES],
            "surface_sha256": surface_sha256,
            "controller": {"submitted_once": True, "restart_reconciled": True, "observation_error_preserved_submission": True, "terminal_observed": True, "explicit_teardown_phase": True},
            "admission": {"instance_type": "m7i.large", "capacity_type": "on-demand", "max_duration_seconds": 900, "max_attempts": 1, "model_download": False, "benchmark_execution": False, "official_study": False, "canonical_p0_grid": False, "roster_ceremony": False, "unblind": False, "analysis": False},
            "cost": {"projected_usd": float(preflight["cost"]["projected_usd"]), "actual_usd_upper_bound": float(preflight["cost"]["ceiling_usd"]), "currency": "USD", "price_source_sha256": preflight["price"]["price_response_sha256"]},
            "teardown": {"status": "COMPLETE", "terminated": True, "network_deleted": True, "iam_deleted": True, "fresh_provider_absence": True, "retained_ecr_images": True},
        }
        validate_production_surface_e2e_receipt(e2e_receipt)
        _write(package / "evidence/production-surface-e2e/receipt.json", e2e_receipt)
        _write(package / "evidence/production-surface-e2e/status.json", {"status": "COMPLETE", "surface_sha256": surface_sha256, "teardown_sha256": teardown_sha256, "projected_usd": preflight["cost"]["projected_usd"], "actual_usd_upper_bound": preflight["cost"]["ceiling_usd"], "parent_job_id": parent_id, "scientific_workload": False})
        print(json.dumps({"status": "COMPLETE", "surface_sha256": surface_sha256, "projected_usd": preflight["cost"]["projected_usd"], "actual_usd_upper_bound": preflight["cost"]["ceiling_usd"], "parent_job_id": parent_id}, sort_keys=True))
        return 0
    finally:
        if teardown_record is None:
            try:
                provider.teardown(provider.submission)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())

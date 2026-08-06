from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.manifests import (
    validate_official_assignment_pending,
    validate_official_input_package,
    validate_official_roster_candidate,
)
from pneuma_lab.cloud.production_run import ProductionRunSpec, canonical_bytes
from scripts.research.build_official_input_package import build_inputs, build_run_spec


def _surface(input_lock_sha256: str, source_commit: str) -> dict[str, object]:
    roles = []
    for role in ("controller", "model-server", "benchmark-worker"):
        roles.append(
            {
                "role": role,
                "image_digest": "sha256:" + ("1" if role == "controller" else "2" if role == "model-server" else "3") * 64,
                "entrypoint": ["python3", "-m", "pneuma_lab.cloud.production_runtime", role],
                "source_sha256": "4" * 64,
                "e2e_receipt_sha256": "5" * 64,
                "gates": {
                    "clean_start": True,
                    "expected_terminal_state": True,
                    "failure_receipt": True,
                    "no_class_a_secret": True,
                    "no_controller_credentials": True,
                    "imds_blocked": True,
                    "docker_socket_absent": True,
                },
            }
        )
    return {
        "record_kind": "cloud_production_execution_surface",
        "schema_version": "0.1.0",
        "input_lock_sha256": input_lock_sha256,
        "source_commit": source_commit,
        "provider_binding_sha256": "6" * 64,
        "e2e_class": "non_scientific_bounded_surface",
        "deployment_id": "aws-ec2-ssm-cpu-production-role-surface-v1",
        "roles": roles,
    }


def test_real_candidate_inputs_are_digest_bound_and_non_authorizing(tmp_path: Path) -> None:
    inputs = build_inputs(tmp_path, frozen_timestamp="2026-08-04T12:00:00Z")
    registry = json.loads(inputs["task_manifest"].read_text(encoding="utf-8"))
    assert len(registry["tasks"]) == 240
    assert sum(task["benchmark"] == "SWE" for task in registry["tasks"]) == 120
    assert sum(task["benchmark"] == "TAU" for task in registry["tasks"]) == 120
    roster = json.loads(inputs["roster"].read_text(encoding="utf-8"))
    assert validate_official_roster_candidate(roster)["ceremony_status"] == "not_performed"
    assignment = json.loads(inputs["assignment"].read_text(encoding="utf-8"))
    assert validate_official_assignment_pending(assignment)["sealed_assignment_ref"] is None

    surface_path = tmp_path / "surface.json"
    surface = _surface(inputs["input_lock"].read_bytes().hex()[:64], "a" * 40)
    surface_path.write_bytes(canonical_bytes(surface))
    # The test surface uses the real input-lock digest and a separate fake
    # provider digest only to exercise the run-spec binding failure surface.
    surface["input_lock_sha256"] = __import__("hashlib").sha256(inputs["input_lock"].read_bytes()).hexdigest()
    surface_path.write_bytes(canonical_bytes(surface))
    spec_path = build_run_spec(
        tmp_path,
        inputs,
        surface=surface_path,
        source_commit="a" * 40,
        images={role: "sha256:" + digit * 64 for role, digit in (("controller", "1"), ("model-server", "2"), ("benchmark-worker", "3"))},
    )
    spec = ProductionRunSpec.load(spec_path)
    assert spec.run_mode == "official_candidate"
    assert spec.value["official_authorization_ref"] is None
    package = json.loads((tmp_path / "input-package.json").read_text(encoding="utf-8"))
    assert validate_official_input_package(package)["authorizing"] is False

    mutated = dict(roster)
    mutated["synthetic_authority"] = True
    with pytest.raises(CloudManifestError):
        validate_official_roster_candidate(mutated)


def test_candidate_execution_is_fail_closed(tmp_path: Path) -> None:
    inputs = build_inputs(tmp_path, frozen_timestamp="2026-08-04T12:00:00Z")
    surface_path = tmp_path / "surface.json"
    surface = _surface(__import__("hashlib").sha256(inputs["input_lock"].read_bytes()).hexdigest(), "a" * 40)
    surface_path.write_bytes(canonical_bytes(surface))
    spec_path = build_run_spec(
        tmp_path,
        inputs,
        surface=surface_path,
        source_commit="a" * 40,
        images={role: "sha256:" + digit * 64 for role, digit in (("controller", "1"), ("model-server", "2"), ("benchmark-worker", "3"))},
    )
    from pneuma_lab.cloud import production_runtime

    assert production_runtime.main(["controller", "--protocol", "production", "--run-spec", str(spec_path), "--run-spec-sha256", __import__("hashlib").sha256(spec_path.read_bytes()).hexdigest(), "--run-root", str(tmp_path)]) == 2

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.manifests import validate_production_worker_evidence
from pneuma_lab.cloud.production_evidence import (
    ProductionWorkerExecutor,
    validate_worker_evidence,
    write_worker_result,
)
from pneuma_lab.cloud.production_run import (
    ProductionRunSpec,
    canonical_bytes,
    official_authorization_subject_digest,
)


def _binding(root: Path, relative: str, value: object, role: str) -> dict[str, object]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(value)
    path.write_bytes(raw)
    return {
        "role": role,
        "relative_path": relative,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "media_type": "application/json",
    }


def _spec(root: Path, *, run_mode: str = "local_mock") -> ProductionRunSpec:
    task_manifest = {
        "record_kind": "resampling_task_registry_v1",
        "schema_version": "1",
        "tasks": [
            {
                "task_id": "swe-001",
                "benchmark": "SWE",
                "stratum": "swe-stratum",
                "lineage": "swe-lineage",
                "groups": [
                    {"kind": "language", "value": "python"},
                    {"kind": "domain", "value": "software"},
                    {"kind": "issue_family", "value": "test"},
                ],
            },
            {
                "task_id": "tau-001",
                "benchmark": "TAU",
                "stratum": "tau-stratum",
                "lineage": "tau-lineage",
                "groups": [
                    {"kind": "language", "value": "python"},
                    {"kind": "domain", "value": "agents"},
                    {"kind": "issue_family", "value": "dialogue"},
                ],
            },
            {
                "task_id": "swe-002",
                "benchmark": "SWE",
                "stratum": "swe-stratum-2",
                "lineage": "swe-lineage-2",
                "groups": [
                    {"kind": "language", "value": "python"},
                    {"kind": "domain", "value": "software"},
                    {"kind": "issue_family", "value": "bug"},
                ],
            },
            {
                "task_id": "tau-002",
                "benchmark": "TAU",
                "stratum": "tau-stratum-2",
                "lineage": "tau-lineage-2",
                "groups": [
                    {"kind": "language", "value": "python"},
                    {"kind": "domain", "value": "agents"},
                    {"kind": "issue_family", "value": "tool"},
                ],
            },
        ],
    }
    bindings = {
        "execution_surface_ref": _binding(
            root, "inputs/execution.json", {"surface": "v1"}, "execution_surface"
        ),
        "input_lock_ref": _binding(
            root, "inputs/input-lock.json", {"lock": "v1"}, "input_lock"
        ),
        "task_manifest_ref": _binding(
            root, "inputs/task-registry.json", task_manifest, "task_manifest"
        ),
        "roster_ref": _binding(
            root, "inputs/roster.json", {"roster": "sealed"}, "roster"
        ),
        "assignment_ref": _binding(
            root, "inputs/assignment.json", {"assignment": "sealed"}, "assignment"
        ),
        "analysis_graph_ref": _binding(
            root, "inputs/analysis.json", {"graph": "sealed"}, "analysis_graph"
        ),
    }
    task_digest = bindings["task_manifest_ref"]["sha256"]
    task_size = bindings["task_manifest_ref"]["byte_count"]
    value: dict[str, object] = {
        "record_kind": "cloud_production_run_spec",
        "schema_version": "0.1.0",
        "action_id": "official-study-test-001",
        "study_id": "p0-test",
        "run_mode": run_mode,
        "code_commit": "a" * 40,
        "image_bindings": [
            {"role": "controller", "image_digest": "sha256:" + "1" * 64},
            {"role": "model-server", "image_digest": "sha256:" + "2" * 64},
            {"role": "benchmark-worker", "image_digest": "sha256:" + "3" * 64},
        ],
        **bindings,
        "model": {
            "repository": "Qwen/Qwen3.6-35B-A3B-FP8",
            "revision": "95a723d08a9490559dae23d0cff1d9466213d989",
            "tokenizer_revision": "95a723d08a9490559dae23d0cff1d9466213d989",
            "serving_engine": "vllm",
            "serving_engine_version": "0.19.0",
            "sampling": {
                "temperature": 0.0,
                "top_p": 1.0,
                "top_k": 0,
                "reasoning_parser": "qwen3",
                "tool_call_parser": "qwen3_coder",
            },
        },
        "benchmarks": [
            {
                "benchmark_id": "swe_multilang",
                "repository": "microsoft/SWE-bench-Live",
                "revision": "70ec57e852e3f2d195790fe71f553e272c691833",
                "dataset_repository": "SWE-bench-Live/MultiLang",
                "dataset_revision": "608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b",
                "task_manifest_sha256": task_digest,
                "task_manifest_size_bytes": task_size,
            },
            {
                "benchmark_id": "tau2",
                "repository": "sierra-research/tau2-bench",
                "revision": "fc0055dc4e0a316c3f83133267fbd6faaa770992",
                "dataset_repository": "sierra-research/tau2-bench",
                "dataset_revision": "fc0055dc4e0a316c3f83133267fbd6faaa770992",
                "task_manifest_sha256": task_digest,
                "task_manifest_size_bytes": task_size,
            },
        ],
        "rng": {
            "contract_id": "official-study-rng-v1",
            "root_u64": 7,
            "draw_domains": ["model", "benchmark"],
            "seeds": {"study": "4" * 64},
        },
        "worker_topology": {
            "worker_ids": ["worker-0", "worker-1"],
            "instance_type": "g6e.2xlarge",
            "vcpus_per_worker": 8,
            "gpus_per_worker": 1,
            "allocation_contract_id": "canonical-round-robin-two-worker-v1",
        },
        "budget": {
            "max_usd": 100.0,
            "max_duration_seconds": 3600,
            "max_attempts": 1,
            "spot_only": True,
        },
        "output": {
            "root": "outputs/official-study-test-001",
            "worker_evidence_template": "outputs/official-study-test-001/{worker_id}.evidence.json",
            "controller_state_path": "outputs/official-study-test-001/controller.json",
        },
        "analysis_graph_ref": bindings["analysis_graph_ref"],
        "power_report_ref": None,
        "power_tier": None,
        "official_authorization_ref": None,
        "official_key_registry_ref": None,
        "model_server": {
            "endpoint": "http://127.0.0.1:8000",
            "launch_argv": ["local-mock-server"],
            "readiness_timeout_seconds": 30,
            "request_timeout_seconds": 30,
        },
        "benchmark_adapter": {
            "adapter_id": "local-mock-benchmark-v1",
            "entrypoint": ["local-mock-benchmark"],
            "timeout_seconds": 30,
        },
    }
    return ProductionRunSpec.from_mapping(value)


def test_local_mock_uses_the_production_control_flow_and_is_not_science(
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    result = ProductionWorkerExecutor(spec, run_root=tmp_path).execute("worker-0")
    assert result.evidence["evidence_class"] == "local_mock_non_scientific"
    assert result.evidence["state"] == "SUCCEEDED"
    validate_worker_evidence(
        result.evidence, spec, run_root=tmp_path, raw_artifact=result.raw_artifact
    )
    evidence_path = tmp_path / "outputs/worker-0.evidence.json"
    raw_path = tmp_path / "outputs/worker-0.raw.json"
    evidence = write_worker_result(
        result,
        evidence_path=evidence_path,
        raw_path=raw_path,
        run_root=tmp_path,
    )
    validate_production_worker_evidence(evidence)
    validate_worker_evidence(evidence, spec, run_root=tmp_path)
    assert (
        json.loads(raw_path.read_text(encoding="utf-8"))["record_kind"]
        == "cloud_production_raw_worker_output"
    )


def test_official_semantics_reject_fixture_adapter(tmp_path: Path) -> None:
    value = dict(_spec(tmp_path).value)
    value["run_mode"] = "official"
    value["official_authorization_ref"] = {
        "role": "official_authorization",
        "relative_path": "inputs/authorization.json",
        "sha256": "5" * 64,
        "byte_count": 1,
        "media_type": "application/json",
    }
    value["official_key_registry_ref"] = {
        "role": "approver_key_registry",
        "relative_path": "inputs/keys.json",
        "sha256": "6" * 64,
        "byte_count": 1,
        "media_type": "application/json",
    }
    value["power_report_ref"] = {
        "role": "power_report",
        "relative_path": "inputs/power-final.json",
        "sha256": "7" * 64,
        "byte_count": 1,
        "media_type": "application/json",
    }
    value["power_tier"] = 120
    for field, role, relative, digest in (
        ("prelaunch_root_ref", "prelaunch_root", "inputs/prelaunch.json", "8"),
        (
            "execution_seed_openings_ref",
            "execution_seed_openings",
            "inputs/execution-seeds.json",
            "9",
        ),
        (
            "execution_assets_ref",
            "swe_execution_assets",
            "inputs/swe-assets.json",
            "a",
        ),
    ):
        value[field] = {
            "role": role,
            "relative_path": relative,
            "sha256": digest * 64,
            "byte_count": 1,
            "media_type": "application/json",
        }
    value["model_server"] = {
        **value["model_server"],
        "launch_argv": [
            "vllm",
            "vllm.entrypoints.openai.api_server",
            "--model",
            "Qwen/Qwen3.6-35B-A3B-FP8",
            "--revision",
            "95a723d08a9490559dae23d0cff1d9466213d989",
        ],
        "simulator_launch_argv": [
            "vllm",
            "vllm.entrypoints.openai.api_server",
            "--model",
            "Qwen/Qwen3.5-9B",
        ],
        "simulator_revision": "c202236235762e1c871ad0ccb60c8ee5ba337b9a",
    }
    with pytest.raises(CloudManifestError, match="mock or fixture"):
        ProductionRunSpec.from_mapping(value)


def test_official_authorization_subject_breaks_only_signature_reference_cycle(
    tmp_path: Path,
) -> None:
    value = dict(_spec(tmp_path).value)
    first = official_authorization_subject_digest(value)
    value["official_authorization_ref"] = {
        "role": "official_authorization",
        "relative_path": "authority/first.json",
        "sha256": "5" * 64,
        "byte_count": 1,
        "media_type": "application/json",
    }
    value["official_key_registry_ref"] = {
        "role": "key_registry",
        "relative_path": "authority/keys.json",
        "sha256": "6" * 64,
        "byte_count": 1,
        "media_type": "application/json",
    }
    assert official_authorization_subject_digest(value) == first
    value["budget"] = {**value["budget"], "max_usd": 101.0}
    assert official_authorization_subject_digest(value) != first


def test_execution_surface_must_match_the_run_code_and_images(tmp_path: Path) -> None:
    base = _spec(tmp_path)
    surface = {
        "record_kind": "cloud_production_execution_surface",
        "schema_version": "0.1.0",
        "input_lock_sha256": base.file_binding("input_lock_ref").sha256,
        "source_commit": base.value["code_commit"],
        "roles": [
            {
                "role": "controller",
                "image_digest": base.image_bindings["controller"],
                "entrypoint": [
                    "python3",
                    "-m",
                    "pneuma_lab.cloud.production_runtime",
                    "controller",
                ],
                "source_sha256": "4" * 64,
                "e2e_receipt_sha256": "5" * 64,
                "gates": {
                    "clean_start": True,
                    "expected_terminal_state": True,
                    "failure_receipt": True,
                    "no_class_a_secret": True,
                    "no_controller_credentials": False,
                    "imds_blocked": True,
                    "docker_socket_absent": False,
                },
            },
            *[
                {
                    "role": role,
                    "image_digest": base.image_bindings[role],
                    "entrypoint": [
                        "python3",
                        "-m",
                        "pneuma_lab.cloud.production_runtime",
                        role,
                    ],
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
                for role in ("model-server", "benchmark-worker")
            ],
        ],
    }
    surface_ref = _binding(
        tmp_path, "inputs/surface.json", surface, "execution_surface"
    )
    value = dict(base.value)
    value["execution_surface_ref"] = surface_ref
    bound = ProductionRunSpec.from_mapping(value)
    assert (
        bound.verify_official_execution_surface(run_root=tmp_path)["source_commit"]
        == "a" * 40
    )

    changed = dict(value)
    changed["image_bindings"] = [
        {**binding, "image_digest": "sha256:" + "9" * 64}
        if binding["role"] == "controller"
        else binding
        for binding in value["image_bindings"]
    ]
    changed_spec = ProductionRunSpec.from_mapping(changed)
    with pytest.raises(CloudManifestError, match="image bindings differ"):
        changed_spec.verify_official_execution_surface(run_root=tmp_path)

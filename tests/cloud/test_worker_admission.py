from __future__ import annotations

import json
from copy import deepcopy

import pytest

from pneuma_lab.cloud.admission_measurement import OUTPUT_PARITY_FIXTURE_IDS, TOOL_CALL_FIXTURES
from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.pilot import protocol_digest
from pneuma_lab.cloud.worker_admission import (
    compile_dual_worker_admissions,
    compile_worker_admission,
    measurement_evidence_digest,
)


def protocol() -> dict:
    return {
        "rungs": ["l40s-tp1-32768", "l40s-tp1-65536"],
        "max_cost_usd": 25.0,
        "max_runtime_minutes": 60,
        "max_retries": 2,
        "max_samples": 20,
        "worker_count": 2,
        "worker_vcpus": 8,
        "worker_gpu_count": 1,
        "total_spot_vcpus": 16,
        "partitioning": "canonical_round_robin",
        "interruption_policy": "freeze_and_resume",
        "minimum_p10_output_tokens_per_second": 8.0,
        "throughput_samples_per_rung": 10,
        "output_tokens_per_sample": 128,
        "warmup_samples_per_rung": 1,
        "p10_method": "nearest_rank",
        "bound_hashes": {
            name: "a" * 64
            for name in ("architecture", "authorization", "image", "input_lock", "code")
        },
    }


def measurement(*, worker_index: int = 0, instance_id: str = "i-0123456789abcdef0") -> dict:
    frozen = protocol()
    rung = {
        "peak_allocated_bytes": int(43.5 * 1024**3),
        "throughput": {
            "p10_method": "nearest_rank",
            "warmup_samples": 1,
            "output_tokens_per_sample": 128,
            "samples": [
                {
                    "index": index,
                    "elapsed_seconds": 16.0,
                    "generated_tokens": 128,
                    "output_token_ids_sha256": f"{index:064x}",
                }
                for index in range(10)
            ],
        },
        "tool_calls": [
            {
                "fixture_id": fixture_id,
                "raw_response_text": json.dumps(
                    {"name": name, "arguments": arguments}, sort_keys=True
                ),
                "name": name,
                "arguments": arguments,
            }
            for fixture_id, (name, arguments) in TOOL_CALL_FIXTURES.items()
        ],
        "output_parity": [
            {
                "fixture_id": fixture_id,
                "first_output_token_ids": [index] * 32,
                "second_output_token_ids": [index] * 32,
            }
            for index, fixture_id in enumerate(OUTPUT_PARITY_FIXTURE_IDS)
        ],
    }
    return {
        "record_kind": "cloud_worker_admission_measurement",
        "schema_version": "0.2.0",
        "protocol_sha256": protocol_digest(frozen),
        "architecture_sha256": "a" * 64,
        "authorization_sha256": "a" * 64,
        "image_sha256": "a" * 64,
        "input_lock_sha256": "a" * 64,
        "code_sha256": "a" * 64,
        "worker_index": worker_index,
        "instance_id": instance_id,
        "runtime": {
            "model": "Qwen/Qwen3.6-35B-A3B-FP8",
            "revision": "a" * 40,
            "cuda_name": "NVIDIA L40S",
            "cuda_total_memory_bytes": 48 * 1024**3,
            "torch_version": "2.8.0",
            "vllm_version": "0.10.0",
        },
        "rungs": {
            "l40s-tp1-32768": deepcopy(rung),
            "l40s-tp1-65536": deepcopy(rung),
        },
    }


def test_compiler_selects_the_largest_passing_rung_and_binds_raw_bytes() -> None:
    raw = measurement()
    evidence = b'{"raw":"worker-0"}\n'
    receipt = compile_worker_admission(
        raw,
        protocol(),
        evidence_sha256=measurement_evidence_digest(evidence),
    )
    assert receipt["rung"] == "l40s-tp1-65536"
    assert receipt["measurement_evidence_sha256"] == measurement_evidence_digest(evidence)


def test_compiler_falls_back_only_to_the_registered_lower_rung() -> None:
    raw = measurement()
    raw["rungs"]["l40s-tp1-65536"]["throughput"]["samples"][0]["elapsed_seconds"] = 128 / 7.99
    receipt = compile_worker_admission(raw, protocol(), evidence_sha256="1" * 64)
    assert receipt["rung"] == "l40s-tp1-32768"


def test_compiler_rejects_missing_or_mismatched_protocol_binding() -> None:
    raw = measurement()
    raw["protocol_sha256"] = "b" * 64
    with pytest.raises(CloudManifestError, match="frozen pilot protocol"):
        compile_worker_admission(raw, protocol(), evidence_sha256="1" * 64)


def test_dual_compiler_rejects_reused_raw_evidence() -> None:
    first = measurement()
    second = measurement(worker_index=1, instance_id="i-1123456789abcdef0")
    with pytest.raises(CloudManifestError, match="distinct raw"):
        compile_dual_worker_admissions(
            {0: (first, "1" * 64), 1: (second, "1" * 64)},
            protocol(),
        )


def test_compiler_recomputes_tool_and_output_parity_gates_from_raw_observations() -> None:
    raw = measurement()
    raw["rungs"]["l40s-tp1-65536"]["tool_calls"][0]["arguments"] = {"left": 99, "right": 3}
    raw["rungs"]["l40s-tp1-65536"]["output_parity"][0]["second_output_token_ids"] = [99] * 32
    receipt = compile_worker_admission(raw, protocol(), evidence_sha256="1" * 64)
    assert receipt["rung"] == "l40s-tp1-32768"


def test_compiler_rejects_raw_memory_above_the_usable_boundary() -> None:
    raw = measurement()
    raw["rungs"]["l40s-tp1-32768"]["peak_allocated_bytes"] = 44 * 1024**3 + 1
    raw["rungs"]["l40s-tp1-65536"]["peak_allocated_bytes"] = 44 * 1024**3 + 1
    with pytest.raises(CloudManifestError, match="44 GiB usable GPU boundary"):
        compile_worker_admission(raw, protocol(), evidence_sha256="1" * 64)


def test_compiler_rejects_a_non_l40s_raw_runtime() -> None:
    raw = measurement()
    raw["runtime"]["cuda_name"] = "NVIDIA H100"
    with pytest.raises(CloudManifestError, match="not from an L40S runtime"):
        compile_worker_admission(raw, protocol(), evidence_sha256="1" * 64)

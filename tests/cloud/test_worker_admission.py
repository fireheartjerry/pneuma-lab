from __future__ import annotations

from copy import deepcopy

import pytest

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
        "peak_gpu_memory_gib": 43.5,
        "p10_output_tokens_per_second": 8.0,
        "tool_call_cases": 4,
        "tool_call_passes": 4,
        "output_parity_cases": 4,
        "output_parity_passes": 4,
    }
    return {
        "record_kind": "cloud_worker_admission_measurement",
        "schema_version": "0.1.0",
        "protocol_sha256": protocol_digest(frozen),
        "architecture_sha256": "a" * 64,
        "authorization_sha256": "a" * 64,
        "image_sha256": "a" * 64,
        "input_lock_sha256": "a" * 64,
        "code_sha256": "a" * 64,
        "worker_index": worker_index,
        "instance_id": instance_id,
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
    raw["rungs"]["l40s-tp1-65536"]["p10_output_tokens_per_second"] = 7.99
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

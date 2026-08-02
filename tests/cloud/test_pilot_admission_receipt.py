from __future__ import annotations

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.manifests import validate_pilot_admission_receipt
from pneuma_lab.cloud.pilot import (
    MINIMUM_P10_OUTPUT_TOKENS_PER_SECOND,
    protocol_digest,
    require_receipt_within_protocol,
    require_worker_receipts_within_protocol,
)


def protocol() -> dict:
    return {
        "record_kind": "cloud_pilot_protocol",
        "schema_version": "0.2.0",
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
        "minimum_p10_output_tokens_per_second": MINIMUM_P10_OUTPUT_TOKENS_PER_SECOND,
        "throughput_samples_per_rung": 10,
        "output_tokens_per_sample": 128,
        "warmup_samples_per_rung": 1,
        "p10_method": "nearest_rank",
        "rungs": ["l40s-tp1-32768", "l40s-tp1-65536"],
        "bound_hashes": {name: "a" * 64 for name in ("architecture", "authorization", "image", "input_lock", "code")},
    }


def receipt() -> dict:
    return {
        "record_kind": "cloud_pilot_admission_receipt",
        "schema_version": "0.2.0",
        "protocol_sha256": "a" * 64,
        "architecture_sha256": "b" * 64,
        "authorization_sha256": "c" * 64,
        "image_sha256": "d" * 64,
        "input_lock_sha256": "e" * 64,
        "code_sha256": "f" * 64,
        "worker_index": 0,
        "rung": "l40s-tp1-65536",
        "compute": {
            "instance_type": "g6e.2xlarge",
            "vcpus": 8,
            "gpu_count": 1,
            "usable_gpu_memory_gib": 44,
        },
        "gates": {
            "oom": True,
            "tool_call": True,
            "output_parity": True,
            "p10_throughput": True,
        },
        "measurements": {
            "peak_gpu_memory_gib": 43.5,
            "p10_output_tokens_per_second": MINIMUM_P10_OUTPUT_TOKENS_PER_SECOND,
            "tool_call_cases": 4,
            "tool_call_passes": 4,
            "output_parity_cases": 4,
            "output_parity_passes": 4,
        },
    }


def test_receipt_binds_the_exact_one_gpu_topology() -> None:
    assert validate_pilot_admission_receipt(receipt())["rung"] == "l40s-tp1-65536"


def test_receipt_p10_gate_is_checked_against_the_exact_frozen_protocol() -> None:
    record = receipt()
    frozen = protocol()
    record["protocol_sha256"] = protocol_digest(frozen)
    assert require_receipt_within_protocol(record, frozen)["gates"]["p10_throughput"]

    record["measurements"]["p10_output_tokens_per_second"] = 0.5
    with pytest.raises(CloudManifestError, match="frozen protocol threshold"):
        require_receipt_within_protocol(record, frozen)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("instance_type", "g6e.12xlarge"),
        ("vcpus", 48),
        ("gpu_count", 4),
        ("usable_gpu_memory_gib", 48),
    ],
)
def test_receipt_rejects_retired_or_nominal_topology(field: str, value: object) -> None:
    record = receipt()
    record["compute"][field] = value
    with pytest.raises(CloudManifestError):
        validate_pilot_admission_receipt(record)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("tool_call_passes", 3, "tool-call gate"),
        ("output_parity_passes", 3, "output-parity gate"),
    ],
)
def test_receipt_rejects_gate_count_contradictions(field: str, value: object, message: str) -> None:
    record = receipt()
    record["measurements"][field] = value
    with pytest.raises(CloudManifestError, match=message):
        validate_pilot_admission_receipt(record)


def test_receipt_rejects_more_passes_than_cases() -> None:
    """A count that cannot happen is refused rather than rounded into a pass."""

    record = receipt()
    record["measurements"]["tool_call_passes"] = 5
    with pytest.raises(CloudManifestError, match="more passes than cases"):
        validate_pilot_admission_receipt(record)


def test_a_coherent_partial_failure_is_recordable() -> None:
    """Failing a gate is representable; only the contradiction is refused."""

    record = receipt()
    record["measurements"]["tool_call_passes"] = 3
    record["gates"]["tool_call"] = False
    assert validate_pilot_admission_receipt(record)["gates"]["tool_call"] is False


def test_two_worker_admission_requires_a_distinct_receipt_for_each_worker() -> None:
    frozen = protocol()
    first = receipt()
    first["protocol_sha256"] = protocol_digest(frozen)
    second = receipt()
    second["protocol_sha256"] = protocol_digest(frozen)
    second["worker_index"] = 1
    assert set(require_worker_receipts_within_protocol({0: first, 1: second}, frozen)) == {0, 1}

    with pytest.raises(CloudManifestError, match="worker indexes"):
        require_worker_receipts_within_protocol({0: first, 1: first}, frozen)

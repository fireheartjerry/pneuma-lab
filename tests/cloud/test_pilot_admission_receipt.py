from __future__ import annotations

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.manifests import validate_pilot_admission_receipt


def receipt() -> dict:
    return {
        "record_kind": "cloud_pilot_admission_receipt",
        "schema_version": "0.1.0",
        "protocol_sha256": "a" * 64,
        "architecture_sha256": "b" * 64,
        "authorization_sha256": "c" * 64,
        "image_sha256": "d" * 64,
        "input_lock_sha256": "e" * 64,
        "code_sha256": "f" * 64,
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
            "p10_output_tokens_per_second": 1.0,
            "tool_call_cases": 4,
            "tool_call_passes": 4,
            "output_parity_cases": 4,
            "output_parity_passes": 4,
        },
    }


def test_receipt_binds_the_exact_one_gpu_topology() -> None:
    assert validate_pilot_admission_receipt(receipt())["rung"] == "l40s-tp1-65536"


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

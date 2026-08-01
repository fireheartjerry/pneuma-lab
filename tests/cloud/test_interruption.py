from __future__ import annotations

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.interruption import require_interruption_qualification


def receipt() -> dict:
    return {
        "record_kind": "cloud_interruption_qualification_receipt",
        "schema_version": "0.1.0",
        "plan_sha256": "a" * 64,
        "input_lock_sha256": "b" * 64,
        "provider": "aws",
        "region": "us-east-1",
        "account_id": "123456789012",
        "drill_id": "interrupt-001",
        "controller_identity_arn": "arn:aws:iam::123456789012:role/controller",
        "watcher_identity_arn": "arn:aws:iam::123456789012:role/watcher",
        "lease": {
            "key": "interrupt-001",
            "issued_timestamp": "2026-08-01T00:00:00Z",
            "expires_timestamp": "2026-08-01T00:01:00Z",
            "watcher_observed_timestamp": "2026-08-01T00:01:01Z",
            "controller_renewal_count": 0,
        },
        "boundary": {
            "sequence": 1,
            "pre_interrupt_sha256": "c" * 64,
            "restored_sha256": "c" * 64,
            "all_arm_visible_bytes_match": True,
        },
        "resources": [
            {"resource_id": "i-1", "resource_type": "compute", "state_before": "running", "state_after": "absent"},
            {"resource_id": "vol-1", "resource_type": "disk", "state_before": "in-use", "state_after": "absent"},
        ],
        "residual_resource_ids": [],
        "gates": {
            "independent_watcher": True,
            "lease_expired": True,
            "controller_could_not_renew": True,
            "boundary_exact": True,
            "all_tagged_resources_absent": True,
        },
    }


def test_exact_interruption_receipt_passes() -> None:
    assert require_interruption_qualification(receipt())["drill_id"] == "interrupt-001"


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda row: row.update(watcher_identity_arn=row["controller_identity_arn"]), "independent"),
        (lambda row: row["lease"].update(watcher_observed_timestamp="2026-08-01T00:00:59Z"), "expiry"),
        (lambda row: row["boundary"].update(restored_sha256="d" * 64), "byte exact"),
        (lambda row: row["resources"].append(dict(row["resources"][0])), "repeats"),
    ],
)
def test_interruption_receipt_fails_closed(mutation, message: str) -> None:
    row = receipt()
    mutation(row)
    with pytest.raises(CloudManifestError, match=message):
        require_interruption_qualification(row)

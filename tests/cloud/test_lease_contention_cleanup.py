from __future__ import annotations

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.lease_contention import require_lease_contention_cleanup


def receipt() -> dict:
    return {
        "record_kind": "cloud_lease_contention_cleanup_receipt",
        "schema_version": "0.1.0",
        "plan_sha256": "1" * 64,
        "input_lock_sha256": None,
        "provider": "aws",
        "region": "us-east-1",
        "account_id": "123456789012",
        "cleanup_id": "lease-contention-cleanup-010",
        "target_action_id": "lease-contention-009",
        "table_name": "pneuma-c160-leases",
        "table_arn": "arn:aws:dynamodb:us-east-1:123456789012:table/pneuma-c160-leases",
        "lease_key": "runs/preparation/lease-contention-009",
        "expected_owner": "lease-contention-009-worker-03",
        "identity_arn": "arn:aws:iam::123456789012:root",
        "preflight": {"table_active": True, "table_arn_exact": True, "item_present": True, "owner_exact": True, "action_id_exact": True},
        "deletion": {"attempted": True, "succeeded": True, "return_code": 0, "stdout_sha256": "a" * 64, "stderr_sha256": "b" * 64},
        "final": {"item_absent": True, "table_count": 0},
        "gates": {"identity_bound": True, "exact_item_bound": True, "delete_succeeded": True, "final_absent": True, "no_retries": True, "no_scientific_action": True},
        "residual_resource_ids": [],
        "no_scientific_action": True,
        "verdict": "passed",
        "failure_reason": None,
    }


def test_cleanup_receipt_passes() -> None:
    assert require_lease_contention_cleanup(receipt())["verdict"] == "passed"


@pytest.mark.parametrize("mutation", [
    lambda row: row["preflight"].update(owner_exact=False),
    lambda row: row["deletion"].update(succeeded=False),
    lambda row: row["final"].update(item_absent=False),
])
def test_cleanup_receipt_fails_closed(mutation) -> None:
    row = receipt()
    mutation(row)
    with pytest.raises(CloudManifestError):
        require_lease_contention_cleanup(row)

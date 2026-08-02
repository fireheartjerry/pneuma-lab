from __future__ import annotations

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.lease_contention import require_lease_contention_qualification


def receipt() -> dict:
    attempts = [
        {"attempt": 0, "owner": "lease-contention-008-worker-00", "outcome": "success", "return_code": 0, "stdout_sha256": "a" * 64, "stderr_sha256": "b" * 64, "duration_ms": 10},
        {"attempt": 1, "owner": "lease-contention-008-worker-01", "outcome": "conditional_failed", "return_code": 254, "stdout_sha256": "c" * 64, "stderr_sha256": "d" * 64, "duration_ms": 11},
    ]
    return {
        "record_kind": "cloud_lease_contention_qualification_receipt",
        "schema_version": "0.1.0",
        "plan_sha256": "1" * 64,
        "input_lock_sha256": None,
        "provider": "aws",
        "region": "us-east-1",
        "account_id": "123456789012",
        "qualification_id": "lease-contention-008",
        "table_name": "pneuma-c160-leases",
        "table_arn": "arn:aws:dynamodb:us-east-1:123456789012:table/pneuma-c160-leases",
        "lease_key": "runs/preparation/lease-contention-008",
        "identity_arn": "arn:aws:iam::123456789012:root",
        "attempt_count": 2,
        "max_concurrency": 2,
        "condition_expression": "attribute_not_exists(lease_key)",
        "preflight": {"table_active": True, "table_arn_exact": True, "item_absent": True, "table_count": 0},
        "contenders": attempts,
        "winner": {"attempt": 0, "owner": attempts[0]["owner"], "item_sha256": "e" * 64, "action_id_exact": True},
        "cleanup": {"delete_attempted": True, "delete_succeeded": True, "final_item_absent": True, "final_table_count": 0},
        "gates": {"table_identity_bound": True, "exactly_one_winner": True, "all_losers_conditional": True, "no_provider_errors": True, "winner_readback_exact": True, "no_retries": True, "exact_teardown": True, "no_scientific_action": True},
        "residual_resource_ids": [],
        "no_scientific_action": True,
        "verdict": "passed",
        "failure_reason": None,
    }


def test_contention_receipt_passes() -> None:
    assert require_lease_contention_qualification(receipt())["verdict"] == "passed"


@pytest.mark.parametrize("mutation", [
    lambda row: row["contenders"].append(dict(row["contenders"][0], attempt=2, owner="lease-contention-008-worker-02")),
    lambda row: row["winner"].update(owner="not-the-winner"),
    lambda row: row["cleanup"].update(final_item_absent=False),
])
def test_contention_receipt_fails_closed(mutation) -> None:
    row = receipt()
    mutation(row)
    with pytest.raises(CloudManifestError):
        require_lease_contention_qualification(row)

from __future__ import annotations

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.step5b_lifecycle import validate_step5b_lifecycle_semantics


def _plan():
    return {"lifecycle_terraform_plan_sha256": "a" * 64}


def _receipt():
    return {"record_kind": "cloud_step5b_lifecycle_receipt", "schema_version": "0.1.0", "generated_timestamp": "2026-08-01T12:00:00Z", "account_id": "892077329800", "region": "us-east-1", "bucket": "pneuma-phase-b-892077329800", "terraform_plan_sha256": "a" * 64, "before_state_sha256": "b" * 64, "after_state_sha256": "c" * 64, "apply_output_sha256": "d" * 64, "plan_counts": {"add": 0, "change": 1, "destroy": 0}, "incremental_cost_usd": 0.0, "rules": [{"id": "expire-experiment-artifacts", "status": "Enabled", "prefix": "runs/", "expiration_days": 365, "noncurrent_days": 30, "abort_days": 7}, {"id": "expire-step5b-payloads", "status": "Enabled", "prefix": "runs/step5b/payloads/", "expiration_days": 35, "noncurrent_days": 30, "abort_days": 7}]}


def test_exact_live_lifecycle_receipt_passes() -> None:
    assert validate_step5b_lifecycle_semantics(_receipt(), _plan())["rules"][1]["expiration_days"] == 35


def test_plan_and_rule_drift_fail_closed() -> None:
    receipt = _receipt()
    receipt["terraform_plan_sha256"] = "e" * 64
    with pytest.raises(CloudManifestError, match="Terraform plan"):
        validate_step5b_lifecycle_semantics(receipt, _plan())
    receipt = _receipt()
    receipt["rules"][1]["expiration_days"] = 36
    with pytest.raises(CloudManifestError):
        validate_step5b_lifecycle_semantics(receipt, _plan())

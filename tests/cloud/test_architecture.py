from __future__ import annotations

import pytest

from pneuma_lab.cloud.architecture import validate_architecture
from pneuma_lab.cloud.errors import CloudManifestError


def architecture() -> dict:
    return {"record_kind": "cloud_architecture_manifest", "schema_version": "0.1.0", "region": "us-east-1", "tier": "tier-agnostic", "compute": {"instance_type": "g6e.2xlarge", "max_vcpus": 8, "min_vcpus": 0, "allocation_strategy": "BEST_FIT_PROGRESSIVE", "ami_id": "ami-fixture", "root_snapshot_id": "snap-fixture", "bootstrap_sha256": "a" * 64}, "storage": {"bucket_prefix": "runs/fixture", "lifecycle_policy_id": "fixture-policy", "absolute_deletion_date": "2027-01-01"}, "lease": {"table": "fixture-leases", "key": "fixture-run"}, "controller_policy": {"identity": "controller", "actions": ["dynamodb:GetItem", "s3:GetObject", "s3:PutObject"]}, "watcher_policy": {"identity": "watcher", "actions": ["dynamodb:UpdateItem", "ec2:TerminateInstances"]}}


def test_architecture_requires_separate_read_only_controller() -> None:
    assert validate_architecture(architecture())["tier"] == "tier-agnostic"


@pytest.mark.parametrize("field,value", [("tier", "C120"), ("tier", "C160")])
def test_tier_constants_fail_closed(field: str, value: str) -> None:
    record = architecture()
    record[field] = value
    with pytest.raises(CloudManifestError):
        validate_architecture(record)


def test_controller_cannot_renew_lease_or_share_watcher_identity() -> None:
    record = architecture()
    record["controller_policy"]["actions"].append("dynamodb:UpdateItem")
    with pytest.raises(CloudManifestError):
        validate_architecture(record)
    record = architecture()
    record["watcher_policy"]["identity"] = "controller"
    with pytest.raises(CloudManifestError):
        validate_architecture(record)

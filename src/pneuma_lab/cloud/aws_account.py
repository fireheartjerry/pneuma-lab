"""Offline construction of an account-bound AWS verification receipt."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .errors import CloudManifestError
from .manifests import _validate
from .preflight import PRIMARY_REQUIRED_VCPUS, require_quota

ON_DEMAND_QUOTA_NAME = "Running On-Demand G and VT instances"
SPOT_QUOTA_NAME = "All G and VT Spot Instance Requests"


def _quota_value(quotas: Sequence[Mapping[str, Any]], name: str) -> float:
    matches = [item for item in quotas if item.get("QuotaName") == name]
    if len(matches) != 1:
        raise CloudManifestError(f"expected exactly one AWS quota named {name!r}")
    value = matches[0].get("Value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise CloudManifestError(f"AWS quota {name!r} has no numeric applied value")
    return float(value)


def build_account_verification(
    *,
    identity: Mapping[str, Any],
    quotas: Sequence[Mapping[str, Any]],
    offerings: Sequence[Mapping[str, Any]],
    terraform_config_sha256: str,
    terraform_plan_sha256: str,
    aws_cli_version: str,
) -> dict[str, Any]:
    """Build a strict receipt from fresh read-only AWS and Terraform outputs."""

    account_id = identity.get("Account")
    principal_arn = identity.get("Arn")
    if not isinstance(account_id, str) or not isinstance(principal_arn, str):
        raise CloudManifestError("AWS identity response is incomplete")
    if f"::{account_id}:" not in principal_arn:
        raise CloudManifestError("AWS principal ARN does not bind the reported account")

    on_demand = _quota_value(quotas, ON_DEMAND_QUOTA_NAME)
    spot = _quota_value(quotas, SPOT_QUOTA_NAME)
    require_quota(int(on_demand))
    require_quota(int(spot))

    zones = sorted(
        {
            str(item["Location"])
            for item in offerings
            if item.get("InstanceType") == "g6e.2xlarge"
            and isinstance(item.get("Location"), str)
        }
    )
    if not zones:
        raise CloudManifestError("g6e.2xlarge has no account-visible us-east-1 offering")

    receipt = {
        "record_kind": "cloud_aws_account_verification",
        "schema_version": "0.1.0",
        "account_id": account_id,
        "principal_arn": principal_arn,
        "region": "us-east-1",
        "instance_type": "g6e.2xlarge",
        "required_vcpus": PRIMARY_REQUIRED_VCPUS,
        "on_demand_g_vt_vcpus": on_demand,
        "spot_g_vt_vcpus": spot,
        "availability_zones": zones,
        "terraform_config_sha256": terraform_config_sha256,
        "terraform_plan_sha256": terraform_plan_sha256,
        "aws_cli_version": aws_cli_version,
    }
    return _validate(receipt, expected_kind="cloud_aws_account_verification")

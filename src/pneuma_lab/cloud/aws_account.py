"""Offline construction of an account-bound AWS verification receipt."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .errors import CloudManifestError
from .manifests import _validate
from .preflight import (
    PRIMARY_ON_DEMAND_REQUIRED_VCPUS,
    PRIMARY_SPOT_REQUIRED_VCPUS,
    require_quota,
)
from .qualification_execution import (
    parse_terraform_show_json,
    verify_provider_bindings,
    verify_spend_history_binding,
)

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
    terraform_show: bytes | str | Mapping[str, Any],
    provider: Any,
    spend_authority: Mapping[str, Any],
    ledger_path: Path,
    aws_cli_version: str,
) -> dict[str, Any]:
    """Build a strict account receipt from real Terraform and read-only checks.

    The old constructor accepted caller-invented ``terraform_config_sha256``
    and ``terraform_plan_sha256`` strings.  Those values proved only that a
    caller supplied strings.  This path parses the actual ``terraform show
    -json`` document, compares the action identity in its variables with the
    planned job environment and compute-resource tags, and performs explicit
    role/subnet/security-group readbacks through ``provider``.
    """

    plan = parse_terraform_show_json(terraform_show)
    provider_bindings = verify_provider_bindings(provider, plan)
    spend_history_sha256 = verify_spend_history_binding(spend_authority, ledger_path)

    account_id = identity.get("Account")
    principal_arn = identity.get("Arn")
    if not isinstance(account_id, str) or not isinstance(principal_arn, str):
        raise CloudManifestError("AWS identity response is incomplete")
    if f"::{account_id}:" not in principal_arn:
        raise CloudManifestError("AWS principal ARN does not bind the reported account")
    if provider_bindings["account_id"] != account_id:
        raise CloudManifestError(
            "Terraform provider binding checks came from a different AWS account"
        )
    if f"::{account_id}:" not in provider_bindings["role"]["Arn"]:
        raise CloudManifestError(
            "verified worker IAM role does not belong to the verified AWS account"
        )
    if plan.get("region") not in (None, "us-east-1"):
        raise CloudManifestError("Terraform qualification plan is not in us-east-1")

    on_demand = _quota_value(quotas, ON_DEMAND_QUOTA_NAME)
    spot = _quota_value(quotas, SPOT_QUOTA_NAME)
    require_quota(int(on_demand), PRIMARY_ON_DEMAND_REQUIRED_VCPUS)
    require_quota(int(spot), PRIMARY_SPOT_REQUIRED_VCPUS)

    zones = sorted(
        {
            str(item["Location"])
            for item in offerings
            if item.get("InstanceType") == "g6e.2xlarge"
            and isinstance(item.get("Location"), str)
        }
    )
    if not zones:
        raise CloudManifestError(
            "g6e.2xlarge has no account-visible us-east-1 offering"
        )

    receipt = {
        "record_kind": "cloud_aws_account_verification",
        "schema_version": "0.2.0",
        "account_id": account_id,
        "principal_arn": principal_arn,
        "region": "us-east-1",
        "instance_type": "g6e.2xlarge",
        "required_on_demand_vcpus": PRIMARY_ON_DEMAND_REQUIRED_VCPUS,
        "required_spot_vcpus": PRIMARY_SPOT_REQUIRED_VCPUS,
        "on_demand_g_vt_vcpus": on_demand,
        "spot_g_vt_vcpus": spot,
        "availability_zones": zones,
        "qualification_action_id": plan["action_id"],
        "terraform_show_sha256": plan["terraform_show_sha256"],
        "worker_role_arn": provider_bindings["role"]["Arn"],
        "subnet_ids": list(plan["subnet_ids"]),
        "security_group_ids": list(plan["security_group_ids"]),
        "spend_history_sha256": spend_history_sha256,
        "aws_cli_version": aws_cli_version,
    }
    return _validate(receipt, expected_kind="cloud_aws_account_verification")

from __future__ import annotations

from pathlib import Path

import pytest

from pneuma_lab.cloud.authorization_keys import canonical_ledger_digest
from pneuma_lab.cloud.aws_account import (
    ON_DEMAND_QUOTA_NAME,
    SPOT_QUOTA_NAME,
    build_account_verification,
)
from pneuma_lab.cloud.errors import CloudManifestError

from .test_ephemeral_runner import terraform_show as qualification_terraform_show


LEDGER = (
    Path(__file__).resolve().parents[2]
    / "docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md"
)


class Provider:
    def get_caller_identity(self):
        return {
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:role/reader",
        }

    def get_role(self, role_name):
        arns = {
            "pneuma-worker": "arn:aws:iam::123456789012:role/pneuma-worker",
            "pneuma-batch": "arn:aws:iam::123456789012:role/pneuma-batch",
            "pneuma-spot": "arn:aws:iam::123456789012:role/pneuma-spot",
        }
        return {
            "Role": {
                "RoleName": role_name,
                "Arn": arns[role_name],
            }
        }

    def get_instance_profile(self, profile_name):
        return {
            "InstanceProfile": {
                "InstanceProfileName": profile_name,
                "Arn": f"arn:aws:iam::123456789012:instance-profile/{profile_name}",
                "Roles": [
                    {
                        "RoleName": "pneuma-worker",
                        "Arn": "arn:aws:iam::123456789012:role/pneuma-worker",
                    }
                ],
            }
        }

    def describe_subnets(self, subnet_ids):
        return [
            {
                "SubnetId": subnet_id,
                "VpcId": "vpc-12345678",
                "AvailabilityZone": f"us-east-1{chr(ord('a') + index)}",
                "State": "available",
            }
            for index, subnet_id in enumerate(subnet_ids)
        ]

    def describe_security_groups(self, group_ids):
        return [
            {
                "GroupId": group_id,
                "VpcId": "vpc-12345678",
                "IpPermissions": [],
            }
            for group_id in group_ids
        ]


def _show() -> dict:
    return qualification_terraform_show(
        action_id="fixed-admission-001", code="signed-code"
    )


def _quotas(on_demand: float = 8.0, spot: float = 16.0) -> list[dict]:
    return [
        {"QuotaName": ON_DEMAND_QUOTA_NAME, "Value": on_demand},
        {"QuotaName": SPOT_QUOTA_NAME, "Value": spot},
    ]


def _kwargs(on_demand: float = 8.0, spot: float = 16.0) -> dict:
    return {
        "identity": {
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:role/reviewer",
        },
        "quotas": _quotas(on_demand, spot),
        "offerings": [{"InstanceType": "g6e.2xlarge", "Location": "us-east-1a"}],
        "terraform_show": _show(),
        "provider": Provider(),
        "spend_authority": {"spend_history_sha256": canonical_ledger_digest(LEDGER)},
        "ledger_path": LEDGER,
        "aws_cli_version": "aws-cli/2.35.19 Python/3.14.6 Linux/fixture",
    }


def test_receipt_uses_terraform_show_and_explicit_provider_bindings() -> None:
    receipt = build_account_verification(**_kwargs())
    assert receipt["qualification_action_id"] == "fixed-admission-001"
    assert receipt["terraform_show_sha256"]
    assert receipt["worker_role_arn"].endswith("/pneuma-worker")
    assert receipt["spend_history_sha256"] == canonical_ledger_digest(LEDGER)


@pytest.mark.parametrize("on_demand,spot", [(7.0, 16.0), (8.0, 15.0)])
def test_both_gpu_quota_paths_must_be_applied(on_demand: float, spot: float) -> None:
    with pytest.raises(CloudManifestError, match="quota"):
        build_account_verification(**_kwargs(on_demand, spot))


def test_wrong_instance_offering_fails_closed() -> None:
    kwargs = _kwargs()
    kwargs["offerings"] = [{"InstanceType": "g6e.12xlarge", "Location": "us-east-1a"}]
    with pytest.raises(CloudManifestError, match="offering"):
        build_account_verification(**kwargs)


def test_caller_supplied_terraform_hash_fields_are_not_an_account_plan() -> None:
    kwargs = _kwargs()
    kwargs.pop("terraform_show")
    kwargs.update(terraform_config_sha256="a" * 64, terraform_plan_sha256="b" * 64)
    with pytest.raises(TypeError):
        build_account_verification(**kwargs)

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.authorization_keys import canonical_ledger_digest
from pneuma_lab.cloud.aws_account import (
    ON_DEMAND_QUOTA_NAME,
    SPOT_QUOTA_NAME,
    build_account_verification,
)
from pneuma_lab.cloud.errors import CloudManifestError


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
        return [{"SubnetId": subnet_id} for subnet_id in subnet_ids]

    def describe_security_groups(self, group_ids):
        return [{"GroupId": group_id} for group_id in group_ids]


def _show() -> dict:
    return {
        "format_version": "1.0",
        "variables": {
            "region": {"value": "us-east-1"},
            "qualification_code": {"value": "signed-code"},
            "qualification_action_id": {"value": "fixed-admission-001"},
            "instance_role_arn": {
                "value": "arn:aws:iam::123456789012:instance-profile/pneuma-worker"
            },
            "batch_service_role_arn": {
                "value": "arn:aws:iam::123456789012:role/pneuma-batch"
            },
            "spot_fleet_role_arn": {
                "value": "arn:aws:iam::123456789012:role/pneuma-spot"
            },
        },
        "planned_values": {
            "root_module": {
                "resources": [
                    {
                        "address": "aws_batch_compute_environment.worker[0]",
                        "values": {
                            "compute_resources": [
                                {
                                    "instance_type": ["g6e.2xlarge"],
                                    "max_vcpus": 16,
                                    "instance_role": "arn:aws:iam::123456789012:instance-profile/pneuma-worker",
                                    "spot_iam_fleet_role": "arn:aws:iam::123456789012:role/pneuma-spot",
                                    "subnets": ["subnet-0123456789abcdef0"],
                                    "security_group_ids": ["sg-0123456789abcdef0"],
                                    "tags": {
                                        "QualificationCode": "signed-code",
                                        "QualificationActionId": "fixed-admission-001",
                                    },
                                }
                            ],
                            "service_role": "arn:aws:iam::123456789012:role/pneuma-batch",
                        },
                    },
                    {
                        "address": "aws_batch_job_definition.gpu_worker",
                        "values": {
                            "container_properties": json.dumps(
                                {
                                    "environment": [
                                        {
                                            "name": "QUALIFICATION_CODE",
                                            "value": "signed-code",
                                        },
                                        {
                                            "name": "QUALIFICATION_ACTION_ID",
                                            "value": "fixed-admission-001",
                                        },
                                    ]
                                }
                            )
                        },
                    },
                    {
                        "address": "aws_launch_template.worker",
                        "values": {
                            "tag_specifications": [
                                {
                                    "resource_type": "instance",
                                    "tags": {
                                        "QualificationCode": "signed-code",
                                        "QualificationActionId": "fixed-admission-001",
                                    },
                                },
                                {
                                    "resource_type": "volume",
                                    "tags": {
                                        "QualificationCode": "signed-code",
                                        "QualificationActionId": "fixed-admission-001",
                                    },
                                },
                            ]
                        },
                    },
                    {
                        "address": "aws_iam_role.worker",
                        "values": {"name": "pneuma-worker", "arn": None},
                    },
                ]
            }
        },
        "resource_changes": [
            {
                "address": "aws_batch_compute_environment.worker[0]",
                "change": {"actions": ["create"]},
            },
            {
                "address": "aws_batch_job_definition.gpu_worker[0]",
                "change": {"actions": ["create"]},
            },
            {
                "address": "aws_launch_template.worker",
                "change": {"actions": ["create"]},
            },
        ],
    }


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

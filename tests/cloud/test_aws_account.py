from __future__ import annotations

import pytest

from pneuma_lab.cloud.aws_account import (
    ON_DEMAND_QUOTA_NAME,
    SPOT_QUOTA_NAME,
    build_account_verification,
)
from pneuma_lab.cloud.errors import CloudManifestError


def _quotas(on_demand: float = 8.0, spot: float = 16.0) -> list[dict]:
    return [
        {"QuotaName": ON_DEMAND_QUOTA_NAME, "Value": on_demand},
        {"QuotaName": SPOT_QUOTA_NAME, "Value": spot},
    ]


def test_receipt_requires_identity_both_quotas_offering_and_plan() -> None:
    receipt = build_account_verification(
        identity={"Account": "123456789012", "Arn": "arn:aws:sts::123456789012:assumed-role/reviewer/session"},
        quotas=_quotas(),
        offerings=[{"InstanceType": "g6e.2xlarge", "Location": "us-east-1a"}],
        terraform_config_sha256="a" * 64,
        terraform_plan_sha256="b" * 64,
        aws_cli_version="aws-cli/2.35.19 Python/3.14.6 Linux/fixture",
    )
    assert receipt["availability_zones"] == ["us-east-1a"]


@pytest.mark.parametrize("on_demand,spot", [(7.0, 16.0), (8.0, 15.0)])
def test_both_gpu_quota_paths_must_be_applied(on_demand: float, spot: float) -> None:
    with pytest.raises(CloudManifestError, match="quota"):
        build_account_verification(
            identity={"Account": "123456789012", "Arn": "arn:aws:iam::123456789012:role/reviewer"},
            quotas=_quotas(on_demand, spot),
            offerings=[{"InstanceType": "g6e.2xlarge", "Location": "us-east-1a"}],
            terraform_config_sha256="a" * 64,
            terraform_plan_sha256="b" * 64,
            aws_cli_version="aws-cli/2.35.19 Python/3.14.6 Linux/fixture",
        )


def test_wrong_instance_offering_fails_closed() -> None:
    with pytest.raises(CloudManifestError, match="offering"):
        build_account_verification(
            identity={"Account": "123456789012", "Arn": "arn:aws:iam::123456789012:role/reviewer"},
            quotas=_quotas(),
            offerings=[{"InstanceType": "g6e.12xlarge", "Location": "us-east-1a"}],
            terraform_config_sha256="a" * 64,
            terraform_plan_sha256="b" * 64,
            aws_cli_version="aws-cli/2.35.19 Python/3.14.6 Linux/fixture",
        )

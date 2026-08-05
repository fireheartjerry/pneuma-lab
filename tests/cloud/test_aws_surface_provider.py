from __future__ import annotations

import json

from pneuma_lab.cloud import aws_surface_provider
from pneuma_lab.cloud.production_controller import ProductionSubmission


class _FakeEc2:
    def describe_images(self, **kwargs):
        assert kwargs == {"ImageIds": [aws_surface_provider.AMI_ID]}
        return {"Images": [{"ImageId": aws_surface_provider.AMI_ID, "OwnerId": aws_surface_provider.AMI_OWNER_ID, "Architecture": "x86_64", "RootDeviceName": "/dev/xvda", "RootDeviceType": "ebs", "State": "available"}]}

    def describe_instance_type_offerings(self, **kwargs):
        assert kwargs == {
            "LocationType": "availability-zone",
            "Filters": [{"Name": "instance-type", "Values": ["m7i.large"]}],
        }
        return {"InstanceTypeOfferings": [{"Location": "us-east-1a"}]}

    def describe_instances(self, **kwargs):
        return {"Reservations": []}

    def describe_security_groups(self, **kwargs):
        return {"SecurityGroups": []}


class _FakeSts:
    def get_caller_identity(self):
        return {"Account": "123456789012"}


class _FakeQuotas:
    def get_service_quota(self, **kwargs):
        assert kwargs == {"ServiceCode": "ec2", "QuotaCode": "L-1216C47A"}
        return {"Quota": {"Value": 32, "Unit": "vCPUs"}}


class _FakePricing:
    def get_products(self, **kwargs):
        assert kwargs["ServiceCode"] == "AmazonEC2"
        document = {
            "terms": {
                "OnDemand": {
                    "term": {
                        "priceDimensions": {
                            "dimension": {
                                "unit": "Hrs",
                                "pricePerUnit": {"USD": "0.1000000000"},
                            }
                        }
                    }
                }
            }
        }
        return {"PriceList": [json.dumps(document)]}


class _FakeBoto3:
    def client(self, service, *, region_name):
        assert region_name in {"us-east-1", "us-east-1"}
        return {
            "ec2": _FakeEc2(),
            "sts": _FakeSts(),
            "service-quotas": _FakeQuotas(),
            "pricing": _FakePricing(),
        }[service]


def test_preflight_uses_the_valid_ec2_offering_filter(monkeypatch) -> None:
    monkeypatch.setattr(aws_surface_provider, "_boto3", lambda: _FakeBoto3())

    result = aws_surface_provider.collect_preflight()

    assert result["capacity_offerings"] == ["us-east-1a"]
    assert result["fresh_resource_absence_before"] is True


def test_surface_bootstrap_logs_into_ecr_without_persisting_credentials() -> None:
    config = aws_surface_provider.AwsSurfaceConfig(
        action_id="surface-test",
        region="us-east-1",
        input_lock_sha256="a" * 64,
        harness_sha256="b" * 64,
        harness_bytes_b64="e30=",
        image_refs={
            "controller": "123456789012.dkr.ecr.us-east-1.amazonaws.com/controller@sha256:" + "1" * 64,
            "model-server": "123456789012.dkr.ecr.us-east-1.amazonaws.com/model@sha256:" + "2" * 64,
            "benchmark-worker": "123456789012.dkr.ecr.us-east-1.amazonaws.com/worker@sha256:" + "3" * 64,
        },
        image_digests={role: "sha256:" + str(index) * 64 for index, role in enumerate(("controller", "model-server", "benchmark-worker"), 1)},
        provider_binding_sha256="c" * 64,
        source_commit="d" * 40,
    )

    user_data = aws_surface_provider.render_surface_user_data(config)

    assert "dnf install" not in user_data
    assert "aws ecr get-login-password --region 'us-east-1' | docker login" in user_data
    assert "awscli2" not in user_data
    assert "rm -f \"$ROOT/image-refs.json\" /root/.docker/config.json" in user_data
    assert "--network none --read-only --tmpfs /tmp --cap-drop ALL" in user_data
    assert "--security-opt no-new-privileges" in user_data
    assert "AWS-RunShellScript" not in user_data
    assert '\n"$ROOT/status.json"\n' not in user_data


def test_action_id_is_fail_closed_and_immutable() -> None:
    aws_surface_provider.validate_action_id("FIXTURE-NONSCI-20260805-v2-a1b2c3d4")

    import pytest

    with pytest.raises(Exception):
        aws_surface_provider.validate_action_id("official-surface-e2e-20260805")


def test_absent_error_classifier_is_narrow() -> None:
    class _Absent(Exception):
        response = {"Error": {"Code": "InvalidInstanceID.NotFound"}}

    class _Other(Exception):
        response = {"Error": {"Code": "UnauthorizedOperation"}}

    assert aws_surface_provider._absent(_Absent(), "InvalidInstanceID.NotFound")
    assert not aws_surface_provider._absent(_Other(), "InvalidInstanceID.NotFound")


def test_vpc_attribute_parser_accepts_aws_nested_value_shape() -> None:
    assert aws_surface_provider.AwsSurfaceProvider._vpc_attribute_enabled(
        {"EnableDnsSupport": {"Value": True}}, "EnableDnsSupport"
    )
    assert aws_surface_provider.AwsSurfaceProvider._vpc_attribute_enabled(
        {"EnableDnsHostnames": {"Value": True}}, "EnableDnsHostnames"
    )
    assert not aws_surface_provider.AwsSurfaceProvider._vpc_attribute_enabled(
        {"EnableDnsSupport": {"Value": False}}, "EnableDnsSupport"
    )


def test_observation_uses_a_fresh_ssm_status_snapshot() -> None:
    class _Exceptions:
        class InvalidInstanceId(Exception):
            pass

        class InvocationDoesNotExist(Exception):
            pass

    class _Ssm:
        exceptions = _Exceptions

        def __init__(self) -> None:
            self.calls = 0
            self.statuses = [
                {"terminal": False, "state": "BOOTSTRAPPING"},
                {"terminal": True, "state": "SUCCEEDED"},
            ]

        def send_command(self, **kwargs):
            self.calls += 1
            return {"Command": {"CommandId": f"command-{self.calls}"}}

        def get_command_invocation(self, **kwargs):
            status = self.statuses[self.calls - 1]
            return {"Status": "Success", "StandardOutputContent": json.dumps(status)}

    provider = object.__new__(aws_surface_provider.AwsSurfaceProvider)
    provider.ssm = _Ssm()
    provider.command_id = None
    provider.instance_id = None
    provider.last_status = None
    provider.external_deadline_epoch = None
    provider.ssm_online_seen = True
    provider.provider_responses = []

    from types import SimpleNamespace

    provider.config = SimpleNamespace(evidence_dir=None)
    provider.document_name = "pneuma-test-document"
    provider.document_version = "1"

    submission = ProductionSubmission("instance-1", ("instance-1",))
    first = provider.observe(submission)
    second = provider.observe(submission)

    assert first["terminal"] is False
    assert second["terminal"] is True
    assert provider.ssm.calls == 2

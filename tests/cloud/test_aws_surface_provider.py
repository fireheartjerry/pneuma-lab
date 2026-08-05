from __future__ import annotations

import json

from pneuma_lab.cloud import aws_surface_provider
from pneuma_lab.cloud.production_controller import ProductionSubmission


class _FakeEc2:
    def describe_instance_type_offerings(self, **kwargs):
        assert kwargs == {
            "LocationType": "availability-zone",
            "Filters": [{"Name": "instance-type", "Values": ["m7i.large"]}],
        }
        return {"InstanceTypeOfferings": [{"Location": "us-east-1a"}]}


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

    assert "dnf install -y docker\n" in user_data
    assert "aws ecr get-login-password --region 'us-east-1' | docker login" in user_data
    assert "awscli2" not in user_data
    assert "rm -f \"$ROOT/image-refs.json\" /root/.docker/config.json" in user_data
    assert "--network none --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges" in user_data
    assert '\n"$ROOT/status.json"\n' not in user_data


def test_iam_profile_propagation_error_is_narrowly_classified() -> None:
    class _Error(Exception):
        response = {
            "Error": {
                "Code": "InvalidParameterValue",
                "Message": "Value ... for parameter iamInstanceProfile.name is invalid",
            }
        }

    assert aws_surface_provider._is_iam_profile_propagation_error(_Error())

    class _OtherError(Exception):
        response = {"Error": {"Code": "InvalidParameterValue", "Message": "invalid instance type"}}

    assert not aws_surface_provider._is_iam_profile_propagation_error(_OtherError())


def test_teardown_treats_an_already_absent_instance_as_success() -> None:
    class _Absent(Exception):
        response = {"Error": {"Code": "InvalidInstanceID.NotFound"}}

    class _Other(Exception):
        response = {"Error": {"Code": "UnauthorizedOperation"}}

    assert aws_surface_provider._is_absent_instance_error(_Absent())
    assert not aws_surface_provider._is_absent_instance_error(_Other())


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

    submission = ProductionSubmission("instance-1", ("instance-1",))
    first = provider.observe(submission)
    second = provider.observe(submission)

    assert first["terminal"] is False
    assert second["terminal"] is True
    assert provider.ssm.calls == 2

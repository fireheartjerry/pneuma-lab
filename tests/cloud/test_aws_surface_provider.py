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


def test_surface_bootstrap_binds_only_verified_private_endpoint_addresses() -> None:
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

    user_data = aws_surface_provider.render_surface_user_data(
        config,
        endpoint_host_bindings={
            "api.ecr.us-east-1.amazonaws.com": "10.42.2.10",
            "123456789012.dkr.ecr.us-east-1.amazonaws.com": "10.42.2.11",
        },
    )

    assert "10.42.2.10\tapi.ecr.us-east-1.amazonaws.com" in user_data
    assert "10.42.2.11\t123456789012.dkr.ecr.us-east-1.amazonaws.com" in user_data
    assert "PrivateDnsEnabled=True" not in user_data

    import pytest

    with pytest.raises(Exception):
        aws_surface_provider.render_surface_user_data(config, endpoint_host_bindings={"api.ecr.us-east-1.amazonaws.com": "8.8.8.8"})


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


def test_network_interface_delete_binding_uses_ec2_attachment_shape() -> None:
    assert aws_surface_provider._network_interface_delete_on_termination(
        {"Attachment": {"DeleteOnTermination": True}}
    )
    assert not aws_surface_provider._network_interface_delete_on_termination(
        {"DeleteOnTermination": True}
    )


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


def test_resource_tags_retries_narrow_aws_eventual_consistency(monkeypatch) -> None:
    class _NotFound(Exception):
        response = {"Error": {"Code": "InvalidSubnetID.NotFound"}}

    class _Ec2:
        def __init__(self) -> None:
            self.calls = 0

        def create_tags(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise _NotFound()
            return {}

    from types import SimpleNamespace

    provider = object.__new__(aws_surface_provider.AwsSurfaceProvider)
    provider.ec2 = _Ec2()
    provider.provider_responses = []
    provider.config = SimpleNamespace(action_id="FIXTURE-NONSCI-20260805-v2-a1b2c3d4", evidence_dir=None)
    monkeypatch.setattr(aws_surface_provider.time, "sleep", lambda seconds: None)

    provider._resource_tags(["subnet-0123456789abcdef0"])

    assert provider.ec2.calls == 2


def test_effective_instance_readback_retries_only_ec2_not_found(monkeypatch) -> None:
    from types import SimpleNamespace

    class _NotFound(Exception):
        response = {"Error": {"Code": "InvalidInstanceID.NotFound"}}

    class _Ec2:
        def __init__(self) -> None:
            self.calls = 0

        def describe_instances(self, **kwargs):
            assert kwargs == {"InstanceIds": ["i-0123456789abcdef0"]}
            self.calls += 1
            if self.calls == 1:
                raise _NotFound()
            return {"Reservations": [{"Instances": [{"InstanceId": "i-0123456789abcdef0"}]}]}

    provider = object.__new__(aws_surface_provider.AwsSurfaceProvider)
    provider.ec2 = _Ec2()
    provider.provider_responses = []
    provider.config = SimpleNamespace(action_id="FIXTURE-NONSCI-20260805-v2-a1b2c3d4", evidence_dir=None)
    monkeypatch.setattr(aws_surface_provider.time, "sleep", lambda seconds: None)

    instance = provider._read_instance("i-0123456789abcdef0")

    assert instance["InstanceId"] == "i-0123456789abcdef0"
    assert provider.ec2.calls == 2
    assert [entry["operation"] for entry in provider.provider_responses] == [
        "describe_instance.effective.error",
        "describe_instance.effective",
    ]


def test_waiter_race_requires_explicit_terminal_confirmation() -> None:
    from types import SimpleNamespace

    class _WaiterFailure(Exception):
        pass

    class _NotFound(Exception):
        response = {"Error": {"Code": "InvalidInstanceID.NotFound"}}

    class _Ec2:
        def get_waiter(self, name):
            assert name == "instance_terminated"

            class _Waiter:
                def wait(self, **kwargs):
                    assert kwargs["InstanceIds"] == ["i-0123456789abcdef0"]
                    raise _WaiterFailure("resource disappeared after pending")

            return _Waiter()

        def describe_instances(self, **kwargs):
            assert kwargs == {"InstanceIds": ["i-0123456789abcdef0"]}
            raise _NotFound()

    provider = object.__new__(aws_surface_provider.AwsSurfaceProvider)
    provider.ec2 = _Ec2()
    provider.provider_responses = []
    provider.config = SimpleNamespace(action_id="FIXTURE-NONSCI-20260805-v2-a1b2c3d4", evidence_dir=None)

    provider._wait_instance_terminated("i-0123456789abcdef0")

    assert [entry["operation"] for entry in provider.provider_responses] == [
        "wait_instance_terminated.error",
        "confirm_instance_terminated.error",
    ]


def test_waiter_failure_is_not_hidden_when_instance_remains_nonterminal() -> None:
    from types import SimpleNamespace

    class _WaiterFailure(Exception):
        pass

    class _Ec2:
        def get_waiter(self, name):
            class _Waiter:
                def wait(self, **kwargs):
                    raise _WaiterFailure("waiter failed")

            return _Waiter()

        def describe_instances(self, **kwargs):
            return {"Reservations": [{"Instances": [{"State": {"Name": "shutting-down"}}]}]}

    provider = object.__new__(aws_surface_provider.AwsSurfaceProvider)
    provider.ec2 = _Ec2()
    provider.provider_responses = []
    provider.config = SimpleNamespace(action_id="FIXTURE-NONSCI-20260805-v2-a1b2c3d4", evidence_dir=None)

    import pytest

    with pytest.raises(_WaiterFailure, match="waiter failed"):
        provider._wait_instance_terminated("i-0123456789abcdef0")


def test_iam_profile_binding_retains_verified_arn_for_ec2_launch() -> None:
    from types import SimpleNamespace

    profile_name = "pneuma-surface-v2-profile-FIXTURE-NONSCI-20260805-v2-a1b2c3d4"
    role_name = "pneuma-surface-v2-role-FIXTURE-NONSCI-20260805-v2-a1b2c3d4"
    profile_arn = f"arn:aws:iam::123456789012:instance-profile/{profile_name}"

    class _Iam:
        def create_role(self, **kwargs):
            return {}

        def put_role_policy(self, **kwargs):
            return {}

        def create_instance_profile(self, **kwargs):
            return {"InstanceProfile": {"Arn": profile_arn}}

        def add_role_to_instance_profile(self, **kwargs):
            return {}

        def tag_role(self, **kwargs):
            return {}

        def tag_instance_profile(self, **kwargs):
            return {}

        def get_instance_profile(self, **kwargs):
            return {"InstanceProfile": {"Arn": profile_arn, "Roles": [{"RoleName": role_name}]}}

    provider = object.__new__(aws_surface_provider.AwsSurfaceProvider)
    provider.iam = _Iam()
    provider.provider_responses = []
    provider.profile_arn = None
    provider.profile_name = profile_name
    provider.role_name = role_name
    provider.policy_name = "pneuma-surface-v2-ecr-FIXTURE-NONSCI-20260805-v2-a1b2c3d4"
    provider.config = SimpleNamespace(
        action_id="FIXTURE-NONSCI-20260805-v2-a1b2c3d4",
        evidence_dir=None,
        image_refs={"controller": "123456789012.dkr.ecr.us-east-1.amazonaws.com/controller@sha256:" + "1" * 64},
    )

    provider._create_iam()

    assert provider.profile_arn == profile_arn


def test_run_admission_retries_only_iam_propagation_and_never_submits(monkeypatch) -> None:
    class _ClientError(Exception):
        def __init__(self, code: str, message: str) -> None:
            self.response = {"Error": {"Code": code, "Message": message}}

    class _Ec2:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def run_instances(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                raise _ClientError("InvalidParameterValue", "iamInstanceProfile is not propagated")
            raise _ClientError("DryRunOperation", "Request would have succeeded, but DryRun flag is set")

    provider = object.__new__(aws_surface_provider.AwsSurfaceProvider)
    provider.ec2 = _Ec2()
    provider.provider_responses = []
    provider.config = type("Config", (), {"evidence_dir": None})()
    monkeypatch.setattr(aws_surface_provider.time, "sleep", lambda seconds: None)

    provider._probe_run_admission({"MinCount": 1, "MaxCount": 1})

    assert len(provider.ec2.calls) == 2
    assert all(call["DryRun"] is True for call in provider.ec2.calls)


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

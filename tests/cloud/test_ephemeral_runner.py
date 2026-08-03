from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from pneuma_lab.cloud.authorization_keys import canonical_ledger_digest
from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.ephemeral_runner import (
    AwsCliAdapter,
    RunnerConfig,
    TerraformAdapter,
    execute,
    require_account_plan,
    terraform_mutation_commands,
)
from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.fixed_admission_probe import build_raw_measurement
from pneuma_lab.cloud.qualification_execution import worker_artifact_uri
from pneuma_lab.cloud.qualification_execution import (
    parse_terraform_show,
    terraform_plan_binding_digest,
    verify_provider_bindings,
)

from .test_qualification_execution import _rungs


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md"
ROLE_ARNS = {
    "pneuma-worker": "arn:aws:iam::123456789012:role/pneuma-worker",
    "pneuma-batch": "arn:aws:iam::123456789012:role/pneuma-batch",
    "pneuma-spot": "arn:aws:iam::123456789012:role/pneuma-spot",
}
PROFILE_ARNS = {
    "pneuma-worker": "arn:aws:iam::123456789012:instance-profile/pneuma-worker"
}


def terraform_show(action_id: str = "qual-1", code: str = "signed-code") -> dict:
    tags = {"QualificationCode": code, "QualificationActionId": action_id}
    subnets = [
        "subnet-0123456789abcdef0",
        "subnet-0123456789abcdef1",
        "subnet-0123456789abcdef2",
        "subnet-0123456789abcdef3",
    ]
    output_path = f"s3://bucket/runs/qualification/{action_id}/outputs/"
    image = "registry.example.invalid/worker@sha256:" + "a" * 64
    return {
        "format_version": "1.0",
        "variables": {
            "region": {"value": "us-east-1"},
            "qualification_code": {"value": code},
            "qualification_action_id": {"value": action_id},
            "instance_role_arn": {"value": PROFILE_ARNS["pneuma-worker"]},
            "batch_service_role_arn": {"value": ROLE_ARNS["pneuma-batch"]},
            "spot_fleet_role_arn": {"value": ROLE_ARNS["pneuma-spot"]},
            "gpu_worker_image": {"value": image},
            "qualification_model": {"value": "fixture-only-cuda"},
            "qualification_model_revision": {"value": "fixture-only-v1"},
            "protocol_path": {"value": output_path.replace("outputs/", "inputs/protocol.json")},
            "architecture_path": {"value": output_path.replace("outputs/", "inputs/architecture.json")},
            "authorization_path": {"value": output_path.replace("outputs/", "inputs/authorization.json")},
            "image_path": {"value": output_path.replace("outputs/", "inputs/image.json")},
            "input_lock_path": {"value": output_path.replace("outputs/", "inputs/input-lock.json")},
            "output_path": {"value": output_path},
            "subnet_ids": {"value": subnets},
            "security_group_ids": {"value": ["sg-0123456789abcdef0"]},
        },
        "planned_values": {
            "root_module": {
                "resources": [
                    {
                        "address": "aws_batch_compute_environment.qualification",
                        "values": {
                            "compute_environment_name": action_id,
                            "tags": tags,
                            "compute_resources": [
                                {
                                    "type": "SPOT",
                                    "allocation_strategy": "SPOT_PRICE_CAPACITY_OPTIMIZED",
                                    "min_vcpus": 0,
                                    "desired_vcpus": 0,
                                    "instance_type": ["g6e.2xlarge"],
                                    "max_vcpus": 16,
                                    "instance_role": PROFILE_ARNS["pneuma-worker"],
                                    "spot_iam_fleet_role": ROLE_ARNS["pneuma-spot"],
                                    "subnets": subnets,
                                    "security_group_ids": ["sg-0123456789abcdef0"],
                                    "tags": tags,
                                    "launch_template": [
                                        {"id": "lt-qualification", "version": "1"}
                                    ],
                                }
                            ],
                            "service_role": ROLE_ARNS["pneuma-batch"],
                        },
                    },
                    {
                        "address": "aws_batch_job_definition.worker",
                        "values": {
                            "name": f"{action_id}-worker",
                            "tags": tags,
                            "timeout": [{"attempt_duration_seconds": 3600}],
                            "retry_strategy": [{"attempts": 1}],
                            "container_properties": json.dumps(
                                {
                                    "image": image,
                                    "resourceRequirements": [
                                        {"type": "GPU", "value": "1"},
                                        {"type": "VCPU", "value": "8"},
                                        {"type": "MEMORY", "value": "60000"},
                                    ],
                                    "environment": [
                                        {"name": "QUALIFICATION_CODE", "value": code},
                                        {
                                            "name": "QUALIFICATION_ACTION_ID",
                                            "value": action_id,
                                        },
                                        {
                                            "name": "QUALIFICATION_ARTIFACT_PREFIX",
                                            "value": output_path,
                                        },
                                        {"name": "QUALIFICATION_MODEL", "value": "fixture-only-cuda"},
                                        {"name": "QUALIFICATION_MODEL_REVISION", "value": "fixture-only-v1"},
                                        {"name": "QUALIFICATION_PROTOCOL", "value": output_path.replace("outputs/", "inputs/protocol.json")},
                                        {"name": "QUALIFICATION_ARCHITECTURE", "value": output_path.replace("outputs/", "inputs/architecture.json")},
                                        {"name": "QUALIFICATION_AUTHORIZATION", "value": output_path.replace("outputs/", "inputs/authorization.json")},
                                        {"name": "QUALIFICATION_IMAGE", "value": output_path.replace("outputs/", "inputs/image.json")},
                                        {"name": "QUALIFICATION_INPUT_LOCK", "value": output_path.replace("outputs/", "inputs/input-lock.json")},
                                        {"name": "QUALIFICATION_OUTPUT_ROOT", "value": output_path},
                                    ]
                                }
                            )
                        },
                    },
                    {
                        "address": "aws_batch_job_queue.qualification",
                        "values": {"name": action_id, "tags": tags},
                    },
                    {
                        "address": "aws_launch_template.qualification",
                        "values": {
                            "image_id": None,
                            "tag_specifications": [
                                {"resource_type": "instance", "tags": tags},
                                {"resource_type": "volume", "tags": tags},
                            ]
                        },
                    },
                ]
            }
        },
        "resource_changes": [
            {
                "address": "aws_batch_compute_environment.qualification",
                "change": {"actions": ["create"]},
            },
            {
                "address": "aws_batch_job_definition.worker",
                "change": {"actions": ["create"]},
            },
            {
                "address": "aws_batch_job_queue.qualification",
                "change": {"actions": ["create"]},
            },
            {
                "address": "aws_launch_template.qualification",
                "change": {"actions": ["create"]},
            },
        ],
        "saved_plan_sha256": hashlib.sha256(b"fixture-saved-plan").hexdigest(),
    }


class ReadOnlyProvider:
    def get_caller_identity(self):
        return {
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:role/reader",
        }

    def get_role(self, role_name):
        return {"Role": {"RoleName": role_name, "Arn": ROLE_ARNS[role_name]}}

    def get_instance_profile(self, profile_name):
        return {
            "InstanceProfile": {
                "InstanceProfileName": profile_name,
                "Arn": PROFILE_ARNS[profile_name],
                "Roles": [
                    {
                        "RoleName": "pneuma-worker",
                        "Arn": ROLE_ARNS["pneuma-worker"],
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
            {"GroupId": group_id, "VpcId": "vpc-12345678", "IpPermissions": []}
            for group_id in group_ids
        ]


@dataclass
class FakeProvider(ReadOnlyProvider):
    calls: list[str] = field(default_factory=list)
    projection: float = 99.0

    def preflight(self, tags):
        self.calls.append("preflight")
        return {"ok": True}

    def wait_ready(self, tags):
        self.calls.append("ready")
        return {"compute_environment_status": "VALID", "queue_status": "VALID"}

    def pricing_projection(self, *, worker_seconds):
        self.calls.append("pricing")
        return self.projection

    def compile_fixture_evidence(self, evidence):
        return {0: {"worker_index": 0}, 1: {"worker_index": 1}}

    def submit_array(self, *, size, timeout_seconds, attempts, tags):
        self.calls.append(f"submit:{size}:{timeout_seconds}:{attempts}")
        return "parent"

    def collect_admission(self, parent_job_id):
        self.calls.append("collect")
        children = tuple(
            {
                "jobId": f"child-{index}",
                "status": "SUCCEEDED",
                "arrayProperties": {"index": index},
                "attempts": [{}],
            }
            for index in (0, 1)
        )
        return {
            "parent_status": "SUCCEEDED",
            "children": children,
            "instance_ids": ("i-worker-0", "i-worker-1"),
            "raw_evidence": {0: b"raw-0", 1: b"raw-1"},
        }

    def run_partition_recovery(self, parent_job_id):
        self.calls.append("recovery")
        return {
            "restored_completed_boundary": True,
            "operations": (
                "describe_jobs_before",
                "freeze_completed_boundary",
                "restore_completed_boundary",
                "describe_jobs_after",
            ),
            "freeze": {"requested": True, "completed": True},
            "restore": {"requested": True, "completed": True},
        }

    def disable_and_drain(self, tags):
        self.calls.append("disable-drain")

    def verify_absence(self, tags):
        self.calls.append("absence")
        return {
            key: True
            for key in (
                "jobs",
                "instances",
                "volumes",
                "launch_template",
                "network_interfaces",
                "security_group",
                "job_definition",
                "queue",
                "compute_environment",
            )
        }


@dataclass
class FakeTerraform:
    calls: list[str] = field(default_factory=list)

    def apply(self, *, lock_timeout, tags):
        self.calls.append(f"apply:{lock_timeout}")

    def destroy(self, *, lock_timeout, tags):
        self.calls.append(f"destroy:{lock_timeout}")


def authority(*args, **kwargs):
    assert kwargs["expected_manifest_sha256"] == terraform_plan_binding_digest(
        hashlib.sha256(b"fixture-saved-plan").hexdigest(),
        parse_terraform_show(terraform_show())["terraform_show_sha256"],
    )
    assert kwargs["spend_history_sha256"] == canonical_ledger_digest(LEDGER)
    return {"authorized": True}


def test_runner_verifies_real_plan_and_executes_exact_two_children() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()
    result = execute(
        RunnerConfig("qual-1", "us-east-1"),
        envelope={},
        admission={},
        key_registry={},
        ledger_path=LEDGER,
        account_plan=terraform_show(),
        provider=provider,
        terraform=terraform,
        verify_authority=authority,
    )
    assert result["qualification_only"] is True
    assert provider.calls == [
        "pricing",
        "preflight",
        "ready",
        "submit:2:3600:1",
        "collect",
        "recovery",
        "disable-drain",
        "absence",
    ]
    assert terraform.calls == ["apply:60s", "destroy:60s"]
    assert provider.calls[-2:] == ["disable-drain", "absence"]


def test_invented_account_plan_fields_are_not_accepted() -> None:
    provider = FakeProvider()
    with pytest.raises(CloudManifestError, match="format_version"):
        require_account_plan(
            {
                "resource_changes": [],
                "approved_existing_inputs": {
                    "roles": True,
                    "subnets": True,
                    "security_groups": True,
                },
            },
            provider=provider,
        )


def test_loaded_account_plan_preserves_raw_show_binding() -> None:
    candidate = terraform_show()
    candidate["saved_plan_sha256"] = "a" * 64
    candidate["terraform_show_sha256"] = "b" * 64
    parsed = require_account_plan(candidate, provider=ReadOnlyProvider())
    assert parsed["terraform_show_sha256"] == "b" * 64
    assert parsed["terraform_plan_binding_sha256"] == terraform_plan_binding_digest(
        "a" * 64, "b" * 64
    )


def test_instance_profile_is_verified_before_its_attached_role() -> None:
    plan = parse_terraform_show(terraform_show())
    provider = ReadOnlyProvider()

    verified = verify_provider_bindings(provider, plan)

    assert verified["instance_profile"]["Arn"] == PROFILE_ARNS["pneuma-worker"]
    assert verified["role"]["Arn"] == ROLE_ARNS["pneuma-worker"]
    assert verified["service_role"]["Arn"] == ROLE_ARNS["pneuma-batch"]
    assert verified["spot_fleet_role"]["Arn"] == ROLE_ARNS["pneuma-spot"]


def test_role_arn_cannot_substitute_for_the_planned_instance_profile() -> None:
    candidate = terraform_show()
    candidate["variables"]["instance_role_arn"]["value"] = ROLE_ARNS[
        "pneuma-worker"
    ]
    candidate["planned_values"]["root_module"]["resources"][0]["values"][
        "compute_resources"
    ][0]["instance_role"] = ROLE_ARNS["pneuma-worker"]

    with pytest.raises(CloudManifestError, match="instance profile"):
        parse_terraform_show(candidate)


@pytest.mark.parametrize("role_count", [0, 2])
def test_instance_profile_requires_exactly_one_attached_role(role_count: int) -> None:
    plan = parse_terraform_show(terraform_show())
    provider = ReadOnlyProvider()
    original = provider.get_instance_profile

    def profile_with_wrong_cardinality(profile_name):
        response = original(profile_name)
        response["InstanceProfile"]["Roles"] = [
            response["InstanceProfile"]["Roles"][0]
        ] * role_count
        return response

    provider.get_instance_profile = profile_with_wrong_cardinality  # type: ignore[method-assign]
    with pytest.raises(CloudManifestError, match="exactly one attached role"):
        verify_provider_bindings(provider, plan)


def test_subnets_and_security_group_must_share_the_verified_vpc() -> None:
    plan = parse_terraform_show(terraform_show())
    provider = ReadOnlyProvider()
    original = provider.describe_security_groups

    def groups_in_wrong_vpc(group_ids):
        rows = original(group_ids)
        for row in rows:
            row["VpcId"] = "vpc-wrong"
        return rows

    provider.describe_security_groups = groups_in_wrong_vpc  # type: ignore[method-assign]
    with pytest.raises(CloudManifestError, match="security-group VPC"):
        verify_provider_bindings(provider, plan)


def test_ephemeral_plan_guard_rejects_a_plan_without_its_launch_template() -> None:
    candidate = terraform_show()
    candidate["resource_changes"] = [
        change
        for change in candidate["resource_changes"]
        if change["address"] != "aws_launch_template.qualification"
    ]
    with pytest.raises(CloudManifestError, match="exactly four creates"):
        require_account_plan(candidate, provider=ReadOnlyProvider())


def test_action_mismatch_is_read_before_any_mutation() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()
    with pytest.raises(CloudManifestError, match="action"):
        execute(
            RunnerConfig("different-action", "us-east-1"),
            envelope={},
            admission={},
            key_registry={},
            ledger_path=LEDGER,
            account_plan=terraform_show(),
            provider=provider,
            terraform=terraform,
            verify_authority=authority,
        )
    assert provider.calls == [] and terraform.calls == []


def test_cost_bound_is_fail_closed() -> None:
    provider, terraform = FakeProvider(projection=100.01), FakeTerraform()
    with pytest.raises(CloudManifestError, match="USD 100"):
        execute(
            RunnerConfig("qual-1", "us-east-1"),
            envelope={},
            admission={},
            key_registry={},
            ledger_path=LEDGER,
            account_plan=terraform_show(),
            provider=provider,
            terraform=terraform,
            verify_authority=authority,
        )


def test_future_terraform_mutations_use_lock_timeout_not_lock_false() -> None:
    apply, destroy = terraform_mutation_commands()
    assert "-lock=false" not in apply + destroy
    assert "-lock-timeout=60s" in apply and "-lock-timeout=60s" in destroy


def test_apply_failure_still_attempts_destroy_and_absence_readback() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()

    def fail_apply(*, lock_timeout, tags):
        terraform.calls.append(f"apply:{lock_timeout}")
        raise RuntimeError("partial apply")

    terraform.apply = fail_apply  # type: ignore[method-assign]
    with pytest.raises(CloudManifestError, match="qualification failed closed"):
        execute(
            RunnerConfig("qual-1", "us-east-1"),
            envelope={},
            admission={},
            key_registry={},
            ledger_path=LEDGER,
            account_plan=terraform_show(),
            provider=provider,
            terraform=terraform,
            verify_authority=authority,
        )
    assert terraform.calls == ["apply:60s", "destroy:60s"]


def test_concrete_provider_arguments_are_bound_to_the_saved_plan() -> None:
    plan = parse_terraform_show(terraform_show())
    provider = AwsCliAdapter(
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, b"{}", b""),
        region="us-east-1",
        queue="wrong-queue",
        job_definition="qual-1-worker",
        compute_environment="qual-1",
        output_root=plan["output_path"],
    )
    with pytest.raises(CloudManifestError, match="queue"):
        provider.bind_qualification_plan(plan)


def test_terraform_adapter_parses_show_json_before_future_apply() -> None:
    plan_path = Path("saved.tfplan")
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if argv[2] == "show":
            return subprocess.CompletedProcess(
                argv, 0, json.dumps(terraform_show()).encode(), b""
            )
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    try:
        plan_path.write_bytes(b"exact-plan-bytes")
        adapter = TerraformAdapter(run)
        plan = adapter.load_account_plan(plan_path)
        expected_show_sha256 = hashlib.sha256(
            json.dumps(terraform_show()).encode()
        ).hexdigest()
        assert plan["terraform_show_sha256"] == expected_show_sha256
        assert plan["saved_plan_sha256"] == hashlib.sha256(
            b"exact-plan-bytes"
        ).hexdigest()
        assert "plan_sha256" not in plan
        adapter.apply(lock_timeout="60s", tags={})
        assert calls[0][2:4] == ["show", "-json"]
        assert str(plan_path) in calls[1]
        assert calls[1][2:4] == ["show", "-json"]
        assert str(plan_path) in calls[2]
        assert "-lock=false" not in calls[2]
        plan_path.write_bytes(b"tampered-plan-bytes")
        with pytest.raises(CloudManifestError, match="plan bytes"):
            adapter.apply(lock_timeout="60s", tags={})
        assert len(calls) == 3
    finally:
        plan_path.unlink(missing_ok=True)


def test_aws_adapter_submission_is_one_tagged_size_two_array_without_command() -> None:
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, b'{"jobId":"parent"}', b"")

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="q",
        job_definition="d",
        output_root="s3://bucket/run",
    )
    assert (
        adapter.submit_array(
            size=2,
            timeout_seconds=3600,
            attempts=1,
            tags={"QualificationAction": "qual-1", "QualificationActionId": "qual-1"},
        )
        == "parent"
    )
    command = " ".join(calls[0])
    assert calls[0][:2] == ["aws", "batch"]
    assert calls[0].count("aws") == 1
    assert '--array-properties {"size":2}' in command
    assert '--retry-strategy {"attempts":1}' in command
    assert "qual-1" in command
    assert "command" not in command


def test_concrete_cli_waits_for_valid_environment_and_queue() -> None:
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if "describe-compute-environments" in argv:
            payload = {"computeEnvironments": [{"status": "VALID"}]}
        else:
            payload = {"jobQueues": [{"status": "VALID"}]}
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload).encode(), b"")

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="q",
        job_definition="d",
        output_root="s3://bucket/runs/qual-1",
        compute_environment="ce",
    )
    assert adapter.wait_ready({}) == {
        "compute_environment_status": "VALID",
        "queue_status": "VALID",
    }
    assert any("describe-compute-environments" in call for call in calls)
    assert any("describe-job-queues" in call for call in calls)


def test_concrete_cli_absence_checks_all_ephemeral_resource_classes() -> None:
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        payloads = {
            "describe-job-queues": {"jobQueues": []},
            "describe-compute-environments": {"computeEnvironments": []},
            "describe-job-definitions": {"jobDefinitions": []},
            "describe-instances": {"Reservations": []},
            "describe-volumes": {"Volumes": []},
            "describe-launch-templates": {"LaunchTemplates": []},
            "describe-network-interfaces": {"NetworkInterfaces": []},
            "describe-security-groups": {"SecurityGroups": []},
        }
        command = next(key for key in payloads if key in argv)
        return subprocess.CompletedProcess(
            argv, 0, json.dumps(payloads[command]).encode(), b""
        )

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="qual-1",
        job_definition="qual-1-worker",
        output_root="s3://bucket/runs/qual-1",
    )
    assert adapter.verify_absence({"QualificationActionId": "qual-1"}) == {
        "jobs": True,
        "instances": True,
        "volumes": True,
        "launch_template": True,
        "network_interfaces": True,
        "security_group": True,
        "job_definition": True,
        "queue": True,
        "compute_environment": True,
    }
    assert any(
        "Name=launch-template-name,Values=qual-1-worker-*" in call
        for call in calls
    )
    assert any("describe-network-interfaces" in call for call in calls)


def test_concrete_cli_absence_accepts_deleted_queue_and_environment() -> None:
    def run(argv, **kwargs):
        if "describe-job-queues" in argv or "describe-compute-environments" in argv:
            return subprocess.CompletedProcess(
                argv,
                254,
                b"",
                b"ResourceNotFoundException: deleted",
            )
        command = next(
            command
            for command in (
                "describe-job-definitions",
                "describe-instances",
                "describe-volumes",
                "describe-launch-templates",
                "describe-network-interfaces",
                "describe-security-groups",
            )
            if command in argv
        )
        collection = {
            "describe-job-definitions": "jobDefinitions",
            "describe-instances": "Reservations",
            "describe-volumes": "Volumes",
            "describe-launch-templates": "LaunchTemplates",
            "describe-network-interfaces": "NetworkInterfaces",
            "describe-security-groups": "SecurityGroups",
        }[command]
        return subprocess.CompletedProcess(
            argv, 0, json.dumps({collection: []}).encode(), b""
        )

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="qual-1",
        job_definition="qual-1-worker",
        output_root="s3://bucket/runs/qual-1",
    )
    assert all(
        adapter.verify_absence({"QualificationActionId": "qual-1"}).values()
    )


def test_concrete_cli_absence_accepts_terminal_job_history_and_inactive_definition() -> None:
    def run(argv, **kwargs):
        if "describe-job-queues" in argv or "describe-compute-environments" in argv:
            return subprocess.CompletedProcess(
                argv,
                254,
                b"",
                b"ResourceNotFoundException: deleted",
            )
        if "describe-jobs" in argv:
            return subprocess.CompletedProcess(
                argv,
                0,
                b'{"jobs":[{"jobId":"parent","status":"FAILED"}]}',
                b"",
            )
        if "describe-job-definitions" in argv:
            status = argv[argv.index("--status") + 1]
            payload = (
                {"jobDefinitions": []}
                if status == "ACTIVE"
                else {
                    "jobDefinitions": [
                        {
                            "jobDefinitionArn": "arn:aws:batch:example:job-definition/qual-1-worker:1",
                            "status": "INACTIVE",
                        }
                    ]
                }
            )
            return subprocess.CompletedProcess(
                argv, 0, json.dumps(payload).encode(), b""
            )
        command = next(
            command
            for command in (
                "describe-instances",
                "describe-volumes",
                "describe-launch-templates",
                "describe-network-interfaces",
                "describe-security-groups",
            )
            if command in argv
        )
        collection = {
            "describe-instances": "Reservations",
            "describe-volumes": "Volumes",
            "describe-launch-templates": "LaunchTemplates",
            "describe-network-interfaces": "NetworkInterfaces",
            "describe-security-groups": "SecurityGroups",
        }[command]
        return subprocess.CompletedProcess(
            argv, 0, json.dumps({collection: []}).encode(), b""
        )

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="qual-1",
        job_definition="qual-1-worker",
        output_root="s3://bucket/runs/qual-1",
    )
    adapter.parent_job_id = "parent"
    absence = adapter.verify_absence({"QualificationActionId": "qual-1"})
    assert all(absence.values())
    assert absence["jobs"] is True
    assert absence["job_definition"] is True


def test_concrete_cli_absence_does_not_swallow_unrelated_provider_errors() -> None:
    def run(argv, **kwargs):
        return subprocess.CompletedProcess(
            argv,
            254,
            b"",
            b"ClientException: invalid parameter",
        )

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="qual-1",
        job_definition="qual-1-worker",
        output_root="s3://bucket/runs/qual-1",
    )
    with pytest.raises(CloudManifestError, match="absence read failed"):
        adapter.verify_absence({"QualificationActionId": "qual-1"})


def test_concrete_cli_adapter_accepts_only_two_succeeded_first_attempt_children(
    tmp_path: Path,
) -> None:
    source = tmp_path / "input.json"
    source.write_text("{}", encoding="utf-8")
    raw_objects = {}
    for index in (0, 1):
        measurement = build_raw_measurement(
            code="signed-code",
            worker_index=index,
            instance_id=f"i-0123456789abcdef{index}",
            protocol_sha256="a" * 64,
            architecture_sha256="b" * 64,
            authorization_sha256="c" * 64,
            image_sha256="d" * 64,
            input_lock_sha256="e" * 64,
            code_sha256="f" * 64,
            input_paths=[source],
            rungs=_rungs(),
        )
        raw_objects[worker_artifact_uri("s3://bucket/runs/qual-1", index)] = (
            canonical_bytes(measurement) + b"\n"
        )

    class Objects:
        def get_object(self, bucket, key):
            return raw_objects[f"s3://{bucket}/{key}"]

    def run(argv, **kwargs):
        job_id = argv[argv.index("--jobs") + 1]
        if job_id == "parent":
            payload = {"jobs": [{"jobId": "parent", "status": "SUCCEEDED"}]}
        else:
            index = int(job_id.rsplit(":", 1)[1])
            payload = {
                "jobs": [
                    {
                        "jobId": job_id,
                        "status": "SUCCEEDED",
                        "arrayProperties": {"index": index},
                        "attempts": [{}],
                        "container": {"instanceId": f"i-0123456789abcdef{index}"},
                    }
                ]
            }
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload).encode(), b"")

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="q",
        job_definition="d",
        output_root="s3://bucket/runs/qual-1",
        transport=Objects(),
    )
    evidence = adapter.collect_admission("parent")
    assert evidence["instance_ids"] == (
        "i-0123456789abcdef0",
        "i-0123456789abcdef1",
    )
    assert set(evidence["raw_evidence"]) == {0, 1}

    def failed_run(argv, **kwargs):
        payload = {"jobs": [{"jobId": "parent", "status": "SUCCEEDED"}]}
        if argv[argv.index("--jobs") + 1] != "parent":
            payload = {
                "jobs": [
                    {
                        "jobId": argv[argv.index("--jobs") + 1],
                        "status": "FAILED",
                        "arrayProperties": {"index": 0},
                        "attempts": [{}],
                        "container": {"instanceId": "i-0123456789abcdef0"},
                    }
                ]
            }
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload).encode(), b"")

    failed = AwsCliAdapter(
        failed_run,
        region="us-east-1",
        queue="q",
        job_definition="d",
        output_root="s3://bucket/runs/qual-1",
        transport=Objects(),
    )
    with pytest.raises(CloudManifestError, match="SUCCEEDED"):
        failed.collect_admission("parent")


def test_concrete_cli_recovery_rejects_a_bare_describe_success() -> None:
    def describe_only(argv, **kwargs):
        return subprocess.CompletedProcess(
            argv,
            0,
            b'{"jobs":[{"jobId":"parent","status":"SUCCEEDED"}]}',
            b"",
        )

    adapter = AwsCliAdapter(
        describe_only,
        region="us-east-1",
        queue="q",
        job_definition="d",
        output_root="s3://bucket/runs/qual-1",
    )
    with pytest.raises(CloudManifestError, match="materialize|restore|boundary"):
        adapter.run_partition_recovery("parent")

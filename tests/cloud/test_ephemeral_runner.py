from __future__ import annotations

from dataclasses import dataclass, field
import base64
import hashlib
import json
from pathlib import Path
import subprocess

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pneuma_lab.cloud.authorization_keys import canonical_ledger_digest
from pneuma_lab.cloud.authorization_keys import canonical_bytes, signed_body
from pneuma_lab.cloud.ephemeral_runner import (
    AwsCliAdapter,
    QualificationExecutionError,
    RunnerConfig,
    TerraformAdapter,
    _require_resource_contract,
    execute,
    require_account_plan,
    require_fresh_qualification_action,
    terraform_mutation_commands,
)
from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.fixed_admission_probe import build_raw_measurement
from pneuma_lab.cloud.iam_simulation import (
    expected_checks,
    run_iam_simulation,
    validate_worker_policy_documents,
)
from pneuma_lab.cloud.qualification_execution import worker_artifact_uri
from pneuma_lab.cloud.qualification_execution import (
    BatchAdmissionError,
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


def kms_verification_record() -> dict[str, object]:
    record: dict[str, object] = {
        "signing_algorithm": "ED25519_SHA_512",
        "envelope_signature_valid": True,
        "admission_signature_valid": True,
        "key_id_sha256": "1" * 64,
        "registry_key_id": "pneuma-kms-20260801-r1",
        "public_key_sha256": "2" * 64,
    }
    record["verification_sha256"] = hashlib.sha256(canonical_bytes(record)).hexdigest()
    return record


def terraform_show(action_id: str = "qual-1", code: str = "signed-code") -> dict:
    tags = {
        "QualificationCode": code,
        "QualificationAction": action_id,
        "QualificationActionId": action_id,
    }
    subnets = [
        "subnet-0123456789abcdef0",
        "subnet-0123456789abcdef1",
        "subnet-0123456789abcdef2",
        "subnet-0123456789abcdef3",
    ]
    output_path = f"s3://bucket/runs/qualification/{action_id}/outputs/"
    image = "registry.example.invalid/worker@sha256:" + "a" * 64
    plan = {
        "format_version": "1.0",
        "variables": {
            "region": {"value": "us-east-1"},
            "vpc_id": {"value": "vpc-12345678"},
            "name_prefix": {"value": action_id},
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
        "configuration": {
            "root_module": {
                "resources": [
                    {
                        "address": "aws_batch_compute_environment.qualification",
                        "expressions": {
                            "compute_resources": [
                                {
                                    "launch_template": [
                                        {
                                            "launch_template_id": {
                                                "references": [
                                                    "aws_launch_template.qualification.id"
                                                ]
                                            },
                                            "version": {
                                                "references": [
                                                    "aws_launch_template.qualification.latest_version"
                                                ]
                                            },
                                        }
                                    ]
                                }
                            ]
                        },
                    },
                    {
                        "address": "aws_batch_job_queue.qualification",
                        "expressions": {
                            "compute_environment_order": [
                                {
                                    "compute_environment": {
                                        "references": [
                                            "aws_batch_compute_environment.qualification.arn"
                                        ]
                                    }
                                }
                            ]
                        },
                    },
                ]
            }
        },
        "planned_values": {
            "root_module": {
                "resources": [
                    {
                        "address": "aws_batch_compute_environment.qualification",
                        "values": {
                            "compute_environment_name": action_id,
                            "type": "MANAGED",
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
                            "type": "container",
                            "platform_capabilities": ["EC2"],
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
                        "values": {
                            "name": action_id,
                            "compute_environment_order": [{"order": 1}],
                            "tags": tags,
                        },
                    },
                    {
                        "address": "aws_launch_template.qualification",
                        "values": {
                            "id": "lt-qualification",
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
    plan["terraform_show_sha256"] = parse_terraform_show(plan)["terraform_show_sha256"]
    plan["terraform_plan_binding_sha256"] = terraform_plan_binding_digest(
        plan["saved_plan_sha256"], plan["terraform_show_sha256"]
    )
    plan["_qualification"] = {
        "saved_plan_sha256": plan["saved_plan_sha256"],
        "terraform_show_sha256": plan["terraform_show_sha256"],
        "terraform_plan_binding_sha256": plan["terraform_plan_binding_sha256"],
    }
    return plan


class ReadOnlyProvider:
    def get_caller_identity(self):
        return {
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:role/reader",
        }

    def get_role(self, role_name):
        role_ids = {
            "pneuma-worker": "AROAWORKER00000000001",
            "pneuma-batch": "AROABATCH000000000002",
            "pneuma-spot": "AROSPOT0000000000003",
        }
        return {
            "Role": {
                "RoleName": role_name,
                "Arn": ROLE_ARNS[role_name],
                "RoleId": role_ids[role_name],
            }
        }

    def get_instance_profile(self, profile_name):
        return {
            "InstanceProfile": {
                "InstanceProfileName": profile_name,
                "Arn": PROFILE_ARNS[profile_name],
                "Roles": [
                    {
                        "RoleName": "pneuma-worker",
                        "Arn": ROLE_ARNS["pneuma-worker"],
                        "RoleId": "AROAWORKER00000000001",
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

    def capture_iam_simulation(self, *, plan, action_id, expected_policy_sha256):
        self.calls.append("iam")
        checks = expected_checks(
            input_paths=plan["input_paths"],
            output_root=plan["output_path"],
            iam_role_arn=plan["worker_role_arn"],
        )
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "s3:GetObject",
                    "Resource": [
                        row["resource_arn"]
                        for row in checks
                        if row["id"].startswith("input-read-")
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": "s3:PutObject",
                    "Resource": [
                        row["resource_arn"]
                        for row in checks
                        if row["id"].startswith("raw-write-")
                    ],
                },
            ],
        }
        policy_inventory = validate_worker_policy_documents(
            (("inline", "bounded-experiment-access", policy),),
            input_paths=plan["input_paths"],
            output_root=plan["output_path"],
            iam_role_arn=plan["worker_role_arn"],
        )

        def call(*args):
            action = args[args.index("--action-names") + 1]
            resource = args[args.index("--resource-arns") + 1]
            expected = next(
                row
                for row in checks
                if row["action"] == action and row["resource_arn"] == resource
            )
            return {
                "EvaluationResults": [
                    {
                        "EvalActionName": action,
                        "EvalResourceName": resource,
                        "EvalDecision": (
                            "allowed"
                            if expected["expected"] == "allowed"
                            else "implicitDeny"
                        ),
                    }
                ]
            }

        return run_iam_simulation(
            call,
            plan=plan,
            action_id=action_id,
            expected_policy_sha256=expected_policy_sha256,
            policy_inventory=policy_inventory,
        )

    def preflight(self, tags):
        self.calls.append("preflight")
        return {"provider_absence": self._absence_evidence()}

    def wait_ready(self, tags):
        self.calls.append("ready")
        return {"compute_environment_status": "VALID", "queue_status": "VALID"}

    def pricing_projection(self, *, worker_seconds):
        self.calls.append("pricing")
        return self.projection

    def compile_fixture_evidence(self, evidence):
        return {0: {"worker_index": 0}, 1: {"worker_index": 1}}

    def capture_kms_verification(self, *, envelope, admission, key_registry, authority):
        self.calls.append("kms")
        return kms_verification_record()

    def submit_array(self, *, size, timeout_seconds, attempts, tags):
        self.calls.append(f"submit:{size}:{timeout_seconds}:{attempts}")
        return "parent"

    def capture_submit_evidence(self, parent_job_id):
        self.calls.append("cloudtrail")
        return {
            "cloudtrail_submit_job_event_id_sha256": "c" * 64,
            "submit_event_time_utc": "2026-08-03T09:34:48Z",
            "submit_count_proven": 1,
            "array_size": 2,
            "retry_attempts": 1,
        }

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
        return self._absence_evidence()

    @staticmethod
    def _absence_evidence():
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
        } | {
            "provider_history": {
                "inactive_job_definition_history_retained_by_aws": False,
                "inactive_job_definition_arn_sha256": None,
            },
            "artifact_prefix": {"empty": True, "object_count": 0},
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
    return {
        "authorized": True,
        "iam_policy_sha256": "a" * 64,
        "kms": {
            "key_alias": "alias/pneuma-approver",
            "registry_key_id": "pneuma-kms-20260801-r1",
        },
    }


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
    assert result["launch"]["submit_count_proven"] == 0
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


def test_runner_requires_complete_preflight_absence_before_apply() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()
    provider.preflight = lambda tags: {"ok": True}  # type: ignore[method-assign]
    with pytest.raises(CloudManifestError, match="absence proof"):
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
    assert terraform.calls == []


def test_runner_rejects_nonempty_output_prefix_after_teardown() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()

    def nonempty_absence(tags):
        provider.calls.append("absence")
        proof = provider._absence_evidence()
        proof["artifact_prefix"] = {"empty": False, "object_count": 1}
        return proof

    provider.verify_absence = nonempty_absence  # type: ignore[method-assign]
    with pytest.raises(
        QualificationExecutionError,
        match="absence validation failed closed",
    ) as raised:
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
    assert raised.value.context["absence"]["artifact_prefix"] == {
        "empty": False,
        "object_count": 1,
    }
    assert terraform.calls == ["apply:60s", "destroy:60s"]


def test_runner_retains_context_when_absence_validation_fails() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()

    def incomplete_absence(tags):
        provider.calls.append("absence")
        return {"jobs": True}

    provider.verify_absence = incomplete_absence  # type: ignore[method-assign]
    with pytest.raises(
        QualificationExecutionError,
        match="absence validation failed closed",
    ) as raised:
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
    context = raised.value.context
    assert context["parent_job_id"] == "parent"
    assert context["evidence"]["parent_status"] == "SUCCEEDED"
    assert context["absence"] == {"jobs": True}
    assert terraform.calls == ["apply:60s", "destroy:60s"]


def test_receipt_runner_captures_and_validates_live_iam_before_apply() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()
    result = execute(
        RunnerConfig("qual-1", "us-east-1", require_receipt_evidence=True),
        envelope={},
        admission={},
        key_registry={},
        ledger_path=LEDGER,
        account_plan=terraform_show(),
        provider=provider,
        terraform=terraform,
        verify_authority=authority,
    )
    assert result["iam_simulation"]["all_expected_decisions_match"] is True
    assert provider.calls.index("iam") < provider.calls.index("ready")
    assert terraform.calls == ["apply:60s", "destroy:60s"]


def test_exhausted_action_id_is_rejected_before_provider_calls(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    (evidence_root / "qual-1-terminal-receipt.json").write_text("{}", encoding="utf-8")
    provider, terraform = FakeProvider(), FakeTerraform()
    with pytest.raises(CloudManifestError, match="already represented"):
        execute(
            RunnerConfig(
                "qual-1",
                "us-east-1",
                action_evidence_root=evidence_root,
            ),
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


def test_fresh_action_id_does_not_match_a_longer_retained_action(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    (evidence_root / "qual-10-terminal-receipt.json").write_text("{}", encoding="utf-8")
    require_fresh_qualification_action("qual-1", evidence_root=evidence_root)


def test_exhausted_action_id_is_found_in_nested_evidence_path(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    nested = evidence_root / "qual-1" / "receipt"
    nested.mkdir(parents=True)
    (nested / "terminal.json").write_text("{}", encoding="utf-8")
    with pytest.raises(CloudManifestError, match="already represented"):
        require_fresh_qualification_action("qual-1", evidence_root=evidence_root)


def test_exhausted_action_id_uses_the_same_token_boundary_in_the_ledger(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "ledger.md"
    ledger.write_text(
        "| prior-dual-l40s-qualification-011 | failed |\n",
        encoding="utf-8",
    )
    with pytest.raises(CloudManifestError, match="already represented"):
        require_fresh_qualification_action(
            "dual-l40s-qualification-011",
            evidence_root=tmp_path / "evidence",
            ledger_path=ledger,
        )


def test_fresh_action_allows_its_nonterminal_plan_and_authority_records(
    tmp_path: Path,
) -> None:
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    action_id = "dual-l40s-qualification-012"
    (evidence_root / f"{action_id}-read-only-plan.json").write_text("{}", encoding="utf-8")
    (evidence_root / f"{action_id}-authority-receipt.json").write_text("{}", encoding="utf-8")
    ledger = tmp_path / "ledger.md"
    ledger.write_text(
        f"| CL-1 | now | AWS | Read-only account-plan validation for `{action_id}` | x | y |\n"
        f"| CL-2 | now | AWS | Exact one-use qualification admission for `{action_id}` | x | y |\n",
        encoding="utf-8",
    )
    require_fresh_qualification_action(
        action_id,
        evidence_root=evidence_root,
        ledger_path=ledger,
    )


def test_fresh_action_rejects_terminal_evidence_and_ledger_records(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    action_id = "dual-l40s-qualification-012"
    (evidence_root / f"{action_id}-execution-receipt.json").write_text("{}", encoding="utf-8")
    with pytest.raises(CloudManifestError, match="already represented"):
        require_fresh_qualification_action(action_id, evidence_root=evidence_root)

    evidence_root = tmp_path / "other-evidence"
    evidence_root.mkdir()
    ledger = tmp_path / "terminal-ledger.md"
    ledger.write_text(
        f"| CL-3 | now | AWS | Failed exact action `{action_id}` | x | y |\n",
        encoding="utf-8",
    )
    with pytest.raises(CloudManifestError, match="already represented"):
        require_fresh_qualification_action(
            action_id,
            evidence_root=evidence_root,
            ledger_path=ledger,
        )


def test_default_action_freshness_is_checked_before_provider_calls() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()
    with pytest.raises(CloudManifestError, match="already represented"):
        execute(
            RunnerConfig("dual-l40s-qualification-011", "us-east-1"),
            envelope={},
            admission={},
            key_registry={},
            ledger_path=LEDGER,
            account_plan=terraform_show("dual-l40s-qualification-011"),
            provider=provider,
            terraform=terraform,
            verify_authority=authority,
        )
    assert provider.calls == [] and terraform.calls == []


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
    candidate["_qualification"]["terraform_show_sha256"] = "b" * 64
    candidate["_qualification"]["saved_plan_sha256"] = "a" * 64
    candidate["terraform_plan_binding_sha256"] = terraform_plan_binding_digest(
        "a" * 64, "b" * 64
    )
    candidate["_qualification"]["terraform_plan_binding_sha256"] = candidate[
        "terraform_plan_binding_sha256"
    ]
    parsed = require_account_plan(candidate, provider=ReadOnlyProvider())
    assert parsed["terraform_show_sha256"] == "b" * 64
    assert parsed["terraform_plan_binding_sha256"] == terraform_plan_binding_digest(
        "a" * 64, "b" * 64
    )


def test_loaded_account_plan_rejects_nonhex_saved_plan_binding() -> None:
    candidate = terraform_show()
    candidate["saved_plan_sha256"] = "g" * 64
    with pytest.raises(CloudManifestError, match="saved Terraform plan SHA-256"):
        require_account_plan(candidate, provider=ReadOnlyProvider())


def test_loaded_account_plan_rejects_conflicting_nested_saved_plan_binding() -> None:
    candidate = terraform_show()
    candidate["_qualification"]["saved_plan_sha256"] = "b" * 64
    with pytest.raises(CloudManifestError, match="conflicting saved"):
        require_account_plan(candidate, provider=ReadOnlyProvider())


def test_loaded_account_plan_rejects_conflicting_composite_binding() -> None:
    candidate = terraform_show()
    candidate["_qualification"]["terraform_plan_binding_sha256"] = "b" * 64
    with pytest.raises(CloudManifestError, match="conflicting composite"):
        require_account_plan(candidate, provider=ReadOnlyProvider())


def test_missing_show_binding_fails_closed_with_cloud_error() -> None:
    candidate = terraform_show()
    candidate["terraform_show_sha256"] = "not-a-digest"
    candidate["_qualification"] = {"terraform_show_sha256": "also-not-a-digest"}
    with pytest.raises(CloudManifestError, match="requires both exact"):
        require_account_plan(candidate, provider=ReadOnlyProvider())


def test_conflicting_show_bindings_fail_closed_with_cloud_error() -> None:
    candidate = terraform_show()
    candidate["_qualification"] = {"terraform_show_sha256": "b" * 64}
    candidate["_qualification"]["saved_plan_sha256"] = candidate[
        "saved_plan_sha256"
    ]
    with pytest.raises(
        CloudManifestError,
        match="conflicting Terraform show SHA-256",
    ):
        require_account_plan(candidate, provider=ReadOnlyProvider())


def test_missing_nested_show_binding_fails_closed() -> None:
    candidate = terraform_show()
    candidate.pop("_qualification")
    with pytest.raises(CloudManifestError, match="requires both exact"):
        require_account_plan(candidate, provider=ReadOnlyProvider())


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


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("type", "UNMANAGED", "AWS Batch managed"),
        ("image_id", "ami-custom", "managed GPU AMI"),
    ],
)
def test_ephemeral_plan_guard_rejects_unmanaged_or_custom_ami(
    field: str,
    value: str,
    message: str,
) -> None:
    candidate = terraform_show()
    compute = candidate["planned_values"]["root_module"]["resources"][0]["values"]
    if field == "type":
        compute[field] = value
    else:
        compute["compute_resources"][0][field] = value
    with pytest.raises(CloudManifestError, match=message):
        parse_terraform_show(candidate)


def test_ephemeral_plan_guard_allows_absent_optional_spot_fleet_role_binding() -> None:
    candidate = terraform_show()
    candidate["variables"]["spot_fleet_role_arn"]["value"] = None
    candidate["planned_values"]["root_module"]["resources"][0]["values"][
        "compute_resources"
    ][0]["spot_iam_fleet_role"] = None
    parsed = parse_terraform_show(candidate)
    assert parsed["spot_fleet_role_arn"] is None
    assert parsed["spot_fleet_role_name"] is None


def test_ephemeral_plan_guard_rejects_unbound_spot_fleet_role() -> None:
    candidate = terraform_show()
    candidate["variables"]["spot_fleet_role_arn"]["value"] = None
    with pytest.raises(CloudManifestError, match="spot_iam_fleet_role"):
        parse_terraform_show(candidate)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("type", "multinode", "container job"),
        ("platform_capabilities", None, "EC2-only"),
    ],
)
def test_ephemeral_plan_guard_rejects_ambiguous_batch_job_definition(
    field: str, value: object, message: str
) -> None:
    candidate = terraform_show()
    values = candidate["planned_values"]["root_module"]["resources"][1]["values"]
    values[field] = value
    with pytest.raises(CloudManifestError, match=message):
        parse_terraform_show(candidate)


def test_ephemeral_plan_guard_rejects_queue_compute_environment_arn_mismatch() -> None:
    candidate = terraform_show()
    resources = candidate["planned_values"]["root_module"]["resources"]
    compute = next(
        resource
        for resource in resources
        if resource["address"] == "aws_batch_compute_environment.qualification"
    )
    queue = next(
        resource
        for resource in resources
        if resource["address"] == "aws_batch_job_queue.qualification"
    )
    compute["values"]["arn"] = (
        "arn:aws:batch:us-east-1:123456789012:compute-environment/qual-1"
    )
    queue["values"]["compute_environment_order"][0]["compute_environment"] = (
        "arn:aws:batch:us-east-1:123456789012:compute-environment/wrong"
    )
    with pytest.raises(CloudManifestError, match="compute-environment binding"):
        parse_terraform_show(candidate)


def test_ephemeral_plan_guard_requires_compute_launch_template_binding() -> None:
    candidate = terraform_show()
    compute = candidate["planned_values"]["root_module"]["resources"][0]["values"]
    compute["compute_resources"][0].pop("launch_template")
    with pytest.raises(CloudManifestError, match="bind exactly one launch template"):
        parse_terraform_show(candidate)


def test_ephemeral_plan_guard_rejects_launch_template_id_mismatch() -> None:
    candidate = terraform_show()
    compute = candidate["planned_values"]["root_module"]["resources"][0]["values"]
    compute["compute_resources"][0]["launch_template"][0]["id"] = "lt-wrong"
    with pytest.raises(CloudManifestError, match="launch-template binding differs"):
        parse_terraform_show(candidate)


def test_ephemeral_plan_guard_proves_unknown_cross_resource_ids_from_configuration() -> None:
    candidate = terraform_show()
    resources = candidate["planned_values"]["root_module"]["resources"]
    compute = next(
        resource
        for resource in resources
        if resource["address"] == "aws_batch_compute_environment.qualification"
    )
    launch_template = next(
        resource
        for resource in resources
        if resource["address"] == "aws_launch_template.qualification"
    )
    compute["values"]["compute_resources"][0]["launch_template"][0]["id"] = None
    launch_template["values"]["id"] = None

    parsed = parse_terraform_show(candidate)

    assert parsed["cross_resource_binding_proof"] == {
        "launch_template": "terraform_configuration_reference",
        "queue_compute_environment": "terraform_configuration_reference",
    }


def test_ephemeral_plan_guard_rejects_mixed_or_ambiguous_unknown_launch_references() -> None:
    candidate = terraform_show()
    resources = candidate["planned_values"]["root_module"]["resources"]
    compute = next(
        resource
        for resource in resources
        if resource["address"] == "aws_batch_compute_environment.qualification"
    )
    launch_template = next(
        resource
        for resource in resources
        if resource["address"] == "aws_launch_template.qualification"
    )
    compute["values"]["compute_resources"][0]["launch_template"][0]["id"] = None
    launch_template["values"]["id"] = None
    launch_expression = next(
        resource
        for resource in candidate["configuration"]["root_module"]["resources"]
        if resource["address"] == "aws_batch_compute_environment.qualification"
    )["expressions"]["compute_resources"][0]["launch_template"][0]
    launch_expression["launch_template_id"]["references"] = [
        "aws_launch_template.qualification.id",
        "aws_launch_template.worker.id",
    ]
    with pytest.raises(CloudManifestError, match="exact Terraform resource reference"):
        parse_terraform_show(candidate)

    candidate = terraform_show()
    resources = candidate["planned_values"]["root_module"]["resources"]
    compute = next(
        resource
        for resource in resources
        if resource["address"] == "aws_batch_compute_environment.qualification"
    )
    launch_template = next(
        resource
        for resource in resources
        if resource["address"] == "aws_launch_template.qualification"
    )
    compute["values"]["compute_resources"][0]["launch_template"][0]["id"] = None
    launch_template["values"]["id"] = None
    launch_expression = next(
        resource
        for resource in candidate["configuration"]["root_module"]["resources"]
        if resource["address"] == "aws_batch_compute_environment.qualification"
    )["expressions"]["compute_resources"][0]["launch_template"][0]
    launch_expression["version"]["references"] = [
        "aws_launch_template.worker.latest_version"
    ]
    with pytest.raises(CloudManifestError, match="exact launch-template resource"):
        parse_terraform_show(candidate)


def test_ephemeral_plan_contract_rejects_unplanned_extra_resources() -> None:
    candidate = terraform_show()
    candidate["planned_values"]["root_module"]["resources"].append(
        {"address": "aws_s3_bucket.unapproved", "values": {}}
    )
    with pytest.raises(CloudManifestError, match="exactly the four approved resources"):
        _require_resource_contract(candidate)


def test_ephemeral_plan_guard_rejects_unknown_ids_without_exact_configuration_references() -> None:
    candidate = terraform_show()
    resources = candidate["planned_values"]["root_module"]["resources"]
    compute = next(
        resource
        for resource in resources
        if resource["address"] == "aws_batch_compute_environment.qualification"
    )
    launch_template = next(
        resource
        for resource in resources
        if resource["address"] == "aws_launch_template.qualification"
    )
    compute["values"]["compute_resources"][0]["launch_template"][0]["id"] = None
    launch_template["values"]["id"] = None
    candidate["configuration"]["root_module"]["resources"][1]["expressions"][
        "compute_environment_order"
    ][0]["compute_environment"]["references"] = ["var.unrelated"]

    with pytest.raises(CloudManifestError, match="exact Terraform resource reference"):
        parse_terraform_show(candidate)


def test_terraform_show_requires_us_east_1_and_a_concrete_vpc() -> None:
    candidate = terraform_show()
    candidate["variables"]["region"]["value"] = "us-west-2"
    with pytest.raises(CloudManifestError, match="us-east-1"):
        parse_terraform_show(candidate)

    candidate = terraform_show()
    candidate["variables"].pop("vpc_id")
    with pytest.raises(CloudManifestError, match="concrete us-east-1 VPC"):
        parse_terraform_show(candidate)


@pytest.mark.parametrize("override", ["command", "entrypoint", "entryPoint"])
def test_terraform_show_rejects_fixed_image_overrides(override: str) -> None:
    candidate = terraform_show()
    job = candidate["planned_values"]["root_module"]["resources"][1]["values"]
    container = json.loads(job["container_properties"])
    container[override] = ["/bin/sh"]
    job["container_properties"] = json.dumps(container)
    with pytest.raises(CloudManifestError, match="ENTRYPOINT"):
        parse_terraform_show(candidate)


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


def test_terminal_batch_failure_retains_child_observations_for_receipt() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()

    def fail_collect(parent_job_id):
        children = tuple(
            {
                "jobId": f"child-{index}",
                "status": "FAILED",
                "statusReason": "JobQueue deleted",
                "arrayProperties": {"index": index},
                "attempts": [],
            }
            for index in (0, 1)
        )
        raise BatchAdmissionError(
            "both fixed admission children must have status SUCCEEDED",
            parent={"jobId": parent_job_id, "status": "FAILED", "statusReason": "Array Child Job failed"},
            children=children,
        )

    provider.collect_admission = fail_collect  # type: ignore[method-assign]
    with pytest.raises(QualificationExecutionError) as raised:
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
    context = raised.value.context
    assert context["parent_job_id"] == "parent"
    assert [row["statusReason"] for row in context["evidence"]["children"]] == [
        "JobQueue deleted",
        "JobQueue deleted",
    ]


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


def test_qualification_resource_names_must_bind_the_action_id() -> None:
    candidate = terraform_show()
    candidate["variables"]["name_prefix"]["value"] = "different-action"
    with pytest.raises(CloudManifestError, match="name_prefix"):
        parse_terraform_show(candidate)


def test_qualification_subnet_and_security_group_variables_bind_compute_resources() -> None:
    candidate = terraform_show()
    candidate["variables"]["subnet_ids"]["value"] = list(
        reversed(candidate["variables"]["subnet_ids"]["value"])
    )
    parsed = parse_terraform_show(candidate)
    assert set(parsed["subnet_ids"]) == set(
        candidate["variables"]["subnet_ids"]["value"]
    )

    candidate["variables"]["subnet_ids"]["value"][-1] = candidate[
        "variables"
    ]["subnet_ids"]["value"][0]
    with pytest.raises(CloudManifestError, match="subnets differ"):
        parse_terraform_show(candidate)


def test_concrete_cli_iam_simulation_binds_the_live_bucket_policy() -> None:
    plan = parse_terraform_show(terraform_show())
    plan["worker_role_arn"] = ROLE_ARNS["pneuma-worker"]
    plan["worker_role_name"] = "pneuma-worker"
    policy = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Deny", "Action": "s3:*", "Resource": "*"}],
    }
    worker_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": [
                    row["resource_arn"]
                    for row in expected_checks(
                        input_paths=plan["input_paths"],
                        output_root=plan["output_path"],
                        iam_role_arn=plan["worker_role_arn"],
                    )
                    if row["id"].startswith("input-read-")
                ],
            },
            {
                "Effect": "Allow",
                "Action": "s3:PutObject",
                "Resource": [
                    row["resource_arn"]
                    for row in expected_checks(
                        input_paths=plan["input_paths"],
                        output_root=plan["output_path"],
                        iam_role_arn=plan["worker_role_arn"],
                    )
                    if row["id"].startswith("raw-write-")
                ],
            }
        ],
    }
    worker_policy_sha256 = hashlib.sha256(
        canonical_bytes(worker_policy)
    ).hexdigest()
    checks = expected_checks(
        input_paths=plan["input_paths"],
        output_root=plan["output_path"],
        iam_role_arn=plan["worker_role_arn"],
    )
    calls: list[list[str]] = []

    def run(argv, **kwargs):
        calls.append(argv)
        if "get-bucket-policy" in argv:
            return subprocess.CompletedProcess(
                argv, 0, json.dumps({"Policy": json.dumps(policy)}).encode(), b""
            )
        if "get-role-policy" in argv:
            return subprocess.CompletedProcess(
                argv,
                0,
                json.dumps({"PolicyDocument": worker_policy}).encode(),
                b"",
            )
        if "list-role-policies" in argv:
            return subprocess.CompletedProcess(
                argv,
                0,
                b'{"IsTruncated":false,"PolicyNames":["bounded-experiment-access"]}',
                b"",
            )
        if "list-attached-role-policies" in argv:
            return subprocess.CompletedProcess(
                argv,
                0,
                b'{"IsTruncated":false,"AttachedPolicies":[]}',
                b"",
            )
        action = argv[argv.index("--action-names") + 1]
        resource = argv[argv.index("--resource-arns") + 1]
        expected = next(
            row
            for row in checks
            if row["action"] == action and row["resource_arn"] == resource
        )
        return subprocess.CompletedProcess(
            argv,
            0,
            json.dumps(
                {
                    "EvaluationResults": [
                        {
                            "EvalActionName": action,
                            "EvalResourceName": resource,
                            "EvalDecision": (
                                "allowed"
                                if expected["expected"] == "allowed"
                                else "implicitDeny"
                            ),
                        }
                    ]
                }
            ).encode(),
            b"",
        )

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="qual-1",
        job_definition="qual-1-worker",
        output_root=plan["output_path"],
    )
    record = adapter.capture_iam_simulation(
        plan=plan,
        action_id="qual-1",
        expected_policy_sha256=worker_policy_sha256,
    )
    assert record["resource_policy_present"] is True
    assert record["resource_policy_sha256"] == hashlib.sha256(
        canonical_bytes(policy)
    ).hexdigest()
    assert any("get-role-policy" in argv for argv in calls)
    assert any("list-role-policies" in argv for argv in calls)
    assert "policy_inventory" in record
    iam_calls = [argv for argv in calls if "simulate-principal-policy" in argv]
    assert len(iam_calls) == 17
    assert all(
        ("--resource-policy" in argv)
        == argv[argv.index("--action-names") + 1].startswith("s3:")
        for argv in iam_calls
    )
    assert "arn:aws" not in json.dumps(record)
    with pytest.raises(CloudManifestError, match="differs from authority"):
        adapter.capture_iam_simulation(
            plan=plan,
            action_id="qual-1",
            expected_policy_sha256="f" * 64,
        )


@pytest.mark.parametrize("flag", ["false", "invalid"])
def test_concrete_cli_rejects_incomplete_iam_policy_pagination(flag: str | None) -> None:
    plan = parse_terraform_show(terraform_show())
    plan["worker_role_arn"] = ROLE_ARNS["pneuma-worker"]
    plan["worker_role_name"] = "pneuma-worker"

    def run(argv, **kwargs):
        payload = {"PolicyNames": []}
        payload["IsTruncated"] = flag
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload).encode(), b"")

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="qual-1",
        job_definition="qual-1-worker",
        output_root=plan["output_path"],
    )
    with pytest.raises(CloudManifestError, match="IsTruncated"):
        adapter.capture_worker_policy_inventory(
            plan=plan,
            expected_policy_sha256="a" * 64,
        )


def test_concrete_cli_kms_verification_checks_registry_and_both_signatures() -> None:
    private = Ed25519PrivateKey.generate()
    key_id = "arn:aws:kms:us-east-1:123456789012:key/live-key"
    registry_key_id = "pneuma-kms-20260801-r1"
    public_raw = private.public_key().public_bytes_raw()
    registry = {
        "record_kind": "cloud_approver_key_registry",
        "schema_version": "0.1.0",
        "frozen_timestamp": "2026-08-01T00:00:00Z",
        "keys": [
            {
                "key_id": registry_key_id,
                "approver_id": "jerry-mathos-ai",
                "algorithm": "ed25519",
                "public_key_hex": public_raw.hex(),
                "not_before": "2026-08-01T00:00:00Z",
                "not_after": "2027-08-01T00:00:00Z",
                "status": "active",
                "revoked_timestamp": None,
                "revocation_reason": None,
            }
        ],
    }

    def signed_record(kind: str) -> dict[str, object]:
        record: dict[str, object] = {
            "record_kind": kind,
            "schema_version": "0.1.0",
            "human_authorization": {
                "approver_id": "jerry-mathos-ai",
                "key_id": registry_key_id,
                "granted_timestamp": "2026-08-03T09:00:00Z",
                "expires_timestamp": "2026-08-03T12:00:00Z",
                "body_sha256": "0" * 64,
                "signature_ed25519": "0" * 128,
            },
        }
        body = canonical_bytes(signed_body(record))
        record["human_authorization"]["body_sha256"] = hashlib.sha256(body).hexdigest()
        record["human_authorization"]["signature_ed25519"] = private.sign(body).hex()
        return record

    public_der = private.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    def run(argv, **kwargs):
        assert "get-public-key" in argv
        return subprocess.CompletedProcess(
            argv,
            0,
            json.dumps(
                {
                    "KeyId": key_id,
                    "KeyUsage": "SIGN_VERIFY",
                    "SigningAlgorithms": ["ED25519_SHA_512"],
                    "PublicKey": base64.b64encode(public_der).decode("ascii"),
                }
            ).encode(),
            b"",
        )

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="qual-1",
        job_definition="qual-1-worker",
        output_root="s3://bucket/runs/qual-1",
    )
    record = adapter.capture_kms_verification(
        envelope=signed_record("cloud_preparation_envelope"),
        admission=signed_record("cloud_preparation_admission"),
        key_registry=registry,
        authority={
            "kms": {
                "key_alias": "alias/pneuma-approver",
                "registry_key_id": registry_key_id,
            }
        },
    )
    assert record["signing_algorithm"] == "ED25519_SHA_512"
    assert record["envelope_signature_valid"] is True
    assert record["admission_signature_valid"] is True
    assert record["registry_key_id"] == registry_key_id


def test_terraform_adapter_parses_show_json_before_future_apply(tmp_path: Path) -> None:
    plan_path = tmp_path / "saved.tfplan"
    variable_file = tmp_path / "qualification.tfvars"
    variable_file.write_text('qualification_action_id = "qual-1"\n', encoding="utf-8")
    variable_file.chmod(0o600)
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
        adapter = TerraformAdapter(run, variable_file=variable_file)
        with pytest.raises(CloudManifestError, match="backend must be initialized"):
            adapter.load_account_plan(plan_path)
        adapter.initialize()
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
        assert calls[0][2:4] == ["init", "-input=false"]
        assert "-reconfigure" in calls[0] and "-lockfile=readonly" in calls[0]
        assert str(plan_path) in calls[1]
        assert calls[1][2:4] == ["show", "-json"]
        assert str(plan_path) in calls[2]
        assert calls[2][2:4] == ["show", "-json"]
        assert "-lock=false" not in calls[3]
        adapter.destroy(lock_timeout="60s", tags={})
        assert calls[4][2:4] == ["destroy", "-input=false"]
        assert "-lock-timeout=60s" in calls[4]
        assert f"-var-file={variable_file.resolve()}" in calls[4]
        plan_path.write_bytes(b"tampered-plan-bytes")
        with pytest.raises(CloudManifestError, match="plan bytes"):
            adapter.apply(lock_timeout="60s", tags={})
        assert len(calls) == 5
    finally:
        plan_path.unlink(missing_ok=True)


def test_terraform_adapter_rejects_changed_variable_file_before_destroy(tmp_path: Path) -> None:
    plan_path = tmp_path / "saved.tfplan"
    variable_file = tmp_path / "qualification.tfvars"
    variable_file.write_text('qualification_action_id = "qual-1"\n', encoding="utf-8")
    variable_file.chmod(0o600)

    def run(argv, **kwargs):
        if argv[2] == "show":
            return subprocess.CompletedProcess(
                argv, 0, json.dumps(terraform_show()).encode(), b""
            )
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    plan_path.write_bytes(b"exact-plan-bytes")
    adapter = TerraformAdapter(run, variable_file=variable_file)
    adapter.initialize()
    adapter.load_account_plan(plan_path)
    variable_file.write_text('qualification_action_id = "tampered"\n', encoding="utf-8")
    variable_file.chmod(0o600)
    with pytest.raises(CloudManifestError, match="variable file changed"):
        adapter.destroy(lock_timeout="60s", tags={})


def test_terraform_adapter_requires_mode_600_variable_file(tmp_path: Path) -> None:
    plan_path = tmp_path / "saved.tfplan"
    variable_file = tmp_path / "qualification.tfvars"
    plan_path.write_bytes(b"exact-plan-bytes")
    variable_file.write_text('qualification_action_id = "qual-1"\n', encoding="utf-8")
    variable_file.chmod(0o644)

    def run(argv, **kwargs):
        return subprocess.CompletedProcess(
            argv, 0, json.dumps(terraform_show()).encode(), b""
        )

    adapter = TerraformAdapter(run, variable_file=variable_file)
    adapter.initialize()
    with pytest.raises(CloudManifestError, match="mode 0600"):
        adapter.load_account_plan(plan_path)


def test_terraform_adapter_resolves_saved_plan_before_chdir(tmp_path: Path, monkeypatch) -> None:
    plan_path = tmp_path / "saved.tfplan"
    plan_path.write_bytes(b"exact-plan-bytes")
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if argv[2] == "show":
            return subprocess.CompletedProcess(
                argv, 0, json.dumps(terraform_show()).encode(), b""
            )
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.chdir(tmp_path)
    adapter = TerraformAdapter(run)
    adapter.initialize()
    adapter.load_account_plan(Path("saved.tfplan"))
    assert Path(calls[1][-1]).is_absolute()


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
            tags={
                "QualificationPurpose": "dual-l40s-admission-only",
                "QualificationTopology": "two-g6e-2xlarge-l40s",
                "QualificationManagedBy": "pneuma-ephemeral-runner-v1",
                "QualificationAction": "qual-1",
                "QualificationActionId": "qual-1",
                "QualificationCode": "fixture-only-qualification-code",
            },
        )
        == "parent"
    )
    command = " ".join(calls[0])
    assert calls[0][:2] == ["aws", "batch"]
    assert calls[0].count("aws") == 1
    assert '--array-properties {"size":2}' in command
    assert '--retry-strategy {"attempts":1}' in command
    assert '--timeout {"attemptDurationSeconds":3600}' in command
    assert "qual-1" in command
    assert "command" not in command


def test_concrete_cli_disables_and_drains_every_submitted_job(monkeypatch) -> None:
    calls = []
    responses = iter(
        [
            {
                "jobs": [
                    {"jobId": "parent", "status": "RUNNING"},
                    {"jobId": "parent:0", "status": "RUNNING"},
                    {"jobId": "parent:1", "status": "RUNNING"},
                ]
            },
            {
                "jobs": [
                    {"jobId": "parent", "status": "FAILED"},
                    {"jobId": "parent:0", "status": "FAILED"},
                    {"jobId": "parent:1", "status": "FAILED"},
                ]
            },
        ]
    )

    def run(argv, **kwargs):
        calls.append(argv)
        payload = next(responses) if "describe-jobs" in argv else {}
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload).encode(), b"")

    monkeypatch.setattr("pneuma_lab.cloud.ephemeral_runner.time.sleep", lambda _: None)
    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="q",
        job_definition="d",
        output_root="s3://bucket/runs/qual-1",
        compute_environment="ce",
    )
    adapter.parent_job_id = "parent"
    adapter.disable_and_drain({})

    assert any("update-job-queue" in call and "DISABLED" in call for call in calls)
    assert any("update-compute-environment" in call and "DISABLED" in call for call in calls)
    assert sum("describe-jobs" in call for call in calls) == 2
    assert not any("terminate-job" in call for call in calls)


def test_concrete_cli_rejects_partial_drain_describe_results() -> None:
    def run(argv, **kwargs):
        if "describe-jobs" in argv:
            return subprocess.CompletedProcess(
                argv,
                0,
                b'{"jobs":[{"jobId":"parent","status":"FAILED"}]}',
                b"",
            )
        return subprocess.CompletedProcess(argv, 0, b"{}", b"")

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="q",
        job_definition="d",
        output_root="s3://bucket/runs/qual-1",
    )
    adapter.parent_job_id = "parent"
    with pytest.raises(CloudManifestError, match="every requested job"):
        adapter.disable_and_drain({})


def test_concrete_cli_waits_for_valid_environment_and_queue() -> None:
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if "describe-compute-environments" in argv:
            payload = {
                "computeEnvironments": [
                    {
                        "status": "VALID",
                        "computeEnvironmentArn": "arn:aws:batch:us-east-1:123456789012:compute-environment/ce",
                    }
                ]
            }
        else:
            payload = {
                "jobQueues": [
                    {
                        "status": "VALID",
                        "computeEnvironmentOrder": [
                            {
                                "order": 1,
                                "computeEnvironment": "arn:aws:batch:us-east-1:123456789012:compute-environment/ce",
                            }
                        ],
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
        compute_environment="ce",
    )
    assert adapter.wait_ready({}) == {
        "compute_environment_status": "VALID",
        "queue_status": "VALID",
    }
    assert any("describe-compute-environments" in call for call in calls)
    assert any("describe-job-queues" in call for call in calls)


def test_concrete_cli_rejects_a_queue_bound_to_another_environment() -> None:
    def run(argv, **kwargs):
        if "describe-compute-environments" in argv:
            payload = {
                "computeEnvironments": [
                    {
                        "status": "VALID",
                        "computeEnvironmentArn": "arn:aws:batch:us-east-1:123456789012:compute-environment/ce",
                    }
                ]
            }
        else:
            payload = {
                "jobQueues": [
                    {
                        "status": "VALID",
                        "computeEnvironmentOrder": [
                            {
                                "order": 1,
                                "computeEnvironment": "arn:aws:batch:us-east-1:123456789012:compute-environment/other",
                            }
                        ],
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
        compute_environment="ce",
    )
    with pytest.raises(CloudManifestError, match="bound to the verified compute environment"):
        adapter.wait_ready({})


def test_concrete_cli_absence_checks_all_ephemeral_resource_classes() -> None:
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        payloads = {
            "describe-job-queues": {"jobQueues": []},
            "describe-compute-environments": {"computeEnvironments": []},
            "describe-job-definitions": {"jobDefinitions": []},
            "list-objects-v2": {},
            "describe-instances": {"Reservations": []},
            "describe-volumes": {"Volumes": []},
            "describe-launch-templates": {"LaunchTemplates": []},
            "describe-network-interfaces": {"NetworkInterfaces": []},
            "describe-security-groups": {"SecurityGroups": []},
            "lookup-events": {"Events": []},
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
        "provider_history": {
            "inactive_job_definition_history_retained_by_aws": False,
            "inactive_job_definition_arn_sha256": None,
        },
        "artifact_prefix": {"empty": True, "object_count": 0},
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
        if "lookup-events" in argv:
            return subprocess.CompletedProcess(argv, 0, b'{"Events":[]}', b"")
        command = next(
            command
            for command in (
                "describe-job-definitions",
                "list-objects-v2",
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
            "list-objects-v2": "Contents",
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
                b'{"jobs":[{"jobId":"parent","status":"FAILED"},{"jobId":"parent:0","status":"FAILED"},{"jobId":"parent:1","status":"FAILED"}]}',
                b"",
            )
        if "lookup-events" in argv:
            event = {
                "eventName": "SubmitJob",
                "requestParameters": {"jobName": "qual-1"},
                "responseElements": {"jobId": "parent"},
            }
            return subprocess.CompletedProcess(
                argv,
                0,
                json.dumps({"Events": [{"CloudTrailEvent": json.dumps(event)}]}).encode(),
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
                "list-objects-v2",
                "describe-instances",
                "describe-volumes",
                "describe-launch-templates",
                "describe-network-interfaces",
                "describe-security-groups",
            )
            if command in argv
        )
        collection = {
            "list-objects-v2": "Contents",
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
    adapter._drained_action_job_ids = {"parent", "parent:0", "parent:1"}
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


def test_concrete_cli_captures_exact_cloudtrail_submit_event() -> None:
    tags = {
        "QualificationPurpose": "dual-l40s-admission-only",
        "QualificationTopology": "two-g6e-2xlarge-l40s",
        "QualificationManagedBy": "pneuma-ephemeral-runner-v1",
        "QualificationAction": "qual-1",
        "QualificationActionId": "qual-1",
        "QualificationCode": "fixture-only-qualification-code",
    }
    event = {
        "EventId": "event-1",
        "EventTime": "2026-08-03T09:34:48Z",
        "CloudTrailEvent": json.dumps(
            {
                "eventName": "SubmitJob",
                "responseElements": {"jobId": "parent"},
                "requestParameters": {
                    "jobName": "qual-1",
                    "jobQueue": "qual-1",
                    "jobDefinition": "qual-1-worker:1",
                    "arrayProperties": {"size": 2},
                    "retryStrategy": {"attempts": 1},
                    "timeout": {"attemptDurationSeconds": 3600},
                    "tags": tags,
                },
            }
        ),
    }

    def run(argv, **kwargs):
        if "submit-job" in argv:
            return subprocess.CompletedProcess(
                argv, 0, b'{"jobId":"parent"}', b""
            )
        assert "cloudtrail" in argv
        return subprocess.CompletedProcess(
            argv, 0, json.dumps({"Events": [event]}).encode(), b""
        )

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="qual-1",
        job_definition="qual-1-worker",
        output_root="s3://bucket/runs/qual-1",
    )
    adapter.submit_array(size=2, timeout_seconds=3600, attempts=1, tags=tags)
    evidence = adapter.capture_submit_evidence("parent")
    assert evidence["submit_count_proven"] == 1
    assert evidence["array_size"] == 2
    assert evidence["retry_attempts"] == 1
    assert evidence["submit_event_time_utc"] == "2026-08-03T09:34:48Z"


def test_concrete_cli_uses_batch_timeout_readback_when_cloudtrail_omits_timeout() -> None:
    tags = {
        "QualificationPurpose": "dual-l40s-admission-only",
        "QualificationTopology": "two-g6e-2xlarge-l40s",
        "QualificationManagedBy": "pneuma-ephemeral-runner-v1",
        "QualificationAction": "qual-1",
        "QualificationActionId": "qual-1",
        "QualificationCode": "fixture-only-qualification-code",
    }
    event = {
        "EventId": "event-omits-timeout",
        "EventTime": "2026-08-03T09:34:48Z",
        "CloudTrailEvent": json.dumps(
            {
                "eventName": "SubmitJob",
                "responseElements": {"jobId": "parent"},
                "requestParameters": {
                    "jobName": "qual-1",
                    "jobQueue": "qual-1",
                    "jobDefinition": "qual-1-worker:1",
                    "arrayProperties": {"size": 2},
                    "retryStrategy": {"attempts": 1},
                    "tags": tags,
                },
            }
        ),
    }

    def run(argv, **kwargs):
        if "submit-job" in argv:
            return subprocess.CompletedProcess(
                argv, 0, b'{"jobId":"parent"}', b""
            )
        if "cloudtrail" in argv:
            return subprocess.CompletedProcess(
                argv, 0, json.dumps({"Events": [event]}).encode(), b""
            )
        assert argv[0:3] == ["aws", "batch", "describe-jobs"]
        return subprocess.CompletedProcess(
            argv,
            0,
            json.dumps(
                {"jobs": [{"jobId": "parent", "timeout": {"attemptDurationSeconds": 3600}}]}
            ).encode(),
            b"",
        )

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="qual-1",
        job_definition="qual-1-worker",
        output_root="s3://bucket/runs/qual-1",
    )
    adapter.submit_array(size=2, timeout_seconds=3600, attempts=1, tags=tags)
    evidence = adapter.capture_submit_evidence("parent")
    assert evidence["submit_count_proven"] == 1


def test_concrete_cli_rejects_same_name_cloudtrail_event_for_wrong_parent() -> None:
    tags = {
        "QualificationPurpose": "dual-l40s-admission-only",
        "QualificationTopology": "two-g6e-2xlarge-l40s",
        "QualificationManagedBy": "pneuma-ephemeral-runner-v1",
        "QualificationAction": "qual-1",
        "QualificationActionId": "qual-1",
        "QualificationCode": "fixture-only-qualification-code",
    }
    event = {
        "EventId": "event-wrong-parent",
        "EventTime": "2026-08-03T09:34:48Z",
        "CloudTrailEvent": json.dumps(
            {
                "eventName": "SubmitJob",
                "responseElements": {"jobId": "different-parent"},
                "requestParameters": {
                    "jobName": "qual-1",
                    "jobQueue": "qual-1",
                    "jobDefinition": "qual-1-worker:1",
                    "arrayProperties": {"size": 2},
                    "retryStrategy": {"attempts": 1},
                    "timeout": {"attemptDurationSeconds": 3600},
                    "tags": tags,
                },
            }
        ),
    }

    def run(argv, **kwargs):
        if "submit-job" in argv:
            return subprocess.CompletedProcess(argv, 0, b'{"jobId":"parent"}', b"")
        return subprocess.CompletedProcess(
            argv, 0, json.dumps({"Events": [event]}).encode(), b""
        )

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="qual-1",
        job_definition="qual-1-worker",
        output_root="s3://bucket/runs/qual-1",
    )
    adapter.submit_array(size=2, timeout_seconds=3600, attempts=1, tags=tags)
    with pytest.raises(CloudManifestError, match="does not match the submitted parent"):
        adapter.capture_submit_evidence("parent")


def test_concrete_cli_rejects_duplicate_submit_events_with_the_same_action_name() -> None:
    tags = {
        "QualificationPurpose": "dual-l40s-admission-only",
        "QualificationTopology": "two-g6e-2xlarge-l40s",
        "QualificationManagedBy": "pneuma-ephemeral-runner-v1",
        "QualificationAction": "qual-1",
        "QualificationActionId": "qual-1",
        "QualificationCode": "fixture-only-qualification-code",
    }
    request = {
        "jobName": "qual-1",
        "jobQueue": "qual-1",
        "jobDefinition": "qual-1-worker:1",
        "arrayProperties": {"size": 2},
        "retryStrategy": {"attempts": 1},
        "timeout": {"attemptDurationSeconds": 3600},
        "tags": tags,
    }
    events = [
        {
            "EventId": f"event-{index}",
            "EventTime": "2026-08-03T09:34:48Z",
            "CloudTrailEvent": json.dumps(
                {
                    "eventName": "SubmitJob",
                    "responseElements": {"jobId": job_id},
                    "requestParameters": request,
                }
            ),
        }
        for index, job_id in enumerate(("parent", "duplicate-parent"), start=1)
    ]

    def run(argv, **kwargs):
        if "submit-job" in argv:
            return subprocess.CompletedProcess(
                argv, 0, b'{"jobId":"parent"}', b""
            )
        return subprocess.CompletedProcess(
            argv, 0, json.dumps({"Events": events}).encode(), b""
        )

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="qual-1",
        job_definition="qual-1-worker",
        output_root="s3://bucket/runs/qual-1",
    )
    adapter.submit_array(size=2, timeout_seconds=3600, attempts=1, tags=tags)
    with pytest.raises(CloudManifestError, match="exactly one SubmitJob event"):
        adapter.capture_submit_evidence("parent")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("jobName", "wrong-action", "wrong qualification job name"),
        ("jobQueue", "wrong-queue", "wrong job queue"),
        ("jobDefinition", "wrong-worker:1", "wrong job definition"),
        ("tags", {"QualificationAction": "wrong-action"}, "tags differ"),
    ],
)
def test_concrete_cli_rejects_submit_event_binding_drift(
    field: str, value: object, message: str
) -> None:
    tags = {
        "QualificationPurpose": "dual-l40s-admission-only",
        "QualificationTopology": "two-g6e-2xlarge-l40s",
        "QualificationManagedBy": "pneuma-ephemeral-runner-v1",
        "QualificationAction": "qual-1",
        "QualificationActionId": "qual-1",
        "QualificationCode": "fixture-only-qualification-code",
    }
    request: dict[str, object] = {
        "jobName": "qual-1",
        "jobQueue": "qual-1",
        "jobDefinition": "qual-1-worker:1",
        "arrayProperties": {"size": 2},
        "retryStrategy": {"attempts": 1},
        "timeout": {"attemptDurationSeconds": 3600},
        "tags": tags,
    }
    request[field] = value
    event = {
        "EventId": "event-drift",
        "EventTime": "2026-08-03T09:34:48Z",
        "CloudTrailEvent": json.dumps(
            {
                "eventName": "SubmitJob",
                "responseElements": {"jobId": "parent"},
                "requestParameters": request,
            }
        ),
    }

    def run(argv, **kwargs):
        if "submit-job" in argv:
            return subprocess.CompletedProcess(
                argv, 0, b'{"jobId":"parent"}', b""
            )
        return subprocess.CompletedProcess(
            argv, 0, json.dumps({"Events": [event]}).encode(), b""
        )

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="qual-1",
        job_definition="qual-1-worker",
        output_root="s3://bucket/runs/qual-1",
    )
    adapter.submit_array(size=2, timeout_seconds=3600, attempts=1, tags=tags)
    with pytest.raises(CloudManifestError, match=message):
        adapter.capture_submit_evidence("parent")


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
            requested = argv[argv.index("--jobs") + 1]
            index = int(requested.rsplit(":", 1)[1])
            payload = {
                "jobs": [
                    {
                        "jobId": requested,
                        "status": "FAILED",
                        "arrayProperties": {"index": index},
                        "attempts": [{}],
                        "container": {"instanceId": f"i-0123456789abcdef{index}"},
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


def test_concrete_cli_rejects_batch_child_id_drift() -> None:
    def run(argv, **kwargs):
        requested = argv[argv.index("--jobs") + 1]
        if requested == "parent":
            payload = {"jobs": [{"jobId": "parent", "status": "SUCCEEDED"}]}
        else:
            payload = {
                "jobs": [
                    {
                        "jobId": "other-parent:0",
                        "status": "SUCCEEDED",
                        "arrayProperties": {"index": 0},
                        "attempts": [{}],
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
    )
    with pytest.raises(BatchAdmissionError, match="wrong array child") as raised:
        adapter.collect_admission("parent")
    assert raised.value.children[0]["jobId"] == "other-parent:0"


def test_concrete_cli_rejects_batch_child_index_drift() -> None:
    def run(argv, **kwargs):
        requested = argv[argv.index("--jobs") + 1]
        if requested == "parent":
            payload = {"jobs": [{"jobId": "parent", "status": "SUCCEEDED"}]}
        else:
            index = int(requested.rsplit(":", 1)[1])
            payload = {
                "jobs": [
                    {
                        "jobId": requested,
                        "status": "SUCCEEDED",
                        "arrayProperties": {"index": 1 - index},
                        "attempts": [{}],
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
    )
    with pytest.raises(BatchAdmissionError, match="wrong array child index") as raised:
        adapter.collect_admission("parent")
    assert raised.value.children[0]["arrayProperties"]["index"] == 1


def test_concrete_cli_retains_partial_artifact_context_on_retrieval_failure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "input.json"
    source.write_text("{}", encoding="utf-8")
    measurements = {}
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
        measurements[worker_artifact_uri("s3://bucket/runs/qual-1", index)] = (
            canonical_bytes(measurement) + b"\n"
        )

    class PartialObjects:
        def get_object(self, bucket, key):
            uri = f"s3://{bucket}/{key}"
            if "/worker-1/" in uri:
                raise RuntimeError("worker-1 object unavailable")
            return measurements[uri]

    def run(argv, **kwargs):
        requested = argv[argv.index("--jobs") + 1]
        if requested == "parent":
            payload = {"jobs": [{"jobId": "parent", "status": "SUCCEEDED"}]}
        else:
            index = int(requested.rsplit(":", 1)[1])
            payload = {
                "jobs": [
                    {
                        "jobId": requested,
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
        transport=PartialObjects(),
    )
    with pytest.raises(BatchAdmissionError, match="raw worker artifact retrieval") as raised:
        adapter.collect_admission("parent")
    assert raised.value.instance_ids == (
        "i-0123456789abcdef0",
        "i-0123456789abcdef1",
    )
    assert set(raised.value.raw_evidence) == {0}


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

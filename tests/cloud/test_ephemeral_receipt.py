from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.authorization_keys import (
    authorization_body_digest,
    canonical_bytes,
)
from pneuma_lab.cloud.ephemeral_receipt import (
    build_ephemeral_qualification_receipt,
    validate_authority_evidence,
)
from pneuma_lab.cloud.iam_simulation import expected_checks, run_iam_simulation
from pneuma_lab.cloud.manifests import (
    validate_ephemeral_dual_worker_qualification_receipt,
)
from pneuma_lab.cloud.qualification_execution import (
    BatchAdmissionError,
    terraform_plan_binding_digest,
)


ROOT = Path(__file__).resolve().parents[2]
RECEIPT = (
    ROOT
    / "docs/research/neurips-2026-workshop/evidence/"
    / "dual-l40s-qualification-011-execution-receipt-20260803.json"
)


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


def _authority_evidence_fixture() -> tuple[
    dict[str, object], bytes, dict[str, object], dict[str, object], dict[str, object]
]:
    action_id = "dual-l40s-qualification-012"
    saved_plan_sha256 = "1" * 64
    terraform_show_sha256 = "2" * 64
    plan_binding_sha256 = terraform_plan_binding_digest(
        saved_plan_sha256, terraform_show_sha256
    )
    plan: dict[str, object] = {
        "saved_plan_sha256": saved_plan_sha256,
        "terraform_show_sha256": terraform_show_sha256,
        "terraform_plan_binding_sha256": plan_binding_sha256,
        "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/worker@sha256:"
        + "4" * 64,
        "output_prefix": (
            "s3://pneuma-artifacts/runs/qualification/"
            f"{action_id}/outputs/"
        ),
        "subnet_az_map": [
            {"availability_zone": f"us-east-1{letter}", "subnet_id": f"subnet-{letter}"}
            for letter in ("a", "b", "c", "d")
        ],
    }

    def authorization_record(label: str) -> dict[str, object]:
        record: dict[str, object] = {
            "record_kind": f"cloud_{label}_authorization",
            "action_id": action_id,
            "human_authorization": {
                "approver_id": "operator",
                "key_id": "test-key",
                "granted_timestamp": "2026-08-03T00:00:00Z",
                "expires_timestamp": "2026-08-04T00:00:00Z",
                "signature_ed25519": "00" * 64,
            },
        }
        approval = record["human_authorization"]
        assert isinstance(approval, dict)
        approval["body_sha256"] = authorization_body_digest(record)
        return record

    envelope = authorization_record("preparation_envelope")
    admission = authorization_record("preparation_admission")
    package: dict[str, object] = {
        "record_kind": "cloud_preparation_signing_package",
        "plan_sha256": saved_plan_sha256,
        "saved_plan_sha256": saved_plan_sha256,
        "terraform_show_sha256": terraform_show_sha256,
        "terraform_plan_binding_sha256": plan_binding_sha256,
        "envelope": envelope,
        "admission": admission,
        "envelope_body_sha256": authorization_body_digest(envelope),
        "admission_body_sha256": authorization_body_digest(admission),
        "qualification_binding": {
            "action_id": action_id,
            "iam_policy_sha256": "a" * 64,
            "image_digest": "sha256:" + "4" * 64,
            "subnet_az_map": plan["subnet_az_map"],
            "output_prefix": plan["output_prefix"],
            "projected_cost_usd": 4.48,
            "max_retries": 0,
        },
    }
    package_bytes = canonical_bytes(package)

    def evidence(record: dict[str, object]) -> dict[str, str]:
        approval = record["human_authorization"]
        assert isinstance(approval, dict)
        signature = approval["signature_ed25519"]
        assert isinstance(signature, str)
        return {
            "body_sha256": authorization_body_digest(record),
            "signature_sha256": hashlib.sha256(bytes.fromhex(signature)).hexdigest(),
        }

    authority: dict[str, object] = {
        "status": "authorized_and_verified",
        "qualification_only": True,
        "action_id": action_id,
        "provider": "aws",
        "region": "us-east-1",
        "action_class": "qualification_audit",
        "signed_package_sha256": hashlib.sha256(package_bytes).hexdigest(),
        "plan_sha256": saved_plan_sha256,
        "saved_plan_sha256": saved_plan_sha256,
        "terraform_show_sha256": terraform_show_sha256,
        "terraform_plan_binding_sha256": plan_binding_sha256,
        "image_digest": "sha256:" + "4" * 64,
        "projected_cost_usd": 4.48,
        "max_retries": 0,
        "iam_policy_sha256": "a" * 64,
        "envelope": evidence(envelope),
        "admission": evidence(admission),
        "kms": {
            "signing_algorithm": "ED25519_SHA_512",
            "envelope_signature_valid": True,
            "admission_signature_valid": True,
        },
    }
    return authority, package_bytes, envelope, admission, plan


def test_validate_authority_evidence_rechecks_complete_package_binding() -> None:
    authority, package_bytes, envelope, admission, plan = _authority_evidence_fixture()
    validated = validate_authority_evidence(
        authority,
        package_bytes=package_bytes,
        envelope=envelope,
        admission=admission,
        action_id="dual-l40s-qualification-012",
        region="us-east-1",
        plan=plan,
        projected_cost_usd=4.48,
    )
    assert validated["status"] == "authorized_and_verified"

    tampered = deepcopy(authority)
    tampered["terraform_show_sha256"] = "9" * 64
    with pytest.raises(CloudManifestError, match="authority terraform_show_sha256"):
        validate_authority_evidence(
            tampered,
            package_bytes=package_bytes,
            envelope=envelope,
            admission=admission,
            action_id="dual-l40s-qualification-012",
            region="us-east-1",
            plan=plan,
            projected_cost_usd=4.48,
        )

    missing_projection = deepcopy(authority)
    missing_projection.pop("projected_cost_usd")
    with pytest.raises(CloudManifestError, match="authority projection"):
        validate_authority_evidence(
            missing_projection,
            package_bytes=package_bytes,
            envelope=envelope,
            admission=admission,
            action_id="dual-l40s-qualification-012",
            region="us-east-1",
            plan=plan,
            projected_cost_usd=4.48,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("status", "not-authorized", "authorized_and_verified"),
        ("qualification_only", False, "qualification-only"),
        ("action_id", "other-action", "action or provider"),
        ("provider", "gcp", "action or provider"),
        ("region", "us-west-2", "region differs"),
        ("action_class", "scientific_experiment", "qualification audit"),
        ("max_retries", 1, "permits retries"),
        ("signed_package_sha256", "0" * 64, "signed package bytes"),
        ("iam_policy_sha256", "b" * 64, "package IAM policy"),
    ],
)
def test_validate_authority_evidence_rejects_authority_drift(
    field: str, value: object, message: str
) -> None:
    authority, package_bytes, envelope, admission, plan = _authority_evidence_fixture()
    tampered = deepcopy(authority)
    tampered[field] = value
    with pytest.raises(CloudManifestError, match=message):
        validate_authority_evidence(
            tampered,
            package_bytes=package_bytes,
            envelope=envelope,
            admission=admission,
            action_id="dual-l40s-qualification-012",
            region="us-east-1",
            plan=plan,
            projected_cost_usd=4.48,
        )


def test_validate_authority_evidence_rejects_kms_drift() -> None:
    authority, package_bytes, envelope, admission, plan = _authority_evidence_fixture()
    tampered = deepcopy(authority)
    tampered["kms"]["signing_algorithm"] = "RSA_SHA_256"
    with pytest.raises(CloudManifestError, match="KMS authority verification"):
        validate_authority_evidence(
            tampered,
            package_bytes=package_bytes,
            envelope=envelope,
            admission=admission,
            action_id="dual-l40s-qualification-012",
            region="us-east-1",
            plan=plan,
            projected_cost_usd=4.48,
        )


def test_current_terminal_no_go_receipt_is_schema_bound() -> None:
    record = json.loads(RECEIPT.read_text(encoding="utf-8"))
    validated = validate_ephemeral_dual_worker_qualification_receipt(record)
    assert validated["status"] == "no_go"
    assert validated["launch"]["retry_attempts"] == 1
    assert validated["teardown"]["teardown_complete_except_provider_history"] is True


def test_ephemeral_receipt_rejects_retry_or_launch_contract_drift() -> None:
    record = json.loads(RECEIPT.read_text(encoding="utf-8"))
    record = deepcopy(record)
    record["launch"]["retry_attempts"] = 2
    with pytest.raises(CloudManifestError):
        validate_ephemeral_dual_worker_qualification_receipt(record)


def test_runner_receipt_builder_preserves_terminal_child_failure_evidence() -> None:
    digest = "a" * 64
    plan = {
        "saved_plan_sha256": "1" * 64,
        "terraform_show_sha256": "2" * 64,
        "terraform_plan_binding_sha256": "3" * 64,
        "image": "registry.example/worker@sha256:" + "4" * 64,
        "qualification_model": "fixture-only-cuda",
        "qualification_model_revision": "fixture-only-v1",
        "worker_role_arn": "arn:aws:iam::123456789012:role/worker",
        "input_paths": {
            "protocol": "s3://bucket/runs/qualification/qual-1/inputs/protocol.json",
            "architecture": "s3://bucket/runs/qualification/qual-1/inputs/architecture.json",
            "authorization": "s3://bucket/runs/qualification/qual-1/inputs/authorization.json",
            "image": "s3://bucket/runs/qualification/qual-1/inputs/image.json",
            "input_lock": "s3://bucket/runs/qualification/qual-1/inputs/input-lock.json",
        },
        "output_path": "s3://bucket/runs/qualification/qual-1/outputs/",
    }
    checks = expected_checks(
        input_paths=plan["input_paths"],
        output_root=plan["output_path"],
        iam_role_arn=plan["worker_role_arn"],
    )

    def simulate(*args: str) -> dict[str, list[dict[str, str]]]:
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
                        "allowed" if expected["expected"] == "allowed" else "implicitDeny"
                    ),
                }
            ]
        }

    iam_simulation = run_iam_simulation(
        simulate,
        plan=plan,
        action_id="qual-1",
        expected_policy_sha256="b" * 64,
    )
    authority = {
        "signed_package_sha256": digest,
        "iam_policy_sha256": "b" * 64,
        "envelope": {"body_sha256": "c" * 64, "signature_sha256": "d" * 64},
        "admission": {"body_sha256": "e" * 64, "signature_sha256": "f" * 64},
        "kms": {"signing_algorithm": "ED25519_SHA_512"},
    }
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
    failure = BatchAdmissionError(
        "children failed",
        parent={"status": "FAILED", "statusReason": "Array Child Job failed"},
        children=children,
    )
    receipt = build_ephemeral_qualification_receipt(
        {
            "parent_job_id": "parent",
            "plan": plan,
            "iam_simulation": iam_simulation,
            "kms_verification": kms_verification_record(),
            "projected_cost_usd": 4.48,
            "launch": {
                "cloudtrail_submit_job_event_id_sha256": "5" * 64,
                "submit_event_time_utc": "2026-08-03T09:34:48Z",
                "submit_count_proven": 1,
                "array_size": 2,
                "retry_attempts": 1,
            },
            "evidence": {
                "parent": {"status": "FAILED", "statusReason": "Array Child Job failed"},
                "children": children,
                "instance_ids": (),
                "raw_evidence": {},
            },
            "failure": failure,
            "cleanup_failure": None,
            "recovery": None,
            "absence": {
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
            | {
                "provider_history": {
                    "inactive_job_definition_history_retained_by_aws": True,
                    "inactive_job_definition_arn_sha256": "6" * 64,
                },
                "artifact_prefix": {"empty": True, "object_count": 0},
            },
        },
        action_id="qual-1",
        region="us-east-1",
        authority=authority,
        output_root=plan["output_path"],
    )
    assert receipt["status"] == "no_go"
    assert receipt["authority"]["kms_verification_sha256"] == kms_verification_record()[
        "verification_sha256"
    ]
    assert receipt["no_go_reason"]["child_statuses"][0]["status_reason"] == "JobQueue deleted"

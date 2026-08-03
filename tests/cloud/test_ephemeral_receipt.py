from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.ephemeral_receipt import (
    build_ephemeral_qualification_receipt,
)
from pneuma_lab.cloud.iam_simulation import expected_checks, run_iam_simulation
from pneuma_lab.cloud.manifests import (
    validate_ephemeral_dual_worker_qualification_receipt,
)
from pneuma_lab.cloud.qualification_execution import BatchAdmissionError


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

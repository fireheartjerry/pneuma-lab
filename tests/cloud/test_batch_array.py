from __future__ import annotations

import pytest

from pneuma_lab.cloud.batch_array import require_batch_array_qualification
from pneuma_lab.cloud.errors import CloudManifestError


def receipt() -> dict:
    operations = [
        "create_service_linked_role", "create_execution_role", "attach_execution_role_policy",
        "create_compute_environment", "create_job_queue", "register_job_definition", "submit_array_job",
        "disable_job_queue", "delete_job_queue", "disable_compute_environment", "delete_compute_environment",
        "deregister_job_definition", "detach_execution_role_policy", "delete_execution_role", "delete_service_linked_role",
    ]
    return {
        "record_kind": "cloud_batch_array_qualification_receipt",
        "schema_version": "0.1.0",
        "plan_sha256": "1" * 64,
        "input_lock_sha256": None,
        "provider": "aws",
        "region": "us-east-1",
        "account_id": "123456789012",
        "qualification_id": "batch-array-qualification-011",
        "identity_arn": "arn:aws:iam::123456789012:root",
        "preflight": {key: True for key in (
            "account_exact", "vpc_exact", "subnet_exact", "security_group_exact",
            "compute_environment_absent", "job_queue_absent", "job_definition_absent",
            "service_linked_role_absent", "execution_role_absent",
        )},
        "resources": {
            "service_linked_role_arn": "arn:aws:iam::123456789012:role/aws-service-role/batch.amazonaws.com/AWSServiceRoleForBatch",
            "execution_role_arn": "arn:aws:iam::123456789012:role/batch-array-exec-011",
            "compute_environment_arn": "arn:aws:batch:us-east-1:123456789012:compute-environment/batch-array-ce-011",
            "compute_environment_name": "batch-array-ce-011",
            "job_queue_arn": "arn:aws:batch:us-east-1:123456789012:job-queue/batch-array-q-011",
            "job_queue_name": "batch-array-q-011",
            "job_definition_arn": "arn:aws:batch:us-east-1:123456789012:job-definition/batch-array-jd-011:1",
            "job_definition_revision": 1,
            "parent_job_id": "parent-011",
            "child_job_ids": ["child-0", "child-1", "child-2"],
        },
        "mutations": [
            {"operation": operation, "return_code": 0, "stdout_sha256": "a" * 64, "stderr_sha256": "b" * 64, "duration_ms": 1, "succeeded": True}
            for operation in operations
        ],
        "observations": {
            "compute_environment_status": "VALID",
            "job_queue_status": "VALID",
            "parent_status": "SUCCEEDED",
            "array_size": 3,
            "child_indices": [0, 1, 2],
            "children": [
                {"job_id": f"child-{index}", "index": index, "status": "SUCCEEDED", "attempt_count": 1}
                for index in range(3)
            ],
        },
        "teardown": {
            "job_cancelled_if_needed": True,
            "queue_disabled": True,
            "queue_deleted": True,
            "compute_environment_disabled": True,
            "compute_environment_deleted": True,
            "job_definition_deregistered": True,
            "execution_policy_detached": True,
            "execution_role_deleted": True,
            "service_linked_role_deleted": True,
            "final_resources_absent": True,
            "service_linked_role_deletion_task_id": "task-011",
        },
        "gates": {
            "preflight_exact": True,
            "compute_environment_valid": True,
            "job_queue_valid": True,
            "array_size_exact": True,
            "child_indices_exact": True,
            "all_children_succeeded": True,
            "all_children_one_attempt": True,
            "no_provider_errors": True,
            "no_retries": True,
            "exact_teardown": True,
            "no_scientific_action": True,
        },
        "residual_resource_ids": [],
        "no_scientific_action": True,
        "verdict": "passed",
        "failure_reason": None,
    }


def test_batch_array_receipt_passes() -> None:
    assert require_batch_array_qualification(receipt())["verdict"] == "passed"


@pytest.mark.parametrize("mutation", [
    lambda row: row["observations"].update(child_indices=[0, 2, 1]),
    lambda row: row["observations"]["children"][1].update(status="FAILED"),
    lambda row: row["teardown"].update(final_resources_absent=False),
    lambda row: row["mutations"].pop(),
])
def test_batch_array_receipt_fails_closed(mutation) -> None:
    row = receipt()
    mutation(row)
    with pytest.raises(CloudManifestError):
        require_batch_array_qualification(row)

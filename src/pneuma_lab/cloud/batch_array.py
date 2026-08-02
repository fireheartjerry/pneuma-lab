"""Fail-closed validation for a real AWS Batch Fargate array receipt."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import CloudManifestError
from .manifests import validate_batch_array_qualification_receipt


_REQUIRED_MUTATIONS = {
    "create_service_linked_role",
    "create_execution_role",
    "attach_execution_role_policy",
    "create_compute_environment",
    "create_job_queue",
    "register_job_definition",
    "submit_array_job",
    "disable_job_queue",
    "delete_job_queue",
    "disable_compute_environment",
    "delete_compute_environment",
    "deregister_job_definition",
    "detach_execution_role_policy",
    "delete_execution_role",
    "delete_service_linked_role",
}


def require_batch_array_qualification(record: Mapping[str, Any]) -> dict[str, Any]:
    """Require exact Fargate array indices, successful children, and teardown."""

    receipt = validate_batch_array_qualification_receipt(record)
    preflight = receipt["preflight"]
    if not all(preflight.values()):
        raise CloudManifestError("Batch qualification preflight was not exact")

    observations = receipt["observations"]
    size = observations["array_size"]
    children = observations["children"]
    if size < 2 or len(children) != size:
        raise CloudManifestError("Batch array receipt does not contain exactly the signed child count")
    indices = [child["index"] for child in children]
    if indices != list(range(size)) or observations["child_indices"] != list(range(size)):
        raise CloudManifestError("Batch array child indices are not exactly contiguous and ordered")
    if len({child["job_id"] for child in children}) != size:
        raise CloudManifestError("Batch array receipt repeats a child job id")
    if any(child["status"] != "SUCCEEDED" for child in children):
        raise CloudManifestError("one or more Batch array children did not succeed")
    if any(child["attempt_count"] != 1 for child in children):
        raise CloudManifestError("Batch array child used a retry or has no recorded attempt")
    if observations["compute_environment_status"] != "VALID" or observations["job_queue_status"] != "VALID":
        raise CloudManifestError("Batch compute environment or queue was not valid")
    if observations["parent_status"] != "SUCCEEDED":
        raise CloudManifestError("Batch array parent did not succeed")

    mutations = receipt["mutations"]
    names = [item["operation"] for item in mutations]
    if len(names) != len(set(names)):
        raise CloudManifestError("Batch qualification repeats a mutation operation")
    if not _REQUIRED_MUTATIONS.issubset(names):
        raise CloudManifestError("Batch qualification omits a required create or teardown mutation")
    if any(not item["succeeded"] for item in mutations):
        raise CloudManifestError("Batch qualification contains a failed provider mutation")

    teardown = receipt["teardown"]
    if not all(value for key, value in teardown.items() if key != "service_linked_role_deletion_task_id"):
        raise CloudManifestError("Batch qualification teardown is incomplete")
    if receipt["residual_resource_ids"]:
        raise CloudManifestError("Batch qualification leaves residual resources")

    expected_gates = {
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
    }
    if receipt["gates"] != expected_gates or receipt["verdict"] != "passed":
        raise CloudManifestError("Batch array qualification has a failing gate")
    if not receipt["no_scientific_action"]:
        raise CloudManifestError("Batch qualification is marked scientific")
    return receipt

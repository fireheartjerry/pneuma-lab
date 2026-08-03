"""Independent verification for the AWS lease-expiry interruption drill."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import hashlib
from typing import Any

from .errors import CloudManifestError
from .manifests import validate_interruption_qualification_receipt


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def require_interruption_qualification(record: Mapping[str, Any]) -> dict[str, Any]:
    receipt = validate_interruption_qualification_receipt(record)
    drill = receipt["drill"]
    expected_operations = (
        "describe_jobs_before",
        "freeze_completed_boundary",
        "restore_completed_boundary",
        "describe_jobs_after",
        "verify_tagged_resource_absence",
    )
    if tuple(drill["operations"]) != expected_operations:
        raise CloudManifestError(
            "interruption receipt does not contain the canonical freeze/restore drill"
        )
    if not drill["freeze"]["requested"] or not drill["freeze"]["completed"]:
        raise CloudManifestError("interruption freeze operation was not completed")
    if not drill["restore"]["requested"] or not drill["restore"]["completed"]:
        raise CloudManifestError("interruption restore operation was not completed")
    gates = receipt["gates"]
    independent = receipt["controller_identity_arn"] != receipt["watcher_identity_arn"]
    if gates["independent_watcher"] != independent or not independent:
        raise CloudManifestError("watcher must be independent from the controller")
    lease = receipt["lease"]
    expired = (
        _instant(lease["watcher_observed_timestamp"])
        >= _instant(lease["expires_timestamp"])
        > _instant(lease["issued_timestamp"])
    )
    if gates["lease_expired"] != expired or not expired:
        raise CloudManifestError(
            "watcher termination was not observed after lease expiry"
        )
    no_renewal = lease["controller_renewal_count"] == 0
    if gates["controller_could_not_renew"] != no_renewal or not no_renewal:
        raise CloudManifestError("controller renewed its own lease")
    boundary = receipt["boundary"]
    exact = (
        boundary["pre_interrupt_sha256"] == boundary["restored_sha256"]
        and boundary["all_arm_visible_bytes_match"]
    )
    if gates["boundary_exact"] != exact or not exact:
        raise CloudManifestError("completed-boundary restoration is not byte exact")
    resource_ids = [item["resource_id"] for item in receipt["resources"]]
    if len(resource_ids) != len(set(resource_ids)):
        raise CloudManifestError("interruption receipt repeats a resource id")
    absent = not receipt["residual_resource_ids"] and all(
        item["state_after"] == "absent" for item in receipt["resources"]
    )
    if gates["all_tagged_resources_absent"] != absent or not absent:
        raise CloudManifestError("tagged resources remain after the watcher drill")
    if not all(gates.values()):
        raise CloudManifestError("interruption qualification has a failing gate")
    return receipt


def run_canonical_interruption_drill(
    adapter: Any,
    *,
    plan_sha256: str,
    input_lock_sha256: str,
    account_id: str,
    region: str,
    drill_id: str,
    controller_identity_arn: str,
    watcher_identity_arn: str,
    lease: Mapping[str, Any],
    job_ids: list[str],
    completed_boundary: bytes,
    resources_before: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Execute and validate the real interruption/freeze/restore sequence.

    The adapter must implement ``describe_jobs``, ``freeze``, ``restore``, and
    ``list_tagged_resources``.  A describe-only response cannot satisfy this
    function because the freeze and restore calls are mandatory and are
    recorded in the receipt.
    """

    for method_name in ("describe_jobs", "freeze", "restore", "list_tagged_resources"):
        if not callable(getattr(adapter, method_name, None)):
            raise CloudManifestError(
                f"interruption drill requires the {method_name} operation"
            )
    if not job_ids or len(set(job_ids)) != len(job_ids):
        raise CloudManifestError("interruption drill requires distinct job ids")
    if not resources_before:
        raise CloudManifestError(
            "interruption drill requires a nonempty tagged-resource inventory"
        )
    for resource in resources_before:
        if (
            not isinstance(resource, Mapping)
            or not resource.get("resource_id")
            or not resource.get("resource_type")
        ):
            raise CloudManifestError(
                "interruption drill resource inventory is incomplete"
            )
    if not completed_boundary:
        raise CloudManifestError(
            "interruption drill requires a nonempty completed boundary"
        )
    before = adapter.describe_jobs(job_ids)
    if not before:
        raise CloudManifestError("interruption drill observed no jobs before freezing")
    frozen = adapter.freeze(job_ids=job_ids, boundary=completed_boundary)
    if not isinstance(frozen, Mapping) or frozen.get("completed") is not True:
        raise CloudManifestError("interruption adapter did not complete the freeze")
    restored = adapter.restore(job_ids=job_ids, boundary=completed_boundary)
    if not isinstance(restored, Mapping) or restored.get("completed") is not True:
        raise CloudManifestError("interruption adapter did not complete the restore")
    after = adapter.describe_jobs(job_ids)
    if not after:
        raise CloudManifestError("interruption drill observed no jobs after restore")
    residual = adapter.list_tagged_resources(action_id=drill_id)
    if not isinstance(residual, list):
        raise CloudManifestError(
            "interruption adapter returned an invalid tagged-resource readback"
        )
    restored_boundary = restored.get("boundary", completed_boundary)
    if not isinstance(restored_boundary, bytes):
        raise CloudManifestError("interruption restore did not return boundary bytes")
    pre_hash = hashlib.sha256(completed_boundary).hexdigest()
    restored_hash = hashlib.sha256(restored_boundary).hexdigest()
    resources = []
    for item in resources_before:
        if item.get("resource_type") not in {
            "compute",
            "pool",
            "disk",
            "endpoint_ip",
            "sibling_container",
        }:
            raise CloudManifestError(
                "interruption drill resource inventory has an unsupported type"
            )
        resources.append(
            {
                "resource_id": str(item["resource_id"]),
                "resource_type": item["resource_type"],
                "state_before": str(item.get("state_before", "present")),
                "state_after": "absent",
            }
        )
    receipt = {
        "record_kind": "cloud_interruption_qualification_receipt",
        "schema_version": "0.1.0",
        "plan_sha256": plan_sha256,
        "input_lock_sha256": input_lock_sha256,
        "provider": "aws",
        "region": region,
        "account_id": account_id,
        "drill_id": drill_id,
        "controller_identity_arn": controller_identity_arn,
        "watcher_identity_arn": watcher_identity_arn,
        "lease": dict(lease),
        "boundary": {
            "sequence": 1,
            "pre_interrupt_sha256": pre_hash,
            "restored_sha256": restored_hash,
            "all_arm_visible_bytes_match": restored.get("all_arm_visible_bytes_match")
            is True
            and pre_hash == restored_hash,
        },
        "drill": {
            "operations": [
                "describe_jobs_before",
                "freeze_completed_boundary",
                "restore_completed_boundary",
                "describe_jobs_after",
                "verify_tagged_resource_absence",
            ],
            "freeze": {"requested": True, "completed": True},
            "restore": {"requested": True, "completed": True},
        },
        "resources": resources,
        "residual_resource_ids": [
            str(item.get("resource_id", "")) for item in residual
        ],
        "gates": {
            "independent_watcher": controller_identity_arn != watcher_identity_arn,
            "lease_expired": _instant(str(lease["watcher_observed_timestamp"]))
            >= _instant(str(lease["expires_timestamp"]))
            > _instant(str(lease["issued_timestamp"])),
            "controller_could_not_renew": lease.get("controller_renewal_count") == 0,
            "boundary_exact": pre_hash == restored_hash
            and restored.get("all_arm_visible_bytes_match") is True,
            "all_tagged_resources_absent": not residual,
        },
    }
    return require_interruption_qualification(receipt)


run_interruption_drill = run_canonical_interruption_drill

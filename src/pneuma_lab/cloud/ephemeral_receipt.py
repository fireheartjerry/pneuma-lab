"""Build and validate the immutable two-worker qualification receipt."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Any

from .authorization_keys import authorization_body_digest
from .errors import CloudManifestError
from .manifests import validate_ephemeral_dual_worker_qualification_receipt
from .qualification_execution import (
    BatchAdmissionError,
    QUALIFICATION_FIXTURE_MODEL,
    QUALIFICATION_FIXTURE_REVISION,
    worker_artifact_uri,
)


_DIGEST_LENGTH = 64


def _digest(value: Any, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != _DIGEST_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CloudManifestError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _hash_identifier(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CloudManifestError(f"{field} must be a nonempty identifier")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _signature_digest(record: Mapping[str, Any], *, field: str) -> str:
    approval = record.get("human_authorization")
    if not isinstance(approval, Mapping):
        raise CloudManifestError(f"{field} has no human authorization")
    signature = approval.get("signature_ed25519")
    if not isinstance(signature, str):
        raise CloudManifestError(f"{field} has no Ed25519 signature")
    try:
        signature_bytes = bytes.fromhex(signature)
    except ValueError as exc:
        raise CloudManifestError(f"{field} has a malformed Ed25519 signature") from exc
    if len(signature_bytes) != 64:
        raise CloudManifestError(f"{field} has a non-Ed25519 signature length")
    return hashlib.sha256(signature_bytes).hexdigest()


def validate_authority_evidence(
    authority: Mapping[str, Any],
    *,
    package_bytes: bytes,
    envelope: Mapping[str, Any],
    admission: Mapping[str, Any],
    action_id: str,
    region: str,
    plan: Mapping[str, Any],
    projected_cost_usd: float,
    iam_simulation_matrix_sha256: str,
) -> dict[str, Any]:
    """Recheck authority evidence before it is copied into a run receipt."""

    if not isinstance(authority, Mapping):
        raise CloudManifestError("authority receipt must be an object")
    if authority.get("status") != "authorized_and_verified":
        raise CloudManifestError("authority receipt is not authorized_and_verified")
    if authority.get("qualification_only") is not True:
        raise CloudManifestError("authority receipt is not qualification-only")
    if authority.get("action_id") != action_id or authority.get("provider") != "aws":
        raise CloudManifestError("authority receipt action or provider differs")
    if authority.get("region") != region:
        raise CloudManifestError("authority receipt region differs")
    package_sha = _digest(authority.get("signed_package_sha256"), field="signed package")
    if hashlib.sha256(package_bytes).hexdigest() != package_sha:
        raise CloudManifestError("signed package bytes differ from authority receipt")
    try:
        package = json.loads(package_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudManifestError("signed package is not UTF-8 JSON") from exc
    if not isinstance(package, Mapping):
        raise CloudManifestError("signed package is not an object")
    if package.get("record_kind") != "cloud_preparation_signing_package":
        raise CloudManifestError("signed package has the wrong record kind")
    if package.get("envelope") != dict(envelope) or package.get("admission") != dict(admission):
        raise CloudManifestError("signed package does not contain the exact authority records")

    saved_plan_sha = _digest(plan.get("saved_plan_sha256"), field="saved plan")
    show_sha = _digest(plan.get("terraform_show_sha256"), field="Terraform show")
    binding_sha = _digest(
        plan.get("terraform_plan_binding_sha256"), field="Terraform plan binding"
    )
    for field, value in (
        ("saved_plan_sha256", saved_plan_sha),
        ("terraform_show_sha256", show_sha),
        ("terraform_plan_binding_sha256", binding_sha),
    ):
        if authority.get(field) != value or package.get(field) != value:
            raise CloudManifestError(f"authority {field} differs from the execution plan")

    image = plan.get("image") or plan.get("gpu_worker_image")
    if not isinstance(image, str) or "@sha256:" not in image:
        raise CloudManifestError("execution plan lacks an immutable image digest")
    image_digest = image.rsplit("@", 1)[1]
    if authority.get("image_digest") != image_digest:
        raise CloudManifestError("authority image digest differs from the execution plan")
    if float(authority.get("projected_cost_usd")) != float(projected_cost_usd):
        raise CloudManifestError("authority projection differs from the execution projection")
    if authority.get("max_retries") != 0:
        raise CloudManifestError("authority receipt permits retries")
    _digest(iam_simulation_matrix_sha256, field="IAM simulation matrix")
    _digest(authority.get("iam_policy_sha256"), field="IAM policy")

    for label, record in (("envelope", envelope), ("admission", admission)):
        body_sha = authorization_body_digest(record)
        approval = record.get("human_authorization")
        if not isinstance(approval, Mapping):
            raise CloudManifestError(f"{label} has no human authorization")
        if approval.get("body_sha256") != body_sha:
            raise CloudManifestError(f"{label} body digest is not canonical")
        record_evidence = authority.get(label)
        if not isinstance(record_evidence, Mapping):
            raise CloudManifestError(f"authority receipt has no {label} evidence")
        if record_evidence.get("body_sha256") != body_sha:
            raise CloudManifestError(f"authority {label} body digest differs")
        signature_sha = _signature_digest(record, field=label)
        if record_evidence.get("signature_sha256") != signature_sha:
            raise CloudManifestError(f"authority {label} signature digest differs")

    kms = authority.get("kms")
    if not isinstance(kms, Mapping):
        raise CloudManifestError("authority receipt has no KMS verification")
    if (
        kms.get("signing_algorithm") != "ED25519_SHA_512"
        or kms.get("envelope_signature_valid") is not True
        or kms.get("admission_signature_valid") is not True
    ):
        raise CloudManifestError("KMS authority verification is not green")
    return dict(authority)


def _children(evidence: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = evidence.get("children")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def _child_status_rows(children: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for child in children:
        array = child.get("arrayProperties") or {}
        index = array.get("index") if isinstance(array, Mapping) else None
        attempts = child.get("attempts") or []
        if not isinstance(attempts, list):
            attempts = []
        status_reason = child.get("statusReason") or child.get("status_reason")
        if not isinstance(status_reason, str) or not status_reason:
            status_reason = "no provider status reason recorded"
        container = child.get("container") or {}
        started = isinstance(container, Mapping) and bool(container.get("instanceId"))
        rows.append(
            {
                "array_index": index,
                "status": child.get("status"),
                "status_reason": status_reason,
                "attempt_count": len(attempts),
                "worker_started": started,
            }
        )
    return rows


def _durations(children: Sequence[Mapping[str, Any]]) -> list[float]:
    durations: list[float] = []
    for child in children:
        started = child.get("startedAt")
        stopped = child.get("stoppedAt")
        if isinstance(started, (int, float)) and isinstance(stopped, (int, float)):
            durations.append((stopped - started) / 1000.0)
    return durations


def _teardown(absence: Mapping[str, Any]) -> dict[str, Any]:
    required = (
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
    if not all(absence.get(key) is True for key in required):
        raise CloudManifestError("cannot emit a receipt before complete provider absence")
    history = absence.get("provider_history")
    if not isinstance(history, Mapping):
        raise CloudManifestError("provider absence lacks inactive job-definition history evidence")
    artifact = absence.get("artifact_prefix")
    if not isinstance(artifact, Mapping) or artifact.get("empty") is not True:
        raise CloudManifestError("provider absence lacks an empty output-prefix proof")
    inactive_digest = history.get("inactive_job_definition_arn_sha256")
    if inactive_digest is not None:
        _digest(inactive_digest, field="inactive job-definition ARN")
    return {
        "live_jobs_absent": True,
        "compute_environment_absent": True,
        "queue_absent": True,
        "active_job_definition_absent": True,
        "inactive_job_definition_history_retained_by_aws": bool(
            history.get("inactive_job_definition_history_retained_by_aws")
        ),
        "inactive_job_definition_arn_sha256": inactive_digest,
        "launch_template_absent": True,
        "instances_absent": True,
        "volumes_absent": True,
        "network_interfaces_absent": True,
        "security_group_absent": True,
        "output_prefix_empty": True,
        "teardown_complete_except_provider_history": True,
        "absence_note": (
            "AWS retains inactive job-definition provider history."
            if history.get("inactive_job_definition_history_retained_by_aws")
            else "No inactive job-definition history was returned."
        ),
    }


def _authority_field(
    authority: Mapping[str, Any], section: str, field: str
) -> Any:
    record = authority.get(section)
    if not isinstance(record, Mapping):
        raise CloudManifestError(f"authority receipt has no {section} evidence")
    return record.get(field)


def build_ephemeral_qualification_receipt(
    context: Mapping[str, Any],
    *,
    action_id: str,
    region: str,
    authority: Mapping[str, Any],
    iam_simulation_matrix_sha256: str,
    output_root: str,
) -> dict[str, Any]:
    """Serialize only a complete post-launch lifecycle into a schema receipt."""

    parent_job_id = context.get("parent_job_id")
    if not isinstance(parent_job_id, str) or not parent_job_id:
        raise CloudManifestError("a final execution receipt requires a submitted parent job")
    plan = context.get("plan")
    if not isinstance(plan, Mapping):
        raise CloudManifestError("execution context lacks the exact parsed plan")
    evidence = context.get("evidence")
    evidence = evidence if isinstance(evidence, Mapping) else {}
    children = _children(evidence)
    failure = context.get("failure")
    cleanup_failure = context.get("cleanup_failure")
    status = "passed" if failure is None and cleanup_failure is None else "no_go"
    image = plan.get("image") or plan.get("gpu_worker_image")
    if not isinstance(image, str) or "@sha256:" not in image:
        raise CloudManifestError("execution context lacks an immutable image")
    image_digest = image.rsplit("@", 1)[1]
    if not image_digest.startswith("sha256:"):
        raise CloudManifestError("execution image is not a SHA-256 digest")
    if plan.get("qualification_model") != QUALIFICATION_FIXTURE_MODEL:
        raise CloudManifestError("execution receipt would not be fixture-only")
    if plan.get("qualification_model_revision") != QUALIFICATION_FIXTURE_REVISION:
        raise CloudManifestError("execution receipt would not bind the fixture revision")
    launch = context.get("launch")
    if not isinstance(launch, Mapping):
        raise CloudManifestError("execution context lacks CloudTrail launch evidence")
    launch = dict(launch)
    launch.update(
        {
            "image_digest": image_digest,
            "qualification_model": QUALIFICATION_FIXTURE_MODEL,
            "qualification_model_revision": QUALIFICATION_FIXTURE_REVISION,
            "parent_job_id_sha256": _hash_identifier(
                parent_job_id, field="parent Batch job id"
            ),
        }
    )
    if len(children) != 2:
        raise CloudManifestError(
            "execution receipt requires exactly two described array children"
        )
    child_job_hashes: list[str] = []
    child_indices: list[int] = []
    for child in children:
        child_job_id = child.get("jobId") or child.get("job_id")
        child_job_hashes.append(_hash_identifier(child_job_id, field="child Batch job id"))
        array = child.get("arrayProperties") or {}
        index = array.get("index") if isinstance(array, Mapping) else None
        if type(index) is not int or index not in (0, 1):
            raise CloudManifestError(
                "execution receipt child array indexes must be exactly 0 and 1"
            )
        child_indices.append(index)
    if sorted(child_indices) != [0, 1] or len(set(child_job_hashes)) != 2:
        raise CloudManifestError(
            "execution receipt child job ids and indexes must be distinct"
        )
    launch["child_job_id_sha256"] = child_job_hashes
    for field in (
        "cloudtrail_submit_job_event_id_sha256",
        "submit_event_time_utc",
    ):
        if field not in launch:
            raise CloudManifestError(f"execution launch evidence lacks {field}")
    durations = _durations(children)
    raw_rows: list[dict[str, Any]] = []
    raw = evidence.get("raw_evidence")
    if isinstance(raw, Mapping):
        for index in (0, 1):
            payload = raw.get(index) or raw.get(str(index))
            if isinstance(payload, (bytes, bytearray)) and payload:
                raw_bytes = bytes(payload)
                raw_rows.append(
                    {
                        "worker_index": index,
                        "uri": worker_artifact_uri(output_root, index),
                        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                        "size_bytes": len(raw_bytes),
                    }
                )
    instance_ids = evidence.get("instance_ids")
    if not isinstance(instance_ids, Sequence) or isinstance(
        instance_ids, (str, bytes, bytearray)
    ):
        instance_ids = ()
    if status == "passed" and len(instance_ids) != 2:
        raise CloudManifestError(
            "qualification success requires two worker identity observations"
        )
    if status == "passed":
        if evidence.get("parent_status") != "SUCCEEDED" or any(
            child.get("status") != "SUCCEEDED" for child in children
        ):
            raise CloudManifestError(
                "qualification success requires a succeeded parent and both children"
            )
        if len(set(instance_ids)) != 2:
            raise CloudManifestError(
                "qualification success requires two distinct worker identities"
            )
    absence = context.get("absence")
    if not isinstance(absence, Mapping):
        raise CloudManifestError("execution context lacks provider absence evidence")
    artifact = absence.get("artifact_prefix")
    object_count = artifact.get("object_count") if isinstance(artifact, Mapping) else None
    if type(object_count) is not int or object_count < 0:
        raise CloudManifestError("provider absence lacks an output object count")
    if status == "passed" and (len(raw_rows) != 2 or object_count != 2):
        raise CloudManifestError(
            "qualification success requires exactly two raw output objects"
        )
    recovery = context.get("recovery")
    if status == "passed":
        if not isinstance(recovery, Mapping):
            raise CloudManifestError(
                "qualification success requires the freeze/restore recovery receipt"
            )
        if (
            recovery.get("restored_completed_boundary") is not True
            or tuple(recovery.get("operations", ()))
            != (
                "describe_jobs_before",
                "freeze_completed_boundary",
                "restore_completed_boundary",
                "describe_jobs_after",
            )
            or recovery.get("freeze") != {"requested": True, "completed": True}
            or recovery.get("restore") != {"requested": True, "completed": True}
        ):
            raise CloudManifestError(
                "qualification success requires an exact freeze/restore recovery receipt"
            )
        recovery_record = {
            "run": True,
            "boundary_sha256": _digest(
                recovery.get("boundary_sha256"), field="recovery boundary"
            ),
        }
    elif isinstance(recovery, Mapping):
        recovery_record = {
            "run": True,
            "boundary_sha256": recovery.get("boundary_sha256"),
        }
    else:
        recovery_record = {
            "run": False,
            "reason": "Admission did not reach two successful children.",
        }
    receipt: dict[str, Any] = {
        "record_kind": "cloud_ephemeral_dual_worker_qualification_receipt",
        "schema_version": "0.1.0",
        "status": status,
        "qualification_only": True,
        "action_id": action_id,
        "provider": "aws",
        "region": region,
        "terminal_outcome": (
            "qualification_passed" if status == "passed" else "post_launch_terminal_no_go"
        ),
        "launch": launch,
        "plan": {
            "saved_plan_sha256": plan.get("saved_plan_sha256"),
            "terraform_show_sha256": plan.get("terraform_show_sha256"),
            "terraform_plan_binding_sha256": plan.get("terraform_plan_binding_sha256"),
        },
        "authority": {
            "package_sha256": authority.get("signed_package_sha256"),
            "envelope_body_sha256": _authority_field(authority, "envelope", "body_sha256"),
            "admission_body_sha256": _authority_field(authority, "admission", "body_sha256"),
            "envelope_signature_sha256": _authority_field(
                authority, "envelope", "signature_sha256"
            ),
            "admission_signature_sha256": _authority_field(
                authority, "admission", "signature_sha256"
            ),
            "signature_algorithm": _authority_field(
                authority, "kms", "signing_algorithm"
            ),
            "action_policy_sha256": authority.get("iam_policy_sha256"),
            "iam_simulation_matrix_sha256": iam_simulation_matrix_sha256,
        },
        "spot_projection": {
            "instance_type": "g6e.2xlarge",
            "worker_count": 2,
            "worker_seconds_ceiling": 3600,
            "projected_cost_usd": float(context.get("projected_cost_usd")),
            "strictly_below_usd_100": float(context.get("projected_cost_usd")) < 100,
            "observed_worker_duration_seconds": durations,
            "observed_worker_duration_note": (
                "No worker reached STARTING/RUNNING; both children had zero attempts."
                if not durations
                else "Durations are derived from the two Batch child timestamps."
            ),
        },
        "workers": {
            "worker_identity_sha256": [
                _hash_identifier(value, field="worker identity") for value in instance_ids
            ],
            "raw_artifacts": raw_rows,
            "raw_artifact_prefix_object_count": object_count,
            "recovery": recovery_record,
        },
        "teardown": _teardown(absence),
    }
    if status == "no_go":
        reason: dict[str, Any] = {
            "kind": (
                "batch_children_failed_before_execution"
                if isinstance(failure, BatchAdmissionError)
                else "qualification_lifecycle_terminal_failure"
            ),
            "qualification_pass_impossible": True,
            "no_retry_after_launch": True,
        }
        parent = evidence.get("parent")
        if not isinstance(parent, Mapping):
            parent = {}
        if parent.get("status") is not None:
            reason["parent_status"] = parent.get("status")
        parent_reason = parent.get("statusReason") or parent.get("status_reason")
        if isinstance(parent_reason, str) and parent_reason:
            reason["parent_status_reason"] = parent_reason
        child_rows = _child_status_rows(children)
        if child_rows:
            reason["child_statuses"] = child_rows
        receipt["no_go_reason"] = reason
    return validate_ephemeral_dual_worker_qualification_receipt(receipt)

"""Exact, sanitized IAM simulation for the dual-worker qualification.

The qualification receipt must be derived from a live AWS IAM simulation, not
from a caller-provided digest.  This module keeps the resource names sent to
AWS private to the provider call and retains only action labels, resource
digests, decisions, and the effective policy digest.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
from typing import Any

from .authorization_keys import canonical_bytes
from .errors import CloudManifestError
from .qualification_execution import parse_s3_uri, worker_artifact_uri


ALLOWED_CHECK_IDS = (
    "input-read-protocol",
    "input-read-architecture",
    "input-read-authorization",
    "input-read-image",
    "input-read-input-lock",
    "raw-write-worker-0",
    "raw-write-worker-1",
)
DENIED_CHECK_IDS = (
    "output-read-worker-0",
    "output-read-worker-1",
    "wrong-worker-output",
    "other-action-input",
    "unrelated-object",
    "bucket-list",
    "output-delete",
    "output-abort",
)
ALL_CHECK_IDS = ALLOWED_CHECK_IDS + DENIED_CHECK_IDS


def _digest(value: Any, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CloudManifestError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _s3_arn(uri: str) -> str:
    location = parse_s3_uri(uri)
    return f"arn:aws:s3:::{location.bucket}/{location.key}"


def _bucket_arn(uri: str) -> str:
    location = parse_s3_uri(uri.rstrip("/") + "/marker")
    return f"arn:aws:s3:::{location.bucket}"


def expected_checks(
    *, input_paths: Mapping[str, Any], output_root: str
) -> tuple[dict[str, str], ...]:
    """Return the fixed action/resource matrix for one exact qualification."""

    if set(input_paths) != {"protocol", "architecture", "authorization", "image", "input_lock"}:
        raise CloudManifestError("IAM simulation requires the five fixed fixture inputs")
    if not all(isinstance(value, str) for value in input_paths.values()):
        raise CloudManifestError("IAM simulation fixture inputs must be S3 URIs")
    output_uris = tuple(worker_artifact_uri(output_root, index) for index in (0, 1))
    output_ref = parse_s3_uri(output_root.rstrip("/") + "/marker")
    output_parent = output_ref.key.rsplit("/", 1)[0]
    action_parent = output_parent.rsplit("/", 1)[0]
    other_action_uri = (
        f"s3://{output_ref.bucket}/{action_parent.rsplit('/', 1)[0]}"
        "/other-action/inputs/protocol.json"
    )
    unrelated_uri = f"s3://{output_ref.bucket}/qualification-unrelated/object"
    wrong_worker_uri = output_uris[0].replace("/worker-0/", "/worker-2/")
    rows = (
        ("input-read-protocol", "s3:GetObject", _s3_arn(input_paths["protocol"]), "allowed"),
        ("input-read-architecture", "s3:GetObject", _s3_arn(input_paths["architecture"]), "allowed"),
        ("input-read-authorization", "s3:GetObject", _s3_arn(input_paths["authorization"]), "allowed"),
        ("input-read-image", "s3:GetObject", _s3_arn(input_paths["image"]), "allowed"),
        ("input-read-input-lock", "s3:GetObject", _s3_arn(input_paths["input_lock"]), "allowed"),
        ("raw-write-worker-0", "s3:PutObject", _s3_arn(output_uris[0]), "allowed"),
        ("raw-write-worker-1", "s3:PutObject", _s3_arn(output_uris[1]), "allowed"),
        ("output-read-worker-0", "s3:GetObject", _s3_arn(output_uris[0]), "denied"),
        ("output-read-worker-1", "s3:GetObject", _s3_arn(output_uris[1]), "denied"),
        ("wrong-worker-output", "s3:PutObject", _s3_arn(wrong_worker_uri), "denied"),
        ("other-action-input", "s3:GetObject", _s3_arn(other_action_uri), "denied"),
        ("unrelated-object", "s3:GetObject", _s3_arn(unrelated_uri), "denied"),
        ("bucket-list", "s3:ListBucket", _bucket_arn(output_root), "denied"),
        ("output-delete", "s3:DeleteObject", _s3_arn(output_uris[0]), "denied"),
        ("output-abort", "s3:AbortMultipartUpload", _s3_arn(output_uris[0]), "denied"),
    )
    checks = tuple(
        {
            "id": check_id,
            "action": action,
            "resource_arn": resource,
            "expected": expected,
        }
        for check_id, action, resource, expected in rows
    )
    if tuple(row["id"] for row in checks) != ALL_CHECK_IDS:
        raise CloudManifestError("IAM simulation matrix does not have the fixed check order")
    return checks


def _matrix_payload(
    *,
    action_id: str,
    role_arn: str,
    effective_policy_sha256: str,
    checks: tuple[Mapping[str, str], ...],
    observed: Mapping[str, str],
) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for check in checks:
        check_id = check["id"]
        decision = observed.get(check_id)
        if decision not in {"allowed", "denied"}:
            raise CloudManifestError(f"IAM simulation omitted {check_id}")
        rows.append(
            {
                "id": check_id,
                "action": check["action"],
                "resource_sha256": hashlib.sha256(
                    check["resource_arn"].encode("utf-8")
                ).hexdigest(),
                "expected": check["expected"],
                "observed": decision,
            }
        )
    payload = {
        "record_kind": "cloud_iam_simulation_matrix",
        "schema_version": "0.1.0",
        "action_id": action_id,
        "policy_source_role_arn_sha256": hashlib.sha256(
            role_arn.encode("utf-8")
        ).hexdigest(),
        "effective_policy_sha256": _digest(
            effective_policy_sha256, field="effective IAM policy"
        ),
        "checks": rows,
        "all_expected_decisions_match": all(
            row["expected"] == row["observed"] for row in rows
        ),
    }
    return payload


def _with_digest(payload: Mapping[str, Any]) -> dict[str, Any]:
    record = dict(payload)
    record["matrix_sha256"] = hashlib.sha256(canonical_bytes(record)).hexdigest()
    return record


def validate_iam_simulation_matrix(
    record: Mapping[str, Any],
    *,
    action_id: str,
    plan: Mapping[str, Any],
    expected_policy_sha256: str,
) -> dict[str, Any]:
    """Recompute and validate the complete sanitized matrix."""

    if not isinstance(record, Mapping):
        raise CloudManifestError("IAM simulation evidence must be an object")
    if record.get("record_kind") != "cloud_iam_simulation_matrix":
        raise CloudManifestError("IAM simulation evidence has the wrong record kind")
    if record.get("schema_version") != "0.1.0" or record.get("action_id") != action_id:
        raise CloudManifestError("IAM simulation evidence is not bound to the action")
    role_arn = plan.get("worker_role_arn")
    if not isinstance(role_arn, str) or not role_arn:
        raise CloudManifestError("IAM simulation plan lacks the attached worker role ARN")
    expected_role_hash = hashlib.sha256(role_arn.encode("utf-8")).hexdigest()
    if record.get("policy_source_role_arn_sha256") != expected_role_hash:
        raise CloudManifestError("IAM simulation source role differs from the plan")
    if record.get("effective_policy_sha256") != _digest(
        expected_policy_sha256, field="effective IAM policy"
    ):
        raise CloudManifestError("IAM simulation policy hash differs from authority")
    checks = expected_checks(
        input_paths=plan.get("input_paths", {}),
        output_root=str(plan.get("output_path", "")),
    )
    rows = record.get("checks")
    if not isinstance(rows, list) or len(rows) != len(checks):
        raise CloudManifestError("IAM simulation evidence does not contain all fixed checks")
    for expected, row in zip(checks, rows, strict=True):
        if not isinstance(row, Mapping):
            raise CloudManifestError("IAM simulation contains an invalid check row")
        if (
            row.get("id") != expected["id"]
            or row.get("action") != expected["action"]
            or row.get("resource_sha256")
            != hashlib.sha256(expected["resource_arn"].encode("utf-8")).hexdigest()
            or row.get("expected") != expected["expected"]
            or row.get("observed") not in {"allowed", "denied"}
        ):
            raise CloudManifestError(f"IAM simulation row differs for {expected['id']}")
    if record.get("all_expected_decisions_match") is not True or any(
        row["expected"] != row["observed"] for row in rows
    ):
        raise CloudManifestError("IAM simulation did not pass every expected decision")
    without_digest = {key: value for key, value in record.items() if key != "matrix_sha256"}
    if record.get("matrix_sha256") != hashlib.sha256(
        canonical_bytes(without_digest)
    ).hexdigest():
        raise CloudManifestError("IAM simulation matrix digest is not derived from its bytes")
    return dict(record)


def run_iam_simulation(
    call: Callable[..., Any],
    *,
    plan: Mapping[str, Any],
    action_id: str,
    expected_policy_sha256: str,
) -> dict[str, Any]:
    """Run one exact IAM simulation per expected action/resource pair."""

    role_arn = plan.get("worker_role_arn")
    if not isinstance(role_arn, str) or not role_arn:
        raise CloudManifestError("IAM simulation requires the planned worker role ARN")
    checks = expected_checks(
        input_paths=plan.get("input_paths", {}),
        output_root=str(plan.get("output_path", "")),
    )
    observed: dict[str, str] = {}
    for check in checks:
        response = call(
            "iam",
            "simulate-principal-policy",
            "--policy-source-arn",
            role_arn,
            "--action-names",
            check["action"],
            "--resource-arns",
            check["resource_arn"],
        )
        results = response.get("EvaluationResults", []) if isinstance(response, Mapping) else []
        if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], Mapping):
            raise CloudManifestError(f"IAM simulation returned an invalid result for {check['id']}")
        result = results[0]
        if result.get("EvalActionName") != check["action"] or result.get(
            "EvalResourceName"
        ) != check["resource_arn"]:
            raise CloudManifestError(f"IAM simulation result was not bound for {check['id']}")
        decision = result.get("EvalDecision")
        if decision == "allowed":
            observed[check["id"]] = "allowed"
        elif decision in {"implicitDeny", "explicitDeny"}:
            observed[check["id"]] = "denied"
        else:
            raise CloudManifestError(f"IAM simulation returned an unknown decision for {check['id']}")
    payload = _matrix_payload(
        action_id=action_id,
        role_arn=role_arn,
        effective_policy_sha256=expected_policy_sha256,
        checks=checks,
        observed=observed,
    )
    record = _with_digest(payload)
    return validate_iam_simulation_matrix(
        record,
        action_id=action_id,
        plan=plan,
        expected_policy_sha256=expected_policy_sha256,
    )

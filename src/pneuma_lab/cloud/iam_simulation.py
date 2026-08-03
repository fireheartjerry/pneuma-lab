"""Exact, sanitized IAM simulation for the dual-worker qualification.

The qualification receipt must be derived from a live AWS IAM simulation, not
from a caller-provided digest.  This module keeps the resource names sent to
AWS private to the provider call and retains only action labels, resource
digests, decisions, and the effective policy digest.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
import json
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
    "kms-decrypt",
    "iam-policy-admin",
)
ALL_CHECK_IDS = ALLOWED_CHECK_IDS + DENIED_CHECK_IDS
QUALIFICATION_WORKER_POLICY_NAME = "bounded-experiment-access"


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


def _resource_policy_sha256(resource_policy: Mapping[str, Any] | None) -> str | None:
    if resource_policy is None:
        return None
    if not isinstance(resource_policy, Mapping):
        raise CloudManifestError("IAM resource policy must be a JSON object")
    try:
        payload = canonical_bytes(dict(resource_policy))
    except (TypeError, ValueError) as exc:
        raise CloudManifestError("IAM resource policy is not canonical JSON") from exc
    return hashlib.sha256(payload).hexdigest()


def policy_document_sha256(policy: Mapping[str, Any]) -> str:
    """Hash one live IAM policy document without retaining its contents."""

    if not isinstance(policy, Mapping):
        raise CloudManifestError("IAM policy document must be a JSON object")
    try:
        payload = canonical_bytes(dict(policy))
    except (TypeError, ValueError) as exc:
        raise CloudManifestError("IAM policy document is not canonical JSON") from exc
    return hashlib.sha256(payload).hexdigest()


def _string_values(value: Any, *, field: str) -> tuple[str, ...]:
    values = (value,) if isinstance(value, str) else value
    if not isinstance(values, (list, tuple)) or not values or not all(
        isinstance(item, str) and item for item in values
    ):
        raise CloudManifestError(f"IAM policy {field} must contain nonempty strings")
    return tuple(values)


def _policy_statements(policy: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    statements = policy.get("Statement")
    if isinstance(statements, Mapping):
        statements = (statements,)
    if not isinstance(statements, (list, tuple)) or not all(
        isinstance(statement, Mapping) for statement in statements
    ):
        raise CloudManifestError("IAM policy Statement must be an object or list")
    return tuple(statements)


def _expected_s3_resources(
    *, input_paths: Mapping[str, Any], output_root: str, iam_role_arn: str
) -> dict[str, frozenset[str]]:
    checks = expected_checks(
        input_paths=input_paths,
        output_root=output_root,
        iam_role_arn=iam_role_arn,
    )
    return {
        action: frozenset(
            row["resource_arn"] for row in checks if row["action"] == action
        )
        for action in ("s3:GetObject", "s3:PutObject")
    }


def validate_worker_policy_documents(
    policy_documents: tuple[tuple[str, str, Mapping[str, Any]], ...],
    *,
    input_paths: Mapping[str, Any],
    output_root: str,
    iam_role_arn: str,
) -> dict[str, Any]:
    """Prove every worker-role S3 allow is within the exact action objects.

    Non-S3 permissions in unrelated policies are preserved.  Any S3 allow
    outside the five fixture reads and two raw writes is rejected, including a
    wildcard resource, wildcard action, NotAction, or NotResource grant.
    Only hashes and counts leave this function.
    """

    expected = _expected_s3_resources(
        input_paths=input_paths,
        output_root=output_root,
        iam_role_arn=iam_role_arn,
    )
    rows: list[dict[str, str]] = []
    for source, identifier, policy in policy_documents:
        if source not in {"inline", "managed"} or not isinstance(identifier, str) or not identifier:
            raise CloudManifestError("IAM policy inventory has an invalid policy identity")
        if not isinstance(policy, Mapping):
            raise CloudManifestError("IAM policy inventory contains a non-object policy")
        for statement in _policy_statements(policy):
            if statement.get("Effect") != "Allow":
                continue
            if "NotAction" in statement or "NotResource" in statement:
                raise CloudManifestError(
                    "worker role contains an allow policy with NotAction or NotResource"
                )
            actions = _string_values(statement.get("Action"), field="Action")
            s3_actions = tuple(
                action
                for action in actions
                if action == "*" or action.lower().startswith("s3:")
            )
            if not s3_actions:
                continue
            resources = frozenset(
                _string_values(statement.get("Resource"), field="Resource")
            )
            for action in s3_actions:
                allowed = expected.get(action)
                if allowed is None or not resources <= allowed:
                    raise CloudManifestError(
                        "worker role contains an S3 allow outside the exact qualification objects"
                    )
        rows.append(
            {
                "source": source,
                "identifier_sha256": hashlib.sha256(
                    identifier.encode("utf-8")
                ).hexdigest(),
                "document_sha256": policy_document_sha256(policy),
            }
        )
    if not rows:
        raise CloudManifestError("worker role policy inventory is empty")
    record: dict[str, Any] = {
        "schema_version": "0.1.0",
        "policies": sorted(rows, key=lambda row: (row["source"], row["identifier_sha256"])),
    }
    record["inventory_sha256"] = hashlib.sha256(canonical_bytes(record)).hexdigest()
    return record


def _resource_policy_applies_to_role(
    statement: Mapping[str, Any], *, iam_role_arn: str
) -> bool:
    """Conservatively decide whether an Allow could apply to the worker role."""

    if "NotPrincipal" in statement:
        return True
    principal = statement.get("Principal")
    if principal == "*":
        return True
    values: list[str] = []
    if isinstance(principal, str):
        values.append(principal)
    elif isinstance(principal, Mapping):
        for value in principal.values():
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list) and all(
                isinstance(item, str) for item in value
            ):
                values.extend(value)
    account_id = iam_role_arn.split(":", 5)[4]
    account_root = f"arn:aws:iam::{account_id}:root"
    return any(value in {"*", iam_role_arn, account_root, account_id} for value in values)


def validate_worker_resource_policy(
    resource_policy: Mapping[str, Any],
    *,
    input_paths: Mapping[str, Any],
    output_root: str,
    iam_role_arn: str,
) -> None:
    """Reject resource-based S3 Allows that could grant the worker extra access."""

    expected = _expected_s3_resources(
        input_paths=input_paths,
        output_root=output_root,
        iam_role_arn=iam_role_arn,
    )
    for statement in _policy_statements(resource_policy):
        if statement.get("Effect") != "Allow" or not _resource_policy_applies_to_role(
            statement, iam_role_arn=iam_role_arn
        ):
            continue
        if "NotAction" in statement or "NotResource" in statement:
            raise CloudManifestError(
                "S3 bucket policy has an allow with NotAction or NotResource applying to the worker"
            )
        actions = _string_values(statement.get("Action"), field="Action")
        s3_actions = tuple(
            action
            for action in actions
            if action == "*" or action.lower().startswith("s3:")
        )
        if not s3_actions:
            continue
        resources = frozenset(_string_values(statement.get("Resource"), field="Resource"))
        for action in s3_actions:
            allowed = expected.get(action)
            if allowed is None or not resources <= allowed:
                raise CloudManifestError(
                    "S3 bucket policy grants the worker access outside the exact qualification objects"
                )


def validate_policy_inventory(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the sanitized policy inventory and its self-digest."""

    if not isinstance(record, Mapping) or set(record) != {
        "schema_version",
        "policies",
        "inventory_sha256",
    }:
        raise CloudManifestError("IAM policy inventory has an unregistered shape")
    if record.get("schema_version") != "0.1.0":
        raise CloudManifestError("IAM policy inventory has an unsupported version")
    policies = record.get("policies")
    if not isinstance(policies, list) or not policies:
        raise CloudManifestError("IAM policy inventory has no policies")
    for policy in policies:
        if not isinstance(policy, Mapping) or set(policy) != {
            "source",
            "identifier_sha256",
            "document_sha256",
        }:
            raise CloudManifestError("IAM policy inventory row has an unregistered shape")
        if policy.get("source") not in {"inline", "managed"}:
            raise CloudManifestError("IAM policy inventory row has an invalid source")
        _digest(policy.get("identifier_sha256"), field="IAM policy identifier")
        _digest(policy.get("document_sha256"), field="IAM policy document")
    unsigned = {key: value for key, value in record.items() if key != "inventory_sha256"}
    if record.get("inventory_sha256") != hashlib.sha256(canonical_bytes(unsigned)).hexdigest():
        raise CloudManifestError("IAM policy inventory digest is not derived from its bytes")
    return dict(record)


def expected_checks(
    *,
    input_paths: Mapping[str, Any],
    output_root: str,
    iam_role_arn: str,
) -> tuple[dict[str, str], ...]:
    """Return the fixed action/resource matrix for one exact qualification."""

    if set(input_paths) != {"protocol", "architecture", "authorization", "image", "input_lock"}:
        raise CloudManifestError("IAM simulation requires the five fixed fixture inputs")
    if not all(isinstance(value, str) for value in input_paths.values()):
        raise CloudManifestError("IAM simulation fixture inputs must be S3 URIs")
    if not isinstance(iam_role_arn, str) or not iam_role_arn:
        raise CloudManifestError("IAM simulation requires a concrete role ARN")
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
        ("kms-decrypt", "kms:Decrypt", "*", "denied"),
        ("iam-policy-admin", "iam:PutRolePolicy", iam_role_arn, "denied"),
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
    resource_policy: Mapping[str, Any] | None,
    policy_inventory: Mapping[str, Any] | None,
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
        "resource_policy_present": resource_policy is not None,
        "resource_policy_sha256": _resource_policy_sha256(resource_policy),
        "checks": rows,
        "all_expected_decisions_match": all(
            row["expected"] == row["observed"] for row in rows
        ),
    }
    if policy_inventory is not None:
        payload["policy_inventory"] = validate_policy_inventory(policy_inventory)
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
    resource_policy_present = record.get("resource_policy_present")
    if not isinstance(resource_policy_present, bool):
        raise CloudManifestError("IAM simulation lacks resource-policy presence evidence")
    resource_policy_sha256 = record.get("resource_policy_sha256")
    if resource_policy_present:
        _digest(resource_policy_sha256, field="IAM resource policy")
    elif resource_policy_sha256 is not None:
        raise CloudManifestError(
            "IAM simulation records a resource-policy digest without a policy"
        )
    if "policy_inventory" in record:
        validate_policy_inventory(record["policy_inventory"])
    checks = expected_checks(
        input_paths=plan.get("input_paths", {}),
        output_root=str(plan.get("output_path", "")),
        iam_role_arn=role_arn,
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
    resource_policy: Mapping[str, Any] | None = None,
    policy_inventory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one exact IAM simulation per expected action/resource pair."""

    role_arn = plan.get("worker_role_arn")
    if not isinstance(role_arn, str) or not role_arn:
        raise CloudManifestError("IAM simulation requires the planned worker role ARN")
    checks = expected_checks(
        input_paths=plan.get("input_paths", {}),
        output_root=str(plan.get("output_path", "")),
        iam_role_arn=role_arn,
    )
    observed: dict[str, str] = {}
    resource_policy_json: str | None = None
    if resource_policy is not None:
        if not isinstance(resource_policy, Mapping):
            raise CloudManifestError("IAM resource policy must be a JSON object")
        try:
            resource_policy_json = json.dumps(
                dict(resource_policy), sort_keys=True, separators=(",", ":")
            )
        except (TypeError, ValueError) as exc:
            raise CloudManifestError("IAM resource policy is not JSON-serializable") from exc
    for check in checks:
        arguments = [
            "iam",
            "simulate-principal-policy",
            "--policy-source-arn",
            role_arn,
            "--action-names",
            check["action"],
            "--resource-arns",
            check["resource_arn"],
        ]
        if resource_policy_json is not None and check["action"].startswith("s3:"):
            arguments.extend(("--resource-policy", resource_policy_json))
        response = call(*arguments)
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
        resource_policy=resource_policy,
        policy_inventory=policy_inventory,
    )
    record = _with_digest(payload)
    return validate_iam_simulation_matrix(
        record,
        action_id=action_id,
        plan=plan,
        expected_policy_sha256=expected_policy_sha256,
    )

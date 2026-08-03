from __future__ import annotations

import hashlib
import json

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.iam_simulation import (
    ALL_CHECK_IDS,
    expected_checks,
    run_iam_simulation,
    validate_iam_simulation_matrix,
    validate_worker_resource_policy,
    validate_worker_policy_documents,
)


def _plan() -> dict[str, object]:
    return {
        "worker_role_arn": "arn:aws:iam::123456789012:role/worker",
        "input_paths": {
            "protocol": "s3://bucket/runs/qualification/action/inputs/protocol.json",
            "architecture": "s3://bucket/runs/qualification/action/inputs/architecture.json",
            "authorization": "s3://bucket/runs/qualification/action/inputs/authorization.json",
            "image": "s3://bucket/runs/qualification/action/inputs/image.json",
            "input_lock": "s3://bucket/runs/qualification/action/inputs/input-lock.json",
        },
        "output_path": "s3://bucket/runs/qualification/action/outputs/",
    }


def test_live_matrix_is_exactly_bound_and_sanitized() -> None:
    plan = _plan()
    checks = expected_checks(
        input_paths=plan["input_paths"],
        output_root=plan["output_path"],
        iam_role_arn=plan["worker_role_arn"],
    )
    calls: list[tuple[str, str]] = []

    def call(*args: str) -> dict[str, list[dict[str, str]]]:
        action = args[args.index("--action-names") + 1]
        resource = args[args.index("--resource-arns") + 1]
        calls.append((action, resource))
        row = next(
            check
            for check in checks
            if check["action"] == action and check["resource_arn"] == resource
        )
        return {
            "EvaluationResults": [
                {
                    "EvalActionName": action,
                    "EvalResourceName": resource,
                    "EvalDecision": (
                        "allowed" if row["expected"] == "allowed" else "explicitDeny"
                    ),
                }
            ]
        }

    record = run_iam_simulation(
        call,
        plan=plan,
        action_id="action",
        expected_policy_sha256="a" * 64,
    )

    assert len(calls) == len(ALL_CHECK_IDS) == 17
    assert [row["id"] for row in record["checks"]] == list(ALL_CHECK_IDS)
    assert all("resource_arn" not in row for row in record["checks"])
    assert "arn:aws" not in json.dumps(record)
    assert record["all_expected_decisions_match"] is True

    tampered = dict(record)
    tampered["matrix_sha256"] = "b" * 64
    with pytest.raises(CloudManifestError, match="digest"):
        validate_iam_simulation_matrix(
            tampered,
            action_id="action",
            plan=plan,
            expected_policy_sha256="a" * 64,
        )


def test_live_matrix_can_include_a_canonical_bucket_policy_without_leaking_it() -> None:
    plan = _plan()
    checks = expected_checks(
        input_paths=plan["input_paths"],
        output_root=plan["output_path"],
        iam_role_arn=plan["worker_role_arn"],
    )
    policy = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": "*"}],
    }
    calls: list[tuple[str, ...]] = []

    def call(*args: str) -> dict[str, list[dict[str, str]]]:
        calls.append(args)
        action = args[args.index("--action-names") + 1]
        resource = args[args.index("--resource-arns") + 1]
        expected = next(
            row
            for row in checks
            if row["action"] == action and row["resource_arn"] == resource
        )
        if action.startswith("s3:"):
            assert "--resource-policy" in args
            assert json.loads(args[args.index("--resource-policy") + 1]) == policy
        else:
            assert "--resource-policy" not in args
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

    record = run_iam_simulation(
        call,
        plan=plan,
        action_id="action",
        expected_policy_sha256="a" * 64,
        resource_policy=policy,
    )
    assert record["resource_policy_present"] is True
    assert record["resource_policy_sha256"] == hashlib.sha256(
        json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert len(calls) == len(ALL_CHECK_IDS)
    assert "Statement" not in json.dumps(record)


def test_worker_policy_inventory_accepts_only_the_exact_action_objects() -> None:
    plan = _plan()
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

    record = validate_worker_policy_documents(
        (("inline", "bounded-experiment-access", policy),),
        input_paths=plan["input_paths"],
        output_root=plan["output_path"],
        iam_role_arn=plan["worker_role_arn"],
    )

    assert record["inventory_sha256"]
    assert "arn:aws" not in json.dumps(record)


@pytest.mark.parametrize(
    "statement",
    [
        {
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "*",
        },
        {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::bucket",
        },
        {
            "Effect": "Allow",
            "Action": "s3:PutObject",
            "Resource": [
                "arn:aws:s3:::bucket/runs/qualification/action/outputs/worker-0/raw-measurement.json",
                "arn:aws:s3:::bucket/runs/qualification/other-action/outputs/worker-0/raw-measurement.json",
            ],
        },
    ],
)
def test_worker_policy_inventory_rejects_broad_or_other_action_s3_allows(
    statement: dict[str, object],
) -> None:
    plan = _plan()
    with pytest.raises(CloudManifestError, match="outside the exact qualification objects"):
        validate_worker_policy_documents(
            (
                (
                    "managed",
                    "arn:aws:iam::123456789012:policy/worker-extra",
                    {"Version": "2012-10-17", "Statement": [statement]},
                ),
            ),
            input_paths=plan["input_paths"],
            output_root=plan["output_path"],
            iam_role_arn=plan["worker_role_arn"],
        )


def test_worker_resource_policy_rejects_a_worker_applicable_broad_allow() -> None:
    plan = _plan()
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": plan["worker_role_arn"]},
                "Action": "s3:GetObject",
                "Resource": "*",
            }
        ],
    }
    with pytest.raises(CloudManifestError, match="outside the exact qualification objects"):
        validate_worker_resource_policy(
            policy,
            input_paths=plan["input_paths"],
            output_root=plan["output_path"],
            iam_role_arn=plan["worker_role_arn"],
        )

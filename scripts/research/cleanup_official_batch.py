"""Remove the action-scoped AWS surface created by submit_official_batch.

The immutable input package and scientific output objects are evidence and are
intentionally retained.  This command removes only resources whose names or
tags bind them to the exact action ID supplied by the operator.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import time
from typing import Any, Callable


REGION = "us-east-1"
ACCOUNT = "892077329800"
WORKER_ROLE = "pneuma-c160-worker"
ACTION_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")
TERMINAL_JOB_STATES = frozenset({"SUCCEEDED", "FAILED"})
ACTIVE_JOB_STATES = (
    "SUBMITTED",
    "PENDING",
    "RUNNABLE",
    "STARTING",
    "RUNNING",
)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _tags(value: dict[str, Any]) -> dict[str, str]:
    return {
        str(row["Key"]): str(row["Value"])
        for row in value.get("Tags", [])
        if isinstance(row, dict) and "Key" in row and "Value" in row
    }


def _require_owned(value: dict[str, Any], action_id: str, label: str) -> None:
    if _tags(value).get("ActionId") != action_id:
        raise RuntimeError(f"refusing to remove non-owned {label}")


def _wait(
    observe: Callable[[], bool], *, deadline: float, label: str, interval: float = 5
) -> None:
    while time.monotonic() < deadline:
        if observe():
            return
        time.sleep(interval)
    raise TimeoutError(f"timed out waiting for {label}")


def _active_jobs(batch: Any, queue_name: str) -> list[str]:
    result: list[str] = []
    for status in ACTIVE_JOB_STATES:
        token: str | None = None
        while True:
            kwargs: dict[str, object] = {
                "jobQueue": queue_name,
                "jobStatus": status,
                "maxResults": 100,
            }
            if token:
                kwargs["nextToken"] = token
            response = batch.list_jobs(**kwargs)
            result.extend(
                str(row["jobId"])
                for row in response.get("jobSummaryList", [])
                if isinstance(row, dict) and row.get("jobId")
            )
            token = response.get("nextToken")
            if not token:
                break
    return result


def cleanup(*, action_id: str, deadline_seconds: int = 3_600) -> dict[str, object]:
    """Drain and remove one exact official-study action surface."""

    import boto3
    from botocore.exceptions import ClientError

    if ACTION_RE.fullmatch(action_id) is None:
        raise ValueError("invalid action ID")
    sts = boto3.client("sts", region_name=REGION)
    identity = sts.get_caller_identity()
    if identity.get("Account") != ACCOUNT:
        raise RuntimeError("AWS account does not match the registered account")
    batch = boto3.client("batch", region_name=REGION)
    ec2 = boto3.client("ec2", region_name=REGION)
    iam = boto3.client("iam", region_name=REGION)
    deadline = time.monotonic() + deadline_seconds
    compute_name = f"{action_id}-ce"
    queue_name = f"{action_id}-queue"
    definition_name = f"{action_id}-job"
    policy_name = f"official-{action_id}"[:128]
    mutations: list[str] = []

    queues = batch.describe_job_queues(jobQueues=[queue_name]).get("jobQueues", [])
    if queues:
        active = _active_jobs(batch, queue_name)
        if active:
            raise RuntimeError(
                "refusing teardown while action jobs remain active: "
                + ",".join(sorted(active))
            )
        batch.update_job_queue(jobQueue=queue_name, state="DISABLED")
        mutations.append("disable_job_queue")
        _wait(
            lambda: (
                (rows := batch.describe_job_queues(jobQueues=[queue_name]).get("jobQueues", []))
                and rows[0].get("state") == "DISABLED"
                and rows[0].get("status") == "VALID"
            ),
            deadline=deadline,
            label="disabled job queue",
        )
        batch.delete_job_queue(jobQueue=queue_name)
        mutations.append("delete_job_queue")
        _wait(
            lambda: not batch.describe_job_queues(jobQueues=[queue_name]).get("jobQueues", []),
            deadline=deadline,
            label="deleted job queue",
        )

    environments = batch.describe_compute_environments(
        computeEnvironments=[compute_name]
    ).get("computeEnvironments", [])
    if environments:
        batch.update_compute_environment(
            computeEnvironment=compute_name, state="DISABLED"
        )
        mutations.append("disable_compute_environment")
        _wait(
            lambda: (
                (
                    rows := batch.describe_compute_environments(
                        computeEnvironments=[compute_name]
                    ).get("computeEnvironments", [])
                )
                and rows[0].get("state") == "DISABLED"
                and rows[0].get("status") == "VALID"
            ),
            deadline=deadline,
            label="disabled compute environment",
            interval=10,
        )
        batch.delete_compute_environment(computeEnvironment=compute_name)
        mutations.append("delete_compute_environment")
        _wait(
            lambda: not batch.describe_compute_environments(
                computeEnvironments=[compute_name]
            ).get("computeEnvironments", []),
            deadline=deadline,
            label="deleted compute environment",
            interval=10,
        )

    definitions = batch.describe_job_definitions(
        jobDefinitionName=definition_name, status="ACTIVE"
    ).get("jobDefinitions", [])
    for definition in definitions:
        batch.deregister_job_definition(jobDefinition=definition["jobDefinitionArn"])
        mutations.append("deregister_job_definition")

    def tagged(filters: list[dict[str, object]], key: str) -> list[dict[str, Any]]:
        return list(getattr(ec2, key)(Filters=filters).get({
            "describe_launch_templates": "LaunchTemplates",
            "describe_security_groups": "SecurityGroups",
            "describe_network_interfaces": "NetworkInterfaces",
            "describe_volumes": "Volumes",
            "describe_instances": "Reservations",
            "describe_subnets": "Subnets",
            "describe_route_tables": "RouteTables",
            "describe_internet_gateways": "InternetGateways",
        }[key], []))

    action_filter = [{"Name": "tag:ActionId", "Values": [action_id]}]
    _wait(
        lambda: (
            not tagged(action_filter, "describe_network_interfaces")
            and not tagged(
                [
                    *action_filter,
                    {
                        "Name": "instance-state-name",
                        "Values": ["pending", "running", "stopping", "stopped"],
                    },
                ],
                "describe_instances",
            )
            and not tagged(
                [
                    *action_filter,
                    {"Name": "status", "Values": ["creating", "available", "in-use"]},
                ],
                "describe_volumes",
            )
        ),
        deadline=deadline,
        label="managed instances, volumes, and network interfaces",
        interval=10,
    )

    for template in tagged(action_filter, "describe_launch_templates"):
        _require_owned(template, action_id, "launch template")
        ec2.delete_launch_template(LaunchTemplateId=template["LaunchTemplateId"])
        mutations.append("delete_launch_template")
    for group in tagged(action_filter, "describe_security_groups"):
        _require_owned(group, action_id, "security group")
        ec2.delete_security_group(GroupId=group["GroupId"])
        mutations.append("delete_security_group")
    for subnet in tagged(action_filter, "describe_subnets"):
        _require_owned(subnet, action_id, "subnet")
        ec2.delete_subnet(SubnetId=subnet["SubnetId"])
        mutations.append("delete_subnet")
    for table in tagged(action_filter, "describe_route_tables"):
        _require_owned(table, action_id, "route table")
        ec2.delete_route_table(RouteTableId=table["RouteTableId"])
        mutations.append("delete_route_table")
    for gateway in tagged(action_filter, "describe_internet_gateways"):
        _require_owned(gateway, action_id, "internet gateway")
        attachments = gateway.get("Attachments", [])
        for attachment in attachments:
            if attachment.get("State") == "available":
                ec2.detach_internet_gateway(
                    InternetGatewayId=gateway["InternetGatewayId"],
                    VpcId=attachment["VpcId"],
                )
                mutations.append("detach_internet_gateway")
        ec2.delete_internet_gateway(InternetGatewayId=gateway["InternetGatewayId"])
        mutations.append("delete_internet_gateway")

    try:
        iam.delete_role_policy(RoleName=WORKER_ROLE, PolicyName=policy_name)
        mutations.append("delete_worker_inline_policy")
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "NoSuchEntity":
            raise

    absence = {
        "job_queue": not batch.describe_job_queues(jobQueues=[queue_name]).get(
            "jobQueues", []
        ),
        "compute_environment": not batch.describe_compute_environments(
            computeEnvironments=[compute_name]
        ).get("computeEnvironments", []),
        "active_job_definition": not batch.describe_job_definitions(
            jobDefinitionName=definition_name, status="ACTIVE"
        ).get("jobDefinitions", []),
        "launch_templates": not tagged(action_filter, "describe_launch_templates"),
        "instances": not tagged(
            [
                *action_filter,
                {
                    "Name": "instance-state-name",
                    "Values": ["pending", "running", "stopping", "stopped"],
                },
            ],
            "describe_instances",
        ),
        "volumes": not tagged(
            [
                *action_filter,
                {"Name": "status", "Values": ["creating", "available", "in-use"]},
            ],
            "describe_volumes",
        ),
        "network_interfaces": not tagged(
            action_filter, "describe_network_interfaces"
        ),
        "security_groups": not tagged(action_filter, "describe_security_groups"),
        "subnets": not tagged(action_filter, "describe_subnets"),
        "route_tables": not tagged(action_filter, "describe_route_tables"),
        "internet_gateways": not tagged(
            action_filter, "describe_internet_gateways"
        ),
    }
    if not all(absence.values()):
        raise RuntimeError(f"provider absence failed: {absence}")
    return {
        "record_kind": "cloud_official_batch_teardown_receipt",
        "schema_version": "0.1.0",
        "action_id": action_id,
        "region": REGION,
        "completed_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "mutations": mutations,
        "active_resource_absence": absence,
        "retained_evidence": ["input_package", "scientific_outputs", "ecr_images"],
        "status": "COMPLETE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    receipt = cleanup(action_id=args.action_id)
    from pathlib import Path

    destination = Path(args.receipt)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(_canonical(receipt))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

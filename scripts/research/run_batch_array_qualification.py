"""Run one signed, zero-retry AWS Batch Fargate array qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from pneuma_lab.cloud.authorization_keys import canonical_bytes, canonical_ledger_digest
from pneuma_lab.cloud.batch_array import require_batch_array_qualification
from pneuma_lab.cloud.preparation_admission import require_preparation_admission


class QualificationError(RuntimeError):
    """A fail-closed preflight, provider, or readback error."""


def plan_digest(plan: dict[str, Any]) -> str:
    body = dict(plan)
    body.pop("plan_sha256", None)
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _run_aws(plan: dict[str, Any], command: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    env["AWS_PROFILE"] = plan["execution_profile"]
    env["AWS_MAX_ATTEMPTS"] = "1"
    env["AWS_RETRY_MODE"] = "standard"
    env["AWS_PAGER"] = ""
    env["AWS_CLI_AUTO_PROMPT"] = "off"
    argv = ["aws", *command, "--region", plan["region"], "--output", "json", "--no-cli-pager"]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=int(plan["cli_timeout_seconds"]),
        )
        stdout = completed.stdout
        stderr = completed.stderr
        return {
            "return_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_sha256": _digest_bytes(stdout),
            "stderr_sha256": _digest_bytes(stderr),
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        if not isinstance(stdout, bytes):
            stdout = str(stdout).encode("utf-8")
        if not isinstance(stderr, bytes):
            stderr = str(stderr).encode("utf-8")
        return {
            "return_code": 124,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_sha256": _digest_bytes(stdout),
            "stderr_sha256": _digest_bytes(stderr),
            "duration_ms": int((time.monotonic() - started) * 1000),
            "timeout": True,
        }


def _json(result: dict[str, Any]) -> Any:
    if result["return_code"] != 0:
        raise QualificationError("AWS read or mutation returned a non-zero status")
    if not result["stdout"].strip():
        return {}
    try:
        return json.loads(result["stdout"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationError("AWS returned non-JSON output") from exc


def _read(plan: dict[str, Any], command: list[str]) -> Any:
    return _json(_run_aws(plan, command))


def _first(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a safe empty object for an eventually-consistent empty read."""

    return rows[0] if rows else {}


def _record_mutation(receipt: dict[str, Any], operation: str, result: dict[str, Any]) -> None:
    receipt["mutations"].append(
        {
            "operation": operation,
            "return_code": result["return_code"],
            "stdout_sha256": result["stdout_sha256"],
            "stderr_sha256": result["stderr_sha256"],
            "duration_ms": result["duration_ms"],
            "succeeded": result["return_code"] == 0,
        }
    )


def _mutate(plan: dict[str, Any], receipt: dict[str, Any], operation: str, command: list[str]) -> Any:
    result = _run_aws(plan, command)
    _record_mutation(receipt, operation, result)
    return _json(result)


def _safe_mutate(
    plan: dict[str, Any], receipt: dict[str, Any], operation: str, command: list[str], errors: list[str]
) -> Any:
    try:
        return _mutate(plan, receipt, operation, command)
    except QualificationError:
        errors.append(operation)
        return None


def _not_found(result: dict[str, Any]) -> bool:
    if result["return_code"] == 0:
        return False
    text = result["stderr"].decode("utf-8", errors="replace")
    return any(token in text for token in ("NoSuchEntity", "NotFound", "does not exist", "not found"))


def _poll(plan: dict[str, Any], reader: Callable[[], Any], predicate: Callable[[Any], bool], label: str) -> Any:
    deadline = time.monotonic() + int(plan["max_poll_seconds"])
    while time.monotonic() <= deadline:
        current = reader()
        if predicate(current):
            return current
        time.sleep(min(float(plan["poll_interval_seconds"]), 5.0, max(0.0, deadline - time.monotonic())))
    raise QualificationError(f"poll timeout: {label}")


def _role_absent(plan: dict[str, Any], role_name: str) -> bool:
    result = _run_aws(plan, ["iam", "get-role", "--role-name", role_name])
    if result["return_code"] == 0:
        return False
    if _not_found(result):
        return True
    raise QualificationError("IAM role preflight returned an unexpected provider error")


def _batch_named_absent(plan: dict[str, Any]) -> tuple[bool, bool, bool]:
    environments = _read(plan, ["batch", "describe-compute-environments", "--compute-environments", plan["compute_environment_name"]]).get("computeEnvironments", [])
    queues = _read(plan, ["batch", "describe-job-queues", "--job-queues", plan["job_queue_name"]]).get("jobQueues", [])
    definitions = _read(
        plan,
        [
            "batch",
            "describe-job-definitions",
            "--job-definition-name",
            plan["job_definition_name"],
            "--status",
            "ACTIVE",
        ],
    ).get("jobDefinitions", [])
    return not environments, not queues, not definitions


def _normalise_egress(group: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rule in group.get("IpPermissionsEgress", []):
        for cidr in rule.get("IpRanges", []):
            rows.append(
                {
                    "ip_protocol": rule.get("IpProtocol"),
                    "from_port": rule.get("FromPort"),
                    "to_port": rule.get("ToPort"),
                    "cidr": cidr.get("CidrIp"),
                    "description": cidr.get("Description"),
                }
            )
        if not rule.get("IpRanges"):
            rows.append(
                {
                    "ip_protocol": rule.get("IpProtocol"),
                    "from_port": rule.get("FromPort"),
                    "to_port": rule.get("ToPort"),
                    "cidr": None,
                    "description": None,
                }
            )
    return sorted(rows, key=lambda row: canonical_bytes(row))


def _preflight(plan: dict[str, Any], receipt: dict[str, Any]) -> None:
    identity = _read(plan, ["sts", "get-caller-identity"])
    receipt["identity_arn"] = identity.get("Arn", "unresolved")
    receipt["preflight"]["account_exact"] = identity.get("Account") == plan["account_id"]

    vpc = _read(plan, ["ec2", "describe-vpcs", "--vpc-ids", plan["vpc_id"]]).get("Vpcs", [])
    receipt["preflight"]["vpc_exact"] = bool(
        len(vpc) == 1
        and vpc[0].get("VpcId") == plan["vpc_id"]
        and vpc[0].get("IsDefault") is True
        and vpc[0].get("State") == "available"
    )
    subnets = _read(plan, ["ec2", "describe-subnets", "--subnet-ids", plan["subnet_id"]]).get("Subnets", [])
    receipt["preflight"]["subnet_exact"] = bool(
        len(subnets) == 1
        and subnets[0].get("SubnetId") == plan["subnet_id"]
        and subnets[0].get("VpcId") == plan["vpc_id"]
        and subnets[0].get("AvailabilityZone") == plan["availability_zone"]
        and subnets[0].get("MapPublicIpOnLaunch") is True
    )
    groups = _read(plan, ["ec2", "describe-security-groups", "--group-ids", plan["security_group_id"]]).get("SecurityGroups", [])
    actual_egress = _normalise_egress(groups[0]) if len(groups) == 1 else []
    expected_egress = sorted(plan["security_group_egress"], key=lambda row: canonical_bytes(row))
    receipt["preflight"]["security_group_exact"] = bool(
        len(groups) == 1
        and groups[0].get("GroupId") == plan["security_group_id"]
        and groups[0].get("VpcId") == plan["vpc_id"]
        and groups[0].get("IpPermissions") == []
        and actual_egress == expected_egress
    )

    ce_absent, queue_absent, definition_absent = _batch_named_absent(plan)
    receipt["preflight"]["compute_environment_absent"] = ce_absent
    receipt["preflight"]["job_queue_absent"] = queue_absent
    receipt["preflight"]["job_definition_absent"] = definition_absent
    receipt["preflight"]["service_linked_role_absent"] = _role_absent(plan, plan["service_linked_role_name"])
    receipt["preflight"]["execution_role_absent"] = _role_absent(plan, plan["execution_role_name"])
    if not all(receipt["preflight"].values()):
        raise QualificationError("signed Batch target or network preflight was not exact")


def _base_receipt(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_kind": "cloud_batch_array_qualification_receipt",
        "schema_version": "0.1.0",
        "plan_sha256": plan["plan_sha256"],
        "input_lock_sha256": plan.get("input_lock_sha256"),
        "provider": plan["provider"],
        "region": plan["region"],
        "account_id": plan["account_id"],
        "qualification_id": plan["action_id"],
        "identity_arn": "unresolved",
        "preflight": {
            "account_exact": False,
            "vpc_exact": False,
            "subnet_exact": False,
            "security_group_exact": False,
            "compute_environment_absent": False,
            "job_queue_absent": False,
            "job_definition_absent": False,
            "service_linked_role_absent": False,
            "execution_role_absent": False,
        },
        "resources": {
            "service_linked_role_arn": None,
            "execution_role_arn": None,
            "compute_environment_arn": None,
            "compute_environment_name": plan["compute_environment_name"],
            "job_queue_arn": None,
            "job_queue_name": plan["job_queue_name"],
            "job_definition_arn": None,
            "job_definition_revision": None,
            "parent_job_id": None,
            "child_job_ids": [],
        },
        "mutations": [],
        "observations": {
            "compute_environment_status": None,
            "job_queue_status": None,
            "parent_status": None,
            "array_size": 0,
            "child_indices": [],
            "children": [],
        },
        "teardown": {
            "job_cancelled_if_needed": False,
            "queue_disabled": False,
            "queue_deleted": False,
            "compute_environment_disabled": False,
            "compute_environment_deleted": False,
            "job_definition_deregistered": False,
            "execution_policy_detached": False,
            "execution_role_deleted": False,
            "service_linked_role_deleted": False,
            "final_resources_absent": False,
            "service_linked_role_deletion_task_id": None,
        },
        "gates": {
            "preflight_exact": False,
            "compute_environment_valid": False,
            "job_queue_valid": False,
            "array_size_exact": False,
            "child_indices_exact": False,
            "all_children_succeeded": False,
            "all_children_one_attempt": False,
            "no_provider_errors": False,
            "no_retries": True,
            "exact_teardown": False,
            "no_scientific_action": True,
        },
        "residual_resource_ids": [],
        "no_scientific_action": True,
        "verdict": "failed",
        "failure_reason": None,
    }


def _array_children(plan: dict[str, Any], parent_id: str) -> dict[str, dict[str, Any]]:
    statuses = ("SUBMITTED", "PENDING", "RUNNABLE", "STARTING", "RUNNING", "SUCCEEDED", "FAILED")
    children: dict[str, dict[str, Any]] = {}
    for status in statuses:
        response = _read(
            plan,
            ["batch", "list-jobs", "--array-job-id", parent_id, "--job-status", status, "--max-items", "100"],
        )
        for summary in response.get("jobSummaryList", []):
            job_id = summary.get("jobId")
            if job_id:
                children[job_id] = summary
    return children


def _describe_jobs(plan: dict[str, Any], job_ids: list[str]) -> list[dict[str, Any]]:
    if not job_ids:
        return []
    output: list[dict[str, Any]] = []
    for start in range(0, len(job_ids), 100):
        output.extend(_read(plan, ["batch", "describe-jobs", "--jobs", *job_ids[start : start + 100]]).get("jobs", []))
    return output


def _poll_array(plan: dict[str, Any], parent_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    deadline = time.monotonic() + int(plan["max_poll_seconds"])
    while time.monotonic() <= deadline:
        parent_jobs = _describe_jobs(plan, [parent_id])
        parent = parent_jobs[0] if parent_jobs else {}
        summaries = _array_children(plan, parent_id)
        if len(summaries) >= int(plan["array_size"]):
            child_jobs = _describe_jobs(plan, sorted(summaries))
            by_id = {job.get("jobId"): job for job in child_jobs}
            children: list[dict[str, Any]] = []
            for job_id, summary in summaries.items():
                job = by_id.get(job_id, summary)
                array = job.get("arrayProperties") or summary.get("arrayProperties") or {}
                attempts = job.get("attempts") or []
                children.append(
                    {
                        "job_id": job_id,
                        "index": int(array.get("index", -1)),
                        "status": job.get("status", summary.get("jobStatus", "UNKNOWN")),
                        "attempt_count": len(attempts),
                    }
                )
            children.sort(key=lambda child: (child["index"], child["job_id"]))
            terminal = all(child["status"] in {"SUCCEEDED", "FAILED"} for child in children)
            if len(children) == int(plan["array_size"]) and terminal:
                return parent, children
        time.sleep(min(float(plan["poll_interval_seconds"]), 5.0, max(0.0, deadline - time.monotonic())))
    raise QualificationError("poll timeout: Batch array children")


def _poll_batch_absent(plan: dict[str, Any], kind: str, name: str) -> bool:
    if kind == "compute_environment":
        reader = lambda: _read(plan, ["batch", "describe-compute-environments", "--compute-environments", name]).get("computeEnvironments", [])
    elif kind == "job_queue":
        reader = lambda: _read(plan, ["batch", "describe-job-queues", "--job-queues", name]).get("jobQueues", [])
    else:
        reader = lambda: _read(plan, ["batch", "describe-job-definitions", "--job-definition-name", name, "--status", "ACTIVE"]).get("jobDefinitions", [])
    _poll(plan, reader, lambda rows: not rows, f"{kind} absence")
    return True


def _poll_role_absent(plan: dict[str, Any], role_name: str) -> bool:
    def reader() -> bool:
        result = _run_aws(plan, ["iam", "get-role", "--role-name", role_name])
        if result["return_code"] == 0:
            return False
        if _not_found(result):
            return True
        raise QualificationError("IAM role readback returned an unexpected provider error")

    _poll(plan, reader, lambda absent: absent, f"IAM role {role_name} absence")
    return True


def _teardown(plan: dict[str, Any], receipt: dict[str, Any], flags: dict[str, bool], errors: list[str]) -> None:
    parent_id = receipt["resources"]["parent_job_id"]
    if parent_id and not flags["parent_terminal"]:
        result = _safe_mutate(plan, receipt, "cancel_job", ["batch", "cancel-job", "--job-id", parent_id, "--reason", "signed qualification teardown"], errors)
        receipt["teardown"]["job_cancelled_if_needed"] = result is not None
    else:
        receipt["teardown"]["job_cancelled_if_needed"] = True

    queue_arn = receipt["resources"]["job_queue_arn"]
    if flags["queue_created"] and queue_arn:
        result = _safe_mutate(plan, receipt, "disable_job_queue", ["batch", "update-job-queue", "--job-queue", queue_arn, "--state", "DISABLED"], errors)
        if result is not None:
            try:
                _poll(plan, lambda: _first(_read(plan, ["batch", "describe-job-queues", "--job-queues", queue_arn]).get("jobQueues", [])), lambda row: row.get("state") == "DISABLED", "job queue disabled")
                receipt["teardown"]["queue_disabled"] = True
            except QualificationError:
                errors.append("poll_disabled_job_queue")
        result = _safe_mutate(plan, receipt, "delete_job_queue", ["batch", "delete-job-queue", "--job-queue", queue_arn], errors)
        if result is not None:
            try:
                receipt["teardown"]["queue_deleted"] = _poll_batch_absent(plan, "job_queue", plan["job_queue_name"])
            except QualificationError:
                errors.append("poll_deleted_job_queue")

    environment_arn = receipt["resources"]["compute_environment_arn"]
    if flags["compute_environment_created"] and environment_arn:
        result = _safe_mutate(plan, receipt, "disable_compute_environment", ["batch", "update-compute-environment", "--compute-environment", environment_arn, "--state", "DISABLED"], errors)
        if result is not None:
            try:
                _poll(plan, lambda: _first(_read(plan, ["batch", "describe-compute-environments", "--compute-environments", environment_arn]).get("computeEnvironments", [])), lambda row: row.get("state") == "DISABLED", "compute environment disabled")
                receipt["teardown"]["compute_environment_disabled"] = True
            except QualificationError:
                errors.append("poll_disabled_compute_environment")
        result = _safe_mutate(plan, receipt, "delete_compute_environment", ["batch", "delete-compute-environment", "--compute-environment", environment_arn], errors)
        if result is not None:
            try:
                receipt["teardown"]["compute_environment_deleted"] = _poll_batch_absent(plan, "compute_environment", plan["compute_environment_name"])
            except QualificationError:
                errors.append("poll_deleted_compute_environment")

    definition_arn = receipt["resources"]["job_definition_arn"]
    if flags["job_definition_created"] and definition_arn:
        result = _safe_mutate(plan, receipt, "deregister_job_definition", ["batch", "deregister-job-definition", "--job-definition", definition_arn], errors)
        if result is not None:
            try:
                receipt["teardown"]["job_definition_deregistered"] = _poll_batch_absent(plan, "job_definition", plan["job_definition_name"])
            except QualificationError:
                errors.append("poll_deregistered_job_definition")

    if flags["policy_attached"]:
        result = _safe_mutate(plan, receipt, "detach_execution_role_policy", ["iam", "detach-role-policy", "--role-name", plan["execution_role_name"], "--policy-arn", plan["execution_policy_arn"]], errors)
        receipt["teardown"]["execution_policy_detached"] = result is not None
    if flags["execution_role_created"]:
        result = _safe_mutate(plan, receipt, "delete_execution_role", ["iam", "delete-role", "--role-name", plan["execution_role_name"]], errors)
        if result is not None:
            try:
                receipt["teardown"]["execution_role_deleted"] = _poll_role_absent(plan, plan["execution_role_name"])
            except QualificationError:
                errors.append("poll_deleted_execution_role")

    if flags["service_linked_role_created"]:
        result = _safe_mutate(plan, receipt, "delete_service_linked_role", ["iam", "delete-service-linked-role", "--role-name", plan["service_linked_role_name"]], errors)
        if result is not None:
            task_id = result.get("DeletionTaskId")
            receipt["teardown"]["service_linked_role_deletion_task_id"] = task_id
            try:
                if not task_id:
                    raise QualificationError("service-linked-role deletion did not return a task id")
                _poll(
                    plan,
                    lambda: _read(plan, ["iam", "get-service-linked-role-deletion-status", "--deletion-task-id", task_id]),
                    lambda row: row.get("Status") == "SUCCEEDED",
                    "service-linked-role deletion",
                )
                receipt["teardown"]["service_linked_role_deleted"] = _poll_role_absent(plan, plan["service_linked_role_name"])
            except QualificationError:
                errors.append("poll_deleted_service_linked_role")


def _final_resources_absent(plan: dict[str, Any], receipt: dict[str, Any]) -> bool:
    checks = [
        not _read(plan, ["batch", "describe-compute-environments", "--compute-environments", plan["compute_environment_name"]]).get("computeEnvironments", []),
        not _read(plan, ["batch", "describe-job-queues", "--job-queues", plan["job_queue_name"]]).get("jobQueues", []),
        not _read(plan, ["batch", "describe-job-definitions", "--job-definition-name", plan["job_definition_name"], "--status", "ACTIVE"]).get("jobDefinitions", []),
        _role_absent(plan, plan["execution_role_name"]),
        _role_absent(plan, plan["service_linked_role_name"]),
    ]
    return all(checks)


def execute(plan: dict[str, Any], package: dict[str, Any], registry: dict[str, Any], ledger_path: Path) -> dict[str, Any]:
    if plan_digest(plan) != plan["plan_sha256"]:
        raise QualificationError("plan_sha256 does not bind canonical plan bytes")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != plan["executor_sha256"]:
        raise QualificationError("executor bytes do not match the signed plan")
    if package.get("record_kind") != "cloud_preparation_signing_package" or package.get("plan_sha256") != plan["plan_sha256"]:
        raise QualificationError("signing package is not bound to this plan")
    source_check = subprocess.run(["git", "merge-base", "--is-ancestor", plan["source_commit"], "HEAD"], check=False)
    if source_check.returncode != 0:
        raise QualificationError("checkout HEAD does not descend from the signed source commit")
    require_preparation_admission(
        package["envelope"],
        package["admission"],
        key_registry=registry,
        ledger_path=ledger_path,
        expected_action_id=plan["action_id"],
        expected_action_class=plan["action_class"],
        expected_provider=plan["provider"],
        expected_region=plan["region"],
        expected_manifest_sha256=plan["plan_sha256"],
        expected_input_lock_sha256=plan.get("input_lock_sha256"),
        expected_projected_cost_usd=plan["projected_cost_usd"],
        expected_max_retries=plan["max_retries"],
        spend_history_sha256=canonical_ledger_digest(ledger_path),
    )
    receipt = _base_receipt(plan)
    flags = {
        "service_linked_role_created": False,
        "execution_role_created": False,
        "policy_attached": False,
        "compute_environment_created": False,
        "queue_created": False,
        "job_definition_created": False,
        "parent_terminal": False,
    }
    cleanup_errors: list[str] = []
    try:
        _preflight(plan, receipt)
        slr = _mutate(plan, receipt, "create_service_linked_role", ["iam", "create-service-linked-role", "--aws-service-name", "batch.amazonaws.com"])
        flags["service_linked_role_created"] = True
        receipt["resources"]["service_linked_role_arn"] = slr.get("Role", {}).get("Arn", plan["service_linked_role_arn"])
        if receipt["resources"]["service_linked_role_arn"] != plan["service_linked_role_arn"]:
            raise QualificationError("service-linked role ARN differs from signed plan")

        trust = json.dumps(plan["execution_role_trust_policy"], sort_keys=True, separators=(",", ":"))
        role = _mutate(plan, receipt, "create_execution_role", ["iam", "create-role", "--role-name", plan["execution_role_name"], "--assume-role-policy-document", trust])
        flags["execution_role_created"] = True
        receipt["resources"]["execution_role_arn"] = role.get("Role", {}).get("Arn")
        if receipt["resources"]["execution_role_arn"] != plan["execution_role_arn"]:
            raise QualificationError("execution role ARN differs from signed plan")
        _mutate(plan, receipt, "attach_execution_role_policy", ["iam", "attach-role-policy", "--role-name", plan["execution_role_name"], "--policy-arn", plan["execution_policy_arn"]])
        flags["policy_attached"] = True

        compute_resources = {
            "type": "FARGATE",
            "maxvCpus": int(plan["max_vcpus"]),
            "subnets": [plan["subnet_id"]],
            "securityGroupIds": [plan["security_group_id"]],
        }
        environment = _mutate(
            plan,
            receipt,
            "create_compute_environment",
            [
                "batch",
                "create-compute-environment",
                "--compute-environment-name",
                plan["compute_environment_name"],
                "--type",
                "MANAGED",
                "--state",
                "ENABLED",
                "--service-role",
                plan["service_linked_role_arn"],
                "--compute-resources",
                json.dumps(compute_resources, sort_keys=True, separators=(",", ":")),
            ],
        )
        flags["compute_environment_created"] = True
        receipt["resources"]["compute_environment_arn"] = environment.get("computeEnvironmentArn")
        if receipt["resources"]["compute_environment_arn"] != plan["compute_environment_arn"]:
            raise QualificationError("compute environment ARN differs from signed plan")
        ce = _poll(
            plan,
            lambda: _first(_read(plan, ["batch", "describe-compute-environments", "--compute-environments", plan["compute_environment_arn"]]).get("computeEnvironments", [])),
            lambda row: row.get("status") == "VALID",
            "compute environment VALID",
        )
        receipt["observations"]["compute_environment_status"] = ce.get("status")

        queue = _mutate(
            plan,
            receipt,
            "create_job_queue",
            [
                "batch",
                "create-job-queue",
                "--job-queue-name",
                plan["job_queue_name"],
                "--state",
                "ENABLED",
                "--priority",
                "1",
                "--compute-environment-order",
                json.dumps([{"order": 1, "computeEnvironment": plan["compute_environment_arn"]}], sort_keys=True, separators=(",", ":")),
            ],
        )
        flags["queue_created"] = True
        receipt["resources"]["job_queue_arn"] = queue.get("jobQueueArn")
        if receipt["resources"]["job_queue_arn"] != plan["job_queue_arn"]:
            raise QualificationError("job queue ARN differs from signed plan")
        job_queue = _poll(
            plan,
            lambda: _first(_read(plan, ["batch", "describe-job-queues", "--job-queues", plan["job_queue_arn"]]).get("jobQueues", [])),
            lambda row: row.get("status") == "VALID",
            "job queue VALID",
        )
        receipt["observations"]["job_queue_status"] = job_queue.get("status")

        container_properties = {
            "image": plan["image"],
            "command": plan["command"],
            "resourceRequirements": [
                {"type": "VCPU", "value": str(plan["vcpus"])},
                {"type": "MEMORY", "value": str(plan["memory_mib"])},
            ],
            "executionRoleArn": plan["execution_role_arn"],
            "networkConfiguration": {"assignPublicIp": plan["assign_public_ip"]},
            "fargatePlatformConfiguration": {"platformVersion": plan["fargate_platform_version"]},
            "runtimePlatform": {"operatingSystemFamily": "LINUX", "cpuArchitecture": "X86_64"},
        }
        definition = _mutate(
            plan,
            receipt,
            "register_job_definition",
            [
                "batch",
                "register-job-definition",
                "--job-definition-name",
                plan["job_definition_name"],
                "--type",
                "container",
                "--platform-capabilities",
                "FARGATE",
                "--retry-strategy",
                json.dumps({"attempts": 1}, sort_keys=True, separators=(",", ":")),
                "--container-properties",
                json.dumps(container_properties, sort_keys=True, separators=(",", ":")),
            ],
        )
        flags["job_definition_created"] = True
        receipt["resources"]["job_definition_arn"] = definition.get("jobDefinitionArn")
        receipt["resources"]["job_definition_revision"] = definition.get("revision")
        if not receipt["resources"]["job_definition_arn"] or not str(receipt["resources"]["job_definition_arn"]).startswith(plan["job_definition_arn_prefix"]):
            raise QualificationError("job definition ARN is outside the signed family")

        submitted = _mutate(
            plan,
            receipt,
            "submit_array_job",
            [
                "batch",
                "submit-job",
                "--job-name",
                plan["job_name"],
                "--job-queue",
                plan["job_queue_arn"],
                "--job-definition",
                receipt["resources"]["job_definition_arn"],
                "--array-properties",
                json.dumps({"size": int(plan["array_size"])}, sort_keys=True, separators=(",", ":")),
                "--retry-strategy",
                json.dumps({"attempts": 1}, sort_keys=True, separators=(",", ":")),
            ],
        )
        receipt["resources"]["parent_job_id"] = submitted.get("jobId")
        if not receipt["resources"]["parent_job_id"]:
            raise QualificationError("Batch submit response omitted the parent job id")
        parent, children = _poll_array(plan, receipt["resources"]["parent_job_id"])
        flags["parent_terminal"] = parent.get("status") in {"SUCCEEDED", "FAILED"}
        receipt["observations"]["parent_status"] = parent.get("status")
        receipt["observations"]["array_size"] = int(plan["array_size"])
        receipt["observations"]["children"] = children
        receipt["observations"]["child_indices"] = [child["index"] for child in children]
        receipt["resources"]["child_job_ids"] = [child["job_id"] for child in children]
        if parent.get("status") != "SUCCEEDED":
            raise QualificationError("Batch array parent did not succeed")
    except Exception as exc:  # Preserve a machine receipt and always enter teardown.
        receipt["failure_reason"] = f"{type(exc).__name__}: qualification failed closed"
    finally:
        _teardown(plan, receipt, flags, cleanup_errors)

    try:
        receipt["teardown"]["final_resources_absent"] = _final_resources_absent(plan, receipt)
    except Exception:
        cleanup_errors.append("final_resource_readback")
    if cleanup_errors and receipt["failure_reason"] is None:
        receipt["failure_reason"] = "teardown or readback failed closed"

    observations = receipt["observations"]
    children = observations["children"]
    expected_indices = list(range(int(plan["array_size"])))
    required_mutations = {
        "create_service_linked_role", "create_execution_role", "attach_execution_role_policy",
        "create_compute_environment", "create_job_queue", "register_job_definition", "submit_array_job",
        "disable_job_queue", "delete_job_queue", "disable_compute_environment", "delete_compute_environment",
        "deregister_job_definition", "detach_execution_role_policy", "delete_execution_role", "delete_service_linked_role",
    }
    observed_mutations = {row["operation"] for row in receipt["mutations"]}
    receipt["gates"] = {
        "preflight_exact": all(receipt["preflight"].values()),
        "compute_environment_valid": observations["compute_environment_status"] == "VALID",
        "job_queue_valid": observations["job_queue_status"] == "VALID",
        "array_size_exact": observations["array_size"] == int(plan["array_size"]) and len(children) == int(plan["array_size"]),
        "child_indices_exact": observations["child_indices"] == expected_indices,
        "all_children_succeeded": len(children) == int(plan["array_size"]) and all(child["status"] == "SUCCEEDED" for child in children),
        "all_children_one_attempt": len(children) == int(plan["array_size"]) and all(child["attempt_count"] == 1 for child in children),
        "no_provider_errors": required_mutations.issubset(observed_mutations) and all(row["succeeded"] for row in receipt["mutations"]),
        "no_retries": int(plan["max_retries"]) == 0 and all(child["attempt_count"] == 1 for child in children),
        "exact_teardown": all(value for key, value in receipt["teardown"].items() if key != "service_linked_role_deletion_task_id"),
        "no_scientific_action": receipt["no_scientific_action"] is True,
    }
    receipt["verdict"] = "passed" if all(receipt["gates"].values()) else "failed"
    if receipt["verdict"] == "passed":
        require_batch_array_qualification(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--key-registry", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    package = json.loads(args.package.read_text(encoding="utf-8"))
    registry = json.loads(args.key_registry.read_text(encoding="utf-8"))
    receipt = execute(plan, package, registry, args.ledger)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(receipt) + b"\n"
    args.output.write_bytes(payload)
    print(json.dumps({"verdict": receipt["verdict"], "plan_sha256": receipt["plan_sha256"], "receipt_sha256": hashlib.sha256(payload).hexdigest()}))
    return 0 if receipt["verdict"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

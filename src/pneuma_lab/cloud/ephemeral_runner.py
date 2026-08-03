"""Mockable, fail-closed runner for the ephemeral Batch qualification.

The provider client is an injected seam.  This module contains the ordering
and invariants, but performs no provider calls when imported or tested.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any, Protocol

from .ephemeral_qualification import (
    MAX_RETRIES,
    MAX_WORKER_RUNTIME_MINUTES,
    TOTAL_COST_CEILING_USD,
    require_cost_ceiling,
    require_two_workers,
)
from .errors import CloudManifestError
from .preparation_admission import require_preparation_admission
from .authorization_keys import canonical_bytes
from .qualification_execution import (
    AwsCliAdapter as ObjectAwsCliAdapter,
    derive_spend_history_binding,
    parse_terraform_show,
    require_two_succeeded_children,
    retrieve_raw_measurement,
    terraform_plan_binding_digest,
    verify_provider_bindings,
)

QUALIFICATION_TAGS = {
    "QualificationPurpose": "dual-l40s-admission-only",
    "QualificationTopology": "two-g6e-2xlarge-l40s",
    "QualificationManagedBy": "pneuma-ephemeral-runner-v1",
}
EXPECTED_RESOURCE_ADDRESSES = frozenset(
    {
        "aws_batch_compute_environment.qualification",
        "aws_launch_template.qualification",
        "aws_batch_job_queue.qualification",
        "aws_batch_job_definition.worker",
    }
)


class QualificationProvider(Protocol):
    def preflight(self, tags: Mapping[str, str]) -> Mapping[str, Any]: ...

    def wait_ready(self, tags: Mapping[str, str]) -> Mapping[str, Any]: ...

    def submit_array(
        self, *, size: int, timeout_seconds: int, attempts: int, tags: Mapping[str, str]
    ) -> str: ...

    def collect_admission(self, parent_job_id: str) -> Mapping[str, Any]: ...

    def run_partition_recovery(self, parent_job_id: str) -> Mapping[str, Any]: ...

    def disable_and_drain(self, tags: Mapping[str, str]) -> None: ...

    def verify_absence(self, tags: Mapping[str, str]) -> Mapping[str, bool]: ...

    def pricing_projection(self, *, worker_seconds: int) -> float: ...


class TerraformQualification(Protocol):
    def apply(self, *, lock_timeout: str, tags: Mapping[str, str]) -> None: ...

    def destroy(self, *, lock_timeout: str, tags: Mapping[str, str]) -> None: ...


CommandRunner = Callable[..., subprocess.CompletedProcess[bytes]]


def _json_result(result: subprocess.CompletedProcess[bytes]) -> Any:
    if result.returncode != 0:
        raise CloudManifestError("provider subprocess failed")
    try:
        return json.loads(result.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudManifestError("provider subprocess returned invalid JSON") from exc


class TerraformAdapter:
    """Terraform adapter whose subprocess is injectable and never retries."""

    def __init__(
        self, run: CommandRunner, *, directory: str = "infra/terraform/qualification"
    ) -> None:
        self.run = run
        self.directory = directory
        self.plan_path: Path | None = None
        self.saved_plan_sha256: str | None = None
        self.terraform_show_sha256: str | None = None

    def load_account_plan(self, plan_path: Path) -> dict[str, Any]:
        saved_plan = plan_path.read_bytes()
        saved_plan_sha256 = hashlib.sha256(saved_plan).hexdigest()
        result = self.run(
            ["terraform", f"-chdir={self.directory}", "show", "-json", str(plan_path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        plan = _json_result(result)
        if not isinstance(plan, dict):
            raise CloudManifestError("terraform show did not return an object")
        parsed = parse_terraform_show(plan)
        _require_resource_contract(plan)
        plan["terraform_show_sha256"] = parsed["terraform_show_sha256"]
        plan["saved_plan_sha256"] = saved_plan_sha256
        plan["terraform_plan_binding_sha256"] = terraform_plan_binding_digest(
            saved_plan_sha256, parsed["terraform_show_sha256"]
        )
        parsed["saved_plan_sha256"] = saved_plan_sha256
        parsed["terraform_plan_binding_sha256"] = plan[
            "terraform_plan_binding_sha256"
        ]
        plan["_qualification"] = parsed
        self.plan_path = plan_path
        self.saved_plan_sha256 = saved_plan_sha256
        self.terraform_show_sha256 = parsed["terraform_show_sha256"]
        return plan

    def apply(self, *, lock_timeout: str, tags: Mapping[str, str]) -> None:
        if self.plan_path is None or self.saved_plan_sha256 is None:
            raise CloudManifestError("no exact saved account plan loaded")
        current_plan_sha256 = hashlib.sha256(self.plan_path.read_bytes()).hexdigest()
        if current_plan_sha256 != self.saved_plan_sha256:
            raise CloudManifestError(
                "saved Terraform plan bytes changed after plan review"
            )
        if self.terraform_show_sha256 is None:
            raise CloudManifestError("no exact Terraform show binding loaded")
        show_result = self.run(
            [
                "terraform",
                f"-chdir={self.directory}",
                "show",
                "-json",
                str(self.plan_path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        current_show = _json_result(show_result)
        if parse_terraform_show(current_show)["terraform_show_sha256"] != self.terraform_show_sha256:
            raise CloudManifestError(
                "Terraform show bytes changed after plan review"
            )
        result = self.run(
            [
                "terraform",
                f"-chdir={self.directory}",
                "apply",
                "-input=false",
                "-auto-approve",
                f"-lock-timeout={lock_timeout}",
                str(self.plan_path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise CloudManifestError("terraform apply of saved plan failed")

    def destroy(self, *, lock_timeout: str, tags: Mapping[str, str]) -> None:
        result = self.run(
            [
                "terraform",
                f"-chdir={self.directory}",
                "destroy",
                "-input=false",
                "-auto-approve",
                f"-lock-timeout={lock_timeout}",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise CloudManifestError("terraform destroy failed")


def _require_resource_contract(plan: Mapping[str, Any]) -> None:
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        raise CloudManifestError(
            "ephemeral qualification plan lacks resource_changes"
        )
    addresses = {
        change.get("address")
        for change in changes
        if isinstance(change, Mapping) and isinstance(change.get("address"), str)
    }
    if addresses != EXPECTED_RESOURCE_ADDRESSES:
        raise CloudManifestError(
            "ephemeral qualification plan must contain exactly the compute "
            "environment, launch template, queue, and job definition"
        )


class AwsCliAdapter(ObjectAwsCliAdapter):
    """Concrete AWS CLI command adapter with an injected subprocess seam."""

    def __init__(
        self,
        run: CommandRunner,
        *,
        region: str,
        queue: str,
        job_definition: str,
        output_root: str,
        compute_environment: str | None = None,
        transport: Any | None = None,
    ) -> None:
        super().__init__(
            region=region,
            transport=transport,
            runner=run,
            recovery_config={
                "boundary_uri": f"{output_root.rstrip('/')}/interruption/boundary.json",
                "compute_environment": compute_environment or queue,
            },
        )
        self.run, self.region = run, region
        self.queue, self.job_definition, self.output_root = (
            queue,
            job_definition,
            output_root,
        )
        self.compute_environment = compute_environment or queue
        self.parent_job_id: str | None = None

    def _call(self, *args: str) -> Any:
        result = self.run(
            [
                "aws",
                *args,
                "--region",
                self.region,
                "--output",
                "json",
                "--no-cli-pager",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return _json_result(result)

    def preflight(self, tags: Mapping[str, str]) -> Mapping[str, Any]:
        return self._call("batch", "describe-job-queues", "--job-queues", self.queue)

    def wait_ready(self, tags: Mapping[str, str]) -> Mapping[str, Any]:
        deadline = time.monotonic() + 600
        while True:
            environment_response = self._call(
                "batch",
                "describe-compute-environments",
                "--compute-environments",
                self.compute_environment,
            )
            queue_response = self._call(
                "batch", "describe-job-queues", "--job-queues", self.queue
            )
            environments = environment_response.get("computeEnvironments", [])
            queues = queue_response.get("jobQueues", [])
            if (
                isinstance(environments, list)
                and len(environments) == 1
                and isinstance(queues, list)
                and len(queues) == 1
            ):
                environment = environments[0]
                queue = queues[0]
                environment_status = environment.get("status")
                queue_status = queue.get("status")
                if environment_status == "VALID" and queue_status == "VALID":
                    return {
                        "compute_environment_status": environment_status,
                        "queue_status": queue_status,
                    }
                if environment_status in {"INVALID", "DELETING", "DELETED"}:
                    raise CloudManifestError(
                        "qualification compute environment is not usable: "
                        f"{environment_status}"
                    )
                if queue_status in {"INVALID", "DELETING", "DELETED"}:
                    raise CloudManifestError(
                        f"qualification queue is not usable: {queue_status}"
                    )
            if time.monotonic() >= deadline:
                raise CloudManifestError(
                    "qualification environment and queue did not become VALID"
                )
            time.sleep(5)

    def pricing_projection(self, *, worker_seconds: int) -> float:
        data = self._call(
            "ec2",
            "describe-spot-price-history",
            "--instance-types",
            "g6e.2xlarge",
            "--product-descriptions",
            "Linux/UNIX",
            "--max-results",
            "100",
        )
        prices = [
            float(row["SpotPrice"])
            for row in data.get("SpotPriceHistory", [])
            if float(row.get("SpotPrice", 0)) >= 0
        ]
        if not prices:
            raise CloudManifestError("no read-only Spot pricing input available")
        return max(prices) * 2 * worker_seconds / 3600

    def submit_array(
        self, *, size: int, timeout_seconds: int, attempts: int, tags: Mapping[str, str]
    ) -> str:
        if size != 2 or timeout_seconds != 3600 or attempts != 1:
            raise CloudManifestError(
                "Batch submission is not the fixed two-worker contract"
            )
        data = self._call(
            "batch",
            "submit-job",
            "--job-name",
            tags["QualificationAction"],
            "--job-queue",
            self.queue,
            "--job-definition",
            self.job_definition,
            "--array-properties",
            '{"size":2}',
            "--retry-strategy",
            '{"attempts":1}',
            "--tags",
            json.dumps(dict(tags), sort_keys=True),
        )
        self.parent_job_id = data.get("jobId")
        if not self.parent_job_id:
            raise CloudManifestError("Batch submit omitted parent job id")
        return self.parent_job_id

    def collect_admission(self, parent_job_id: str) -> Mapping[str, Any]:
        deadline = time.monotonic() + 3600
        while True:
            parent_response = self._call(
                "batch", "describe-jobs", "--jobs", parent_job_id
            )
            parent_rows = parent_response.get("jobs", [])
            if not isinstance(parent_rows, list) or len(parent_rows) != 1:
                raise CloudManifestError(
                    "Batch describe-jobs did not return exactly one array parent"
                )
            parent = dict(parent_rows[0])
            children: list[dict[str, Any]] = []
            for index in (0, 1):
                detail = self._call(
                    "batch", "describe-jobs", "--jobs", f"{parent_job_id}:{index}"
                )
                rows = detail.get("jobs", [])
                if not isinstance(rows, list) or len(rows) != 1:
                    raise CloudManifestError(
                        "Batch describe-jobs did not return exactly one array child"
                    )
                children.append(dict(rows[0]))
            if parent.get("status") == "FAILED" or any(
                child.get("status") == "FAILED" for child in children
            ):
                require_two_succeeded_children(
                    children, parent_status=parent.get("status")
                )
            if parent.get("status") == "SUCCEEDED" and all(
                child.get("status") == "SUCCEEDED" for child in children
            ):
                break
            if time.monotonic() >= deadline:
                raise CloudManifestError(
                    "qualification array did not reach terminal success"
                )
            time.sleep(5)
        first, second = require_two_succeeded_children(
            children, parent_status=parent.get("status")
        )
        raw = {
            index: retrieve_raw_measurement(
                self,
                artifact_prefix=self.output_root,
                worker_index=index,
            )
            for index in (0, 1)
        }
        instance_ids: list[str] = []
        for child in children:
            instance_id = (child.get("container") or {}).get("instanceId")
            if not isinstance(instance_id, str) or not instance_id:
                raise CloudManifestError("worker identity missing from Batch detail")
            instance_ids.append(instance_id)
        return {
            "parent_status": parent.get("status"),
            "children": tuple(children),
            "instance_ids": tuple(instance_ids),
            "raw_evidence": raw,
        }

    def run_partition_recovery(self, parent_job_id: str) -> Mapping[str, Any]:
        parent_response = self._call("batch", "describe-jobs", "--jobs", parent_job_id)
        parent_rows = parent_response.get("jobs", [])
        if not isinstance(parent_rows, list) or len(parent_rows) != 1:
            raise CloudManifestError(
                "recovery requires exactly one described array parent"
            )
        parent = parent_rows[0]
        if parent.get("status") != "SUCCEEDED":
            raise CloudManifestError("recovery requires a completed array parent")
        child_ids = [f"{parent_job_id}:0", f"{parent_job_id}:1"]
        boundary = canonical_bytes({"parent": parent, "children": child_ids})
        frozen = self.freeze(job_ids=(parent_job_id, *child_ids), boundary=boundary)
        if frozen.get("completed") is not True or frozen.get("boundary") != boundary:
            raise CloudManifestError(
                "interruption freeze did not seal the completed boundary"
            )
        restored = self.restore(job_ids=(parent_job_id, *child_ids), boundary=boundary)
        if (
            restored.get("completed") is not True
            or restored.get("boundary") != boundary
            or restored.get("all_arm_visible_bytes_match") is not True
        ):
            raise CloudManifestError(
                "interruption restore did not validate the exact boundary"
            )
        return {
            "restored_completed_boundary": True,
            "boundary_sha256": hashlib.sha256(boundary).hexdigest(),
            "operations": (
                "describe_jobs_before",
                "freeze_completed_boundary",
                "restore_completed_boundary",
                "describe_jobs_after",
            ),
            "freeze": {"requested": True, "completed": True},
            "restore": {"requested": True, "completed": True},
        }

    def disable_and_drain(self, tags: Mapping[str, str]) -> None:
        self._call(
            "batch",
            "update-job-queue",
            "--job-queue",
            self.queue,
            "--state",
            "DISABLED",
        )
        self._call(
            "batch",
            "update-compute-environment",
            "--compute-environment",
            self.compute_environment,
            "--state",
            "DISABLED",
        )

    def verify_absence(self, tags: Mapping[str, str]) -> Mapping[str, bool]:
        queue = self._call("batch", "describe-job-queues", "--job-queues", self.queue)
        env = self._call(
            "batch",
            "describe-compute-environments",
            "--compute-environments",
            self.compute_environment,
        )
        definition = self._call(
            "batch",
            "describe-job-definitions",
            "--job-definition-name",
            self.job_definition,
            "--status",
            "ACTIVE",
        )
        instances = self._call(
            "ec2",
            "describe-instances",
            "--filters",
            f"Name=tag:QualificationActionId,Values={tags['QualificationActionId']}",
        )
        volumes = self._call(
            "ec2",
            "describe-volumes",
            "--filters",
            f"Name=tag:QualificationActionId,Values={tags['QualificationActionId']}",
        )
        jobs = self._call(
            "batch", "list-jobs", "--job-queue", self.queue, "--job-status", "RUNNING"
        )
        return {
            "jobs": not jobs.get("jobSummaryList"),
            "instances": not instances.get("Reservations"),
            "volumes": not volumes.get("Volumes"),
            "job_definition": not definition.get("jobDefinitions"),
            "queue": not queue.get("jobQueues"),
            "compute_environment": not env.get("computeEnvironments"),
        }


@dataclass(frozen=True)
class RunnerConfig:
    action_id: str
    region: str
    expected_projected_cost_usd: float | None = None
    expected_max_retries: int = MAX_RETRIES
    lock_timeout: str = "60s"


def require_account_plan(
    plan: Mapping[str, Any],
    *,
    action_id: str | None = None,
    provider: Any | None = None,
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Parse real Terraform show-json values and verify existing bindings.

    ``approved_existing_inputs`` and caller-supplied spend booleans are not
    evidence.  The plan carries concrete role, subnet, security-group, tag,
    and environment values; the provider readback below verifies those
    objects explicitly.  The spend binding, when requested, is recomputed
    from the ledger bytes rather than accepted from the plan.
    """

    parsed = parse_terraform_show(plan)
    _require_resource_contract(plan)
    if action_id is not None and parsed["action_id"] != action_id:
        raise CloudManifestError(
            "account plan action tag differs from signed action id"
        )
    if provider is None:
        raise CloudManifestError(
            "account-plan acceptance requires explicit provider read-only checks"
        )
    verify_provider_bindings(provider, parsed)
    if ledger_path is not None:
        derive_spend_history_binding(ledger_path)
    saved_plan_sha256 = plan.get("saved_plan_sha256")
    if not isinstance(saved_plan_sha256, str) or len(saved_plan_sha256) != 64:
        raise CloudManifestError(
            "account plan lacks the exact saved Terraform plan SHA-256"
        )
    parsed["saved_plan_sha256"] = saved_plan_sha256
    parsed["terraform_plan_binding_sha256"] = terraform_plan_binding_digest(
        saved_plan_sha256, parsed["terraform_show_sha256"]
    )
    return parsed


def terraform_mutation_commands(
    *, directory: str = "infra/terraform/qualification"
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return locked future mutation commands; lock disabling is forbidden."""

    prefix = ("terraform", f"-chdir={directory}")
    return (
        prefix + ("apply", "-input=false", "-auto-approve", "-lock-timeout=60s"),
        prefix + ("destroy", "-input=false", "-auto-approve", "-lock-timeout=60s"),
    )


def _require_evidence(receipt: Mapping[str, Any]) -> None:
    children = receipt.get("children")
    if not isinstance(children, Sequence) or isinstance(children, (str, bytes)):
        raise CloudManifestError(
            "admission receipt must retain both described array children"
        )
    require_two_succeeded_children(
        children,
        parent_status=receipt.get("parent_status"),
    )
    ids = require_two_workers(receipt.get("instance_ids", ()))
    evidence = receipt.get("raw_evidence")
    if not isinstance(evidence, Mapping) or set(evidence) != {0, 1}:
        raise CloudManifestError(
            "admission receipt must contain raw evidence for both workers"
        )
    if any(
        not isinstance(evidence[index], (bytes, bytearray)) or not evidence[index]
        for index in (0, 1)
    ):
        raise CloudManifestError("each worker must retain nonempty raw admission bytes")
    if len(set(ids)) != 2:
        raise CloudManifestError("worker identities must remain distinct")


def execute(
    config: RunnerConfig,
    *,
    envelope: Mapping[str, Any],
    admission: Mapping[str, Any],
    key_registry: Mapping[str, Any],
    ledger_path: Any,
    account_plan: Mapping[str, Any],
    provider: QualificationProvider,
    terraform: TerraformQualification,
    verify_authority: Callable[..., Any] = require_preparation_admission,
) -> Mapping[str, Any]:
    """Run the ordered qualification lifecycle through injected seams."""

    if not isinstance(ledger_path, Path):
        raise CloudManifestError(
            "qualification execution requires the authoritative spend ledger path"
        )
    parsed_plan = require_account_plan(
        account_plan,
        action_id=config.action_id,
        provider=provider,
        ledger_path=ledger_path,
    )
    spend_history_sha256 = derive_spend_history_binding(ledger_path)
    if config.expected_max_retries != MAX_RETRIES:
        raise CloudManifestError("qualification runner permits zero retries only")
    projected = provider.pricing_projection(
        worker_seconds=MAX_WORKER_RUNTIME_MINUTES * 60
    )
    if projected >= TOTAL_COST_CEILING_USD:
        raise CloudManifestError(
            "qualification projection must be strictly below USD 100"
        )
    require_cost_ceiling(projected_cost_usd=projected)
    verify_authority(
        envelope,
        admission,
        key_registry=key_registry,
        ledger_path=ledger_path,
        expected_action_id=config.action_id,
        expected_action_class="qualification_audit",
        expected_provider="aws",
        expected_region=config.region,
        expected_manifest_sha256=parsed_plan["terraform_plan_binding_sha256"],
        expected_input_lock_sha256=parsed_plan.get("input_lock_sha256"),
        expected_projected_cost_usd=projected,
        expected_max_retries=MAX_RETRIES,
        spend_history_sha256=spend_history_sha256,
    )

    tags = dict(QUALIFICATION_TAGS)
    tags["QualificationAction"] = config.action_id
    tags["QualificationActionId"] = config.action_id
    tags["QualificationCode"] = str(parsed_plan["qualification_code"])
    preflight = provider.preflight(tags)
    ready: Mapping[str, Any] | None = None
    parent_job_id: str | None = None
    evidence: Mapping[str, Any] | None = None
    recovery: Mapping[str, Any] | None = None
    failure: Exception | None = None
    cleanup_failure: Exception | None = None
    try:
        terraform.apply(lock_timeout=config.lock_timeout, tags=tags)
        ready = provider.wait_ready(tags)
        parent_job_id = provider.submit_array(
            size=2,
            timeout_seconds=MAX_WORKER_RUNTIME_MINUTES * 60,
            attempts=1,
            tags=tags,
        )
        evidence = provider.collect_admission(parent_job_id)
        _require_evidence(evidence)
        recovery = provider.run_partition_recovery(parent_job_id)
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
                "partition/interruption recovery boundary was not restored exactly"
            )
    except Exception as exc:
        failure = exc
    finally:
        try:
            provider.disable_and_drain(tags)
        except Exception as exc:
            cleanup_failure = exc
        try:
            terraform.destroy(lock_timeout=config.lock_timeout, tags=tags)
        except Exception as exc:
            cleanup_failure = cleanup_failure or exc
    absence = provider.verify_absence(tags)
    required_absence = {
        "jobs",
        "instances",
        "volumes",
        "job_definition",
        "queue",
        "compute_environment",
    }
    if set(absence) != required_absence or not all(absence.values()):
        raise CloudManifestError(
            "provider-side qualification teardown absence is incomplete"
        )
    if cleanup_failure is not None:
        raise CloudManifestError(
            "qualification teardown failed closed"
        ) from cleanup_failure
    if failure is not None:
        raise CloudManifestError("qualification failed closed") from failure
    return {
        "parent_job_id": parent_job_id,
        "tags": tags,
        "qualification_only": True,
        "projected_cost_usd": projected,
        "preflight": preflight,
        "ready": ready,
        "evidence": evidence,
        "recovery": recovery,
        "absence": dict(absence),
    }

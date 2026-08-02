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

QUALIFICATION_TAGS = {
    "QualificationPurpose": "dual-l40s-admission-only",
    "QualificationTopology": "two-g6e-2xlarge-l40s",
    "QualificationManagedBy": "pneuma-ephemeral-runner-v1",
}
EXPECTED_RESOURCE_ADDRESSES = frozenset(
    {
        "aws_batch_compute_environment.qualification",
        "aws_batch_job_queue.qualification",
        "aws_batch_job_definition.worker",
    }
)


class QualificationProvider(Protocol):
    def preflight(self, tags: Mapping[str, str]) -> Mapping[str, Any]: ...

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

    def load_account_plan(self, plan_path: Path) -> dict[str, Any]:
        raw = plan_path.read_bytes()
        result = self.run(
            ["terraform", f"-chdir={self.directory}", "show", "-json", str(plan_path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        plan = _json_result(result)
        if not isinstance(plan, dict):
            raise CloudManifestError("terraform show did not return an object")
        plan["plan_sha256"] = hashlib.sha256(raw).hexdigest()
        self.plan_path = plan_path
        return plan

    def apply(self, *, lock_timeout: str, tags: Mapping[str, str]) -> None:
        if self.plan_path is None:
            raise CloudManifestError("no exact saved account plan loaded")
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


class AwsCliAdapter:
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
    ) -> None:
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
        jobs = self._call("batch", "describe-jobs", "--jobs", parent_job_id)
        children = (
            jobs.get("jobs", [])[0].get("arrayProperties", {}).get("statusSummary", {})
            if jobs.get("jobs")
            else {}
        )
        if set(children) != {"0", "1"}:
            raise CloudManifestError(
                "Batch array did not expose exactly two completed children"
            )
        raw: dict[int, bytes] = {}
        ids: list[str] = []
        for index in (0, 1):
            detail = self._call(
                "batch", "describe-jobs", "--jobs", f"{parent_job_id}:{index}"
            )
            instance_id = (
                detail.get("jobs", [{}])[0].get("container", {}).get("instanceId")
            )
            if not instance_id:
                raise CloudManifestError("worker identity missing from Batch detail")
            ids.append(instance_id)
            result = self.run(
                [
                    "aws",
                    "s3",
                    "cp",
                    f"{self.output_root}/worker-{index}/measurement.json",
                    "-",
                    "--region",
                    self.region,
                    "--no-cli-pager",
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0 or not result.stdout:
                raise CloudManifestError("raw admission evidence download failed")
            raw[index] = result.stdout
        return {"instance_ids": tuple(ids), "raw_evidence": raw}

    def run_partition_recovery(self, parent_job_id: str) -> Mapping[str, Any]:
        result = self._call("batch", "describe-jobs", "--jobs", parent_job_id)
        return {"restored_completed_boundary": bool(result.get("jobs"))}

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
            f"Name=tag:QualificationAction,Values={tags['QualificationAction']}",
        )
        volumes = self._call(
            "ec2",
            "describe-volumes",
            "--filters",
            f"Name=tag:QualificationAction,Values={tags['QualificationAction']}",
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
    plan: Mapping[str, Any], *, action_id: str | None = None
) -> None:
    """Accept only the three ephemeral resources and approved existing inputs."""

    changes = plan.get("resource_changes")
    if not isinstance(changes, Sequence) or isinstance(changes, (str, bytes)):
        raise CloudManifestError("account plan must expose resource_changes")
    observed = set()
    for change in changes:
        if (
            not isinstance(change, Mapping)
            or change.get("address") not in EXPECTED_RESOURCE_ADDRESSES
        ):
            raise CloudManifestError(
                "account plan creates a non-qualification resource"
            )
        actions = tuple(change.get("actions", ()))
        if actions != ("create",):
            raise CloudManifestError(
                "qualification account plan must contain only creates"
            )
        observed.add(change["address"])
    if observed != EXPECTED_RESOURCE_ADDRESSES or len(changes) != len(
        EXPECTED_RESOURCE_ADDRESSES
    ):
        raise CloudManifestError(
            "account plan must contain exactly three ephemeral Batch resources"
        )
    if plan.get("approved_existing_inputs") != {
        "roles": True,
        "subnets": True,
        "security_groups": True,
    }:
        raise CloudManifestError(
            "account plan must reference pre-existing approved role/subnet/security-group inputs"
        )
    if action_id is not None and plan.get("qualification_action_id") != action_id:
        raise CloudManifestError(
            "account plan action tag differs from signed action id"
        )


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

    require_account_plan(account_plan, action_id=config.action_id)
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
        expected_manifest_sha256=account_plan["plan_sha256"],
        expected_input_lock_sha256=account_plan.get("input_lock_sha256"),
        expected_projected_cost_usd=projected,
        expected_max_retries=MAX_RETRIES,
        spend_history_sha256=account_plan["spend_history_sha256"],
    )

    tags = dict(QUALIFICATION_TAGS)
    tags["QualificationAction"] = config.action_id
    provider.preflight(tags)
    parent_job_id: str | None = None
    failure: Exception | None = None
    cleanup_failure: Exception | None = None
    try:
        terraform.apply(lock_timeout=config.lock_timeout, tags=tags)
        parent_job_id = provider.submit_array(
            size=2,
            timeout_seconds=MAX_WORKER_RUNTIME_MINUTES * 60,
            attempts=1,
            tags=tags,
        )
        evidence = provider.collect_admission(parent_job_id)
        _require_evidence(evidence)
        recovery = provider.run_partition_recovery(parent_job_id)
        if recovery.get("restored_completed_boundary") is not True:
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
    return {"parent_job_id": parent_job_id, "tags": tags, "qualification_only": True}

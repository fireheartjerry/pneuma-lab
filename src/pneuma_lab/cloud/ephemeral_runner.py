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
    BatchAdmissionError,
    derive_spend_history_binding,
    parse_s3_uri,
    parse_terraform_show,
    parse_terraform_show_json,
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
REQUIRED_ABSENCE_KEYS = frozenset(
    {
        "jobs",
        "instances",
        "volumes",
        "launch_template",
        "network_interfaces",
        "security_group",
        "job_definition",
        "queue",
        "compute_environment",
    }
)
TERMINAL_BATCH_JOB_STATUSES = frozenset({"SUCCEEDED", "FAILED"})


class QualificationExecutionError(CloudManifestError):
    """A post-lifecycle failure carrying sanitized-receipt source evidence."""

    def __init__(self, message: str, *, context: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.context = dict(context)


class QualificationProvider(Protocol):
    def preflight(self, tags: Mapping[str, str]) -> Mapping[str, Any]: ...

    def wait_ready(self, tags: Mapping[str, str]) -> Mapping[str, Any]: ...

    def submit_array(
        self, *, size: int, timeout_seconds: int, attempts: int, tags: Mapping[str, str]
    ) -> str: ...

    def collect_admission(self, parent_job_id: str) -> Mapping[str, Any]: ...

    def run_partition_recovery(self, parent_job_id: str) -> Mapping[str, Any]: ...

    def disable_and_drain(self, tags: Mapping[str, str]) -> None: ...

    def verify_absence(self, tags: Mapping[str, str]) -> Mapping[str, Any]: ...

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
        parsed = parse_terraform_show_json(result.stdout)
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
        if show_result.returncode != 0:
            raise CloudManifestError("terraform show failed before apply")
        current_show = parse_terraform_show_json(show_result.stdout)
        if current_show["terraform_show_sha256"] != self.terraform_show_sha256:
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
    if len(changes) != len(EXPECTED_RESOURCE_ADDRESSES):
        raise CloudManifestError(
            "ephemeral qualification plan must contain exactly four creates"
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
    if any(
        not isinstance(change, Mapping)
        or not isinstance(change.get("change"), Mapping)
        or change["change"].get("actions") != ["create"]
        for change in changes
    ):
        raise CloudManifestError(
            "ephemeral qualification plan must contain only approved creates"
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
        self._fixture_protocol: dict[str, Any] | None = None
        self._fixture_binding: dict[str, Any] | None = None

    def bind_qualification_plan(self, plan: Mapping[str, Any]) -> Mapping[str, Any]:
        """Bind provider arguments and the live fixture bytes to the plan."""

        planned_names = {
            "queue": plan.get("job_queue_name"),
            "job definition": plan.get("job_definition_name"),
            "compute environment": plan.get("compute_environment_name"),
        }
        supplied_names = {
            "queue": self.queue,
            "job definition": self.job_definition,
            "compute environment": self.compute_environment,
        }
        for label, planned in planned_names.items():
            if planned is not None and planned != supplied_names[label]:
                raise CloudManifestError(
                    f"provider {label} differs from the exact Terraform plan"
                )
        if plan.get("output_path") != self.output_root:
            raise CloudManifestError(
                "provider output root differs from the exact Terraform plan"
            )
        input_paths = plan.get("input_paths")
        if not isinstance(input_paths, Mapping) or set(input_paths) != {
            "protocol",
            "architecture",
            "authorization",
            "image",
            "input_lock",
        }:
            raise CloudManifestError("Terraform plan lacks the five fixed fixture inputs")
        payloads: dict[str, bytes] = {}
        for name, uri in input_paths.items():
            if not isinstance(uri, str):
                raise CloudManifestError(f"planned {name} fixture input is not an S3 URI")
            payloads[name] = self.get_object(uri)
        hashes = {
            name: hashlib.sha256(payload).hexdigest()
            for name, payload in payloads.items()
        }
        code = plan.get("qualification_code")
        image = plan.get("image")
        if not isinstance(code, str) or not isinstance(image, str):
            raise CloudManifestError("qualification plan lacks code or immutable image bindings")
        hashes["code"] = hashlib.sha256(code.encode("utf-8")).hexdigest()
        try:
            protocol = json.loads(payloads["protocol"].decode("utf-8"))
            image_record = json.loads(payloads["image"].decode("utf-8"))
            input_lock = json.loads(payloads["input_lock"].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CloudManifestError("qualification fixture inputs are not valid UTF-8 JSON") from exc
        if not isinstance(protocol, Mapping) or not isinstance(image_record, Mapping) or not isinstance(input_lock, Mapping):
            raise CloudManifestError("qualification fixture inputs must be JSON objects")
        from .pilot import validate_protocol

        validate_protocol(protocol)
        expected_hashes = {
            "architecture": hashes["architecture"],
            "authorization": hashes["authorization"],
            "image": hashes["image"],
            "input_lock": hashes["input_lock"],
            "code": hashes["code"],
        }
        if dict(protocol.get("bound_hashes", {})) != expected_hashes:
            raise CloudManifestError(
                "protocol bound hashes differ from the exact action fixture bytes"
            )
        if image_record.get("image") != image or image_record.get("action_id") != plan.get("action_id"):
            raise CloudManifestError("image fixture does not bind the exact qualification action")
        if image_record.get("command_override") is not False:
            raise CloudManifestError("image fixture permits a command override")
        if input_lock.get("action_id") != plan.get("action_id"):
            raise CloudManifestError("input lock does not bind the exact qualification action")
        image_ref, digest = image.rsplit("@", 1)
        host, separator, repository = image_ref.partition("/")
        identity = self._call("sts", "get-caller-identity")
        account_id = identity.get("Account") if isinstance(identity, Mapping) else None
        expected_host = (
            f"{account_id}.dkr.ecr.{self.region}.amazonaws.com"
            if isinstance(account_id, str)
            else None
        )
        if not separator or not repository or host != expected_host:
            raise CloudManifestError("qualification image is not in the bound regional ECR registry")
        image_response = self._call(
            "ecr",
            "describe-images",
            "--repository-name",
            repository,
            "--image-ids",
            f"imageDigest={digest}",
        )
        image_details = image_response.get("imageDetails", [])
        if (
            not isinstance(image_details, list)
            or len(image_details) != 1
            or image_details[0].get("imageDigest") != digest
        ):
            raise CloudManifestError("active immutable qualification image digest was not verified")
        self._fixture_protocol = dict(protocol)
        self._fixture_binding = {
            "input_hashes": hashes,
            "input_paths": dict(input_paths),
            "image": image,
        }
        return {
            "input_lock_sha256": hashes["input_lock"],
            "input_hashes": hashes,
            "image": image,
        }

    def compile_fixture_evidence(
        self, evidence: Mapping[str, Any]
    ) -> Mapping[int, Mapping[str, Any]]:
        """Compile both immutable raw worker records against the live protocol."""

        if self._fixture_protocol is None:
            raise CloudManifestError("fixture evidence was collected before plan binding")
        raw_evidence = evidence.get("raw_evidence")
        if not isinstance(raw_evidence, Mapping) or set(raw_evidence) != {0, 1}:
            raise CloudManifestError("fixture compilation requires raw evidence for both workers")
        measurements: dict[int, tuple[Mapping[str, Any], str]] = {}
        for index in (0, 1):
            payload = raw_evidence[index]
            if not isinstance(payload, (bytes, bytearray)) or not payload:
                raise CloudManifestError("fixture raw evidence must be nonempty bytes")
            try:
                record = json.loads(bytes(payload).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise CloudManifestError("fixture raw evidence is not UTF-8 JSON") from exc
            if not isinstance(record, Mapping):
                raise CloudManifestError("fixture raw evidence is not an object")
            measurements[index] = (
                record,
                hashlib.sha256(bytes(payload)).hexdigest(),
            )
        from .worker_admission import compile_dual_worker_admissions

        return compile_dual_worker_admissions(measurements, self._fixture_protocol)

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

    def _call_absence(self, *args: str) -> Any:
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
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace")
            normalized = detail.lower()
            missing = any(
                marker in detail
                for marker in (
                    "ResourceNotFoundException",
                    "JobQueueNotFoundException",
                    "ComputeEnvironmentNotFoundException",
                )
            ) or (
                "clientexception" in normalized
                and ("does not exist" in normalized or "not found" in normalized)
            )
            if missing:
                return {}
            raise CloudManifestError("provider absence read failed")
        return _json_result(result)

    def preflight(self, tags: Mapping[str, str]) -> Mapping[str, Any]:
        absence = self.verify_absence(tags)
        if not REQUIRED_ABSENCE_KEYS <= set(absence) or not all(
            bool(absence[key]) for key in REQUIRED_ABSENCE_KEYS
        ):
            raise CloudManifestError(
                "qualification preflight found residual action-scoped provider resources"
            )
        return {"provider_absence": dict(absence)}

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

    def capture_submit_evidence(self, parent_job_id: str) -> Mapping[str, Any]:
        """Capture exactly one CloudTrail SubmitJob event for this parent."""

        events: list[Mapping[str, Any]] = []
        next_token: str | None = None
        seen_tokens: set[str] = set()
        while True:
            arguments = [
                "cloudtrail",
                "lookup-events",
                "--lookup-attributes",
                "AttributeKey=EventName,AttributeValue=SubmitJob",
                "--max-results",
                "50",
            ]
            if next_token is not None:
                arguments.extend(("--next-token", next_token))
            response = self._call(*arguments)
            page = response.get("Events", [])
            if not isinstance(page, list):
                raise CloudManifestError("CloudTrail lookup returned invalid Events")
            for event in page:
                if isinstance(event, Mapping):
                    raw = event.get("CloudTrailEvent")
                    if not isinstance(raw, str):
                        continue
                    try:
                        detail = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        raise CloudManifestError(
                            "CloudTrail SubmitJob event was not valid JSON"
                        ) from exc
                    if not isinstance(detail, Mapping):
                        continue
                    response_elements = detail.get("responseElements") or {}
                    if (
                        isinstance(response_elements, Mapping)
                        and response_elements.get("jobId") == parent_job_id
                    ):
                        events.append(event)
            candidate = response.get("NextToken")
            if not isinstance(candidate, str) or not candidate:
                break
            if candidate in seen_tokens:
                raise CloudManifestError("CloudTrail lookup pagination repeated a token")
            seen_tokens.add(candidate)
            next_token = candidate
        if len(events) != 1:
            raise CloudManifestError(
                "CloudTrail must contain exactly one SubmitJob event for the parent"
            )
        event = events[0]
        raw = event.get("CloudTrailEvent")
        detail = json.loads(raw) if isinstance(raw, str) else {}
        request = detail.get("requestParameters") if isinstance(detail, Mapping) else {}
        request = request if isinstance(request, Mapping) else {}
        array_properties = request.get("arrayProperties") or {}
        retry_strategy = request.get("retryStrategy") or request.get("retry_strategy") or {}
        if not isinstance(array_properties, Mapping) or not isinstance(retry_strategy, Mapping):
            raise CloudManifestError("CloudTrail SubmitJob event lacks fixed array bindings")
        if array_properties.get("size") != 2 or retry_strategy.get("attempts") != 1:
            raise CloudManifestError("CloudTrail SubmitJob event differs from the fixed retry contract")
        event_id = event.get("EventId")
        event_time = event.get("EventTime")
        if not isinstance(event_id, str) or not event_id:
            raise CloudManifestError("CloudTrail SubmitJob event has no event id")
        if not isinstance(event_time, str) or not event_time:
            raise CloudManifestError("CloudTrail SubmitJob event has no event time")
        return {
            "cloudtrail_submit_job_event_id_sha256": hashlib.sha256(
                event_id.encode("utf-8")
            ).hexdigest(),
            "submit_event_time_utc": event_time,
            "submit_count_proven": 1,
            "array_size": 2,
            "retry_attempts": 1,
        }

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
                try:
                    require_two_succeeded_children(
                        children, parent_status=parent.get("status")
                    )
                except CloudManifestError as exc:
                    raise BatchAdmissionError(
                        str(exc), parent=parent, children=children
                    ) from exc
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

    def verify_absence(self, tags: Mapping[str, str]) -> Mapping[str, Any]:
        queue = self._call_absence(
            "batch", "describe-job-queues", "--job-queues", self.queue
        )
        env = self._call_absence(
            "batch",
            "describe-compute-environments",
            "--compute-environments",
            self.compute_environment,
        )
        active_definition = self._call_absence(
            "batch",
            "describe-job-definitions",
            "--job-definition-name",
            self.job_definition,
            "--status",
            "ACTIVE",
        )
        inactive_definition = self._call_absence(
            "batch",
            "describe-job-definitions",
            "--job-definition-name",
            self.job_definition,
            "--status",
            "INACTIVE",
        )
        instances = self._call_absence(
            "ec2",
            "describe-instances",
            "--filters",
            f"Name=tag:QualificationActionId,Values={tags['QualificationActionId']}",
        )
        volumes = self._call_absence(
            "ec2",
            "describe-volumes",
            "--filters",
            f"Name=tag:QualificationActionId,Values={tags['QualificationActionId']}",
        )
        launch_templates = self._call_absence(
            "ec2",
            "describe-launch-templates",
            "--filters",
            f"Name=launch-template-name,Values={tags['QualificationActionId']}-worker-*",
        )
        network_interfaces = self._call_absence(
            "ec2",
            "describe-network-interfaces",
            "--filters",
            f"Name=tag:QualificationActionId,Values={tags['QualificationActionId']}",
        )
        security_groups = self._call_absence(
            "ec2",
            "describe-security-groups",
            "--filters",
            f"Name=tag:QualificationActionId,Values={tags['QualificationActionId']}",
        )
        output = parse_s3_uri(self.output_root.rstrip("/") + "/marker")
        output_listing = self._call_absence(
            "s3api",
            "list-objects-v2",
            "--bucket",
            output.bucket,
            "--prefix",
            output.key.rsplit("/", 1)[0] + "/",
        )
        output_objects = output_listing.get("Contents", [])
        if not isinstance(output_objects, list):
            raise CloudManifestError("qualification output listing was not an object collection")
        inactive_rows = inactive_definition.get("jobDefinitions", [])
        if not isinstance(inactive_rows, list):
            raise CloudManifestError("inactive job-definition listing was not an object collection")
        inactive_arns = [
            row.get("jobDefinitionArn")
            for row in inactive_rows
            if isinstance(row, Mapping)
        ]
        if any(not isinstance(arn, str) or not arn for arn in inactive_arns):
            raise CloudManifestError("inactive job-definition history has an invalid ARN")
        if len(inactive_arns) > 1:
            raise CloudManifestError(
                "fresh qualification action has multiple inactive job-definition revisions"
            )
        jobs = True
        if self.parent_job_id is not None:
            job_rows = self._call_absence(
                "batch",
                "describe-jobs",
                "--jobs",
                self.parent_job_id,
                f"{self.parent_job_id}:0",
                f"{self.parent_job_id}:1",
            ).get("jobs", [])
            # Batch retains terminal job history after completion.  Teardown
            # proves that no submitted job remains runnable, not that the
            # provider has erased its immutable audit history.
            jobs = isinstance(job_rows, list) and all(
                isinstance(row, Mapping)
                and row.get("status") in TERMINAL_BATCH_JOB_STATUSES
                for row in job_rows
            )
        return {
            "jobs": jobs,
            "instances": not instances.get("Reservations"),
            "volumes": not volumes.get("Volumes"),
            "launch_template": not launch_templates.get("LaunchTemplates"),
            "network_interfaces": not network_interfaces.get("NetworkInterfaces"),
            "security_group": not security_groups.get("SecurityGroups"),
            # Deregistration makes the revision INACTIVE; AWS retains that
            # revision as provider history.  Only an ACTIVE revision is a
            # live/runnable resource for absence purposes.
            "job_definition": not active_definition.get("jobDefinitions"),
            "queue": not queue.get("jobQueues"),
            "compute_environment": not env.get("computeEnvironments"),
            "provider_history": {
                "inactive_job_definition_history_retained_by_aws": bool(inactive_arns),
                "inactive_job_definition_arn_sha256": (
                    hashlib.sha256(inactive_arns[0].encode("utf-8")).hexdigest()
                    if inactive_arns
                    else None
                ),
            },
            "artifact_prefix": {
                "empty": not output_objects,
                "object_count": len(output_objects),
            },
        }


@dataclass(frozen=True)
class RunnerConfig:
    action_id: str
    region: str
    expected_projected_cost_usd: float | None = None
    expected_max_retries: int = MAX_RETRIES
    lock_timeout: str = "60s"
    require_receipt_evidence: bool = False


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
    raw_show_sha256 = plan.get("terraform_show_sha256")
    if not (
        isinstance(raw_show_sha256, str)
        and len(raw_show_sha256) == 64
        and all(character in "0123456789abcdef" for character in raw_show_sha256)
    ):
        loaded_metadata = plan.get("_qualification")
        candidate = (
            loaded_metadata.get("terraform_show_sha256")
            if isinstance(loaded_metadata, Mapping)
            else None
        )
        if (
            isinstance(candidate, str)
            and len(candidate) == 64
            and all(character in "0123456789abcdef" for character in candidate)
        ):
            raw_show_sha256 = candidate
    if isinstance(raw_show_sha256, str) and len(raw_show_sha256) == 64:
        parsed["terraform_show_sha256"] = raw_show_sha256
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
    bind_plan = getattr(provider, "bind_qualification_plan", None)
    if callable(bind_plan):
        binding = bind_plan(parsed_plan)
        if not isinstance(binding, Mapping):
            raise CloudManifestError("qualification provider returned an invalid fixture binding")
        input_lock_sha256 = binding.get("input_lock_sha256")
        if not isinstance(input_lock_sha256, str) or len(input_lock_sha256) != 64:
            raise CloudManifestError("qualification provider did not bind the live input lock")
        parsed_plan["input_lock_sha256"] = input_lock_sha256
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
    authority_result = verify_authority(
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
    launch: dict[str, Any] = {
        "submit_count_proven": 1,
        "array_size": 2,
        "retry_attempts": 1,
    }
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
        if config.require_receipt_evidence:
            capture = getattr(provider, "capture_submit_evidence", None)
            if not callable(capture):
                raise CloudManifestError(
                    "concrete qualification provider lacks CloudTrail submit evidence"
                )
            observed_launch = capture(parent_job_id)
            if not isinstance(observed_launch, Mapping):
                raise CloudManifestError("CloudTrail submit evidence is not an object")
            launch.update(dict(observed_launch))
            if (
                launch.get("submit_count_proven") != 1
                or launch.get("array_size") != 2
                or launch.get("retry_attempts") != 1
            ):
                raise CloudManifestError(
                    "CloudTrail submit evidence differs from the fixed launch contract"
                )
        evidence = provider.collect_admission(parent_job_id)
        _require_evidence(evidence)
        compile_fixture = getattr(provider, "compile_fixture_evidence", None)
        if not callable(compile_fixture):
            raise CloudManifestError(
                "concrete qualification provider lacks fixture admission compilation"
            )
        compiled = compile_fixture(evidence)
        if not isinstance(compiled, Mapping) or set(compiled) != {0, 1}:
            raise CloudManifestError(
                "fixture admission compilation did not produce exactly two worker receipts"
            )
        evidence = dict(evidence)
        evidence["fixture_admissions"] = compiled
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
        if isinstance(exc, BatchAdmissionError):
            evidence = {
                "parent_status": exc.parent.get("status"),
                "parent": exc.parent,
                "children": exc.children,
                "instance_ids": (),
                "raw_evidence": {},
            }
    finally:
        try:
            provider.disable_and_drain(tags)
        except Exception as exc:
            cleanup_failure = exc
        try:
            terraform.destroy(lock_timeout=config.lock_timeout, tags=tags)
        except Exception as exc:
            cleanup_failure = cleanup_failure or exc
    try:
        absence = provider.verify_absence(tags)
    except Exception as exc:
        context = {
            "plan": dict(parsed_plan),
            "authority": authority_result,
            "projected_cost_usd": projected,
            "preflight": preflight,
            "ready": ready,
            "parent_job_id": parent_job_id,
            "evidence": evidence,
            "recovery": recovery,
            "launch": launch,
            "failure": failure,
            "cleanup_failure": cleanup_failure,
            "absence": None,
        }
        raise QualificationExecutionError(
            "qualification teardown absence failed closed", context=context
        ) from exc
    if not REQUIRED_ABSENCE_KEYS <= set(absence) or not all(
        bool(absence[key]) for key in REQUIRED_ABSENCE_KEYS
    ):
        raise CloudManifestError(
            "provider-side qualification teardown absence is incomplete"
        )
    context = {
        "plan": dict(parsed_plan),
        "authority": authority_result,
        "projected_cost_usd": projected,
        "preflight": preflight,
        "ready": ready,
        "parent_job_id": parent_job_id,
        "evidence": evidence,
        "recovery": recovery,
        "launch": launch,
        "failure": failure,
        "cleanup_failure": cleanup_failure,
        "absence": dict(absence),
    }
    if cleanup_failure is not None:
        raise QualificationExecutionError(
            "qualification teardown failed closed", context=context
        ) from cleanup_failure
    if failure is not None:
        raise QualificationExecutionError(
            "qualification failed closed", context=context
        ) from failure
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
        "plan": dict(parsed_plan),
        "authority": authority_result,
        "launch": dict(launch),
    }

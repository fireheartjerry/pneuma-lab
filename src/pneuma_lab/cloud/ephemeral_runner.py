"""Mockable, fail-closed runner for the ephemeral Batch qualification.

The provider client is an injected seam.  This module contains the ordering
and invariants, but performs no provider calls when imported or tested.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import stat
import time
from typing import Any, Protocol
from urllib.parse import unquote

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

from .ephemeral_qualification import (
    MAX_RETRIES,
    MAX_WORKER_RUNTIME_MINUTES,
    TOTAL_COST_CEILING_USD,
    require_cost_ceiling,
    require_two_workers,
)
from .errors import CloudManifestError
from .preparation_admission import require_preparation_admission
from .authorization_keys import (
    canonical_bytes,
    signed_body,
    validate_key_registry,
)
from .qualification_execution import (
    AwsCliAdapter as ObjectAwsCliAdapter,
    BatchAdmissionError,
    derive_spend_history_binding,
    parse_s3_uri,
    parse_terraform_show,
    parse_terraform_show_json,
    QUALIFICATION_FIXTURE_MODEL,
    QUALIFICATION_FIXTURE_REVISION,
    require_two_succeeded_children,
    retrieve_raw_measurement,
    terraform_plan_binding_digest,
    verify_provider_bindings,
)
from .iam_simulation import (
    QUALIFICATION_WORKER_POLICY_NAME,
    policy_document_sha256,
    run_iam_simulation,
    validate_policy_inventory,
    validate_iam_simulation_matrix,
    validate_worker_resource_policy,
    validate_worker_policy_documents,
)

QUALIFICATION_TAGS = {
    "QualificationPurpose": "dual-l40s-admission-only",
    "QualificationTopology": "two-g6e-2xlarge-l40s",
    "QualificationManagedBy": "pneuma-ephemeral-runner-v1",
}
DEFAULT_QUALIFICATION_EVIDENCE_ROOT = (
    Path(__file__).resolve().parents[3]
    / "docs/research/neurips-2026-workshop/evidence"
)
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
ABSENT_PROVIDER_ERROR_CODES = frozenset(
    {
        "ResourceNotFoundException",
        "JobQueueNotFoundException",
        "JobNotFoundException",
        "ComputeEnvironmentNotFoundException",
        "InvalidLaunchTemplateName.NotFoundException",
        "InvalidGroup.NotFound",
        "InvalidInstanceID.NotFound",
        "InvalidVolume.NotFound",
        "InvalidNetworkInterfaceID.NotFound",
        "NoSuchBucketPolicy",
        "NoSuchEntity",
    }
)
CLOUDTRAIL_SUBMIT_EVIDENCE_TIMEOUT_SECONDS = 300
CLOUDTRAIL_SUBMIT_EVIDENCE_POLL_SECONDS = 5
BATCH_OBSERVATION_TIMEOUT_SECONDS = 3600
BATCH_OBSERVATION_POLL_SECONDS = 5
PROVIDER_READ_RETRY_TIMEOUT_SECONDS = 120
TRANSIENT_PROVIDER_ERROR_CODES = frozenset(
    {
        "InternalException",
        "InternalServerError",
        "JobNotFoundException",
        "RequestLimitExceeded",
        "ResourceNotFoundException",
        "ServerException",
        "ServiceException",
        "ServiceUnavailableException",
        "ThrottlingException",
        "TooManyRequestsException",
    }
)
TRANSIENT_PROVIDER_ERROR_MARKERS = (
    "Could not connect to the endpoint URL",
    "Connection reset",
    "ConnectionResetError",
    "EndpointConnectionError",
    "ReadTimeoutError",
    "Read timed out",
    "timed out",
)


def _require_complete_provider_absence(
    absence: Mapping[str, Any],
    *,
    phase: str,
    allow_retained_raw_artifacts: bool = False,
) -> dict[str, Any]:
    """Require resource absence, allowing only retained failure evidence."""

    if not isinstance(absence, Mapping):
        raise CloudManifestError(f"qualification {phase} absence proof is not an object")
    if not REQUIRED_ABSENCE_KEYS <= set(absence) or not all(
        absence[key] is True for key in REQUIRED_ABSENCE_KEYS
    ):
        raise CloudManifestError(
            f"qualification {phase} found residual action-scoped provider resources"
        )
    artifact = absence.get("artifact_prefix")
    if not isinstance(artifact, Mapping):
        raise CloudManifestError(
            f"qualification {phase} absence proof lacks an output-prefix record"
        )
    object_count = artifact.get("object_count")
    if type(object_count) is not int or object_count < 0:
        raise CloudManifestError(
            f"qualification {phase} output-prefix record has an invalid object count"
        )
    if artifact.get("empty") is True and object_count != 0:
        raise CloudManifestError(
            f"qualification {phase} output-prefix record contradicts its object count"
        )
    if artifact.get("empty") is not True and not allow_retained_raw_artifacts:
        raise CloudManifestError(
            f"qualification {phase} output prefix is not empty"
        )
    return dict(absence)


def _decode_iam_policy_document(value: Any, *, label: str) -> dict[str, Any]:
    """Decode IAM policy output from either AWS CLI string or object shape."""

    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str) and value:
        try:
            decoded = json.loads(unquote(value))
        except json.JSONDecodeError as exc:
            raise CloudManifestError(
                f"IAM {label} policy document is not valid JSON"
            ) from exc
        if isinstance(decoded, Mapping):
            return dict(decoded)
    raise CloudManifestError(f"IAM {label} policy document is missing or invalid")


class QualificationExecutionError(CloudManifestError):
    """A post-lifecycle failure carrying sanitized-receipt source evidence."""

    def __init__(self, message: str, *, context: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.context = dict(context)


class ProviderSubprocessError(CloudManifestError):
    """A sanitized provider CLI failure with retry classification."""

    def __init__(
        self,
        message: str,
        *,
        operation: str,
        error_code: str | None,
        stderr_sha256: str,
        retryable: bool,
    ) -> None:
        super().__init__(message)
        self.operation = operation
        self.error_code = error_code
        self.stderr_sha256 = stderr_sha256
        self.retryable = retryable


def require_fresh_qualification_action(
    action_id: str,
    *,
    evidence_root: Path,
    receipt_path: Path | None = None,
    ledger_path: Path | None = None,
) -> None:
    """Refuse action IDs already represented in retained qualification evidence."""

    if not isinstance(action_id, str) or not action_id:
        raise CloudManifestError("qualification action id must be nonempty")
    action_pattern = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(action_id)}(?![A-Za-z0-9])"
    )
    terminal_evidence_markers = (
        "execution-receipt",
        "preflight-no-go",
        "terminal-no-go",
        "terminal",
        "no-go",
        "completion",
        "teardown",
    )
    if evidence_root.exists():
        matches = sorted(
            path
            for path in evidence_root.rglob("*")
            if path.is_file()
            and action_pattern.search(path.relative_to(evidence_root).as_posix())
            and any(
                marker in path.relative_to(evidence_root).as_posix()
                for marker in terminal_evidence_markers
            )
        )
        if matches:
            raise CloudManifestError(
                "qualification action id is already represented in terminal retained evidence: "
                + matches[0].as_posix()
            )
    if receipt_path is not None and receipt_path.exists():
        raise CloudManifestError(
            "qualification receipt path already exists; refusing to overwrite evidence"
        )
    if ledger_path is not None:
        if not ledger_path.is_file():
            raise CloudManifestError(
                "qualification freshness requires the authoritative spend ledger"
            )
        ledger_text = ledger_path.read_text(encoding="utf-8")
        active_ledger_markers = (
            "read-only account-plan validation",
            "fresh qualification preparation envelope",
            "fresh preparation envelope",
            "exact one-use qualification admission",
        )
        for line in ledger_text.splitlines():
            if action_pattern.search(line) and not any(
                marker in line.lower() for marker in active_ledger_markers
            ):
                raise CloudManifestError(
                    "qualification action id is already represented in terminal spend-ledger history"
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

    def verify_absence(self, tags: Mapping[str, str]) -> Mapping[str, Any]: ...

    def pricing_projection(self, *, worker_seconds: int) -> float: ...

    def verify_post_apply_iam_binding(
        self, *, plan: Mapping[str, Any], expected_policy_sha256: str
    ) -> Mapping[str, Any]: ...


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


def _provider_error_code(result: subprocess.CompletedProcess[bytes]) -> str | None:
    """Extract only an AWS CLI structured error code from stderr."""

    detail = result.stderr.decode("utf-8", errors="replace").strip()
    # The AWS CLI itself prefixes usage failures with ``aws: error:``.  That
    # token is not a provider error code and must not mask the real
    # classification (or turn a transient read into a misleading
    # ``error_code=aws`` receipt).
    match = re.search(r"\(([A-Za-z0-9_.]+)\)", detail)
    if match is not None:
        return match.group(1)
    match = re.match(r"\s*([A-Za-z0-9_.]+):", detail)
    if match is None or match.group(1).lower() in {"aws", "error", "usage"}:
        return None
    return match.group(1)


def _provider_subprocess_error(
    args: Sequence[str], result: subprocess.CompletedProcess[bytes]
) -> ProviderSubprocessError:
    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    error_code = _provider_error_code(result)
    retryable = error_code in TRANSIENT_PROVIDER_ERROR_CODES or any(
        marker in stderr for marker in TRANSIENT_PROVIDER_ERROR_MARKERS
    )
    operation = " ".join(args[:2]) if len(args) >= 2 else "aws provider call"
    stderr_sha256 = hashlib.sha256(stderr.encode("utf-8")).hexdigest()
    return ProviderSubprocessError(
        (
            f"provider subprocess failed for {operation} "
            f"(error_code={error_code or 'unknown'}, stderr_sha256={stderr_sha256})"
        ),
        operation=operation,
        error_code=error_code,
        stderr_sha256=stderr_sha256,
        retryable=retryable,
    )


def _validate_kms_verification(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the sanitized live KMS verification receipt and its digest."""

    required = {
        "signing_algorithm",
        "envelope_signature_valid",
        "admission_signature_valid",
        "key_id_sha256",
        "registry_key_id",
        "public_key_sha256",
        "verification_sha256",
    }
    if not isinstance(record, Mapping) or set(record) != required:
        raise CloudManifestError("KMS verification evidence has an unregistered shape")
    if (
        record["signing_algorithm"] != "ED25519_SHA_512"
        or record["envelope_signature_valid"] is not True
        or record["admission_signature_valid"] is not True
    ):
        raise CloudManifestError("live KMS verification is not green")
    for field in ("key_id_sha256", "public_key_sha256"):
        value = record[field]
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise CloudManifestError(f"KMS verification {field} is not a digest")
    if not isinstance(record["registry_key_id"], str) or not record["registry_key_id"]:
        raise CloudManifestError("KMS verification lacks its registry key id")
    unsigned = {key: value for key, value in record.items() if key != "verification_sha256"}
    expected = hashlib.sha256(canonical_bytes(unsigned)).hexdigest()
    if record["verification_sha256"] != expected:
        raise CloudManifestError("KMS verification digest is not derived from its bytes")
    return dict(record)


def _validate_post_apply_iam_binding(
    record: Mapping[str, Any], *, expected_policy_sha256: str
) -> dict[str, Any]:
    """Validate the sanitized IAM readback performed immediately after apply."""

    required = {
        "status",
        "expected_policy_sha256",
        "observed_policy_sha256",
        "policy_inventory_sha256",
    }
    if not isinstance(record, Mapping) or set(record) != required:
        raise CloudManifestError(
            "post-apply IAM binding evidence has an unregistered shape"
        )
    if (
        record.get("status") != "pass"
        or record.get("expected_policy_sha256") != expected_policy_sha256
        or record.get("observed_policy_sha256") != expected_policy_sha256
    ):
        raise CloudManifestError(
            "post-apply worker IAM policy differs from authority"
        )
    for field in ("expected_policy_sha256", "observed_policy_sha256", "policy_inventory_sha256"):
        value = record.get(field)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise CloudManifestError(
                f"post-apply IAM {field} is not a digest"
            )
    return dict(record)


class TerraformAdapter:
    """Terraform adapter whose subprocess is injectable and never retries."""

    def __init__(
        self,
        run: CommandRunner,
        *,
        directory: str = "infra/terraform/qualification",
        variable_file: Path | None = None,
    ) -> None:
        self.run = run
        self.directory = directory
        self.variable_file = variable_file.resolve() if variable_file is not None else None
        self.plan_path: Path | None = None
        self.saved_plan_sha256: str | None = None
        self.terraform_show_sha256: str | None = None
        self.terraform_plan_binding_sha256: str | None = None
        self.variable_file_sha256: str | None = None
        self.backend_initialized = False

    def _capture_variable_file(self) -> str | None:
        if self.variable_file is None:
            return None
        if self.variable_file.suffix != ".tfvars" or self.variable_file.is_symlink():
            raise CloudManifestError(
                "qualification Terraform variable file must be a regular .tfvars file"
            )
        try:
            mode = stat.S_IMODE(self.variable_file.stat().st_mode)
            payload = self.variable_file.read_bytes()
        except OSError as exc:
            raise CloudManifestError(
                "qualification Terraform variable file is not readable"
            ) from exc
        if mode != 0o600:
            raise CloudManifestError(
                "qualification Terraform variable file must have mode 0600"
            )
        if not payload:
            raise CloudManifestError("qualification Terraform variable file is empty")
        return hashlib.sha256(payload).hexdigest()

    def _require_variable_file_unchanged(self, phase: str) -> None:
        if self.variable_file is None:
            return
        if self.variable_file_sha256 is None:
            raise CloudManifestError(
                f"qualification Terraform variable file was not bound before {phase}"
            )
        current = self._capture_variable_file()
        if current != self.variable_file_sha256:
            raise CloudManifestError(
                f"qualification Terraform variable file changed before {phase}"
            )

    def initialize(self) -> None:
        """Initialize the committed shared backend before reading or mutating state."""

        result = self.run(
            [
                "terraform",
                f"-chdir={self.directory}",
                "init",
                "-input=false",
                "-reconfigure",
                "-lockfile=readonly",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise CloudManifestError(
                "terraform shared backend initialization failed"
            )
        self.backend_initialized = True

    def load_account_plan(self, plan_path: Path) -> dict[str, Any]:
        if not self.backend_initialized:
            raise CloudManifestError(
                "terraform shared backend must be initialized before loading a plan"
            )
        if plan_path.is_symlink() or not plan_path.is_file():
            raise CloudManifestError(
                "saved Terraform plan must be a regular file"
            )
        plan_path = plan_path.resolve()
        self.variable_file_sha256 = self._capture_variable_file()
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
        self.terraform_plan_binding_sha256 = plan["terraform_plan_binding_sha256"]
        return plan

    def apply(self, *, lock_timeout: str, tags: Mapping[str, str]) -> None:
        if not self.backend_initialized:
            raise CloudManifestError(
                "terraform shared backend must be initialized before apply"
            )
        if self.plan_path is None or self.saved_plan_sha256 is None:
            raise CloudManifestError("no exact saved account plan loaded")
        self._require_variable_file_unchanged("apply")
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
        current_show_sha256 = current_show.get("terraform_show_sha256")
        if (
            not isinstance(current_show_sha256, str)
            or len(current_show_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in current_show_sha256
            )
            or current_show_sha256 != self.terraform_show_sha256
        ):
            raise CloudManifestError(
                "Terraform show bytes changed after plan review"
            )
        if self.terraform_plan_binding_sha256 is None:
            raise CloudManifestError("no exact composite Terraform binding loaded")
        current_binding_sha256 = terraform_plan_binding_digest(
            current_plan_sha256, current_show_sha256
        )
        if current_binding_sha256 != self.terraform_plan_binding_sha256:
            raise CloudManifestError(
                "Terraform composite plan binding changed after plan review"
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
        if not self.backend_initialized:
            raise CloudManifestError(
                "terraform shared backend must be initialized before destroy"
            )
        self._require_variable_file_unchanged("destroy")
        arguments = [
            "terraform",
            f"-chdir={self.directory}",
            "destroy",
            "-input=false",
            "-auto-approve",
            f"-lock-timeout={lock_timeout}",
        ]
        if self.variable_file is not None:
            arguments.append(f"-var-file={self.variable_file}")
        result = self.run(
            arguments,
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

    planned = plan.get("planned_values")
    root = planned.get("root_module") if isinstance(planned, Mapping) else None
    if not isinstance(root, Mapping):
        raise CloudManifestError(
            "ephemeral qualification plan lacks planned resource values"
        )
    planned_addresses: list[str] = []

    def walk(module: Mapping[str, Any]) -> None:
        resources = module.get("resources", [])
        if not isinstance(resources, list):
            raise CloudManifestError(
                "ephemeral qualification planned module has an invalid resource list"
            )
        for resource in resources:
            if not isinstance(resource, Mapping) or not isinstance(
                resource.get("address"), str
            ):
                raise CloudManifestError(
                    "ephemeral qualification planned resource lacks an address"
                )
            planned_addresses.append(resource["address"])
        children = module.get("child_modules", [])
        if not isinstance(children, list):
            raise CloudManifestError(
                "ephemeral qualification planned module has invalid child modules"
            )
        for child in children:
            if not isinstance(child, Mapping):
                raise CloudManifestError(
                    "ephemeral qualification planned child module is invalid"
                )
            walk(child)

    walk(root)
    if len(planned_addresses) != len(set(planned_addresses)) or set(
        planned_addresses
    ) != EXPECTED_RESOURCE_ADDRESSES:
        raise CloudManifestError(
            "ephemeral qualification planned values must contain exactly the four approved resources"
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
        self._observed_action_job_ids: set[str] = set()
        self._drained_action_job_ids: set[str] = set()
        self._last_submit_tags: dict[str, str] | None = None
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
            if not isinstance(planned, str) or not planned:
                raise CloudManifestError(
                    f"provider {label} is not bound to a concrete Terraform name"
                )
            if planned != supplied_names[label]:
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

    def _list_iam_rows(
        self, operation: str, role_name: str, result_key: str
    ) -> list[Any]:
        """Read every inline or attached worker-role policy without truncation."""

        rows: list[Any] = []
        marker: str | None = None
        seen: set[str] = set()
        while True:
            arguments = ["iam", operation, "--role-name", role_name]
            if marker is not None:
                arguments.extend(("--marker", marker))
            response = self._call(*arguments)
            page = response.get(result_key) if isinstance(response, Mapping) else None
            if not isinstance(page, list):
                raise CloudManifestError(
                    f"IAM {operation} response lacks its {result_key} list"
                )
            rows.extend(page)
            if "IsTruncated" not in response:
                # AWS CLI omits the false pagination marker on current IAM
                # responses when the first page is complete.
                return rows
            truncated = response.get("IsTruncated")
            if truncated is False:
                return rows
            if truncated is not True:
                raise CloudManifestError(
                    f"IAM {operation} response has an invalid IsTruncated flag"
                )
            candidate = response.get("Marker")
            if not isinstance(candidate, str) or not candidate or candidate in seen:
                raise CloudManifestError(
                    f"IAM {operation} pagination did not provide a fresh marker"
                )
            seen.add(candidate)
            marker = candidate

    def capture_worker_policy_inventory(
        self,
        *,
        plan: Mapping[str, Any],
        expected_policy_sha256: str,
    ) -> Mapping[str, Any]:
        """Enumerate every worker-role policy and reject broad S3 grants."""

        role_name = plan.get("worker_role_name")
        role_arn = plan.get("worker_role_arn")
        if not isinstance(role_name, str) or not role_name or not isinstance(role_arn, str):
            raise CloudManifestError("IAM policy inventory lacks the verified worker role")
        documents: list[tuple[str, str, Mapping[str, Any]]] = []
        inline_names = self._list_iam_rows(
            "list-role-policies", role_name, "PolicyNames"
        )
        if not all(isinstance(name, str) and name for name in inline_names):
            raise CloudManifestError("IAM inline policy listing contains an invalid name")
        if inline_names.count(QUALIFICATION_WORKER_POLICY_NAME) != 1:
            raise CloudManifestError(
                "worker role must contain exactly one qualification artifact policy"
            )
        for policy_name in inline_names:
            response = self._call(
                "iam",
                "get-role-policy",
                "--role-name",
                role_name,
                "--policy-name",
                policy_name,
            )
            encoded = response.get("PolicyDocument") if isinstance(response, Mapping) else None
            document = _decode_iam_policy_document(encoded, label="inline")
            documents.append(("inline", policy_name, document))
            if policy_name == QUALIFICATION_WORKER_POLICY_NAME and (
                policy_document_sha256(document) != expected_policy_sha256
            ):
                raise CloudManifestError(
                    "qualification artifact policy differs from authority"
                )

        attached_rows = self._list_iam_rows(
            "list-attached-role-policies", role_name, "AttachedPolicies"
        )
        for attached in attached_rows:
            if not isinstance(attached, Mapping):
                raise CloudManifestError("IAM attached-policy listing contains an invalid row")
            policy_arn = attached.get("PolicyArn")
            if not isinstance(policy_arn, str) or not policy_arn:
                raise CloudManifestError("IAM attached-policy row lacks its ARN")
            policy_response = self._call(
                "iam", "get-policy", "--policy-arn", policy_arn
            )
            policy = policy_response.get("Policy") if isinstance(policy_response, Mapping) else None
            default_version = policy.get("DefaultVersionId") if isinstance(policy, Mapping) else None
            if not isinstance(default_version, str) or not default_version:
                raise CloudManifestError("IAM managed policy lacks its default version")
            version_response = self._call(
                "iam",
                "get-policy-version",
                "--policy-arn",
                policy_arn,
                "--version-id",
                default_version,
            )
            version = (
                version_response.get("PolicyVersion")
                if isinstance(version_response, Mapping)
                else None
            )
            encoded = version.get("Document") if isinstance(version, Mapping) else None
            document = _decode_iam_policy_document(encoded, label="managed")
            documents.append(("managed", policy_arn, document))

        inventory = validate_worker_policy_documents(
            tuple(documents),
            input_paths=plan.get("input_paths", {}),
            output_root=str(plan.get("output_path", "")),
            iam_role_arn=role_arn,
        )
        return validate_policy_inventory(inventory)

    def capture_iam_simulation(
        self,
        *,
        plan: Mapping[str, Any],
        action_id: str,
        expected_policy_sha256: str,
    ) -> Mapping[str, Any]:
        """Run the exact action/resource IAM matrix before any apply."""

        output = parse_s3_uri(str(plan["output_path"]).rstrip("/") + "/marker")
        policy_response = self._call_absence(
            "s3api",
            "get-bucket-policy",
            "--bucket",
            output.bucket,
            missing_codes=frozenset({"NoSuchBucketPolicy"}),
        )
        resource_policy: Mapping[str, Any] | None = None
        if policy_response:
            policy_text = policy_response.get("Policy")
            if not isinstance(policy_text, str) or not policy_text:
                raise CloudManifestError(
                    "S3 bucket-policy response lacks its JSON policy document"
                )
            try:
                decoded_policy = json.loads(policy_text)
            except json.JSONDecodeError as exc:
                raise CloudManifestError(
                    "S3 bucket-policy response is not valid JSON"
                ) from exc
            if not isinstance(decoded_policy, Mapping):
                raise CloudManifestError("S3 bucket policy must be a JSON object")
            resource_policy = decoded_policy
            validate_worker_resource_policy(
                resource_policy,
                input_paths=plan.get("input_paths", {}),
                output_root=str(plan.get("output_path", "")),
                iam_role_arn=str(plan.get("worker_role_arn", "")),
            )
        role_name = plan.get("worker_role_name")
        if not isinstance(role_name, str) or not role_name:
            raise CloudManifestError(
                "IAM simulation plan lacks the verified worker role name"
            )
        worker_policy_response = self._call(
            "iam",
            "get-role-policy",
            "--role-name",
            role_name,
            "--policy-name",
            QUALIFICATION_WORKER_POLICY_NAME,
        )
        encoded_document = (
            worker_policy_response.get("PolicyDocument")
            if isinstance(worker_policy_response, Mapping)
            else None
        )
        worker_policy = _decode_iam_policy_document(
            encoded_document,
            label="qualification worker",
        )
        live_policy_sha256 = policy_document_sha256(worker_policy)
        if live_policy_sha256 != expected_policy_sha256:
            raise CloudManifestError(
                "live qualification worker policy differs from authority"
            )
        inventory = self.capture_worker_policy_inventory(
            plan=plan,
            expected_policy_sha256=expected_policy_sha256,
        )
        return run_iam_simulation(
            self._call,
            plan=plan,
            action_id=action_id,
            expected_policy_sha256=expected_policy_sha256,
            resource_policy=resource_policy,
            policy_inventory=inventory,
        )

    def verify_post_apply_iam_binding(
        self, *, plan: Mapping[str, Any], expected_policy_sha256: str
    ) -> Mapping[str, Any]:
        """Re-read the effective worker-role policy after apply, before launch."""

        inventory = self.capture_worker_policy_inventory(
            plan=plan,
            expected_policy_sha256=expected_policy_sha256,
        )
        rows = inventory.get("policies")
        expected_identifier_sha256 = hashlib.sha256(
            QUALIFICATION_WORKER_POLICY_NAME.encode("utf-8")
        ).hexdigest()
        matches = [
            row
            for row in rows
            if isinstance(row, Mapping)
            and row.get("source") == "inline"
            and row.get("identifier_sha256") == expected_identifier_sha256
            and row.get("document_sha256") == expected_policy_sha256
        ]
        if len(matches) != 1:
            raise CloudManifestError(
                "post-apply worker IAM policy does not match the signed binding"
            )
        inventory_sha256 = inventory.get("inventory_sha256")
        if (
            not isinstance(inventory_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", inventory_sha256)
        ):
            raise CloudManifestError(
                "post-apply worker IAM inventory lacks a valid digest"
            )
        return {
            "status": "pass",
            "expected_policy_sha256": expected_policy_sha256,
            "observed_policy_sha256": matches[0]["document_sha256"],
            "policy_inventory_sha256": inventory_sha256,
        }

    def capture_kms_verification(
        self,
        *,
        envelope: Mapping[str, Any],
        admission: Mapping[str, Any],
        key_registry: Mapping[str, Any],
        authority: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Verify the live KMS public key and both signed authority records."""

        kms_authority = authority.get("kms")
        if not isinstance(kms_authority, Mapping):
            raise CloudManifestError("authority evidence lacks KMS binding")
        key_alias = kms_authority.get("key_alias")
        registry_key_id = kms_authority.get("registry_key_id")
        if not isinstance(key_alias, str) or not key_alias:
            raise CloudManifestError("authority KMS binding lacks its key alias")
        if not isinstance(registry_key_id, str) or not registry_key_id:
            raise CloudManifestError("authority KMS binding lacks its registry key id")
        registry = validate_key_registry(key_registry)
        registered = next(
            (key for key in registry["keys"] if key["key_id"] == registry_key_id),
            None,
        )
        if not isinstance(registered, Mapping) or registered.get("status") != "active":
            raise CloudManifestError("authority KMS key is not active in the committed registry")
        public_response = self._call(
            "kms", "get-public-key", "--key-id", key_alias
        )
        if not isinstance(public_response, Mapping):
            raise CloudManifestError("live KMS public-key response is not an object")
        signing_algorithms = public_response.get("SigningAlgorithms")
        if (
            public_response.get("KeyUsage") != "SIGN_VERIFY"
            or not isinstance(signing_algorithms, list)
            or "ED25519_SHA_512" not in signing_algorithms
        ):
            raise CloudManifestError("live KMS key is not an Ed25519 SIGN_VERIFY key")
        key_id = public_response.get("KeyId")
        encoded_public = public_response.get("PublicKey")
        if not isinstance(key_id, str) or not key_id:
            raise CloudManifestError("live KMS public-key response lacks its key id")
        if not isinstance(encoded_public, str) or not encoded_public:
            raise CloudManifestError("live KMS public-key response lacks its public key")
        try:
            der_public = base64.b64decode(encoded_public, validate=True)
            loaded_public = serialization.load_der_public_key(der_public)
        except (ValueError, TypeError) as exc:
            raise CloudManifestError("live KMS public key is not valid DER") from exc
        if not isinstance(loaded_public, Ed25519PublicKey):
            raise CloudManifestError("live KMS public key is not Ed25519")
        raw_public = loaded_public.public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        if raw_public.hex() != registered.get("public_key_hex"):
            raise CloudManifestError(
                "live KMS public key differs from the committed approver registry"
            )
        for label, record in (("envelope", envelope), ("admission", admission)):
            approval = record.get("human_authorization")
            if not isinstance(approval, Mapping):
                raise CloudManifestError(f"{label} lacks its human authorization")
            if approval.get("key_id") != registry_key_id:
                raise CloudManifestError(f"{label} is signed by the wrong registry key")
            signature = approval.get("signature_ed25519")
            if not isinstance(signature, str):
                raise CloudManifestError(f"{label} lacks its Ed25519 signature")
            try:
                signature_bytes = bytes.fromhex(signature)
                if len(signature_bytes) != 64:
                    raise ValueError("signature length")
                loaded_public.verify(signature_bytes, canonical_bytes(signed_body(record)))
            except (ValueError, TypeError, InvalidSignature) as exc:
                raise CloudManifestError(f"live KMS verification failed for {label}") from exc
        verification = {
            "signing_algorithm": "ED25519_SHA_512",
            "envelope_signature_valid": True,
            "admission_signature_valid": True,
            "key_id_sha256": hashlib.sha256(key_id.encode("utf-8")).hexdigest(),
            "registry_key_id": registry_key_id,
            "public_key_sha256": hashlib.sha256(raw_public).hexdigest(),
        }
        verification["verification_sha256"] = hashlib.sha256(
            canonical_bytes(verification)
        ).hexdigest()
        return _validate_kms_verification(verification)

    def _call(self, *args: str) -> Any:
        argv = [
            "aws",
            *args,
            "--region",
            self.region,
            "--output",
            "json",
            "--no-cli-pager",
        ]
        result = self.run(
            argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise _provider_subprocess_error(args, result)
        return _json_result(result)

    def _call_with_retry(
        self,
        *args: str,
        deadline: float,
        retry_unclassified: bool = False,
    ) -> Any:
        """Retry bounded read failures before a deadline.

        Batch observation uses ``retry_unclassified`` because the service has
        emitted transient control-plane errors without a parseable AWS code;
        the caller still supplies the hard observation deadline.
        """

        while True:
            try:
                return self._call(*args)
            except ProviderSubprocessError as exc:
                remaining = deadline - time.monotonic()
                if (not exc.retryable and not retry_unclassified) or remaining <= 0:
                    raise
                time.sleep(min(BATCH_OBSERVATION_POLL_SECONDS, remaining))

    def _describe_batch_jobs(
        self, job_ids: Sequence[str], *, deadline: float
    ) -> Mapping[str, Any]:
        response = self._call_with_retry(
            "batch",
            "describe-jobs",
            "--jobs",
            *job_ids,
            deadline=deadline,
            retry_unclassified=True,
        )
        if not isinstance(response, Mapping):
            raise CloudManifestError("Batch describe-jobs returned a non-object response")
        return response

    def _call_absence(
        self,
        *args: str,
        missing_codes: frozenset[str] = ABSENT_PROVIDER_ERROR_CODES,
    ) -> Any:
        deadline = time.monotonic() + PROVIDER_READ_RETRY_TIMEOUT_SECONDS
        argv = [
            "aws",
            *args,
            "--region",
            self.region,
            "--output",
            "json",
            "--no-cli-pager",
        ]
        while True:
            result = self.run(
                argv,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode == 0:
                return _json_result(result)
            if _provider_error_code(result) in missing_codes:
                return {}
            error = _provider_subprocess_error(args, result)
            remaining = deadline - time.monotonic()
            if not error.retryable or remaining <= 0:
                raise ProviderSubprocessError(
                    f"provider absence read failed: {error}",
                    operation=error.operation,
                    error_code=error.error_code,
                    stderr_sha256=error.stderr_sha256,
                    retryable=error.retryable,
                ) from error
            time.sleep(min(BATCH_OBSERVATION_POLL_SECONDS, remaining))

    def preflight(self, tags: Mapping[str, str]) -> Mapping[str, Any]:
        absence = self.verify_absence(tags)
        return {"provider_absence": _require_complete_provider_absence(absence, phase="preflight")}

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
                    environment_arn = environment.get("computeEnvironmentArn")
                    queue_order = queue.get("computeEnvironmentOrder")
                    if not isinstance(environment_arn, str) or not environment_arn:
                        raise CloudManifestError(
                            "qualification compute environment readback lacks its ARN"
                        )
                    if (
                        not isinstance(queue_order, list)
                        or len(queue_order) != 1
                        or not isinstance(queue_order[0], Mapping)
                        or queue_order[0].get("order") != 1
                        or queue_order[0].get("computeEnvironment") != environment_arn
                    ):
                        raise CloudManifestError(
                            "qualification queue is not bound to the verified compute environment"
                        )
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
        expected_tag_keys = set(QUALIFICATION_TAGS) | {
            "QualificationAction",
            "QualificationActionId",
            "QualificationCode",
        }
        if set(tags) != expected_tag_keys or any(
            not isinstance(value, str) or not value for value in tags.values()
        ):
            raise CloudManifestError(
                "Batch submission tags are not the exact qualification tag set"
            )
        if tags["QualificationActionId"] != tags["QualificationAction"]:
            raise CloudManifestError(
                "Batch submission action and action-id tags differ"
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
            "--timeout",
            json.dumps(
                {"attemptDurationSeconds": timeout_seconds},
                sort_keys=True,
                separators=(",", ":"),
            ),
            "--tags",
            json.dumps(dict(tags), sort_keys=True),
        )
        if not isinstance(data, Mapping):
            raise CloudManifestError("Batch submit returned a non-object response")
        parent_job_id = data.get("jobId")
        if not isinstance(parent_job_id, str) or not parent_job_id:
            raise CloudManifestError("Batch submit omitted parent job id")
        self.parent_job_id = parent_job_id
        self._last_submit_tags = dict(tags)
        return parent_job_id

    def capture_submit_evidence(self, parent_job_id: str) -> Mapping[str, Any]:
        """Capture exactly one CloudTrail SubmitJob event for this parent."""

        if self._last_submit_tags is None:
            raise CloudManifestError(
                "CloudTrail SubmitJob evidence was requested without the concrete submission"
            )
        expected_job_name = self._last_submit_tags["QualificationAction"]
        deadline = time.monotonic() + CLOUDTRAIL_SUBMIT_EVIDENCE_TIMEOUT_SECONDS
        events: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
        while True:
            events = []
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
                response = self._call_with_retry(*arguments, deadline=deadline)
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
                        request_parameters = detail.get("requestParameters") or {}
                        observed_job_name = (
                            request_parameters.get("jobName")
                            if isinstance(request_parameters, Mapping)
                            else None
                        )
                        observed_parent = (
                            response_elements.get("jobId")
                            if isinstance(response_elements, Mapping)
                            else None
                        )
                        if detail.get("eventName") != "SubmitJob":
                            continue
                        if observed_parent == parent_job_id or observed_job_name == expected_job_name:
                            if isinstance(observed_parent, str) and observed_parent:
                                self._observed_action_job_ids.add(observed_parent)
                            events.append((event, detail))
                candidate = response.get("NextToken")
                if not isinstance(candidate, str) or not candidate:
                    break
                if candidate in seen_tokens:
                    raise CloudManifestError("CloudTrail lookup pagination repeated a token")
                seen_tokens.add(candidate)
                next_token = candidate
            if len(events) > 1:
                raise CloudManifestError(
                    "CloudTrail must contain exactly one SubmitJob event for the qualification action"
                )
            if events:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CloudManifestError(
                    "CloudTrail SubmitJob evidence was not indexed before the bounded lookup deadline"
                )
            time.sleep(min(CLOUDTRAIL_SUBMIT_EVIDENCE_POLL_SECONDS, remaining))
        event, detail = events[0]
        response_elements = detail.get("responseElements")
        if (
            not isinstance(response_elements, Mapping)
            or response_elements.get("jobId") != parent_job_id
        ):
            raise CloudManifestError(
                "CloudTrail SubmitJob event response does not match the submitted parent job"
            )
        request = detail.get("requestParameters") if isinstance(detail, Mapping) else {}
        request = request if isinstance(request, Mapping) else {}
        array_properties = request.get("arrayProperties") or {}
        retry_strategy = request.get("retryStrategy") or request.get("retry_strategy") or {}
        timeout = request.get("timeout") or request.get("attemptDurationSeconds")
        if not isinstance(array_properties, Mapping) or not isinstance(retry_strategy, Mapping):
            raise CloudManifestError("CloudTrail SubmitJob event lacks fixed array bindings")
        if array_properties.get("size") != 2 or retry_strategy.get("attempts") != 1:
            raise CloudManifestError("CloudTrail SubmitJob event differs from the fixed retry contract")
        if timeout is not None and (
            not isinstance(timeout, Mapping)
            or timeout.get("attemptDurationSeconds") != 3600
        ):
            raise CloudManifestError("CloudTrail SubmitJob event differs from the fixed timeout contract")
        if timeout is None:
            # CloudTrail's Batch event shape may omit the timeout even though
            # SubmitJob accepted it and the job record carries it.  Read the
            # provider's authoritative job detail instead of converting that
            # telemetry omission into an early teardown/no-go.
            detail_response = self._describe_batch_jobs(
                (parent_job_id,), deadline=deadline
            )
            detail_rows = detail_response.get("jobs", [])
            if not isinstance(detail_rows, list) or len(detail_rows) != 1:
                raise CloudManifestError(
                    "Batch timeout readback did not return exactly one submitted parent"
                )
            detail_row = detail_rows[0]
            observed_timeout = detail_row.get("timeout") if isinstance(detail_row, Mapping) else None
            if (
                not isinstance(observed_timeout, Mapping)
                or observed_timeout.get("attemptDurationSeconds") != 3600
            ):
                raise CloudManifestError(
                    "Batch timeout readback differs from the fixed timeout contract"
                )

        def batch_identifier_matches(
            observed: Any, expected: str, *, job_definition: bool = False
        ) -> bool:
            if not isinstance(observed, str) or not observed:
                return False
            if observed == expected:
                return True
            leaf = observed.rsplit("/", 1)[-1]
            if leaf == expected:
                return True
            if job_definition and re.fullmatch(
                re.escape(expected) + r":[0-9]+", leaf
            ):
                return True
            return False

        if request.get("jobName") != expected_job_name:
            raise CloudManifestError(
                "CloudTrail SubmitJob event has the wrong qualification job name"
            )
        if not batch_identifier_matches(request.get("jobQueue"), self.queue):
            raise CloudManifestError(
                "CloudTrail SubmitJob event is bound to the wrong job queue"
            )
        if not batch_identifier_matches(
            request.get("jobDefinition"), self.job_definition, job_definition=True
        ):
            raise CloudManifestError(
                "CloudTrail SubmitJob event is bound to the wrong job definition"
            )
        request_tags = request.get("tags")
        if not isinstance(request_tags, Mapping) or dict(request_tags) != self._last_submit_tags:
            raise CloudManifestError(
                "CloudTrail SubmitJob event tags differ from the exact qualification tags"
            )
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
        if not isinstance(parent_job_id, str) or not parent_job_id:
            raise CloudManifestError("Batch admission requires a nonempty parent job id")
        deadline = time.monotonic() + BATCH_OBSERVATION_TIMEOUT_SECONDS
        while True:
            parent_response = self._describe_batch_jobs(
                (parent_job_id,), deadline=deadline
            )
            parent_rows = parent_response.get("jobs", [])
            if not isinstance(parent_rows, list):
                raise CloudManifestError(
                    "Batch describe-jobs returned an invalid array parent collection"
                )
            if not parent_rows:
                if time.monotonic() >= deadline:
                    raise CloudManifestError(
                        "Batch describe-jobs did not expose the submitted array parent before the bounded observation deadline"
                    )
                time.sleep(BATCH_OBSERVATION_POLL_SECONDS)
                continue
            if len(parent_rows) != 1:
                raise CloudManifestError(
                    "Batch describe-jobs did not return exactly one array parent"
                )
            if not isinstance(parent_rows[0], Mapping):
                raise BatchAdmissionError(
                    "Batch describe-jobs returned a non-object array parent",
                    parent={},
                    children=(),
                    failure_kind="batch_admission_observation_invalid",
                )
            parent = dict(parent_rows[0])
            if parent.get("jobId") != parent_job_id:
                raise BatchAdmissionError(
                    "Batch describe-jobs returned the wrong array parent",
                    parent=parent,
                    children=(),
                    failure_kind="batch_identity_binding_failure",
                )
            children: list[dict[str, Any]] = []
            for index in (0, 1):
                expected_child_id = f"{parent_job_id}:{index}"
                detail = self._describe_batch_jobs(
                    (f"{parent_job_id}:{index}",), deadline=deadline
                )
                rows = detail.get("jobs", [])
                if not isinstance(rows, list):
                    raise CloudManifestError(
                        "Batch describe-jobs returned an invalid array child collection"
                    )
                if not rows:
                    break
                if len(rows) != 1:
                    raise CloudManifestError(
                        "Batch describe-jobs did not return exactly one array child"
                    )
                if not isinstance(rows[0], Mapping):
                    raise BatchAdmissionError(
                        "Batch describe-jobs returned a non-object array child",
                        parent=parent,
                        children=children,
                        failure_kind="batch_admission_observation_invalid",
                    )
                child = dict(rows[0])
                if child.get("jobId") != expected_child_id:
                    raise BatchAdmissionError(
                        "Batch describe-jobs returned the wrong array child",
                        parent=parent,
                        children=(*children, child),
                        failure_kind="batch_identity_binding_failure",
                    )
                array = child.get("arrayProperties") or {}
                if not isinstance(array, Mapping) or array.get("index") != index:
                    raise BatchAdmissionError(
                        "Batch describe-jobs returned the wrong array child index",
                        parent=parent,
                        children=(*children, child),
                        failure_kind="batch_identity_binding_failure",
                    )
                children.append(child)
            if len(children) != 2:
                if time.monotonic() >= deadline:
                    raise CloudManifestError(
                        "Batch describe-jobs did not expose both submitted array children before the bounded observation deadline"
                    )
                time.sleep(BATCH_OBSERVATION_POLL_SECONDS)
                continue
            if parent.get("status") == "FAILED" or any(
                child.get("status") == "FAILED" for child in children
            ):
                try:
                    require_two_succeeded_children(
                        children, parent_status=parent.get("status")
                    )
                except CloudManifestError as exc:
                    # A failed fixture worker may have published its immutable
                    # raw measurement before a later local lifecycle error.
                    # Retrieve any such evidence for the terminal no-go
                    # receipt, but never replace the concrete Batch failure
                    # with a best-effort evidence-read failure.
                    raw_evidence: dict[int, bytes] = {}
                    instance_ids: list[str] = []
                    for index in (0, 1):
                        try:
                            payload = retrieve_raw_measurement(
                                self,
                                artifact_prefix=self.output_root,
                                worker_index=index,
                            )
                        except Exception:
                            continue
                        raw_evidence[index] = payload
                        try:
                            record = json.loads(payload.decode("utf-8"))
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            continue
                        instance_id = record.get("instance_id") if isinstance(record, Mapping) else None
                        if isinstance(instance_id, str) and instance_id:
                            instance_ids.append(instance_id)
                    raise BatchAdmissionError(
                        str(exc),
                        parent=parent,
                        children=children,
                        raw_evidence=raw_evidence,
                        instance_ids=tuple(instance_ids),
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
        require_two_succeeded_children(
            children, parent_status=parent.get("status")
        )
        instance_ids_by_index: dict[int, str] = {}
        for child in children:
            array = child.get("arrayProperties") or {}
            index = array.get("index") if isinstance(array, Mapping) else None
            instance_id = (child.get("container") or {}).get("instanceId")
            if type(index) is not int or index not in (0, 1):
                raise BatchAdmissionError(
                    "worker identity lacks a valid array index",
                    parent=parent,
                    children=children,
                    failure_kind="worker_identity_binding_failure",
                )
            if not isinstance(instance_id, str) or not instance_id:
                raise BatchAdmissionError(
                    "worker identity missing from Batch detail",
                    parent=parent,
                    children=children,
                    failure_kind="worker_identity_binding_failure",
                )
            if index in instance_ids_by_index:
                raise BatchAdmissionError(
                    "worker identity repeats an array index",
                    parent=parent,
                    children=children,
                    failure_kind="worker_identity_binding_failure",
                )
            instance_ids_by_index[index] = instance_id
        if set(instance_ids_by_index) != {0, 1}:
            raise BatchAdmissionError(
                "worker identities do not cover both array indexes",
                parent=parent,
                children=children,
                failure_kind="worker_identity_binding_failure",
            )
        instance_ids = (
            instance_ids_by_index[0],
            instance_ids_by_index[1],
        )
        raw: dict[int, bytes] = {}
        for index in (0, 1):
            try:
                raw[index] = retrieve_raw_measurement(
                    self,
                    artifact_prefix=self.output_root,
                    worker_index=index,
                )
            except Exception as exc:
                raise BatchAdmissionError(
                    "raw worker artifact retrieval failed",
                    parent=parent,
                    children=children,
                    raw_evidence=raw,
                    instance_ids=instance_ids,
                    failure_kind="raw_artifact_retrieval_failure",
                ) from exc
        return {
            "parent_status": parent.get("status"),
            "children": tuple(children),
            "instance_ids": instance_ids,
            "raw_evidence": raw,
        }

    def run_partition_recovery(self, parent_job_id: str) -> Mapping[str, Any]:
        if not isinstance(parent_job_id, str) or not parent_job_id:
            raise CloudManifestError("recovery requires a nonempty parent job id")
        parent_response = self._call("batch", "describe-jobs", "--jobs", parent_job_id)
        parent_rows = parent_response.get("jobs", [])
        if not isinstance(parent_rows, list) or len(parent_rows) != 1:
            raise CloudManifestError(
                "recovery requires exactly one described array parent"
            )
        parent = parent_rows[0]
        if not isinstance(parent, Mapping) or parent.get("jobId") != parent_job_id:
            raise CloudManifestError("recovery returned the wrong array parent")
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

    def _list_action_job_ids(self, action_id: str) -> set[str]:
        """Find every queued or historical job with this exact action name."""

        if not isinstance(action_id, str) or not action_id:
            return set()
        found: set[str] = set()
        for status in (
            "SUBMITTED",
            "PENDING",
            "RUNNABLE",
            "STARTING",
            "RUNNING",
            "SUCCEEDED",
            "FAILED",
        ):
            next_token: str | None = None
            seen_tokens: set[str] = set()
            while True:
                arguments = [
                    "batch",
                    "list-jobs",
                    "--job-queue",
                    self.queue,
                    "--job-status",
                    status,
                ]
                if next_token is not None:
                    arguments.extend(("--next-token", next_token))
                response = self._call_absence(*arguments)
                rows = response.get("jobSummaryList") if isinstance(response, Mapping) else None
                if not isinstance(rows, list):
                    raise CloudManifestError(
                        "Batch list-jobs returned an invalid job summary collection"
                    )
                for row in rows:
                    if not isinstance(row, Mapping):
                        raise CloudManifestError(
                            "Batch list-jobs returned a non-object job summary"
                        )
                    if row.get("jobName") == action_id:
                        job_id = row.get("jobId")
                        if not isinstance(job_id, str) or not job_id:
                            raise CloudManifestError(
                                "action-scoped Batch job summary lacks its job id"
                            )
                        found.add(job_id)
                candidate = response.get("nextToken")
                if not isinstance(candidate, str) or not candidate:
                    break
                if candidate in seen_tokens:
                    raise CloudManifestError("Batch list-jobs pagination repeated a token")
                seen_tokens.add(candidate)
                next_token = candidate
        return found

    def _list_cloudtrail_action_job_ids(self, action_id: str) -> set[str]:
        """Find every SubmitJob parent recorded for this exact action name."""

        if not isinstance(action_id, str) or not action_id:
            return set()
        found: set[str] = set()
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
            response = self._call_absence(*arguments)
            events = response.get("Events") if isinstance(response, Mapping) else None
            if not isinstance(events, list):
                raise CloudManifestError(
                    "CloudTrail absence lookup returned an invalid Events collection"
                )
            for event in events:
                if not isinstance(event, Mapping):
                    raise CloudManifestError(
                        "CloudTrail absence lookup returned a non-object event"
                    )
                raw = event.get("CloudTrailEvent")
                if not isinstance(raw, str) or not raw:
                    raise CloudManifestError(
                        "CloudTrail absence event lacks its raw event document"
                    )
                try:
                    detail = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise CloudManifestError(
                        "CloudTrail absence event is not valid JSON"
                    ) from exc
                if not isinstance(detail, Mapping) or detail.get("eventName") != "SubmitJob":
                    continue
                request = detail.get("requestParameters")
                if not isinstance(request, Mapping) or request.get("jobName") != action_id:
                    continue
                response_elements = detail.get("responseElements")
                job_id = (
                    response_elements.get("jobId")
                    if isinstance(response_elements, Mapping)
                    else None
                )
                if not isinstance(job_id, str) or not job_id:
                    raise CloudManifestError(
                        "CloudTrail action event lacks its submitted parent job id"
                    )
                found.add(job_id)
            candidate = response.get("NextToken") if isinstance(response, Mapping) else None
            if not isinstance(candidate, str) or not candidate:
                break
            if candidate in seen_tokens:
                raise CloudManifestError(
                    "CloudTrail absence lookup pagination repeated a token"
                )
            seen_tokens.add(candidate)
            next_token = candidate
        return found

    @staticmethod
    def _complete_job_rows(
        rows: Any, expected_job_ids: set[str], *, phase: str
    ) -> dict[str, Mapping[str, Any]]:
        if not isinstance(rows, list):
            raise CloudManifestError(f"Batch {phase} returned an invalid jobs collection")
        indexed: dict[str, Mapping[str, Any]] = {}
        for row in rows:
            if not isinstance(row, Mapping):
                raise CloudManifestError(f"Batch {phase} returned a non-object job row")
            job_id = row.get("jobId")
            if not isinstance(job_id, str) or not job_id:
                raise CloudManifestError(f"Batch {phase} returned a job without an id")
            if job_id in indexed:
                raise CloudManifestError(f"Batch {phase} returned a duplicate job row")
            indexed[job_id] = row
        if set(indexed) != expected_job_ids:
            raise CloudManifestError(
                f"Batch {phase} did not return exactly every requested job"
            )
        return indexed

    def disable_and_drain(self, tags: Mapping[str, str]) -> None:
        """Disable scheduling, then drain or terminate every submitted job."""

        action_id = tags.get("QualificationActionId")
        job_ids = set(self._observed_action_job_ids)
        if isinstance(action_id, str) and action_id:
            job_ids.update(self._list_action_job_ids(action_id))
        if self.parent_job_id is not None:
            job_ids.update(
                {
                    self.parent_job_id,
                    f"{self.parent_job_id}:0",
                    f"{self.parent_job_id}:1",
                }
            )
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
        if job_ids:
            ordered_job_ids = tuple(sorted(job_ids))
            deadline = time.monotonic() + 600
            termination_sent = False
            while True:
                response = self._call_absence(
                    "batch", "describe-jobs", "--jobs", *ordered_job_ids
                )
                rows = self._complete_job_rows(
                    response.get("jobs") if isinstance(response, Mapping) else None,
                    set(ordered_job_ids),
                    phase="drain",
                )
                if all(
                    row.get("status") in TERMINAL_BATCH_JOB_STATUSES
                    for row in rows.values()
                ):
                    self._drained_action_job_ids = set(ordered_job_ids)
                    break
                if time.monotonic() >= deadline:
                    if termination_sent:
                        raise CloudManifestError(
                            "Batch jobs did not drain after the signed termination request"
                        )
                    for job_id in ordered_job_ids:
                        self._call(
                            "batch",
                            "terminate-job",
                            "--job-id",
                            job_id,
                            "--reason",
                            "signed qualification teardown drain",
                        )
                    termination_sent = True
                    deadline = time.monotonic() + 300
                    continue
                time.sleep(5)
        else:
            self._drained_action_job_ids = set()

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
            "Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down",
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
        action_id = tags.get("QualificationActionId")
        jobs = True
        cloudtrail_job_ids = (
            self._list_cloudtrail_action_job_ids(action_id)
            if isinstance(action_id, str) and action_id
            else set()
        )
        expected_cloudtrail_ids = set(self._observed_action_job_ids)
        if self.parent_job_id is None:
            jobs = not cloudtrail_job_ids
        elif expected_cloudtrail_ids:
            jobs = cloudtrail_job_ids == expected_cloudtrail_ids
        else:
            jobs = len(cloudtrail_job_ids) == 1
        if isinstance(action_id, str) and action_id and queue.get("jobQueues"):
            jobs = jobs and not self._list_action_job_ids(action_id)
        if self.parent_job_id is not None:
            expected_job_ids = set(self._observed_action_job_ids)
            expected_job_ids.update(
                {
                    self.parent_job_id,
                    f"{self.parent_job_id}:0",
                    f"{self.parent_job_id}:1",
                }
            )
            expected_job_ids.update(self._drained_action_job_ids)
            if self._drained_action_job_ids != expected_job_ids:
                jobs = False
            job_rows = self._call_absence(
                "batch",
                "describe-jobs",
                "--jobs",
                *sorted(expected_job_ids),
            )
            # Batch retains terminal job history after completion.  Teardown
            # proves that no submitted job remains runnable, not that the
            # provider has erased its immutable audit history.
            try:
                described = self._complete_job_rows(
                    job_rows.get("jobs") if isinstance(job_rows, Mapping) else None,
                    expected_job_ids,
                    phase="absence",
                )
            except CloudManifestError:
                jobs = False
            else:
                jobs = jobs and all(
                    row.get("status") in TERMINAL_BATCH_JOB_STATUSES
                    for row in described.values()
                )
        live_instances = []
        reservations = instances.get("Reservations", [])
        if isinstance(reservations, list):
            for reservation in reservations:
                if not isinstance(reservation, Mapping):
                    continue
                rows = reservation.get("Instances", [])
                if not isinstance(rows, list):
                    continue
                live_instances.extend(
                    row
                    for row in rows
                    if isinstance(row, Mapping)
                    and (row.get("State") or {}).get("Name") != "terminated"
                )
        return {
            "jobs": jobs,
            "instances": not live_instances,
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
    action_evidence_root: Path | None = None
    receipt_path: Path | None = None


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
    provider_bindings = verify_provider_bindings(provider, parsed)
    attached_role = provider_bindings.get("role")
    if not isinstance(attached_role, Mapping) or not isinstance(
        attached_role.get("Arn"), str
    ):
        raise CloudManifestError(
            "provider verification did not return the attached worker role ARN"
        )
    # The Terraform stack binds an existing instance profile, so the attached
    # role is often absent from planned resources. Carry the independently
    # verified role ARN into the parsed plan for IAM simulation; never
    # substitute the instance-profile ARN.
    parsed["worker_role_arn"] = attached_role["Arn"]
    parsed["worker_role_name"] = attached_role.get("RoleName")
    parsed["subnet_az_map"] = tuple(
        {
            "availability_zone": row["AvailabilityZone"],
            "subnet_id": row["SubnetId"],
        }
        for row in sorted(
            provider_bindings["subnets"],
            key=lambda value: str(value.get("AvailabilityZone")),
        )
    )
    parsed["image_digest"] = parsed["image"].rsplit("@", 1)[1]
    parsed["output_prefix"] = parsed["output_path"]
    job_definition = parsed.get("job_definition")
    if not isinstance(job_definition, Mapping):
        raise CloudManifestError("account plan lacks its parsed job definition")
    environment = job_definition.get("environment")
    environment_values = {
        row.get("name"): row.get("value")
        for row in environment
        if isinstance(row, Mapping) and isinstance(row.get("name"), str)
    } if isinstance(environment, list) else {}
    if environment_values.get("QUALIFICATION_MODEL") != QUALIFICATION_FIXTURE_MODEL:
        raise CloudManifestError("account plan fixture model is not the registered non-model fixture")
    if environment_values.get("QUALIFICATION_MODEL_REVISION") != QUALIFICATION_FIXTURE_REVISION:
        raise CloudManifestError("account plan fixture revision is not the registered fixture revision")
    parsed["qualification_model"] = environment_values["QUALIFICATION_MODEL"]
    parsed["qualification_model_revision"] = environment_values["QUALIFICATION_MODEL_REVISION"]
    if ledger_path is not None:
        derive_spend_history_binding(ledger_path)

    def valid_sha256(value: Any) -> bool:
        return isinstance(value, str) and len(value) == 64 and all(
            character in "0123456789abcdef" for character in value
        )

    saved_plan_sha256 = plan.get("saved_plan_sha256")
    if not valid_sha256(saved_plan_sha256):
        raise CloudManifestError(
            "account plan lacks the exact saved Terraform plan SHA-256"
        )
    parsed["saved_plan_sha256"] = saved_plan_sha256
    top_level_show_sha256 = plan.get("terraform_show_sha256")
    loaded_metadata = plan.get("_qualification")
    nested_show_sha256 = (
        loaded_metadata.get("terraform_show_sha256")
        if isinstance(loaded_metadata, Mapping)
        else None
    )
    nested_saved_plan_sha256 = (
        loaded_metadata.get("saved_plan_sha256")
        if isinstance(loaded_metadata, Mapping)
        else None
    )

    if not valid_sha256(saved_plan_sha256) or not valid_sha256(
        nested_saved_plan_sha256
    ):
        raise CloudManifestError(
            "qualification plan requires both exact saved Terraform plan SHA-256 bindings"
        )
    if saved_plan_sha256 != nested_saved_plan_sha256:
        raise CloudManifestError(
            "qualification plan contains conflicting saved Terraform plan SHA-256 bindings"
        )
    if not valid_sha256(top_level_show_sha256) or not valid_sha256(nested_show_sha256):
        raise CloudManifestError(
            "qualification plan requires both exact Terraform show SHA-256 bindings"
        )
    if top_level_show_sha256 != nested_show_sha256:
        raise CloudManifestError(
            "qualification plan contains conflicting Terraform show SHA-256 "
            "bindings"
        )
    parsed["terraform_show_sha256"] = top_level_show_sha256
    expected_plan_binding_sha256 = terraform_plan_binding_digest(
        saved_plan_sha256, parsed["terraform_show_sha256"]
    )
    top_level_plan_binding_sha256 = plan.get("terraform_plan_binding_sha256")
    nested_plan_binding_sha256 = (
        loaded_metadata.get("terraform_plan_binding_sha256")
        if isinstance(loaded_metadata, Mapping)
        else None
    )
    if not valid_sha256(top_level_plan_binding_sha256) or not valid_sha256(
        nested_plan_binding_sha256
    ):
        raise CloudManifestError(
            "qualification plan requires both exact composite Terraform bindings"
        )
    if (
        top_level_plan_binding_sha256 != nested_plan_binding_sha256
        or top_level_plan_binding_sha256 != expected_plan_binding_sha256
    ):
        raise CloudManifestError(
            "qualification plan contains a conflicting composite Terraform binding"
        )
    parsed["saved_plan_sha256"] = saved_plan_sha256
    parsed["terraform_plan_binding_sha256"] = expected_plan_binding_sha256
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
    authority_evidence: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Run the ordered qualification lifecycle through injected seams."""

    if not isinstance(ledger_path, Path):
        raise CloudManifestError(
            "qualification execution requires the authoritative spend ledger path"
        )
    require_fresh_qualification_action(
        config.action_id,
        evidence_root=config.action_evidence_root or DEFAULT_QUALIFICATION_EVIDENCE_ROOT,
        receipt_path=config.receipt_path,
        ledger_path=ledger_path,
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
    if not isinstance(authority_result, Mapping):
        raise CloudManifestError("authority verifier did not return an object")
    execution_authority = (
        authority_evidence if authority_evidence is not None else authority_result
    )
    if not isinstance(execution_authority, Mapping):
        raise CloudManifestError("execution authority evidence is not an object")

    tags = dict(QUALIFICATION_TAGS)
    tags["QualificationAction"] = config.action_id
    tags["QualificationActionId"] = config.action_id
    tags["QualificationCode"] = str(parsed_plan["qualification_code"])
    preflight = provider.preflight(tags)
    if not isinstance(preflight, Mapping):
        raise CloudManifestError("qualification preflight evidence is not an object")
    _require_complete_provider_absence(
        preflight.get("provider_absence"), phase="preflight"
    )
    ready: Mapping[str, Any] | None = None
    parent_job_id: str | None = None
    evidence: Mapping[str, Any] | None = None
    recovery: Mapping[str, Any] | None = None
    iam_simulation: Mapping[str, Any] | None = None
    post_apply_iam_binding: Mapping[str, Any] | None = None
    kms_verification: Mapping[str, Any] | None = None
    launch: dict[str, Any] = {
        # A requested submit contract is not proof of exactly one provider
        # submission. The concrete receipt path replaces this sentinel with
        # the live CloudTrail result before a receipt can be built.
        "submit_count_proven": 0,
        "array_size": 2,
        "retry_attempts": 1,
    }
    failure: Exception | None = None
    cleanup_failure: Exception | None = None
    try:
        if config.require_receipt_evidence:
            capture_iam = getattr(provider, "capture_iam_simulation", None)
            expected_policy_sha256 = execution_authority.get("iam_policy_sha256")
            if not callable(capture_iam):
                raise CloudManifestError(
                    "concrete qualification provider lacks live IAM simulation"
                )
            if not isinstance(expected_policy_sha256, str):
                raise CloudManifestError(
                    "authority receipt lacks the action-specific IAM policy hash"
                )
            observed_iam = capture_iam(
                plan=parsed_plan,
                action_id=config.action_id,
                expected_policy_sha256=expected_policy_sha256,
            )
            if not isinstance(observed_iam, Mapping):
                raise CloudManifestError("IAM simulation evidence is not an object")
            iam_simulation = validate_iam_simulation_matrix(
                observed_iam,
                action_id=config.action_id,
                plan=parsed_plan,
                expected_policy_sha256=expected_policy_sha256,
            )
            if not isinstance(iam_simulation.get("policy_inventory"), Mapping):
                raise CloudManifestError(
                    "live IAM simulation lacks the complete worker-policy inventory"
                )
            capture_kms = getattr(provider, "capture_kms_verification", None)
            if not callable(capture_kms):
                raise CloudManifestError(
                    "concrete qualification provider lacks live KMS verification"
                )
            observed_kms = capture_kms(
                envelope=envelope,
                admission=admission,
                key_registry=key_registry,
                authority=execution_authority,
            )
            if not isinstance(observed_kms, Mapping):
                raise CloudManifestError("KMS verification evidence is not an object")
            kms_verification = _validate_kms_verification(observed_kms)
        terraform.apply(lock_timeout=config.lock_timeout, tags=tags)
        if config.require_receipt_evidence:
            verify_post_apply = getattr(provider, "verify_post_apply_iam_binding", None)
            expected_policy_sha256 = execution_authority.get("iam_policy_sha256")
            if not callable(verify_post_apply):
                raise CloudManifestError(
                    "concrete qualification provider lacks post-apply IAM readback"
                )
            if not isinstance(expected_policy_sha256, str):
                raise CloudManifestError(
                    "authority receipt lacks the action-specific IAM policy hash"
                )
            observed_post_apply = verify_post_apply(
                plan=parsed_plan,
                expected_policy_sha256=expected_policy_sha256,
            )
            post_apply_iam_binding = _validate_post_apply_iam_binding(
                observed_post_apply,
                expected_policy_sha256=expected_policy_sha256,
            )
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
                "instance_ids": exc.instance_ids,
                "raw_evidence": exc.raw_evidence,
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
            "iam_simulation": iam_simulation,
            "post_apply_iam_binding": post_apply_iam_binding,
            "kms_verification": kms_verification,
            "launch": launch,
            "failure": failure,
            "cleanup_failure": cleanup_failure,
            "absence": None,
        }
        raise QualificationExecutionError(
            "qualification teardown absence failed closed", context=context
        ) from exc
    try:
        _require_complete_provider_absence(
            absence,
            phase="teardown",
            allow_retained_raw_artifacts=failure is not None,
        )
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
            "iam_simulation": iam_simulation,
            "post_apply_iam_binding": post_apply_iam_binding,
            "kms_verification": kms_verification,
            "launch": launch,
            "failure": failure,
            "cleanup_failure": cleanup_failure,
            "absence": absence,
        }
        raise QualificationExecutionError(
            "qualification teardown absence validation failed closed",
            context=context,
        ) from exc
    context = {
        "plan": dict(parsed_plan),
        "authority": authority_result,
        "projected_cost_usd": projected,
        "preflight": preflight,
        "ready": ready,
        "parent_job_id": parent_job_id,
        "evidence": evidence,
        "recovery": recovery,
        "iam_simulation": iam_simulation,
        "post_apply_iam_binding": post_apply_iam_binding,
        "kms_verification": kms_verification,
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
        "iam_simulation": iam_simulation,
        "post_apply_iam_binding": post_apply_iam_binding,
        "kms_verification": kms_verification,
        "absence": dict(absence),
        "plan": dict(parsed_plan),
        "authority": authority_result,
        "launch": dict(launch),
    }

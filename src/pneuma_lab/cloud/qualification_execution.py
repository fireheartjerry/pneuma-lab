"""Provider-injected execution contracts for the dual-worker qualification.

The qualification path has two deliberately separate halves.  The pure half
parses the Terraform plan, verifies the signed input authority, and checks
receipts.  The provider half is a small AWS CLI adapter which is only called
when an executor explicitly asks it to do so.  Tests inject a transport into
that adapter; no AWS SDK or credentials are needed to exercise the contracts.

In particular, an S3 URI is an object locator, never a local pathname.  Inputs
are downloaded, hashed, and atomically installed as ordinary local files
before a probe can be started.  Raw worker measurements are published under
different, immutable worker keys and can be retrieved through the same
adapter.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import unquote, urlsplit

from .authorization_keys import canonical_bytes, canonical_ledger_digest
from .errors import CloudManifestError
from .manifests import validate_worker_admission_measurement
from .pilot import WORKER_COUNT
from .retrieval import require_authorized


QUALIFICATION_CODE_ENV = "QUALIFICATION_CODE"
QUALIFICATION_ACTION_ID_ENV = "QUALIFICATION_ACTION_ID"
QUALIFICATION_FIXTURE_MODEL = "fixture-only-cuda"
QUALIFICATION_FIXTURE_REVISION = "fixture-only-v1"
RAW_MEASUREMENT_NAME = "raw-measurement.json"
_TERRAFORM_RUNNER_METADATA_KEYS = frozenset(
    {
        "_qualification",
        "saved_plan_sha256",
        "terraform_plan_binding_sha256",
        "terraform_show_sha256",
    }
)
QUALIFICATION_AZS = (
    "us-east-1a",
    "us-east-1b",
    "us-east-1c",
    "us-east-1d",
)
QUALIFICATION_IMAGE_DIGEST_RE = re.compile(r"@sha256:[0-9a-f]{64}$")
QUALIFICATION_RESOURCE_REQUIREMENTS = frozenset(
    {("GPU", "1"), ("VCPU", "8"), ("MEMORY", "60000")}
)


class BatchAdmissionError(CloudManifestError):
    """A terminal Batch admission failure retaining provider observations."""

    def __init__(
        self,
        message: str,
        *,
        parent: Mapping[str, Any],
        children: Sequence[Mapping[str, Any]],
    ) -> None:
        super().__init__(message)
        self.parent = dict(parent)
        self.children = tuple(dict(child) for child in children)


def terraform_plan_binding_digest(
    saved_plan_sha256: str, terraform_show_sha256: str
) -> str:
    """Bind the exact saved plan bytes and parsed Terraform show bytes together."""

    if not all(
        isinstance(value, str) and len(value) == 64
        for value in (saved_plan_sha256, terraform_show_sha256)
    ):
        raise CloudManifestError("Terraform plan binding requires two SHA-256 digests")
    return hashlib.sha256(
        canonical_bytes(
            {
                "saved_plan_sha256": saved_plan_sha256,
                "terraform_show_sha256": terraform_show_sha256,
            }
        )
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class S3ObjectRef:
    """A parsed S3 object address, kept separate from :class:`pathlib.Path`."""

    bucket: str
    key: str

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket}/{self.key}"


def parse_s3_uri(value: str) -> S3ObjectRef:
    """Parse one nonempty ``s3://bucket/key`` URI.

    Accepting a URI as a ``Path`` is a particularly nasty failure mode: on
    POSIX it looks like a relative path and the probe can start with no input
    at all.  Parsing is therefore strict and happens before any local path is
    constructed.
    """

    if not isinstance(value, str) or not value:
        raise CloudManifestError("S3 object address must be a nonempty s3:// URI")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "s3"
        or not parsed.netloc
        or not parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise CloudManifestError(f"invalid S3 object URI: {value!r}")
    key = unquote(parsed.path.lstrip("/"))
    if (
        not key
        or "\\" in key
        or any(part in {"", ".", ".."} for part in key.split("/"))
    ):
        raise CloudManifestError(f"invalid S3 object key: {value!r}")
    return S3ObjectRef(bucket=parsed.netloc, key=key)


def _as_bytes(value: Any, *, label: str) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, Mapping) and isinstance(value.get("Body"), (bytes, bytearray)):
        return bytes(value["Body"])
    raise CloudManifestError(f"{label} transport response was not bytes")


class QualificationTransport(Protocol):
    """The small fakeable surface used by :class:`AwsCliAdapter`."""

    def get_object(self, bucket: str, key: str) -> bytes: ...

    def put_object(
        self, bucket: str, key: str, payload: bytes, *, if_none_match: str
    ) -> Any: ...


class AwsCliAdapter:
    """AWS CLI adapter with an injectable transport for local regression tests.

    Construction is side-effect free.  The default transport invokes the AWS
    CLI only when a method is called; this module never authenticates or
    discovers credentials on import.
    """

    def __init__(
        self,
        *,
        region: str = "us-east-1",
        profile: str | None = None,
        transport: Any | None = None,
        runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
        timeout_seconds: int = 60,
        recovery_config: Mapping[str, str] | None = None,
    ) -> None:
        self.region = region
        self.profile = profile
        self.transport = transport
        self.runner = runner
        self.timeout_seconds = timeout_seconds
        self.recovery_config = dict(recovery_config or {})

    def _transport_call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        if self.transport is None:
            return _MISSING
        method = getattr(self.transport, name, None)
        if method is None:
            raise CloudManifestError(f"fake AWS transport lacks required method {name}")
        return method(*args, **kwargs)

    def _run(
        self, command: Sequence[str], *, allow_failure: bool = False
    ) -> subprocess.CompletedProcess[bytes]:
        argv = [
            "aws",
            *command,
            "--region",
            self.region,
            "--output",
            "json",
            "--no-cli-pager",
        ]
        if self.profile:
            argv.extend(["--profile", self.profile])
        result = self.runner(
            argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout_seconds,
        )
        if result.returncode != 0 and not allow_failure:
            detail = result.stderr.decode("utf-8", errors="replace")[-1000:]
            raise CloudManifestError(f"AWS CLI operation failed: {detail}")
        return result

    @staticmethod
    def _decode_json(result: subprocess.CompletedProcess[bytes]) -> Any:
        if not result.stdout.strip():
            return {}
        try:
            return json.loads(result.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CloudManifestError("AWS CLI returned non-JSON output") from exc

    def get_object(self, uri: str | S3ObjectRef) -> bytes:
        location = uri if isinstance(uri, S3ObjectRef) else parse_s3_uri(uri)
        transported = self._transport_call("get_object", location.bucket, location.key)
        if transported is not _MISSING:
            return _as_bytes(transported, label="get_object")

        with tempfile.TemporaryDirectory(prefix="pneuma-get-object-") as directory:
            destination = Path(directory) / "object"
            self._run(
                [
                    "s3api",
                    "get-object",
                    "--bucket",
                    location.bucket,
                    "--key",
                    location.key,
                    str(destination),
                ]
            )
            try:
                return destination.read_bytes()
            except OSError as exc:
                raise CloudManifestError(
                    f"AWS get-object did not materialize {location.uri}"
                ) from exc

    def put_object(
        self,
        uri: str | S3ObjectRef,
        payload: bytes,
        *,
        immutable: bool = True,
    ) -> None:
        location = uri if isinstance(uri, S3ObjectRef) else parse_s3_uri(uri)
        if not isinstance(payload, bytes) or not payload:
            raise CloudManifestError("published S3 objects must be nonempty bytes")
        if not immutable:
            raise CloudManifestError(
                "qualification artifacts must use immutable publication"
            )
        transported = self._transport_call(
            "put_object", location.bucket, location.key, payload, if_none_match="*"
        )
        if transported is not _MISSING:
            return

        with tempfile.TemporaryDirectory(prefix="pneuma-put-object-") as directory:
            source = Path(directory) / "object"
            source.write_bytes(payload)
            self._run(
                [
                    "s3api",
                    "put-object",
                    "--bucket",
                    location.bucket,
                    "--key",
                    location.key,
                    "--body",
                    str(source),
                    "--if-none-match",
                    "*",
                    "--server-side-encryption",
                    "AES256",
                ]
            )

    def submit_array_job(
        self,
        *,
        job_name: str,
        job_queue: str,
        job_definition: str,
        environment: Mapping[str, str],
        array_size: int = WORKER_COUNT,
    ) -> dict[str, Any]:
        """Submit the fixed probe without a command override.

        The image ENTRYPOINT receives the qualification code from its
        environment.  In particular this method never emits ``command: []``;
        an empty override is not equivalent to allowing Docker's fixed image
        entrypoint to run.
        """

        if array_size != WORKER_COUNT:
            raise CloudManifestError(
                "fixed admission requires exactly two array children"
            )
        if set(environment) - {
            QUALIFICATION_CODE_ENV,
            QUALIFICATION_ACTION_ID_ENV,
            "QUALIFICATION_ARTIFACT_PREFIX",
        }:
            raise CloudManifestError("unexpected qualification container environment")
        for name in (
            QUALIFICATION_CODE_ENV,
            QUALIFICATION_ACTION_ID_ENV,
            "QUALIFICATION_ARTIFACT_PREFIX",
        ):
            if not isinstance(environment.get(name), str) or not environment[name]:
                raise CloudManifestError(f"fixed admission requires nonempty {name}")
        transported = self._transport_call(
            "submit_array_job",
            job_name=job_name,
            job_queue=job_queue,
            job_definition=job_definition,
            environment=dict(environment),
            array_size=array_size,
        )
        if transported is not _MISSING:
            if not isinstance(transported, Mapping):
                raise CloudManifestError(
                    "submit_array_job transport response was not an object"
                )
            return dict(transported)

        overrides = {
            "environment": [
                {"name": key, "value": value}
                for key, value in sorted(environment.items())
            ]
        }
        return self._decode_json(
            self._run(
                [
                    "batch",
                    "submit-job",
                    "--job-name",
                    job_name,
                    "--job-queue",
                    job_queue,
                    "--job-definition",
                    job_definition,
                    "--array-properties",
                    json.dumps({"size": array_size}, separators=(",", ":")),
                    "--container-overrides",
                    json.dumps(overrides, separators=(",", ":")),
                ]
            )
        )

    def describe_jobs(self, job_ids: Sequence[str]) -> list[dict[str, Any]]:
        if not job_ids:
            raise CloudManifestError("describe_jobs requires at least one job id")
        transported = self._transport_call("describe_jobs", tuple(job_ids))
        if transported is not _MISSING:
            if isinstance(transported, Mapping):
                rows = transported.get("jobs")
            else:
                rows = transported
            if not isinstance(rows, list) or not all(
                isinstance(row, Mapping) for row in rows
            ):
                raise CloudManifestError(
                    "describe_jobs transport response was not a job list"
                )
            return [dict(row) for row in rows]
        output: list[dict[str, Any]] = []
        for start in range(0, len(job_ids), 100):
            response = self._decode_json(
                self._run(
                    ["batch", "describe-jobs", "--jobs", *job_ids[start : start + 100]]
                )
            )
            rows = response.get("jobs", [])
            if not isinstance(rows, list):
                raise CloudManifestError("AWS describe-jobs response omitted jobs")
            output.extend(row for row in rows if isinstance(row, Mapping))
        return [dict(row) for row in output]

    def get_caller_identity(self) -> dict[str, Any]:
        return self._read_provider(
            "get_caller_identity", ["sts", "get-caller-identity"]
        )

    def get_role(self, role_name: str) -> dict[str, Any]:
        return self._read_provider(
            "get_role",
            ["iam", "get-role", "--role-name", role_name],
            transport_args=(role_name,),
        )

    def get_instance_profile(self, profile_name: str) -> dict[str, Any]:
        return self._read_provider(
            "get_instance_profile",
            [
                "iam",
                "get-instance-profile",
                "--instance-profile-name",
                profile_name,
            ],
            transport_args=(profile_name,),
        )

    def describe_subnets(self, subnet_ids: Sequence[str]) -> list[dict[str, Any]]:
        return self._read_provider_list(
            "describe_subnets",
            ["ec2", "describe-subnets", "--subnet-ids", *subnet_ids],
            "Subnets",
            transport_args=(tuple(subnet_ids),),
        )

    def describe_security_groups(
        self, security_group_ids: Sequence[str]
    ) -> list[dict[str, Any]]:
        return self._read_provider_list(
            "describe_security_groups",
            ["ec2", "describe-security-groups", "--group-ids", *security_group_ids],
            "SecurityGroups",
            transport_args=(tuple(security_group_ids),),
        )

    def _read_provider(
        self,
        transport_name: str,
        command: Sequence[str],
        *,
        transport_args: Sequence[Any] = (),
    ) -> dict[str, Any]:
        transported = self._transport_call(transport_name, *transport_args)
        if transported is not _MISSING:
            if not isinstance(transported, Mapping):
                raise CloudManifestError(
                    f"{transport_name} transport response was not an object"
                )
            return dict(transported)
        response = self._decode_json(self._run(command))
        if not isinstance(response, Mapping):
            raise CloudManifestError(f"AWS {transport_name} response was not an object")
        return dict(response)

    def _read_provider_list(
        self,
        transport_name: str,
        command: Sequence[str],
        field: str,
        *,
        transport_args: Sequence[Any] = (),
    ) -> list[dict[str, Any]]:
        transported = self._transport_call(transport_name, *transport_args)
        if transported is not _MISSING:
            rows = (
                transported.get(field)
                if isinstance(transported, Mapping)
                else transported
            )
            if not isinstance(rows, list) or not all(
                isinstance(row, Mapping) for row in rows
            ):
                raise CloudManifestError(
                    f"{transport_name} transport response was not a list"
                )
            return [dict(row) for row in rows]
        response = self._decode_json(self._run(command))
        rows = response.get(field, []) if isinstance(response, Mapping) else []
        if not isinstance(rows, list):
            raise CloudManifestError(f"AWS {field} response was not a list")
        return [dict(row) for row in rows if isinstance(row, Mapping)]

    # The following methods form the explicit provider seam for the canonical
    # recovery drill.  Fakes implement them in local tests; the default path
    # uses only the explicitly supplied recovery names and the AWS CLI.
    def _recovery_value(self, name: str) -> str:
        value = self.recovery_config.get(name)
        if not isinstance(value, str) or not value:
            raise CloudManifestError(f"recovery configuration lacks {name}")
        return value

    def freeze(self, *, job_ids: Sequence[str], boundary: bytes) -> Mapping[str, Any]:
        result = self._transport_call(
            "freeze", job_ids=tuple(job_ids), boundary=boundary
        )
        if result is _MISSING:
            boundary_uri = self._recovery_value("boundary_uri")
            compute_environment = self._recovery_value("compute_environment")
            self.put_object(boundary_uri, boundary, immutable=True)
            self._run(
                [
                    "batch",
                    "update-compute-environment",
                    "--compute-environment",
                    compute_environment,
                    "--state",
                    "DISABLED",
                ]
            )
            for job_id in job_ids:
                observed = self.describe_jobs([job_id])
                status = observed[0].get("status") if observed else None
                if status not in {"SUCCEEDED", "FAILED"}:
                    self._run(
                        [
                            "batch",
                            "terminate-job",
                            "--job-id",
                            job_id,
                            "--reason",
                            "canonical qualification freeze",
                        ]
                    )
            return {"completed": True, "boundary": boundary}
        if not isinstance(result, Mapping):
            raise CloudManifestError("freeze transport response was not an object")
        return dict(result)

    def restore(self, *, job_ids: Sequence[str], boundary: bytes) -> Mapping[str, Any]:
        result = self._transport_call(
            "restore", job_ids=tuple(job_ids), boundary=boundary
        )
        if result is _MISSING:
            restored = self.get_object(self._recovery_value("boundary_uri"))
            if restored != boundary:
                raise CloudManifestError(
                    "restored interruption boundary differs from the frozen boundary"
                )
            if self.recovery_config.get("restore_compute_environment") == "true":
                self._run(
                    [
                        "batch",
                        "update-compute-environment",
                        "--compute-environment",
                        self._recovery_value("compute_environment"),
                        "--state",
                        "ENABLED",
                    ]
                )
            return {
                "completed": True,
                "boundary": restored,
                "all_arm_visible_bytes_match": True,
            }
        if not isinstance(result, Mapping):
            raise CloudManifestError("restore transport response was not an object")
        return dict(result)

    def list_tagged_resources(self, *, action_id: str) -> list[dict[str, Any]]:
        result = self._transport_call("list_tagged_resources", action_id=action_id)
        if result is _MISSING:
            filters = ["Name=tag:QualificationActionId,Values=" + action_id]
            instances_response = self._decode_json(
                self._run(["ec2", "describe-instances", "--filters", *filters])
            )
            resources: list[dict[str, Any]] = []
            for reservation in instances_response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    resources.append(
                        {
                            "resource_id": instance.get("InstanceId"),
                            "resource_type": "compute",
                            "state": (instance.get("State") or {}).get("Name"),
                        }
                    )
            volume_response = self._decode_json(
                self._run(["ec2", "describe-volumes", "--filters", *filters])
            )
            resources.extend(
                {
                    "resource_id": volume.get("VolumeId"),
                    "resource_type": "disk",
                    "state": volume.get("State"),
                }
                for volume in volume_response.get("Volumes", [])
            )
            return [
                row
                for row in resources
                if isinstance(row.get("resource_id"), str) and row["resource_id"]
            ]
        if not isinstance(result, list) or not all(
            isinstance(row, Mapping) for row in result
        ):
            raise CloudManifestError("tagged-resource readback was not a resource list")
        return [dict(row) for row in result]


_MISSING = object()


def _relative_destination(root: Path, relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path or "\\" in relative_path:
        raise CloudManifestError(
            "input relative_path must be a nonempty POSIX relative path"
        )
    candidate = root / relative_path
    resolved_root = root.resolve()
    try:
        candidate.resolve().relative_to(resolved_root)
    except ValueError as exc:
        raise CloudManifestError(
            "input relative_path escapes its materialization root"
        ) from exc
    return candidate


def _input_rows(artifacts: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for artifact in artifacts:
        uri = (
            artifact.get("s3_uri") or artifact.get("uri") or artifact.get("source_uri")
        )
        location = parse_s3_uri(uri)
        digest = artifact.get("sha256")
        size = artifact.get("size_bytes")
        relative = artifact.get("relative_path") or artifact.get("name")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise CloudManifestError(
                f"input {location.uri} lacks a lowercase SHA-256 digest"
            )
        if type(size) is not int or size < 0:
            raise CloudManifestError(
                f"input {location.uri} lacks a nonnegative byte size"
            )
        if not isinstance(relative, str):
            raise CloudManifestError(
                f"input {location.uri} lacks a local relative_path"
            )
        rows.append(
            {
                "s3_uri": location.uri,
                "sha256": digest,
                "size_bytes": size,
                "relative_path": relative,
            }
        )
    if not rows:
        raise CloudManifestError(
            "authenticated qualification requires at least one input"
        )
    if len({row["relative_path"] for row in rows}) != len(rows):
        raise CloudManifestError("authenticated inputs must have distinct local paths")
    return tuple(sorted(rows, key=lambda row: row["relative_path"]))


def input_manifest_digest(artifacts: Sequence[Mapping[str, Any]]) -> str:
    """Digest the exact object locations and expected bytes to be materialized."""

    return hashlib.sha256(canonical_bytes(_input_rows(artifacts))).hexdigest()


def verify_authenticated_input_authority(
    artifacts: Sequence[Mapping[str, Any]],
    *,
    authorization: Mapping[str, Any],
    lock: Mapping[str, Any],
    key_registry: Mapping[str, Any],
    ledger_path: Path,
) -> dict[str, Any]:
    """Require signed input, lock, manifest, and spend-history bindings.

    The spend digest is always derived from the current ledger bytes.  A
    caller-provided ``spend_history_ok`` flag or digest is never treated as
    proof; the digest carried by the signed authorization must equal the
    freshly derived authority value.
    """

    rows = _input_rows(artifacts)
    if authorization.get("record_kind") != "cloud_retrieval_authorization":
        raise CloudManifestError(
            "qualification inputs require an authenticated retrieval authorization"
        )
    verified = require_authorized(
        authorization,
        lock,
        key_registry=key_registry,
        ledger_path=ledger_path,
    )
    if verified.get("input_manifest_sha256") != input_manifest_digest(rows):
        raise CloudManifestError(
            "retrieval authorization does not bind the exact qualification input manifest"
        )
    observed_spend = canonical_ledger_digest(ledger_path)
    if verified.get("spend_history_sha256") != observed_spend:
        raise CloudManifestError(
            "retrieval authorization does not bind the current spend history"
        )
    return verified


def materialize_authenticated_inputs(
    artifacts: Sequence[Mapping[str, Any]],
    *,
    destination: Path,
    adapter: AwsCliAdapter,
    authorization: Mapping[str, Any],
    lock: Mapping[str, Any],
    key_registry: Mapping[str, Any],
    ledger_path: Path,
) -> dict[str, Path]:
    """Download and verify all authorized inputs before a probe can start."""

    rows = _input_rows(artifacts)
    verify_authenticated_input_authority(
        rows,
        authorization=authorization,
        lock=lock,
        key_registry=key_registry,
        ledger_path=ledger_path,
    )
    destination.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".qualification-inputs-", dir=destination))
    installed: dict[str, Path] = {}
    try:
        for row in rows:
            target = _relative_destination(destination, row["relative_path"])
            if target.exists() or target.is_symlink():
                raise CloudManifestError(
                    f"materialization target is already occupied: {row['relative_path']}"
                )
            staged = staging / row["relative_path"]
            staged.parent.mkdir(parents=True, exist_ok=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = adapter.get_object(row["s3_uri"])
            if len(payload) != row["size_bytes"]:
                raise CloudManifestError(
                    f"materialized input size mismatch for {row['relative_path']}"
                )
            digest = hashlib.sha256(payload).hexdigest()
            if digest != row["sha256"]:
                raise CloudManifestError(
                    f"materialized input digest mismatch for {row['relative_path']}"
                )
            staged.write_bytes(payload)
            os.replace(staged, target)
            if not target.is_file() or target.stat().st_size != row["size_bytes"]:
                raise CloudManifestError(
                    f"materialized input is not a readable file: {row['relative_path']}"
                )
            installed[row["relative_path"]] = target
        if set(installed) != {row["relative_path"] for row in rows}:
            raise CloudManifestError("not all authorized inputs were materialized")
        return installed
    except Exception:
        for path in installed.values():
            path.unlink(missing_ok=True)
        raise
    finally:
        for path in sorted(staging.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                path.rmdir()
        staging.rmdir()


def worker_artifact_uri(artifact_prefix: str, worker_index: int) -> str:
    """Return the immutable raw-measurement location for one array child."""

    if worker_index not in range(WORKER_COUNT):
        raise CloudManifestError("worker index must be 0 or 1")
    trimmed = artifact_prefix.rstrip("/")
    if not trimmed:
        raise CloudManifestError(
            "qualification artifact prefix must name a nonempty S3 prefix"
        )
    prefix = parse_s3_uri(trimmed + "/marker")
    parent = prefix.key.rsplit("/", 1)[0]
    return f"s3://{prefix.bucket}/{parent}/worker-{worker_index}/{RAW_MEASUREMENT_NAME}"


def publish_raw_measurement(
    adapter: AwsCliAdapter,
    *,
    artifact_prefix: str,
    worker_index: int,
    raw_bytes: bytes,
) -> dict[str, str | int]:
    """Publish one raw measurement once, under a worker-specific S3 key."""

    if not isinstance(raw_bytes, bytes) or not raw_bytes:
        raise CloudManifestError("raw worker measurement must be nonempty bytes")
    try:
        parsed = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudManifestError("raw worker measurement must be UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping) or parsed.get("worker_index") != worker_index:
        raise CloudManifestError(
            "raw measurement worker index does not match its publication slot"
        )
    validate_worker_admission_measurement(parsed)
    uri = worker_artifact_uri(artifact_prefix, worker_index)
    adapter.put_object(uri, raw_bytes, immutable=True)
    return {
        "worker_index": worker_index,
        "uri": uri,
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "size_bytes": len(raw_bytes),
    }


def retrieve_raw_measurement(
    adapter: AwsCliAdapter,
    *,
    artifact_prefix: str,
    worker_index: int,
    expected_sha256: str | None = None,
) -> bytes:
    uri = worker_artifact_uri(artifact_prefix, worker_index)
    payload = adapter.get_object(uri)
    if not payload:
        raise CloudManifestError(f"raw measurement is empty at {uri}")
    observed = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and observed != expected_sha256:
        raise CloudManifestError(f"raw measurement digest mismatch at {uri}")
    try:
        record = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudManifestError(f"raw measurement at {uri} is not JSON") from exc
    if not isinstance(record, Mapping) or record.get("worker_index") != worker_index:
        raise CloudManifestError(
            f"raw measurement at {uri} is bound to the wrong worker"
        )
    validate_worker_admission_measurement(record)
    return payload


def require_two_succeeded_children(
    jobs: Sequence[Mapping[str, Any]],
    *,
    parent_status: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Accept only array children 0 and 1 with one successful attempt each."""

    if parent_status != "SUCCEEDED":
        raise CloudManifestError("fixed admission requires a succeeded array parent")
    if len(jobs) != WORKER_COUNT:
        raise CloudManifestError("fixed admission requires exactly two array children")
    normalized: dict[int, dict[str, Any]] = {}
    for job in jobs:
        array = job.get("arrayProperties") or {}
        index = array.get("index")
        job_id = job.get("jobId")
        attempts = job.get("attempts")
        if type(index) is not int or index not in range(WORKER_COUNT):
            raise CloudManifestError("fixed admission child index is not 0 or 1")
        if not isinstance(job_id, str) or not job_id:
            raise CloudManifestError("fixed admission child has no job id")
        if job.get("status") != "SUCCEEDED":
            raise CloudManifestError(
                "both fixed admission children must have status SUCCEEDED"
            )
        if not isinstance(attempts, list) or len(attempts) != 1:
            raise CloudManifestError(
                "each fixed admission child must have exactly one attempt"
            )
        if index in normalized:
            raise CloudManifestError("fixed admission repeats an array child index")
        normalized[index] = {
            "job_id": job_id,
            "index": index,
            "status": job["status"],
            "attempt_count": len(attempts),
        }
    if (
        set(normalized) != set(range(WORKER_COUNT))
        or len({row["job_id"] for row in normalized.values()}) != WORKER_COUNT
    ):
        raise CloudManifestError(
            "fixed admission does not contain two distinct array children"
        )
    return normalized[0], normalized[1]


def require_array_evidence(
    adapter: AwsCliAdapter,
    *,
    parent_job_id: str,
    child_job_ids: Sequence[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch and accept only one successful parent plus both child records."""

    if not isinstance(parent_job_id, str) or not parent_job_id:
        raise CloudManifestError("array evidence requires a parent job id")
    if len(child_job_ids) != WORKER_COUNT or len(set(child_job_ids)) != WORKER_COUNT:
        raise CloudManifestError("array evidence requires two distinct child job ids")
    requested = [parent_job_id, *child_job_ids]
    rows = adapter.describe_jobs(requested)
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        job_id = row.get("jobId")
        if not isinstance(job_id, str) or job_id in by_id:
            raise CloudManifestError(
                "array evidence must contain each requested job exactly once"
            )
        by_id[job_id] = dict(row)
    if set(by_id) != set(requested):
        raise CloudManifestError(
            "array evidence is missing the parent or an array child"
        )
    parent = by_id[parent_job_id]
    return require_two_succeeded_children(
        [by_id[child_job_id] for child_job_id in child_job_ids],
        parent_status=parent.get("status"),
    )


# Short aliases keep the execution seam discoverable to small launchers while
# retaining the deliberately explicit function names above for callers that
# need to distinguish materialization from ordinary local file handling.
materialize_inputs = materialize_authenticated_inputs
publish_worker_measurement = publish_raw_measurement
retrieve_worker_measurement = retrieve_raw_measurement
collect_array_evidence = require_array_evidence


def derive_spend_history_binding(ledger_path: Path) -> str:
    """Derive the spend binding from the authoritative ledger bytes."""

    return canonical_ledger_digest(ledger_path)


def verify_spend_history_binding(
    authority: Mapping[str, Any], ledger_path: Path
) -> str:
    """Verify an authority's spend digest against the real ledger source."""

    observed = derive_spend_history_binding(ledger_path)
    if authority.get("spend_history_sha256") != observed:
        raise CloudManifestError(
            "authority spend-history binding differs from the current ledger"
        )
    return observed


def _json_object(value: Any, *, field: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise CloudManifestError(f"Terraform {field} is not JSON") from exc
        if isinstance(parsed, Mapping):
            return dict(parsed)
    raise CloudManifestError(f"Terraform {field} is not an object")


def _resource_rows(document: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}

    def walk(module: Mapping[str, Any]) -> None:
        for row in (
            module.get("resources", [])
            if isinstance(module.get("resources", []), list)
            else []
        ):
            if (
                isinstance(row, Mapping)
                and isinstance(row.get("address"), str)
                and isinstance(row.get("values"), Mapping)
            ):
                rows[row["address"]] = dict(row["values"])
        children = module.get("child_modules", [])
        if isinstance(children, list):
            for child in children:
                if isinstance(child, Mapping):
                    walk(child)

    planned = document.get("planned_values")
    if isinstance(planned, Mapping) and isinstance(planned.get("root_module"), Mapping):
        walk(planned["root_module"])
    changes = document.get("resource_changes", [])
    if isinstance(changes, list):
        for change in changes:
            if not isinstance(change, Mapping) or not isinstance(
                change.get("address"), str
            ):
                continue
            payload = change.get("change")
            if isinstance(payload, Mapping) and isinstance(
                payload.get("after"), Mapping
            ):
                rows.setdefault(change["address"], dict(payload["after"]))
    return rows


def _resource(
    rows: Mapping[str, Mapping[str, Any]], base_address: str
) -> dict[str, Any]:
    exact = rows.get(base_address)
    if exact is not None:
        return dict(exact)
    matches = [
        values
        for address, values in rows.items()
        if address.startswith(base_address + "[")
    ]
    if len(matches) != 1:
        raise CloudManifestError(
            f"Terraform show is missing an unambiguous resource {base_address}"
        )
    return dict(matches[0])


def _resource_any(
    rows: Mapping[str, Mapping[str, Any]], *base_addresses: str
) -> dict[str, Any]:
    for address in base_addresses:
        try:
            return _resource(rows, address)
        except CloudManifestError:
            continue
    joined = ", ".join(base_addresses)
    raise CloudManifestError(
        f"Terraform show is missing an unambiguous resource ({joined})"
    )


def _tag_maps(value: Mapping[str, Any]) -> list[dict[str, str]]:
    maps: list[dict[str, str]] = []
    for candidate in (value.get("tags"), value.get("tags_all")):
        if isinstance(candidate, Mapping):
            maps.append({str(key): str(item) for key, item in candidate.items()})
    return maps


def _iam_binding_name(value: Any, *, kind: str, field: str) -> str:
    """Return the simple IAM name from one planned ARN.

    The qualification variables contain ARNs, but Batch's ``instance_role``
    field is specifically an instance-profile ARN.  Keeping the ARN kind
    explicit here prevents a role ARN from being accidentally passed to
    ``get-instance-profile`` (or vice versa).
    """

    if not isinstance(value, str) or not value:
        raise CloudManifestError(f"planned {field} lacks a concrete ARN")
    parts = value.split(":", 5)
    if (
        len(parts) != 6
        or parts[0] != "arn"
        or parts[1] != "aws"
        or parts[2] != "iam"
        or not parts[4].isdigit()
        or len(parts[4]) != 12
        or parts[5].count("/") != 1
        or not parts[5].startswith(f"{kind}/")
        or not parts[5].split("/", 1)[1]
    ):
        raise CloudManifestError(
            f"planned {field} must be an AWS IAM {kind} ARN"
        )
    return parts[5].split("/", 1)[1]


def parse_terraform_show(document: Mapping[str, Any]) -> dict[str, Any]:
    """Parse actual ``terraform show -json`` values into a qualification plan.

    This intentionally does not accept a hand-written account-plan dictionary.
    Every binding below comes from Terraform's ``variables``,
    ``planned_values`` or ``resource_changes`` objects.
    """

    if not isinstance(document, Mapping) or not isinstance(
        document.get("format_version"), str
    ):
        raise CloudManifestError("Terraform show JSON lacks format_version")
    variables = document.get("variables")
    if not isinstance(variables, Mapping):
        raise CloudManifestError("Terraform show JSON lacks its variables object")

    def variable(*names: str) -> Any:
        values: list[Any] = []
        for name in names:
            row = variables.get(name)
            if isinstance(row, Mapping) and "value" in row:
                values.append(row["value"])
        if len({json.dumps(value, sort_keys=True) for value in values}) > 1:
            raise CloudManifestError(
                f"Terraform variables disagree for {', '.join(names)}"
            )
        return values[0] if values else None

    code = variable("qualification_code", "QUALIFICATION_CODE")
    action_id = variable(
        "qualification_action_id", "action_id", "QUALIFICATION_ACTION_ID"
    )
    if not isinstance(code, str) or not code:
        raise CloudManifestError(
            "Terraform planned variables do not contain qualification_code"
        )
    if not isinstance(action_id, str) or not action_id:
        raise CloudManifestError(
            "Terraform planned variables do not contain a qualification action id"
        )

    rows = _resource_rows(document)
    changes = document.get("resource_changes")
    if not isinstance(changes, list):
        raise CloudManifestError("Terraform show JSON lacks resource_changes")
    qualification_addresses = (
        "aws_batch_compute_environment.worker",
        "aws_batch_compute_environment.qualification",
        "aws_batch_job_definition.gpu_worker",
        "aws_batch_job_definition.worker",
        "aws_launch_template.worker",
        "aws_launch_template.qualification",
    )
    for change in changes:
        if not isinstance(change, Mapping):
            raise CloudManifestError("Terraform resource_changes contains a non-object")
        address = change.get("address")
        if not isinstance(address, str):
            raise CloudManifestError(
                "Terraform resource_changes contains an addressless resource"
            )
        if address.startswith(qualification_addresses) and isinstance(
            change.get("change"), Mapping
        ):
            actions = change["change"].get("actions")
            if actions not in (None, ["create"], ["update"]):
                raise CloudManifestError(
                    f"qualification resource {address} has a destructive plan action"
                )
    compute = _resource_any(
        rows,
        "aws_batch_compute_environment.worker",
        "aws_batch_compute_environment.qualification",
    )
    job_definition = _resource_any(
        rows,
        "aws_batch_job_definition.gpu_worker",
        "aws_batch_job_definition.worker",
    )
    container = _json_object(
        job_definition.get("container_properties"), field="container_properties"
    )
    image = variable("gpu_worker_image")
    if not isinstance(image, str) or not QUALIFICATION_IMAGE_DIGEST_RE.search(image):
        raise CloudManifestError(
            "planned qualification image must be an immutable sha256 digest"
        )
    if container.get("image") != image:
        raise CloudManifestError(
            "planned job definition image differs from the pinned Terraform image"
        )
    environment = container.get("environment")
    if not isinstance(environment, list):
        raise CloudManifestError("planned job definition has no environment list")
    environment_values: dict[str, Any] = {}
    for item in environment:
        if not isinstance(item, Mapping) or not isinstance(item.get("name"), str):
            raise CloudManifestError("planned job definition has an invalid environment entry")
        name = item["name"]
        if name in environment_values:
            raise CloudManifestError(f"planned job definition repeats {name}")
        environment_values[name] = item.get("value")
    if (
        sum(
            item.get("name") == QUALIFICATION_CODE_ENV
            for item in environment
            if isinstance(item, Mapping)
        )
        != 1
    ):
        raise CloudManifestError(
            "planned job definition must contain exactly one QUALIFICATION_CODE"
        )
    if (
        sum(
            item.get("name") == QUALIFICATION_ACTION_ID_ENV
            for item in environment
            if isinstance(item, Mapping)
        )
        != 1
    ):
        raise CloudManifestError(
            "planned job definition must contain exactly one QUALIFICATION_ACTION_ID"
        )
    if environment_values.get(QUALIFICATION_CODE_ENV) != code:
        raise CloudManifestError(
            "planned QUALIFICATION_CODE differs from the Terraform variable"
        )
    if environment_values.get(QUALIFICATION_ACTION_ID_ENV) != action_id:
        raise CloudManifestError(
            "planned qualification action id differs from the Terraform variable"
        )
    output_path = variable("output_path")
    input_paths = {
        "protocol": variable("protocol_path"),
        "architecture": variable("architecture_path"),
        "authorization": variable("authorization_path"),
        "image": variable("image_path"),
        "input_lock": variable("input_lock_path"),
    }
    if not isinstance(output_path, str):
        raise CloudManifestError("planned qualification output path is not concrete")
    input_prefix = output_path.rstrip("/").rsplit("/", 1)[0] + "/inputs"
    for name, value in input_paths.items():
        expected_path = f"{input_prefix}/{name.replace('_', '-')}.json"
        if value != expected_path:
            raise CloudManifestError(
                f"planned qualification {name} input is not action-scoped"
            )
    expected_environment = {
        "QUALIFICATION_CODE": code,
        "QUALIFICATION_ACTION_ID": action_id,
        "QUALIFICATION_ARTIFACT_PREFIX": output_path,
        "QUALIFICATION_MODEL": variable("qualification_model"),
        "QUALIFICATION_MODEL_REVISION": variable("qualification_model_revision"),
        "QUALIFICATION_PROTOCOL": input_paths["protocol"],
        "QUALIFICATION_ARCHITECTURE": input_paths["architecture"],
        "QUALIFICATION_AUTHORIZATION": input_paths["authorization"],
        "QUALIFICATION_IMAGE": input_paths["image"],
        "QUALIFICATION_INPUT_LOCK": input_paths["input_lock"],
        "QUALIFICATION_OUTPUT_ROOT": output_path,
    }
    if expected_environment["QUALIFICATION_MODEL"] != QUALIFICATION_FIXTURE_MODEL:
        raise CloudManifestError(
            "planned qualification must bind the non-model CUDA fixture"
        )
    if (
        expected_environment["QUALIFICATION_MODEL_REVISION"]
        != QUALIFICATION_FIXTURE_REVISION
    ):
        raise CloudManifestError(
            "planned qualification must bind the registered fixture revision"
        )
    if (
            not output_path.startswith("s3://")
        or not output_path.rstrip("/").endswith(f"/{action_id}/outputs")
    ):
        raise CloudManifestError(
            "planned qualification output path must be an action-scoped S3 output prefix"
        )
    if environment_values != expected_environment:
        raise CloudManifestError(
            "planned qualification environment does not exactly match its Terraform bindings"
        )
    if "command" in container:
        raise CloudManifestError(
            "planned fixed qualification image must inherit its ENTRYPOINT"
        )
    resource_requirements = container.get("resourceRequirements")
    if not isinstance(resource_requirements, list) or len(resource_requirements) != 3:
        raise CloudManifestError(
            "planned job definition must request exactly one GPU, 8 vCPUs, and 60000 MiB"
        )
    observed_requirements = {
        (item.get("type"), item.get("value"))
        for item in resource_requirements
        if isinstance(item, Mapping)
    }
    if observed_requirements != QUALIFICATION_RESOURCE_REQUIREMENTS:
        raise CloudManifestError(
            "planned job definition resource requirements differ from the fixed worker contract"
        )
    if job_definition.get("platform_capabilities") not in (None, ["EC2"]):
        raise CloudManifestError("planned qualification job is not EC2-only")
    timeout = job_definition.get("timeout")
    if timeout != [{"attempt_duration_seconds": 3600}]:
        raise CloudManifestError(
            "planned qualification job must have a 3600-second attempt timeout"
        )
    retry_strategy = job_definition.get("retry_strategy")
    if (
        not isinstance(retry_strategy, list)
        or len(retry_strategy) != 1
        or not isinstance(retry_strategy[0], Mapping)
        or retry_strategy[0].get("attempts") != 1
        or retry_strategy[0].get("evaluate_on_exit") not in (None, [])
    ):
        raise CloudManifestError(
            "planned qualification job must have exactly one attempt"
        )

    compute_resources = compute.get("compute_resources")
    if (
        not isinstance(compute_resources, list)
        or len(compute_resources) != 1
        or not isinstance(compute_resources[0], Mapping)
    ):
        raise CloudManifestError(
            "planned compute environment has no unambiguous compute_resources block"
        )
    resources = dict(compute_resources[0])
    if resources.get("type") != "SPOT":
        raise CloudManifestError("planned compute environment must use Spot capacity")
    if resources.get("allocation_strategy") != "SPOT_PRICE_CAPACITY_OPTIMIZED":
        raise CloudManifestError(
            "planned compute environment must use Spot price-capacity optimization"
        )
    if resources.get("min_vcpus") != 0 or resources.get("desired_vcpus") != 0:
        raise CloudManifestError(
            "planned compute environment must start with zero requested vCPUs"
        )
    tags: dict[str, str] = {}
    for tag_map in _tag_maps(compute) + _tag_maps(resources):
        tags.update(tag_map)
    if tags.get("QualificationCode") != code:
        raise CloudManifestError(
            "planned compute resources do not carry the qualification code tag"
        )
    if tags.get("QualificationActionId") != action_id:
        raise CloudManifestError(
            "planned compute resources do not carry the qualification action id tag"
        )
    launch_template = _resource_any(
        rows,
        "aws_launch_template.worker",
        "aws_launch_template.qualification",
    )
    tag_specifications = launch_template.get("tag_specifications")
    if not isinstance(tag_specifications, list):
        raise CloudManifestError(
            "planned worker launch template has no tag specifications"
        )
    for resource_type in ("instance", "volume"):
        matching = [
            item
            for item in tag_specifications
            if isinstance(item, Mapping) and item.get("resource_type") == resource_type
        ]
        if len(matching) != 1 or not isinstance(matching[0].get("tags"), Mapping):
            raise CloudManifestError(
                f"planned worker launch template lacks {resource_type} qualification tags"
            )
        launch_tags = matching[0]["tags"]
        if (
            launch_tags.get("QualificationCode") != code
            or launch_tags.get("QualificationActionId") != action_id
        ):
            raise CloudManifestError(
                f"planned {resource_type} tags do not bind the qualification action"
            )
    subnets = resources.get("subnets") or variable("subnet_ids")
    security_groups = resources.get("security_group_ids") or variable(
        "security_group_ids"
    )
    if (
        not isinstance(subnets, list)
        or len(subnets) != len(QUALIFICATION_AZS)
        or not all(isinstance(item, str) and item for item in subnets)
        or len(set(subnets)) != len(QUALIFICATION_AZS)
    ):
        raise CloudManifestError(
            "planned compute resources do not contain concrete subnet ids"
        )
    if (
        not isinstance(security_groups, list)
        or len(security_groups) != 1
        or not all(isinstance(item, str) and item for item in security_groups)
    ):
        raise CloudManifestError(
            "planned compute resources do not contain concrete security-group ids"
        )

    instance_types = resources.get("instance_type")
    if instance_types != ["g6e.2xlarge"]:
        raise CloudManifestError(
            "planned compute resources are not the pinned one-GPU worker type"
        )
    if resources.get("max_vcpus") != 16:
        raise CloudManifestError(
            "planned compute resources do not preserve the 16-vCPU ceiling"
        )
    if launch_template.get("image_id") not in (None, ""):
        raise CloudManifestError(
            "qualification launch template must use the Batch-managed GPU AMI path"
        )
    queue = _resource_any(rows, "aws_batch_job_queue.qualification")
    for label, row in (
        ("job queue", queue),
        ("job definition", job_definition),
    ):
        row_tags = _tag_maps(row)
        if not any(
            tags.get("QualificationCode") == code
            and tags.get("QualificationActionId") == action_id
            for tags in row_tags
        ):
            raise CloudManifestError(
                f"planned {label} tags do not bind the qualification action"
            )

    instance_profile_arn = variable("instance_role_arn")
    instance_profile_name = _iam_binding_name(
        instance_profile_arn,
        kind="instance-profile",
        field="worker instance profile",
    )
    planned_instance_role = resources.get("instance_role")
    if planned_instance_role != instance_profile_arn:
        raise CloudManifestError(
            "planned Batch instance_role does not equal the Terraform instance-profile ARN"
        )

    batch_service_role_arn = variable("batch_service_role_arn")
    batch_service_role_name = _iam_binding_name(
        batch_service_role_arn,
        kind="role",
        field="Batch service role",
    )
    planned_service_role = compute.get("service_role")
    if planned_service_role != batch_service_role_arn:
        raise CloudManifestError(
            "planned Batch service_role does not equal its Terraform role ARN"
        )

    spot_fleet_role_arn = variable("spot_fleet_role_arn")
    planned_spot_role = resources.get("spot_iam_fleet_role")
    if spot_fleet_role_arn is None:
        spot_fleet_role_name = None
        if planned_spot_role is not None:
            raise CloudManifestError(
                "planned spot_iam_fleet_role is not absent while its Terraform variable is null"
            )
    else:
        spot_fleet_role_name = _iam_binding_name(
            spot_fleet_role_arn,
            kind="role",
            field="Spot fleet role",
        )
    if spot_fleet_role_arn is not None and planned_spot_role != spot_fleet_role_arn:
        raise CloudManifestError(
            "planned spot_iam_fleet_role does not equal its Terraform role ARN"
        )

    # A qualification stack normally references an existing profile and does
    # not create its role.  If a role resource is present, retain its planned
    # identity as an additional exact constraint on the profile's one
    # attached role; never treat the profile ARN itself as that role.
    try:
        worker_role = _resource_any(rows, "aws_iam_role.worker")
    except CloudManifestError:
        planned_worker_role_name = None
        planned_worker_role_arn = None
    else:
        planned_worker_role_name = worker_role.get("name")
        if not isinstance(planned_worker_role_name, str) or not planned_worker_role_name:
            raise CloudManifestError("planned worker IAM role lacks a concrete name")
        planned_worker_role_arn = worker_role.get("arn")
        if planned_worker_role_arn is not None:
            _iam_binding_name(
                planned_worker_role_arn,
                kind="role",
                field="planned worker role",
            )
    vpc_id = variable("vpc_id")
    region = variable("region")
    show_document = {
        key: value
        for key, value in document.items()
        if key not in _TERRAFORM_RUNNER_METADATA_KEYS
    }
    return {
        "action_id": action_id,
        "qualification_code": code,
        "worker_instance_profile_name": instance_profile_name,
        "worker_instance_profile_arn": instance_profile_arn,
        "worker_role_name": planned_worker_role_name,
        "worker_role_arn": planned_worker_role_arn,
        "batch_service_role_name": batch_service_role_name,
        "batch_service_role_arn": batch_service_role_arn,
        "spot_fleet_role_name": spot_fleet_role_name,
        "spot_fleet_role_arn": spot_fleet_role_arn,
        "subnet_ids": tuple(subnets),
        "security_group_ids": tuple(security_groups),
        "vpc_id": vpc_id if isinstance(vpc_id, str) and vpc_id else None,
        "region": region if isinstance(region, str) and region else None,
        "compute_resources": resources,
        "job_definition": container,
        "image": image,
        "output_path": output_path,
        "input_paths": input_paths,
        "compute_environment_name": compute.get("compute_environment_name"),
        "job_queue_name": queue.get("name"),
        "job_definition_name": job_definition.get("name"),
        "terraform_show_sha256": hashlib.sha256(
            canonical_bytes(show_document)
        ).hexdigest(),
    }


def parse_terraform_show_json(
    payload: bytes | str | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(payload, Mapping):
        return parse_terraform_show(payload)
    raw_payload: bytes
    if isinstance(payload, bytes):
        raw_payload = payload
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CloudManifestError("Terraform show JSON is not UTF-8") from exc
    elif isinstance(payload, str):
        raw_payload = payload.encode("utf-8")
    else:
        raise CloudManifestError("Terraform show output is not JSON")
    try:
        document = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise CloudManifestError("Terraform show output is not JSON") from exc
    if not isinstance(document, Mapping):
        raise CloudManifestError("Terraform show output is not an object")
    parsed = parse_terraform_show(document)
    # The runner consumes the provider's exact stdout bytes.  Preserve that
    # byte-level digest instead of silently replacing it with a canonicalized
    # re-serialization of the JSON document.
    parsed["terraform_show_sha256"] = hashlib.sha256(raw_payload).hexdigest()
    return parsed


def verify_provider_bindings(
    adapter: AwsCliAdapter, plan: Mapping[str, Any]
) -> dict[str, Any]:
    """Perform explicit read-only existence checks for the planned bindings."""

    identity = adapter.get_caller_identity()
    account_id = identity.get("Account")
    if (
        not isinstance(account_id, str)
        or not account_id.isdigit()
        or len(account_id) != 12
    ):
        raise CloudManifestError("provider identity did not return a concrete account")
    planned_region = plan.get("region")
    provider_region = getattr(adapter, "region", None)
    if planned_region is not None and provider_region is not None and planned_region != provider_region:
        raise CloudManifestError("provider region differs from the Terraform plan")

    def account_arn(value: Any, *, kind: str, label: str) -> str:
        name = _iam_binding_name(value, kind=kind, field=label)
        assert isinstance(value, str)
        if value.split(":", 5)[4] != account_id:
            raise CloudManifestError(f"{label} ARN belongs to a different account")
        return name

    profile_arn = plan.get("worker_instance_profile_arn")
    profile_name = plan.get("worker_instance_profile_name")
    expected_profile_name = account_arn(
        profile_arn,
        kind="instance-profile",
        label="planned worker instance profile",
    )
    if profile_name != expected_profile_name:
        raise CloudManifestError(
            "planned worker instance-profile name differs from its ARN"
        )
    profile_response = adapter.get_instance_profile(expected_profile_name)
    profile = (
        profile_response.get("InstanceProfile")
        if isinstance(profile_response, Mapping)
        else None
    )
    if not isinstance(profile, Mapping):
        raise CloudManifestError(
            "planned worker instance profile was not explicitly verified"
        )
    if profile.get("InstanceProfileName") != expected_profile_name:
        raise CloudManifestError(
            "provider instance-profile name differs from the Terraform plan"
        )
    if profile.get("Arn") != profile_arn:
        raise CloudManifestError(
            "provider instance-profile ARN differs from the Terraform plan"
        )
    attached_roles = profile.get("Roles")
    if not isinstance(attached_roles, list) or len(attached_roles) != 1:
        raise CloudManifestError(
            "worker instance profile must have exactly one attached role"
        )
    attached = attached_roles[0]
    if not isinstance(attached, Mapping):
        raise CloudManifestError("worker instance profile has an invalid attached role")
    attached_role_name = attached.get("RoleName")
    attached_role_arn = attached.get("Arn")
    account_arn(
        attached_role_arn,
        kind="role",
        label="attached worker role",
    )
    if not isinstance(attached_role_name, str) or not attached_role_name:
        raise CloudManifestError("worker instance profile has no attached role name")
    expected_worker_role_name = plan.get("worker_role_name")
    expected_worker_role_arn = plan.get("worker_role_arn")
    if (
        expected_worker_role_name is not None
        and attached_role_name != expected_worker_role_name
    ):
        raise CloudManifestError(
            "attached worker role name differs from the planned role"
        )
    if expected_worker_role_arn is not None and attached_role_arn != expected_worker_role_arn:
        raise CloudManifestError("attached worker role ARN differs from the planned role")
    role_response = adapter.get_role(attached_role_name)
    role = role_response.get("Role") if isinstance(role_response, Mapping) else None
    if not isinstance(role, Mapping):
        raise CloudManifestError("attached worker role was not explicitly verified")
    if role.get("RoleName") != attached_role_name or role.get("Arn") != attached_role_arn:
        raise CloudManifestError(
            "iam get-role does not match the role attached to the instance profile"
        )

    def verify_role_binding(arn: Any, name: Any, label: str) -> dict[str, Any]:
        expected_name = account_arn(arn, kind="role", label=label)
        if name != expected_name:
            raise CloudManifestError(f"planned {label} name differs from its ARN")
        response = adapter.get_role(expected_name)
        observed = response.get("Role") if isinstance(response, Mapping) else None
        if not isinstance(observed, Mapping):
            raise CloudManifestError(f"planned {label} was not explicitly verified")
        if observed.get("RoleName") != expected_name or observed.get("Arn") != arn:
            raise CloudManifestError(f"provider {label} ARN differs from the Terraform plan")
        return dict(observed)

    service_role = verify_role_binding(
        plan.get("batch_service_role_arn"),
        plan.get("batch_service_role_name"),
        "Batch service role",
    )
    spot_arn = plan.get("spot_fleet_role_arn")
    spot_role = (
        verify_role_binding(
            spot_arn,
            plan.get("spot_fleet_role_name"),
            "Spot fleet role",
        )
        if spot_arn is not None
        else None
    )
    subnets = adapter.describe_subnets(tuple(plan["subnet_ids"]))
    if len(plan["subnet_ids"]) != len(QUALIFICATION_AZS) or len(subnets) != len(QUALIFICATION_AZS):
        raise CloudManifestError("qualification must use exactly four subnets")
    if {row.get("SubnetId") for row in subnets} != set(plan["subnet_ids"]):
        raise CloudManifestError("planned subnet ids were not explicitly verified")
    observed_azs = {row.get("AvailabilityZone") for row in subnets}
    if observed_azs != set(QUALIFICATION_AZS):
        raise CloudManifestError(
            "verified subnets do not cover us-east-1a through us-east-1d"
        )
    if any(row.get("State") != "available" for row in subnets):
        raise CloudManifestError("a planned qualification subnet is not available")
    subnet_vpcs = {row.get("VpcId") for row in subnets}
    if len(subnet_vpcs) != 1 or None in subnet_vpcs:
        raise CloudManifestError("verified qualification subnets do not share one VPC")
    observed_vpc = next(iter(subnet_vpcs))
    if plan.get("vpc_id") is not None and observed_vpc != plan["vpc_id"]:
        raise CloudManifestError("verified subnet VPC differs from the Terraform plan")
    groups = adapter.describe_security_groups(tuple(plan["security_group_ids"]))
    if len(plan["security_group_ids"]) != 1 or len(groups) != 1:
        raise CloudManifestError("qualification must use exactly one security group")
    if {row.get("GroupId") for row in groups} != set(plan["security_group_ids"]):
        raise CloudManifestError(
            "planned security-group ids were not explicitly verified"
        )
    group_vpcs = {row.get("VpcId") for row in groups}
    if group_vpcs != {observed_vpc}:
        raise CloudManifestError(
            "verified security-group VPC differs from the verified subnet VPC"
        )
    if any(
        not isinstance(group.get("IpPermissions"), list)
        or group.get("IpPermissions")
        for group in groups
    ):
        raise CloudManifestError("qualification security group must have zero ingress")
    return {
        "account_id": account_id,
        "role": dict(role),
        "roles": [dict(role), service_role, *([spot_role] if spot_role else [])],
        "instance_profile": dict(profile),
        "vpc_id": observed_vpc,
        "service_role": service_role,
        "spot_fleet_role": spot_role,
        "subnets": subnets,
        "security_groups": groups,
    }

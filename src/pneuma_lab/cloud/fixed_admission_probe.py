"""Fixed image adapter and provider-free contracts for admission workers.

The image entrypoint supplies ``--code`` from the signed Terraform
environment.  Before the GPU probe is imported, every declared input is
materialized as a readable local file; S3 object names never become
``pathlib.Path`` instances.  The actual dual-worker probe then writes one raw
measurement and this adapter publishes it once under the worker-specific
immutable object key.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from .authorization_keys import canonical_bytes
from .errors import CloudManifestError
from .manifests import validate_worker_admission_measurement
from .qualification_execution import (
    AwsCliAdapter,
    materialize_authenticated_inputs,
    parse_s3_uri,
    publish_raw_measurement,
    worker_artifact_uri,
)


def validate_local_probe_inputs(input_paths: Sequence[str | Path]) -> tuple[Path, ...]:
    """Require distinct readable local files and reject remote locators."""

    paths: list[Path] = []
    for value in input_paths:
        if isinstance(value, str) and value.startswith("s3://"):
            raise CloudManifestError(
                "fixed admission probe received an S3 URI instead of a materialized local file"
            )
        path = Path(value)
        if not path.is_file() or not os.access(path, os.R_OK):
            raise CloudManifestError(
                f"fixed admission probe input is not a readable local file: {path}"
            )
        paths.append(path)
    if not paths:
        raise CloudManifestError(
            "fixed admission probe requires at least one local input"
        )
    if len({path.resolve() for path in paths}) != len(paths):
        raise CloudManifestError("fixed admission probe inputs must be distinct files")
    return tuple(paths)


def _digest_inputs(paths: Sequence[Path]) -> list[dict[str, Any]]:
    return [
        {
            "path": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(paths, key=lambda item: item.as_posix())
    ]


def build_raw_measurement(
    *,
    code: str,
    worker_index: int,
    instance_id: str,
    protocol_sha256: str,
    architecture_sha256: str,
    authorization_sha256: str,
    image_sha256: str,
    input_lock_sha256: str,
    code_sha256: str,
    input_paths: Sequence[Path],
    rungs: Mapping[str, Mapping[str, Any]],
    runtime: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one schema-valid raw measurement without promoting evidence."""

    if not isinstance(code, str) or not code:
        raise CloudManifestError("fixed admission probe requires a nonempty --code")
    if worker_index not in {0, 1}:
        raise CloudManifestError("fixed admission probe worker index must be 0 or 1")
    if not isinstance(instance_id, str) or not instance_id:
        raise CloudManifestError("fixed admission probe requires an instance identity")
    for name, digest in {
        "protocol": protocol_sha256,
        "architecture": architecture_sha256,
        "authorization": authorization_sha256,
        "image": image_sha256,
        "input_lock": input_lock_sha256,
        "code": code_sha256,
    }.items():
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise CloudManifestError(
                f"fixed admission probe has an invalid {name} digest"
            )
    local = validate_local_probe_inputs(input_paths)
    if set(rungs) != {"l40s-tp1-32768", "l40s-tp1-65536"}:
        raise CloudManifestError("fixed admission probe must measure both frozen rungs")
    if runtime is None:
        runtime = {
            "model": "fixture-model",
            "revision": "fixture-revision",
            "cuda_name": "NVIDIA L40S",
            "cuda_total_memory_bytes": 1,
            "torch_version": "fixture",
            "vllm_version": "fixture",
        }
    return validate_worker_admission_measurement(
        {
            "record_kind": "cloud_worker_admission_measurement",
            "schema_version": "0.2.0",
            "protocol_sha256": protocol_sha256,
            "architecture_sha256": architecture_sha256,
            "authorization_sha256": authorization_sha256,
            "image_sha256": image_sha256,
            "input_lock_sha256": input_lock_sha256,
            "code_sha256": code_sha256,
            "worker_index": worker_index,
            "instance_id": instance_id,
            "qualification_code_sha256": hashlib.sha256(
                code.encode("utf-8")
            ).hexdigest(),
            "inputs": _digest_inputs(local),
            "runtime": dict(runtime),
            "rungs": {name: dict(value) for name, value in rungs.items()},
        }
    )


def run_probe(
    *,
    code: str,
    worker_index: int,
    instance_id: str,
    protocol_sha256: str,
    architecture_sha256: str,
    authorization_sha256: str,
    image_sha256: str,
    input_lock_sha256: str,
    code_sha256: str,
    input_paths: Sequence[str | Path],
    rungs: Mapping[str, Mapping[str, Any]],
    output: Path,
    adapter: AwsCliAdapter | None = None,
    output_uri: str | None = None,
    artifact_prefix: str | None = None,
) -> bytes:
    """Run the local contract and optionally publish its immutable raw bytes."""

    local = validate_local_probe_inputs(input_paths)
    record = build_raw_measurement(
        code=code,
        worker_index=worker_index,
        instance_id=instance_id,
        protocol_sha256=protocol_sha256,
        architecture_sha256=architecture_sha256,
        authorization_sha256=authorization_sha256,
        image_sha256=image_sha256,
        input_lock_sha256=input_lock_sha256,
        code_sha256=code_sha256,
        input_paths=local,
        rungs=rungs,
    )
    payload = canonical_bytes(record) + b"\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise CloudManifestError(
            "fixed admission probe refuses to overwrite raw evidence"
        )
    output.write_bytes(payload)
    if output_uri is not None:
        if adapter is None or artifact_prefix is None:
            raise CloudManifestError(
                "remote probe publication requires an adapter and prefix"
            )
        if output_uri != worker_artifact_uri(artifact_prefix, worker_index):
            raise CloudManifestError("remote probe output is not worker-specific")
        publish_raw_measurement(
            adapter,
            artifact_prefix=artifact_prefix,
            worker_index=worker_index,
            raw_bytes=payload,
        )
    return payload


def run_authenticated_probe(
    *,
    artifacts: Sequence[Mapping[str, Any]],
    materialization_root: Path,
    adapter: AwsCliAdapter,
    authorization: Mapping[str, Any],
    lock: Mapping[str, Any],
    key_registry: Mapping[str, Any],
    ledger_path: Path,
    **probe: Any,
) -> bytes:
    """Materialize authenticated inputs before invoking the local probe."""

    installed = materialize_authenticated_inputs(
        artifacts,
        destination=materialization_root,
        adapter=adapter,
        authorization=authorization,
        lock=lock,
        key_registry=key_registry,
        ledger_path=ledger_path,
    )
    probe["input_paths"] = tuple(installed.values())
    return run_probe(adapter=adapter, **probe)


def build_probe_argv(code: str) -> list[str]:
    """Return the required fixed-probe argument fragment."""

    if not isinstance(code, str) or not code:
        raise CloudManifestError(
            "fixed admission probe command requires a nonempty --code"
        )
    return ["--code", code]


def _materialize_one(value: str, *, destination: Path, name: str) -> Path:
    """Turn one local path or authenticated S3 object into a local file."""

    destination.mkdir(parents=True, exist_ok=True)
    target = destination / name
    if value.startswith("s3://"):
        location = parse_s3_uri(value)
        result = subprocess.run(
            [
                "aws",
                "s3api",
                "get-object",
                "--bucket",
                location.bucket,
                "--key",
                location.key,
                str(target),
                "--no-cli-pager",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise CloudManifestError(f"authenticated input download failed for {value}")
    else:
        source = Path(value)
        if not source.is_file() or not os.access(source, os.R_OK):
            raise CloudManifestError(
                f"qualification input is not a readable local file: {value}"
            )
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
    if not target.is_file() or not os.access(target, os.R_OK):
        raise CloudManifestError(
            f"materialized qualification input is not readable: {value}"
        )
    return target


def _runtime_argv(code: str, *, root: Path) -> tuple[list[str], Path]:
    """Materialize image-bound inputs and build the dual-worker argv."""

    raw_index = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
    if raw_index not in {"0", "1"}:
        raise SystemExit("AWS_BATCH_JOB_ARRAY_INDEX must be exactly 0 or 1")
    model = os.environ.get(
        "QUALIFICATION_MODEL", os.environ.get("PNEUMA_SUBJECT_MODEL")
    )
    revision = os.environ.get(
        "QUALIFICATION_MODEL_REVISION", os.environ.get("PNEUMA_SUBJECT_REVISION")
    )
    if not model or not revision:
        raise SystemExit("qualification image lacks model and revision bindings")
    argv = [
        "dual_worker_admission_probe.py",
        "--model",
        model,
        "--revision",
        revision,
        "--code",
    ]
    required = {
        "QUALIFICATION_PROTOCOL": "--protocol",
        "QUALIFICATION_ARCHITECTURE": "--architecture",
        "QUALIFICATION_AUTHORIZATION": "--authorization",
        "QUALIFICATION_IMAGE": "--image",
        "QUALIFICATION_INPUT_LOCK": "--input-lock",
    }
    code_path = _materialize_one(code, destination=root, name="qualification-code")
    argv.append(str(code_path))
    for variable, flag in required.items():
        value = os.environ.get(variable)
        if not value:
            raise SystemExit(f"missing image-bound qualification variable: {variable}")
        path = _materialize_one(
            value, destination=root, name=variable.lower().replace("_", "-")
        )
        argv.extend((flag, str(path)))
    output = root / f"worker-{raw_index}" / "raw-measurement.json"
    argv.extend(("--worker-index", raw_index, "--output", str(output)))
    argv.extend(("--rung", "l40s-tp1-32768", "--rung", "l40s-tp1-65536"))
    return argv, output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", required=True)
    args = parser.parse_args(argv)
    prefix = os.environ.get("QUALIFICATION_ARTIFACT_PREFIX")
    if not prefix:
        raise SystemExit("QUALIFICATION_ARTIFACT_PREFIX must be supplied")
    raw_index = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
    if raw_index not in {"0", "1"}:
        raise SystemExit("AWS_BATCH_JOB_ARRAY_INDEX must be exactly 0 or 1")
    with tempfile.TemporaryDirectory(prefix="pneuma-qualification-") as temporary:
        command, output = _runtime_argv(args.code, root=Path(temporary))
        saved_argv = sys.argv
        try:
            sys.argv = command
            from . import dual_worker_admission_probe

            dual_worker_admission_probe.main()
        finally:
            sys.argv = saved_argv
        payload = output.read_bytes()
        # This enforces schema validation, worker-index binding and the
        # immutable S3 precondition in the same adapter used by the controller.
        publish_raw_measurement(
            AwsCliAdapter(),
            artifact_prefix=prefix,
            worker_index=int(raw_index),
            raw_bytes=payload,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Content-addressed runtime for the three production image roles.

The default ``verify`` protocol is the small Step 7B image probe.  The
``e2e`` protocol is retained as an explicitly qualification-only harness.
The ``production`` protocol consumes the immutable run specification and
sends the registered task surface through the real model and benchmark
adapters.  It is a runtime path, not authorization to launch it.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib import error as urllib_error
from urllib import request as urllib_request

from .production_evidence import ProductionWorkerExecutor, launch_model_server, write_worker_result
from .production_controller import ProductionOrchestrator, ProductionStateStore
from .production_run import ProductionRunSpec, canonical_digest, task_rows, work_ids_for_worker

_ROLES = frozenset({"controller", "model-server", "benchmark-worker"})
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_E2E_KIND = "cloud_production_e2e_harness"


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _canonical_bytes(value: object) -> bytes:
    return (_canonical(value) + "\n").encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _failure(role: str, reason: str) -> int:
    print(_canonical({"role": role, "state": "FAILED", "reason": reason}))
    return 2


def _s3_location(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.lstrip("/"):
        raise ValueError("S3 URI must identify one object")
    return parsed.netloc, parsed.path.lstrip("/")


def _extract_package(archive: Path, destination: Path) -> None:
    """Extract one regular-file-only run package beneath a new destination."""

    if destination.exists() and any(destination.iterdir()):
        raise ValueError("run root must be empty before immutable package staging")
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive, mode="r:gz") as handle:
        members = handle.getmembers()
        if not members:
            raise ValueError("run package is empty")
        for member in members:
            if not member.isfile() and not member.isdir():
                raise ValueError("run package may contain only regular files/directories")
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                raise ValueError("run package path escapes the run root")
        handle.extractall(destination, filter="data")


def _stage_official_package(
    *, package_uri: str, package_sha256: str, run_root: Path
) -> dict[str, object]:
    """Fetch, verify, and admit the exact official package for sibling roles."""

    if not _DIGEST.fullmatch(package_sha256):
        raise ValueError("package digest must be lowercase SHA-256")
    bucket, key = _s3_location(package_uri)
    import boto3

    with tempfile.TemporaryDirectory(prefix="pneuma-official-stage-") as temporary:
        archive = Path(temporary) / "package.tar.gz"
        boto3.client("s3", region_name="us-east-1").download_file(
            bucket, key, str(archive)
        )
        raw_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if raw_digest != package_sha256:
            raise ValueError("downloaded run package digest differs")
        _extract_package(archive, run_root)
    spec_path = run_root / "run-spec.json"
    spec = ProductionRunSpec.load(spec_path)
    if spec.run_mode != "official":
        raise ValueError("staged package is not an official run")
    spec.verify_official_authorization(run_root=run_root)
    payload_receipts = _reconstruct_registered_payloads(run_root=run_root)
    receipt: dict[str, object] = {
        "record_kind": "cloud_official_package_stage_receipt",
        "schema_version": "0.1.0",
        "action_id": spec.value["action_id"],
        "package_s3_uri": package_uri,
        "package_sha256": package_sha256,
        "run_spec_sha256": spec.digest,
        "payloads": payload_receipts,
        "state": "STAGED",
    }
    (run_root / "package-stage-receipt.json").write_bytes(_canonical_bytes(receipt))
    return receipt


def _reconstruct_registered_payloads(*, run_root: Path) -> list[dict[str, object]]:
    bucket = os.environ.get("PNEUMA_PAYLOAD_BUCKET")
    prefix = os.environ.get("PNEUMA_PAYLOAD_PREFIX")
    if not bucket or not prefix:
        raise ValueError("official payload bucket/prefix is required")
    prefix = prefix.strip("/")
    roles = {
        "subject_model": "subject-model",
        "simulator_model": "simulator-model",
        "swe_harness": "swe-harness",
        "tau2_harness": "tau2-harness",
        "repo_launcher": "repo-launcher",
    }
    import boto3

    client = boto3.client("s3", region_name="us-east-1")
    receipts: list[dict[str, object]] = []
    for snapshot_name, destination_name in roles.items():
        snapshot_path = run_root / f"inputs/receipts/{snapshot_name}-snapshot.json"
        raw = snapshot_path.read_bytes()
        snapshot = json.loads(raw.decode("utf-8"))
        rows = snapshot.get("objects") if isinstance(snapshot, dict) else None
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{snapshot_name} payload snapshot is missing")
        destination = run_root / "payloads" / destination_name
        destination.mkdir(parents=True, exist_ok=False)

        def install(row: object) -> int:
            if not isinstance(row, dict):
                raise ValueError("payload row is malformed")
            relative = Path(str(row["path"]))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("payload path escapes its role root")
            target = (destination / relative).resolve()
            if destination.resolve() not in target.parents:
                raise ValueError("payload path escapes its role root")
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".partial")
            client.download_file(
                bucket,
                f"{prefix}/objects/{row['object_id']}",
                str(temporary),
            )
            payload = temporary.read_bytes()
            if (
                len(payload) != row.get("size_bytes")
                or hashlib.sha256(payload).hexdigest() != row.get("payload_sha256")
            ):
                temporary.unlink(missing_ok=True)
                raise ValueError("payload bytes differ from their frozen snapshot")
            temporary.replace(target)
            return len(payload)

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            sizes = list(executor.map(install, rows))
        expected_count = snapshot.get("object_count")
        expected_bytes = snapshot.get("payload_bytes")
        if len(sizes) != expected_count or sum(sizes) != expected_bytes:
            raise ValueError("reconstructed payload totals differ")
        receipts.append(
            {
                "role": snapshot_name,
                "object_count": len(sizes),
                "payload_bytes": sum(sizes),
                "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return receipts


def _worker_id_from_environment() -> str | None:
    index = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
    if index is None:
        return None
    if index not in {"0", "1"}:
        raise ValueError("official Batch array index must be 0 or 1")
    return f"worker-{index}"


def _ensure_worker_identity(worker_id: str) -> None:
    if os.environ.get("PNEUMA_WORKER_IDENTITY"):
        return
    job_id = os.environ.get("AWS_BATCH_JOB_ID")
    if not job_id:
        raise ValueError("official Batch job identity is unavailable")
    os.environ["PNEUMA_WORKER_IDENTITY"] = f"aws-batch:{job_id}:{worker_id}"


def _publish_worker_outputs(
    *, output_uri: str, worker_id: str, evidence_path: Path, raw_path: Path
) -> None:
    bucket, prefix = _s3_location(output_uri.rstrip("/") + "/sentinel")
    prefix = prefix.rsplit("/", 1)[0]
    import boto3

    client = boto3.client("s3", region_name="us-east-1")
    for label, path in (("evidence", evidence_path), ("raw", raw_path)):
        client.put_object(
            Bucket=bucket,
            Key=f"{prefix}/{worker_id}.{label}.json",
            Body=path.read_bytes(),
            ServerSideEncryption="AES256",
            ContentType="application/json",
            IfNoneMatch="*",
        )


def _wait_for_model(spec: ProductionRunSpec) -> None:
    model_server = spec.value["model_server"]
    if not isinstance(model_server, dict):
        raise ValueError("model server specification is malformed")
    endpoint = str(model_server["endpoint"]).rstrip("/") + "/health"
    deadline = time.monotonic() + int(model_server["readiness_timeout_seconds"])
    while time.monotonic() < deadline:
        try:
            with urllib_request.urlopen(endpoint, timeout=5) as response:
                if 200 <= response.status < 300:
                    return
        except (urllib_error.URLError, TimeoutError, OSError):
            pass
        time.sleep(5)
    raise TimeoutError("model server did not become ready before the frozen deadline")


def _read_harness(path: Path, expected: str) -> tuple[bytes, str] | None:
    payload = path.read_bytes()
    observed = _sha256(payload)
    if observed != expected:
        return None
    return payload, observed


def _require_e2e_harness(payload: bytes) -> dict[str, Any] | None:
    try:
        harness = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(harness, dict) or _canonical_bytes(harness) != payload:
        return None
    if harness.get("record_kind") != _E2E_KIND or harness.get("schema_version") != "0.1.0":
        return None
    if not isinstance(harness.get("action_id"), str) or not harness["action_id"]:
        return None
    if not isinstance(harness.get("input_lock_sha256"), str) or not _DIGEST.fullmatch(harness["input_lock_sha256"]):
        return None
    request = harness.get("request")
    if not isinstance(request, dict):
        return None
    if not isinstance(request.get("request_id"), str) or not request["request_id"]:
        return None
    if not isinstance(request.get("prompt"), str) or not request["prompt"]:
        return None
    if type(request.get("max_tokens")) is not int or not 1 <= request["max_tokens"] <= 16:
        return None
    if type(request.get("temperature")) is not float or request["temperature"] != 0.0:
        return None
    return harness


def _common(harness: dict[str, Any], role: str, state: str, harness_sha256: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = harness["request"]
    request_bytes = _canonical_bytes(request)
    return {
        "record_kind": "cloud_production_role_receipt",
        "schema_version": "0.1.0",
        "role": role,
        "state": state,
        "action_id": harness["action_id"],
        "input_lock_sha256": harness["input_lock_sha256"],
        "harness_sha256": harness_sha256,
        "harness_bytes": len(_canonical_bytes(harness)),
        "request_id": request["request_id"],
        "request_sha256": _sha256(request_bytes),
        "payload": payload,
    }


def _load_input(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _e2e(role: str, harness: dict[str, Any], harness_sha256: str, input_path: Path | None) -> int:
    request = harness["request"]
    request_sha256 = _sha256(_canonical_bytes(request))
    if role == "controller":
        if input_path is not None:
            return _failure(role, "controller_input_forbidden")
        receipt = _common(
            harness,
            role,
            "DISPATCHED",
            harness_sha256,
            {"next_role": "model-server", "request": request},
        )
        print(_canonical(receipt))
        return 0

    if input_path is None:
        return _failure(role, "role_input_required")
    predecessor = _load_input(input_path)
    if predecessor is None:
        return _failure(role, "predecessor_receipt_invalid")
    if predecessor.get("record_kind") != "cloud_production_role_receipt":
        return _failure(role, "predecessor_kind_mismatch")
    if predecessor.get("harness_sha256") != harness_sha256:
        return _failure(role, "predecessor_harness_mismatch")
    if predecessor.get("action_id") != harness["action_id"] or predecessor.get("input_lock_sha256") != harness["input_lock_sha256"]:
        return _failure(role, "predecessor_authority_mismatch")
    if predecessor.get("request_sha256") != request_sha256:
        return _failure(role, "predecessor_request_mismatch")

    if role == "model-server":
        if predecessor.get("role") != "controller" or predecessor.get("state") != "DISPATCHED":
            return _failure(role, "controller_dispatch_required")
        digest = _sha256(request["prompt"].encode("utf-8"))
        token_count = min(request["max_tokens"], 4)
        response = {
            "adapter": "content-addressed-qualification-v1",
            "text": f"qualification:{digest[:16]}",
            "token_ids": [int(digest[index : index + 2], 16) for index in range(0, token_count * 2, 2)],
        }
        response_sha256 = _sha256(_canonical_bytes(response))
        receipt = _common(
            harness,
            role,
            "RESPONDED",
            harness_sha256,
            {"response": response, "response_sha256": response_sha256, "next_role": "benchmark-worker"},
        )
        print(_canonical(receipt))
        return 0

    if predecessor.get("role") != "model-server" or predecessor.get("state") != "RESPONDED":
        return _failure(role, "model_response_required")
    predecessor_payload = predecessor.get("payload")
    if not isinstance(predecessor_payload, dict):
        return _failure(role, "model_payload_invalid")
    response = predecessor_payload.get("response")
    response_sha256 = predecessor_payload.get("response_sha256")
    if not isinstance(response, dict) or not isinstance(response_sha256, str) or _sha256(_canonical_bytes(response)) != response_sha256:
        return _failure(role, "model_response_digest_mismatch")
    token_ids = response.get("token_ids")
    if not isinstance(token_ids, list) or not token_ids or any(type(token) is not int or not 0 <= token <= 255 for token in token_ids):
        return _failure(role, "model_response_tokens_invalid")
    receipt = _common(
        harness,
        role,
        "COMPLETE",
        harness_sha256,
        {
            "response_sha256": response_sha256,
            "accepted": True,
            "generated_tokens": len(token_ids),
            "evaluation": "protocol_round_trip",
        },
    )
    print(_canonical(receipt))
    return 0


def _production(
    role: str,
    spec_path: Path | None,
    spec_sha256: str | None,
    *,
    worker_id: str | None,
    output_path: Path | None,
    raw_output_path: Path | None,
    run_root: Path,
) -> int:
    """Run one production role without ever falling back to the fixture path."""

    if spec_path is None or spec_sha256 is None:
        return _failure(role, "production_run_spec_required")
    try:
        spec = ProductionRunSpec.load(spec_path, expected_sha256=spec_sha256)
        if spec.run_mode == "official_candidate":
            return _failure(role, "prelaunch_candidate_not_executable")
        if spec.run_mode == "official":
            # A real official job must carry its own cryptographically verified
            # authority.  Merely selecting ``--protocol production`` cannot
            # turn a qualification action or local mock into official evidence.
            spec.verify_official_authorization(run_root=run_root)
        if role == "controller":
            rows = task_rows(spec, run_root=run_root)
            allocation = {
                worker: list(
                    work_ids_for_worker(spec, worker_id=worker, run_root=run_root)
                )
                for worker in spec.worker_ids
            }
            state_ref = spec.value["output"]["controller_state_path"]
            state_path = run_root / str(state_ref)
            store = ProductionStateStore(
                state_path,
                action_id=str(spec.value["action_id"]),
                run_spec_sha256=spec.digest,
                binding={"action_id": spec.value["action_id"], "run_spec_sha256": spec.digest},
            )
            orchestrator = ProductionOrchestrator(
                store,
                action_id=str(spec.value["action_id"]),
                run_spec_sha256=spec.digest,
                allocation=allocation,
            )
            orchestrator.prepare()
            print(
                _canonical(
                    {
                        "record_kind": "cloud_production_dispatch_plan",
                        "schema_version": "0.1.0",
                        "run_spec_sha256": spec.digest,
                        "task_count": len(rows),
                        "allocation": allocation,
                        "execution_class": (
                            "official"
                            if spec.run_mode == "official"
                            else "local_mock_non_scientific"
                        ),
                    }
                )
            )
            return 0
        if role == "model-server":
            launch_model_server(spec, run_root=run_root)
            return 0
        worker_id = worker_id or _worker_id_from_environment()
        if worker_id is not None and output_path is None:
            template = str(spec.value["output"]["worker_evidence_template"])
            output_path = run_root / template.format(worker_id=worker_id)
        if worker_id is not None and raw_output_path is None:
            output_root = Path(str(spec.value["output"]["root"]))
            raw_output_path = run_root / output_root / f"{worker_id}.raw.json"
        if worker_id is None or output_path is None or raw_output_path is None:
            return _failure(role, "production_worker_outputs_required")
        if spec.run_mode == "official":
            _ensure_worker_identity(worker_id)
            _wait_for_model(spec)
        result = ProductionWorkerExecutor(spec, run_root=run_root).execute(worker_id)
        evidence = write_worker_result(
            result,
            evidence_path=output_path,
            raw_path=raw_output_path,
            run_root=run_root,
        )
        output_uri = os.environ.get("PNEUMA_OUTPUT_S3_URI")
        if spec.run_mode == "official":
            if not output_uri:
                return _failure(role, "official_output_s3_uri_required")
            _publish_worker_outputs(
                output_uri=output_uri,
                worker_id=worker_id,
                evidence_path=output_path,
                raw_path=raw_output_path,
            )
        print(
            _canonical(
                {
                    "record_kind": "cloud_production_worker_terminal",
                    "schema_version": "0.1.0",
                    "run_spec_sha256": spec.digest,
                    "worker_id": worker_id,
                    "evidence_sha256": canonical_digest(evidence),
                    "state": evidence["state"],
                }
            )
        )
        return 0
    except Exception as exc:
        return _failure(role, type(exc).__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=sorted(_ROLES))
    parser.add_argument("--harness", type=Path)
    parser.add_argument("--harness-sha256")
    parser.add_argument(
        "--protocol", choices=("verify", "e2e", "stage", "production"), default="verify"
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--run-spec", type=Path)
    parser.add_argument("--run-spec-sha256")
    parser.add_argument("--worker-id")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--raw-output", type=Path)
    parser.add_argument("--run-root", type=Path, default=Path.cwd())
    parser.add_argument("--package-s3-uri")
    parser.add_argument("--package-sha256")
    args = parser.parse_args(argv)
    if args.protocol == "stage":
        if args.role != "controller":
            return _failure(args.role, "only_controller_may_stage_package")
        if args.package_s3_uri is None or args.package_sha256 is None:
            parser.error("--package-s3-uri and --package-sha256 are required for staging")
        try:
            receipt = _stage_official_package(
                package_uri=args.package_s3_uri,
                package_sha256=args.package_sha256,
                run_root=args.run_root,
            )
        except Exception as exc:
            return _failure(args.role, type(exc).__name__)
        print(_canonical(receipt))
        return 0
    if args.protocol == "production":
        if args.run_spec_sha256 is not None and not _DIGEST.fullmatch(args.run_spec_sha256):
            parser.error("--run-spec-sha256 must be lowercase SHA-256")
        return _production(
            args.role,
            args.run_spec,
            args.run_spec_sha256,
            worker_id=args.worker_id,
            output_path=args.output,
            raw_output_path=args.raw_output,
            run_root=args.run_root,
        )
    if args.harness is None or args.harness_sha256 is None:
        parser.error("--harness and --harness-sha256 are required for qualification protocols")
    if not _DIGEST.fullmatch(args.harness_sha256):
        parser.error("--harness-sha256 must be lowercase SHA-256")
    read = _read_harness(args.harness, args.harness_sha256)
    if read is None:
        return _failure(args.role, "harness_sha256_mismatch")
    payload, observed = read
    if args.protocol == "verify":
        print(_canonical({"role": args.role, "state": "READY", "harness_sha256": observed, "harness_bytes": len(payload)}))
        return 0
    harness = _require_e2e_harness(payload)
    if harness is None:
        return _failure(args.role, "e2e_harness_invalid")
    return _e2e(args.role, harness, observed, args.input)


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the in-image fixture/materialization/raw-publication smoke check.

This check is deliberately CPU-only and uses an injected in-memory transport.
It proves that the immutable image contains the package path and that the
fixed entrypoint adapter materializes all five inputs and publishes one
worker-indexed immutable raw object without contacting AWS or loading a model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.fixed_admission_probe import build_raw_measurement, run_fixed_worker
from pneuma_lab.cloud.qualification_execution import AwsCliAdapter


ACTION_ID = "qualification-image-fixture-check"
PREFIX = "s3://fixture-bucket/qualification-image-fixture-check/outputs/"
MODEL = "fixture-only-cuda"
REVISION = "fixture-only-v1"


class MemoryTransport:
    def __init__(self, objects: dict[tuple[str, str], bytes]) -> None:
        self.objects = dict(objects)
        self.puts: list[tuple[str, str, bytes]] = []
        self.output_get_attempts: list[tuple[str, str]] = []

    def get_object(self, bucket: str, key: str) -> bytes:
        if "/outputs/worker-" in key:
            self.output_get_attempts.append((bucket, key))
            raise AssertionError("worker fixture attempted a forbidden output read")
        return self.objects[(bucket, key)]

    def put_object(
        self, bucket: str, key: str, payload: bytes, *, if_none_match: str
    ) -> None:
        if if_none_match != "*" or (bucket, key) in self.objects:
            raise AssertionError("fixture publication was not immutable")
        self.objects[(bucket, key)] = payload
        self.puts.append((bucket, key, payload))


def _rungs() -> dict[str, dict[str, Any]]:
    rung: dict[str, Any] = {
        "peak_allocated_bytes": int(1.0 * 1024**3),
        "throughput": {
            "p10_method": "nearest_rank",
            "warmup_samples": 1,
            "output_tokens_per_sample": 128,
            "samples": [
                {
                    "index": index,
                    "elapsed_seconds": 1.0,
                    "generated_tokens": 128,
                    "output_token_ids_sha256": hashlib.sha256(
                        json.dumps([index] * 128, separators=(",", ":")).encode()
                    ).hexdigest(),
                }
                for index in range(10)
            ],
        },
        "tool_calls": [
            {
                "fixture_id": fixture_id,
                "raw_response_text": json.dumps(
                    {"name": name, "arguments": arguments},
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "name": name,
                "arguments": arguments,
            }
            for fixture_id, (name, arguments) in {
                "admission-add": ("qualification_add", {"left": 2, "right": 3}),
                "admission-echo": ("qualification_echo", {"text": "pneuma-admission"}),
                "admission-lookup": ("qualification_lookup", {"key": "runtime"}),
                "admission-status": ("qualification_status", {"component": "worker"}),
            }.items()
        ],
        "output_parity": [
            {
                "fixture_id": f"admission-parity-{index}",
                "first_output_token_ids": [index] * 32,
                "second_output_token_ids": [index] * 32,
            }
            for index in range(4)
        ],
    }
    return {
        "l40s-tp1-32768": json.loads(json.dumps(rung)),
        "l40s-tp1-65536": json.loads(json.dumps(rung)),
    }


def _option(argv: list[str], name: str) -> str:
    index = argv.index(name)
    return argv[index + 1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    objects = {
        ("fixture-bucket", f"qualification-image-fixture-check/inputs/{name}.json"): payload
        for name, payload in {
            "protocol": b'{"record_kind":"fixture-protocol"}',
            "architecture": b'{"record_kind":"fixture-architecture"}',
            "authorization": b'{"record_kind":"fixture-authorization"}',
            "image": b'{"record_kind":"fixture-image"}',
            "input-lock": b'{"record_kind":"fixture-input-lock"}',
        }.items()
    }
    transport = MemoryTransport(objects)
    adapter = AwsCliAdapter(transport=transport)
    env = {
        "AWS_BATCH_JOB_ARRAY_INDEX": "0",
        "QUALIFICATION_ACTION_ID": ACTION_ID,
        "QUALIFICATION_MODEL": MODEL,
        "QUALIFICATION_MODEL_REVISION": REVISION,
        "QUALIFICATION_ARTIFACT_PREFIX": PREFIX,
        "QUALIFICATION_OUTPUT_ROOT": PREFIX,
        "QUALIFICATION_PROTOCOL": "s3://fixture-bucket/qualification-image-fixture-check/inputs/protocol.json",
        "QUALIFICATION_ARCHITECTURE": "s3://fixture-bucket/qualification-image-fixture-check/inputs/architecture.json",
        "QUALIFICATION_AUTHORIZATION": "s3://fixture-bucket/qualification-image-fixture-check/inputs/authorization.json",
        "QUALIFICATION_IMAGE": "s3://fixture-bucket/qualification-image-fixture-check/inputs/image.json",
        "QUALIFICATION_INPUT_LOCK": "s3://fixture-bucket/qualification-image-fixture-check/inputs/input-lock.json",
    }

    def fake_probe(argv: Any, output: Path) -> None:
        inputs = [Path(_option(list(argv), flag)) for flag in (
            "--protocol", "--architecture", "--authorization", "--image", "--input-lock"
        )]
        worker_index = int(_option(list(argv), "--worker-index"))
        code_path = Path(_option(list(argv), "--code"))
        record = build_raw_measurement(
            code=code_path.read_text(encoding="utf-8"),
            worker_index=worker_index,
            instance_id=f"i-0123456789abcdef{worker_index}",
            protocol_sha256=hashlib.sha256(inputs[0].read_bytes()).hexdigest(),
            architecture_sha256=hashlib.sha256(inputs[1].read_bytes()).hexdigest(),
            authorization_sha256=hashlib.sha256(inputs[2].read_bytes()).hexdigest(),
            image_sha256=hashlib.sha256(inputs[3].read_bytes()).hexdigest(),
            input_lock_sha256=hashlib.sha256(inputs[4].read_bytes()).hexdigest(),
            code_sha256=hashlib.sha256(code_path.read_bytes()).hexdigest(),
            input_paths=inputs,
            rungs=_rungs(),
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_bytes(record) + b"\n")

    payloads: dict[int, bytes] = {}
    with tempfile.TemporaryDirectory(prefix="pneuma-image-fixture-") as directory:
        for worker_index in (0, 1):
            worker_env = dict(env)
            worker_env["AWS_BATCH_JOB_ARRAY_INDEX"] = str(worker_index)
            payloads[worker_index] = run_fixed_worker(
                code="fixture-only-code",
                root=Path(directory) / f"worker-{worker_index}",
                adapter=adapter,
                env=worker_env,
                probe_runner=fake_probe,
            )
    expected_keys = {
        f"qualification-image-fixture-check/outputs/worker-{index}/raw-measurement.json"
        for index in (0, 1)
    }
    if len(transport.puts) != 2 or {key for _, key, _ in transport.puts} != expected_keys:
        raise RuntimeError("fixture image check did not publish exactly one object per worker")
    if transport.output_get_attempts:
        raise RuntimeError(
            "fixture image check attempted a forbidden worker output read: "
            f"{transport.output_get_attempts!r}"
        )
    for bucket, key, published in transport.puts:
        if bucket != "fixture-bucket":
            raise RuntimeError("fixture image check published to the wrong bucket")
        worker_index = int(key.split("/worker-", 1)[1].split("/", 1)[0])
        if payloads[worker_index] != published or transport.objects[(bucket, key)] != published:
            raise RuntimeError("fixture image check could not retrieve byte-identical raw evidence")
    print(
        json.dumps(
            {
                "status": "pass",
                "model_loaded": False,
                "published_bytes": {
                    str(index): len(payload) for index, payload in payloads.items()
                },
                "worker_indices": [0, 1],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

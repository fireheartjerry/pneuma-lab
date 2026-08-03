"""Record one worker's complete, non-efficacy GPU admission evidence.

This command is intentionally inert until a human supplies a GPU, immutable
inputs, and explicit execution authority. It never calls AWS, creates cloud
resources, loads a model, selects scientific work, or compiles an admission
receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import tempfile
import time
import urllib.request
from importlib.metadata import version
from pathlib import Path
from typing import Any

from pneuma_lab.cloud.admission_measurement import (
    OUTPUT_PARITY_FIXTURE_IDS,
    TOOL_CALL_FIXTURES,
)
from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.pilot import RUNG_NAMES, protocol_digest


_RUNG_LENGTHS = {"l40s-tp1-32768": 32768, "l40s-tp1-65536": 65536}
_WATCHDOG_SECONDS = 3500
FIXTURE_MODEL = "fixture-only-cuda"
FIXTURE_REVISION = "fixture-only-v1"


def _watchdog(_: int, __: Any) -> None:
    raise SystemExit("qualification watchdog expired before the Batch timeout")


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"bound input is not a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aws_instance_id() -> str:
    token_request = urllib.request.Request(
        "http://169.254.169.254/latest/api/token",
        method="PUT",
        headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
    )
    with urllib.request.urlopen(token_request, timeout=2) as response:  # nosec B310
        token = response.read().decode("ascii")
    identity_request = urllib.request.Request(
        "http://169.254.169.254/latest/meta-data/instance-id",
        headers={"X-aws-ec2-metadata-token": token},
    )
    with urllib.request.urlopen(identity_request, timeout=2) as response:  # nosec B310
        instance_id = response.read().decode("ascii")
    if not instance_id.startswith("i-"):
        raise RuntimeError("EC2 metadata did not return an instance identity")
    return instance_id


def _token_ids_sha256(token_ids: list[int]) -> str:
    return hashlib.sha256(
        json.dumps(token_ids, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def require_fixture_binding(model: str, revision: str) -> None:
    """Refuse every model-backed execution path in the qualification image."""

    if (model, revision) != (FIXTURE_MODEL, FIXTURE_REVISION):
        raise RuntimeError(
            "qualification worker accepts only the CUDA fixture binding; "
            "subject-model execution is excluded"
        )


def _fixture_tool_call_observations() -> list[dict[str, object]]:
    return [
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
        for fixture_id, (name, arguments) in TOOL_CALL_FIXTURES.items()
    ]


def _fixture_output_parity_observations() -> list[dict[str, object]]:
    return [
        {
            "fixture_id": fixture_id,
            "first_output_token_ids": [index] * 32,
            "second_output_token_ids": [index] * 32,
        }
        for index, fixture_id in enumerate(OUTPUT_PARITY_FIXTURE_IDS)
    ]


def _fixture_rung(*, rung: str, torch: Any) -> dict[str, object]:
    """Exercise CUDA with deterministic tensors and no model or network."""

    tokens = _RUNG_LENGTHS[rung]
    device = torch.device("cuda:0")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    # The rung size is real input to a CUDA allocation, but the fixture is
    # deliberately tiny relative to the 44 GiB usable-device boundary.
    working_set = torch.zeros((tokens, 8), device=device, dtype=torch.float16)
    working_set.add_(1)
    torch.cuda.synchronize()

    def sample(index: int) -> dict[str, object]:
        started = time.monotonic_ns()
        token_ids = torch.arange(128, device=device, dtype=torch.int32)
        token_ids = (token_ids + tokens + index) % 32000
        token_ids = token_ids.cpu().tolist()
        torch.cuda.synchronize()
        elapsed = (time.monotonic_ns() - started) / 1_000_000_000
        if len(token_ids) != 128:
            raise RuntimeError("CUDA fixture did not produce exactly 128 token IDs")
        return {
            "index": index,
            "elapsed_seconds": max(elapsed, 1e-9),
            "generated_tokens": 128,
            "output_token_ids_sha256": _token_ids_sha256(token_ids),
        }

    sample(0)
    samples = [sample(index) for index in range(10)]
    peak_allocated_bytes = int(torch.cuda.max_memory_allocated())
    del working_set
    torch.cuda.synchronize()
    torch.cuda.empty_cache()
    return {
        "peak_allocated_bytes": peak_allocated_bytes,
        "throughput": {
            "p10_method": "nearest_rank",
            "warmup_samples": 1,
            "output_tokens_per_sample": 128,
            "samples": samples,
        },
        "tool_calls": _fixture_tool_call_observations(),
        "output_parity": _fixture_output_parity_observations(),
    }


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temporary_path = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary_path = Path(raw_temporary_path)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--worker-index", choices=(0, 1), type=int, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--architecture", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--input-lock", type=Path, required=True)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--rung", action="append", choices=RUNG_NAMES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require_fixture_binding(args.model, args.revision)

    signal.signal(signal.SIGALRM, _watchdog)
    signal.alarm(_WATCHDOG_SECONDS)
    try:
        if tuple(args.rung) != RUNG_NAMES:
            parser.error(
                "supply --rung l40s-tp1-32768 followed by --rung l40s-tp1-65536"
            )
        if args.output.exists():
            parser.error("refusing to overwrite existing raw measurement evidence")
        protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
        protocol_sha256 = protocol_digest(protocol)
        bound_hashes = {
            "architecture_sha256": _sha256_file(args.architecture),
            "authorization_sha256": _sha256_file(args.authorization),
            "image_sha256": _sha256_file(args.image),
            "input_lock_sha256": _sha256_file(args.input_lock),
            "code_sha256": _sha256_file(args.code),
        }
        bound_inputs = [
            {
                "path": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
            for path in sorted(
                (
                    args.protocol,
                    args.architecture,
                    args.authorization,
                    args.image,
                    args.input_lock,
                    args.code,
                ),
                key=lambda item: item.as_posix(),
            )
        ]
        instance_id = _aws_instance_id()

        import torch

        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise RuntimeError("admission probe requires exactly one CUDA device")
        properties = torch.cuda.get_device_properties(0)
        if "L40S" not in properties.name:
            raise RuntimeError(
                f"admission probe requires an L40S, found {properties.name!r}"
            )
        raw = {
            "record_kind": "cloud_worker_admission_measurement",
            "schema_version": "0.2.0",
            "protocol_sha256": protocol_sha256,
            **bound_hashes,
            "worker_index": args.worker_index,
            "instance_id": instance_id,
            "qualification_code_sha256": bound_hashes["code_sha256"],
            "inputs": bound_inputs,
            "runtime": {
                "model": args.model,
                "revision": args.revision,
                "cuda_name": properties.name,
                "cuda_total_memory_bytes": properties.total_memory,
                "torch_version": torch.__version__,
                # The image contains vLLM for the separate production
                # surface, but this qualification worker never imports it or
                # loads a model.
                "vllm_version": version("vllm"),
            },
            "rungs": {
                rung: _fixture_rung(rung=rung, torch=torch)
                for rung in args.rung
            },
        }
        _write_new(args.output, canonical_bytes(raw) + b"\n")
        print(
            json.dumps(
                {"status": "measured", "worker_index": args.worker_index},
                sort_keys=True,
            )
        )
        return 0
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())

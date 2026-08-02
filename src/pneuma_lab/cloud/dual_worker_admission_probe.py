"""Record one worker's complete, non-efficacy GPU admission evidence.

This command is intentionally inert until a human supplies a GPU, immutable
inputs, and explicit execution authority. It never calls AWS, creates cloud
resources, selects scientific work, or compiles an admission receipt.
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
from pathlib import Path
from typing import Any

from pneuma_lab.cloud.admission_measurement import (
    OUTPUT_PARITY_FIXTURE_IDS,
    TOOL_CALL_FIXTURES,
    canonical_tool_call,
    parse_tool_call_text,
)
from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.pilot import RUNG_NAMES, protocol_digest


_RUNG_LENGTHS = {"l40s-tp1-32768": 32768, "l40s-tp1-65536": 65536}
_WATCHDOG_SECONDS = 3500


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


def _tool_schema(name: str, arguments: dict[str, object]) -> dict[str, object]:
    properties: dict[str, object] = {}
    for key, value in arguments.items():
        json_type = (
            "integer"
            if isinstance(value, int) and not isinstance(value, bool)
            else "string"
        )
        properties[key] = {"type": json_type, "const": value}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": "Return one sealed infrastructure qualification call.",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(arguments),
                "additionalProperties": False,
            },
        },
    }


def _sampling_params(vllm: Any, *, tokens: int) -> Any:
    return vllm.SamplingParams(
        temperature=0.0,
        seed=0,
        max_tokens=tokens,
        min_tokens=tokens,
        ignore_eos=True,
    )


def _one_output(engine: Any, prompt: str, params: Any) -> Any:
    return engine.generate([prompt], params, use_tqdm=False)[0].outputs[0]


def _throughput_observation(engine: Any, vllm: Any, *, rung: str) -> dict[str, object]:
    params = _sampling_params(vllm, tokens=128)
    _one_output(
        engine,
        "This is an excluded infrastructure warmup. Return a short neutral sentence.",
        params,
    )
    samples = []
    for index in range(10):
        started = time.monotonic_ns()
        output = _one_output(
            engine,
            f"Infrastructure throughput fixture {rung}:{index}. Return a neutral sentence.",
            params,
        )
        elapsed = (time.monotonic_ns() - started) / 1_000_000_000
        token_ids = list(output.token_ids)
        if len(token_ids) != 128:
            raise RuntimeError(
                f"throughput fixture {index} returned {len(token_ids)} tokens, expected 128"
            )
        samples.append(
            {
                "index": index,
                "elapsed_seconds": elapsed,
                "generated_tokens": len(token_ids),
                "output_token_ids_sha256": _token_ids_sha256(token_ids),
            }
        )
    return {
        "p10_method": "nearest_rank",
        "warmup_samples": 1,
        "output_tokens_per_sample": 128,
        "samples": samples,
    }


def _tool_call_observations(engine: Any, vllm: Any) -> list[dict[str, object]]:
    observations = []
    params = _sampling_params(vllm, tokens=128)
    for fixture_id, (name, arguments) in TOOL_CALL_FIXTURES.items():
        output = engine.chat(
            [
                {
                    "role": "user",
                    "content": (
                        "Run the provided qualification function exactly once. "
                        "Do not explain the call or produce a benchmark answer."
                    ),
                }
            ],
            sampling_params=params,
            tools=[_tool_schema(name, arguments)],
        )[0].outputs[0]
        raw_response_text = output.text
        parsed = parse_tool_call_text(raw_response_text)
        observations.append(
            {
                "fixture_id": fixture_id,
                "raw_response_text": raw_response_text,
                **canonical_tool_call(parsed["name"], parsed["arguments"]),
            }
        )
    return observations


def _output_parity_observations(engine: Any, vllm: Any) -> list[dict[str, object]]:
    params = _sampling_params(vllm, tokens=32)
    observations = []
    for fixture_id in OUTPUT_PARITY_FIXTURE_IDS:
        prompt = (
            "This is a deterministic infrastructure parity fixture named "
            f"{fixture_id}. Return a neutral sequence and no tool call."
        )
        first = list(_one_output(engine, prompt, params).token_ids)
        second = list(_one_output(engine, prompt, params).token_ids)
        if len(first) != 32 or len(second) != 32:
            raise RuntimeError(
                "output-parity fixture did not produce exactly 32 token IDs"
            )
        observations.append(
            {
                "fixture_id": fixture_id,
                "first_output_token_ids": first,
                "second_output_token_ids": second,
            }
        )
    return observations


def _measure_rung(
    *, model: str, revision: str, rung: str, torch: Any, vllm: Any
) -> dict[str, object]:
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    engine = vllm.LLM(
        model=model,
        revision=revision,
        tokenizer=model,
        tokenizer_revision=revision,
        trust_remote_code=False,
        max_model_len=_RUNG_LENGTHS[rung],
        max_num_seqs=1,
        gpu_memory_utilization=0.90,
        enforce_eager=True,
        tensor_parallel_size=1,
    )
    try:
        result = {
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "throughput": _throughput_observation(engine, vllm, rung=rung),
            "tool_calls": _tool_call_observations(engine, vllm),
            "output_parity": _output_parity_observations(engine, vllm),
        }
        result["peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
        return result
    finally:
        del engine
        torch.cuda.empty_cache()


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
        instance_id = _aws_instance_id()

        import torch
        import vllm

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
            "runtime": {
                "model": args.model,
                "revision": args.revision,
                "cuda_name": properties.name,
                "cuda_total_memory_bytes": properties.total_memory,
                "torch_version": torch.__version__,
                "vllm_version": vllm.__version__,
            },
            "rungs": {
                rung: _measure_rung(
                    model=args.model,
                    revision=args.revision,
                    rung=rung,
                    torch=torch,
                    vllm=vllm,
                )
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

"""Measure the preregistered one-L40S p10 without running benchmark tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time


SAMPLES = 10
TOKENS = 128
WARMUPS = 1


def _prompt(index: int) -> str:
    return (
        "You are executing a sealed infrastructure qualification, not a benchmark. "
        f"Qualification nonce {index:02d}. In one compact paragraph, explain why raw "
        "timing observations must be retained beside a reported percentile."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--rung", choices=("l40s-tp1-32768", "l40s-tp1-65536"), required=True)
    parser.add_argument("--max-model-len", choices=(32768, 65536), type=int, required=True)
    args = parser.parse_args()
    expected_length = 32768 if args.rung.endswith("32768") else 65536
    if args.max_model_len != expected_length:
        raise ValueError("rung and max-model-len disagree")

    import torch
    import vllm
    from vllm import LLM, SamplingParams

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("qualification requires exactly one CUDA device")
    torch.cuda.reset_peak_memory_stats()
    initialized_at = time.monotonic()
    engine = LLM(
        model=args.model,
        tokenizer=args.model,
        trust_remote_code=False,
        max_model_len=args.max_model_len,
        max_num_seqs=1,
        gpu_memory_utilization=0.90,
        enforce_eager=True,
        tensor_parallel_size=1,
    )
    initialization_seconds = time.monotonic() - initialized_at
    params = SamplingParams(
        temperature=0.0,
        seed=0,
        max_tokens=TOKENS,
        min_tokens=TOKENS,
        ignore_eos=True,
    )

    engine.generate([_prompt(-1)], params, use_tqdm=False)
    observations = []
    for index in range(SAMPLES):
        started = time.monotonic_ns()
        output = engine.generate([_prompt(index)], params, use_tqdm=False)[0].outputs[0]
        finished = time.monotonic_ns()
        elapsed = (finished - started) / 1_000_000_000
        generated = len(output.token_ids)
        if generated != TOKENS:
            raise RuntimeError(f"sample {index} generated {generated}, expected {TOKENS}")
        observations.append(
            {
                "index": index,
                "elapsed_seconds": elapsed,
                "generated_tokens": generated,
                "output_tokens_per_second": generated / elapsed,
                "token_ids_sha256": hashlib.sha256(
                    json.dumps(list(output.token_ids), separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
            }
        )
    rates = sorted(item["output_tokens_per_second"] for item in observations)
    p10 = rates[math.ceil(0.10 * len(rates)) - 1]
    receipt = {
        "record_kind": "step5b_throughput_observation",
        "schema_version": "0.1.0",
        "rung": args.rung,
        "model_path": args.model,
        "max_model_len": args.max_model_len,
        "p10_method": "nearest_rank",
        "warmup_samples": WARMUPS,
        "output_tokens_per_sample": TOKENS,
        "output_tokens_per_second": [item["output_tokens_per_second"] for item in observations],
        "p10_output_tokens_per_second": p10,
        "samples": observations,
        "initialization_seconds": initialization_seconds,
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "cuda_name": torch.cuda.get_device_name(0),
        "torch_version": torch.__version__,
        "vllm_version": vllm.__version__,
    }
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

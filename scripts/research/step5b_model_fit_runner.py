"""Run one receipt-bound local-model vLLM fit and throughput qualification."""

from __future__ import annotations

import argparse
import json
import time


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--role", choices=("subject", "simulator"), required=True)
    parser.add_argument("--max-model-len", type=int, required=True)
    parser.add_argument("--max-tokens", type=int, default=128)
    args = parser.parse_args()

    import torch
    import vllm
    from vllm import LLM, SamplingParams

    if torch.cuda.device_count() != 1 or not torch.cuda.is_available():
        raise RuntimeError("qualification requires exactly one CUDA device")
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
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
    initialized = time.monotonic()
    prompt = (
        "You are a deterministic qualification worker. Explain in one compact paragraph why "
        "immutable inputs and isolated sandboxes matter for reproducible agent evaluation."
    )
    outputs = engine.generate(
        [prompt], SamplingParams(temperature=0.0, max_tokens=args.max_tokens)
    )
    finished = time.monotonic()
    token_ids = outputs[0].outputs[0].token_ids
    generated = len(token_ids)
    generation_seconds = finished - initialized
    result = {
        "record_kind": "step5b_model_fit_observation",
        "schema_version": "0.1.0",
        "role": args.role,
        "model_path": args.model,
        "max_model_len": args.max_model_len,
        "generated_tokens": generated,
        "output_text": outputs[0].outputs[0].text,
        "initialization_seconds": initialized - started,
        "generation_seconds": generation_seconds,
        "output_tokens_per_second": generated / generation_seconds,
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "cuda_name": torch.cuda.get_device_name(0),
        "torch_version": torch.__version__,
        "vllm_version": vllm.__version__,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

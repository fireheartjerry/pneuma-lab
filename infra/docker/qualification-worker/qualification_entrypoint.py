"""Fail-closed entrypoint for the bounded single-L40S qualification worker."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time


def inspect() -> int:
    import torch
    import vllm

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    properties = torch.cuda.get_device_properties(0)
    if torch.cuda.device_count() != 1:
        raise RuntimeError(f"expected exactly one GPU, found {torch.cuda.device_count()}")
    print(
        json.dumps(
            {
                "cuda_device_count": torch.cuda.device_count(),
                "cuda_name": properties.name,
                "cuda_total_memory_bytes": properties.total_memory,
                "torch_version": torch.__version__,
                "vllm_version": vllm.__version__,
                "subject_model": os.environ["PNEUMA_SUBJECT_MODEL"],
                "subject_revision": os.environ["PNEUMA_SUBJECT_REVISION"],
                "simulator_model": os.environ["PNEUMA_SIMULATOR_MODEL"],
                "simulator_revision": os.environ["PNEUMA_SIMULATOR_REVISION"],
            },
            sort_keys=True,
        )
    )
    return 0


def smoke(model: str, revision: str, max_model_len: int) -> int:
    from vllm import LLM, SamplingParams

    started = time.monotonic()
    engine = LLM(
        model=model,
        revision=revision,
        tokenizer_revision=revision,
        trust_remote_code=False,
        max_model_len=max_model_len,
        max_num_seqs=1,
        gpu_memory_utilization=0.90,
        enforce_eager=True,
    )
    outputs = engine.generate(
        ["Return exactly the token OK."],
        SamplingParams(temperature=0.0, max_tokens=8),
    )
    elapsed = time.monotonic() - started
    text = outputs[0].outputs[0].text
    tokens = len(outputs[0].outputs[0].token_ids)
    print(json.dumps({"elapsed_seconds": elapsed, "generated_tokens": tokens, "output": text}))
    return 0


def serve(model: str, revision: str, max_model_len: int) -> int:
    command = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        model,
        "--revision",
        revision,
        "--tokenizer-revision",
        revision,
        "--max-model-len",
        str(max_model_len),
        "--gpu-memory-utilization",
        "0.90",
        "--max-num-seqs",
        "1",
        "--reasoning-parser",
        "qwen3",
        "--tool-call-parser",
        "qwen3_coder",
        "--enable-auto-tool-choice",
    ]
    return subprocess.call(command)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("inspect", "smoke-subject", "smoke-simulator", "serve-subject", "serve-simulator"))
    parser.add_argument("--max-model-len", type=int, default=32768)
    args = parser.parse_args()
    if args.mode == "inspect":
        return inspect()
    subject = "subject" in args.mode
    model = os.environ["PNEUMA_SUBJECT_MODEL" if subject else "PNEUMA_SIMULATOR_MODEL"]
    revision = os.environ["PNEUMA_SUBJECT_REVISION" if subject else "PNEUMA_SIMULATOR_REVISION"]
    if args.mode.startswith("smoke-"):
        return smoke(model, revision, args.max_model_len)
    return serve(model, revision, args.max_model_len)


if __name__ == "__main__":
    raise SystemExit(main())

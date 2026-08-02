"""Derive admission summaries from retained per-worker raw observations.

The cloud admission compiler must not accept a self-reported percentile or
passing-case count. This module is deliberately provider-free: it verifies the
evidence shape recorded by a worker and derives the only summary values the
typed admission receipt is allowed to carry.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .errors import CloudManifestError
from .throughput import (
    OUTPUT_TOKENS_PER_SAMPLE,
    P10_METHOD,
    THROUGHPUT_SAMPLES_PER_RUNG,
    WARMUP_SAMPLES_PER_RUNG,
    nearest_rank_p10,
)


USABLE_GPU_MEMORY_BYTES = 44 * 1024**3

# These cases exercise a real structured function-call path, but contain no
# benchmark task, repository state, private input, or efficacy outcome. They
# are code-bound qualification fixtures, not a scientific workload.
TOOL_CALL_FIXTURES: dict[str, tuple[str, dict[str, object]]] = {
    "admission-add": ("qualification_add", {"left": 2, "right": 3}),
    "admission-echo": ("qualification_echo", {"text": "pneuma-admission"}),
    "admission-lookup": ("qualification_lookup", {"key": "runtime"}),
    "admission-status": ("qualification_status", {"component": "worker"}),
}

OUTPUT_PARITY_FIXTURE_IDS = (
    "admission-parity-0",
    "admission-parity-1",
    "admission-parity-2",
    "admission-parity-3",
)


def _require_exact_fixture_ids(
    observations: Sequence[Mapping[str, Any]], expected: Sequence[str], *, label: str
) -> None:
    actual = [item.get("fixture_id") for item in observations]
    if actual != list(expected):
        raise CloudManifestError(
            f"{label} fixture order or coverage does not match the frozen probe"
        )


def _require_finite_positive(value: Any, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CloudManifestError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise CloudManifestError(f"{label} must be finite and positive")
    return result


def _derive_tool_call_cases(observations: Sequence[Mapping[str, Any]]) -> tuple[int, int]:
    _require_exact_fixture_ids(observations, tuple(TOOL_CALL_FIXTURES), label="tool-call")
    passed = 0
    for observation in observations:
        expected_name, expected_arguments = TOOL_CALL_FIXTURES[observation["fixture_id"]]
        parsed = parse_tool_call_text(observation["raw_response_text"])
        if parsed["name"] != observation["name"] or parsed["arguments"] != observation["arguments"]:
            continue
        if parsed["name"] != expected_name:
            continue
        if parsed["arguments"] != expected_arguments:
            continue
        passed += 1
    return len(observations), passed


def _derive_output_parity_cases(observations: Sequence[Mapping[str, Any]]) -> tuple[int, int]:
    _require_exact_fixture_ids(observations, OUTPUT_PARITY_FIXTURE_IDS, label="output-parity")
    passed = sum(
        1
        for observation in observations
        if observation["first_output_token_ids"] == observation["second_output_token_ids"]
    )
    return len(observations), passed


def summarize_rung(rung: Mapping[str, Any]) -> dict[str, float | int]:
    """Recompute a receipt-ready rung summary from its complete raw evidence."""

    peak_bytes = rung["peak_allocated_bytes"]
    if isinstance(peak_bytes, bool) or not isinstance(peak_bytes, int) or peak_bytes < 0:
        raise CloudManifestError("peak allocated GPU memory must be a non-negative integer")
    if peak_bytes > USABLE_GPU_MEMORY_BYTES:
        raise CloudManifestError("raw worker measurement exceeds the 44 GiB usable GPU boundary")

    throughput = rung["throughput"]
    if throughput["p10_method"] != P10_METHOD:
        raise CloudManifestError("raw worker measurement uses an unregistered p10 method")
    if throughput["warmup_samples"] != WARMUP_SAMPLES_PER_RUNG:
        raise CloudManifestError("raw worker measurement has the wrong warmup count")
    if throughput["output_tokens_per_sample"] != OUTPUT_TOKENS_PER_SAMPLE:
        raise CloudManifestError("raw worker measurement has the wrong output token count")
    samples = throughput["samples"]
    if len(samples) != THROUGHPUT_SAMPLES_PER_RUNG:
        raise CloudManifestError("raw worker measurement must retain exactly ten throughput samples")
    rates: list[float] = []
    for index, sample in enumerate(samples):
        if sample["index"] != index:
            raise CloudManifestError("raw worker throughput sample indexes must be canonical")
        if sample["generated_tokens"] != OUTPUT_TOKENS_PER_SAMPLE:
            raise CloudManifestError("raw worker throughput sample has the wrong token count")
        elapsed = _require_finite_positive(
            sample["elapsed_seconds"], label="raw worker throughput elapsed time"
        )
        rates.append(OUTPUT_TOKENS_PER_SAMPLE / elapsed)

    tool_cases, tool_passes = _derive_tool_call_cases(rung["tool_calls"])
    parity_cases, parity_passes = _derive_output_parity_cases(rung["output_parity"])
    return {
        "peak_gpu_memory_gib": peak_bytes / 1024**3,
        "p10_output_tokens_per_second": nearest_rank_p10(rates),
        "tool_call_cases": tool_cases,
        "tool_call_passes": tool_passes,
        "output_parity_cases": parity_cases,
        "output_parity_passes": parity_passes,
    }


def require_l40s_runtime(runtime: Mapping[str, Any]) -> None:
    """Refuse a raw admission record from a non-L40S or undersized device."""

    cuda_name = runtime["cuda_name"]
    total_memory = runtime["cuda_total_memory_bytes"]
    if not isinstance(cuda_name, str) or "L40S" not in cuda_name:
        raise CloudManifestError("raw worker measurement is not from an L40S runtime")
    if isinstance(total_memory, bool) or not isinstance(total_memory, int):
        raise CloudManifestError("raw worker measurement has invalid CUDA memory")
    if total_memory < USABLE_GPU_MEMORY_BYTES:
        raise CloudManifestError("raw worker measurement has less than 44 GiB usable device memory")


def canonical_tool_call(name: str, arguments: Mapping[str, object]) -> dict[str, object]:
    """Normalize a parsed function call before retaining it as evidence."""

    if not isinstance(name, str) or not name:
        raise CloudManifestError("tool-call evidence has no function name")
    if not isinstance(arguments, Mapping):
        raise CloudManifestError("tool-call evidence has non-object function arguments")
    # JSON round-tripping proves values are plain, portable JSON before a raw
    # evidence file is written by the GPU-side probe.
    return {"name": name, "arguments": json.loads(json.dumps(dict(arguments), sort_keys=True))}


def parse_tool_call_text(raw_response_text: str) -> dict[str, object]:
    """Parse the exact one-call JSON emitted by the fixed qualification fixture."""

    if not isinstance(raw_response_text, str) or not raw_response_text.strip():
        raise CloudManifestError("tool-call evidence has no raw response text")
    text = raw_response_text.strip()
    match = re.fullmatch(r"<tool_call>\s*(.*?)\s*</tool_call>", text, flags=re.DOTALL)
    if match:
        text = match.group(1)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CloudManifestError("tool-call evidence is not valid JSON") from exc
    if isinstance(value, list):
        if len(value) != 1:
            raise CloudManifestError("tool-call evidence must contain exactly one call")
        value = value[0]
    if not isinstance(value, Mapping):
        raise CloudManifestError("tool-call evidence must be an object")
    function = value.get("function", value)
    if not isinstance(function, Mapping):
        raise CloudManifestError("tool-call evidence has malformed function data")
    arguments = function.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise CloudManifestError("tool-call evidence has non-JSON arguments") from exc
    return canonical_tool_call(function.get("name"), arguments)

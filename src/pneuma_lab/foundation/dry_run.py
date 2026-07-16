"""Offline no-gradient dry run over the verified pinned 2B snapshot.

The dry run proves the launch gates without ever constructing an optimizer,
calling backward, or touching the network: receipt-bound snapshot
verification, junction-disabled numerical parity across the required cache
boundaries, the pinned junction contract (latent width 256, 64 memory slots,
two candidates, four total microsteps, one layer-19 junction), a p95 latency
budget, and an analytic FLOPs budget. Torch and transformers are imported
lazily so this module stays importable on machines without the foundation
extra.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import time
from typing import Callable, Mapping

from pneuma_lab.foundation.artifacts import write_atomic_json
from pneuma_lab.foundation.model_cache import verify_pinned_snapshot
from pneuma_lab.foundation.runtime import (
    CacheBoundary,
    cache_for_boundary,
    load_local_qwen,
)
from pneuma_lab.foundation.specs import CORE_LIMITS


_REPORT_NAME = "dry-run-report.json"
_WARMUP_FORWARDS = 5
_TIMED_FORWARDS = 20
_PARITY_ATOL = 1e-5
_PARITY_RTOL = 1e-5
_REQUIRED_PRIMARY_LAYER = 19
_SYNTHETIC_TEXT = "Predict whether this synthetic local action succeeds."
_REQUIRED_CASES = (
    ("fresh", CacheBoundary.NEW_DOCUMENT, "Fix the failing local test."),
    ("cached", CacheBoundary.TOOL_TICK, "Inspect the next tool observation."),
    ("packed_reset", CacheBoundary.NEW_DOCUMENT, "Start a distinct repository task."),
    ("explicit_reset", CacheBoundary.EXPLICIT_RESET, "Reset all recurrent state."),
    ("continued", CacheBoundary.TOOL_TICK, "Continue only this tool tick."),
)


class DryRunError(Exception):
    """Raised when the no-gradient dry run cannot prove its launch gates."""


@dataclass(frozen=True)
class DryRunRequest:
    model_key: str
    cache_root: Path
    output_root: Path
    stage: str


def estimate_junction_flops(
    *,
    sequence_length: int,
    hidden_size: int,
    latent_width: int,
    candidate_plans: int,
    total_microsteps: int,
    memory_slots: int,
) -> int:
    """Analytic per-forward FLOPs added by one pooled junction pass."""

    values = (
        sequence_length,
        hidden_size,
        latent_width,
        candidate_plans,
        total_microsteps,
        memory_slots,
    )
    if any(type(value) is not int or value <= 0 for value in values):
        raise DryRunError("junction FLOP inputs must be positive integers")
    pooling = sequence_length * hidden_size
    down_projection = 2 * hidden_size * latent_width
    candidate_projection = 2 * latent_width * latent_width * candidate_plans
    candidate_scores = 2 * latent_width * candidate_plans
    candidate_blend = 2 * latent_width * candidate_plans
    memory_queries = 2 * latent_width * latent_width * (total_microsteps + 1)
    memory_attention = 2 * (2 * latent_width * memory_slots) * total_microsteps
    recurrence = 2 * 3 * (2 * latent_width * latent_width) * total_microsteps
    up_projection = 2 * latent_width * hidden_size
    residual = sequence_length * hidden_size
    return (
        pooling
        + down_projection
        + candidate_projection
        + candidate_scores
        + candidate_blend
        + memory_queries
        + memory_attention
        + recurrence
        + up_projection
        + residual
    )


def estimate_base_forward_flops(
    *,
    parameter_count: int,
    sequence_length: int,
) -> int:
    """Standard dense-forward estimate: two FLOPs per parameter per token."""

    if type(parameter_count) is not int or parameter_count < 0:
        raise DryRunError("parameter count must be a non-negative integer")
    if type(sequence_length) is not int or sequence_length <= 0:
        raise DryRunError("sequence length must be a positive integer")
    return 2 * parameter_count * sequence_length


def percentile_95(samples) -> float:
    values = sorted(float(value) for value in samples)
    if not values:
        raise DryRunError("p95 requires at least one timing sample")
    return values[math.ceil(0.95 * len(values)) - 1]


def enforce_latency_budget(
    *,
    enabled_p95: float,
    disabled_p95: float,
    limit: float = CORE_LIMITS.max_p95_latency_overhead,
) -> float:
    if disabled_p95 <= 0.0:
        raise DryRunError("disabled-core p95 latency must be positive")
    overhead = enabled_p95 / disabled_p95 - 1.0
    if overhead > limit:
        raise DryRunError(
            f"enabled-core p95 latency overhead {overhead:.4f} exceeds "
            f"the {limit:.2f} limit"
        )
    return overhead


def enforce_flops_budget(
    *,
    additional_flops: int,
    base_flops: int,
    limit: float = CORE_LIMITS.max_flops_overhead,
) -> float:
    if base_flops <= 0:
        raise DryRunError("base forward FLOP estimate must be positive")
    overhead = additional_flops / base_flops
    if overhead > limit:
        raise DryRunError(
            f"estimated additional FLOP overhead {overhead:.4f} exceeds "
            f"the {limit:.2f} limit"
        )
    return overhead


def build_required_cache_cases(tokenizer) -> tuple:
    """Tokenize the five required cache-boundary cases in execution order."""

    return tuple(
        (name, boundary, tokenizer(text, return_tensors="pt"))
        for name, boundary, text in _REQUIRED_CASES
    )


def capture_case_outputs(model, cases) -> dict:
    """Run the boundary cases sequentially, honoring native cache continuity."""

    outputs = {}
    cache = None
    device = next(model.parameters()).device
    for name, boundary, model_inputs in cases:
        cache = cache_for_boundary(cache, boundary)
        prepared = {key: value.to(device) for key, value in model_inputs.items()}
        result = model(**prepared, past_key_values=cache, use_cache=True)
        outputs[name] = result.logits.detach().cpu()
        cache = result.past_key_values
    return outputs


def compare_captured_outputs(reference: Mapping, modified: Mapping) -> dict:
    import torch

    if set(reference) != set(modified):
        raise DryRunError("parity case sets differ")
    maximum = 0.0
    for name in sorted(reference):
        torch.testing.assert_close(
            reference[name],
            modified[name],
            atol=_PARITY_ATOL,
            rtol=_PARITY_RTOL,
        )
        maximum = max(
            maximum,
            float((reference[name] - modified[name]).abs().max().item()),
        )
    return {"case_names": sorted(reference), "max_absolute_error": maximum}


def _synthetic_inputs(model, tokenizer) -> dict:
    device = next(model.parameters()).device
    inputs = {
        key: value.to(device)
        for key, value in tokenizer(_SYNTHETIC_TEXT, return_tensors="pt").items()
    }
    if "input_ids" not in inputs:
        raise DryRunError("the synthetic record must tokenize to input_ids")
    return inputs


def run_one_synthetic_forward(model, tokenizer):
    """One forward over one synthetic, non-corpus record with caching off."""

    return model(**_synthetic_inputs(model, tokenizer), use_cache=False)


def _no_synchronize() -> None:
    return None


def _time_forwards(forward: Callable, *, clock: Callable, synchronize: Callable):
    for _ in range(_WARMUP_FORWARDS):
        forward()
    synchronize()
    durations = []
    for _ in range(_TIMED_FORWARDS):
        start = clock()
        forward()
        synchronize()
        durations.append(clock() - start)
    return tuple(durations)


def _verify_installed_contract(installed) -> dict:
    core = installed.shared_core
    checks = (
        (
            core.latent_width == CORE_LIMITS.latent_width,
            f"latent width must be {CORE_LIMITS.latent_width}",
        ),
        (
            core.memory_slots == CORE_LIMITS.memory_slots,
            f"active memory slots must be {CORE_LIMITS.memory_slots}",
        ),
        (
            core.candidate_plans == CORE_LIMITS.candidate_plans,
            f"candidate plans must be {CORE_LIMITS.candidate_plans}",
        ),
        (
            installed.total_microsteps == CORE_LIMITS.total_microsteps,
            f"total microsteps must be {CORE_LIMITS.total_microsteps}",
        ),
        (
            installed.layer_indices == (_REQUIRED_PRIMARY_LAYER,),
            f"exactly one junction at layer {_REQUIRED_PRIMARY_LAYER} is required",
        ),
    )
    for passed, message in checks:
        if not passed:
            raise DryRunError(f"junction contract violated: {message}")
    return {
        "latent_width": core.latent_width,
        "memory_slots": core.memory_slots,
        "candidate_plans": core.candidate_plans,
        "total_microsteps": installed.total_microsteps,
        "layer_indices": list(installed.layer_indices),
    }


def _validate_request(request: DryRunRequest) -> None:
    if request.model_key != "2b":
        raise DryRunError("the no-gradient dry run supports only the pinned 2b model")
    if not isinstance(request.stage, str) or not request.stage:
        raise DryRunError("dry-run stage must be a non-empty string")


def run_no_gradient_dry_run(
    request: DryRunRequest,
    *,
    runtime_loader: Callable = load_local_qwen,
    tokenizer_loader: Callable | None = None,
    optimizer_factory: Callable | None = None,
    clock: Callable | None = None,
    synchronize: Callable | None = None,
) -> dict:
    """Prove the launch gates offline; the optimizer factory is never called."""

    del optimizer_factory  # Accepted for symmetry with training; never invoked.
    try:
        import torch
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise DryRunError(
            "the no-gradient dry run requires the foundation torch extra"
        ) from exc
    from pneuma_lab.foundation.integration import CoreDisabled, install_junctions

    _validate_request(request)
    cached = verify_pinned_snapshot(request.model_key, cache_root=request.cache_root)
    if tokenizer_loader is None:
        try:
            from transformers import AutoTokenizer
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise DryRunError(
                "the no-gradient dry run requires the transformers extra"
            ) from exc
        tokenizer_loader = AutoTokenizer.from_pretrained
    tokenizer = tokenizer_loader(cached.snapshot_path, local_files_only=True)
    clock = clock or time.perf_counter
    if synchronize is None:
        synchronize = (
            torch.cuda.synchronize if torch.cuda.is_available() else _no_synchronize
        )

    runtime = runtime_loader(
        request.model_key,
        allow_download=False,
        vision=False,
        snapshot_path=cached.snapshot_path,
    )
    base_parameter_count = sum(
        parameter.numel() for parameter in runtime.model.parameters()
    )
    cases = build_required_cache_cases(tokenizer)
    with torch.inference_mode():
        reference_outputs = capture_case_outputs(runtime.model, cases)
    installed = install_junctions(runtime.model, runtime.architecture_plan)
    junction_contract = _verify_installed_contract(installed)
    with torch.inference_mode():
        with CoreDisabled(installed):
            disabled_outputs = capture_case_outputs(runtime.model, cases)
        try:
            parity = compare_captured_outputs(reference_outputs, disabled_outputs)
        except AssertionError as exc:
            raise DryRunError(f"junction-disabled parity failed: {exc}") from exc
        output = run_one_synthetic_forward(runtime.model, tokenizer)
        timed_inputs = _synthetic_inputs(runtime.model, tokenizer)

        def forward() -> None:
            runtime.model(**timed_inputs, use_cache=False)

        with CoreDisabled(installed):
            disabled_durations = _time_forwards(
                forward,
                clock=clock,
                synchronize=synchronize,
            )
        enabled_durations = _time_forwards(
            forward,
            clock=clock,
            synchronize=synchronize,
        )

    disabled_p95 = percentile_95(disabled_durations)
    enabled_p95 = percentile_95(enabled_durations)
    latency_overhead = enforce_latency_budget(
        enabled_p95=enabled_p95,
        disabled_p95=disabled_p95,
    )
    sequence_length = int(timed_inputs["input_ids"].shape[-1])
    additional_flops = estimate_junction_flops(
        sequence_length=sequence_length,
        hidden_size=runtime.architecture_plan.hidden_size,
        latent_width=CORE_LIMITS.latent_width,
        candidate_plans=CORE_LIMITS.candidate_plans,
        total_microsteps=CORE_LIMITS.total_microsteps,
        memory_slots=CORE_LIMITS.memory_slots,
    )
    base_flops = estimate_base_forward_flops(
        parameter_count=base_parameter_count,
        sequence_length=sequence_length,
    )
    flops_overhead = enforce_flops_budget(
        additional_flops=additional_flops,
        base_flops=base_flops,
    )

    report = {
        "report_kind": "pneuma_foundation_no_gradient_dry_run",
        "report_schema_version": "0.1.0",
        "model_key": request.model_key,
        "stage": request.stage,
        "model_revision": cached.revision,
        "parity": parity,
        "output_shape": [int(value) for value in output.logits.shape],
        "optimizer_constructed": False,
        "backward_called": False,
        "gradient_tensor_count": sum(
            parameter.grad is not None for parameter in runtime.model.parameters()
        ),
        "junction": junction_contract,
        "latency": {
            "warmup_forwards": _WARMUP_FORWARDS,
            "timed_forwards": _TIMED_FORWARDS,
            "disabled_p95_seconds": disabled_p95,
            "enabled_p95_seconds": enabled_p95,
            "overhead_fraction": latency_overhead,
            "limit_fraction": CORE_LIMITS.max_p95_latency_overhead,
        },
        "flops": {
            "sequence_length": sequence_length,
            "base_forward_estimate": base_flops,
            "additional_estimate": additional_flops,
            "overhead_fraction": flops_overhead,
            "limit_fraction": CORE_LIMITS.max_flops_overhead,
        },
    }
    write_atomic_json(Path(request.output_root) / _REPORT_NAME, report)
    return report


__all__ = [
    "DryRunError",
    "DryRunRequest",
    "build_required_cache_cases",
    "capture_case_outputs",
    "compare_captured_outputs",
    "enforce_flops_budget",
    "enforce_latency_budget",
    "estimate_base_forward_flops",
    "estimate_junction_flops",
    "percentile_95",
    "run_no_gradient_dry_run",
    "run_one_synthetic_forward",
]

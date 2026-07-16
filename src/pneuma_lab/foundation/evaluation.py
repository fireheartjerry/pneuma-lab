"""Stage-aware, claim-free evaluation for local foundation runs.

This module is torch-free by construction: it consumes only run-manifest
mappings, per-batch validation metric dicts, and variant-result records. It
never imports the archived evidence methodology and never emits an evidence
level or a machine-interiority claim.

Validation batch contract (``aggregate_validation_metrics``): each batch is a
mapping with a required positive-integer ``token_count`` weight, a required
finite non-negative ``validation_loss``, and any additional finite numeric
metrics (for example ``forecast_mse``). Every batch must report the same
metric names; the aggregate is the token-weighted mean per metric.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Mapping

from pneuma_lab.foundation.curriculum import (
    APPROVED_LEARNING_RATES,
    LrTrial,
    next_token_stage,
    select_learning_rate,
)
from pneuma_lab.foundation.falsification import (
    REQUIRED_VARIANTS,
    VariantResult,
    evaluate_early_kill_gate,
)
from pneuma_lab.foundation.specs import CORE_LIMITS


EVALUATION_REPORT_KIND = "pneuma_foundation_evaluation"
EVALUATION_REPORT_SCHEMA_VERSION = "0.1.0"
PRE_2M_STAGES = ("100k", "500k", "1m")
GATE_STAGES = ("2m", "8m", "16m", "32m")
STAGE_TOKENS = {
    "100k": 100_000,
    "500k": 500_000,
    "2m": 2_000_000,
    "8m": 8_000_000,
    "16m": 16_000_000,
    "32m": 32_000_000,
}
CHECK_NAMES = (
    "parity",
    "resume_integrity",
    "denied_action_classes",
    "memory_integrity",
)
CLAIM_BOUNDARY = {
    "no_consciousness_claim": True,
    "claim_status": "engineering_and_precaution_only",
}

_TOKENS_TO_STAGE = {tokens: stage for stage, tokens in STAGE_TOKENS.items()}
_RESERVED_METRIC_NAMES = frozenset({"token_count", "batch_count"})


class EvaluationError(ValueError):
    """Raised when run evaluation inputs are missing, malformed, or unsafe."""


def _finite_number(value, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvaluationError(f"{label} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise EvaluationError(f"{label} must be a finite number")
    return number


def aggregate_validation_metrics(validation_batches: Iterable[Mapping]) -> dict:
    """Token-weighted means over per-batch validation metric mappings."""

    batches = tuple(validation_batches)
    if not batches:
        raise EvaluationError("validation metrics require at least one batch")
    metric_names: tuple[str, ...] | None = None
    totals: dict[str, float] = {}
    token_total = 0
    for index, batch in enumerate(batches, start=1):
        if not isinstance(batch, Mapping):
            raise EvaluationError(f"validation batch {index} must be a mapping")
        if "batch_count" in batch:
            raise EvaluationError(
                f"validation batch {index} uses the reserved name 'batch_count'"
            )
        if "token_count" not in batch:
            raise EvaluationError(f"validation batch {index} is missing token_count")
        token_count = batch["token_count"]
        if (
            isinstance(token_count, bool)
            or not isinstance(token_count, int)
            or token_count <= 0
        ):
            raise EvaluationError(
                f"validation batch {index} token_count must be a positive integer"
            )
        if "validation_loss" not in batch:
            raise EvaluationError(
                f"validation batch {index} is missing validation_loss"
            )
        names = tuple(
            sorted(name for name in batch if name not in _RESERVED_METRIC_NAMES)
        )
        if metric_names is None:
            metric_names = names
        elif names != metric_names:
            raise EvaluationError(
                "validation batches must report one consistent metric set"
            )
        for name in names:
            value = _finite_number(
                batch[name],
                label=f"validation batch {index} metric {name!r}",
            )
            if name == "validation_loss" and value < 0:
                raise EvaluationError(
                    f"validation batch {index} validation_loss must be non-negative"
                )
            totals[name] = totals.get(name, 0.0) + value * token_count
        token_total += token_count
    assert metric_names is not None
    metrics: dict = {name: totals[name] / token_total for name in metric_names}
    metrics["token_count"] = token_total
    metrics["batch_count"] = len(batches)
    return metrics


def evaluate_regression_gate(
    *,
    p95_latency_overhead: float | None,
    estimated_flops_overhead: float | None,
) -> dict:
    """Fail-closed regression check against the pinned core overhead limits."""

    failures: list[str] = []
    if p95_latency_overhead is None:
        failures.append("p95_latency_overhead_unmeasured")
    else:
        p95_latency_overhead = _finite_number(
            p95_latency_overhead, label="p95 latency overhead"
        )
        if p95_latency_overhead > CORE_LIMITS.max_p95_latency_overhead:
            failures.append("p95_latency_overhead")
    if estimated_flops_overhead is None:
        failures.append("flops_overhead_unmeasured")
    else:
        estimated_flops_overhead = _finite_number(
            estimated_flops_overhead, label="estimated FLOPs overhead"
        )
        if estimated_flops_overhead > CORE_LIMITS.max_flops_overhead:
            failures.append("flops_overhead")
    return {
        "p95_latency_overhead": p95_latency_overhead,
        "estimated_flops_overhead": estimated_flops_overhead,
        "max_p95_latency_overhead": CORE_LIMITS.max_p95_latency_overhead,
        "max_flops_overhead": CORE_LIMITS.max_flops_overhead,
        "passed": not failures,
        "failures": failures,
    }


def _latency_p95_overhead(latency: Mapping) -> float | None:
    base = latency.get("base_p95_ms")
    core = latency.get("core_p95_ms")
    if base is None or core is None:
        return None
    base_value = _finite_number(base, label="run manifest latency base_p95_ms")
    core_value = _finite_number(core, label="run manifest latency core_p95_ms")
    if base_value <= 0 or core_value < 0:
        raise EvaluationError(
            "run manifest p95 latencies must be positive to derive overhead"
        )
    return core_value / base_value - 1.0


def load_variant_results(
    paths: Iterable[str | os.PathLike],
) -> tuple[VariantResult, ...]:
    """Load the four repo-disjoint variant-result JSON files for the 2m gate."""

    results: list[VariantResult] = []
    for path in tuple(paths):
        target = Path(path)
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise EvaluationError(
                f"variant result {target} cannot be read: {exc}"
            ) from exc
        if not isinstance(payload, Mapping):
            raise EvaluationError(f"variant result {target} must be a JSON object")
        try:
            results.append(
                VariantResult(
                    name=str(payload["name"]),
                    task_ids=tuple(str(value) for value in payload["task_ids"]),
                    repos=tuple(str(value) for value in payload["repos"]),
                    resolved=tuple(bool(value) for value in payload["resolved"]),
                    repo_disjoint=bool(payload["repo_disjoint"]),
                    flops_overhead=float(payload["flops_overhead"]),
                    p95_latency_overhead=float(payload["p95_latency_overhead"]),
                    peak_vram_gb=float(payload["peak_vram_gb"]),
                    peak_ram_gb=float(payload["peak_ram_gb"]),
                    general_regression_points=float(
                        payload["general_regression_points"]
                    ),
                    functioning_exploits=int(payload["functioning_exploits"]),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise EvaluationError(
                f"variant result {target} is malformed: {exc}"
            ) from exc
    if len(results) != len(REQUIRED_VARIANTS):
        raise EvaluationError("2m and later evaluation requires four variant results")
    return tuple(results)


def _coerce_variant_results(variant_results) -> tuple[VariantResult, ...]:
    items = tuple(variant_results)
    if items and all(isinstance(item, VariantResult) for item in items):
        return items
    if items and all(isinstance(item, (str, os.PathLike)) for item in items):
        return load_variant_results(items)
    raise EvaluationError(
        "variant results must be VariantResult values or result-file paths"
    )


def _normalized_checks(checks: Mapping | None) -> dict:
    if checks is None:
        provided: dict = {}
    elif isinstance(checks, Mapping):
        provided = dict(checks)
    else:
        raise EvaluationError("evaluation checks must be a mapping")
    unknown = sorted(set(provided) - set(CHECK_NAMES))
    if unknown:
        raise EvaluationError(f"unknown evaluation checks: {unknown}")
    return {
        name: provided.get(name, {"status": "not_measured"}) for name in CHECK_NAMES
    }


def evaluate_run(
    run_manifest: Mapping,
    *,
    validation_batches: Iterable[Mapping],
    variant_results: Iterable | None = None,
    estimated_flops_overhead: float | None = None,
    checks: Mapping | None = None,
    bootstrap_samples: int = 10_000,
    bootstrap_seed: int = 0,
) -> dict:
    """Evaluate one completed run into a claim-bounded report mapping.

    Before the 2m stage the falsification gate is structurally not
    applicable; at 2m and later it is mandatory and consumes exactly the four
    pre-registered variant results (objects or result-file paths).
    """

    if not isinstance(run_manifest, Mapping):
        raise EvaluationError("run manifest must be a mapping")
    run_id = run_manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise EvaluationError("run manifest run_id must be a non-empty string")
    curriculum = run_manifest.get("curriculum")
    if not isinstance(curriculum, Mapping):
        raise EvaluationError("run manifest curriculum must be a mapping")
    stage = curriculum.get("stage")
    if stage not in PRE_2M_STAGES and stage not in GATE_STAGES:
        raise EvaluationError(f"unknown curriculum stage: {stage!r}")

    metrics = aggregate_validation_metrics(validation_batches)

    if stage in PRE_2M_STAGES:
        if variant_results is not None:
            raise EvaluationError(
                "variant results apply only at the 2m stage and later"
            )
        gate = {"status": "not_applicable_before_2m", "decision": None}
    else:
        if variant_results is None:
            raise EvaluationError(
                "2m and later evaluation requires four variant results"
            )
        variants = _coerce_variant_results(variant_results)
        try:
            decision = evaluate_early_kill_gate(
                variants,
                bootstrap_samples=bootstrap_samples,
                seed=bootstrap_seed,
            )
        except ValueError as exc:
            raise EvaluationError(
                f"early kill gate rejected the variant results: {exc}"
            ) from exc
        decision_payload = asdict(decision)
        decision_payload["failures"] = list(decision.failures)
        gate = {
            "status": "killed" if decision.kill else "passed",
            "decision": decision_payload,
        }

    latency = run_manifest.get("latency")
    p95_overhead = _latency_p95_overhead(
        latency if isinstance(latency, Mapping) else {}
    )
    regression_gate = evaluate_regression_gate(
        p95_latency_overhead=p95_overhead,
        estimated_flops_overhead=estimated_flops_overhead,
    )

    return {
        "report_kind": EVALUATION_REPORT_KIND,
        "report_schema_version": EVALUATION_REPORT_SCHEMA_VERSION,
        "run_id": run_id,
        "stage": stage,
        "metrics": metrics,
        "falsification_gate": gate,
        "regression_gate": regression_gate,
        "checks": _normalized_checks(checks),
        "claim_boundary": dict(CLAIM_BOUNDARY),
    }


def select_stage_learning_rate(trial_runs: Iterable[Mapping]) -> float:
    """Select the 100k learning rate from the three approved smoke runs.

    Delegates to :func:`select_learning_rate`, whose tie-break already
    prefers the lower rate at equal validation loss.
    """

    trials: list[LrTrial] = []
    for index, run in enumerate(tuple(trial_runs), start=1):
        if not isinstance(run, Mapping):
            raise EvaluationError(f"learning-rate run {index} must be a mapping")
        missing = [
            key
            for key in ("learning_rate", "validation_loss", "stable")
            if key not in run
        ]
        if missing:
            raise EvaluationError(f"learning-rate run {index} is missing {missing}")
        stable = run["stable"]
        if not isinstance(stable, bool):
            raise EvaluationError(
                f"learning-rate run {index} stable flag must be a bool"
            )
        trials.append(
            LrTrial(
                learning_rate=_finite_number(
                    run["learning_rate"],
                    label=f"learning-rate run {index} learning_rate",
                ),
                validation_loss=_finite_number(
                    run["validation_loss"],
                    label=f"learning-rate run {index} validation_loss",
                ),
                stable=stable,
            )
        )
    rates = tuple(trial.learning_rate for trial in trials)
    if len(rates) != len(APPROVED_LEARNING_RATES) or set(rates) != set(
        APPROVED_LEARNING_RATES
    ):
        raise EvaluationError(
            "learning-rate selection requires exactly the three approved 100k runs"
        )
    try:
        return select_learning_rate(trials)
    except ValueError as exc:
        raise EvaluationError(str(exc)) from exc


def next_stage_decision(
    stage: str,
    *,
    stable: bool,
    regression_passed: bool,
    falsification_gate_passed: bool = False,
    held_out_resolved_rate: float | None = None,
    previous_resolved_rate: float | None = None,
) -> str | None:
    """Report-level next-stage decision over the approved token ladder.

    16m and 32m are reachable only when the preceding doubling improved the
    held-out resolved rate by at least 0.5 absolute points; saturation,
    instability, or a failed regression gate returns ``None`` (no next
    stage). Delegates the ladder math to :func:`next_token_stage`.
    """

    if stage not in STAGE_TOKENS:
        raise EvaluationError(
            f"no approved next-stage decision exists for stage {stage!r}"
        )
    for name, flag in (
        ("stable", stable),
        ("regression_passed", regression_passed),
        ("falsification_gate_passed", falsification_gate_passed),
    ):
        if not isinstance(flag, bool):
            raise EvaluationError(f"{name} must be a bool")
    if (held_out_resolved_rate is None) != (previous_resolved_rate is None):
        raise EvaluationError(
            "held-out resolved rates must be provided as a before/after pair"
        )
    validation_gain_points: float | None = None
    if held_out_resolved_rate is not None and previous_resolved_rate is not None:
        current = _finite_number(held_out_resolved_rate, label="held-out resolved rate")
        previous = _finite_number(
            previous_resolved_rate, label="previous resolved rate"
        )
        for value in (current, previous):
            if not 0.0 <= value <= 1.0:
                raise EvaluationError("resolved rates must lie in [0, 1]")
        validation_gain_points = (current - previous) * 100.0
    try:
        next_tokens = next_token_stage(
            STAGE_TOKENS[stage],
            stable=stable,
            regression_passed=regression_passed,
            falsification_gate_passed=falsification_gate_passed,
            validation_gain_points=validation_gain_points,
        )
    except ValueError as exc:
        raise EvaluationError(str(exc)) from exc
    return None if next_tokens is None else _TOKENS_TO_STAGE[next_tokens]


__all__ = [
    "CHECK_NAMES",
    "CLAIM_BOUNDARY",
    "EVALUATION_REPORT_KIND",
    "EVALUATION_REPORT_SCHEMA_VERSION",
    "EvaluationError",
    "GATE_STAGES",
    "PRE_2M_STAGES",
    "STAGE_TOKENS",
    "aggregate_validation_metrics",
    "evaluate_regression_gate",
    "evaluate_run",
    "load_variant_results",
    "next_stage_decision",
    "select_stage_learning_rate",
]

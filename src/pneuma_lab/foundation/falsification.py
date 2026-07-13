"""Pre-registered early-kill decision for the recurrent junction thesis."""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import fmean
from typing import Iterable

from pneuma_lab.foundation.specs import CORE_LIMITS, RUNTIME_LIMITS


REQUIRED_VARIANTS = (
    "untouched_qwen",
    "continued_deltanet",
    "feed_forward_adapter",
    "pneuma_recurrent",
)
MIN_ABSOLUTE_IMPROVEMENT = 0.02
MAX_GENERAL_REGRESSION_POINTS = 1.0


@dataclass(frozen=True)
class VariantResult:
    name: str
    task_ids: tuple[str, ...]
    repos: tuple[str, ...]
    resolved: tuple[bool, ...]
    repo_disjoint: bool
    flops_overhead: float
    p95_latency_overhead: float
    peak_vram_gb: float
    peak_ram_gb: float
    general_regression_points: float
    functioning_exploits: int

    @property
    def resolved_rate(self) -> float:
        return fmean(float(value) for value in self.resolved)


@dataclass(frozen=True)
class FalsificationDecision:
    kill: bool
    strongest_baseline: str
    absolute_improvement: float
    ci95_lower: float
    ci95_upper: float
    failures: tuple[str, ...]


def _paired_bootstrap_ci(
    recurrent: tuple[bool, ...],
    baseline: tuple[bool, ...],
    *,
    samples: int,
    seed: int,
) -> tuple[float, float]:
    if samples < 100:
        raise ValueError("bootstrap_samples must be at least 100")
    if len(recurrent) != len(baseline) or not recurrent:
        raise ValueError("paired resolved outcomes must be non-empty and aligned")
    differences = [
        float(left) - float(right) for left, right in zip(recurrent, baseline)
    ]
    rng = random.Random(seed)
    estimates = []
    for _ in range(samples):
        estimates.append(
            fmean(differences[rng.randrange(len(differences))] for _ in differences)
        )
    estimates.sort()
    lower_index = int(0.025 * (len(estimates) - 1))
    upper_index = int(0.975 * (len(estimates) - 1))
    return estimates[lower_index], estimates[upper_index]


def _validate_variants(results: Iterable[VariantResult]) -> dict[str, VariantResult]:
    mapped = {result.name: result for result in results}
    if set(mapped) != set(REQUIRED_VARIANTS):
        raise ValueError(f"results must contain exactly {REQUIRED_VARIANTS!r}")
    recurrent = mapped["pneuma_recurrent"]
    if not recurrent.task_ids or len(recurrent.task_ids) != len(recurrent.resolved):
        raise ValueError("pneuma_recurrent task_ids and outcomes must align")
    if len(recurrent.repos) != len(recurrent.task_ids):
        raise ValueError("pneuma_recurrent repos and task_ids must align")
    for result in mapped.values():
        if result.task_ids != recurrent.task_ids or result.repos != recurrent.repos:
            raise ValueError("all variants must use the same paired tasks and repos")
        if len(result.resolved) != len(result.task_ids):
            raise ValueError(f"{result.name} outcomes do not align with task_ids")
    return mapped


def evaluate_early_kill_gate(
    results: Iterable[VariantResult],
    *,
    bootstrap_samples: int = 10_000,
    seed: int = 0,
) -> FalsificationDecision:
    """Return a fail-closed promotion decision for the recurrent junction."""

    mapped = _validate_variants(results)
    recurrent = mapped["pneuma_recurrent"]
    # A tie favors the native recurrent incumbent, making Pneuma's gate harder.
    tie_priority = {
        "untouched_qwen": 0,
        "feed_forward_adapter": 1,
        "continued_deltanet": 2,
    }
    baseline = max(
        (mapped[name] for name in REQUIRED_VARIANTS[:-1]),
        key=lambda item: (item.resolved_rate, tie_priority[item.name]),
    )
    improvement = recurrent.resolved_rate - baseline.resolved_rate
    lower, upper = _paired_bootstrap_ci(
        recurrent.resolved,
        baseline.resolved,
        samples=bootstrap_samples,
        seed=seed,
    )

    failures: list[str] = []
    if improvement < MIN_ABSOLUTE_IMPROVEMENT:
        failures.append("absolute_improvement")
    if lower <= 0.0:
        failures.append("bootstrap_ci_not_above_zero")
    if not all(result.repo_disjoint for result in mapped.values()):
        failures.append("repo_disjointness")
    if recurrent.flops_overhead > CORE_LIMITS.max_flops_overhead:
        failures.append("flops_overhead")
    if recurrent.p95_latency_overhead > CORE_LIMITS.max_p95_latency_overhead:
        failures.append("p95_latency_overhead")
    if recurrent.peak_vram_gb > RUNTIME_LIMITS.max_vram_gb:
        failures.append("peak_vram")
    if recurrent.peak_ram_gb > RUNTIME_LIMITS.max_ram_gb:
        failures.append("peak_ram")
    if recurrent.general_regression_points > MAX_GENERAL_REGRESSION_POINTS:
        failures.append("general_capability_regression")
    if any(result.functioning_exploits != 0 for result in mapped.values()):
        failures.append("functioning_exploit")

    return FalsificationDecision(
        kill=bool(failures),
        strongest_baseline=baseline.name,
        absolute_improvement=improvement,
        ci95_lower=lower,
        ci95_upper=upper,
        failures=tuple(failures),
    )

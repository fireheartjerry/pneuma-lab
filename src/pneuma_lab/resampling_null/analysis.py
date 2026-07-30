"""Frozen Task 7A statistical primitives.

These pure functions deliberately do not load manifests or classify outcomes;
the authorized analysis wrapper owns those responsibilities in Task 7B.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
from itertools import product
from math import ceil, comb, isfinite, sqrt
from typing import Literal, Sequence

import numpy as np

from .types import AnalysisRow, RandomizationResult, ResolutionResult, SimultaneousBounds

_ENUMERATION_LIMIT = 100_000
_DYNAMIC_STATE_LIMIT = 100_000
_DOMAINS = {"content": 0x43544E54, "excess": 0x45584353, "omnibus": 0x4F4D4E49, "multiplier": 0x4D554C54}


def task_contrasts(row: AnalysisRow) -> dict[str, float]:
    """Return the six registered task-block contrasts in canonical orientation."""
    no_feedback = (row.none + row.resample) / 2.0
    return {
        "content": row.real - row.sham,
        "excess": row.real - no_feedback,
        "sham_packet": row.sham - no_feedback,
        "continuation": no_feedback - row.prefix,
        "total": row.real - row.prefix,
        "null": row.resample - row.none,
    }


def _weights(rows: Sequence[AnalysisRow]) -> dict[str, Fraction]:
    by_benchmark: dict[str, int] = Counter(row.benchmark for row in rows)
    if not by_benchmark:
        raise ValueError("rows must not be empty")
    benchmark_count = len(by_benchmark)
    return {benchmark: Fraction(1, benchmark_count * count) for benchmark, count in by_benchmark.items()}


def _observed(rows: Sequence[AnalysisRow], name: str) -> Fraction:
    weights = _weights(rows)
    return sum((weights[row.benchmark] * Fraction(task_contrasts(row)[name]) for row in rows), Fraction())


def _rng(seed: int, domain: str) -> np.random.Generator:
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("seed must be an unsigned 64-bit integer")
    return np.random.Generator(np.random.Philox(np.random.SeedSequence((seed, _DOMAINS[domain]))))


def _tail_result(observed: Fraction, distribution: Counter[Fraction], support_size: int, mode: Literal["enumerated_exact", "dynamic_program_exact"]) -> RandomizationResult:
    total = sum(distribution.values())
    exceedances = sum(count for statistic, count in distribution.items() if statistic >= observed)
    return RandomizationResult(float(observed), exceedances / total, mode, support_size, None, None)


def _monte_carlo(observed: Fraction, rows: Sequence[AnalysisRow], name: str, choices: Sequence[Sequence[Fraction]], draws: int, seed: int, domain: str) -> RandomizationResult:
    if type(draws) is not int or draws <= 0:
        raise ValueError("draws must be a positive exact int")
    generator = _rng(seed, domain)
    exceedances = 0
    for _ in range(draws):
        statistic = sum((options[int(generator.integers(len(options)))] for options in choices), Fraction())
        exceedances += statistic >= observed
    p_value = (1 + exceedances) / (1 + draws)
    return RandomizationResult(float(observed), p_value, "add_one_monte_carlo", None, draws, sqrt(p_value * (1 - p_value) / draws))


def _product_tail(observed: Fraction, choices: Sequence[Sequence[Fraction]], rows: Sequence[AnalysisRow], name: str, draws: int, seed: int, domain: str) -> RandomizationResult:
    support_size = 1
    for options in choices:
        support_size *= len(options)
    if support_size <= _ENUMERATION_LIMIT:
        distribution: Counter[Fraction] = Counter(sum(values, Fraction()) for values in product(*choices))
        return _tail_result(observed, distribution, support_size, "enumerated_exact")
    distribution = Counter({Fraction(): 1})
    for options in choices:
        next_distribution: Counter[Fraction] = Counter()
        for old, count in distribution.items():
            for value in options:
                next_distribution[old + value] += count
        distribution = next_distribution
        if len(distribution) > _DYNAMIC_STATE_LIMIT:
            return _monte_carlo(observed, rows, name, choices, draws, seed, domain)
    return _tail_result(observed, distribution, support_size, "dynamic_program_exact")


def sharp_content_pvalue(rows: Sequence[AnalysisRow], *, draws: int, seed: int) -> RandomizationResult:
    """One-sided conditional REAL/SHAM swap Fisher test."""
    weights = _weights(rows)
    observed = _observed(rows, "content")
    choices = [[weights[row.benchmark] * (row.real - row.sham), weights[row.benchmark] * (row.sham - row.real)] for row in rows]
    return _product_tail(observed, choices, rows, "content", draws, seed, "content")


def sharp_excess_pvalue(rows: Sequence[AnalysisRow], *, draws: int, seed: int) -> RandomizationResult:
    """One-sided conditional one-of-three REAL reassignment Fisher test."""
    weights = _weights(rows)
    observed = _observed(rows, "excess")
    choices: list[list[Fraction]] = []
    for row in rows:
        values = (row.real, row.none, row.resample)
        choices.append([weights[row.benchmark] * Fraction(3 * value - sum(values), 2) for value in values])
    return _product_tail(observed, choices, rows, "excess", draws, seed, "excess")


def _studentized(values: Sequence[Fraction]) -> float:
    if not values:
        return 0.0
    mean = sum(values, Fraction()) / len(values)
    if len(values) < 2:
        return 0.0 if mean == 0 else float("inf")
    variance = sum((float(value - mean) ** 2 for value in values)) / (len(values) - 1)
    return float(mean) / sqrt(variance / len(values)) if variance else (0.0 if mean == 0 else float("inf"))


def omnibus_sharp_pvalue(rows: Sequence[AnalysisRow], *, draws: int, seed: int) -> RandomizationResult:
    """Full 12-way, sharp-global-null studentized max-T Fisher test."""
    _weights(rows)
    observed_values = [[Fraction(row.real - row.sham), Fraction(2 * row.real - row.none - row.resample, 2)] for row in rows]
    observed = max(_studentized([value[k] for value in observed_values]) for k in range(2))
    # NONE and RESAMPLE are exchangeable here: choose ordered REAL/SHAM slots.
    allocations = tuple((real, sham) for real in range(4) for sham in range(4) if real != sham)
    support_size = 12 ** len(rows)
    if support_size > _ENUMERATION_LIMIT:
        if type(draws) is not int or draws <= 0:
            raise ValueError("draws must be a positive exact int")
        generator = _rng(seed, "omnibus")
        exceeds = 0
        for _ in range(draws):
            sampled = []
            for row in rows:
                values = (row.real, row.sham, row.none, row.resample)
                order = allocations[int(generator.integers(12))]
                real, sham = order
                remaining = [index for index in range(4) if index not in order]
                sampled.append((Fraction(values[real] - values[sham]), Fraction(2 * values[real] - values[remaining[0]] - values[remaining[1]], 2)))
            statistic = max(_studentized([value[k] for value in sampled]) for k in range(2))
            exceeds += statistic >= observed
        p_value = (1 + exceeds) / (1 + draws)
        return RandomizationResult(observed, p_value, "add_one_monte_carlo", None, draws, sqrt(p_value * (1 - p_value) / draws))
    exceeds = 0
    for allocation_product in product(allocations, repeat=len(rows)):
        sampled = []
        for row, order in zip(rows, allocation_product, strict=True):
            values = (row.real, row.sham, row.none, row.resample)
            real, sham = order
            remaining = [index for index in range(4) if index not in order]
            sampled.append((Fraction(values[real] - values[sham]), Fraction(2 * values[real] - values[remaining[0]] - values[remaining[1]], 2)))
        statistic = max(_studentized([value[k] for value in sampled]) for k in range(2))
        exceeds += statistic >= observed
    return RandomizationResult(observed, exceeds / support_size, "enumerated_exact", support_size, None, None)


def conservative_multiplier_quantile(draws: Sequence[float], *, alpha: float) -> tuple[float, int]:
    if not draws or not 0 < alpha < 1:
        raise ValueError("draws must be non-empty and alpha must lie in (0, 1)")
    if not all(isfinite(value) for value in draws):
        raise ValueError("draws must be finite")
    order = min(len(draws), ceil((len(draws) + 1) * (1 - alpha)))
    return sorted(draws)[order - 1], order


def multiplier_lower_bounds(rows: Sequence[AnalysisRow], *, contrast_names: tuple[str, ...], family_name: Literal["co_primary", "secondary_three"], draws: int, seed: int) -> SimultaneousBounds:
    """Benchmark-stratified task-cluster Rademacher max-t lower bounds."""
    if not contrast_names or type(draws) is not int or draws <= 0:
        raise ValueError("contrast_names and a positive exact draws are required")
    grouped: dict[str, list[AnalysisRow]] = defaultdict(list)
    for row in rows:
        grouped[row.benchmark].append(row)
    if not grouped:
        raise ValueError("rows must not be empty")
    b_count = len(grouped)
    estimates = tuple(float(_observed(rows, name)) for name in contrast_names)
    matrices: list[np.ndarray] = []
    valid = True
    for benchmark_rows in grouped.values():
        n = len(benchmark_rows)
        if n < 2:
            valid = False
            break
        matrix = np.array([[task_contrasts(row)[name] for name in contrast_names] for row in benchmark_rows], dtype=float)
        matrices.append(matrix)
    if valid:
        covariance = sum((np.cov(matrix, rowvar=False, ddof=1) / len(matrix) for matrix in matrices), np.zeros((len(contrast_names), len(contrast_names)))) / (b_count**2)
        standard_errors = tuple(float(sqrt(value)) if value > 0 and isfinite(value) else float("inf") for value in np.diag(covariance))
    else:
        standard_errors = tuple(float("inf") for _ in contrast_names)
    if not all(isfinite(value) and value > 0 for value in standard_errors):
        return SimultaneousBounds(family_name, contrast_names, estimates, standard_errors, tuple(float("-inf") for _ in estimates), tuple(float("inf") for _ in estimates), float("inf"), "task_cluster_rademacher_max_t", draws, seed, 0)
    generator = _rng(seed, "multiplier")
    maxima: list[float] = []
    for _ in range(draws):
        total = np.zeros(len(contrast_names))
        for matrix in matrices:
            n = len(matrix)
            centered = matrix - matrix.mean(axis=0)
            signs = generator.integers(0, 2, size=n, dtype=np.int8) * 2 - 1
            total += signs @ centered * sqrt(n / (n - 1)) / n
        z = total / (2 * b_count) / np.array(standard_errors)
        maxima.append(float(np.max(z)))
    critical, order = conservative_multiplier_quantile(maxima, alpha=0.05)
    lowers = tuple(estimate - critical * standard_error for estimate, standard_error in zip(estimates, standard_errors, strict=True))
    uppers = tuple(estimate + critical * standard_error for estimate, standard_error in zip(estimates, standard_errors, strict=True))
    return SimultaneousBounds(family_name, contrast_names, estimates, standard_errors, lowers, uppers, critical, "task_cluster_rademacher_max_t", draws, seed, order)


def resampling_resolution(rows: Sequence[AnalysisRow]) -> ResolutionResult:
    """Exact sign-flip resolution scale for NONE/RESAMPLE discordance."""
    weights = _weights(rows)
    q0 = sum((weights[row.benchmark] * abs(row.resample - row.none) for row in rows), Fraction())
    discordant = [row for row in rows if row.resample != row.none]
    counts = Counter(row.benchmark for row in rows)
    equal = len(set(counts.values())) == 1
    if equal:
        n = next(iter(counts.values()))
        m = len(discordant)
        distribution = Counter()
        for k in range(m + 1):
            distribution[abs(Fraction(2 * k - m, 2 * n))] += comb(m, k)
        mode: Literal["equal_roster_exact_binomial", "unequal_roster_exact_weighted_convolution"] = "equal_roster_exact_binomial"
    else:
        distribution: Counter[Fraction] = Counter({Fraction(): 1})
        for row in discordant:
            weight = weights[row.benchmark]
            next_distribution: Counter[Fraction] = Counter()
            for total, mass in distribution.items():
                next_distribution[total + weight] += mass
                next_distribution[total - weight] += mass
            distribution = next_distribution
        raw = distribution
        distribution = Counter()
        for total, mass in raw.items():
            distribution[abs(total)] += mass
        mode = "unequal_roster_exact_weighted_convolution"
    total_mass = sum(distribution.values())
    cumulative = 0
    r95 = Fraction()
    for value in sorted(distribution):
        cumulative += distribution[value]
        if cumulative * 20 >= total_mass * 19:
            r95 = value
            break
    return ResolutionResult(float(q0), float(r95), len(discordant), mode)

"""Frozen Task 7A statistical primitives.

These pure functions deliberately do not load manifests or classify outcomes;
the authorized analysis wrapper owns those responsibilities in Task 7B.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
from itertools import product
from math import ceil, comb, isfinite, sqrt
from pathlib import Path
from typing import Literal, Sequence
import json

import numpy as np

from .types import (
    AnalysisConfig, AnalysisRow, ArtifactRef, BinarySufficientStatistics,
    BinarySufficientStatisticsBatch, GateBatchResult, GateResult, GroupLabel,
    RandomizationResult, ResolutionResult, SimultaneousBounds,
    AnalysisResult, BenchmarkEstimate, ContrastResult, LeaveOneEstimate,
    SecondaryFamilyResult, Verdict,
)

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
    if set(by_benchmark) != {"SWE", "TAU"}:
        raise ValueError("registered analysis requires exactly SWE and TAU rows")
    return {benchmark: Fraction(1, 2 * count) for benchmark, count in by_benchmark.items()}


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


def _omnibus_local_statistics(row: AnalysisRow) -> tuple[tuple[Fraction, Fraction], ...]:
    values = (row.real, row.sham, row.none, row.resample)
    return tuple(
        (
            Fraction(values[real] - values[sham]),
            Fraction(2 * values[real] - values[remaining[0]] - values[remaining[1]], 2),
        )
        for real in range(4)
        for sham in range(4)
        if real != sham
        for remaining in ([index for index in range(4) if index not in (real, sham)],)
    )


def _omnibus_variances(rows: Sequence[AnalysisRow]) -> tuple[float, float]:
    weights = _weights(rows)
    variances = [0.0, 0.0]
    for row in rows:
        local = _omnibus_local_statistics(row)
        for contrast_index in range(2):
            values = [float(item[contrast_index]) for item in local]
            mean = sum(values) / len(values)
            variances[contrast_index] += float(weights[row.benchmark] ** 2) * sum(
                (value - mean) ** 2 for value in values
            ) / len(values)
    return tuple(variances)  # type: ignore[return-value]


def omnibus_sharp_pvalue(rows: Sequence[AnalysisRow], *, draws: int, seed: int) -> RandomizationResult:
    """Full 12-way, sharp-global-null studentized max-T Fisher test."""
    weights = _weights(rows)
    local_statistics = [_omnibus_local_statistics(row) for row in rows]
    variances = _omnibus_variances(rows)
    observed_components = (
        float(_observed(rows, "content")), float(_observed(rows, "excess"))
    )
    if any(variance == 0.0 and component != 0.0 for variance, component in zip(variances, observed_components, strict=True)):
        raise ValueError("omnibus conditional variance is zero for a nonzero statistic")
    observed = max(
        component / sqrt(variance) if variance else 0.0
        for component, variance in zip(observed_components, variances, strict=True)
    )
    support_size = 12 ** len(rows)
    if support_size > _ENUMERATION_LIMIT:
        if type(draws) is not int or draws <= 0:
            raise ValueError("draws must be a positive exact int")
        generator = _rng(seed, "omnibus")
        exceeds = 0
        for _ in range(draws):
            sampled = []
            for local in local_statistics:
                sampled.append(local[int(generator.integers(12))])
            totals = [sum((weights[row.benchmark] * value[index] for row, value in zip(rows, sampled, strict=True)), Fraction()) for index in range(2)]
            statistic = max(float(total) / sqrt(variance) if variance else 0.0 for total, variance in zip(totals, variances, strict=True))
            exceeds += statistic >= observed
        p_value = (1 + exceeds) / (1 + draws)
        return RandomizationResult(observed, p_value, "add_one_monte_carlo", None, draws, sqrt(p_value * (1 - p_value) / draws))
    exceeds = 0
    for sampled in product(*local_statistics):
        totals = [sum((weights[row.benchmark] * value[index] for row, value in zip(rows, sampled, strict=True)), Fraction()) for index in range(2)]
        statistic = max(float(total) / sqrt(variance) if variance else 0.0 for total, variance in zip(totals, variances, strict=True))
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
    canonical_rows = tuple(
        sorted(rows, key=lambda row: (row.benchmark.encode("utf-8"), row.task_id.encode("utf-8")))
    )
    if len({(row.benchmark, row.task_id) for row in canonical_rows}) != len(canonical_rows):
        raise ValueError("(benchmark, task_id) pairs must be unique")
    _weights(canonical_rows)
    grouped: dict[str, list[AnalysisRow]] = defaultdict(list)
    for row in canonical_rows:
        grouped[row.benchmark].append(row)
    if not grouped:
        raise ValueError("rows must not be empty")
    b_count = len(grouped)
    estimates = tuple(float(_observed(canonical_rows, name)) for name in contrast_names)
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


def _multiplier_z_draws(rows: Sequence[AnalysisRow], names: tuple[str, ...], standard_errors: tuple[float, ...], *, draws: int, seed: int) -> np.ndarray:
    """One Philox stream shared by secondary max-t bounds and marginal p-values."""
    canonical = tuple(sorted(rows, key=lambda row: (row.benchmark.encode(), row.task_id.encode())))
    grouped = {benchmark: [row for row in canonical if row.benchmark == benchmark] for benchmark in ("SWE", "TAU")}
    matrices = [np.array([[task_contrasts(row)[name] for name in names] for row in grouped[benchmark]], dtype=float) for benchmark in ("SWE", "TAU")]
    generator = _rng(seed, "multiplier")
    result = np.empty((draws, len(names)), dtype=float)
    denominator = np.asarray(standard_errors)
    for draw in range(draws):
        total = np.zeros(len(names))
        for matrix in matrices:
            n = len(matrix)
            signs = generator.integers(0, 2, size=n, dtype=np.int8) * 2 - 1
            total += signs @ (matrix - matrix.mean(axis=0)) * sqrt(n / (n - 1)) / n
        result[draw] = total / 4 / denominator
    return result


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


_PATTERNS = tuple(product((0, 1), repeat=4))


def _pattern_index(row: AnalysisRow) -> int:
    return (row.real << 3) | (row.sham << 2) | (row.none << 1) | row.resample


def rows_to_binary_sufficient_statistics(
    rows: Sequence[AnalysisRow], *, roster_ref: ArtifactRef,
) -> BinarySufficientStatistics:
    """Collapse verified binary rows without accepting a caller-owned roster digest."""
    if type(roster_ref) is not ArtifactRef:
        raise TypeError("roster_ref must be an exact ArtifactRef")
    _weights(rows)
    buckets: dict[tuple[str, tuple[GroupLabel, ...]], list[int]] = {}
    failures: dict[str, list[int]] = {}
    invalid = 0
    for row in rows:
        if not isinstance(row, AnalysisRow):
            raise TypeError("rows must contain AnalysisRow")
        memberships = ((),) + tuple((group,) for group in row.sensitivity_groups)
        for labels in memberships:
            counts = buckets.setdefault((row.benchmark, labels), [0] * 16)
            counts[_pattern_index(row)] += 1
        arm_counts = failures.setdefault(row.benchmark, [0, 0, 0, 0])
        for index, failed in enumerate((
            row.real_infrastructure_failure, row.sham_infrastructure_failure,
            row.none_infrastructure_failure, row.resample_infrastructure_failure,
        )):
            arm_counts[index] += int(failed)
        invalid += int(not row.pipeline_valid or bool(row.invalid_codes))
    ordered = tuple(
        (benchmark, labels, tuple(counts))
        for (benchmark, labels), counts in sorted(
            buckets.items(), key=lambda item: (item[0][0].encode(), tuple((g.kind.value, g.value) for g in item[0][1]))
        )
    )
    arm_counts = tuple((benchmark, tuple(counts)) for benchmark, counts in sorted(failures.items()))
    return BinarySufficientStatistics(roster_ref, ordered, arm_counts, invalid)


def _statistics_rows(statistics: BinarySufficientStatistics) -> list[AnalysisRow]:
    """Rehydrate only overall benchmark counts for exact finite randomization."""
    rows: list[AnalysisRow] = []
    for benchmark, labels, counts in statistics.benchmark_group_pattern_counts:
        if labels:
            continue
        for pattern_index, count in enumerate(counts):
            if type(count) is not int or count < 0:
                raise TypeError("pattern counts must be non-negative exact ints")
            real, sham, none, resample = _PATTERNS[pattern_index]
            rows.extend(
                AnalysisRow(
                    task_id=f"{benchmark}-{pattern_index}-{ordinal}", benchmark=benchmark,
                    stratum="sufficient-statistics", lineage="sufficient-statistics",
                    sensitivity_groups=(), triggered=True, prefix=0, real=real, sham=sham,
                    none=none, resample=resample, real_infrastructure_failure=False,
                    sham_infrastructure_failure=False, none_infrastructure_failure=False,
                    resample_infrastructure_failure=False, pipeline_valid=True, invalid_codes=(),
                ) for ordinal in range(count)
            )
    _weights(rows)
    return rows


def _failure_gap(statistics: BinarySufficientStatistics) -> float:
    totals = {benchmark: counts for benchmark, counts in statistics.arm_failure_counts}
    overall = {
        benchmark: sum(counts)
        for benchmark, labels, counts in statistics.benchmark_group_pattern_counts if not labels
    }
    if set(overall) != {"SWE", "TAU"} or any(overall[b] == 0 for b in overall):
        raise ValueError("statistics requires non-empty SWE and TAU overall counts")
    rates = [0.5 * (totals["SWE"][arm] / overall["SWE"] + totals["TAU"][arm] / overall["TAU"]) for arm in range(4)]
    return max(abs(left - right) for left in rates for right in rates)


def _count_sharp_tail(counts: np.ndarray, *, excess: bool, draws: int, seed: int) -> np.ndarray:
    """Exact count-level Fisher tails; no task-row reconstruction is involved."""
    result = np.empty(counts.shape[0], dtype=float)
    for run in range(counts.shape[0]):
        choices: list[tuple[Fraction, ...]] = []
        observed = Fraction()
        for benchmark_index, benchmark in enumerate(("SWE", "TAU")):
            n = int(counts[run, benchmark_index].sum())
            weight = Fraction(1, 2 * n)
            for index, amount in enumerate(counts[run, benchmark_index]):
                real, sham, none, resample = _PATTERNS[index]
                if excess:
                    values = (real, none, resample)
                    options = tuple(weight * Fraction(3 * value - sum(values), 2) for value in values)
                    observed += weight * Fraction(2 * real - none - resample, 2) * int(amount)
                else:
                    options = (weight * (real - sham), weight * (sham - real))
                    observed += weight * (real - sham) * int(amount)
                choices.extend([options] * int(amount))
        support = 1
        for options in choices:
            support *= len(options)
        distribution: Counter[Fraction] = Counter({Fraction(): 1})
        for options in choices:
            following: Counter[Fraction] = Counter()
            for previous, mass in distribution.items():
                for option in options:
                    following[previous + option] += mass
            distribution = following
            if len(distribution) > _DYNAMIC_STATE_LIMIT:
                # Same Philox/add-one rule and domain as the scalar primitive.
                generator = _rng(seed, "excess" if excess else "content")
                exceeds = 0
                for _ in range(draws):
                    statistic = sum((options[int(generator.integers(len(options)))] for options in choices), Fraction())
                    exceeds += statistic >= observed
                result[run] = (1 + exceeds) / (1 + draws)
                break
        else:
            total = sum(distribution.values())
            result[run] = sum(mass for value, mass in distribution.items() if value >= observed) / total
    return result


def _count_resolution(counts: np.ndarray) -> np.ndarray:
    """Exact count-level NONE/RESAMPLE sign-flip resolution by integer DP."""
    output = np.empty(counts.shape[0], dtype=float)
    for run in range(counts.shape[0]):
        roster = [int(counts[run, benchmark].sum()) for benchmark in range(2)]
        discordant = [int(sum(counts[run, benchmark, index] for index, pattern in enumerate(_PATTERNS) if pattern[2] != pattern[3])) for benchmark in range(2)]
        if roster[0] == roster[1]:
            n, m = roster[0], sum(discordant)
            masses = Counter({abs(Fraction(2 * k - m, 2 * n)): comb(m, k) for k in range(m + 1)})
        else:
            distribution: Counter[Fraction] = Counter({Fraction(): 1})
            for benchmark, m in enumerate(discordant):
                weight = Fraction(1, 2 * roster[benchmark])
                for _ in range(m):
                    following: Counter[Fraction] = Counter()
                    for old, mass in distribution.items():
                        following[old + weight] += mass
                        following[old - weight] += mass
                    distribution = following
            masses = Counter()
            for value, mass in distribution.items():
                masses[abs(value)] += mass
        total, cumulative = sum(masses.values()), 0
        for value in sorted(masses):
            cumulative += masses[value]
            if cumulative * 20 >= total * 19:
                output[run] = float(value)
                break
    return output


def evaluate_binary_gate_kernel(
    statistics: BinarySufficientStatistics, config: AnalysisConfig, *, critical_value: float, seed: int = 0,
) -> tuple[GateResult, ...]:
    """The sole scalar implementation of registered outcome gate predicates."""
    if not isinstance(statistics, BinarySufficientStatistics) or not isinstance(config, AnalysisConfig):
        raise TypeError("statistics and config must be registered value records")
    if not isfinite(critical_value) or critical_value < 0:
        raise ValueError("critical_value must be finite and non-negative")
    rows = _statistics_rows(statistics)
    content = float(_observed(rows, "content"))
    excess = float(_observed(rows, "excess"))
    content_p = sharp_content_pvalue(rows, draws=config.sharp_draws, seed=seed).p_value
    excess_p = sharp_excess_pvalue(rows, draws=config.sharp_draws, seed=seed).p_value
    bounds = multiplier_lower_bounds(rows, contrast_names=("content", "excess"), family_name="co_primary", draws=1, seed=0)
    primary_lowers = tuple(estimate - critical_value * se if isfinite(se) else float("-inf") for estimate, se in zip(bounds.estimates, bounds.standard_errors, strict=True))
    resolution = resampling_resolution(rows)
    weights = _weights(rows)
    benchmark_ok = all(float(sum((weights[row.benchmark] * task_contrasts(row)[name] for row in rows if row.benchmark == benchmark), Fraction()) * 2) >= 0.0 for benchmark in ("SWE", "TAU") for name in ("content", "excess"))
    leave_one_ok = True
    for benchmark, labels, counts in statistics.benchmark_group_pattern_counts:
        if not labels:
            continue
        overall_counts = next(overall for b, group, overall in statistics.benchmark_group_pattern_counts if b == benchmark and not group)
        retained = tuple(left - right for left, right in zip(overall_counts, counts, strict=True))
        if sum(retained) == 0:
            leave_one_ok = False
            continue
        retained_rows = _statistics_rows(BinarySufficientStatistics(statistics.roster_ref, ((benchmark, (), retained), ("TAU" if benchmark == "SWE" else "SWE", (), next(c for b, g, c in statistics.benchmark_group_pattern_counts if b != benchmark and not g))), statistics.arm_failure_counts, 0))
        leave_one_ok &= all(float(_observed(retained_rows, name)) >= -0.05 for name in ("content", "excess"))
    gap = _failure_gap(statistics)
    values = (
        ("pipeline_valid", statistics.pipeline_invalid_count == 0, statistics.pipeline_invalid_count, "==", 0),
        ("content_sharp", content_p <= config.alpha, content_p, "<=", config.alpha),
        ("excess_sharp", excess_p <= config.alpha, excess_p, "<=", config.alpha),
        ("content_lower", primary_lowers[0] > 0.0, primary_lowers[0], ">", 0.0),
        ("excess_lower", primary_lowers[1] > 0.0, primary_lowers[1], ">", 0.0),
        ("content_materiality", content >= config.delta_star, content, ">=", config.delta_star),
        ("excess_materiality", excess >= config.delta_star, excess, ">=", config.delta_star),
        ("content_resolution", content > resolution.r95, content, ">", resolution.r95),
        ("excess_resolution", excess > resolution.r95, excess, ">", resolution.r95),
        ("benchmark_nonnegative", benchmark_ok, benchmark_ok, "is", True),
        ("leave_one_nonnegative", leave_one_ok, leave_one_ok, "is", True),
        ("differential_failure_gap", gap <= config.max_differential_failure_gap, gap, "<=", config.max_differential_failure_gap),
    )
    return tuple(GateResult(*value) for value in values)


def evaluate_binary_gate_batch(
    statistics: BinarySufficientStatisticsBatch, config: AnalysisConfig, *, critical_values: np.ndarray,
) -> GateBatchResult:
    """Evaluate immutable simulator tensors; the scalar kernel remains authoritative."""
    patterns = np.asarray(statistics.pattern_counts, dtype=np.int64)
    failures = np.asarray(statistics.arm_failure_counts, dtype=np.int64)
    invalid = np.asarray(statistics.pipeline_invalid_counts, dtype=np.int64)
    critical = np.asarray(critical_values, dtype=np.float64)
    if patterns.ndim != 3 or patterns.shape[2] != 16 or failures.ndim != 3 or failures.shape[0] != patterns.shape[0] or failures.shape[2] != 4:
        raise ValueError("batch statistics have incompatible shapes")
    if patterns.shape[0] != len(critical) or invalid.shape != (patterns.shape[0],):
        raise ValueError("batch dimensions must agree")
    overall_entries = [entry for entry, (_, group) in enumerate(statistics.group_manifest) if group is None]
    if len(overall_entries) != 2 or {statistics.group_manifest[index][0] for index in overall_entries} != {"SWE", "TAU"} or failures.shape[1] != 2:
        raise ValueError("batch requires one SWE and one TAU overall count row")
    swe_index = next(index for index in overall_entries if statistics.group_manifest[index][0] == "SWE")
    tau_index = next(index for index in overall_entries if statistics.group_manifest[index][0] == "TAU")
    bits = np.asarray(_PATTERNS, dtype=np.float64)
    contrast_matrix = np.column_stack((bits[:, 0] - bits[:, 1], bits[:, 0] - (bits[:, 2] + bits[:, 3]) / 2))
    counts = patterns[:, [swe_index, tau_index], :]
    n = counts.sum(axis=2)
    if np.any(n == 0) or np.any(counts < 0) or np.any(failures < 0):
        raise ValueError("batch counts must be non-negative with both rosters non-empty")
    means_by_benchmark = np.einsum("nbi,ik->nbk", counts, contrast_matrix) / n[:, :, None]
    estimates = means_by_benchmark.mean(axis=1)
    centered_second = np.einsum("nbi,ik,il->nbkl", counts, contrast_matrix, contrast_matrix) / n[:, :, None, None]
    numerator = centered_second - np.einsum("nbk,nbl->nbkl", means_by_benchmark, means_by_benchmark)
    covariance = numerator / np.maximum(1, n - 1)[:, :, None, None]
    se = np.sqrt(np.maximum(0.0, covariance.sum(axis=1).diagonal(axis1=1, axis2=2) / 4))
    se[np.any(n < 2, axis=1)] = np.inf
    primary_lowers = np.full_like(estimates, -np.inf)
    np.subtract(estimates, critical[:, None] * np.where(np.isfinite(se), se, 0.0), out=primary_lowers, where=np.isfinite(se))
    content_p = _count_sharp_tail(counts, excess=False, draws=config.sharp_draws, seed=0)
    excess_p = _count_sharp_tail(counts, excess=True, draws=config.sharp_draws, seed=0)
    r95 = _count_resolution(counts)
    rates = failures / n[:, :, None]
    equal_rates = rates.mean(axis=1)
    gap = np.max(np.abs(equal_rates[:, :, None] - equal_rates[:, None, :]), axis=(1, 2))
    benchmark_ok = np.all(means_by_benchmark >= 0.0, axis=(1, 2))
    leave_one_ok = np.ones(patterns.shape[0], dtype=np.bool_)
    for entry, (benchmark, group) in enumerate(statistics.group_manifest):
        if group is None:
            continue
        base = 0 if benchmark == "SWE" else 1
        retained = n[:, base] - patterns[:, entry, :].sum(axis=1)
        if np.any(retained <= 0):
            leave_one_ok &= False
            continue
        retained_mean = np.einsum("ni,ik->nk", counts[:, base, :] - patterns[:, entry, :], contrast_matrix) / retained[:, None]
        other_mean = means_by_benchmark[:, 1 - base, :]
        leave_one_ok &= np.all((retained_mean + other_mean) / 2 >= -0.05, axis=1)
    causal = ((invalid == 0) & (content_p <= config.alpha) & (excess_p <= config.alpha)
              & np.all(primary_lowers > 0, axis=1) & np.all(estimates >= config.delta_star, axis=1)
              & np.all(estimates > r95[:, None], axis=1) & benchmark_ok & leave_one_ok
              & (gap <= config.max_differential_failure_gap))
    return GateBatchResult(causal, estimates[:, 0], estimates[:, 1], content_p, excess_p, primary_lowers, r95, gap, benchmark_ok, leave_one_ok)


def classify_verdict(
    gates: Sequence[GateResult], *, content: ContrastResult, excess: ContrastResult,
    sham_packet: ContrastResult, resolution: ResolutionResult,
    secondary: SecondaryFamilyResult,
) -> Verdict:
    """Apply the closed outcome precedence; feasibility is deliberately absent."""
    gate_map = {gate.code: gate for gate in gates}
    if not all(gate.passed for gate in gates if gate.code in {"pipeline_valid", "differential_failure_gap"}):
        return Verdict.PIPELINE_INVALID
    if ((content.estimate <= -0.05 and isfinite(content.simultaneous_upper) and content.simultaneous_upper < 0) or
            (excess.estimate <= -0.05 and isfinite(excess.simultaneous_upper) and excess.simultaneous_upper < 0)):
        return Verdict.HARMFUL_OR_MISDIRECTING
    causal_codes = {"pipeline_valid", "content_sharp", "excess_sharp", "content_lower", "excess_lower", "content_materiality", "excess_materiality", "content_resolution", "excess_resolution", "benchmark_nonnegative", "leave_one_nonnegative", "differential_failure_gap"}
    if (all(gate_map.get(code, GateResult(code, False, None, "", None)).passed for code in causal_codes)
            and content.estimate >= 0.05 and excess.estimate >= 0.05
            and content.simultaneous_lower > 0 and excess.simultaneous_lower > 0
            and content.estimate > resolution.r95 and excess.estimate > resolution.r95):
        return Verdict.CAUSAL_CONTENT
    sham_holm = secondary.holm_adjusted_p[0]
    content_registered_failure = any(not gate_map.get(code, GateResult(code, False, None, "", None)).passed for code in ("content_lower", "content_sharp", "content_materiality", "content_resolution", "benchmark_nonnegative", "leave_one_nonnegative"))
    if (sham_packet.estimate >= 0.05 and sham_packet.estimate > resolution.r95 and sham_holm <= 0.05 and sham_packet.simultaneous_lower > 0 and content_registered_failure):
        return Verdict.SHAM_PACKET_ONLY
    if (not isfinite(content.standard_error) or content.standard_error <= 0 or
            not isfinite(excess.standard_error) or excess.standard_error <= 0 or
            content.estimate < 0.05 or excess.estimate < 0.05 or
            content.estimate <= resolution.r95 or excess.estimate <= resolution.r95):
        return Verdict.UNRESOLVED_RESAMPLING
    return Verdict.RESAMPLING_CONSISTENT


def _verify_roster_rows(rows: Sequence[AnalysisRow], *, roster_ref: ArtifactRef, selected_task_ids: Sequence[str], run_root: Path) -> None:
    """Fail closed on referenced roster bytes, row coverage, and registered labels."""
    from .artifacts import _read_ref
    _, payload = _read_ref(roster_ref, run_root=run_root)
    try:
        roster = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("roster_ref must resolve to JSON") from exc
    if (not isinstance(roster, dict) or set(roster) != {"record_kind", "schema_version", "roster_kind", "supported_tiers", "tasks"}
            or roster.get("record_kind") != "resampling_roster_v1" or roster.get("schema_version") != "1"
            or roster.get("roster_kind") not in {"synthetic_fixture", "eligible_confirmation"}
            or roster.get("supported_tiers") not in ([120], [120, 160]) or not isinstance(roster.get("tasks"), list)):
        raise ValueError("roster_ref does not resolve to a registered roster")
    expected: dict[str, tuple[str, str, str, tuple[tuple[str, str], ...]]] = {}
    for task in roster["tasks"]:
        if not isinstance(task, dict) or set(task) != {"task_id", "benchmark", "stratum", "lineage", "groups", "tiers"}:
            raise ValueError("roster task has incomplete membership")
        groups = task["groups"]
        if (not isinstance(groups, list) or len(groups) != 3 or
                [group.get("kind") if isinstance(group, dict) else None for group in groups] != ["language", "domain", "issue_family"] or
                any(not isinstance(group.get("value"), str) or not group["value"] for group in groups if isinstance(group, dict)) or
                not isinstance(task["task_id"], str) or not task["task_id"] or task["task_id"] in expected or
                not isinstance(task["tiers"], list) or not task["tiers"] or task["tiers"] != sorted(set(task["tiers"])) or
                any(type(tier) is not int or tier not in roster["supported_tiers"] for tier in task["tiers"])):
            raise ValueError("roster task groups are invalid")
        expected[task["task_id"]] = (task["benchmark"], task["stratum"], task["lineage"], tuple((group["kind"], group["value"]) for group in groups))
    selected = set(selected_task_ids)
    if not selected or not selected <= set(expected):
        raise ValueError("completed power selection is not roster membership")
    observed = {row.task_id: row for row in rows}
    if len(observed) != len(rows) or set(observed) != selected:
        raise ValueError("analysis rows must cover the manifest-bound roster exactly")
    for task_id, row in observed.items():
        benchmark, stratum, lineage, groups = expected[task_id]
        actual_groups = tuple((group.kind.value, group.value) for group in row.sensitivity_groups)
        if (row.benchmark, row.stratum, row.lineage, actual_groups) != (benchmark, stratum, lineage, groups):
            raise ValueError(f"analysis row {task_id!r} does not match roster membership")


def analyze(rows: Sequence[AnalysisRow], config: AnalysisConfig, *, seed: int, manifest_ref: ArtifactRef, power_final_ref: ArtifactRef, run_root: Path) -> AnalysisResult:
    """Perform admission-bound registered inference; no claimed roster is accepted."""
    from .assignment import require_schedulable_power_final
    from .artifacts import _load_direct_scientific_parent
    if type(manifest_ref) is not ArtifactRef or type(power_final_ref) is not ArtifactRef:
        raise TypeError("analysis admission requires exact manifest and power ArtifactRefs")
    selection = require_schedulable_power_final(manifest_ref, power_final_ref, run_root=run_root)
    manifest = _load_direct_scientific_parent(
        {"role": manifest_ref.role, "relative_path": manifest_ref.relative_path, "sha256": manifest_ref.sha256, "byte_count": manifest_ref.byte_count, "media_type": manifest_ref.media_type},
        run_root=run_root, field="manifest_ref", expected_kind="resampling_study_manifest",
    )
    payload = manifest.value["payload"]
    if not isinstance(payload, dict):
        raise ValueError("manifest payload is invalid")
    raw_roster_ref = payload.get("roster_ref")
    if not isinstance(raw_roster_ref, dict):
        raise ValueError("manifest lacks roster authority")
    roster_ref = ArtifactRef(**raw_roster_ref)
    _verify_roster_rows(rows, roster_ref=roster_ref, selected_task_ids=selection.selected_task_ids, run_root=run_root)
    statistics = rows_to_binary_sufficient_statistics(rows, roster_ref=roster_ref)
    primary = multiplier_lower_bounds(rows, contrast_names=("content", "excess"), family_name="co_primary", draws=config.multiplier_draws, seed=seed)
    gates = evaluate_binary_gate_kernel(statistics, config, critical_value=primary.critical_value, seed=seed)
    contrast_values = {name: float(_observed(rows, name)) for name in ("content", "excess", "sham_packet", "continuation", "total", "null")}
    content_random = sharp_content_pvalue(rows, draws=config.sharp_draws, seed=seed)
    excess_random = sharp_excess_pvalue(rows, draws=config.sharp_draws, seed=seed)
    secondary_bounds = multiplier_lower_bounds(rows, contrast_names=("sham_packet", "continuation", "total"), family_name="secondary_three", draws=config.multiplier_draws, seed=seed)
    # One Philox stream feeds both the three-family max-t bound and marginal add-one p-values.
    if all(isfinite(se) and se > 0 for se in secondary_bounds.standard_errors):
        z_draws = _multiplier_z_draws(rows, secondary_bounds.contrast_names, secondary_bounds.standard_errors, draws=config.multiplier_draws, seed=seed)
        observed_z = np.asarray(secondary_bounds.estimates) / np.asarray(secondary_bounds.standard_errors)
        raw = tuple(float((1 + np.count_nonzero(z_draws[:, index] >= observed_z[index])) / (1 + config.multiplier_draws)) for index in range(3))
    else:
        raw = (1.0, 1.0, 1.0)
    order = np.argsort(raw)
    holm_work = [0.0, 0.0, 0.0]
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, raw[index] * (3 - rank)))
        holm_work[int(index)] = running
    adjusted = tuple(holm_work)
    secondary = SecondaryFamilyResult(("sham_packet", "continuation", "total"), raw, adjusted, secondary_bounds)
    content = ContrastResult(contrast_values["content"], primary.standard_errors[0], primary.lowers[0], primary.uppers[0], content_random)
    excess = ContrastResult(contrast_values["excess"], primary.standard_errors[1], primary.lowers[1], primary.uppers[1], excess_random)
    sham = ContrastResult(contrast_values["sham_packet"], secondary_bounds.standard_errors[0], secondary_bounds.lowers[0], secondary_bounds.uppers[0], None)
    resolution = resampling_resolution(rows)
    benchmark_estimates = tuple(
        BenchmarkEstimate(
            benchmark,
            float(sum(task_contrasts(row)["content"] for row in rows if row.benchmark == benchmark) / sum(row.benchmark == benchmark for row in rows)),
            float(sum(task_contrasts(row)["excess"] for row in rows if row.benchmark == benchmark) / sum(row.benchmark == benchmark for row in rows)),
        )
        for benchmark in ("SWE", "TAU")
    )
    registered_groups = sorted({group for row in rows for group in row.sensitivity_groups}, key=lambda group: (group.kind.value, group.value))
    leave_one_items: list[LeaveOneEstimate] = []
    for group in registered_groups:
        for benchmark in ("SWE", "TAU"):
            retained = [row for row in rows if row.benchmark == benchmark and group not in row.sensitivity_groups]
            if not retained:
                raise ValueError("registered leave-one group empties a benchmark")
            leave_one_items.append(LeaveOneEstimate(
                benchmark, group.kind, group.value,
                float(sum(task_contrasts(row)["content"] for row in retained) / len(retained)),
                float(sum(task_contrasts(row)["excess"] for row in retained) / len(retained)),
            ))
    leave_one = tuple(leave_one_items)
    verdict = classify_verdict(gates, content=content, excess=excess, sham_packet=sham, resolution=resolution, secondary=secondary)
    return AnalysisResult(content, excess, sham, contrast_values["continuation"], contrast_values["total"], contrast_values["null"], omnibus_sharp_pvalue(rows, draws=config.sharp_draws, seed=seed), primary, secondary, resolution, _failure_gap(statistics), benchmark_estimates, leave_one, gates, verdict, tuple(gate.code for gate in gates if not gate.passed))

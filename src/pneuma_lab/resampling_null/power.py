"""Closed, non-executing authority contracts for registered P0 power work.

Task 8A deliberately stops before any screen or simulator.  This module only
turns manifest-owned bytes into typed authority/configuration values.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from math import erf, exp, lgamma, log, pi, sqrt
from pathlib import Path
from statistics import NormalDist
from time import perf_counter
from typing import Literal, cast

import numpy as np

from pneuma_lab.foundation.artifacts import canonical_json_bytes, write_atomic_bytes

from .artifacts import (_artifact_ref_for_path, _load_direct_scientific_parent,
                        _prepare_destination, _read_ref, _ref_mapping, _scientific_documents,
                        _validate_power_identities, write_record)
from .assignment import BytesField, TextField, U64Field, commitment_sha256, kdf_frame
from .analysis import evaluate_binary_gate_batch
from .authority_refs import closed_mapping, decode_artifact_ref
from .errors import RecordValidationError
from .json_io import load_json_bytes
from .types import ArtifactRef
from .types import AnalysisConfig, BinarySufficientStatisticsBatch, GateBatchResult, GroupKind, GroupLabel


POWER_AUTHORITY_MEDIA_TYPE = "application/vnd.pneuma.power-authority+json"
_AUTHORITY_COMMON_FIELDS = frozenset(
    {"schema_version", "authority_kind", "manifest_ref", "roster_ref", "tier_membership_sha256"}
)
_RNG_FIELDS = (
    "bit_generator", "contract_id", "counter_fields", "counter_frame",
    "draw_domains", "draw_kinds", "integer_encoding", "key_fields",
    "key_frame", "numpy_version", "root_u64",
)
_RNG_CONTRACT: dict[str, object] = {
    "bit_generator": "numpy.random.Philox",
    "contract_id": "power-philox-v1",
    "counter_fields": ["draw_domain", "phase", "cell_id", "replicate_index", "draw_kind", "draw_index"],
    "counter_frame": "power-rng-counter-v1",
    "draw_domains": ["screen", "grid", "validation"],
    "draw_kinds": [
        "screen_trigger_partition", "screen_triggered_pattern", "screen_no_trigger_success",
        "grid_trigger_partition", "grid_triggered_pattern", "grid_no_trigger_success",
        "gaussian_validation_trigger_partition", "gaussian_validation_triggered_pattern",
        "gaussian_validation_no_trigger_success", "multiplier_rademacher",
    ],
    "integer_encoding": "unsigned-big-endian",
    "key_fields": ["root_u64", "authority_kind", "tier_membership_sha256_raw32", "grid_content_sha256_raw32"],
    "key_frame": "power-rng-key-v1",
    "numpy_version": "2.3.5",
    "root_u64": 7640891576956012809,
}
RNG_CONTRACT_SHA256 = hashlib.sha256(canonical_json_bytes(_RNG_CONTRACT, indent=None)).hexdigest()

GAUSS_HERMITE_ORDER = 96
GAUSS_LEGENDRE_ORDER = 128
PROBABILITY_TOLERANCE = 1e-10
GAUSSIAN_ROOT_TOLERANCE = 1e-10
GAUSSIAN_ROOT_MAX_ITERATIONS = 200
CLOPPER_PEARSON_TOLERANCE = 1e-12
CLOPPER_PEARSON_MAX_ITERATIONS = 200
_NORMAL = NormalDist()


@dataclass(frozen=True, slots=True)
class Nuisance:
    p0: float
    trigger_rate: float
    rho: float


@dataclass(frozen=True, slots=True)
class PowerCell:
    """One ordered, frozen P0 cell; identifiers are independent of execution topology."""
    cell_id: str
    family: Literal["alternative", "null_both", "null_content", "null_excess"]
    swe: Nuisance
    tau: Nuisance


@dataclass(frozen=True, slots=True)
class BenchmarkPatternCounts:
    """One benchmark's exact-size triggered and no-trigger pattern counts."""

    pattern_counts: tuple[int, ...]
    triggered_pattern_counts: tuple[int, ...]
    no_trigger_pattern_counts: tuple[int, ...]
    joint_group_pattern_counts: tuple[tuple[int, ...], ...]
    triggered_count: int
    expected_content: float
    expected_excess: float


def frozen_power_cells() -> tuple[PowerCell, ...]:
    """The exact 729 cross-benchmark alternatives and three 729-cell null families."""
    values = (0.1, 0.4, 0.7)
    triggers = (0.6, 0.75, 0.9)
    rhos = (0.0, 0.4, 0.8)
    nuisances = tuple(Nuisance(p0, trigger, rho) for p0 in values for trigger in triggers for rho in rhos)
    cells: list[PowerCell] = []
    for family in ("alternative", "null_both", "null_content", "null_excess"):
        for swe_index, swe in enumerate(nuisances):
            for tau_index, tau in enumerate(nuisances):
                cells.append(PowerCell(
                    f"{family}:swe-{swe_index:02d}:tau-{tau_index:02d}", cast(Literal["alternative", "null_both", "null_content", "null_excess"], family), swe, tau,
                ))
    return tuple(cells)


@dataclass(frozen=True, slots=True)
class PatternProbabilityReceipt:
    probabilities: tuple[float, ...]
    probability_sum_error: float
    marginal_errors: tuple[float, float, float, float]
    latent_rho: float
    quadrature_order: int


def _phi(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def bernoulli_pattern_probabilities(
    marginals: tuple[float, float, float, float], rho: float,
) -> PatternProbabilityReceipt:
    """One-factor latent-Gaussian 16-pattern table in canonical R,S,N,Z bits."""
    if len(marginals) != 4 or any(type(p) is not float or not 0.0 < p < 1.0 for p in marginals):
        raise ValueError("marginals must be four strict probabilities")
    if not -1e-12 <= rho <= 1.0 + 1e-12:
        raise ValueError("latent rho must be in [0, 1]")
    rho = min(1.0, max(0.0, rho))
    thresholds = tuple(_NORMAL.inv_cdf(p) for p in marginals)
    patterns = tuple(tuple((index >> shift) & 1 for shift in (3, 2, 1, 0)) for index in range(16))
    if rho == 0.0:
        values = [float(np.prod([p if bit else 1.0 - p for p, bit in zip(marginals, pattern)])) for pattern in patterns]
    else:
        nodes, weights = np.polynomial.hermite.hermgauss(GAUSS_HERMITE_ORDER)
        scale = sqrt(1.0 - rho)
        values = []
        for pattern in patterns:
            total = 0.0
            for node, weight in zip(nodes, weights):
                conditional = [_phi((threshold - sqrt(rho) * sqrt(2.0) * float(node)) / scale) for threshold in thresholds]
                total += float(weight) * float(np.prod([p if bit else 1.0 - p for p, bit in zip(conditional, pattern)]))
            values.append(total / sqrt(pi))
    probability_sum_error = abs(sum(values) - 1.0)
    recovered = tuple(sum(value for value, pattern in zip(values, patterns) if pattern[column]) for column in range(4))
    errors = tuple(abs(actual - expected) for actual, expected in zip(recovered, marginals))
    if min(values) < -PROBABILITY_TOLERANCE or probability_sum_error > PROBABILITY_TOLERANCE or max(errors) > PROBABILITY_TOLERANCE:
        raise RecordValidationError("latent Gaussian pattern probabilities fail frozen numeric tolerance")
    return PatternProbabilityReceipt(tuple(values), probability_sum_error, cast(tuple[float, float, float, float], errors), rho, GAUSS_HERMITE_ORDER)


def _triggered_marginals(p0: float, gamma: float, family: str) -> tuple[float, float, float, float]:
    """Registered triggered-arm boundary family; all effects are ITT 0.15 or 0."""
    uplift = 0.15 / gamma
    if family == "alternative":
        values = (p0 + uplift, p0, p0, p0)
    elif family == "null_both":
        values = (p0, p0, p0, p0)
    elif family == "null_content":
        values = (p0 + uplift, p0 + uplift, p0, p0)
    elif family == "null_excess":
        values = (p0 + uplift, p0, p0 + uplift, p0 + uplift)
    else:
        raise RecordValidationError("unregistered P0 cell family")
    if any(not 0.10 <= value <= 0.95 for value in values):
        raise RecordValidationError("registered triggered marginal lies outside [0.10, 0.95]")
    return cast(tuple[float, float, float, float], values)


def simulate_benchmark_pattern_counts(
    *, p0: float, gamma: float, rho: float,
    family: str, task_count: int, authority_kind: str,
    tier_membership_sha256: str, grid_content_digest: str, phase: str,
    cell_id: str, replicate_index: int, joint_group_sizes: tuple[int, ...],
    draw_domain: Literal["screen", "grid", "validation"] = "grid",
) -> BenchmarkPatternCounts:
    """Generate the registered count-level P0 outcome model for one benchmark.

    The task-level outcome bytes are intentionally never materialized: exact
    group-cell allocations and sixteen-pattern counts are the sufficient
    statistics consumed by the Task-7 batch gate.
    """
    if type(task_count) is not int or task_count <= 0 or any(type(size) is not int or size <= 0 for size in joint_group_sizes) or sum(joint_group_sizes) != task_count:
        raise RecordValidationError("joint sensitivity-group sizes must exactly partition the benchmark roster")
    if p0 not in (0.1, 0.4, 0.7) or gamma not in (0.6, 0.75, 0.9) or rho not in (0.0, 0.4, 0.8):
        raise RecordValidationError("P0 nuisance values differ from the frozen grid")
    triggered_exact = gamma * task_count
    triggered_count = round(triggered_exact)
    if triggered_count != triggered_exact:
        raise RecordValidationError("gamma * benchmark roster count must be exact")
    prefix = "gaussian_validation" if draw_domain == "validation" else draw_domain
    partition_rng = philox_generator(
        authority_kind, tier_membership_sha256, grid_content_digest, draw_domain,
        phase, cell_id, replicate_index, f"{prefix}_trigger_partition", 0,
    )
    # This is the exact uniform fixed-size subset allocation over joint cells.
    triggered_by_group = partition_rng.multivariate_hypergeometric(
        np.asarray(joint_group_sizes, dtype=np.int64), triggered_count,
    )
    marginals = _triggered_marginals(p0, gamma, family)
    probabilities = np.asarray(bernoulli_pattern_probabilities(marginals, rho).probabilities)
    triggered_patterns = np.zeros(16, dtype=np.int64)
    no_trigger_patterns = np.zeros(16, dtype=np.int64)
    joint_patterns: list[tuple[int, ...]] = []
    for group_index, (group_size, triggered_here) in enumerate(zip(joint_group_sizes, triggered_by_group, strict=True)):
        pattern_rng = philox_generator(
            authority_kind, tier_membership_sha256, grid_content_digest, draw_domain,
            phase, cell_id, replicate_index, f"{prefix}_triggered_pattern", group_index,
        )
        triggered_here_patterns = pattern_rng.multinomial(int(triggered_here), probabilities)
        triggered_patterns += triggered_here_patterns
        no_trigger_rng = philox_generator(
            authority_kind, tier_membership_sha256, grid_content_digest, draw_domain,
            phase, cell_id, replicate_index, f"{prefix}_no_trigger_success", group_index,
        )
        successes = int(no_trigger_rng.binomial(group_size - int(triggered_here), p0))
        # No-trigger rows are exactly (B,B,B,B), not an independent four-arm draw.
        no_trigger_patterns[15] += successes
        no_trigger_patterns[0] += group_size - int(triggered_here) - successes
        local = triggered_here_patterns.copy()
        local[15] += successes
        local[0] += group_size - int(triggered_here) - successes
        joint_patterns.append(tuple(int(value) for value in local))
    expected_content = gamma * (marginals[0] - marginals[1])
    expected_excess = gamma * (marginals[0] - (marginals[2] + marginals[3]) / 2.0)
    return BenchmarkPatternCounts(
        tuple(int(value) for value in triggered_patterns + no_trigger_patterns),
        tuple(int(value) for value in triggered_patterns),
        tuple(int(value) for value in no_trigger_patterns),
        tuple(joint_patterns),
        triggered_count, expected_content, expected_excess,
    )


def evaluate_simulated_pattern_batch(
    swe: BenchmarkPatternCounts, tau: BenchmarkPatternCounts, *, roster_ref: ArtifactRef,
    critical_value: float,
    joint_group_labels: tuple[
        tuple[tuple[GroupLabel, ...], ...], tuple[tuple[GroupLabel, ...], ...],
    ] | None = None,
) -> GateBatchResult:
    """Route synthetic sufficient statistics through the authoritative Task-7 gate."""
    if type(roster_ref) is not ArtifactRef:
        raise TypeError("simulated batch requires the manifest-derived roster ArtifactRef")
    group_manifest: list[tuple[str, GroupLabel | None]] = [("SWE", None), ("TAU", None)]
    rows: list[tuple[int, ...]] = [swe.pattern_counts, tau.pattern_counts]
    if joint_group_labels is not None:
        for benchmark, counts, labels_by_joint_cell in (
            ("SWE", swe, joint_group_labels[0]), ("TAU", tau, joint_group_labels[1]),
        ):
            if len(labels_by_joint_cell) != len(counts.joint_group_pattern_counts):
                raise RecordValidationError("joint group labels do not match simulated group cells")
            labels = tuple(sorted({label for cell in labels_by_joint_cell for label in cell}, key=lambda label: (label.kind.value, label.value)))
            for label in labels:
                group_manifest.append((benchmark, label))
                rows.append(tuple(sum(pattern[index] for pattern, cell in zip(counts.joint_group_pattern_counts, labels_by_joint_cell, strict=True) if label in cell) for index in range(16)))
    patterns = np.asarray([rows], dtype=np.int64)
    batch = BinarySufficientStatisticsBatch(
        roster_ref=roster_ref,
        group_manifest=tuple(group_manifest),
        pattern_counts=patterns,
        arm_failure_counts=np.zeros((1, 2, 4), dtype=np.int64),
        pipeline_invalid_counts=np.zeros(1, dtype=np.int64),
    )
    return evaluate_binary_gate_batch(
        batch, AnalysisConfig(), critical_values=np.asarray([critical_value]),
    )


def _batch_group_manifest_and_patterns(
    rows: tuple[tuple[BenchmarkPatternCounts, BenchmarkPatternCounts], ...],
    joint_group_labels: tuple[
        tuple[tuple[GroupLabel, ...], ...], tuple[tuple[GroupLabel, ...], ...],
    ] | None,
) -> tuple[tuple[tuple[str, GroupLabel | None], ...], np.ndarray]:
    """Preserve each roster label's count tensor for Task-7 leave-one gates."""
    manifest: list[tuple[str, GroupLabel | None]] = [("SWE", None), ("TAU", None)]
    labels_by_benchmark: tuple[tuple[GroupLabel, ...], tuple[GroupLabel, ...]] = ((), ())
    if joint_group_labels is not None:
        labels_by_benchmark = tuple(
            tuple(sorted({label for cell in labels for label in cell}, key=lambda label: (label.kind.value, label.value)))
            for labels in joint_group_labels
        )  # type: ignore[assignment]
        manifest.extend((benchmark, label) for benchmark, labels in zip(("SWE", "TAU"), labels_by_benchmark, strict=True) for label in labels)
    tensor: list[list[tuple[int, ...]]] = []
    for swe, tau in rows:
        entries: list[tuple[int, ...]] = [swe.pattern_counts, tau.pattern_counts]
        if joint_group_labels is not None:
            for counts, labels_by_cell, labels in zip((swe, tau), joint_group_labels, labels_by_benchmark, strict=True):
                if len(counts.joint_group_pattern_counts) != len(labels_by_cell):
                    raise RecordValidationError("joint group labels do not match simulated group cells")
                entries.extend(tuple(sum(pattern[index] for pattern, cell in zip(counts.joint_group_pattern_counts, labels_by_cell, strict=True) if label in cell) for index in range(16)) for label in labels)
        tensor.append(entries)
    return tuple(manifest), np.asarray(tensor, dtype=np.int64)


def _raw_contrast_rows(counts: BenchmarkPatternCounts) -> np.ndarray:
    """Expand only one 20-task sufficient-statistic tensor for multiplier work.

    This is deliberately local and ephemeral: validation stores counts and
    commitments, never task-level simulated outcomes.
    """
    patterns = np.asarray(counts.pattern_counts[:16], dtype=np.int64)
    rows: list[tuple[float, float]] = []
    for index, count in enumerate(patterns):
        r, s, n, z = ((index >> shift) & 1 for shift in (3, 2, 1, 0))
        rows.extend(((float(r - s), float(r - (n + z) / 2.0)),) * int(count))
    result = np.asarray(rows, dtype=float)
    if result.shape != (sum(counts.pattern_counts[:16]), 2):
        raise RecordValidationError("raw multiplier rows do not reconstruct the count tensor")
    return result


def full_multiplier_gate_pass(
    swe: BenchmarkPatternCounts, tau: BenchmarkPatternCounts, *, authority_kind: str,
    tier_membership_sha256: str, grid_content_digest: str, phase: str, cell_id: str,
    replicate_index: int, multiplier_draws: int,
) -> bool:
    """Run the registered 99,999-draw Rademacher max comparison on raw counts.

    The implementation intentionally has no Gaussian critical-value fallback:
    callers either execute this exact bounded routine or do not claim a
    multiplier result.
    """
    if type(multiplier_draws) is not int or multiplier_draws != 99999:
        raise RecordValidationError("full multiplier validation requires exactly 99,999 draws")
    rows = np.concatenate((_raw_contrast_rows(swe), _raw_contrast_rows(tau)), axis=0)
    if rows.shape[0] != 40:
        raise RecordValidationError("full multiplier validation requires two n=20 benchmarks")
    observed = rows.mean(axis=0)
    centered = rows - observed
    scale = np.sqrt(np.mean(centered * centered, axis=0) / rows.shape[0])
    if np.any(scale <= 0.0):
        return False
    observed_z = observed / scale
    rng = philox_generator(authority_kind, tier_membership_sha256, grid_content_digest,
                           "validation", phase, cell_id, replicate_index,
                           "multiplier_rademacher", 0)
    # Bounded memory (~32 MB) and all raw-count operations stay in-process.
    signs = rng.integers(0, 2, size=(multiplier_draws, rows.shape[0]), dtype=np.int8) * 2 - 1
    draws = (signs @ centered) / rows.shape[0] / scale
    critical = np.sort(np.max(draws, axis=1))[int(np.ceil((1.0 - 0.05) * multiplier_draws)) - 1]
    return bool(np.all(observed_z >= critical))


def pattern_count_digest(counts: BenchmarkPatternCounts) -> str:
    """Stable leaf commitment for one regenerated benchmark/replicate tensor."""
    return hashlib.sha256(canonical_json_bytes({
        "pattern_counts": list(counts.pattern_counts), "triggered_count": counts.triggered_count,
        "joint_group_pattern_counts": [list(row) for row in counts.joint_group_pattern_counts],
    }, indent=None)).hexdigest()


def merkle_root(leaves: tuple[str, ...]) -> str:
    """Domain-separated duplicate-last Merkle root; no raw-count artifact exists."""
    if not leaves or any(type(leaf) is not str or len(leaf) != 64 for leaf in leaves):
        raise RecordValidationError("Merkle commitment requires non-empty SHA-256 leaves")
    level = [bytes.fromhex(value) for value in leaves]
    while len(level) > 1:
        if len(level) & 1:
            level.append(level[-1])
        level = [hashlib.sha256(b"p0-count-merkle-v1\\0" + level[i] + level[i + 1]).digest()
                 for i in range(0, len(level), 2)]
    return level[0].hex()


def replay_pattern_chunk(cell: PowerCell, *, authority: PowerAuthority, grid_digest: str, phase: str,
                         roster_group_sizes: tuple[tuple[int, ...], tuple[int, ...]], start: int, count: int,
                         draw_domain: Literal["screen", "grid", "validation"] = "grid") -> tuple[tuple[BenchmarkPatternCounts, BenchmarkPatternCounts], ...]:
    """Regenerate a bounded count-tensor chunk from per-replicate Philox identities."""
    if type(start) is not int or type(count) is not int or start < 0 or not 0 < count <= 256:
        raise RecordValidationError("replay chunks must be bounded to 1..256 exact replicates")
    result = []
    for replicate in range(start, start + count):
        result.append((
            simulate_benchmark_pattern_counts(p0=cell.swe.p0, gamma=cell.swe.trigger_rate, rho=cell.swe.rho, family=cell.family, task_count=sum(roster_group_sizes[0]), authority_kind=authority.authority_kind, tier_membership_sha256=authority.tier_membership_sha256, grid_content_digest=grid_digest, phase=phase, cell_id=cell.cell_id, replicate_index=replicate, joint_group_sizes=roster_group_sizes[0], draw_domain=draw_domain),
            simulate_benchmark_pattern_counts(p0=cell.tau.p0, gamma=cell.tau.trigger_rate, rho=cell.tau.rho, family=cell.family, task_count=sum(roster_group_sizes[1]), authority_kind=authority.authority_kind, tier_membership_sha256=authority.tier_membership_sha256, grid_content_digest=grid_digest, phase=phase, cell_id=cell.cell_id, replicate_index=replicate, joint_group_sizes=roster_group_sizes[1], draw_domain=draw_domain),
        ))
    return tuple(result)


def power_replay_receipt(cell: PowerCell, *, authority: PowerAuthority, grid_digest: str, phase: str,
                         roster_group_sizes: tuple[tuple[int, ...], tuple[int, ...]], dataset_count: int,
                         replay_start: int = 0, replay_count: int = 8) -> dict[str, object]:
    rows = replay_pattern_chunk(cell, authority=authority, grid_digest=grid_digest, phase=phase, roster_group_sizes=roster_group_sizes, start=replay_start, count=replay_count)
    leaves = tuple(hashlib.sha256((pattern_count_digest(swe) + pattern_count_digest(tau)).encode("ascii")).hexdigest() for swe, tau in rows)
    layout = hashlib.sha256(canonical_json_bytes({"SWE": list(roster_group_sizes[0]), "TAU": list(roster_group_sizes[1])}, indent=None)).hexdigest()
    return {"contract_id": "p0-count-replay-merkle-v1", "cell_id": cell.cell_id, "authority_kind": authority.authority_kind, "tier_membership_sha256": authority.tier_membership_sha256, "grid_content_sha256": grid_digest, "phase": phase, "dataset_count": dataset_count, "group_layout_sha256": layout, "replay_start": replay_start, "replay_count": replay_count, "leaf_sha256s": list(leaves), "merkle_root_sha256": merkle_root(leaves)}


def validate_power_replay_receipt(receipt: Mapping[str, object], cell: PowerCell, *, authority: PowerAuthority,
                                  grid_digest: str, phase: str, roster_group_sizes: tuple[tuple[int, ...], tuple[int, ...]]) -> None:
    expected = power_replay_receipt(cell, authority=authority, grid_digest=grid_digest, phase=phase, roster_group_sizes=roster_group_sizes, dataset_count=cast(int, receipt.get("dataset_count")), replay_start=cast(int, receipt.get("replay_start")), replay_count=cast(int, receipt.get("replay_count")))
    if dict(receipt) != expected:
        raise RecordValidationError("power replay/Merkle receipt differs from regenerated count tensors")


def bivariate_normal_cdf_equal_threshold(threshold: float, rho: float) -> float:
    """Plackett integral, with exact correlation endpoints."""
    if not -1.0 - 1e-12 <= rho <= 1.0 + 1e-12:
        raise ValueError("correlation must be in [-1, 1]")
    rho = min(1.0, max(-1.0, rho))
    if rho == 1.0:
        return _phi(threshold)
    if rho == -1.0:
        return max(0.0, 2.0 * _phi(threshold) - 1.0)
    nodes, weights = np.polynomial.legendre.leggauss(GAUSS_LEGENDRE_ORDER)
    lo, hi = 0.0, rho
    points = (hi - lo) * (nodes + 1.0) / 2.0 + lo
    density = np.exp(-(threshold * threshold) / (1.0 + points)) / (2.0 * pi * np.sqrt(1.0 - points * points))
    return _phi(threshold) ** 2 + float((hi - lo) * np.dot(weights, density) / 2.0)


def gaussian_max_critical(correlation: float, alpha: float) -> float:
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be a strict probability")
    if correlation >= 1.0 - 1e-12:
        return _NORMAL.inv_cdf(1.0 - alpha)
    if correlation <= -1.0 + 1e-12:
        return _NORMAL.inv_cdf(1.0 - alpha / 2.0)
    low, high = -10.0, 10.0
    for _ in range(GAUSSIAN_ROOT_MAX_ITERATIONS):
        midpoint = (low + high) / 2.0
        if bivariate_normal_cdf_equal_threshold(midpoint, correlation) < 1.0 - alpha:
            low = midpoint
        else:
            high = midpoint
        if high - low <= GAUSSIAN_ROOT_TOLERANCE:
            break
    return (low + high) / 2.0


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    """Lentz evaluation of the incomplete-beta continued fraction."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = tiny if abs(d) < tiny else d
    d = 1.0 / d
    result = d
    for iteration in range(1, 201):
        doubled = 2 * iteration
        aa = iteration * (b - iteration) * x / ((qam + doubled) * (a + doubled))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        result *= d * c
        aa = -(a + iteration) * (qab + iteration) * x / ((a + doubled) * (qap + doubled))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) <= 3e-14:
            return result
    raise RecordValidationError("binomial-tail continued fraction did not converge")


def _regularized_beta(x: float, a: float, b: float) -> float:
    if not 0.0 <= x <= 1.0 or a <= 0.0 or b <= 0.0:
        raise ValueError("regularized beta arguments are outside their domain")
    if x == 0.0 or x == 1.0:
        return x
    front = exp(lgamma(a + b) - lgamma(a) - lgamma(b) + a * log(x) + b * log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_continued_fraction(a, b, x) / a
    return 1.0 - front * _beta_continued_fraction(b, a, 1.0 - x) / b


def _binomial_cdf(successes: int, trials: int, probability: float) -> float:
    """Stable binomial CDF through the regularized-beta identity.

    Direct ``comb`` summation over 20,000 trials overflows before the power
    protocol reaches its first validation receipt.
    """
    if not 0 <= successes <= trials or not 0.0 <= probability <= 1.0:
        raise ValueError("binomial CDF arguments are outside their domain")
    if successes == trials or probability == 0.0:
        return 1.0
    if probability == 1.0:
        return 0.0
    return _regularized_beta(1.0 - probability, trials - successes, successes + 1)


def clopper_pearson_lower(successes: int, trials: int, *, tail_probability: float) -> float:
    if successes == 0:
        return 0.0
    low, high = 0.0, 1.0
    for _ in range(CLOPPER_PEARSON_MAX_ITERATIONS):
        middle = (low + high) / 2.0
        # P[X >= successes] = tail at the lower endpoint.
        if 1.0 - _binomial_cdf(successes - 1, trials, middle) < tail_probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def clopper_pearson_upper(successes: int, trials: int, *, tail_probability: float) -> float:
    if successes == trials:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(CLOPPER_PEARSON_MAX_ITERATIONS):
        middle = (low + high) / 2.0
        # P[X <= successes] = tail at the upper endpoint.
        if _binomial_cdf(successes, trials, middle) > tail_probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def philox_generator(
    authority_kind: str, tier_membership_sha256: str, grid_content_digest: str,
    draw_domain: str, phase: str, cell_id: str, replicate_index: int,
    draw_kind: str, draw_index: int,
) -> np.random.Generator:
    """Fresh, public counter/key mapping; no state can leak across draws."""
    if authority_kind not in {"synthetic_validation", "roster_bound_selection"}:
        raise RecordValidationError("unregistered power authority kind")
    if draw_domain not in _RNG_CONTRACT["draw_domains"] or draw_kind not in _RNG_CONTRACT["draw_kinds"]:
        raise RecordValidationError("unregistered Philox draw domain or kind")
    for value, field in ((tier_membership_sha256, "tier_membership_sha256"), (grid_content_digest, "grid_content_sha256")):
        _strict_sha256(value, field=field)
    if type(replicate_index) is not int or type(draw_index) is not int or replicate_index < 0 or draw_index < 0:
        raise RecordValidationError("Philox replicate and draw indices must be nonnegative integers")
    key_bytes = hashlib.sha256(kdf_frame("power-rng-key-v1", [
        U64Field(7640891576956012809), TextField(authority_kind),
        BytesField(bytes.fromhex(tier_membership_sha256)), BytesField(bytes.fromhex(grid_content_digest)),
    ])).digest()[:16]
    counter_bytes = hashlib.sha256(kdf_frame("power-rng-counter-v1", [
        TextField(draw_domain), TextField(phase), TextField(cell_id), U64Field(replicate_index),
        TextField(draw_kind), U64Field(draw_index),
    ])).digest()
    return np.random.Generator(np.random.Philox(
        counter=int.from_bytes(counter_bytes, "big"), key=int.from_bytes(key_bytes, "big"),
    ))


@dataclass(frozen=True, slots=True)
class SyntheticPowerAuthority:
    schema_version: Literal["1"]
    authority_kind: Literal["synthetic_validation"]
    manifest_ref: ArtifactRef
    roster_ref: ArtifactRef
    tier_membership_sha256: str


@dataclass(frozen=True, slots=True)
class RosterBoundPowerAuthority:
    schema_version: Literal["1"]
    authority_kind: Literal["roster_bound_selection"]
    manifest_ref: ArtifactRef
    eligibility_manifest_ref: ArtifactRef
    roster_ref: ArtifactRef
    tier_membership_sha256: str


PowerAuthority = SyntheticPowerAuthority | RosterBoundPowerAuthority


@dataclass(frozen=True, slots=True)
class PowerRngContract:
    contract_id: Literal["power-philox-v1"]
    bit_generator: Literal["numpy.random.Philox"]
    counter_fields: tuple[str, ...]
    counter_frame: Literal["power-rng-counter-v1"]
    draw_domains: tuple[str, ...]
    draw_kinds: tuple[str, ...]
    integer_encoding: Literal["unsigned-big-endian"]
    key_fields: tuple[str, ...]
    key_frame: Literal["power-rng-key-v1"]
    numpy_version: Literal["2.3.5"]
    root_u64: Literal[7640891576956012809]


@dataclass(frozen=True, slots=True)
class PowerGridSpec:
    schema_version: Literal["1"]
    benchmark_tiers: tuple[Literal[120], Literal[160]]
    p0_values: tuple[float, float, float]
    trigger_rates: tuple[float, float, float]
    latent_rhos: tuple[float, float, float]
    datasets_per_cell: int
    screen_datasets_per_cell: int
    max_projected_wall_seconds: int
    validation_cell_count: int
    validation_datasets_per_cell: int
    multiplier_draws: int
    target_effect: float
    target_power: float
    familywise_alpha: float
    gauss_hermite_order: int
    gauss_legendre_order: int
    probability_tolerance: float
    gaussian_root_tolerance: float
    gaussian_root_max_iterations: int
    clopper_pearson_tolerance: float
    clopper_pearson_max_iterations: int
    rng: PowerRngContract


@dataclass(frozen=True, slots=True)
class PowerConfig:
    authority_ref: ArtifactRef
    grid_ref: ArtifactRef
    screen_topology_ref: ArtifactRef
    rng_contract_sha256: str


def _strict_sha256(value: object, *, field: str) -> str:
    if type(value) is not str or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise RecordValidationError(f"{field} must be a lowercase SHA-256 digest")
    return cast(str, value)


def _manifest(ref: ArtifactRef, *, run_root: Path) -> Mapping[str, object]:
    document = _load_direct_scientific_parent(
        _ref_mapping(ref), run_root=run_root, field="manifest_ref", expected_kind="resampling_study_manifest"
    )
    payload = document.value["payload"]
    if not isinstance(payload, Mapping):
        raise RecordValidationError("study manifest payload must be an object")
    return payload


def _manifest_study_id(ref: ArtifactRef, *, run_root: Path) -> str:
    document = _load_direct_scientific_parent(
        _ref_mapping(ref), run_root=run_root, field="manifest_ref", expected_kind="resampling_study_manifest"
    )
    study_id = document.value["study_id"]
    if type(study_id) is not str or not study_id:
        raise RecordValidationError("study manifest has invalid study_id")
    return study_id


def _manifest_frozen_created_at(ref: ArtifactRef, *, run_root: Path) -> str:
    document = _load_direct_scientific_parent(
        _ref_mapping(ref), run_root=run_root, field="manifest_ref", expected_kind="resampling_study_manifest"
    )
    value = document.value["frozen_created_at"]
    if type(value) is not str or not value:
        raise RecordValidationError("study manifest has invalid frozen_created_at")
    return value


def _manifest_ref(payload: Mapping[str, object], name: str) -> ArtifactRef:
    return decode_artifact_ref(payload.get(name), field=f"manifest {name}")


def _load_roster(ref: ArtifactRef, *, run_root: Path) -> Mapping[str, object]:
    path, raw = _read_ref(ref, run_root=run_root)
    decoded = load_json_bytes(raw, source=path)
    roster = closed_mapping(decoded, fields={"record_kind", "schema_version", "roster_kind", "supported_tiers", "tasks"}, field="power roster")
    if roster["record_kind"] != "resampling_roster_v1" or roster["schema_version"] != "1":
        raise RecordValidationError("power roster has wrong identity")
    if roster["roster_kind"] not in {"synthetic_fixture", "eligible_confirmation"}:
        raise RecordValidationError("power roster has unsupported roster_kind")
    return roster


def _roster_rows(roster: Mapping[str, object]) -> dict[str, tuple[tuple[int, ...], tuple[tuple[str, str], ...]]]:
    """Return the exact accepted identity/tier/group surface for confirmation."""
    rows: dict[str, tuple[tuple[int, ...], tuple[tuple[str, str], ...]]] = {}
    for index, task_value in enumerate(cast(list[object], roster["tasks"])):
        task = closed_mapping(task_value, fields={"task_id", "benchmark", "stratum", "lineage", "groups", "tiers"}, field=f"power roster task[{index}]")
        task_id = task["task_id"]
        if type(task_id) is not str or not task_id or task_id in rows:
            raise RecordValidationError("power roster task IDs must be unique strict text")
        tiers = task["tiers"]
        groups = task["groups"]
        if not isinstance(tiers, list) or not isinstance(groups, list):
            raise RecordValidationError("power roster tiers/groups must be arrays")
        group_rows: list[tuple[str, str]] = []
        for group_index, group_value in enumerate(groups):
            group = closed_mapping(group_value, fields={"kind", "value"}, field=f"power roster task[{index}].groups[{group_index}]")
            if type(group["kind"]) is not str or type(group["value"]) is not str:
                raise RecordValidationError("power roster group fields must be strict text")
            group_rows.append((cast(str, group["kind"]), cast(str, group["value"])))
        rows[task_id] = (tuple(cast(list[int], tiers)), tuple(group_rows))
    return rows


def _validate_confirmation_eligibility(
    eligibility_ref: ArtifactRef,
    roster: Mapping[str, object],
    *,
    study_id: str,
    frozen_created_at: str,
    manifest_payload: Mapping[str, object],
    run_root: Path,
) -> None:
    """Prove the manifest-pinned eligibility source derives this exact roster.

    This is intentionally a closed source grammar.  A file that merely exists
    is not evidence of confirmation eligibility—cute try, attacker.
    """
    path, raw = _read_ref(eligibility_ref, run_root=run_root)
    value = load_json_bytes(raw, source=path)
    fields = {
        "record_kind", "schema_version", "study_id", "precommit", "precommit_sha256",
        "timestamp_receipt", "beacon_receipt", "roster_local_nonce_hex", "roster_seed_sha256",
        "accepted_task_ids", "rejected_task_ids", "tier_membership", "group_labels", "reserves",
    }
    eligibility = closed_mapping(value, fields=fields, field="confirmation eligibility manifest")
    if eligibility["record_kind"] != "resampling_eligibility_manifest_v1" or eligibility["schema_version"] != "1" or eligibility["study_id"] != study_id:
        raise RecordValidationError("confirmation eligibility manifest has wrong identity or study_id")
    precommit = closed_mapping(eligibility["precommit"], fields={"study_id", "qualification_universe_sha256", "roster_local_nonce_commitment_sha256", "schedule_seed_commitment_sha256", "assignment_master_key_commitment_sha256"}, field="confirmation eligibility precommit")
    if precommit["study_id"] != study_id:
        raise RecordValidationError("confirmation eligibility precommit study_id differs")
    for field in ("qualification_universe_sha256", "roster_local_nonce_commitment_sha256", "schedule_seed_commitment_sha256", "assignment_master_key_commitment_sha256"):
        _strict_sha256(precommit[field], field=f"confirmation eligibility precommit {field}")
    precommit_digest = hashlib.sha256(canonical_json_bytes(precommit, indent=None)).hexdigest()
    if eligibility["precommit_sha256"] != precommit_digest:
        raise RecordValidationError("confirmation eligibility precommit_sha256 does not bind precommit bytes")
    timestamp = closed_mapping(eligibility["timestamp_receipt"], fields={"precommit_sha256", "timestamp"}, field="confirmation eligibility timestamp receipt")
    if timestamp["precommit_sha256"] != precommit_digest or timestamp["timestamp"] != frozen_created_at:
        raise RecordValidationError("confirmation eligibility timestamp receipt does not bind precommit")
    beacon = closed_mapping(eligibility["beacon_receipt"], fields={"chain_hash", "round", "randomness_hex"}, field="confirmation eligibility beacon receipt")
    if beacon["chain_hash"] != "8990e7a9aaed2ffed73dbd7092123d6f289930540d7651336225dc172e51b2ce" or type(beacon["round"]) is not int or beacon["round"] < 0 or type(beacon["randomness_hex"]) is not str:
        raise RecordValidationError("confirmation eligibility beacon receipt has invalid frozen contract")
    try:
        nonce = bytes.fromhex(cast(str, eligibility["roster_local_nonce_hex"]))
        randomness = bytes.fromhex(cast(str, beacon["randomness_hex"]))
    except ValueError as exc:
        raise RecordValidationError("confirmation eligibility nonce/beacon randomness must be hex") from exc
    if len(nonce) != 32 or len(randomness) != 32:
        raise RecordValidationError("confirmation eligibility nonce/beacon randomness must be 32 bytes")
    for field in ("roster_local_nonce_commitment_sha256", "schedule_seed_commitment_sha256", "assignment_master_key_commitment_sha256"):
        if precommit[field] != manifest_payload[field]:
            raise RecordValidationError(f"confirmation eligibility precommit {field} differs from study manifest")
    expected_nonce_commitment = commitment_sha256(
        "roster-local-nonce", study_id, BytesField(nonce)
    )
    if expected_nonce_commitment != manifest_payload["roster_local_nonce_commitment_sha256"]:
        raise RecordValidationError("confirmation eligibility nonce reveal does not match study manifest commitment")
    expected_seed = hashlib.sha256(kdf_frame("roster-seed-v1", [
        BytesField(bytes.fromhex(precommit_digest)), BytesField(nonce),
        BytesField(bytes.fromhex(cast(str, beacon["chain_hash"]))),
        U64Field(cast(int, beacon["round"])), BytesField(randomness),
    ])).hexdigest()
    if eligibility["roster_seed_sha256"] != expected_seed:
        raise RecordValidationError("confirmation eligibility roster_seed_sha256 is not the derived ceremony seed")
    accepted = eligibility["accepted_task_ids"]
    rejected = eligibility["rejected_task_ids"]
    if not isinstance(accepted, list) or not isinstance(rejected, list) or any(type(value) is not str or not value for value in [*accepted, *rejected]) or accepted != sorted(set(accepted)) or rejected != sorted(set(rejected)) or set(accepted) & set(rejected):
        raise RecordValidationError("confirmation eligibility accepted/rejected task IDs must be disjoint strict sorted sets")
    roster_rows = _roster_rows(roster)
    if accepted != sorted(roster_rows):
        raise RecordValidationError("confirmation eligibility accepted task IDs do not exactly reproduce roster")
    memberships = closed_mapping(eligibility["tier_membership"], fields={"120", "160"}, field="confirmation eligibility tier_membership")
    tier_ids: dict[int, list[str]] = {}
    for tier in (120, 160):
        values = memberships[str(tier)]
        if not isinstance(values, list) or any(type(value) is not str for value in values) or values != sorted(set(values)):
            raise RecordValidationError("confirmation eligibility tier membership must be sorted unique task IDs")
        tier_ids[tier] = cast(list[str], values)
        if set(values) != {task_id for task_id, (tiers, _groups) in roster_rows.items() if tier in tiers}:
            raise RecordValidationError("confirmation eligibility tier membership differs from roster")
    if not set(tier_ids[160]).issubset(tier_ids[120]):
        raise RecordValidationError("confirmation eligibility C160 membership must be nested in C120")
    labels = eligibility["group_labels"]
    if not isinstance(labels, Mapping) or set(labels) != set(roster_rows):
        raise RecordValidationError("confirmation eligibility group labels must exactly cover roster")
    for task_id, (_tiers, expected_groups) in roster_rows.items():
        groups = labels[task_id]
        if not isinstance(groups, list):
            raise RecordValidationError("confirmation eligibility group labels must be arrays")
        actual: list[tuple[str, str]] = []
        for group_index, group_value in enumerate(groups):
            group = closed_mapping(group_value, fields={"kind", "value"}, field=f"confirmation eligibility group_labels.{task_id}[{group_index}]")
            if type(group["kind"]) is not str or type(group["value"]) is not str:
                raise RecordValidationError("confirmation eligibility group label must use strict text")
            actual.append((cast(str, group["kind"]), cast(str, group["value"])))
        if tuple(actual) != expected_groups:
            raise RecordValidationError("confirmation eligibility group labels differ from roster")
    reserves = eligibility["reserves"]
    if not isinstance(reserves, list) or any(type(value) is not str or not value for value in reserves) or reserves != sorted(set(reserves)) or set(reserves) & set(accepted):
        raise RecordValidationError("confirmation eligibility reserves must be ordered, unique, and disjoint from accepted roster")


def _tier_membership_sha256(roster: Mapping[str, object]) -> str:
    tasks = roster["tasks"]
    if not isinstance(tasks, list) or not tasks:
        raise RecordValidationError("power roster tasks must be a non-empty array")
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    group_order = {"language": 0, "domain": 1, "issue_family": 2}
    for index, task_value in enumerate(tasks):
        task = closed_mapping(task_value, fields={"task_id", "benchmark", "stratum", "lineage", "groups", "tiers"}, field=f"power roster task[{index}]")
        task_id, benchmark = task["task_id"], task["benchmark"]
        if type(task_id) is not str or type(benchmark) is not str or not task_id or not benchmark:
            raise RecordValidationError("power roster task identity must be non-empty strict text")
        identity = (benchmark, task_id)
        if identity in seen:
            raise RecordValidationError("power roster tasks must have unique benchmark/task_id")
        seen.add(identity)
        tiers = task["tiers"]
        if not isinstance(tiers, list) or not tiers or any(type(tier) is not int for tier in tiers) or tiers != sorted(set(tiers)) or any(tier not in (120, 160) for tier in tiers):
            raise RecordValidationError("power roster tiers must be a strict non-empty C120/C160 subset")
        groups_value = task["groups"]
        if not isinstance(groups_value, list):
            raise RecordValidationError("power roster groups must be an array")
        groups: list[dict[str, str]] = []
        group_keys: list[tuple[int, str]] = []
        for group_index, group_value in enumerate(groups_value):
            group = closed_mapping(group_value, fields={"kind", "value"}, field=f"power roster task[{index}].groups[{group_index}]")
            kind, value = group["kind"], group["value"]
            if type(kind) is not str or type(value) is not str or not value or kind not in group_order:
                raise RecordValidationError("power roster group must use a registered non-empty kind/value")
            group_keys.append((group_order[kind], value))
            groups.append({"kind": kind, "value": value})
        if group_keys != sorted(set(group_keys)):
            raise RecordValidationError("power roster groups must be unique in frozen kind/value order")
        rows.append({"benchmark": benchmark, "groups": groups, "task_id": task_id, "tiers": tiers})
    if [(row["benchmark"], row["task_id"]) for row in rows] != sorted((row["benchmark"], row["task_id"]) for row in rows):
        raise RecordValidationError("power roster tasks must be UTF-8 ordered by benchmark/task_id")
    return hashlib.sha256(canonical_json_bytes({"rows": rows, "schema_version": "1"}, indent=None)).hexdigest()


def _authority_from_manifest(manifest_ref: ArtifactRef, *, run_root: Path, expected_kind: str) -> PowerAuthority:
    manifest = _manifest(manifest_ref, run_root=run_root)
    roster_ref = _manifest_ref(manifest, "roster_ref")
    roster = _load_roster(roster_ref, run_root=run_root)
    eligibility = manifest.get("eligibility_manifest_ref")
    membership = _tier_membership_sha256(roster)
    if expected_kind == "synthetic_validation":
        if roster["roster_kind"] != "synthetic_fixture" or eligibility is not None:
            raise RecordValidationError("synthetic authority requires synthetic_fixture and null eligibility_manifest_ref")
        return SyntheticPowerAuthority("1", "synthetic_validation", manifest_ref, roster_ref, membership)
    if roster["roster_kind"] != "eligible_confirmation":
        raise RecordValidationError("roster-bound authority requires eligible_confirmation roster")
    # `ConfirmationPreflightRegistry` deliberately exposes no reviewed live
    # ceremony adapter.  A local JSON beacon/timestamp receipt cannot prove it
    # was externally authenticated, so accepting one here would mint false
    # confirmation authority.  Future support must arrive through a
    # manifest-approved opaque capability, never a caller callback or blob.
    raise RecordValidationError(
        "roster-bound power authority unavailable: no reviewed verified ceremony adapter"
    )


def _authority_value(authority: PowerAuthority) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": authority.schema_version,
        "authority_kind": authority.authority_kind,
        "manifest_ref": _ref_mapping(authority.manifest_ref),
        "roster_ref": _ref_mapping(authority.roster_ref),
        "tier_membership_sha256": authority.tier_membership_sha256,
    }
    if isinstance(authority, RosterBoundPowerAuthority):
        value["eligibility_manifest_ref"] = _ref_mapping(authority.eligibility_manifest_ref)
    return value


def _seal(authority: PowerAuthority, *, run_root: Path, out: Path) -> ArtifactRef:
    target, _ = _prepare_destination(out, run_root)
    write_atomic_bytes(target, canonical_json_bytes(_authority_value(authority), indent=None))
    return _artifact_ref_for_path(target, run_root, "power_authority", POWER_AUTHORITY_MEDIA_TYPE)


def seal_synthetic_power_authority(manifest_ref: ArtifactRef, *, run_root: Path, out: Path) -> ArtifactRef:
    """Seal the sole synthetic arm derived from the referenced manifest."""
    if type(manifest_ref) is not ArtifactRef:
        raise TypeError("manifest_ref must be an exact ArtifactRef")
    return _seal(_authority_from_manifest(manifest_ref, run_root=run_root, expected_kind="synthetic_validation"), run_root=run_root, out=out)


def seal_roster_bound_power_authority(manifest_ref: ArtifactRef, *, run_root: Path, out: Path) -> ArtifactRef:
    """Seal the sole confirmation arm; no eligibility/roster override exists."""
    if type(manifest_ref) is not ArtifactRef:
        raise TypeError("manifest_ref must be an exact ArtifactRef")
    return _seal(_authority_from_manifest(manifest_ref, run_root=run_root, expected_kind="roster_bound_selection"), run_root=run_root, out=out)


def load_power_authority(authority_ref: ArtifactRef, *, run_root: Path) -> PowerAuthority:
    """Load canonical blob bytes and repeat all manifest/roster proofs."""
    if type(authority_ref) is not ArtifactRef or authority_ref.media_type != POWER_AUTHORITY_MEDIA_TYPE:
        raise RecordValidationError("power authority_ref must use the closed power-authority media type")
    path, raw = _read_ref(authority_ref, run_root=run_root)
    value = load_json_bytes(raw, source=path)
    if canonical_json_bytes(value, indent=None) != raw:
        raise RecordValidationError("power authority bytes must be compact canonical JSON")
    if not isinstance(value, Mapping):
        raise RecordValidationError("power authority must be a JSON object")
    kind = value.get("authority_kind")
    fields = _AUTHORITY_COMMON_FIELDS | ({"eligibility_manifest_ref"} if kind == "roster_bound_selection" else set())
    decoded = closed_mapping(value, fields=fields, field="power authority")
    if decoded["schema_version"] != "1" or kind not in {"synthetic_validation", "roster_bound_selection"}:
        raise RecordValidationError("power authority has unsupported identity")
    manifest_ref = decode_artifact_ref(decoded["manifest_ref"], field="power authority manifest_ref")
    expected = _authority_from_manifest(manifest_ref, run_root=run_root, expected_kind=cast(str, kind))
    if _authority_value(expected) != dict(decoded):
        raise RecordValidationError("power authority differs from manifest-derived closed authority")
    return expected


def _load_power_grid(grid_ref: ArtifactRef, *, run_root: Path) -> PowerGridSpec:
    """Decode the exact manifest fixture; all numeric science stays closed."""
    path, raw = _read_ref(grid_ref, run_root=run_root)
    value = load_json_bytes(raw, source=path)
    expected_fields = {
        "schema_version", "benchmark_tiers", "p0_values", "trigger_rates", "latent_rhos",
        "datasets_per_cell", "screen_datasets_per_cell", "max_projected_wall_seconds",
        "validation_cell_count", "validation_datasets_per_cell", "multiplier_draws",
        "target_effect", "target_power", "familywise_alpha", "gauss_hermite_order",
        "gauss_legendre_order", "probability_tolerance", "gaussian_root_tolerance",
        "gaussian_root_max_iterations", "clopper_pearson_tolerance", "clopper_pearson_max_iterations", "rng",
    }
    grid = closed_mapping(value, fields=expected_fields, field="power grid")
    if grid["schema_version"] != "1":
        raise RecordValidationError("power grid has unsupported schema_version")
    if grid["benchmark_tiers"] != [120, 160] or grid["p0_values"] != [0.1, 0.4, 0.7] or grid["trigger_rates"] != [0.6, 0.75, 0.9] or grid["latent_rhos"] != [0.0, 0.4, 0.8]:
        raise RecordValidationError("power grid does not contain the frozen P0 nuisance grid")
    for field, expected in (("datasets_per_cell", 20000), ("screen_datasets_per_cell", 200), ("max_projected_wall_seconds", 43200), ("validation_cell_count", 5), ("validation_datasets_per_cell", 2000), ("multiplier_draws", 99999), ("target_effect", 0.15), ("target_power", 0.8), ("familywise_alpha", 0.05), ("gauss_hermite_order", 96), ("gauss_legendre_order", 128), ("probability_tolerance", 1e-10), ("gaussian_root_tolerance", 1e-10), ("gaussian_root_max_iterations", 200), ("clopper_pearson_tolerance", 1e-12), ("clopper_pearson_max_iterations", 200)):
        if grid[field] != expected:
            raise RecordValidationError(f"power grid {field} differs from the frozen P0 contract")
    rng = closed_mapping(grid["rng"], fields=_RNG_FIELDS, field="power grid rng")
    if rng != _RNG_CONTRACT:
        raise RecordValidationError("power grid RNG contract differs from the frozen P0 contract")
    return PowerGridSpec("1", (120, 160), (0.1, 0.4, 0.7), (0.6, 0.75, 0.9), (0.0, 0.4, 0.8), 20000, 200, 43200, 5, 2000, 99999, 0.15, 0.8, 0.05, 96, 128, 1e-10, 1e-10, 200, 1e-12, 200, PowerRngContract(**cast(dict[str, object], rng)))


def grid_content_sha256(grid_ref: ArtifactRef, *, run_root: Path) -> str:
    """Return the scientific grid digest only after complete closed parsing."""
    path, raw = _read_ref(grid_ref, run_root=run_root)
    value = load_json_bytes(raw, source=path)
    if canonical_json_bytes(value, indent=None) != raw:
        raise RecordValidationError("power grid bytes must be compact canonical JSON")
    _load_power_grid(grid_ref, run_root=run_root)
    return hashlib.sha256(raw).hexdigest()


def load_power_config(authority_ref: ArtifactRef, grid_ref: ArtifactRef, screen_topology_ref: ArtifactRef, *, run_root: Path) -> PowerConfig:
    """Return the only public config constructor, rejecting all ref overrides."""
    authority = load_power_authority(authority_ref, run_root=run_root)
    manifest = _manifest(authority.manifest_ref, run_root=run_root)
    if grid_ref != _manifest_ref(manifest, "power_grid_ref") or screen_topology_ref != _manifest_ref(manifest, "power_screen_topology_ref"):
        raise RecordValidationError("power grid/topology refs must exactly equal manifest-bound refs")
    grid_content_sha256(grid_ref, run_root=run_root)
    _read_ref(screen_topology_ref, run_root=run_root)
    return PowerConfig(authority_ref, grid_ref, screen_topology_ref, RNG_CONTRACT_SHA256)


def _power_contract_refs(config: PowerConfig, *, run_root: Path) -> tuple[ArtifactRef, ArtifactRef]:
    """Persist non-scientific code/numeric receipts once; later records mirror them."""
    root = Path(run_root)
    payload = canonical_json_bytes({"numeric_contract": _numeric_contract(), "rng_contract_sha256": config.rng_contract_sha256}, indent=None)
    digest = hashlib.sha256(payload).hexdigest()
    path = root / "power-contracts" / f"{digest}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        write_atomic_bytes(path, payload)
    ref = _artifact_ref_for_path(path, root, "power_contract", "application/json")
    return ref, ref


def _numeric_contract() -> dict[str, object]:
    return {"numpy_version": "2.3.5", "gauss_hermite_order": 96, "gauss_legendre_order": 128,
            "probability_tolerance": 1e-10, "gaussian_root_tolerance": 1e-10,
            "gaussian_root_max_iterations": 200, "clopper_pearson_tolerance": 1e-12,
            "clopper_pearson_max_iterations": 200}


def _record_base(config: PowerConfig, *, phase: str, generation: int, kernel_id: str, shard_count: int, run_root: Path) -> dict[str, object]:
    authority = load_power_authority(config.authority_ref, run_root=run_root)
    manifest_document = _load_direct_scientific_parent(_ref_mapping(authority.manifest_ref), run_root=run_root, field="manifest_ref", expected_kind="resampling_study_manifest")
    config_ref, numeric_ref = _power_contract_refs(config, run_root=run_root)
    return {"authority_ref": _ref_mapping(config.authority_ref), "decision_authority": authority.authority_kind,
            "phase": phase, "generation": generation, "roster_ref": _ref_mapping(authority.roster_ref),
            "tier_membership_sha256": authority.tier_membership_sha256, "grid_ref": _ref_mapping(config.grid_ref),
            "screen_topology_ref": _ref_mapping(config.screen_topology_ref), "rng_contract_sha256": config.rng_contract_sha256,
            "grid_content_sha256": grid_content_sha256(config.grid_ref, run_root=run_root), "kernel_id": kernel_id,
            "shard_count": shard_count, "config_ref": _ref_mapping(config_ref), "numeric_fixture_ref": _ref_mapping(numeric_ref),
            "numeric_contract": _numeric_contract(), "_study_id": manifest_document.value["study_id"],
            "_frozen_created_at": manifest_document.value["frozen_created_at"], "_provenance": manifest_document.value["provenance"]}


def _write_power(out: Path, payload: dict[str, object], *, run_root: Path) -> ArtifactRef:
    study_id = payload.pop("_study_id")
    frozen_created_at = payload.pop("_frozen_created_at")
    provenance = payload.pop("_provenance")
    return write_record(out, {"record_kind": "resampling_power_report", "schema_version": "0.1.0", "study_id": study_id,
                              "frozen_created_at": frozen_created_at, "provenance": provenance, "payload": payload}, run_root=run_root, role="power_report")


def _authority_attempt_refs(config: PowerConfig, *, run_root: Path) -> tuple[ArtifactRef, ...]:
    """Discover, validate, and canonically order the whole authority ledger.

    Finalization is deliberately not allowed to accept a hand-picked subset:
    retries and incomplete generations are evidence, not operator discretion.
    """
    root = Path(run_root)
    authority_mapping = _ref_mapping(config.authority_ref)
    reports = []
    # Manifest-owned input blobs are intentionally not scientific records and
    # may use their own ``resampling_*`` grammars.
    excluded = tuple((root / "inputs").rglob("*.json"))
    for document in _scientific_documents(root, excluded=excluded).values():
        if document.value["record_kind"] != "resampling_power_report":
            continue
        payload = cast(Mapping[str, object], document.value["payload"])
        if payload["authority_ref"] == authority_mapping:
            reports.append(document)
    if any(cast(Mapping[str, object], report.value["payload"])["stage"] == "final" for report in reports):
        raise RecordValidationError("power authority already has a final report")
    if not reports:
        raise RecordValidationError("power finalization requires discovered authority attempts")
    _validate_power_identities(reports, run_root=root)
    stage_order = {"screen": 0, "shard": 1, "selection": 2, "validation": 3}
    phase_order = {"gaussian_approximation": 0, "full_multiplier_fallback": 1}
    reports.sort(key=lambda document: (
        phase_order[cast(str, cast(Mapping[str, object], document.value["payload"])["phase"])],
        cast(int, cast(Mapping[str, object], document.value["payload"])["generation"]),
        stage_order[cast(str, cast(Mapping[str, object], document.value["payload"])["stage"])],
        cast(int, cast(Mapping[str, object], document.value["payload"]).get("shard_index", -1)),
        document.relative_path,
    ))
    return tuple(_artifact_ref_for_path(document.path, root, "power_report", "application/json") for document in reports)


def _assert_power_write_open(config: PowerConfig, *, run_root: Path, stage: str,
                             phase: str | None = None, generation: int | None = None,
                             shard_index: int | None = None) -> None:
    """Global pre-write ledger guard; finals close an authority before mutation."""
    root = Path(run_root)
    authority = _ref_mapping(config.authority_ref)
    matches: list[Mapping[str, object]] = []
    for document in _scientific_documents(root, excluded=tuple((root / "inputs").rglob("*.json"))).values():
        if document.value.get("record_kind") != "resampling_power_report":
            continue
        payload = cast(Mapping[str, object], document.value["payload"])
        if payload.get("authority_ref") == authority:
            matches.append(payload)
    if any(payload.get("stage") == "final" for payload in matches):
        raise RecordValidationError("power authority is closed by a final report")
    if phase is not None and generation is not None:
        same = [payload for payload in matches if payload.get("stage") == stage and payload.get("phase") == phase and payload.get("generation") == generation]
        if any(payload.get("shard_index") == shard_index for payload in same):
            raise RecordValidationError("power attempt identity already exists; overwrite/repartition is forbidden")
    if stage == "screen" and phase is not None and generation is not None:
        existing = [cast(int, payload["generation"]) for payload in matches if payload.get("stage") == "screen" and payload.get("phase") == phase]
        if generation != (max(existing) + 1 if existing else 0):
            raise RecordValidationError("power screen generation must be the next immutable generation")


def _projected_screen_wall_seconds(*, elapsed_seconds: float, measured_datasets_per_cell: int,
                                  cell_count: int, production_datasets_per_cell: int,
                                  shard_count: int) -> int:
    """Fail-closed per-shard projection from measured work to production work."""
    if (not np.isfinite(elapsed_seconds) or elapsed_seconds <= 0.0
            or any(type(value) is not int or value <= 0 for value in (
                measured_datasets_per_cell, cell_count, production_datasets_per_cell, shard_count,
            ))):
        raise RecordValidationError("screen timing projection requires positive finite measured work")
    return int(np.ceil(
        elapsed_seconds / measured_datasets_per_cell * cell_count
        * production_datasets_per_cell / shard_count
    ))


def _current_failed_gaussian_validation(config: PowerConfig, *, run_root: Path) -> ArtifactRef:
    """Reload the sole current Gaussian terminal failure before fallback mutation."""
    root = Path(run_root)
    authority_mapping = _ref_mapping(config.authority_ref)
    candidates = []
    for document in _scientific_documents(root, excluded=tuple((root / "inputs").rglob("*.json"))).values():
        if document.value.get("record_kind") != "resampling_power_report":
            continue
        payload = cast(Mapping[str, object], document.value["payload"])
        if (payload.get("authority_ref") == authority_mapping
                and payload.get("phase") == "gaussian_approximation"
                and payload.get("stage") == "validation"):
            candidates.append(document)
    if not candidates:
        raise RecordValidationError("fallback requires a persisted Gaussian validation")
    current = max(candidates, key=lambda document: cast(int, cast(Mapping[str, object], document.value["payload"])["generation"]))
    payload = cast(Mapping[str, object], current.value["payload"])
    _same_config(payload, config, run_root=run_root)
    approximation = cast(Mapping[str, object], payload.get("approximation_receipt"))
    if approximation.get("passed") is not False:
        raise RecordValidationError("fallback requires the current terminal failed Gaussian validation")
    return _artifact_ref_for_path(current.path, root, "power_report", "application/json")


def screen_power_grid(config: PowerConfig, *, phase: Literal["gaussian_approximation", "full_multiplier_fallback"], generation: int, shard_count: int, fallback_trigger_ref: ArtifactRef | None, run_root: Path, out: Path) -> ArtifactRef:
    """Seal immutable topology/timing before any shard can execute."""
    if type(generation) is not int or generation < 0 or type(shard_count) is not int or shard_count <= 0:
        raise RecordValidationError("power screen generation and shard_count must be nonnegative/positive integers")
    _assert_power_write_open(config, run_root=run_root, stage="screen", phase=phase, generation=generation)
    if (phase == "gaussian_approximation") != (fallback_trigger_ref is None):
        raise RecordValidationError("Gaussian screens forbid and fallback screens require a failed validation trigger")
    if fallback_trigger_ref is not None:
        current_failed = _current_failed_gaussian_validation(config, run_root=run_root)
        if fallback_trigger_ref != current_failed:
            raise RecordValidationError("fallback trigger is not the current terminal failed Gaussian validation")
    grid = _load_power_grid(config.grid_ref, run_root=run_root)
    # Measure the registered 200-dataset screen kernel and extrapolate its
    # observed per-cell time to the full immutable grid.  `1` was a lie.
    started = perf_counter()
    authority = load_power_authority(config.authority_ref, run_root=run_root)
    _gate_totals_for_cell(frozen_power_cells()[0], authority=authority,
        digest=grid_content_sha256(config.grid_ref, run_root=run_root), phase=phase,
        roster_group_sizes=_roster_group_sizes(authority, run_root=run_root),
        dataset_count=grid.screen_datasets_per_cell, draw_domain="screen",
        joint_group_labels=_roster_joint_group_labels(authority, run_root=run_root))
    if phase == "full_multiplier_fallback":
        # Measure the actual registered expensive kernel before allowing a
        # fallback screen.  A passing Gaussian never enters this branch.
        swe, tau = replay_pattern_chunk(frozen_power_cells()[0], authority=authority,
            grid_digest=grid_content_sha256(config.grid_ref, run_root=run_root), phase=phase,
            roster_group_sizes=_roster_group_sizes(authority, run_root=run_root), start=0, count=1,
            draw_domain="validation")[0]
        full_multiplier_gate_pass(swe, tau, authority_kind=authority.authority_kind,
            tier_membership_sha256=authority.tier_membership_sha256,
            grid_content_digest=grid_content_sha256(config.grid_ref, run_root=run_root), phase=phase,
            cell_id=frozen_power_cells()[0].cell_id, replicate_index=0,
            multiplier_draws=grid.multiplier_draws)
    elapsed = perf_counter() - started
    # A screen measures a fixed number of datasets for one cell.  Project that
    # measured work across the full immutable grid, production datasets, and
    # the frozen parallel shard topology.  Anything else is numerology.
    projected = _projected_screen_wall_seconds(
        elapsed_seconds=elapsed, measured_datasets_per_cell=grid.screen_datasets_per_cell,
        cell_count=len(frozen_power_cells()), production_datasets_per_cell=grid.datasets_per_cell,
        shard_count=shard_count,
    )
    if projected > grid.max_projected_wall_seconds:
        raise RecordValidationError("screen projection exceeds frozen 12-hour wall-clock cap")
    kernel = "power-screen-gaussian-v1" if phase == "gaussian_approximation" else "power-screen-full-multiplier-v1"
    payload = _record_base(config, phase=phase, generation=generation, kernel_id=kernel, shard_count=shard_count, run_root=run_root)
    payload.update({"stage": "screen", "parent_refs": [] if fallback_trigger_ref is None else [_ref_mapping(fallback_trigger_ref)],
                    "projected_wall_seconds": projected, "cell_count": len(frozen_power_cells()), "dataset_count": grid.screen_datasets_per_cell})
    if fallback_trigger_ref is not None:
        payload["fallback_trigger_ref"] = _ref_mapping(fallback_trigger_ref)
    return _write_power(out, payload, run_root=run_root)


def _report(ref: ArtifactRef, *, run_root: Path, stage: str) -> Mapping[str, object]:
    document = _load_direct_scientific_parent(_ref_mapping(ref), run_root=run_root, field="power report", expected_kind="resampling_power_report", expected_stage=stage)
    return cast(Mapping[str, object], document.value["payload"])


def _same_config(payload: Mapping[str, object], config: PowerConfig, *, run_root: Path) -> None:
    base = _record_base(config, phase=cast(str, payload["phase"]), generation=cast(int, payload["generation"]), kernel_id=cast(str, payload["kernel_id"]), shard_count=cast(int, payload["shard_count"]), run_root=run_root)
    for field in ("authority_ref", "roster_ref", "grid_ref", "screen_topology_ref", "rng_contract_sha256", "grid_content_sha256"):
        if payload[field] != base[field]:
            raise RecordValidationError(f"power parent {field} differs from config")


def _roster_group_sizes(authority: PowerAuthority, *, run_root: Path) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Derive exact joint sensitivity cells from roster benchmark/group fields.

    Task identifiers are opaque identifiers, not a covert experimental layout.
    Group order is canonicalized so a roster reordering cannot alter a draw.
    """
    roster = _load_roster(authority.roster_ref, run_root=run_root)
    cells: dict[str, dict[tuple[tuple[str, str], ...], int]] = {"SWE": {}, "TAU": {}}
    for index, value in enumerate(cast(list[object], roster["tasks"])):
        task = closed_mapping(value, fields={"task_id", "benchmark", "stratum", "lineage", "groups", "tiers"}, field=f"power roster task[{index}]")
        benchmark = task["benchmark"]
        if benchmark not in cells:
            raise RecordValidationError("P0 roster must contain only SWE and TAU benchmarks")
        groups = task["groups"]
        if not isinstance(groups, list):
            raise RecordValidationError("P0 roster groups must be arrays")
        key = tuple(sorted(
            (cast(str, closed_mapping(group, fields={"kind", "value"}, field="power roster group")["kind"]),
             cast(str, closed_mapping(group, fields={"kind", "value"}, field="power roster group")["value"]))
            for group in groups
        ))
        cells[cast(str, benchmark)][key] = cells[cast(str, benchmark)].get(key, 0) + 1
    if any(sum(cells[name].values()) != 20 for name in ("SWE", "TAU")):
        raise RecordValidationError("P0 execution requires exactly n=20 manifest tasks per benchmark")
    return (tuple(cells["SWE"][key] for key in sorted(cells["SWE"])),
            tuple(cells["TAU"][key] for key in sorted(cells["TAU"])))


def _roster_joint_group_labels(authority: PowerAuthority, *, run_root: Path) -> tuple[
    tuple[tuple[GroupLabel, ...], ...], tuple[tuple[GroupLabel, ...], ...],
]:
    """Return the same canonical joint-cell order used for simulation sizes."""
    roster = _load_roster(authority.roster_ref, run_root=run_root)
    cells: dict[str, set[tuple[tuple[str, str], ...]]] = {"SWE": set(), "TAU": set()}
    for value in cast(list[object], roster["tasks"]):
        task = closed_mapping(value, fields={"task_id", "benchmark", "stratum", "lineage", "groups", "tiers"}, field="power roster task")
        benchmark = cast(str, task["benchmark"])
        if benchmark not in cells:
            raise RecordValidationError("P0 roster must contain only SWE and TAU benchmarks")
        key = tuple(sorted((cast(str, closed_mapping(group, fields={"kind", "value"}, field="power roster group")["kind"]), cast(str, closed_mapping(group, fields={"kind", "value"}, field="power roster group")["value"])) for group in cast(list[object], task["groups"])))
        cells[benchmark].add(key)
    def labels(benchmark: str) -> tuple[tuple[GroupLabel, ...], ...]:
        return tuple(tuple(GroupLabel(GroupKind(kind), value) for kind, value in key) for key in sorted(cells[benchmark]))
    return labels("SWE"), labels("TAU")


def _receipt_joint_group_labels(joint_group_labels: tuple[
    tuple[tuple[GroupLabel, ...], ...], tuple[tuple[GroupLabel, ...], ...],
] | None) -> list[list[list[dict[str, str]]]] | None:
    """Serialize the canonical joint-cell labels that determine Task-7 gates."""
    if joint_group_labels is None:
        return None
    return [
        [[{"kind": label.kind.value, "value": label.value} for label in cell]
         for cell in benchmark]
        for benchmark in joint_group_labels
    ]


def _gate_totals_for_cell(
    cell: PowerCell, *, authority: PowerAuthority, digest: str, phase: str,
    roster_group_sizes: tuple[tuple[int, ...], tuple[int, ...]], dataset_count: int,
    draw_domain: Literal["screen", "grid", "validation"] = "grid", critical_value: float = 1.96,
    joint_group_labels: tuple[tuple[tuple[GroupLabel, ...], ...], tuple[tuple[GroupLabel, ...], ...]] | None = None,
) -> tuple[dict[str, int], dict[str, object]]:
    """Evaluate bounded real count tensors and retain only aggregate gate totals."""
    chunk_size = 128
    causal_count = 0
    leaves: list[str] = []
    chunks: list[dict[str, object]] = []
    for start in range(0, dataset_count, chunk_size):
        count = min(chunk_size, dataset_count - start)
        rows = replay_pattern_chunk(cell, authority=authority, grid_digest=digest, phase=phase,
                                    roster_group_sizes=roster_group_sizes, start=start, count=count, draw_domain=draw_domain)
        group_manifest, patterns = _batch_group_manifest_and_patterns(rows, joint_group_labels)
        gate = evaluate_binary_gate_batch(
            BinarySufficientStatisticsBatch(
                roster_ref=authority.roster_ref, group_manifest=group_manifest,
                pattern_counts=patterns, arm_failure_counts=np.zeros((count, 2, 4), dtype=np.int64),
                pipeline_invalid_counts=np.zeros(count, dtype=np.int64),
            ),
            AnalysisConfig(), critical_values=np.full(count, critical_value),
        )
        chunk_passes = int(np.count_nonzero(gate.causal_pass))
        causal_count += chunk_passes
        chunk_leaves = tuple(hashlib.sha256((pattern_count_digest(swe) + pattern_count_digest(tau)).encode("ascii")).hexdigest()
                             for swe, tau in rows)
        leaves.extend(chunk_leaves)
        chunks.append({"start": start, "dataset_count": count, "causal_pass_count": chunk_passes,
                       "merkle_root_sha256": merkle_root(chunk_leaves)})
    totals = {"dataset_count": dataset_count, "causal_pass_count": causal_count}
    receipt_labels = _receipt_joint_group_labels(joint_group_labels)
    layout = hashlib.sha256(canonical_json_bytes({
        "SWE": list(roster_group_sizes[0]), "TAU": list(roster_group_sizes[1]),
        "joint_group_labels": receipt_labels,
    }, indent=None)).hexdigest()
    receipt: dict[str, object] = {
        "contract_id": "p0-count-replay-merkle-v2", "cell_id": cell.cell_id,
        "authority_kind": authority.authority_kind, "tier_membership_sha256": authority.tier_membership_sha256,
        "grid_content_sha256": digest, "phase": phase, "draw_domain": draw_domain, "critical_value": critical_value, "dataset_count": dataset_count,
        "group_layout_sha256": layout, "joint_group_labels": receipt_labels,
        "chunk_size": chunk_size, "chunk_count": len(chunks),
        "chunks": chunks, "full_merkle_root_sha256": merkle_root(tuple(leaves)),
        "aggregate_gate_totals": totals,
    }
    return totals, receipt


def validate_power_execution_receipt(result: Mapping[str, object], *, authority: PowerAuthority,
                                     grid_digest: str, roster_group_sizes: tuple[tuple[int, ...], tuple[int, ...]],
                                     joint_group_labels: tuple[
                                         tuple[tuple[GroupLabel, ...], ...], tuple[tuple[GroupLabel, ...], ...],
                                     ] | None = None) -> None:
    """Replay every committed chunk and bind it to the persisted aggregate.

    This is intentionally expensive: a receipt that cannot be recomputed is a
    label, not evidence.
    """
    cell_id = result.get("cell_id")
    cell = next((candidate for candidate in frozen_power_cells() if candidate.cell_id == cell_id), None)
    if cell is None or result.get("family") != cell.family:
        raise RecordValidationError("power shard result does not name a frozen cell family")
    receipt = cast(Mapping[str, object], result.get("replay_receipt"))
    if not isinstance(receipt, Mapping) or receipt.get("cell_id") != cell_id:
        raise RecordValidationError("power shard receipt does not bind its cell")
    domain = cast(Literal["screen", "grid", "validation"], receipt.get("draw_domain", "grid"))
    critical = receipt.get("critical_value", 1.96)
    if domain not in {"screen", "grid", "validation"} or type(critical) not in (int, float):
        raise RecordValidationError("power shard receipt has invalid draw contract")
    expected_totals, expected = _gate_totals_for_cell(cell, authority=authority, digest=grid_digest,
        phase=cast(str, receipt.get("phase")), roster_group_sizes=roster_group_sizes,
        dataset_count=cast(int, receipt.get("dataset_count")), draw_domain=domain, critical_value=float(critical),
        joint_group_labels=joint_group_labels)
    if expected != dict(receipt) or expected_totals != result.get("gate_totals"):
        raise RecordValidationError("power shard replay receipt or aggregate totals differ from regenerated tensors")


def simulate_power_shard(screen_ref: ArtifactRef, config: PowerConfig, *, shard_index: int, run_root: Path, out: Path,
                         max_datasets: int | None = None, max_cells: int | None = None) -> ArtifactRef:
    """Produce real n=20 pattern counts in resumable bounded batches.

    ``max_datasets`` is a synthetic-only test escape hatch.  Its receipt is
    explicitly incomplete, and merge consumers reject it as authority.
    """
    screen = _report(screen_ref, run_root=run_root, stage="screen")
    _assert_power_write_open(config, run_root=run_root, stage="shard", phase=cast(str, screen["phase"]), generation=cast(int, screen["generation"]), shard_index=shard_index)
    _same_config(screen, config, run_root=run_root)
    count = cast(int, screen["shard_count"])
    if type(shard_index) is not int or not 0 <= shard_index < count:
        raise RecordValidationError("shard_index lies outside the frozen screen topology")
    cells = frozen_power_cells()
    # Contiguous ranges satisfy the artifact's ordered merged representation;
    # changing count therefore requires a new immutable screen generation.
    start, end = len(cells) * shard_index // count, len(cells) * (shard_index + 1) // count
    phase = cast(str, screen["phase"])
    grid = _load_power_grid(config.grid_ref, run_root=run_root)
    authority = load_power_authority(config.authority_ref, run_root=run_root)
    digest = grid_content_sha256(config.grid_ref, run_root=run_root)
    if max_datasets is not None and (type(max_datasets) is not int or not 0 < max_datasets <= grid.datasets_per_cell):
        raise RecordValidationError("max_datasets must be a positive bounded integer")
    if max_cells is not None and (type(max_cells) is not int or not 0 < max_cells <= end - start):
        raise RecordValidationError("max_cells must be a positive bounded integer")
    if (max_datasets is not None or max_cells is not None) and authority.authority_kind != "synthetic_validation":
        raise RecordValidationError("only synthetic fixtures may use incomplete P0 shard execution")
    dataset_count = grid.datasets_per_cell if max_datasets is None else max_datasets
    roster_group_sizes = _roster_group_sizes(authority, run_root=run_root)
    joint_group_labels = _roster_joint_group_labels(authority, run_root=run_root)
    results: list[dict[str, object]] = []
    for cell in cells[start:end if max_cells is None else min(end, start + max_cells)]:
        totals, receipt = _gate_totals_for_cell(cell, authority=authority, digest=digest, phase=phase,
                                                roster_group_sizes=roster_group_sizes, dataset_count=dataset_count,
                                                joint_group_labels=joint_group_labels)
        # A P0 family is evaluated by the same Task-7 gate; there is no second
        # static-binomial simulator hiding behind a convenient field name.
        results.append({"cell_id": cell.cell_id, "family": cell.family,
                        "gate_totals": totals, "replay_receipt": receipt})
    kernel = "power-grid-gaussian-v1" if phase == "gaussian_approximation" else "power-grid-full-multiplier-v1"
    payload = _record_base(config, phase=phase, generation=cast(int, screen["generation"]), kernel_id=kernel, shard_count=count, run_root=run_root)
    payload.update({"stage": "shard", "parent_refs": [_ref_mapping(screen_ref)], "shard_index": shard_index,
                    "cell_results": results, "dataset_count": dataset_count,
                    "execution_complete": dataset_count == grid.datasets_per_cell and max_cells is None})
    return _write_power(out, payload, run_root=run_root)


def _complete_shards(screen_ref: ArtifactRef, shard_refs: tuple[ArtifactRef, ...], config: PowerConfig, *, run_root: Path) -> tuple[Mapping[str, object], ...]:
    screen = _report(screen_ref, run_root=run_root, stage="screen")
    if len(shard_refs) != screen["shard_count"]:
        raise RecordValidationError("selection/validation requires every frozen shard")
    shards = tuple(_report(ref, run_root=run_root, stage="shard") for ref in shard_refs)
    if [shard["shard_index"] for shard in shards] != list(range(len(shards))):
        raise RecordValidationError("shards must be complete ordered zero-based topology")
    if any(shard["parent_refs"] != [_ref_mapping(screen_ref)] for shard in shards):
        raise RecordValidationError("shard parent does not match selected screen")
    grid = _load_power_grid(config.grid_ref, run_root=run_root)
    if any(shard["execution_complete"] is not True or shard["dataset_count"] != grid.datasets_per_cell for shard in shards):
        raise RecordValidationError("incomplete synthetic shard receipts cannot enter an authority merge")
    return shards


def select_validation_cells(screen_ref: ArtifactRef, shard_refs: tuple[ArtifactRef, ...], config: PowerConfig, *, run_root: Path, out: Path) -> ArtifactRef:
    screen = _report(screen_ref, run_root=run_root, stage="screen")
    _assert_power_write_open(config, run_root=run_root, stage="selection", phase="gaussian_approximation", generation=cast(int, screen["generation"]))
    if screen["phase"] != "gaussian_approximation":
        raise RecordValidationError("fallback phase forbids validation selection")
    shards = _complete_shards(screen_ref, shard_refs, config, run_root=run_root)
    results = [row for shard in shards for row in cast(list[Mapping[str, object]], shard["cell_results"])]
    alternative = [row for row in results if cast(str, row["cell_id"]).startswith("alternative:")]
    selected = sorted(alternative, key=lambda row: (
        cast(int, cast(Mapping[str, object], row["gate_totals"])["causal_pass_count"])
        / cast(int, cast(Mapping[str, object], row["gate_totals"])["dataset_count"]),
        cast(str, row["cell_id"]),
    ))[:5]
    payload = _record_base(config, phase="gaussian_approximation", generation=cast(int, screen["generation"]), kernel_id="power-worst-five-selection-v1", shard_count=cast(int, screen["shard_count"]), run_root=run_root)
    payload.update({"stage": "selection", "parent_refs": [_ref_mapping(screen_ref), *[_ref_mapping(ref) for ref in shard_refs]], "selected_cells": [row["cell_id"] for row in selected], "candidate_count": len(alternative), "selection_count": 5})
    return _write_power(out, payload, run_root=run_root)


def _write_validation_evidence(out: Path, value: Mapping[str, object], *, run_root: Path,
                               role: str) -> ArtifactRef:
    """Write canonical non-record evidence only after the report prewrite guard."""
    raw = canonical_json_bytes(dict(value), indent=None)
    digest = hashlib.sha256(raw).hexdigest()
    path = Path(run_root) / "power-validation" / f"{out.stem}-{digest[:16]}-{role}.json"
    if path.exists() and path.read_bytes() != raw:
        raise RecordValidationError("validation evidence destination has immutable conflicting bytes")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        write_atomic_bytes(path, raw)
    return _artifact_ref_for_path(path, Path(run_root), role, "application/json")


def _tier_decision(*, authority: PowerAuthority, rows: list[Mapping[str, object]]) -> str:
    if authority.authority_kind == "synthetic_validation":
        return "CONDITIONAL_ONLY"
    # Both roster tiers consume the same full grid today; keep the decision
    # derived from receipts rather than accepting a caller's preferred tier.
    alternatives = [row for row in rows if cast(str, row["family"]) == "alternative"]
    nulls = [row for row in rows if cast(str, row["family"]) != "alternative"]
    passes = (all(cast(float, row["lower"]) >= 0.80 for row in alternatives)
              and all(cast(float, row["upper"]) <= 0.05 for row in nulls))
    return "C160" if passes else "FEASIBILITY_NO_GO"


def _validation_family_totals(cell: PowerCell, *, authority: PowerAuthority, digest: str,
                              phase: str, roster_group_sizes: tuple[tuple[int, ...], tuple[int, ...]],
                              dataset_count: int, multiplier_draws: int,
                              joint_group_labels: tuple[tuple[tuple[GroupLabel, ...], ...], tuple[tuple[GroupLabel, ...], ...]] | None = None) -> tuple[dict[str, int], dict[str, int]]:
    """Independently regenerate validation-domain outcomes for both engines."""
    gaussian, _ = _gate_totals_for_cell(cell, authority=authority, digest=digest, phase=phase,
                                        roster_group_sizes=roster_group_sizes, dataset_count=dataset_count,
                                        draw_domain="validation", joint_group_labels=joint_group_labels)
    multiplier_pass = 0
    for replicate in range(dataset_count):
        swe, tau = replay_pattern_chunk(cell, authority=authority, grid_digest=digest, phase=phase,
                                        roster_group_sizes=roster_group_sizes, start=replicate, count=1,
                                        draw_domain="validation")[0]
        multiplier_pass += int(full_multiplier_gate_pass(
            swe, tau, authority_kind=authority.authority_kind,
            tier_membership_sha256=authority.tier_membership_sha256,
            grid_content_digest=digest, phase=phase, cell_id=cell.cell_id,
            replicate_index=replicate, multiplier_draws=multiplier_draws,
        ))
    return gaussian, {"dataset_count": dataset_count, "causal_pass_count": multiplier_pass}


def validate_gaussian_approximation(screen_ref: ArtifactRef, shard_refs: tuple[ArtifactRef, ...], selection_ref: ArtifactRef, config: PowerConfig, *, run_root: Path, out: Path) -> ArtifactRef:
    screen = _report(screen_ref, run_root=run_root, stage="screen")
    _assert_power_write_open(config, run_root=run_root, stage="validation", phase="gaussian_approximation", generation=cast(int, screen["generation"]))
    selection = _report(selection_ref, run_root=run_root, stage="selection")
    _complete_shards(screen_ref, shard_refs, config, run_root=run_root)
    if selection["parent_refs"] != [_ref_mapping(screen_ref), *[_ref_mapping(ref) for ref in shard_refs]]:
        raise RecordValidationError("validation selection does not bind the complete shard set")
    grid = _load_power_grid(config.grid_ref, run_root=run_root)
    authority = load_power_authority(config.authority_ref, run_root=run_root)
    digest = grid_content_sha256(config.grid_ref, run_root=run_root)
    layout = _roster_group_sizes(authority, run_root=run_root)
    joint_group_labels = _roster_joint_group_labels(authority, run_root=run_root)
    by_cell = {cell.cell_id: cell for cell in frozen_power_cells()}
    raw_rows: list[dict[str, object]] = []
    for selected_id in cast(list[str], selection["selected_cells"]):
        for family in ("alternative", "null_both", "null_content", "null_excess"):
            cell_id = selected_id.replace("alternative", family, 1)
            gaussian, multiplier = _validation_family_totals(
                by_cell[cell_id], authority=authority, digest=digest, phase="gaussian_approximation",
                roster_group_sizes=layout, dataset_count=grid.validation_datasets_per_cell,
                multiplier_draws=grid.multiplier_draws, joint_group_labels=joint_group_labels,
            )
            raw_rows.append({"cell_id": cell_id, "family": family, "gaussian_gate_totals": gaussian,
                             "full_multiplier_gate_totals": multiplier})
    lower_tail, upper_tail = 0.05 / 729, 0.05 / 2187
    receipts = []
    for cell_id in cast(list[str], selection["selected_cells"]):
        alternate = next(row for row in raw_rows if row["cell_id"] == cell_id)
        null_rows = [row for row in raw_rows if cast(str, row["cell_id"]).replace(cast(str, row["family"]), "alternative", 1) == cell_id and row["family"] != "alternative"]
        receipts.append({"cell_id": cell_id,
            "alternative_power_lower": clopper_pearson_lower(cast(int, cast(Mapping[str, object], alternate["full_multiplier_gate_totals"])["causal_pass_count"]), grid.validation_datasets_per_cell, tail_probability=lower_tail),
            "null_false_positive_upper": clopper_pearson_upper(max(cast(int, cast(Mapping[str, object], row["full_multiplier_gate_totals"])["causal_pass_count"]) for row in null_rows), grid.validation_datasets_per_cell, tail_probability=upper_tail)})
    gaussian_rows = [{"family": row["family"], "lower": clopper_pearson_lower(cast(int, cast(Mapping[str, object], row["gaussian_gate_totals"])["causal_pass_count"]), grid.validation_datasets_per_cell, tail_probability=lower_tail), "upper": clopper_pearson_upper(cast(int, cast(Mapping[str, object], row["gaussian_gate_totals"])["causal_pass_count"]), grid.validation_datasets_per_cell, tail_probability=upper_tail)} for row in raw_rows]
    multiplier_rows = [{"family": row["family"], "lower": clopper_pearson_lower(cast(int, cast(Mapping[str, object], row["full_multiplier_gate_totals"])["causal_pass_count"]), grid.validation_datasets_per_cell, tail_probability=lower_tail), "upper": clopper_pearson_upper(cast(int, cast(Mapping[str, object], row["full_multiplier_gate_totals"])["causal_pass_count"]), grid.validation_datasets_per_cell, tail_probability=upper_tail)} for row in raw_rows]
    maximum = max(abs(cast(int, cast(Mapping[str, object], row["gaussian_gate_totals"])["causal_pass_count"]) - cast(int, cast(Mapping[str, object], row["full_multiplier_gate_totals"])["causal_pass_count"])) / grid.validation_datasets_per_cell for row in raw_rows)
    gaussian_decision, multiplier_decision = _tier_decision(authority=authority, rows=gaussian_rows), _tier_decision(authority=authority, rows=multiplier_rows)
    raw_ref = _write_validation_evidence(out, {"contract_id": "p0-validation-raw-counts-v1", "draw_domain": "validation", "dataset_count": grid.validation_datasets_per_cell, "multiplier_draws": grid.multiplier_draws, "rows": raw_rows}, run_root=run_root, role="power_validation_raw_counts")
    numeric_ref = _write_validation_evidence(out, {"contract_id": "p0-validation-decision-v1", "interval_receipts": receipts, "gaussian_decision": gaussian_decision, "full_multiplier_decision": multiplier_decision}, run_root=run_root, role="power_validation_numeric_receipt")
    payload = _record_base(config, phase="gaussian_approximation", generation=cast(int, screen["generation"]), kernel_id="power-gaussian-vs-multiplier-validation-v1", shard_count=cast(int, screen["shard_count"]), run_root=run_root)
    payload.update({"stage": "validation", "parent_refs": [_ref_mapping(screen_ref), *[_ref_mapping(ref) for ref in shard_refs], _ref_mapping(selection_ref)], "selected_cells": selection["selected_cells"], "interval_receipts": receipts, "validation_dataset_count": grid.validation_datasets_per_cell,
                    "raw_counts_ref": _ref_mapping(raw_ref), "numeric_receipt_ref": _ref_mapping(numeric_ref),
                    "approximation_receipt": {"max_absolute_gate_pass_rate_difference": maximum, "gaussian_tier_decision": gaussian_decision, "full_multiplier_tier_decision": multiplier_decision, "tier_decision_unchanged": gaussian_decision == multiplier_decision, "passed": maximum <= 0.01 and gaussian_decision == multiplier_decision}})
    return _write_power(out, payload, run_root=run_root)


def finalize_synthetic_power_report(screen_ref: ArtifactRef, shard_refs: tuple[ArtifactRef, ...], selection_ref: ArtifactRef, validation_ref: ArtifactRef, config: PowerConfig, *, run_root: Path, out: Path) -> ArtifactRef:
    """Only synthetic completed arm: null tier and CONDITIONAL_ONLY, forever."""
    authority = load_power_authority(config.authority_ref, run_root=run_root)
    if authority.authority_kind != "synthetic_validation":
        raise RecordValidationError("synthetic finalizer cannot select a confirmation tier")
    screen = _report(screen_ref, run_root=run_root, stage="screen")
    validation = _report(validation_ref, run_root=run_root, stage="validation")
    _complete_shards(screen_ref, shard_refs, config, run_root=run_root)
    if validation["approximation_receipt"]["passed"] is not True:  # type: ignore[index]
        raise RecordValidationError("failed Gaussian validation must use the synthetic failed terminal arm")
    attempts = _authority_attempt_refs(config, run_root=run_root)
    selected_attempts = (screen_ref, *shard_refs, selection_ref, validation_ref)
    if not set(selected_attempts).issubset(set(attempts)):
        raise RecordValidationError("selected final chain is not in the discovered authority ledger")
    payload = _record_base(config, phase="gaussian_approximation", generation=cast(int, screen["generation"]), kernel_id="power-final-gaussian-v1", shard_count=cast(int, screen["shard_count"]), run_root=run_root)
    payload.update({"stage": "final", "parent_refs": [_ref_mapping(ref) for ref in attempts], "all_attempt_refs": [_ref_mapping(ref) for ref in attempts],
                    "finalization": {"kind": "completed_chain", "selected_phase": "gaussian_approximation", "selected_generation": screen["generation"], "selected_kernel_id": "power-final-gaussian-v1", "selected_shard_count": screen["shard_count"], "selected_screen_ref": _ref_mapping(screen_ref), "selected_shard_refs": [_ref_mapping(ref) for ref in shard_refs], "selected_selection_ref": _ref_mapping(selection_ref), "selected_validation_ref": _ref_mapping(validation_ref), "selected_tier": None, "decision": "CONDITIONAL_ONLY"}})
    return _write_power(out, payload, run_root=run_root)


def validate_full_multiplier_fallback(screen_ref: ArtifactRef, shard_refs: tuple[ArtifactRef, ...],
                                      config: PowerConfig, *, run_root: Path, out: Path) -> ArtifactRef:
    """Execute the phase-closed full-grid fallback, never a second Gaussian pass."""
    screen = _report(screen_ref, run_root=run_root, stage="screen")
    _assert_power_write_open(config, run_root=run_root, stage="validation",
                             phase="full_multiplier_fallback", generation=cast(int, screen["generation"]))
    if screen["phase"] != "full_multiplier_fallback":
        raise RecordValidationError("full-grid validator requires a fallback screen")
    _complete_shards(screen_ref, shard_refs, config, run_root=run_root)
    trigger = cast(Mapping[str, object], screen["fallback_trigger_ref"])
    failed = _report(ArtifactRef(**dict(trigger)), run_root=run_root, stage="validation")
    if failed["phase"] != "gaussian_approximation" or failed["approximation_receipt"]["passed"] is not False:  # type: ignore[index]
        raise RecordValidationError("fallback requires the terminal failed Gaussian validation")
    grid, authority = _load_power_grid(config.grid_ref, run_root=run_root), load_power_authority(config.authority_ref, run_root=run_root)
    digest, layout = grid_content_sha256(config.grid_ref, run_root=run_root), _roster_group_sizes(authority, run_root=run_root)
    raw_rows: list[dict[str, object]] = []
    for cell in frozen_power_cells():
        # The fallback producer regenerates every dataset in its own phase and
        # evaluates the full multiplier; it never relabels Gaussian shard totals.
        passed = 0
        for replicate in range(grid.datasets_per_cell):
            swe, tau = replay_pattern_chunk(cell, authority=authority, grid_digest=digest,
                phase="full_multiplier_fallback", roster_group_sizes=layout,
                start=replicate, count=1)[0]
            passed += int(full_multiplier_gate_pass(swe, tau, authority_kind=authority.authority_kind,
                tier_membership_sha256=authority.tier_membership_sha256, grid_content_digest=digest,
                phase="full_multiplier_fallback", cell_id=cell.cell_id, replicate_index=replicate,
                multiplier_draws=grid.multiplier_draws))
        lower_tail = grid.familywise_alpha / 729 if cell.family == "alternative" else grid.familywise_alpha / 2187
        raw_rows.append({"cell_id": cell.cell_id, "family": cell.family,
            "gate_totals": {"dataset_count": grid.datasets_per_cell, "causal_pass_count": passed},
            "lower": clopper_pearson_lower(passed, grid.datasets_per_cell, tail_probability=lower_tail),
            "upper": clopper_pearson_upper(passed, grid.datasets_per_cell, tail_probability=lower_tail)})
    decision = _tier_decision(authority=authority, rows=raw_rows)
    raw_ref = _write_validation_evidence(out, {"contract_id": "p0-full-multiplier-raw-counts-v1", "multiplier_draws": grid.multiplier_draws, "rows": raw_rows}, run_root=run_root, role="power_full_multiplier_raw_counts")
    numeric_ref = _write_validation_evidence(out, {"contract_id": "p0-full-multiplier-decision-v1", "decision": decision, "complete_cell_ids": [row["cell_id"] for row in raw_rows]}, run_root=run_root, role="power_full_multiplier_numeric_receipt")
    payload = _record_base(config, phase="full_multiplier_fallback", generation=cast(int, screen["generation"]), kernel_id="power-full-grid-validation-v1", shard_count=cast(int, screen["shard_count"]), run_root=run_root)
    payload.update({"stage": "validation", "parent_refs": [_ref_mapping(ArtifactRef(**dict(trigger))), _ref_mapping(screen_ref), *[_ref_mapping(ref) for ref in shard_refs]], "fallback_trigger_ref": dict(trigger), "complete_cell_ids": [row["cell_id"] for row in raw_rows], "expected_cell_count": len(frozen_power_cells()), "observed_cell_count": len(raw_rows), "raw_counts_ref": _ref_mapping(raw_ref), "numeric_receipt_ref": _ref_mapping(numeric_ref), "selected_tier": None if decision == "CONDITIONAL_ONLY" or decision == "FEASIBILITY_NO_GO" else int(decision[1:]), "decision": "CONDITIONAL_ONLY" if decision == "CONDITIONAL_ONLY" else ("NO_GO" if decision == "FEASIBILITY_NO_GO" else "GO")})
    return _write_power(out, payload, run_root=run_root)


def finalize_synthetic_full_multiplier_report(screen_ref: ArtifactRef, shard_refs: tuple[ArtifactRef, ...], validation_ref: ArtifactRef, config: PowerConfig, *, run_root: Path, out: Path) -> ArtifactRef:
    """Close only a completed fallback chain; Gaussian success cannot reach here."""
    authority = load_power_authority(config.authority_ref, run_root=run_root)
    if authority.authority_kind != "synthetic_validation":
        raise RecordValidationError("synthetic fallback finalizer cannot select a confirmation tier")
    screen, validation = _report(screen_ref, run_root=run_root, stage="screen"), _report(validation_ref, run_root=run_root, stage="validation")
    if screen["phase"] != "full_multiplier_fallback" or validation["phase"] != "full_multiplier_fallback":
        raise RecordValidationError("fallback finalizer requires fallback-only records")
    _complete_shards(screen_ref, shard_refs, config, run_root=run_root)
    attempts = _authority_attempt_refs(config, run_root=run_root)
    trigger = cast(Mapping[str, object], screen["fallback_trigger_ref"])
    payload = _record_base(config, phase="full_multiplier_fallback", generation=cast(int, screen["generation"]), kernel_id="power-final-full-multiplier-v1", shard_count=cast(int, screen["shard_count"]), run_root=run_root)
    payload.update({"stage": "final", "parent_refs": [_ref_mapping(ref) for ref in attempts], "all_attempt_refs": [_ref_mapping(ref) for ref in attempts], "finalization": {"kind": "completed_chain", "selected_phase": "full_multiplier_fallback", "selected_generation": screen["generation"], "selected_kernel_id": "power-final-full-multiplier-v1", "selected_shard_count": screen["shard_count"], "fallback_trigger_ref": dict(trigger), "selected_screen_ref": _ref_mapping(screen_ref), "selected_shard_refs": [_ref_mapping(ref) for ref in shard_refs], "full_grid_validation_ref": _ref_mapping(validation_ref), "selected_tier": None, "decision": "CONDITIONAL_ONLY"}})
    return _write_power(out, payload, run_root=run_root)


def finalize_synthetic_validation_failed(
    all_attempt_refs: tuple[ArtifactRef, ...], terminal_attempt_ref: ArtifactRef,
    *, terminal_stage: Literal["screen", "shard", "selection", "validation"],
    reason: Literal["gaussian_screen_exhausted", "full_multiplier_screen_exhausted", "numeric_fixture_failed", "runtime_bound_exceeded", "attempt_incomplete", "synthetic_validation_gate_failed"],
    config: PowerConfig, run_root: Path, out: Path,
) -> ArtifactRef:
    """Closed nondecisive terminal arm; never a disguised feasibility decision."""
    authority = load_power_authority(config.authority_ref, run_root=run_root)
    discovered_attempts = _authority_attempt_refs(config, run_root=run_root)
    if authority.authority_kind != "synthetic_validation" or not discovered_attempts or terminal_attempt_ref not in discovered_attempts:
        raise RecordValidationError("synthetic terminal final requires its own complete attempted chain")
    if tuple(all_attempt_refs) != discovered_attempts:
        raise RecordValidationError("synthetic terminal final must parent the globally discovered authority ledger")
    terminal = _report(terminal_attempt_ref, run_root=run_root, stage=terminal_stage)
    if terminal_stage == "validation" and reason == "attempt_incomplete":
        raise RecordValidationError("a persisted validation cannot be labelled attempt_incomplete")
    if terminal_stage == "validation" and reason != "synthetic_validation_gate_failed":
        raise RecordValidationError("a persisted synthetic validation requires synthetic_validation_gate_failed")
    phase = cast(str, terminal["phase"])
    kernel = "power-final-gaussian-v1" if phase == "gaussian_approximation" else "power-final-full-multiplier-v1"
    payload = _record_base(config, phase=phase, generation=cast(int, terminal["generation"]), kernel_id=kernel, shard_count=cast(int, terminal["shard_count"]), run_root=run_root)
    payload.update({"stage": "final", "parent_refs": [_ref_mapping(ref) for ref in discovered_attempts], "all_attempt_refs": [_ref_mapping(ref) for ref in discovered_attempts],
                    "finalization": {"kind": "synthetic_validation_failed", "terminal_attempt_ref": _ref_mapping(terminal_attempt_ref), "terminal_stage": terminal_stage, "terminal_phase": phase, "terminal_kernel_id": kernel, "terminal_shard_count": terminal["shard_count"], "reason": reason, "selected_tier": None, "decision": "CONDITIONAL_ONLY"}})
    return _write_power(out, payload, run_root=run_root)


__all__ = (
    "POWER_AUTHORITY_MEDIA_TYPE", "RNG_CONTRACT_SHA256", "PowerAuthority", "PowerConfig", "PowerGridSpec",
    "RosterBoundPowerAuthority", "SyntheticPowerAuthority", "grid_content_sha256", "load_power_authority", "load_power_config",
    "seal_roster_bound_power_authority", "seal_synthetic_power_authority",
)

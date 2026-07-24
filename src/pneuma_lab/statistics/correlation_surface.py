"""Fail-closed diagnostic correlation surface for the sealed P0 power study."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
from pathlib import Path
from statistics import NormalDist
from typing import Any, Iterable

import numpy as np

from pneuma_lab.statistics.power import (
    ALPHA,
    COMPONENT_COUNT,
    DELTA_VALUES,
    FULL_SUPPORT,
    H2_COMPONENTS,
    MODEL_VERSION,
    POWER_THRESHOLD,
    UTILITY_MARGIN,
    UTILITY_U0,
    UTILITY_U1,
    NuisanceProfile,
    PriorAnchor,
    PriorAnchorError,
    PriorCell,
    PriorGrid,
    _canonical_json_bytes,
    _component_names,
    _group_cells,
    _max_t_critical,
    _paired_binary_compatible,
    _scenario_counts,
    _straddles_threshold,
    _utility_pair_compatible,
    load_prior_anchor,
    monte_carlo_interval,
)


SURFACE_SCHEMA_VERSION = "pneuma-p0-correlation-surface/1.0.0"
CORRELATION_GRID = (0.0, 0.25, 0.50, 0.75, 0.99)
OFFICIAL_SEED = 20260724
INITIAL_DRAWS = 10_000
ADAPTIVE_DRAWS = 100_000
SEALED_REPORT_SCHEMA_VERSION = "pneuma-p0-power-report/1.0.0"
VALIDATION_FAMILYWISE_ERROR = 0.01


class CorrelationSurfaceError(RuntimeError):
    """Raised when the diagnostic surface cannot be trusted."""


class IndependenceValidationError(CorrelationSurfaceError):
    """Raised when rho-zero simulation disagrees with the closed form."""

    def __init__(self, message: str, receipt: dict[str, Any]) -> None:
        super().__init__(message)
        self.receipt = receipt


def diagnostic_code_sha256() -> str:
    """Return the digest of this isolated diagnostic implementation."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def equicorrelation_eigenvalues(
    correlation: float,
    component_count: int,
) -> tuple[float, float]:
    """Return the smallest and largest equicorrelation eigenvalues."""
    if isinstance(component_count, bool) or component_count <= 0:
        raise ValueError("component_count must be a positive integer")
    if not math.isfinite(correlation):
        raise ValueError("correlation must be finite")
    if component_count == 1:
        return 1.0, 1.0
    return 1.0 - correlation, 1.0 + (component_count - 1) * correlation


def _assert_positive_definite(correlation: float) -> None:
    smallest, largest = equicorrelation_eigenvalues(correlation, COMPONENT_COUNT)
    if smallest <= 0.0 or largest <= 0.0:
        raise PriorAnchorError(
            "cross-component equicorrelation matrix is not positive definite"
        )


def _load_canonical_json(path: Path, name: str) -> tuple[bytes, dict[str, Any]]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CorrelationSurfaceError(f"{name} is unavailable: {path}") from exc
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorrelationSurfaceError(f"{name} is not valid JSON") from exc
    if not isinstance(parsed, dict) or raw != _canonical_json_bytes(parsed):
        raise CorrelationSurfaceError(f"{name} is not canonical JSON")
    return raw, parsed


def _load_sealed_report(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw, report = _load_canonical_json(path, "sealed P0 power report")
    if report.get("schema_version") != SEALED_REPORT_SCHEMA_VERSION:
        raise CorrelationSurfaceError("sealed P0 power report schema mismatch")
    config = report.get("config")
    if not isinstance(config, dict):
        raise CorrelationSurfaceError("sealed P0 power report has no config")
    observed_config_digest = hashlib.sha256(_canonical_json_bytes(config)).hexdigest()
    if report.get("config_sha256") != observed_config_digest:
        raise CorrelationSurfaceError("sealed P0 config digest mismatch")
    selection = report.get("selection")
    if not isinstance(selection, dict) or selection.get("outcome") != "P0 no-go":
        raise CorrelationSurfaceError("sealed P0 decision is not the required no-go")
    return raw, report


def _fixed_correlation_grid(
    anchor: PriorAnchor,
    *,
    delta_power: float,
    correlation: float,
) -> PriorGrid:
    """Build the governed prior conditional on one diagnostic rho value."""
    _assert_positive_definite(correlation)
    cells: list[PriorCell] = []
    rejected = 0
    products = itertools.product(
        anchor.base_harm_support,
        anchor.paired_discordance,
        anchor.lineage_icc,
        anchor.nuisance_profiles,
    )
    for base, discordance, icc, nuisance in products:
        compatible = _paired_binary_compatible(
            base.value,
            delta_power,
            discordance.value,
        ) and _utility_pair_compatible(
            nuisance.utility_event_rate,
            nuisance.utility_discordance,
        )
        if not compatible:
            rejected += 1
            continue
        cells.append(
            PriorCell(
                base_harm=base.value,
                paired_discordance=discordance.value,
                lineage_icc=icc.value,
                cross_component_correlation=correlation,
                nuisance=nuisance,
                weight=(base.weight * discordance.weight * icc.weight * nuisance.weight),
            )
        )
    pre_rejection_count = (
        len(anchor.base_harm_support)
        * len(anchor.paired_discordance)
        * len(anchor.lineage_icc)
        * len(anchor.nuisance_profiles)
    )
    total_weight = math.fsum(cell.weight for cell in cells)
    if not cells or total_weight <= 0.0:
        raise PriorAnchorError("no diagnostic prior cells survive compatibility checks")
    normalized = tuple(
        PriorCell(
            base_harm=cell.base_harm,
            paired_discordance=cell.paired_discordance,
            lineage_icc=cell.lineage_icc,
            cross_component_correlation=cell.cross_component_correlation,
            nuisance=cell.nuisance,
            weight=cell.weight / total_weight,
        )
        for cell in cells
    )
    return PriorGrid(
        cells=normalized,
        pre_rejection_count=pre_rejection_count,
        rejected_count=rejected,
    )


def _surface_target() -> dict[str, Any]:
    return {
        "joint_power": 0.0,
        "interval_lower": 0.0,
        "interval_upper": 0.0,
        "component_marginal_power": {},
        "product_bound": 0.0,
        "min_marginal_bound": 0.0,
        "minimum_draws": math.inf,
        "maximum_draws": 0,
        "adaptive_parameter_cells": 0,
        "surviving_parameter_cells": 0,
        "surviving_grid_cells": 0,
    }


def _accumulate_surface_cell(
    target: dict[str, Any],
    *,
    counts: Any,
    support: int,
    weight: float,
    grid_cell_count: int,
    adaptive: bool,
) -> tuple[float, float, dict[str, float]]:
    joint_power = counts.conjunction[support] / counts.draws
    marginal_power = {
        name: component_counts[support] / counts.draws
        for name, component_counts in counts.components.items()
    }
    product_bound = math.prod(marginal_power.values())
    min_marginal_bound = min(marginal_power.values())
    interval = monte_carlo_interval(counts.conjunction[support], counts.draws)
    target["joint_power"] += weight * joint_power
    target["interval_lower"] += weight * interval[0]
    target["interval_upper"] += weight * interval[1]
    target["product_bound"] += weight * product_bound
    target["min_marginal_bound"] += weight * min_marginal_bound
    for name, value in marginal_power.items():
        target["component_marginal_power"][name] = (
            target["component_marginal_power"].get(name, 0.0) + weight * value
        )
    target["minimum_draws"] = min(target["minimum_draws"], counts.draws)
    target["maximum_draws"] = max(target["maximum_draws"], counts.draws)
    target["adaptive_parameter_cells"] += int(adaptive)
    target["surviving_parameter_cells"] += 1
    target["surviving_grid_cells"] += grid_cell_count
    return joint_power, product_bound, marginal_power


def _comparison_error_allowance(comparison: dict[str, Any], z_value: float) -> float:
    draws = int(comparison["draws"])
    joint_power = float(comparison["joint_power"])
    marginals = tuple(
        float(value) for value in comparison["component_marginal_power"].values()
    )
    variance_floor = 0.25 / draws
    joint_variance = max(
        joint_power * (1.0 - joint_power),
        variance_floor,
    ) / draws
    product_variance = 0.0
    for index, marginal in enumerate(marginals):
        product_without = math.prod(
            value for other, value in enumerate(marginals) if other != index
        )
        marginal_variance = max(
            marginal * (1.0 - marginal),
            variance_floor,
        ) / draws
        product_variance += product_without**2 * marginal_variance
    return z_value * (
        math.sqrt(joint_variance) + math.sqrt(product_variance)
    ) + 1.0 / draws


def validate_independence(
    comparisons: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Validate rho-zero conjunction estimates against the product closed form."""
    records = list(comparisons)
    if not records:
        raise IndependenceValidationError(
            "rho=0 closed-form validation received no comparisons",
            {
                "status": "failed",
                "comparisons": 0,
                "failed_comparisons": 0,
                "worst_case": None,
            },
        )
    tail_probability = VALIDATION_FAMILYWISE_ERROR / (2.0 * len(records))
    z_value = NormalDist().inv_cdf(1.0 - tail_probability)
    failures = 0
    worst: dict[str, Any] | None = None
    worst_ratio = -math.inf
    for comparison in records:
        discrepancy = abs(
            float(comparison["joint_power"])
            - float(comparison["product_bound"])
        )
        allowance = _comparison_error_allowance(comparison, z_value)
        comparison["monte_carlo_error_allowance"] = allowance
        ratio = discrepancy / allowance if allowance > 0.0 else math.inf
        if discrepancy > allowance:
            failures += 1
        if ratio > worst_ratio:
            worst_ratio = ratio
            worst = {
                "coordinate": comparison["coordinate"],
                "draws": comparison["draws"],
                "joint_power": comparison["joint_power"],
                "product_bound": comparison["product_bound"],
                "absolute_discrepancy": discrepancy,
                "monte_carlo_error_allowance": allowance,
                "allowance_fraction_used": ratio,
            }
    receipt = {
        "status": "passed" if failures == 0 else "failed",
        "method": (
            "rho=0 joint Monte Carlo estimate versus product of component "
            "marginal estimates; conservative delta-method error with "
            "99% Bonferroni familywise coverage"
        ),
        "familywise_coverage": 1.0 - VALIDATION_FAMILYWISE_ERROR,
        "bonferroni_z": z_value,
        "comparisons": len(records),
        "failed_comparisons": failures,
        "worst_case": worst,
    }
    if failures:
        assert worst is not None
        raise IndependenceValidationError(
            "rho=0 closed-form validation FAILED: "
            f"{failures}/{len(records)} comparisons exceeded Monte Carlo error; "
            f"worst joint={worst['joint_power']:.8g}, "
            f"product={worst['product_bound']:.8g}, "
            f"discrepancy={worst['absolute_discrepancy']:.8g}, "
            f"allowance={worst['monte_carlo_error_allowance']:.8g}",
            receipt,
        )
    return receipt


def _validate_arguments(
    *,
    report: dict[str, Any],
    seed: int,
    initial_draws: int,
    adaptive_draws: int,
    support_counts: tuple[int, ...],
    delta_values: tuple[float, ...],
    correlations: tuple[float, ...],
) -> None:
    if seed != OFFICIAL_SEED or seed != report["config"].get("seed"):
        raise CorrelationSurfaceError("diagnostic seed must match sealed seed 20260724")
    if initial_draws < INITIAL_DRAWS or adaptive_draws < initial_draws:
        raise CorrelationSurfaceError(
            "diagnostic draws must be at least 10000 and nondecreasing"
        )
    if not support_counts or tuple(sorted(set(support_counts))) != support_counts:
        raise CorrelationSurfaceError("support_counts must be sorted and unique")
    if min(support_counts) < min(FULL_SUPPORT) or max(support_counts) > max(FULL_SUPPORT):
        raise CorrelationSurfaceError("support_counts must stay inside [24, 96]")
    if 48 not in support_counts:
        raise CorrelationSurfaceError("support_counts must include G=48 for brackets")
    if any(delta not in DELTA_VALUES for delta in delta_values) or 0.10 not in delta_values:
        raise CorrelationSurfaceError(
            "delta_values must use the frozen set and include 0.10 for brackets"
        )
    if not correlations or correlations[0] != 0.0:
        raise CorrelationSurfaceError("correlation grid must begin with independence")
    if tuple(sorted(set(correlations))) != correlations:
        raise CorrelationSurfaceError("correlations must be sorted and unique")
    for correlation in correlations:
        _assert_positive_definite(correlation)


def _simulate_surface(
    *,
    anchor: PriorAnchor,
    seed: int,
    initial_draws: int,
    adaptive_draws: int,
    support_counts: tuple[int, ...],
    delta_values: tuple[float, ...],
    correlations: tuple[float, ...],
    adapt: bool,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    generator = np.random.Generator(np.random.PCG64(seed))
    shared = generator.standard_normal((adaptive_draws, 1))
    independent = generator.standard_normal((adaptive_draws, COMPONENT_COUNT))
    max_t = {
        (correlation, comparator_count): _max_t_critical(
            correlation=correlation,
            component_count=comparator_count,
            seed=seed ^ int(correlation * 10_000) ^ comparator_count,
        )
        for correlation in correlations
        for comparator_count in (1, 3)
    }
    accumulator: dict[tuple[float, float, int, str, str], dict[str, Any]] = {}
    rho_zero_comparisons: list[dict[str, Any]] = []
    grid_metadata: dict[str, Any] = {}

    for correlation in correlations:
        z_all = (
            math.sqrt(correlation) * shared
            + math.sqrt(1.0 - correlation) * independent
        )
        rho_key = f"{correlation:.2f}"
        grid_metadata[rho_key] = {}
        for delta_power in delta_values:
            grid = _fixed_correlation_grid(
                anchor,
                delta_power=delta_power,
                correlation=correlation,
            )
            grouped = _group_cells(grid)
            delta_key = f"{delta_power:.2f}"
            grid_metadata[rho_key][delta_key] = {
                "pre_rejection_cells": grid.pre_rejection_count,
                "surviving_cells": len(grid.cells),
                "rejected_cells": grid.rejected_count,
                "surviving_parameter_cells": len(grouped),
            }
            for parameter_index, (cell, weight, grid_cell_count) in enumerate(grouped):
                initial_counts: dict[tuple[str, str], Any] = {}
                should_adapt = False
                for scope in ("U0", "U1"):
                    for tier, comparator_count in (("core", 3), ("floor", 1)):
                        counts = _scenario_counts(
                            z_all[:initial_draws],
                            cell=cell,
                            delta_power=delta_power,
                            tier=tier,
                            scope=scope,
                            support_counts=support_counts,
                            max_t_critical=max_t[(correlation, comparator_count)],
                        )
                        initial_counts[(scope, tier)] = counts
                        should_adapt = should_adapt or _straddles_threshold(counts)
                adaptive = adapt and should_adapt and adaptive_draws > initial_draws
                if adaptive:
                    final_counts = {
                        (scope, tier): _scenario_counts(
                            z_all,
                            cell=cell,
                            delta_power=delta_power,
                            tier=tier,
                            scope=scope,
                            support_counts=support_counts,
                            max_t_critical=max_t[(correlation, comparator_count)],
                        )
                        for scope in ("U0", "U1")
                        for tier, comparator_count in (("core", 3), ("floor", 1))
                    }
                else:
                    final_counts = initial_counts

                for scope in ("U0", "U1"):
                    for tier in ("core", "floor"):
                        counts = final_counts[(scope, tier)]
                        for support in support_counts:
                            key = (correlation, delta_power, support, scope, tier)
                            target = accumulator.setdefault(key, _surface_target())
                            joint, product, marginals = _accumulate_surface_cell(
                                target,
                                counts=counts,
                                support=support,
                                weight=weight,
                                grid_cell_count=grid_cell_count,
                                adaptive=adaptive,
                            )
                            if correlation == 0.0:
                                rho_zero_comparisons.append(
                                    {
                                        "coordinate": {
                                            "delta_power": delta_power,
                                            "G": support,
                                            "utility_scope": scope,
                                            "tier": tier,
                                            "parameter_cell": parameter_index,
                                            "paired_discordance": cell.paired_discordance,
                                            "lineage_icc": cell.lineage_icc,
                                            "nuisance": {
                                                "attrition": cell.nuisance.attrition,
                                                "evaluator_error": (
                                                    cell.nuisance.evaluator_error
                                                ),
                                                "utility_event_rate": (
                                                    cell.nuisance.utility_event_rate
                                                ),
                                                "utility_discordance": (
                                                    cell.nuisance.utility_discordance
                                                ),
                                            },
                                        },
                                        "surface_key": key,
                                        "weight": weight,
                                        "draws": counts.draws,
                                        "joint_power": joint,
                                        "product_bound": product,
                                        "component_marginal_power": marginals,
                                    }
                                )

    validation = validate_independence(rho_zero_comparisons)
    allowance_by_key: dict[tuple[float, float, int, str, str], float] = {}
    for comparison in rho_zero_comparisons:
        key = comparison["surface_key"]
        allowance_by_key[key] = allowance_by_key.get(key, 0.0) + (
            comparison["weight"] * comparison["monte_carlo_error_allowance"]
        )

    rows: list[dict[str, Any]] = []
    for key in sorted(
        accumulator,
        key=lambda item: (item[1], item[2], item[3], item[4], item[0]),
    ):
        correlation, delta_power, support, scope, tier = key
        target = accumulator[key]
        row = {
            "rho": correlation,
            "G": support,
            "delta_power": delta_power,
            "utility_scope": scope,
            "tier": tier,
            "joint_power": target["joint_power"],
            "monte_carlo_interval_99": [
                target["interval_lower"],
                target["interval_upper"],
            ],
            "component_marginal_power": dict(
                sorted(target["component_marginal_power"].items())
            ),
            "product_bound": target["product_bound"],
            "min_marginal_bound": target["min_marginal_bound"],
            "cell_draws": {
                "minimum": int(target["minimum_draws"]),
                "maximum": int(target["maximum_draws"]),
                "adaptive_parameter_cells": target["adaptive_parameter_cells"],
                "surviving_parameter_cells": target["surviving_parameter_cells"],
                "surviving_grid_cells": target["surviving_grid_cells"],
            },
        }
        if correlation == 0.0:
            row["rho_zero_monte_carlo_error_allowance"] = allowance_by_key[key]
        rows.append(row)
    return rows, validation, grid_metadata


def _build_brackets(
    rows: list[dict[str, Any]],
    sealed_report: dict[str, Any],
    correlations: tuple[float, ...],
) -> dict[str, dict[str, Any]]:
    indexed = {
        (
            row["rho"],
            row["delta_power"],
            row["G"],
            row["utility_scope"],
            row["tier"],
        ): row
        for row in rows
    }
    brackets: dict[str, dict[str, Any]] = {}
    for scope in ("U0", "U1"):
        brackets[scope] = {}
        for tier in ("core", "floor"):
            endpoint_rows = [
                indexed[(correlation, 0.10, 48, scope, tier)]
                for correlation in correlations
            ]
            brackets[scope][tier] = {
                "G": 48,
                "delta_power": 0.10,
                "product_bound": endpoint_rows[0]["product_bound"],
                "min_marginal_bound": endpoint_rows[-1]["min_marginal_bound"],
                "swept_joint_power": {
                    f"{row['rho']:.2f}": row["joint_power"]
                    for row in endpoint_rows
                },
                "sealed_weighted_average": sealed_report["results"]["0.10"][
                    "48"
                ][scope]["tiers"][tier]["conjunction_power"],
            }
    return brackets


def _bind_artifact_digest(payload: dict[str, Any]) -> dict[str, Any]:
    artifact = dict(payload)
    artifact["artifact_sha256"] = hashlib.sha256(
        _canonical_json_bytes(payload)
    ).hexdigest()
    return artifact


def build_correlation_surface(
    *,
    anchor_path: Path,
    sealed_report_path: Path,
    seed: int = OFFICIAL_SEED,
    initial_draws: int = INITIAL_DRAWS,
    adaptive_draws: int = ADAPTIVE_DRAWS,
    support_counts: tuple[int, ...] = FULL_SUPPORT,
    delta_values: tuple[float, ...] = DELTA_VALUES,
    correlations: tuple[float, ...] = CORRELATION_GRID,
    adapt: bool = True,
) -> dict[str, Any]:
    """Build the diagnostic surface, failing before return on rho-zero mismatch."""
    sealed_raw, sealed_report = _load_sealed_report(sealed_report_path)
    _validate_arguments(
        report=sealed_report,
        seed=seed,
        initial_draws=initial_draws,
        adaptive_draws=adaptive_draws,
        support_counts=support_counts,
        delta_values=delta_values,
        correlations=correlations,
    )
    anchor_raw = anchor_path.read_bytes()
    anchor_digest = hashlib.sha256(anchor_raw).hexdigest()
    if sealed_report.get("anchor_sha256") != anchor_digest:
        raise CorrelationSurfaceError("sealed report and prior anchor digest mismatch")
    anchor = load_prior_anchor(anchor_path, expected_sha256=anchor_digest)

    rows, validation, grid_metadata = _simulate_surface(
        anchor=anchor,
        seed=seed,
        initial_draws=initial_draws,
        adaptive_draws=adaptive_draws,
        support_counts=support_counts,
        delta_values=delta_values,
        correlations=correlations,
        adapt=adapt,
    )
    payload = {
        "schema_version": SURFACE_SCHEMA_VERSION,
        "does_not_supersede_or_amend_sealed_p0_no_go": True,
        "diagnostic_only_statement": (
            "This diagnostic sensitivity artifact does not supersede or amend "
            "the sealed P0 no-go and performs no tier selection."
        ),
        "sealed_p0": {
            "report_sha256": hashlib.sha256(sealed_raw).hexdigest(),
            "config_sha256": sealed_report["config_sha256"],
            "anchor_sha256": anchor_digest,
            "code_sha256": sealed_report["code_sha256"],
            "selection": sealed_report["selection"],
        },
        "diagnostic_code_sha256": diagnostic_code_sha256(),
        "config": {
            "model_version": MODEL_VERSION,
            "seed": seed,
            "initial_draws": initial_draws,
            "adaptive_draws": adaptive_draws,
            "adaptive_enabled": adapt,
            "adaptation_boundary": POWER_THRESHOLD,
            "support_counts": list(support_counts),
            "delta_values": list(delta_values),
            "correlations": list(correlations),
            "utility_scopes": ["U0", "U1"],
            "utility_scope_components": {
                "U0": list(UTILITY_U0),
                "U1": list(UTILITY_U1),
            },
            "tiers": ["core", "floor"],
            "alpha": ALPHA,
            "utility_margin": UTILITY_MARGIN,
            "observed_behavior_margin": 0.05,
            "training_weight": 0.0,
            "common_random_numbers": True,
            "max_component_count": COMPONENT_COUNT,
            "h2_components": list(H2_COMPONENTS),
            "correlation_role": (
                "diagnostic axis; no weights assigned and no tier selection rerun"
            ),
        },
        "rho_zero_closed_form_validation": validation,
        "grid": grid_metadata,
        "reference_curve_definitions": {
            "product_bound": (
                "weighted mean over surviving non-rho prior cells of the product "
                "of per-component marginal powers"
            ),
            "min_marginal_bound": (
                "weighted mean over surviving non-rho prior cells of the minimum "
                "per-component marginal power"
            ),
        },
        "surface": rows,
        "brackets": _build_brackets(rows, sealed_report, correlations),
    }
    return _bind_artifact_digest(payload)


def _verify_artifact_digest(artifact: dict[str, Any]) -> None:
    payload = dict(artifact)
    observed = payload.pop("artifact_sha256", None)
    expected = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    if observed != expected:
        raise CorrelationSurfaceError("diagnostic artifact digest mismatch")


def write_surface_artifact(
    artifact: dict[str, Any],
    *,
    output_path: Path,
    sealed_report_path: Path,
    anchor_path: Path,
) -> None:
    """Atomically write only the diagnostic after sealed-byte identity checks."""
    _verify_artifact_digest(artifact)
    report_before = sealed_report_path.read_bytes()
    anchor_before = anchor_path.read_bytes()
    if hashlib.sha256(report_before).hexdigest() != artifact["sealed_p0"][
        "report_sha256"
    ]:
        raise CorrelationSurfaceError("sealed report changed before artifact write")
    if hashlib.sha256(anchor_before).hexdigest() != artifact["sealed_p0"][
        "anchor_sha256"
    ]:
        raise CorrelationSurfaceError("prior anchor changed before artifact write")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    try:
        temporary.write_bytes(_canonical_json_bytes(artifact))
        if (
            sealed_report_path.read_bytes() != report_before
            or anchor_path.read_bytes() != anchor_before
        ):
            raise CorrelationSurfaceError("sealed evidence changed during artifact write")
        os.replace(temporary, output_path)
        if (
            sealed_report_path.read_bytes() != report_before
            or anchor_path.read_bytes() != anchor_before
        ):
            output_path.unlink(missing_ok=True)
            raise CorrelationSurfaceError("sealed evidence changed after artifact write")
    finally:
        temporary.unlink(missing_ok=True)


def generate_official_surface(root: Path | None = None) -> dict[str, Any]:
    """Generate and write the official full diagnostic surface."""
    repository_root = Path.cwd() if root is None else root
    artifact_root = repository_root / "build" / "research" / "neurips-p0"
    anchor_path = artifact_root / "prior-anchor.json"
    sealed_report_path = artifact_root / "p0-power-report.json"
    output_path = artifact_root / "p0-correlation-surface.json"
    artifact = build_correlation_surface(
        anchor_path=anchor_path,
        sealed_report_path=sealed_report_path,
    )
    write_surface_artifact(
        artifact,
        output_path=output_path,
        sealed_report_path=sealed_report_path,
        anchor_path=anchor_path,
    )
    return artifact


def main() -> None:
    artifact = generate_official_surface()
    validation = artifact["rho_zero_closed_form_validation"]
    worst = validation["worst_case"]
    print(
        "rho=0 closed-form validation PASSED: "
        f"{validation['comparisons']} comparisons, "
        f"worst discrepancy={worst['absolute_discrepancy']:.8g}, "
        f"MC allowance={worst['monte_carlo_error_allowance']:.8g}"
    )
    print(
        "wrote build/research/neurips-p0/p0-correlation-surface.json "
        f"sha256={artifact['artifact_sha256']}"
    )


if __name__ == "__main__":
    main()

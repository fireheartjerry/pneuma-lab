"""Focused deterministic P0 numerical contracts."""

from __future__ import annotations

from statistics import NormalDist

import pytest

from pneuma_lab.resampling_null.power import (
    frozen_power_cells,
    philox_generator,
    bernoulli_pattern_probabilities,
    bivariate_normal_cdf_equal_threshold,
    clopper_pearson_lower,
    clopper_pearson_upper,
    gaussian_max_critical,
)


def test_probability_table_recovers_marginals_and_is_normalized() -> None:
    receipt = bernoulli_pattern_probabilities((0.25, 0.4, 0.6, 0.8), 0.4)
    assert sum(receipt.probabilities) == pytest.approx(1.0, abs=1e-10)
    assert min(receipt.probabilities) >= 0.0
    assert receipt.marginal_errors == pytest.approx((0.0, 0.0, 0.0, 0.0), abs=1e-10)


def test_gaussian_max_boundary_cases_and_independent_case() -> None:
    alpha = 0.05
    assert gaussian_max_critical(1.0, alpha) == pytest.approx(NormalDist().inv_cdf(1 - alpha))
    assert gaussian_max_critical(-1.0, alpha) == pytest.approx(NormalDist().inv_cdf(1 - alpha / 2))
    independent = gaussian_max_critical(0.0, alpha)
    assert bivariate_normal_cdf_equal_threshold(independent, 0.0) == pytest.approx(1 - alpha, abs=1e-10)


def test_clopper_pearson_uses_one_sided_tail_without_halving() -> None:
    assert clopper_pearson_lower(8, 10, tail_probability=0.05) < 0.8
    assert clopper_pearson_upper(0, 10, tail_probability=0.05) > 0.0


def test_public_philox_mapping_is_repeatable_and_domain_separated() -> None:
    key = "1" * 64
    grid = "2" * 64
    first = philox_generator("synthetic_validation", key, grid, "grid", "gaussian_approximation", "a", 0, "grid_triggered_pattern", 0).random()
    repeat = philox_generator("synthetic_validation", key, grid, "grid", "gaussian_approximation", "a", 0, "grid_triggered_pattern", 0).random()
    other = philox_generator("synthetic_validation", key, grid, "grid", "gaussian_approximation", "a", 1, "grid_triggered_pattern", 0).random()
    assert first == repeat
    assert first != other


def test_frozen_grid_has_complete_ordered_alternative_and_null_families() -> None:
    cells = frozen_power_cells()
    assert len([cell for cell in cells if cell.family == "alternative"]) == 729
    assert len([cell for cell in cells if cell.family != "alternative"]) == 2187
    assert len({cell.cell_id for cell in cells}) == len(cells)

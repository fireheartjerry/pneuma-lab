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
    simulate_benchmark_pattern_counts,
    evaluate_simulated_pattern_batch,
    merkle_root,
    power_replay_receipt,
    validate_power_replay_receipt,
)
from pneuma_lab.resampling_null.types import ArtifactRef


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


@pytest.mark.parametrize(
    ("family", "expected_content", "expected_excess"),
    (("alternative", 0.15, 0.15), ("null_both", 0.0, 0.0),
     ("null_content", 0.0, 0.15), ("null_excess", 0.15, 0.0)),
)
def test_registered_pattern_simulator_has_exact_trigger_and_null_boundaries(
    family: str, expected_content: float, expected_excess: float,
) -> None:
    result = simulate_benchmark_pattern_counts(
        p0=0.4, gamma=0.6, rho=0.4, family=family, task_count=20,
        authority_kind="synthetic_validation", tier_membership_sha256="1" * 64,
        grid_content_digest="2" * 64, phase="gaussian_approximation",
        cell_id="alternative:swe-00:tau-00", replicate_index=7,
        joint_group_sizes=(8, 12),
    )
    repeat = simulate_benchmark_pattern_counts(
        p0=0.4, gamma=0.6, rho=0.4, family=family, task_count=20,
        authority_kind="synthetic_validation", tier_membership_sha256="1" * 64,
        grid_content_digest="2" * 64, phase="gaussian_approximation",
        cell_id="alternative:swe-00:tau-00", replicate_index=7,
        joint_group_sizes=(8, 12),
    )

    assert result == repeat
    assert result.triggered_count == 12
    assert sum(result.pattern_counts) == 20
    assert sum(result.triggered_pattern_counts) == 12
    assert sum(result.no_trigger_pattern_counts) == 8
    assert result.no_trigger_pattern_counts[1:15] == (0,) * 14
    assert result.expected_content == pytest.approx(expected_content)
    assert result.expected_excess == pytest.approx(expected_excess)


def test_registered_pattern_counts_enter_the_task7_batch_gate() -> None:
    kwargs = dict(
        p0=0.4, gamma=0.6, rho=0.4, family="alternative", task_count=20,
        authority_kind="synthetic_validation", tier_membership_sha256="1" * 64,
        grid_content_digest="2" * 64, phase="gaussian_approximation",
        replicate_index=4, joint_group_sizes=(20,),
    )
    swe = simulate_benchmark_pattern_counts(cell_id="alternative:swe-00:tau-00", **kwargs)
    tau = simulate_benchmark_pattern_counts(cell_id="alternative:swe-00:tau-00", **kwargs)
    result = evaluate_simulated_pattern_batch(
        swe, tau,
        roster_ref=ArtifactRef("roster", "inputs/roster.json", "3" * 64, 1, "application/json"),
        critical_value=1.96,
    )

    assert result.causal_pass.shape == (1,)


def test_replay_merkle_receipt_rejects_a_tampered_leaf() -> None:
    from pneuma_lab.resampling_null.power import SyntheticPowerAuthority
    cell = frozen_power_cells()[0]
    authority = SyntheticPowerAuthority("1", "synthetic_validation",
        ArtifactRef("manifest", "study.json", "a" * 64, 1, "application/json"),
        ArtifactRef("roster", "roster.json", "b" * 64, 1, "application/json"), "1" * 64)
    receipt = power_replay_receipt(cell, authority=authority, grid_digest="2" * 64,
        phase="gaussian_approximation", roster_group_sizes=((20,), (20,)), dataset_count=20000)
    validate_power_replay_receipt(receipt, cell, authority=authority, grid_digest="2" * 64,
        phase="gaussian_approximation", roster_group_sizes=((20,), (20,)))
    receipt["leaf_sha256s"][0] = "0" * 64  # type: ignore[index]
    with pytest.raises(Exception, match="replay/Merkle"):
        validate_power_replay_receipt(receipt, cell, authority=authority, grid_digest="2" * 64,
            phase="gaussian_approximation", roster_group_sizes=((20,), (20,)))
    assert merkle_root(("1" * 64,)) == "1" * 64


def test_replay_receipt_commits_every_chunk_and_aggregate_gate_totals() -> None:
    """A sample of eight leaves is a debugging aid, not a 20k evidence receipt."""
    from pneuma_lab.resampling_null.power import SyntheticPowerAuthority, _gate_totals_for_cell

    authority = SyntheticPowerAuthority("1", "synthetic_validation",
        ArtifactRef("manifest", "study.json", "a" * 64, 1, "application/json"),
        ArtifactRef("roster", "roster.json", "b" * 64, 1, "application/json"), "1" * 64)
    totals, receipt = _gate_totals_for_cell(frozen_power_cells()[0], authority=authority,
        digest="2" * 64, phase="gaussian_approximation", roster_group_sizes=((8, 12), (7, 13)),
        dataset_count=257)
    assert totals["dataset_count"] == 257
    assert receipt["chunk_count"] == 3
    assert sum(chunk["dataset_count"] for chunk in receipt["chunks"]) == 257
    assert receipt["aggregate_gate_totals"] == totals

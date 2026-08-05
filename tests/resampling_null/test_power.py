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
from pneuma_lab.resampling_null.types import ArtifactRef, GroupKind, GroupLabel


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


def test_gaussian_grid_critical_is_derived_from_each_dataset_covariance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pneuma_lab.resampling_null import power

    counts = simulate_benchmark_pattern_counts(
        p0=0.4, gamma=0.6, rho=0.4, family="alternative", task_count=20,
        authority_kind="synthetic_validation", tier_membership_sha256="1" * 64,
        grid_content_digest="2" * 64, phase="gaussian_approximation",
        cell_id="alternative:swe-00:tau-00", replicate_index=7,
        joint_group_sizes=(20,), draw_domain="validation",
    )
    seen: list[tuple[float, float]] = []

    def fake_critical(correlation: float, alpha: float) -> float:
        seen.append((correlation, alpha))
        return 1.75

    monkeypatch.setattr(power, "gaussian_max_critical", fake_critical)

    assert power._gaussian_critical_for_counts(counts, counts) == 1.75
    assert len(seen) == 1
    assert -1.0 <= seen[0][0] <= 1.0
    assert seen[0][1] == 0.05


def test_cellwise_power_certificates_aggregate_to_four_worst_case_rows() -> None:
    from pneuma_lab.resampling_null.power import _aggregate_tier_rows

    rows = [
        {"family": "alternative", "tier": 160, "lower": 0.83, "upper": 0.9},
        {"family": "alternative", "tier": 160, "lower": 0.81, "upper": 0.88},
        {"family": "null_both", "tier": 160, "lower": 0.0, "upper": 0.03},
        {"family": "null_content", "tier": 160, "lower": 0.0, "upper": 0.04},
        {"family": "null_excess", "tier": 160, "lower": 0.0, "upper": 0.02},
    ]

    summary = _aggregate_tier_rows(rows)

    assert [row["family"] for row in summary] == [
        "alternative", "null_both", "null_content", "null_excess",
    ]
    assert summary[0]["lower"] == 0.81
    assert summary[0]["cell_count"] == 2


def test_clopper_pearson_uses_one_sided_tail_without_halving() -> None:
    assert clopper_pearson_lower(8, 10, tail_probability=0.05) < 0.8
    assert clopper_pearson_upper(0, 10, tail_probability=0.05) > 0.0


def test_full_multiplier_uses_frozen_rademacher_draws_on_raw_pattern_counts() -> None:
    """The fallback comparison is an engine calculation, not a Gaussian label."""
    from pneuma_lab.resampling_null.power import full_multiplier_gate_pass

    counts = simulate_benchmark_pattern_counts(
        p0=0.4, gamma=0.6, rho=0.4, family="alternative", task_count=20,
        authority_kind="synthetic_validation", tier_membership_sha256="1" * 64,
        grid_content_digest="2" * 64, phase="gaussian_approximation",
        cell_id="alternative:swe-00:tau-00", replicate_index=7,
        joint_group_sizes=(20,), draw_domain="validation",
    )
    assert isinstance(full_multiplier_gate_pass(
        counts, counts, authority_kind="synthetic_validation",
        tier_membership_sha256="1" * 64, grid_content_digest="2" * 64,
        phase="gaussian_approximation", cell_id="alternative:swe-00:tau-00",
        replicate_index=7, multiplier_draws=99999,
    ), bool)


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


def test_simulated_batch_preserves_joint_groups_for_leave_one_gate() -> None:
    """A hostile group must be able to change Task-7's leave-one gate."""
    kwargs = dict(
        p0=0.4, gamma=0.6, rho=0.4, family="alternative", task_count=20,
        authority_kind="synthetic_validation", tier_membership_sha256="1" * 64,
        grid_content_digest="2" * 64, phase="gaussian_approximation",
        replicate_index=4, joint_group_sizes=(1, 19),
    )
    swe = simulate_benchmark_pattern_counts(cell_id="alternative:swe-00:tau-00", **kwargs)
    tau = simulate_benchmark_pattern_counts(cell_id="alternative:swe-00:tau-00", **kwargs)
    roster_ref = ArtifactRef("roster", "inputs/roster.json", "3" * 64, 1, "application/json")
    labels = ((GroupLabel(GroupKind.LANGUAGE, "tiny"),), (GroupLabel(GroupKind.LANGUAGE, "rest"),))
    baseline = evaluate_simulated_pattern_batch(swe, tau, roster_ref=roster_ref, critical_value=1.96)
    grouped = evaluate_simulated_pattern_batch(
        swe, tau, roster_ref=roster_ref, critical_value=1.96,
        joint_group_labels=(labels, labels),
    )

    assert grouped.all_benchmark_nonnegative.shape == (1,)
    assert grouped.all_benchmark_nonnegative.tolist() == baseline.all_benchmark_nonnegative.tolist()
    assert grouped.causal_pass.shape == (1,)


def test_screen_projection_charges_the_entire_production_workload() -> None:
    from pneuma_lab.resampling_null.power import _projected_screen_wall_seconds

    assert _projected_screen_wall_seconds(
        elapsed_seconds=2.0, measured_datasets_per_cell=200, cell_count=2916,
        production_datasets_per_cell=20_000, shard_count=4,
    ) == 583_200


def test_production_timing_probe_replays_every_frozen_cell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cheap single-cell proxy cannot authorize the full P0 workload."""
    from pneuma_lab.resampling_null import power

    cells = power.frozen_power_cells()[:2]
    seen: list[tuple[str, int, str]] = []

    def fake_gate(cell: object, **kwargs: object) -> tuple[dict[str, int], dict[str, object]]:
        seen.append((getattr(cell, "cell_id"), kwargs["dataset_count"], kwargs["draw_domain"]))
        return {"dataset_count": 200, "causal_pass_count": 1}, {"cell_id": getattr(cell, "cell_id")}

    monkeypatch.setattr(power, "_gate_totals_for_cell", fake_gate)
    monkeypatch.setattr(power, "perf_counter", iter((10.0, 12.0)).__next__)
    authority = power.SyntheticPowerAuthority(
        "1", "synthetic_validation",
        ArtifactRef("manifest", "inputs/study.json", "c" * 64, 1, "application/json"),
        ArtifactRef("roster", "inputs/roster.json", "d" * 64, 1, "application/json"),
        "b" * 64,
    )
    receipt = power._production_timing_probe(
        cells=cells, authority=authority, digest="a" * 64, phase="gaussian_approximation",
        roster_group_sizes=((20,), (20,)), joint_group_labels=None,
        datasets_per_cell=200,
    )

    assert seen == [(cell.cell_id, 200, "screen") for cell in cells]
    assert receipt["cell_count"] == 2
    assert receipt["replay_receipts_sha256"] == power._production_timing_probe_commitment(
        cells=cells, authority=authority, digest="a" * 64, phase="gaussian_approximation",
        roster_group_sizes=((20,), (20,)), joint_group_labels=None,
        datasets_per_cell=200,
    )


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


def test_execution_receipt_binds_canonical_joint_group_labels() -> None:
    """Equal-sized labels are not interchangeable under Task-7 leave-one gates."""
    from pneuma_lab.resampling_null.power import (SyntheticPowerAuthority, _gate_totals_for_cell,
                                                   validate_power_execution_receipt)

    authority = SyntheticPowerAuthority("1", "synthetic_validation",
        ArtifactRef("manifest", "study.json", "a" * 64, 1, "application/json"),
        ArtifactRef("roster", "roster.json", "b" * 64, 1, "application/json"), "1" * 64)
    alpha = GroupLabel(GroupKind.LANGUAGE, "alpha")
    beta = GroupLabel(GroupKind.LANGUAGE, "beta")
    labels = (((alpha,), (beta,)), ((alpha,), (beta,)))
    _, receipt = _gate_totals_for_cell(frozen_power_cells()[0], authority=authority,
        digest="2" * 64, phase="gaussian_approximation", roster_group_sizes=((8, 12), (7, 13)),
        dataset_count=1, joint_group_labels=labels)

    assert receipt["joint_group_labels"] == [
        [[{"kind": "language", "value": "alpha"}], [{"kind": "language", "value": "beta"}]],
        [[{"kind": "language", "value": "alpha"}], [{"kind": "language", "value": "beta"}]],
    ]
    result = {"cell_id": frozen_power_cells()[0].cell_id, "family": frozen_power_cells()[0].family,
              "gate_totals": receipt["aggregate_gate_totals"], "replay_receipt": receipt}
    validate_power_execution_receipt(result, authority=authority, grid_digest="2" * 64,
        roster_group_sizes=((8, 12), (7, 13)), joint_group_labels=labels)
    receipt["joint_group_labels"] = [
        [[{"kind": "language", "value": "beta"}], [{"kind": "language", "value": "alpha"}]],
        [[{"kind": "language", "value": "alpha"}], [{"kind": "language", "value": "beta"}]],
    ]
    with pytest.raises(Exception, match="replay receipt|aggregate totals"):
        validate_power_execution_receipt(result, authority=authority, grid_digest="2" * 64,
            roster_group_sizes=((8, 12), (7, 13)), joint_group_labels=labels)


def test_leave_one_group_gate_changes_outcome_when_a_group_is_registered() -> None:
    """The Task-7 leave-one gate consumes the registered group tensor."""
    from pneuma_lab.resampling_null.power import BenchmarkPatternCounts

    positive = (0,) * 8 + (19,) + (0,) * 7
    negative = (0,) * 4 + (1,) + (0,) * 11
    swe = BenchmarkPatternCounts(
        pattern_counts=tuple(left + right for left, right in zip(positive, negative, strict=True)),
        triggered_pattern_counts=(0,) * 16, no_trigger_pattern_counts=(0,) * 16,
        joint_group_pattern_counts=(positive, negative), triggered_count=0,
        expected_content=0.0, expected_excess=0.0,
    )
    tau = BenchmarkPatternCounts(
        pattern_counts=(20,) + (0,) * 15, triggered_pattern_counts=(0,) * 16,
        no_trigger_pattern_counts=(0,) * 16, joint_group_pattern_counts=((20,) + (0,) * 15,) * 2,
        triggered_count=0, expected_content=0.0, expected_excess=0.0,
    )
    roster_ref = ArtifactRef("roster", "inputs/roster.json", "3" * 64, 1, "application/json")
    labels = ((GroupLabel(GroupKind.LANGUAGE, "good"),), (GroupLabel(GroupKind.LANGUAGE, "bad"),))
    ungrouped = evaluate_simulated_pattern_batch(swe, tau, roster_ref=roster_ref, critical_value=1.96)
    grouped = evaluate_simulated_pattern_batch(
        swe, tau, roster_ref=roster_ref, critical_value=1.96,
        joint_group_labels=(labels, ((), ())),
    )

    assert ungrouped.all_leave_one_nonnegative.tolist() == [True]
    assert grouped.all_leave_one_nonnegative.tolist() == [False]

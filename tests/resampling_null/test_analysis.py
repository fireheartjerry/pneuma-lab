"""Hand calculations for the Task 7A registered statistical primitives."""

from __future__ import annotations

from math import inf, isclose
from inspect import signature
from types import SimpleNamespace

import pytest

from pneuma_lab.resampling_null.analysis import (
    conservative_multiplier_quantile,
    multiplier_lower_bounds,
    omnibus_sharp_pvalue,
    resampling_resolution,
    sharp_content_pvalue,
    sharp_excess_pvalue,
    task_contrasts,
    rows_to_binary_sufficient_statistics,
    evaluate_binary_gate_kernel,
    evaluate_binary_gate_batch,
    classify_verdict,
)
import pneuma_lab.resampling_null.analysis as analysis_module
from pneuma_lab.resampling_null.types import (
    AnalysisConfig, AnalysisResult, AnalysisRow, ArtifactRef, BenchmarkEstimate,
    BinarySufficientStatisticsBatch,
    ContrastResult, GateResult, GroupKind, GroupLabel, RandomizationResult,
    ResolutionResult, SecondaryFamilyResult, SimultaneousBounds, Verdict,
)
import numpy as np


def _row(task_id: str, *, benchmark: str = "SWE", real: int, sham: int,
         none: int, resample: int) -> AnalysisRow:
    return AnalysisRow(
        task_id=task_id, benchmark=benchmark, stratum="s", lineage="l",
        sensitivity_groups=(GroupLabel(GroupKind.LANGUAGE, "python"),),
        triggered=True, prefix=0, real=real, sham=sham, none=none,
        resample=resample, real_infrastructure_failure=False,
        sham_infrastructure_failure=False, none_infrastructure_failure=False,
        resample_infrastructure_failure=False, pipeline_valid=True,
        invalid_codes=(),
    )


def test_task_contrasts_follow_registered_decomposition() -> None:
    contrasts = task_contrasts(_row("one", real=1, sham=0, none=0, resample=1))

    assert contrasts == {
        "content": 1.0, "excess": 0.5, "sham_packet": -0.5,
        "continuation": 0.5, "total": 1.0, "null": 1.0,
    }


def test_sharp_content_enumerates_two_task_swap_tail_exactly() -> None:
    result = sharp_content_pvalue(
        [_row("a", real=1, sham=0, none=0, resample=0),
         _row("b", benchmark="TAU", real=1, sham=0, none=0, resample=0)],
        draws=7, seed=1,
    )

    assert result.statistic == 1.0
    assert result.p_value == 0.25  # 1 of 2^2 signed swap assignments.
    assert result.mode == "enumerated_exact"
    assert result.support_size == 4


def test_sharp_content_uses_exact_dynamic_program_when_product_support_is_large() -> None:
    result = sharp_content_pvalue(
        [_row(str(index), benchmark="SWE" if index < 8 else "TAU", real=index % 2,
              sham=1 - index % 2, none=0, resample=0)
         for index in range(17)],
        draws=7,
        seed=1,
    )

    assert result.mode == "dynamic_program_exact"
    assert result.support_size == 2**17
    assert result.draws is None


def test_sharp_excess_enumerates_one_of_three_real_reassignment() -> None:
    result = sharp_excess_pvalue(
        [_row("a", real=1, sham=0, none=0, resample=0),
         _row("b", benchmark="TAU", real=0, sham=0, none=0, resample=0)],
        draws=7, seed=1,
    )

    assert result.statistic == 0.5
    assert result.p_value == 1 / 3
    assert result.mode == "enumerated_exact"
    assert result.support_size == 9


def test_omnibus_is_labeled_exact_sharp_null_with_full_twelve_way_support() -> None:
    result = omnibus_sharp_pvalue(
        [_row("a", real=1, sham=0, none=0, resample=0),
         _row("b", benchmark="TAU", real=0, sham=0, none=0, resample=0)],
        draws=7, seed=2,
    )

    assert result.mode == "enumerated_exact"
    assert result.support_size == 144
    assert 0.0 < result.p_value <= 1.0


def test_omnibus_uses_registered_finite_conditional_variance_for_one_task() -> None:
    result = omnibus_sharp_pvalue(
        [_row("a", real=1, sham=0, none=0, resample=0),
         _row("b", benchmark="TAU", real=0, sham=0, none=0, resample=0)],
        draws=7,
        seed=2,
    )

    # max(sqrt(2), sqrt(8 / 3)); the latter is the excess component.
    assert isclose(result.statistic, (8 / 3) ** 0.5)
    assert result.p_value == 0.25


def test_large_omnibus_uses_domain_separated_add_one_philox_monte_carlo() -> None:
    rows = [_row(str(index), benchmark="SWE" if index < 2 else "TAU", real=1,
                 sham=0, none=0, resample=0) for index in range(5)]
    first = omnibus_sharp_pvalue(rows, draws=11, seed=9)
    second = omnibus_sharp_pvalue(rows, draws=11, seed=9)

    assert first == second
    assert first.mode == "add_one_monte_carlo"
    assert first.p_value >= 1 / 12
    assert first.monte_carlo_se is not None


def test_multiplier_bounds_use_frozen_quantile_order_and_benchmark_covariance() -> None:
    rows = [
        _row("a", real=1, sham=0, none=0, resample=0),
        _row("b", real=0, sham=1, none=1, resample=1),
        _row("c", benchmark="TAU", real=1, sham=0, none=0, resample=0),
        _row("d", benchmark="TAU", real=0, sham=1, none=1, resample=1),
    ]
    result = multiplier_lower_bounds(
        rows, contrast_names=("content", "excess"), family_name="co_primary",
        draws=4, seed=0,
    )

    assert result.standard_errors == (2**-0.5, 2**-0.5)
    assert result.quantile_order_1_based == 4
    assert result.critical_value >= 0.0
    assert all(isclose(lower, -result.critical_value * 2**-0.5) for lower in result.lowers)


def test_multiplier_process_has_registered_benchmark_scaling() -> None:
    """The wild process must have the covariance used by its studentization."""
    rows = [
        _row("a", real=1, sham=0, none=0, resample=0),
        _row("b", real=0, sham=1, none=1, resample=1),
        _row("c", benchmark="TAU", real=1, sham=0, none=0, resample=0),
        _row("d", benchmark="TAU", real=0, sham=1, none=1, resample=1),
    ]
    bounds = multiplier_lower_bounds(
        rows, contrast_names=("content", "excess"), family_name="co_primary",
        draws=20_000, seed=41,
    )
    draws = analysis_module._multiplier_z_draws(
        rows, ("content", "excess"), bounds.standard_errors,
        draws=20_000, seed=41,
    )

    assert np.diag(np.cov(draws, rowvar=False, ddof=1)) == pytest.approx((1.0, 1.0), abs=0.03)


def test_multiplier_philox_order_is_canonicalized_by_task_id() -> None:
    rows = [
        _row("b", real=1, sham=0, none=0, resample=0),
        _row("a", real=0, sham=1, none=1, resample=1),
        _row("d", benchmark="TAU", real=1, sham=0, none=0, resample=0),
        _row("c", benchmark="TAU", real=0, sham=1, none=1, resample=1),
    ]

    assert multiplier_lower_bounds(rows, contrast_names=("content", "excess"),
                                    family_name="co_primary", draws=7, seed=3) == (
        multiplier_lower_bounds(list(reversed(rows)), contrast_names=("content", "excess"),
                                 family_name="co_primary", draws=7, seed=3)
    )


def test_multiplier_canonicalizes_interleaved_cross_benchmark_task_ids() -> None:
    rows = [
        _row("z", real=1, sham=0, none=0, resample=0),
        _row("a", benchmark="TAU", real=0, sham=1, none=1, resample=1),
        _row("a", real=0, sham=1, none=1, resample=1),
        _row("z", benchmark="TAU", real=1, sham=0, none=0, resample=0),
    ]

    forward = multiplier_lower_bounds(
        rows, contrast_names=("content", "excess"), family_name="co_primary",
        draws=7, seed=5,
    )
    reversed_rows = multiplier_lower_bounds(
        list(reversed(rows)), contrast_names=("content", "excess"),
        family_name="co_primary", draws=7, seed=5,
    )

    assert forward == reversed_rows


def test_frozen_quantile_has_no_interpolation() -> None:
    value, order = conservative_multiplier_quantile([0.0, 1.0, 2.0, 3.0], alpha=0.05)
    assert (value, order) == (3.0, 4)


def test_resolution_exact_equal_and_unequal_rosters() -> None:
    equal = resampling_resolution([
        _row("a", real=0, sham=0, none=0, resample=1),
        _row("b", benchmark="TAU", real=0, sham=0, none=0, resample=1),
    ])
    unequal = resampling_resolution([
        _row("a", benchmark="SWE", real=0, sham=0, none=0, resample=1),
        _row("b", benchmark="SWE", real=0, sham=0, none=0, resample=0),
        _row("c", benchmark="TAU", real=0, sham=0, none=0, resample=1),
    ])

    assert (equal.q0, equal.r95, equal.discordant_task_count) == (1.0, 1.0, 2)
    assert equal.mode == "equal_roster_exact_binomial"
    assert unequal.q0 == 0.75
    assert unequal.r95 == 0.75
    assert unequal.mode == "unequal_roster_exact_weighted_convolution"


def test_equal_roster_r95_aggregates_absolute_binomial_masses() -> None:
    rows = [
        _row(f"s{index}", real=0, sham=0, none=0, resample=1)
        for index in range(7)
    ] + [
        _row(f"t{index}", benchmark="TAU", real=0, sham=0, none=0, resample=1)
        for index in range(7)
    ]
    assert resampling_resolution(rows).r95 == 4 / 7


def test_registered_primitives_reject_rosters_other_than_swe_and_tau() -> None:
    with pytest.raises(ValueError, match="SWE and TAU"):
        resampling_resolution([_row("a", real=0, sham=0, none=0, resample=0)])


def test_binary_gate_kernel_equal_weights_and_batch_are_bit_for_bit_equivalent() -> None:
    """Two SWE rows must not outweigh the one TAU row merely by row count."""
    rows = [
        _row("s1", real=1, sham=0, none=0, resample=0),
        _row("s2", real=1, sham=0, none=0, resample=0),
        _row("t1", benchmark="TAU", real=0, sham=1, none=1, resample=1),
    ]
    ref = ArtifactRef("roster", "roster.json", "0" * 64, 0, "application/json")
    scalar = rows_to_binary_sufficient_statistics(rows, roster_ref=ref)
    gates = evaluate_binary_gate_kernel(scalar, AnalysisConfig(), critical_value=0.0)
    by_code = {gate.code: gate for gate in gates}
    assert by_code["content_materiality"].observed == 0.0

    batch = BinarySufficientStatisticsBatch(
        roster_ref=ref,
        group_manifest=tuple(
            (benchmark, labels[0] if labels else None)
            for benchmark, labels, _ in scalar.benchmark_group_pattern_counts
        ),
        pattern_counts=np.array([counts for _, _, counts in scalar.benchmark_group_pattern_counts], dtype=np.int64)[None, :, :],
        arm_failure_counts=np.array([counts for _, counts in scalar.arm_failure_counts], dtype=np.int64)[None, :, :],
        pipeline_invalid_counts=np.array([scalar.pipeline_invalid_count], dtype=np.int64),
    )
    result = evaluate_binary_gate_batch(batch, AnalysisConfig(), critical_values=np.array([0.0]))
    assert bool(result.causal_pass[0]) is False
    assert result.content_estimate[0] == by_code["content_materiality"].observed
    assert result.excess_estimate[0] == by_code["excess_materiality"].observed
    assert result.content_sharp_p[0] == by_code["content_sharp"].observed
    assert result.excess_sharp_p[0] == by_code["excess_sharp"].observed
    assert result.differential_failure_gap[0] == by_code["differential_failure_gap"].observed
    assert bool(result.all_benchmark_nonnegative[0]) is by_code["benchmark_nonnegative"].passed
    assert bool(result.all_leave_one_nonnegative[0]) is by_code["leave_one_nonnegative"].passed


def test_outcome_classifier_has_frozen_precedence_and_never_feasibility_no_go() -> None:
    randomization = RandomizationResult(0.0, 1.0, "enumerated_exact", 1, None, None)
    bounds = SimultaneousBounds("secondary_three", ("sham_packet", "continuation", "total"), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (-1.0, -1.0, -1.0), (1.0, 1.0, 1.0), 1.0, "task_cluster_rademacher_max_t", 1, 0, 1)
    secondary = SecondaryFamilyResult(("sham_packet", "continuation", "total"), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), bounds)
    good = [GateResult(code, True, True, "is", True) for code in ("pipeline_valid", "differential_failure_gap", "content_sharp", "excess_sharp", "content_lower", "excess_lower", "content_materiality", "excess_materiality", "content_resolution", "excess_resolution", "benchmark_nonnegative", "leave_one_nonnegative")]
    positive = ContrastResult(0.1, 0.1, 0.01, 0.2, randomization)
    assert classify_verdict(good, content=positive, excess=positive, sham_packet=positive, resolution=ResolutionResult(0, 0.0, 0, "equal_roster_exact_binomial"), secondary=secondary) is Verdict.CAUSAL_CONTENT
    invalid = [GateResult("pipeline_valid", False, False, "is", True)]
    assert classify_verdict(invalid, content=positive, excess=positive, sham_packet=positive, resolution=ResolutionResult(0, 0, 0, "equal_roster_exact_binomial"), secondary=secondary) is Verdict.PIPELINE_INVALID
    harmful = ContrastResult(-0.05, 0.1, -0.2, -0.01, randomization)
    assert classify_verdict(good, content=harmful, excess=positive, sham_packet=positive, resolution=ResolutionResult(0, 0, 0, "equal_roster_exact_binomial"), secondary=secondary) is Verdict.HARMFUL_OR_MISDIRECTING
    unresolved = ContrastResult(0.01, 0.1, -0.1, 0.2, randomization)
    assert classify_verdict(good, content=unresolved, excess=positive, sham_packet=positive, resolution=ResolutionResult(0, 0, 0, "equal_roster_exact_binomial"), secondary=secondary) is Verdict.UNRESOLVED_RESAMPLING
    content_failure = [gate if gate.code != "content_sharp" else GateResult("content_sharp", False, 1.0, "<=", 0.05) for gate in good]
    sham_secondary = SecondaryFamilyResult(("sham_packet", "continuation", "total"), (0.01, 0.8, 0.9), (0.03, 1.0, 1.0), bounds)
    assert classify_verdict(content_failure, content=positive, excess=positive, sham_packet=positive, resolution=ResolutionResult(0, 0, 0, "equal_roster_exact_binomial"), secondary=sham_secondary) is Verdict.SHAM_PACKET_ONLY
    assert classify_verdict(content_failure, content=positive, excess=positive, sham_packet=positive, resolution=ResolutionResult(0, 0, 0, "equal_roster_exact_binomial"), secondary=secondary) is Verdict.RESAMPLING_CONSISTENT


def test_sham_verdict_does_not_treat_an_excess_only_joint_gate_failure_as_content_failure() -> None:
    randomization = RandomizationResult(0.0, 1.0, "enumerated_exact", 1, None, None)
    bounds = SimultaneousBounds("secondary_three", ("sham_packet", "continuation", "total"), (0.1, 0.0, 0.0), (0.1, 1.0, 1.0), (0.01, -1.0, -1.0), (0.2, 1.0, 1.0), 1.0, "task_cluster_rademacher_max_t", 1, 0, 1)
    secondary = SecondaryFamilyResult(("sham_packet", "continuation", "total"), (0.01, 1.0, 1.0), (0.03, 1.0, 1.0), bounds)
    positive = ContrastResult(0.1, 0.1, 0.01, 0.2, randomization)
    gates = [GateResult(code, True, True, "is", True) for code in (
        "pipeline_valid", "differential_failure_gap", "content_sharp", "excess_sharp",
        "content_lower", "excess_lower", "content_materiality", "excess_materiality",
        "content_resolution", "excess_resolution", "benchmark_nonnegative",
        "leave_one_nonnegative",
    )]
    gates = [
        gate if gate.code != "benchmark_nonnegative"
        else GateResult("benchmark_nonnegative", False, False, "is", True)
        for gate in gates
    ]

    verdict = classify_verdict(
        gates, content=positive, excess=positive, sham_packet=positive,
        resolution=ResolutionResult(0, 0, 0, "equal_roster_exact_binomial"),
        secondary=secondary, content_benchmark_nonnegative=True,
        content_leave_one_nonnegative=True,
    )

    assert verdict is Verdict.RESAMPLING_CONSISTENT


def test_batch_leave_one_empty_support_fails_only_affected_dataset() -> None:
    ref = ArtifactRef("roster", "roster.json", "0" * 64, 0, "application/json")
    overall = np.zeros((2, 16), dtype=np.int64)
    overall[:, 8] = (1, 2)
    group = np.zeros((2, 16), dtype=np.int64)
    group[:, 8] = (1, 1)
    patterns = np.stack((overall, group, overall, np.zeros_like(group)), axis=1)
    batch = BinarySufficientStatisticsBatch(
        roster_ref=ref,
        group_manifest=(("SWE", None), ("SWE", GroupLabel(GroupKind.LANGUAGE, "only")), ("TAU", None), ("TAU", GroupLabel(GroupKind.LANGUAGE, "empty"))),
        pattern_counts=patterns,
        arm_failure_counts=np.zeros((2, 2, 4), dtype=np.int64),
        pipeline_invalid_counts=np.zeros(2, dtype=np.int64),
    )

    result = evaluate_binary_gate_batch(batch, AnalysisConfig(), critical_values=np.zeros(2))

    assert result.all_leave_one_nonnegative.tolist() == [False, True]


def test_production_analysis_has_no_caller_selected_seed() -> None:
    from pneuma_lab.resampling_null.analysis import analyze

    assert "seed" not in signature(analyze).parameters


def test_manifest_inference_seed_is_domain_bound_and_manifest_owned() -> None:
    first = ArtifactRef("study_manifest", "study.json", "1" * 64, 1, "application/json")
    second = ArtifactRef("study_manifest", "study.json", "2" * 64, 1, "application/json")

    assert analysis_module.manifest_inference_seed(first, study_id="study") == 11077569387776841865
    assert analysis_module.manifest_inference_seed(first, study_id="study") != analysis_module.manifest_inference_seed(
        second, study_id="study",
    )
    assert analysis_module.manifest_inference_seed(first, study_id="study") != analysis_module.manifest_inference_seed(
        first, study_id="other",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("alpha", 0.1),
        ("delta_star", 0.04),
        ("sharp_draws", 999_998),
        ("multiplier_draws", 99_998),
        ("max_differential_failure_gap", 0.03),
    ],
)
def test_analysis_config_rejects_unregistered_decision_regions(
    field: str, value: float | int,
) -> None:
    with pytest.raises(ValueError, match="frozen"):
        AnalysisConfig(**{field: value})


def test_invalid_standard_errors_serialize_as_explicit_nulls() -> None:
    from pneuma_lab.resampling_null.artifacts import validate_record

    randomization = RandomizationResult(0.0, 1.0, "enumerated_exact", 1, None, None)
    primary = SimultaneousBounds(
        "co_primary", ("content", "excess"), (0.0, 0.0), (inf, inf),
        (-inf, -inf), (inf, inf), inf, "task_cluster_rademacher_max_t",
        99_999, 7, 0,
    )
    secondary_bounds = SimultaneousBounds(
        "secondary_three", ("sham_packet", "continuation", "total"),
        (0.0, 0.0, 0.0), (inf, inf, inf), (-inf, -inf, -inf),
        (inf, inf, inf), inf, "task_cluster_rademacher_max_t", 99_999, 7, 0,
    )
    contrast = ContrastResult(0.0, inf, -inf, inf, randomization)
    result = AnalysisResult(
        contrast, contrast, ContrastResult(0.0, inf, -inf, inf, None),
        0.0, 0.0, 0.0, randomization, primary,
        SecondaryFamilyResult(
            ("sham_packet", "continuation", "total"), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), secondary_bounds,
        ),
        ResolutionResult(0.0, 0.0, 0, "equal_roster_exact_binomial"),
        0.0, (BenchmarkEstimate("SWE", 0.0, 0.0), BenchmarkEstimate("TAU", 0.0, 0.0)),
        (), (), Verdict.UNRESOLVED_RESAMPLING, ("content_lower",),
    )

    payload = analysis_module.analysis_result_payload(result)

    assert payload["content"]["standard_error"] is None
    assert payload["primary_bounds"]["critical_value"] is None
    assert payload["primary_bounds"]["standard_errors"] == [None, None]
    ref = {
        "role": "test", "relative_path": "test.json", "sha256": "0" * 64,
        "byte_count": 1, "media_type": "application/json",
    }
    validate_record({
        "record_kind": "resampling_analysis",
        "schema_version": "0.2.0",
        "study_id": "study",
        "frozen_created_at": "2026-07-30T00:00:00Z",
        "provenance": {"design_sha256": "1" * 64, "code_sha256": "2" * 64},
        "payload": {
            "analysis_freeze_ref": ref,
            "projection_ref": ref,
            "unblind_receipt_ref": ref,
            "config_ref": ref,
            "row_count": 2,
            "result": payload,
            "numeric_receipt": {"finite": True},
        },
    })


def test_sensitivity_groups_apply_only_to_their_registered_benchmark() -> None:
    ref = ArtifactRef("roster", "roster.json", "0" * 64, 0, "application/json")
    swe = _row("s", real=1, sham=0, none=0, resample=0)
    tau = _row("t", benchmark="TAU", real=1, sham=0, none=0, resample=0)
    swe = AnalysisRow(
        **{
            **{field: getattr(swe, field) for field in swe.__dataclass_fields__},
            "sensitivity_groups": (
                GroupLabel(GroupKind.LANGUAGE, "python"),
                GroupLabel(GroupKind.DOMAIN, "not_applicable"),
                GroupLabel(GroupKind.ISSUE_FAMILY, "not_applicable"),
            ),
        }
    )
    tau = AnalysisRow(
        **{
            **{field: getattr(tau, field) for field in tau.__dataclass_fields__},
            "sensitivity_groups": (
                GroupLabel(GroupKind.LANGUAGE, "not_applicable"),
                GroupLabel(GroupKind.DOMAIN, "retail"),
                GroupLabel(GroupKind.ISSUE_FAMILY, "action"),
            ),
        }
    )

    statistics = rows_to_binary_sufficient_statistics((swe, tau), roster_ref=ref)

    grouped = {
        (benchmark, tuple(group.kind for group in labels))
        for benchmark, labels, _ in statistics.benchmark_group_pattern_counts
        if labels
    }
    assert grouped == {
        ("SWE", (GroupKind.LANGUAGE,)),
        ("TAU", (GroupKind.DOMAIN,)),
        ("TAU", (GroupKind.ISSUE_FAMILY,)),
    }


def test_leave_one_empty_group_is_reported_invalid_instead_of_crashing() -> None:
    swe = _row("s", real=1, sham=0, none=0, resample=0)
    tau = _row("t", benchmark="TAU", real=1, sham=0, none=0, resample=0)

    estimates = analysis_module.leave_one_estimates((swe, tau))

    swe_language = next(item for item in estimates if item.benchmark == "SWE")
    assert swe_language.content is None
    assert swe_language.excess is None


def test_hostile_asymmetric_benchmark_effect_fails_nonnegative_gate() -> None:
    rows = [
        *[
            _row(f"s{index}", real=0, sham=1, none=1, resample=1)
            for index in range(1, 4)
        ],
        _row("s4", real=1, sham=0, none=0, resample=0),
        *[
            _row(f"t{index}", benchmark="TAU", real=1, sham=0, none=0, resample=0)
            for index in range(1, 5)
        ],
    ]
    ref = ArtifactRef("roster", "roster.json", "0" * 64, 0, "application/json")

    gates = evaluate_binary_gate_kernel(
        rows_to_binary_sufficient_statistics(rows, roster_ref=ref),
        AnalysisConfig(), critical_value=0.0,
    )

    assert next(gate for gate in gates if gate.code == "benchmark_nonnegative").passed is False


def test_hostile_differential_branch_failure_fails_pipeline_gate() -> None:
    rows = [
        _row("s", real=1, sham=0, none=0, resample=0),
        _row("t", benchmark="TAU", real=1, sham=0, none=0, resample=0),
    ]
    rows[0] = AnalysisRow(
        **{
            **{field: getattr(rows[0], field) for field in rows[0].__dataclass_fields__},
            "real_infrastructure_failure": True,
        }
    )
    ref = ArtifactRef("roster", "roster.json", "0" * 64, 0, "application/json")

    gates = evaluate_binary_gate_kernel(
        rows_to_binary_sufficient_statistics(rows, roster_ref=ref),
        AnalysisConfig(), critical_value=0.0,
    )

    failure = next(gate for gate in gates if gate.code == "differential_failure_gap")
    assert failure.passed is False
    assert failure.observed == 0.5


def test_hostile_no_feedback_label_imbalance_fails_resolution_gates() -> None:
    rows = [
        _row("s", real=1, sham=0, none=0, resample=1),
        _row("t", benchmark="TAU", real=1, sham=0, none=0, resample=1),
    ]
    ref = ArtifactRef("roster", "roster.json", "0" * 64, 0, "application/json")

    gates = evaluate_binary_gate_kernel(
        rows_to_binary_sufficient_statistics(rows, roster_ref=ref),
        AnalysisConfig(), critical_value=0.0,
    )

    by_code = {gate.code: gate for gate in gates}
    assert by_code["content_resolution"].passed is False
    assert by_code["excess_resolution"].passed is False


def test_analyze_reloads_power_and_manifest_authority_before_rows(
    tmp_path, monkeypatch,
) -> None:
    import pneuma_lab.resampling_null.artifacts as artifacts_module
    import pneuma_lab.resampling_null.assignment as assignment_module

    manifest_ref = ArtifactRef(
        "study_manifest", "study.json", "1" * 64, 1, "application/json",
    )
    final_ref = ArtifactRef(
        "power_report", "power.json", "2" * 64, 1, "application/json",
    )
    roster_ref = ArtifactRef(
        "power_roster", "roster.json", "3" * 64, 1, "application/json",
    )
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        assignment_module, "require_schedulable_power_final",
        lambda manifest, final, *, run_root: (
            seen.setdefault("admission", (manifest, final, run_root)),
            SimpleNamespace(selected_task_ids=("task",)),
        )[1],
    )
    monkeypatch.setattr(
        artifacts_module, "_load_direct_scientific_parent",
        lambda *args, **kwargs: SimpleNamespace(value={
            "study_id": "study",
            "payload": {
                "roster_ref": {
                    field: getattr(roster_ref, field)
                    for field in roster_ref.__dataclass_fields__
                },
            },
        }),
    )
    monkeypatch.setattr(
        analysis_module, "manifest_inference_seed",
        lambda ref, *, study_id: seen.setdefault("rng", (ref, study_id)) or 7,
    )

    def stop_at_rows(*args, **kwargs):
        seen["rows"] = (args, kwargs)
        raise RuntimeError("row-admission-stop")

    monkeypatch.setattr(analysis_module, "_verify_roster_rows", stop_at_rows)

    with pytest.raises(RuntimeError, match="row-admission-stop"):
        analysis_module.analyze(
            (), AnalysisConfig(), manifest_ref=manifest_ref,
            power_final_ref=final_ref, run_root=tmp_path,
        )

    assert seen["admission"] == (manifest_ref, final_ref, tmp_path)
    assert seen["rng"] == (manifest_ref, "study")
    assert seen["rows"][1]["selected_task_ids"] == ("task",)

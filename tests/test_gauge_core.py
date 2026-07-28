"""Core gauge maths: stats primitives, cube IO, and estimator ground-truth recovery."""

from __future__ import annotations

import math
import random

import pytest

from pneuma_lab.gauge.anova import varianceComponents
from pneuma_lab.gauge.cube import Response, ResponseCube
from pneuma_lab.gauge.resolution import (
    discriminationIndex,
    effectiveSupport,
    gaugeResolution,
    gaugeVerdict,
    icc,
    ndc,
    pctGrr,
    resolvingPower,
    selectionStability,
)
from pneuma_lab.gauge.stats import (
    auroc,
    benjaminiHochberg,
    bootstrapCi,
    cohenKappa,
    expectedCalibrationError,
    normalCdf,
    normalQuantile,
    pairedTTest,
    shannonEntropy,
)
from pneuma_lab.gauge.synthetic import SELFTEST_SPECS, SyntheticSpec, syntheticCube
from pneuma_lab.gauge.theory import (
    aggregationAsymptote,
    aggregationCurve,
    aurocCeiling,
    minimumDetectableEffect,
    requiredK,
    validityCeiling,
)

# ---------------------------------------------------------------- stats


def test_normal_cdf_known_points():
    assert abs(normalCdf(0.0) - 0.5) < 1e-12
    assert abs(normalCdf(1.959963985) - 0.975) < 1e-8


def test_normal_quantile_roundtrips():
    for p in (0.001, 0.01, 0.25, 0.5, 0.75, 0.99, 0.999):
        assert abs(normalCdf(normalQuantile(p)) - p) < 1e-9


def test_bootstrap_ci_is_deterministic_and_brackets_the_truth():
    xs = [float(i) for i in range(100)]
    a = bootstrapCi(xs, lambda s: sum(s) / len(s), draws=400, seed=11)
    b = bootstrapCi(xs, lambda s: sum(s) / len(s), draws=400, seed=11)
    assert a == b
    assert a.low < 49.5 < a.high
    assert a.excludes(0.0)


def test_shannon_entropy_uniform():
    assert abs(shannonEntropy([1, 1, 1]) - math.log(3)) < 1e-12
    assert shannonEntropy([5]) == 0.0


def test_auroc_perfect_and_tied():
    assert auroc([0.1, 0.2, 0.9, 0.8], [0, 0, 1, 1]) == 1.0
    assert auroc([0.5, 0.5, 0.5, 0.5], [0, 0, 1, 1]) == 0.5
    assert auroc([1.0, 1.0], [1, 1]) is None


def test_ece_and_kappa_and_bh():
    assert expectedCalibrationError([0.95] * 4, [1, 1, 1, 1]) == pytest.approx(0.05)
    assert cohenKappa([1, 1, 0, 0], [1, 1, 0, 0]) == pytest.approx(1.0)
    assert cohenKappa([1, 0, 1, 0], [0, 1, 0, 1]) == pytest.approx(-1.0)
    assert benjaminiHochberg([0.001, 0.9, 0.02], q=0.05) == [True, False, True]


def test_paired_t_test_detects_a_small_shift():
    t, p = pairedTTest([0.05] * 40)
    assert math.isinf(t) and p == 0.0
    t, p = pairedTTest([0.05 + 0.01 * ((-1) ** i) for i in range(40)])
    assert p < 0.001


# ---------------------------------------------------------------- cube


def _response(item, cond, rep, value, **kw):
    fields = {
        "item_id": item,
        "model": "m",
        "wording_id": cond,
        "scale_id": "p2",
        "provenance": "foreign",
        "arm": "base",
        "temperature": 0.7,
        "replicate": rep,
        "raw_text": str(value),
        "value": value,
        "parse_ok": True,
    }
    fields.update(kw)
    return Response(**fields)


def test_cube_jsonl_roundtrip_is_byte_stable(tmp_path):
    rows = [
        _response(f"i{i}", f"w{o}", r, 0.1 * i + 0.01 * o + 0.001 * r)
        for i in range(3)
        for o in range(2)
        for r in range(2)
    ]
    cube = ResponseCube(rows)
    first = cube.toJsonl(tmp_path / "a.jsonl").read_bytes()
    second = (
        ResponseCube.fromJsonl(tmp_path / "a.jsonl")
        .toJsonl(tmp_path / "b.jsonl")
        .read_bytes()
    )
    assert first == second


def test_balanced_matrix_truncates_and_reports():
    rows = [_response("i0", "w0", r, 0.5) for r in range(3)]
    rows += [_response("i0", "w1", r, 0.6) for r in range(2)]
    rows += [_response("i1", "w0", r, 0.7) for r in range(2)]
    rows += [_response("i1", "w1", r, 0.8) for r in range(2)]
    rows.append(_response("i1", "w1", 9, None, parse_ok=False, raw_text="dunno"))
    matrix = ResponseCube(rows).balancedMatrix(("wording_id",))
    assert matrix.n_items == 2 and matrix.n_conditions == 2 and matrix.n_reps == 2
    assert matrix.parse_failure_rate == pytest.approx(1 / 10)
    assert all(len(v) == 2 for v in matrix.cells.values())


def test_balanced_matrix_drops_uncrossed_cells():
    rows = [_response("i0", "w0", r, 0.5) for r in range(2)]
    rows += [_response("i1", "w0", r, 0.6) for r in range(2)]
    rows += [_response("i2", "w0", r, 0.7) for r in range(2)]
    rows += [_response("i0", "w1", r, 0.8) for r in range(2)]
    rows += [_response("i1", "w1", r, 0.9) for r in range(2)]
    matrix = ResponseCube(rows).balancedMatrix(("wording_id",))
    assert matrix.dropped_items == ("i2",)
    assert matrix.n_items == 2 and matrix.n_conditions == 2


# ---------------------------------------------------------------- anova


def _matrix(sd_item, sd_cond, sd_inter, sd_err, n_items=48, n_cond=8, n_reps=8, seed=3):
    rng = random.Random(seed)
    a = [rng.gauss(0, sd_item) for _ in range(n_items)]
    b = [rng.gauss(0, sd_cond) for _ in range(n_cond)]
    ab = [[rng.gauss(0, sd_inter) for _ in range(n_cond)] for _ in range(n_items)]
    return {
        (f"i{i:03d}", f"c{o}"): [
            a[i] + b[o] + ab[i][o] + rng.gauss(0, sd_err) for _ in range(n_reps)
        ]
        for i in range(n_items)
        for o in range(n_cond)
    }


def test_anova_recovers_known_variance_components():
    vc = varianceComponents(_matrix(0.30, 0.10, 0.05, 0.20))
    assert vc.sd_item == pytest.approx(0.30, abs=0.06)
    assert vc.sd_repeatability == pytest.approx(0.20, abs=0.02)
    assert vc.sd_condition == pytest.approx(0.10, abs=0.06)
    assert vc.sd_interaction == pytest.approx(0.05, abs=0.03)


def test_anova_recovers_zero_item_variance():
    vc = varianceComponents(_matrix(0.0, 0.05, 0.02, 0.20))
    assert vc.sd_item < 0.05
    assert icc(vc) < 0.05


def test_anova_rejects_degenerate_designs():
    with pytest.raises(ValueError):
        varianceComponents({("i0", "c0"): [0.1, 0.2], ("i1", "c0"): [0.3, 0.4]})
    with pytest.raises(ValueError):
        varianceComponents(
            {
                ("i0", "c0"): [0.1],
                ("i0", "c1"): [0.2],
                ("i1", "c0"): [0.3],
                ("i1", "c1"): [0.4],
            }
        )


def test_anova_rejects_unbalanced_replicates():
    m = _matrix(0.2, 0.05, 0.02, 0.1, n_items=3, n_cond=2, n_reps=4)
    m[("i000", "c0")] = m[("i000", "c0")][:3]
    with pytest.raises(ValueError):
        varianceComponents(m)


# ---------------------------------------------------------------- resolution


def test_good_gauge_is_usable():
    m = _matrix(0.30, 0.01, 0.005, 0.02)
    vc = varianceComponents(m)
    assert ndc(vc) >= 5
    assert pctGrr(vc) <= 30.0
    assert discriminationIndex(m) > 0.95
    assert (
        gaugeVerdict(
            pct_grr=pctGrr(vc),
            ndc_value=ndc(vc),
            icc_value=icc(vc),
            d=discriminationIndex(m),
            s_eff=99.0,
        )
        == "USABLE"
    )


def test_pure_noise_gauge_is_a_coin_flip():
    m = _matrix(0.0, 0.05, 0.02, 0.20)
    vc = varianceComponents(m)
    assert ndc(vc) == 0
    assert discriminationIndex(m) == pytest.approx(0.5, abs=0.05)
    assert (
        gaugeVerdict(
            pct_grr=pctGrr(vc),
            ndc_value=ndc(vc),
            icc_value=icc(vc),
            d=discriminationIndex(m),
            s_eff=99.0,
        )
        == "UNINTERPRETABLE"
    )


def test_constant_channel_scores_exactly_one_half_and_is_degenerate():
    m = {(f"i{i}", f"c{o}"): [0.95] * 4 for i in range(6) for o in range(3)}
    assert discriminationIndex(m) == pytest.approx(0.5)
    assert resolvingPower(m) == 0.0
    assert effectiveSupport([0.95] * 100) == pytest.approx(1.0)
    vc = varianceComponents(m)
    assert (
        gaugeVerdict(
            pct_grr=pctGrr(vc), ndc_value=ndc(vc), icc_value=icc(vc), d=0.5, s_eff=1.0
        )
        == "DEGENERATE"
    )


def test_resolving_power_never_exceeds_discrimination():
    m = _matrix(0.1, 0.05, 0.02, 0.15)
    assert resolvingPower(m) <= discriminationIndex(m) + 1e-12


def test_selection_stability_brackets_a_good_gauge_and_pure_noise():
    """A verification pipeline ranks and verifies the bottom q; is that queue reproducible?"""
    good = selectionStability(_matrix(0.30, 0.01, 0.005, 0.02), q=0.2)
    noise = selectionStability(_matrix(0.0, 0.05, 0.02, 0.20), q=0.2)
    assert good["jaccard"] > 0.8
    assert noise["jaccard"] == pytest.approx(noise["random_floor"], abs=0.05)
    assert good["random_floor"] == pytest.approx(0.2 / 1.8)
    assert good["n_selected"] == 10


def test_selection_stability_is_deterministic():
    m = _matrix(0.1, 0.05, 0.02, 0.15)
    assert selectionStability(m, q=0.25) == selectionStability(m, q=0.25)


def test_effective_support_counts_levels_not_range():
    assert effectiveSupport([0.0, 1.0] * 50) == pytest.approx(2.0)
    assert effectiveSupport([0.85, 0.95, 1.0] * 30) == pytest.approx(3.0)


# ---------------------------------------------------------------- theory


def test_validity_ceiling_is_sqrt_reliability():
    assert validityCeiling(0.04) == pytest.approx(0.2)
    assert validityCeiling(0.0) == 0.0
    assert validityCeiling(1.0) == 1.0


def test_auroc_ceiling_bounds_and_monotonicity():
    assert aurocCeiling(0.0, 0.5) == pytest.approx(0.5)
    assert aurocCeiling(0.999999, 0.5) > 0.99
    prev = 0.5
    for r in (0.05, 0.1, 0.3, 0.5, 0.7, 0.9):
        got = aurocCeiling(r, 0.5)
        assert got >= prev
        prev = got
    with pytest.raises(ValueError):
        aurocCeiling(0.5, 0.0)


def test_aggregation_curve_converges_to_its_asymptote():
    vc = varianceComponents(_matrix(0.05, 0.08, 0.04, 0.30))
    curve = aggregationCurve(vc, ks=(1, 2, 4, 8, 10**6))
    values = [point["reliability"] for point in curve["curve"]]
    assert values == sorted(values)
    assert values[-1] == pytest.approx(curve["asymptote"], abs=1e-6)
    assert curve["asymptote"] < 0.70


def test_required_k_is_none_when_the_asymptote_is_below_target():
    vc = varianceComponents(_matrix(0.02, 0.10, 0.05, 0.30))
    assert (
        aggregationAsymptote(
            var_item=vc.var_item, var_systematic=vc.var_condition + vc.var_interaction
        )
        < 0.70
    )
    assert requiredK(vc, target=0.70) is None


def test_required_k_is_finite_when_reachable():
    vc = varianceComponents(_matrix(0.30, 0.001, 0.001, 0.40))
    k = requiredK(vc, target=0.70)
    assert k is not None and k >= 1


def test_mde_shrinks_with_sample_size_regardless_of_resolution():
    small = minimumDetectableEffect(sd_grr=0.2, n_items=48, k=1)
    large = minimumDetectableEffect(sd_grr=0.2, n_items=48, k=64)
    assert large < small
    assert large < 0.02


# ---------------------------------------------------------------- selftest battery


@pytest.mark.parametrize(
    "spec,expected", SELFTEST_SPECS, ids=[s.name for s, _ in SELFTEST_SPECS]
)
def test_selftest_battery_reaches_its_known_verdict(spec: SyntheticSpec, expected: str):
    matrix = syntheticCube(spec).filter(arm="base").balancedMatrix(("wording_id",))
    assert gaugeResolution(matrix).verdict == expected

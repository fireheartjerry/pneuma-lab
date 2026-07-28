"""The remedy battery and the placebo machinery.

The load-bearing test in this file is `test_strictly_monotone_calibration_is_exactly_invariant`:
T2 says post-hoc calibration cannot change resolution, and it says so to machine
precision, not approximately.
"""

from __future__ import annotations

import math
import random

import pytest

from pneuma_lab.gauge.cube import Response, ResponseCube
from pneuma_lab.gauge.placebo import placeboReport
from pneuma_lab.gauge.remedies import (
    calibration,
    isotonicFit,
    plattFit,
    runRemedies,
    secondModel,
    selfConsistency,
    thresholding,
    wordingAveraging,
)
from pneuma_lab.gauge.resolution import (
    discriminationIndex,
    gaugeResolution,
    resolvingPower,
)
from pneuma_lab.gauge.stats import auroc, expectedCalibrationError
from pneuma_lab.gauge.synthetic import SyntheticSpec, syntheticCube


def _cube(**kw) -> ResponseCube:
    spec = SyntheticSpec(
        **{
            "sd_item": 0.02,
            "sd_condition": 0.05,
            "sd_interaction": 0.03,
            "sd_error": 0.15,
            **kw,
        }
    )
    return syntheticCube(spec)


def _matrixOf(cube: ResponseCube, facets=("wording_id", "scale_id")) -> dict:
    return dict(cube.balancedMatrix(facets).cells)


# ------------------------------------------------------------ T2: calibration


def test_strictly_monotone_calibration_is_exactly_invariant():
    """T2(1): strictly increasing g => D and resolving power are unchanged, exactly."""
    cube = _cube()
    d0 = discriminationIndex(_matrixOf(cube))
    p0 = resolvingPower(_matrixOf(cube))
    maps = (
        lambda v: 1.0 / (1.0 + math.exp(-6.0 * (v - 0.5))),
        lambda v: v**3,
        lambda v: 3.7 * v - 12.0,
        lambda v: math.atan(v),
    )
    for g in maps:
        mapped = cube.mapValues(g)
        assert discriminationIndex(_matrixOf(mapped)) == d0
        assert resolvingPower(_matrixOf(mapped)) == p0


def test_strictly_monotone_calibration_leaves_auroc_exactly_invariant():
    rng = random.Random(5)
    scores = [rng.random() for _ in range(200)]
    labels = [1 if rng.random() < s else 0 for s in scores]
    base = auroc(scores, labels)
    g = plattFit(scores, labels)
    assert auroc([g(s) for s in scores], labels) == pytest.approx(base, abs=1e-12)


def test_isotonic_can_only_destroy_ordering_never_create_it():
    """T2(2): weakly increasing g => resolving power can only fall."""
    cube = _cube()
    truth = {item: (0 if int(item[1:]) % 2 else 1) for item in cube.values("item_id")}
    p0 = resolvingPower(_matrixOf(cube))
    flat = [(r.value, truth[r.item_id]) for r in cube.rows if r.parse_ok]
    iso = isotonicFit([s for s, _ in flat], [y for _, y in flat])
    assert resolvingPower(_matrixOf(cube.mapValues(iso))) <= p0 + 1e-12


def test_calibration_remedy_reports_the_ece_illusion():
    cube = _cube()
    truth = {item: (0 if int(item[1:]) % 2 else 1) for item in cube.values("item_id")}
    result = calibration(cube, truth, draws=120)
    assert result.verdict == "FAILS"
    # ECE improves substantially while D does not move at all.
    assert result.detail["after"]["platt"]["ece"] < result.detail["before"]["ece"]
    assert result.detail["after"]["platt"]["d"] == pytest.approx(
        result.detail["before"]["d"], abs=1e-12
    )


def test_platt_fit_is_strictly_increasing():
    rng = random.Random(9)
    scores = [rng.random() for _ in range(300)]
    labels = [1 if rng.random() < s else 0 for s in scores]
    g = plattFit(scores, labels)
    xs = [i / 100.0 for i in range(101)]
    ys = [g(x) for x in xs]
    assert all(b > a for a, b in zip(ys[:-1], ys[1:], strict=True))


def test_expected_calibration_error_moves_when_platt_recentres():
    rng = random.Random(4)
    scores = [0.9 + 0.05 * rng.random() for _ in range(200)]
    labels = [1 if rng.random() < 0.5 else 0 for _ in range(200)]
    g = plattFit(scores, labels)
    assert expectedCalibrationError(
        [g(s) for s in scores], labels
    ) < expectedCalibrationError(scores, labels)


# ------------------------------------------------------------ aggregation remedies


def test_self_consistency_fails_when_the_asymptote_is_below_the_floor():
    result = selfConsistency(_cube(), ks=(1, 2, 4, 8), draws=120)
    assert result.verdict == "FAILS"
    assert result.detail["asymptote"] < 0.70
    assert result.detail["required_k"] is None
    assert "unreachable" in result.note
    curve = [point["reliability"] for point in result.detail["empirical_curve"]]
    assert curve == sorted(curve) or max(curve) < 0.70


def test_self_consistency_helps_on_a_gauge_that_is_merely_noisy():
    """Control: the remedy is not rigged to fail. A high-signal, high-noise gauge is fixable."""
    result = selfConsistency(
        _cube(sd_item=0.30, sd_condition=0.001, sd_interaction=0.001, sd_error=0.30),
        ks=(1, 2, 4, 8),
        draws=120,
    )
    assert result.verdict == "HELPS"
    assert result.detail["required_k"] is not None


def test_wording_averaging_reports_its_asymptote_and_required_k():
    result = wordingAveraging(_cube(), draws=120)
    assert result.verdict == "FAILS"
    assert "asymptote" in result.note
    assert result.ci.low <= result.value <= result.ci.high


def test_thresholding_reports_the_best_cut_and_the_flip_rate():
    result = thresholding(_cube(), draws=120)
    assert result.verdict == "FAILS"
    assert 0.0 <= result.detail["flip_rate"] <= 1.0
    assert result.detail["n_cuts"] >= 1


def test_second_model_adds_variance_rather_than_removing_it():
    a = _cube(name="model_a")
    b = syntheticCube(
        SyntheticSpec(
            sd_item=0.02,
            sd_condition=0.06,
            sd_interaction=0.03,
            sd_error=0.18,
            name="model_b",
        ),
        seed=99,
    )
    result = secondModel(a.merge(b), primary="model_a", judge="model_b", draws=120)
    assert result.verdict == "FAILS"
    assert result.detail["cross_model_icc"] < 0.70


def test_run_remedies_records_skips_rather_than_dropping_them():
    results = runRemedies(_cube(), draws=60)
    names = [r.name for r in results]
    assert names == [
        "second_model",
        "thresholding",
        "calibration",
        "wording_averaging",
        "self_consistency",
    ]
    skipped = {r.name: r for r in results if r.verdict == "SKIPPED"}
    assert set(skipped) == {"second_model", "calibration"}
    assert all(r.note for r in skipped.values())


# ------------------------------------------------------------ placebo


def test_placebo_dominance_exceeds_one_when_item_variance_collapses():
    cube = syntheticCube(
        SyntheticSpec(
            sd_item=0.005,
            sd_condition=0.05,
            sd_interaction=0.02,
            sd_error=0.15,
            sham_shift=0.05,
            name="collapsed",
        )
    )
    report = placeboReport(cube, draws=200)
    assert report.pi > 1.0
    assert report.p_value < 0.05
    assert report.contrast_ci.excludes(0.0)
    # The same data has no resolution to state that effect in.
    resolution = gaugeResolution(
        cube.filter(arm="base").balancedMatrix(("wording_id",))
    )
    assert resolution.verdict == "UNINTERPRETABLE"
    assert resolution.ndc < 2


def test_placebo_dominance_is_below_one_for_a_real_gauge():
    """Control: a gauge that actually measures something is item-dominated, not placebo-dominated."""
    cube = syntheticCube(
        SyntheticSpec(
            sd_item=0.30,
            sd_condition=0.01,
            sd_interaction=0.005,
            sd_error=0.02,
            sham_shift=0.005,
            name="real_gauge",
        )
    )
    report = placeboReport(cube, draws=200)
    assert report.pi < 1.0


def test_mde_shrinks_below_the_placebo_effect_it_would_certify():
    cube = syntheticCube(
        SyntheticSpec(
            sd_item=0.005,
            sd_condition=0.05,
            sd_interaction=0.02,
            sd_error=0.15,
            sham_shift=0.05,
            name="collapsed",
        )
    )
    report = placeboReport(cube, draws=100)
    assert report.mde < abs(report.contrast)


def test_placebo_requires_both_arms():
    with pytest.raises(ValueError):
        placeboReport(_cube(), draws=50)

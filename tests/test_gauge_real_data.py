"""Regression tests against *real* elicitations, not synthetic ones.

`fixtures/gauge/g1-core-sample.jsonl` is a balanced 12-item x 4-wording slice of the
G-1 core stage (qwen2.5-coder:7b rating bank code it did not write, p2 scale,
T=0.7). Synthetic data can be made to satisfy any theorem; these assertions have to
hold on numbers a real model actually produced.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from pneuma_lab.gauge.anova import varianceComponents
from pneuma_lab.gauge.cube import ResponseCube
from pneuma_lab.gauge.remedies import isotonicFit, plattFit
from pneuma_lab.gauge.resolution import (
    discriminationIndex,
    effectiveSupport,
    gaugeResolution,
    resolvingPower,
)
from pneuma_lab.gauge.stats import auroc, expectedCalibrationError
from pneuma_lab.gauge.theory import aurocCeiling, validityCeiling

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "gauge" / "g1-core-sample.jsonl"
)


@pytest.fixture(scope="module")
def cube() -> ResponseCube:
    return ResponseCube.fromJsonl(FIXTURE)


@pytest.fixture(scope="module")
def matrix(cube: ResponseCube):
    return cube.balancedMatrix(("wording_id",))


def _truth(cube: ResponseCube) -> dict[str, int]:
    return {i: (1 if i.endswith("__correct") else 0) for i in cube.values("item_id")}


def test_fixture_shape(cube: ResponseCube, matrix):
    assert len(cube) == 384
    assert matrix.n_items >= 10 and matrix.n_conditions == 4 and matrix.n_reps >= 5
    assert set(cube.values("model")) == {"qwen2.5-coder:7b"}
    assert set(cube.values("provenance")) == {"foreign"}


def test_real_channel_emits_few_levels_but_is_not_degenerate(cube: ResponseCube):
    values = [r.value for r in cube.rows if r.parse_ok]
    support = effectiveSupport(values)
    # Offered a continuous 0.00-1.00 scale, the channel uses a handful of levels.
    assert 2.0 < support < 12.0
    assert len({round(v, 4) for v in values}) < 30


def test_real_channel_has_signal_but_no_item_resolution(matrix):
    """The core finding: aggregate signal is real, per-item resolution is not."""
    res = gaugeResolution(matrix)
    assert res.components.var_item > 0.0, (
        "there IS item variance; this is not pure noise"
    )
    assert res.ndc < 2, "yet the gauge resolves fewer than two distinct categories"
    assert res.verdict in {"UNINTERPRETABLE", "MARGINAL"}
    assert 0.5 < res.d < 0.95


def test_observed_validity_respects_the_reliability_ceiling(cube: ResponseCube, matrix):
    """T1 on real data: measured AUROC must not exceed the ceiling its reliability implies."""
    truth = _truth(cube)
    scores = [r.value for r in cube.rows if r.parse_ok and r.item_id in truth]
    labels = [truth[r.item_id] for r in cube.rows if r.parse_ok and r.item_id in truth]
    observed = auroc(scores, labels)
    res = gaugeResolution(matrix)
    ceiling = aurocCeiling(res.icc, sum(labels) / len(labels))
    assert observed is not None
    assert observed <= ceiling + 1e-9
    assert validityCeiling(res.icc) <= 1.0


def test_calibration_on_real_data_moves_ece_and_not_resolution(
    cube: ResponseCube, matrix
):
    """T2 on real data: the ECE improvement is real and the resolution change is exactly zero."""
    truth = _truth(cube)
    scores = [r.value for r in cube.rows if r.parse_ok and r.item_id in truth]
    labels = [truth[r.item_id] for r in cube.rows if r.parse_ok and r.item_id in truth]

    before_d = discriminationIndex(matrix)
    before_rp = resolvingPower(matrix)
    before_ece = expectedCalibrationError(scores, labels)
    before_auroc = auroc(scores, labels)

    platt = plattFit(scores, labels)
    after = cube.mapValues(platt).balancedMatrix(("wording_id",))

    assert discriminationIndex(after) == before_d
    assert resolvingPower(after) == before_rp
    assert auroc([platt(s) for s in scores], labels) == pytest.approx(
        before_auroc, abs=1e-12
    )
    # ...while the statistic papers report improves substantially.
    assert (
        expectedCalibrationError([platt(s) for s in scores], labels) < before_ece - 0.05
    )


def test_isotonic_on_real_data_cannot_increase_resolving_power(
    cube: ResponseCube, matrix
):
    truth = _truth(cube)
    scores = [r.value for r in cube.rows if r.parse_ok and r.item_id in truth]
    labels = [truth[r.item_id] for r in cube.rows if r.parse_ok and r.item_id in truth]
    iso = isotonicFit(scores, labels)
    after = cube.mapValues(iso).balancedMatrix(("wording_id",))
    assert resolvingPower(after) <= resolvingPower(matrix) + 1e-12


def test_wordings_shift_the_level_of_the_same_channel(cube: ResponseCube):
    """Reproducibility is not hypothetical: rewording moves the reported number."""
    means = {}
    for wording in cube.values("wording_id"):
        values = [r.value for r in cube.rows if r.wording_id == wording and r.parse_ok]
        means[wording] = math.fsum(values) / len(values)
    assert max(means.values()) - min(means.values()) > 0.02


def test_variance_components_are_all_identified_on_real_data(matrix):
    vc = varianceComponents(matrix)
    assert vc.var_total > 0.0
    assert vc.var_repeatability > 0.0
    assert vc.var_grr > 0.0

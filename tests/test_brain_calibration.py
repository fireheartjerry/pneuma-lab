from __future__ import annotations

from pneuma_lab.brain import calibration as cal
from pneuma_lab.estimators.metrics import auroc, ece


def test_platt_preserves_ranking() -> None:
    scores = [0.05, 0.2, 0.55, 0.7, 0.9, 0.95]
    labels = [0, 0, 1, 0, 1, 1]
    a, b = cal.fit_platt(scores, labels)
    calibrated = [cal.apply_platt(s, a, b) for s in scores]
    # Monotonic map -> AUROC unchanged.
    assert auroc(calibrated, labels) == auroc(scores, labels)


def test_platt_reduces_ece_on_miscalibrated_scores() -> None:
    # Scores that rank well but are systematically overconfident-low.
    labels = [0, 0, 0, 0, 1, 1, 1, 1]
    scores = [0.01, 0.02, 0.03, 0.04, 0.10, 0.12, 0.14, 0.16]
    a, b = cal.fit_platt(scores, labels)
    calibrated = [cal.apply_platt(s, a, b) for s in scores]
    assert ece(calibrated, labels) <= ece(scores, labels)


def test_fit_platt_is_deterministic() -> None:
    scores = [0.1, 0.4, 0.6, 0.9]
    labels = [0, 0, 1, 1]
    assert cal.fit_platt(scores, labels) == cal.fit_platt(scores, labels)


def test_guarded_platt_falls_back_to_identity_when_inverted() -> None:
    # Logits anti-correlated with labels would fit a negative slope; the guard
    # must refuse it and return identity rather than ship an inverted advisory.
    logits = [3.0, 2.0, 1.0, -1.0, -2.0, -3.0]
    labels = [0, 0, 0, 1, 1, 1]
    a, b = cal.fit_guarded_platt(logits, labels)
    assert (a, b) == cal.IDENTITY


def test_guarded_platt_never_worsens_ece_and_keeps_ranking() -> None:
    from pneuma_lab.estimators.logistic import sigmoid
    from pneuma_lab.estimators.metrics import auroc, ece

    logits = [-2.0, -1.0, -0.5, 0.5, 1.0, 2.0, 2.5, 3.0]
    labels = [0, 0, 1, 0, 1, 1, 1, 1]
    a, b = cal.fit_guarded_platt(logits, labels)
    assert a >= 0.0
    raw = [sigmoid(x) for x in logits]
    calibrated = [cal.apply_platt(x, a, b) for x in logits]
    assert ece(calibrated, labels) <= ece(raw, labels)
    assert auroc(calibrated, labels) == auroc(raw, labels)

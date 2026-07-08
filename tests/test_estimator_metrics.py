"""AUROC / Brier / ECE against hand-computed values on tiny cases.
Hermetic — no dataset reads."""

import pytest

from pneuma_lab.estimators import metrics as met


def test_aurocSimple():
    # pos 0.35 beats neg 0.1, loses to neg 0.4; pos 0.8 beats both -> 3/4
    assert met.auroc([0.1, 0.4, 0.35, 0.8], [0, 0, 1, 1]) == pytest.approx(0.75)


def test_aurocPerfect():
    assert met.auroc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) == 1.0


def test_aurocTieMidranks():
    # pos 0.5: win vs 0.2 (1) + tie vs 0.5 (0.5); pos 0.9: 2 wins -> 3.5/4
    assert met.auroc([0.2, 0.5, 0.5, 0.9], [0, 0, 1, 1]) == pytest.approx(0.875)


def test_aurocAllTiedIsChance():
    assert met.auroc([0.3, 0.3, 0.3, 0.3], [0, 1, 0, 1]) == pytest.approx(0.5)


def test_aurocSingleClassIsNone():
    assert met.auroc([0.1, 0.9], [1, 1]) is None
    assert met.auroc([0.1, 0.9], [0, 0]) is None


def test_brierHandComputed():
    # ((0.8-1)^2 + (0.4-0)^2) / 2 = (0.04 + 0.16) / 2
    assert met.brier([0.8, 0.4], [1, 0]) == pytest.approx(0.1)


def test_brierPerfectAndWorst():
    assert met.brier([1.0, 0.0], [1, 0]) == 0.0
    assert met.brier([0.0, 1.0], [1, 0]) == 1.0


def test_eceTwoBinsHandComputed():
    # bin1 [0.2,0.4]: |0.3-0.5|=0.2; bin2 [0.6,0.8]: |0.7-1.0|=0.3
    # ECE = 0.5*0.2 + 0.5*0.3 = 0.25
    probs = [0.2, 0.4, 0.6, 0.8]
    labels = [0, 1, 1, 1]
    assert met.ece(probs, labels, n_bins=2) == pytest.approx(0.25)


def test_eceFifteenBinsSmallNIsMeanAbsGap():
    # with n=4 < 15 bins, every non-empty equal-mass bin is a singleton
    probs = [0.2, 0.4, 0.6, 0.8]
    labels = [0, 0, 1, 1]
    expected = (0.2 + 0.4 + 0.4 + 0.2) / 4
    assert met.ece(probs, labels) == pytest.approx(expected)


def test_ecePerfectCalibrationConstant():
    # constant prediction equal to the base rate, one bin
    assert met.ece([0.5, 0.5, 0.5, 0.5], [0, 1, 0, 1], n_bins=1) == pytest.approx(0.0)


def test_lengthMismatchRaises():
    with pytest.raises(ValueError):
        met.auroc([0.1], [0, 1])
    with pytest.raises(ValueError):
        met.brier([0.1], [0, 1])
    with pytest.raises(ValueError):
        met.ece([0.1], [0, 1])

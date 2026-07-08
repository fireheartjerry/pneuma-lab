"""Deterministic pure-stdlib logistic regression: learns a separable toy
problem and repeats byte-identically. Hermetic — no dataset reads."""

from pneuma_lab.adapters.envelope import canonical_json
from pneuma_lab.estimators import logistic as logit
from pneuma_lab.estimators import metrics as met

TOY_ROWS = [
    (-2.0, 1.0),
    (-1.5, 0.5),
    (-1.0, 1.5),
    (-0.5, 0.0),
    (0.5, 1.0),
    (1.0, 0.5),
    (1.5, 1.5),
    (2.0, 0.0),
]
TOY_LABELS = [0, 0, 0, 0, 1, 1, 1, 1]


def trainToy():
    means, stds = logit.standardizationParams(TOY_ROWS)
    rows_std = [logit.standardizeRow(r, means, stds) for r in TOY_ROWS]
    weights, bias = logit.trainLogistic(rows_std, TOY_LABELS)
    probs = [logit.predictProb(r, weights, bias) for r in rows_std]
    return weights, bias, probs


def test_learnsSeparableToyProblem():
    weights, bias, probs = trainToy()
    for p, y in zip(probs, TOY_LABELS):
        if y == 1:
            assert p > 0.5
        else:
            assert p < 0.5
    assert met.auroc(probs, TOY_LABELS) == 1.0
    # the separating feature carries the weight, the noise feature does not
    assert weights[0] > abs(weights[1])


def test_deterministicRepeat():
    first = trainToy()
    second = trainToy()
    assert canonical_json(first) == canonical_json(second)


def test_zeroVarianceFeatureGetsUnitStd():
    rows = [(1.0, 7.0), (2.0, 7.0), (3.0, 7.0)]
    means, stds = logit.standardizationParams(rows)
    assert stds[1] == 1.0
    assert means[1] == 7.0
    assert logit.standardizeRow((2.0, 7.0), means, stds)[1] == 0.0


def test_sigmoidStableAtExtremes():
    assert logit.sigmoid(1000.0) == 1.0
    assert logit.sigmoid(-1000.0) == 0.0
    assert logit.sigmoid(0.0) == 0.5

"""Platt scaling: map raw scores to calibrated probabilities.

Fits a 1-D logistic ``p = sigmoid(a*score + b)`` by deterministic full-batch
gradient descent. Monotonic in ``score`` when ``a >= 0``, so ranking (and hence
AUROC) is preserved; only probability calibration changes.
"""

from __future__ import annotations

import math

from pneuma_lab.estimators.logistic import sigmoid

PLATT_ITERATIONS = 400
PLATT_LR = 0.5


def fit_platt(
    scores: list[float],
    labels: list[int],
    *,
    iterations: int = PLATT_ITERATIONS,
    lr: float = PLATT_LR,
) -> tuple[float, float]:
    """Fit (a, b) for p = sigmoid(a*score + b). Deterministic."""
    if not scores or len(scores) != len(labels):
        raise ValueError("scores/labels empty or mismatched")
    n = len(scores)
    a, b = 1.0, 0.0
    for _ in range(iterations):
        grad_a = 0.0
        grad_b = 0.0
        for score, label in zip(scores, labels):
            error = sigmoid(a * score + b) - label
            grad_a += error * score
            grad_b += error
        a -= lr * grad_a / n
        b -= lr * grad_b / n
    return a, b


def apply_platt(score: float, a: float, b: float) -> float:
    """Calibrated probability for one raw score."""
    return sigmoid(a * score + b)


__all__ = ["PLATT_ITERATIONS", "PLATT_LR", "fit_platt", "apply_platt"]

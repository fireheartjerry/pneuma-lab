"""Platt scaling: map raw scores to calibrated probabilities.

Fits a 1-D logistic ``p = sigmoid(a*score + b)`` by deterministic full-batch
gradient descent. Monotonic in ``score`` when ``a >= 0``, so ranking (and hence
AUROC) is preserved; only probability calibration changes.
"""

from __future__ import annotations

import math

from pneuma_lab.estimators.logistic import sigmoid
from pneuma_lab.estimators.metrics import ece

PLATT_ITERATIONS = 400
PLATT_LR = 0.5

# Identity in logit space: apply_platt(logit, 1.0, 0.0) == sigmoid(logit) == the
# model's own raw probability, i.e. no calibration change.
IDENTITY = (1.0, 0.0)


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
    """Calibrated probability for one raw logit score."""
    return sigmoid(a * score + b)


def fit_guarded_platt(logits: list[float], labels: list[int]) -> tuple[float, float]:
    """Fit Platt on logits, but fall back to identity unless it strictly helps.

    Returns identity ``(1.0, 0.0)`` (which reproduces the model's own raw
    probability) whenever the fitted slope is negative — which would invert the
    advisory — or whenever calibration does not reduce ECE. This makes the
    calibration layer safe: it can never invert risk and can never worsen
    calibration relative to the raw sigmoid.
    """
    a, b = fit_platt(logits, labels)
    if a < 0.0:
        return IDENTITY
    before = ece([sigmoid(x) for x in logits], labels)
    after = ece([apply_platt(x, a, b) for x in logits], labels)
    if after > before:
        return IDENTITY
    return a, b


__all__ = [
    "PLATT_ITERATIONS",
    "PLATT_LR",
    "IDENTITY",
    "fit_platt",
    "apply_platt",
    "fit_guarded_platt",
]

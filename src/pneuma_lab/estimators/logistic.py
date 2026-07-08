"""Deterministic pure-stdlib logistic regression with L2 (full batch).

Fixed learning-rate schedule, fixed iteration count, zero-initialized weights,
features standardized with dev-split means/stds. Gradient sums use
``math.fsum`` in a fixed order — repeat training on identical inputs is
byte-identical. No numpy, no randomness, no wall-clock.
"""

from __future__ import annotations

import math
from operator import mul

LEARNING_RATE = 0.3
LR_DECAY = 0.005
N_ITERATIONS = 800
L2_LAMBDA = 0.001


def sigmoid(z: float) -> float:
    """Numerically stable logistic function."""
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def standardizationParams(rows: list) -> tuple[list, list]:
    """Per-feature (means, stds) over ``rows``; zero-variance stds become 1.0."""
    if not rows:
        raise ValueError("no rows to standardize")
    n = len(rows)
    d = len(rows[0])
    means = [math.fsum(col) / n for col in zip(*rows)]
    stds = []
    for j, col in enumerate(zip(*rows)):
        var = math.fsum((v - means[j]) ** 2 for v in col) / n
        std = math.sqrt(var)
        stds.append(std if std > 0.0 else 1.0)
    return means, stds


def standardizeRow(row, means: list, stds: list) -> tuple:
    return tuple((v - m) / s for v, m, s in zip(row, means, stds))


def trainLogistic(
    rows_std: list,
    labels: list,
    learning_rate: float = LEARNING_RATE,
    lr_decay: float = LR_DECAY,
    n_iterations: int = N_ITERATIONS,
    l2_lambda: float = L2_LAMBDA,
) -> tuple[list, float]:
    """Full-batch gradient descent on standardized rows. Returns (weights, bias).

    L2 penalty applies to weights only, never the bias. Deterministic by
    construction: zero init, fixed schedule ``lr_t = lr / (1 + decay * t)``,
    fixed iteration count, fsum reductions in fixed order.
    """
    if not rows_std or len(rows_std) != len(labels):
        raise ValueError("rows/labels empty or mismatched")
    n = len(rows_std)
    d = len(rows_std[0])
    cols = list(zip(*rows_std))
    weights = [0.0] * d
    bias = 0.0
    for t in range(n_iterations):
        lr = learning_rate / (1.0 + lr_decay * t)
        errors = [
            sigmoid(bias + math.fsum(map(mul, weights, row))) - y
            for row, y in zip(rows_std, labels)
        ]
        bias -= lr * (math.fsum(errors) / n)
        for j in range(d):
            grad = math.fsum(map(mul, errors, cols[j])) / n + l2_lambda * weights[j]
            weights[j] -= lr * grad
    return weights, bias


def predictProb(row_std, weights: list, bias: float) -> float:
    return sigmoid(bias + math.fsum(map(mul, weights, row_std)))


__all__ = [
    "LEARNING_RATE",
    "LR_DECAY",
    "N_ITERATIONS",
    "L2_LAMBDA",
    "sigmoid",
    "standardizationParams",
    "standardizeRow",
    "trainLogistic",
    "predictProb",
]

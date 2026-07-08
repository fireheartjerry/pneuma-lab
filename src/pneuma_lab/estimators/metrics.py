"""Pure-stdlib, deterministic evaluation metrics: AUROC, Brier, ECE.

AUROC is rank-based (Mann-Whitney) with midranks for ties. ECE is equal-mass
binning (15 bins by default) over a stable sort of predicted probabilities.
No numpy, no randomness; identical inputs give identical bytes.
"""

from __future__ import annotations

import math

ECE_N_BINS = 15


def auroc(scores: list, labels: list) -> float | None:
    """Mann-Whitney AUROC with tie midranks. None if one class is absent."""
    if len(scores) != len(labels):
        raise ValueError("scores/labels length mismatch")
    n = len(scores)
    n_pos = sum(1 for y in labels if y == 1)
    n_neg = n - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    order = sorted(range(n), key=lambda i: scores[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        midrank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = midrank
        i = j + 1
    rank_sum_pos = math.fsum(ranks[i] for i in range(n) if labels[i] == 1)
    return (rank_sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def brier(probs: list, labels: list) -> float:
    """Mean squared error between predicted probabilities and 0/1 labels."""
    if not probs or len(probs) != len(labels):
        raise ValueError("probs/labels empty or mismatched")
    return math.fsum((p - y) ** 2 for p, y in zip(probs, labels)) / len(probs)


def ece(probs: list, labels: list, n_bins: int = ECE_N_BINS) -> float:
    """Expected calibration error, equal-mass bins over sorted probabilities.

    Bin k covers sorted indices [floor(k*n/B), floor((k+1)*n/B)); empty bins
    contribute zero. Stable sort keeps tie handling deterministic.
    """
    if not probs or len(probs) != len(labels):
        raise ValueError("probs/labels empty or mismatched")
    n = len(probs)
    order = sorted(range(n), key=lambda i: probs[i])
    total = 0.0
    for k in range(n_bins):
        lo = (k * n) // n_bins
        hi = ((k + 1) * n) // n_bins
        if hi <= lo:
            continue
        idx = order[lo:hi]
        mean_p = math.fsum(probs[i] for i in idx) / len(idx)
        mean_y = math.fsum(labels[i] for i in idx) / len(idx)
        total += (len(idx) / n) * abs(mean_p - mean_y)
    return total


__all__ = ["ECE_N_BINS", "auroc", "brier", "ece"]

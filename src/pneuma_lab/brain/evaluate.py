"""Honest generalization estimates: leave-one-repo-out CV and bootstrap CIs.

Deterministic: LORO is a pure function of the data ordering; bootstrap uses a
fixed integer seed via ``random.Random``. No wall-clock, no unseeded randomness.
"""

from __future__ import annotations

import random
from typing import Callable

from pneuma_lab.estimators.metrics import auroc

# (feature_row, label, repo)
Item = tuple[list[float], int, str]
FitFn = Callable[[list[list[float]], list[int]], object]
PredictFn = Callable[[object, list[float]], float]

BOOTSTRAP_SEED = 20260710


def leave_one_repo_out(items: list[Item], fit_fn: FitFn, predict_fn: PredictFn) -> dict:
    """Train on all-but-one repo, predict the held-out repo, pool out-of-fold.

    Returns per-repo AUROC/counts and the pooled out-of-fold (OOF) AUROC, which
    is the honest generalization estimate: no repository is ever in its own
    training fold.
    """
    repos = sorted({repo for _, _, repo in items})
    if len(repos) < 2:
        raise ValueError(
            f"leave_one_repo_out needs at least 2 repos to hold one out; got {len(repos)}"
        )
    per_repo: dict[str, dict] = {}
    oof_scores: list[float] = []
    oof_labels: list[int] = []
    for held in repos:
        train_rows = [row for row, _, repo in items if repo != held]
        train_labels = [label for _, label, repo in items if repo != held]
        test = [(row, label) for row, label, repo in items if repo == held]
        model = fit_fn(train_rows, train_labels)
        scores = [predict_fn(model, row) for row, _ in test]
        labels = [label for _, label in test]
        per_repo[held] = {
            "n": len(test),
            "n_pos": sum(labels),
            "auroc": auroc(scores, labels),
        }
        oof_scores.extend(scores)
        oof_labels.extend(labels)
    return {
        "repos": repos,
        "per_repo": per_repo,
        "oof_auroc": auroc(oof_scores, oof_labels),
        "oof_scores": oof_scores,
        "oof_labels": oof_labels,
    }


def bootstrap_auroc(
    scores: list[float],
    labels: list[int],
    *,
    n_resamples: int = 2000,
    seed: int = BOOTSTRAP_SEED,
    alpha: float = 0.05,
) -> dict:
    """Percentile bootstrap CI for AUROC. Deterministic for a fixed seed."""
    rng = random.Random(seed)
    n = len(scores)
    values: list[float] = []
    for _ in range(n_resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        value = auroc([scores[i] for i in idx], [labels[i] for i in idx])
        if value is not None:
            values.append(value)
    values.sort()
    if not values:
        return {
            "auroc": auroc(scores, labels),
            "lo": None,
            "hi": None,
            "n_effective": 0,
        }
    lo = values[int((alpha / 2) * len(values))]
    hi = values[min(len(values) - 1, int((1 - alpha / 2) * len(values)))]
    return {
        "auroc": auroc(scores, labels),
        "lo": lo,
        "hi": hi,
        "n_effective": len(values),
    }


__all__ = [
    "Item",
    "FitFn",
    "PredictFn",
    "BOOTSTRAP_SEED",
    "leave_one_repo_out",
    "bootstrap_auroc",
]

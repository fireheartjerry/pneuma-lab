from __future__ import annotations

from pneuma_lab.brain import evaluate
from pneuma_lab.brain import model as m


def _fit(rows, labels):
    return m.fit_head([f"f{i}" for i in range(len(rows[0]))], rows, labels)


def _predict(head, row):
    return m.predict_head(head, row)


def _separable_multi_repo():
    # Four repos; within each, class 1 has larger feature values (separable).
    items = []
    for repo in ("a", "b", "c", "d"):
        for k in range(6):
            label = 1 if k >= 3 else 0
            base = 5.0 if label else 0.0
            items.append(([base + 0.1 * k, base - 0.1 * k], label, repo))
    return items


def test_leave_one_repo_out_generalizes_on_separable_data() -> None:
    result = evaluate.leave_one_repo_out(_separable_multi_repo(), _fit, _predict)
    assert result["repos"] == ["a", "b", "c", "d"]
    assert result["oof_auroc"] is not None and result["oof_auroc"] >= 0.9
    for repo in result["repos"]:
        assert result["per_repo"][repo]["n"] == 6


def test_bootstrap_auroc_is_deterministic_and_brackets_point() -> None:
    scores = [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9]
    labels = [0, 0, 0, 0, 1, 1, 1, 1]
    a = evaluate.bootstrap_auroc(scores, labels, n_resamples=500)
    b = evaluate.bootstrap_auroc(scores, labels, n_resamples=500)
    assert a == b  # deterministic for the fixed seed
    assert a["lo"] <= a["auroc"] <= a["hi"]

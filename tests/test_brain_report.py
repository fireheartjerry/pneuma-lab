from __future__ import annotations

from pneuma_lab.brain import report


def test_score_split_reports_auroc_brier_ece() -> None:
    probs = [0.1, 0.2, 0.8, 0.9]
    labels = [0, 0, 1, 1]
    scored = report.score_split(probs, labels)
    assert scored["n"] == 4
    assert scored["n_pos"] == 2
    assert scored["auroc"] == 1.0
    assert 0.0 <= scored["brier"] <= 1.0
    assert scored["ece"] >= 0.0


def test_score_split_handles_single_class() -> None:
    scored = report.score_split([0.3, 0.4], [0, 0])
    assert scored["auroc"] is None


def test_markdown_contains_task_and_metrics() -> None:
    payload = {
        "model_version": "pneuma-brain/0.1.0",
        "split_method": "sha256_repo_mod10_lt3_eval_v1",
        "tasks": {
            "RISK_PREDICTION": {
                "dev": {"n": 8, "n_pos": 4, "auroc": 0.9, "brier": 0.1, "ece": 0.05},
                "eval": {"n": 4, "n_pos": 2, "auroc": 0.75, "brier": 0.2, "ece": 0.1},
                "baseline_e0_auroc": 0.70,
            }
        },
    }
    text = report.markdown(payload)
    assert "RISK_PREDICTION" in text
    assert "0.75" in text
    assert "baseline" in text.lower()

"""Task-conditioned multi-task model: one standardized logistic head per task."""

from __future__ import annotations

import json
import math
from operator import mul

from pneuma_lab.brain import BRAIN_VERSION
from pneuma_lab.estimators import logistic as logit


def fit_head(
    feature_names: list[str], rows: list[list[float]], labels: list[int]
) -> dict:
    """Standardize on the given rows and fit one logistic head."""
    means, stds = logit.standardizationParams(rows)
    rows_std = [logit.standardizeRow(row, means, stds) for row in rows]
    weights, bias = logit.trainLogistic(rows_std, labels)
    return {
        "feature_names": list(feature_names),
        "means": list(means),
        "stds": list(stds),
        "weights": list(weights),
        "bias": bias,
    }


def predict_head(head: dict, row: list[float]) -> float:
    """Predicted probability for one raw (unstandardized) feature row."""
    row_std = logit.standardizeRow(row, head["means"], head["stds"])
    return logit.predictProb(row_std, head["weights"], head["bias"])


def predict_logit(head: dict, row: list[float]) -> float:
    """Pre-sigmoid score (logit) for one raw feature row.

    AUROC is invariant to the sigmoid, so ranking metrics are identical to
    ``predict_head``; this is the correct input domain for Platt calibration.
    """
    row_std = logit.standardizeRow(row, head["means"], head["stds"])
    return head["bias"] + math.fsum(map(mul, head["weights"], row_std))


class MultiTaskModel:
    """A named collection of per-task heads with canonical-JSON serialization."""

    def __init__(self, BRAIN_VERSION_OK: str = BRAIN_VERSION) -> None:
        self.model_version = BRAIN_VERSION_OK
        self._heads: dict[str, dict] = {}

    def add_task(self, task_type: str, head: dict) -> None:
        self._heads[task_type] = head

    def head(self, task_type: str) -> dict:
        return self._heads[task_type]

    def tasks(self) -> list[str]:
        return sorted(self._heads)

    def to_json(self) -> str:
        payload = {
            "model_version": self.model_version,
            "heads": {task: self._heads[task] for task in sorted(self._heads)},
        }
        return json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    @classmethod
    def from_json(cls, text: str) -> "MultiTaskModel":
        payload = json.loads(text)
        model = cls(BRAIN_VERSION_OK=payload["model_version"])
        for task, head in payload["heads"].items():
            model.add_task(task, head)
        return model


__all__ = ["fit_head", "predict_head", "predict_logit", "MultiTaskModel"]

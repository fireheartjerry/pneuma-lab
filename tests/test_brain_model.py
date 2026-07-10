from __future__ import annotations

import json

from pneuma_lab.brain import model as m


def _separable():
    # Two features; class 1 has larger values -> perfectly separable.
    rows = [[0.0, 0.0], [0.1, 0.2], [5.0, 5.0], [5.1, 4.9]]
    labels = [0, 0, 1, 1]
    names = ["f0", "f1"]
    return names, rows, labels


def test_fit_and_predict_learns_direction() -> None:
    names, rows, labels = _separable()
    head = m.fit_head(names, rows, labels)
    lo = m.predict_head(head, [0.0, 0.0])
    hi = m.predict_head(head, [5.0, 5.0])
    assert hi > lo
    assert 0.0 <= lo <= 1.0 and 0.0 <= hi <= 1.0


def test_model_round_trips_through_canonical_json() -> None:
    names, rows, labels = _separable()
    model = m.MultiTaskModel(BRAIN_VERSION_OK="pneuma-brain/0.1.0")
    model.add_task("RISK_PREDICTION", m.fit_head(names, rows, labels))
    text = model.to_json()
    restored = m.MultiTaskModel.from_json(text)
    assert restored.tasks() == ["RISK_PREDICTION"]
    original = m.predict_head(model.head("RISK_PREDICTION"), [5.0, 5.0])
    loaded = m.predict_head(restored.head("RISK_PREDICTION"), [5.0, 5.0])
    assert original == loaded
    # canonical JSON is stable
    assert json.loads(text)["model_version"] == "pneuma-brain/0.1.0"

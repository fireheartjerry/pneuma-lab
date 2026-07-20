"""Per-batch validation persistence: the runner writes what evaluate consumes."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from pneuma_lab.foundation.evaluation import (  # noqa: E402
    EvaluationError,
    aggregate_validation_metrics,
)
from pneuma_lab.foundation.runner import (  # noqa: E402
    VALIDATION_BATCHES_NAME,
    PauseSignal,
    resume_foundation_training,
    run_foundation_training,
)
from test_foundation_runner import (  # noqa: E402
    _run_request,
    _runner_dependencies,
)


def _batches(run_root: Path) -> list:
    return json.loads((run_root / VALIDATION_BATCHES_NAME).read_text(encoding="utf-8"))


def test_completed_run_persists_per_batch_validation_records(
    tmp_path: Path,
) -> None:
    request = _run_request(tmp_path)
    result = run_foundation_training(
        request,
        dependencies=_runner_dependencies(),
    )
    assert result.status == "completed"
    batches = _batches(request.run_root)
    assert isinstance(batches, list)
    assert len(batches) == result.progress.optimizer_step == 1
    batch = batches[0]
    assert set(batch) == {"token_count", "validation_loss", "forecast_loss"}
    assert type(batch["token_count"]) is int
    assert batch["token_count"] == result.progress.tokens_seen
    assert batch["validation_loss"] >= 0.0
    manifest = json.loads(result.run_manifest_path.read_text(encoding="utf-8"))
    assert batch["validation_loss"] == pytest.approx(
        manifest["validation"]["last_loss"]
    )


def test_persisted_batches_satisfy_aggregate_validation_metrics(
    tmp_path: Path,
) -> None:
    request = _run_request(tmp_path)
    result = run_foundation_training(
        request,
        dependencies=_runner_dependencies(record_count=64, tokens_per_call=25),
    )
    batches = _batches(request.run_root)
    assert len(batches) == result.progress.optimizer_step == 2
    metrics = aggregate_validation_metrics(batches)
    assert metrics["batch_count"] == 2
    assert metrics["token_count"] == result.progress.tokens_seen
    assert metrics["validation_loss"] >= 0.0
    assert "forecast_loss" in metrics


def test_zero_window_run_writes_an_empty_honest_array(tmp_path: Path) -> None:
    request = _run_request(tmp_path)
    # Sixteen records can never form one complete 32-microbatch window.
    result = run_foundation_training(
        request,
        dependencies=_runner_dependencies(record_count=16),
    )
    assert result.status == "completed"
    batches = _batches(request.run_root)
    assert batches == []
    with pytest.raises(EvaluationError, match="at least one batch"):
        aggregate_validation_metrics(batches)


def test_resumed_run_extends_batches_to_match_uninterrupted(
    tmp_path: Path,
) -> None:
    uninterrupted_request = _run_request(tmp_path / "a")
    uninterrupted = run_foundation_training(
        uninterrupted_request,
        dependencies=_runner_dependencies(record_count=64, tokens_per_call=25),
    )
    assert uninterrupted.progress.optimizer_step == 2

    interrupted_request = _run_request(tmp_path / "b")
    pause = PauseSignal()
    pause.request()
    paused = run_foundation_training(
        interrupted_request,
        dependencies=_runner_dependencies(record_count=64, tokens_per_call=25),
        pause_signal=pause,
    )
    assert paused.status == "paused"
    assert len(_batches(interrupted_request.run_root)) == 1

    resumed = resume_foundation_training(
        dataclasses.replace(
            interrupted_request,
            checkpoint_path=paused.last_checkpoint,
        ),
        dependencies=_runner_dependencies(record_count=64, tokens_per_call=25),
    )
    assert resumed.status == "completed"
    left = _batches(uninterrupted_request.run_root)
    right = _batches(interrupted_request.run_root)
    assert len(left) == len(right) == 2
    assert [batch["token_count"] for batch in left] == [
        batch["token_count"] for batch in right
    ]
    for one, other in zip(left, right):
        assert one["validation_loss"] == pytest.approx(other["validation_loss"])
        assert one["forecast_loss"] == pytest.approx(other["forecast_loss"])

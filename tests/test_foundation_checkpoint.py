"""Resumable local checkpoint and retention tests."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from pneuma_lab.foundation.checkpoints import (  # noqa: E402
    CheckpointManager,
    CheckpointSchedule,
)


def test_checkpoint_schedule_uses_steps_or_elapsed_minutes() -> None:
    schedule = CheckpointSchedule(every_steps=500, every_seconds=1_800)
    assert schedule.due(step=500, last_step=0, now=10.0, last_time=0.0)
    assert schedule.due(step=2, last_step=0, now=1_800.0, last_time=0.0)
    assert not schedule.due(step=499, last_step=0, now=1_799.0, last_time=0.0)


def test_checkpoint_restores_model_optimizer_progress_and_rng(tmp_path: Path) -> None:
    random.seed(11)
    torch.manual_seed(11)
    model = torch.nn.Linear(3, 1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    loss = model(torch.ones(2, 3)).square().mean()
    loss.backward()
    optimizer.step()

    manager = CheckpointManager(tmp_path)
    checkpoint = manager.save(
        model=model,
        optimizer=optimizer,
        progress={"step": 5, "tokens_seen": 160},
        validation_score=0.6,
    )
    expected_python = random.random()
    expected_torch = torch.rand(1)

    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    random.seed(99)
    torch.manual_seed(99)
    restored = manager.load(checkpoint, model=model, optimizer=optimizer)
    assert restored == {"step": 5, "tokens_seen": 160}
    assert random.random() == expected_python
    assert torch.equal(torch.rand(1), expected_torch)
    assert any(parameter.abs().sum() > 0 for parameter in model.parameters())


def test_checkpoint_retains_last_three_plus_best(tmp_path: Path) -> None:
    model = torch.nn.Linear(1, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    manager = CheckpointManager(tmp_path, keep_last=3)
    for step, score in enumerate((0.1, 0.9, 0.2, 0.3, 0.4), start=1):
        manager.save(
            model=model,
            optimizer=optimizer,
            progress={"step": step, "tokens_seen": step * 10},
            validation_score=score,
        )
    checkpoints = sorted(path.name for path in tmp_path.glob("checkpoint-*.pt"))
    assert checkpoints == [
        "checkpoint-00000002.pt",
        "checkpoint-00000003.pt",
        "checkpoint-00000004.pt",
        "checkpoint-00000005.pt",
    ]

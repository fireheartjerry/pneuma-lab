"""Uninterrupted-versus-resumed fake training must be bit-for-bit equal."""

from __future__ import annotations

import copy
import dataclasses
import random
from dataclasses import dataclass
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from pneuma_lab.foundation.checkpoints import (  # noqa: E402
    CheckpointError,
    CheckpointManager,
    ResumeBindings,
    TrainingProgress,
    ValidationMetric,
)


BINDINGS = ResumeBindings(
    authorization_digest="a" * 64,
    model_revision="15852e8c16360a2fea060d615a32b45270f8a8fc",
    tokenizer_revision="15852e8c16360a2fea060d615a32b45270f8a8fc",
    shard_hashes=("1" * 64, "2" * 64),
    code_commit="c" * 40,
    optimizer_definition="adamw(lr=1e-3,betas=(0.9,0.999),weight_decay=0.01)",
    curriculum_digest="d" * 64,
)


@dataclass(frozen=True)
class FakeTrainingResult:
    trainable_state: dict
    optimizer_state: dict
    scheduler_state: dict
    progress: TrainingProgress
    metrics: tuple[float, ...]
    checkpoint: Path | None


def assert_state_dict_equal(left, right) -> None:
    assert set(left) == set(right)
    for key in left:
        assert torch.equal(left[key], right[key]), f"tensor differs: {key}"


def assert_nested_equal(left, right, *, path: str = "$") -> None:
    assert type(left) is type(right), f"type differs at {path}"
    if isinstance(left, torch.Tensor):
        assert torch.equal(left, right), f"tensor differs at {path}"
        return
    if isinstance(left, dict):
        assert set(left) == set(right), f"keys differ at {path}"
        for key in left:
            assert_nested_equal(left[key], right[key], path=f"{path}.{key}")
        return
    if isinstance(left, (list, tuple)):
        assert len(left) == len(right), f"length differs at {path}"
        for index, (one, two) in enumerate(zip(left, right)):
            assert_nested_equal(one, two, path=f"{path}[{index}]")
        return
    assert left == right, f"value differs at {path}: {left!r} != {right!r}"


def _build(seed: int):
    random.seed(seed)
    torch.manual_seed(seed)
    model = torch.nn.Linear(4, 3)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.5)
    return model, optimizer, scheduler


def run_fake_training(
    *,
    seed: int,
    steps: int,
    checkpoint_root: Path | None = None,
    resume_from: Path | None = None,
) -> FakeTrainingResult:
    """Drive a tiny deterministic model for N fake optimizer steps on CPU."""

    model, optimizer, scheduler = _build(seed)
    metrics: list[float] = []
    progress = TrainingProgress(
        epoch=0,
        sampler_seed=seed,
        dataset_cursor=0,
        microbatch=0,
        optimizer_step=0,
        tokens_seen=0,
        selected_learning_rate=1e-4,
    )
    manager = CheckpointManager(checkpoint_root) if checkpoint_root else None
    if resume_from is not None:
        restored = CheckpointManager(Path(resume_from).parent).load(
            resume_from,
            trainable_modules={"model": model},
            optimizer=optimizer,
            scheduler=scheduler,
            expected_bindings=BINDINGS,
        )
        progress = restored.progress
        metrics = list(restored.telemetry_state["losses"])

    checkpoint: Path | None = None
    for _ in range(progress.optimizer_step, steps):
        inputs = torch.randn(2, 4)
        targets = torch.randn(2, 3) * (1.0 + random.random())
        loss = (model(inputs) - targets).square().mean()
        loss.backward()
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad(set_to_none=True)
        metrics.append(float(loss.detach()))
        progress = dataclasses.replace(
            progress,
            dataset_cursor=progress.dataset_cursor + 2,
            microbatch=progress.microbatch + 1,
            optimizer_step=progress.optimizer_step + 1,
            tokens_seen=progress.tokens_seen + 8,
        )
        if manager is not None and progress.optimizer_step == steps:
            checkpoint = manager.save(
                trainable_modules={"model": model},
                optimizer=optimizer,
                scheduler=scheduler,
                progress=progress,
                bindings=BINDINGS,
                recurrent_state=None,
                active_memory=None,
                telemetry_state={"losses": list(metrics)},
                best_validation=ValidationMetric(
                    metric_name="validation_loss",
                    value=metrics[-1],
                    higher_is_better=False,
                ),
                lineage=("fake-run",),
                termination_reason=None,
                gradient_accumulation=1,
            )
    return FakeTrainingResult(
        trainable_state={
            key: value.detach().clone() for key, value in model.state_dict().items()
        },
        optimizer_state=copy.deepcopy(optimizer.state_dict()),
        scheduler_state=copy.deepcopy(scheduler.state_dict()),
        progress=progress,
        metrics=tuple(metrics),
        checkpoint=checkpoint,
    )


def test_interrupted_and_resumed_fake_training_are_exactly_equal(
    tmp_path: Path,
) -> None:
    uninterrupted = run_fake_training(seed=17, steps=8)
    first_half = run_fake_training(seed=17, steps=4, checkpoint_root=tmp_path)
    resumed = run_fake_training(
        seed=999,
        steps=8,
        checkpoint_root=tmp_path,
        resume_from=first_half.checkpoint,
    )
    assert_state_dict_equal(uninterrupted.trainable_state, resumed.trainable_state)
    assert_nested_equal(uninterrupted.optimizer_state, resumed.optimizer_state)
    assert_nested_equal(uninterrupted.scheduler_state, resumed.scheduler_state)
    assert uninterrupted.progress == resumed.progress
    assert uninterrupted.metrics == resumed.metrics


@pytest.mark.parametrize(
    "field, changed_value",
    (
        ("authorization_digest", "b" * 64),
        ("model_revision", "different-model-revision"),
        ("tokenizer_revision", "different-tokenizer-revision"),
        ("shard_hashes", ("9" * 64,)),
        ("code_commit", "e" * 40),
        ("optimizer_definition", "sgd(lr=0.1)"),
        ("curriculum_digest", "f" * 64),
    ),
)
def test_changed_bindings_reject_resume(
    tmp_path: Path, field: str, changed_value
) -> None:
    first = run_fake_training(seed=3, steps=2, checkpoint_root=tmp_path)
    assert first.checkpoint is not None
    model, optimizer, scheduler = _build(1234)
    changed = dataclasses.replace(BINDINGS, **{field: changed_value})
    with pytest.raises(CheckpointError, match=field):
        CheckpointManager(tmp_path).load(
            first.checkpoint,
            trainable_modules={"model": model},
            optimizer=optimizer,
            scheduler=scheduler,
            expected_bindings=changed,
        )


def test_failed_binding_verification_mutates_nothing(tmp_path: Path) -> None:
    first = run_fake_training(seed=5, steps=2, checkpoint_root=tmp_path)
    assert first.checkpoint is not None
    model, optimizer, scheduler = _build(4321)
    before_model = {
        key: value.detach().clone() for key, value in model.state_dict().items()
    }
    before_scheduler = copy.deepcopy(scheduler.state_dict())
    changed = dataclasses.replace(BINDINGS, code_commit="0" * 40)
    with pytest.raises(CheckpointError):
        CheckpointManager(tmp_path).load(
            first.checkpoint,
            trainable_modules={"model": model},
            optimizer=optimizer,
            scheduler=scheduler,
            expected_bindings=changed,
        )
    assert_state_dict_equal(before_model, model.state_dict())
    assert_nested_equal(before_scheduler, scheduler.state_dict())
    assert not optimizer.state_dict()["state"]

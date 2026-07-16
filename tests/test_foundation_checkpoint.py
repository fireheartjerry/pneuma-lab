"""Resumable local checkpoint, safe-boundary, and retention tests."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from pneuma_lab.foundation.checkpoints import (  # noqa: E402
    CheckpointError,
    CheckpointManager,
    CheckpointSchedule,
    ResumeBindings,
    TrainingProgress,
    ValidationMetric,
    assert_safe_boundary,
)
from pneuma_lab.foundation.core import JunctionAdapter, SharedPneumaCore  # noqa: E402


BINDINGS = ResumeBindings(
    authorization_digest="a" * 64,
    model_revision="15852e8c16360a2fea060d615a32b45270f8a8fc",
    tokenizer_revision="15852e8c16360a2fea060d615a32b45270f8a8fc",
    shard_hashes=("1" * 64,),
    code_commit="c" * 40,
    optimizer_definition="adamw(lr=1e-3)",
    curriculum_digest="d" * 64,
)


def _progress(
    *, optimizer_step: int, microbatch: int | None = None
) -> TrainingProgress:
    return TrainingProgress(
        epoch=0,
        sampler_seed=11,
        dataset_cursor=optimizer_step * 2,
        microbatch=optimizer_step if microbatch is None else microbatch,
        optimizer_step=optimizer_step,
        tokens_seen=optimizer_step * 8,
        selected_learning_rate=1e-4,
    )


def _save(
    manager: CheckpointManager,
    *,
    model,
    optimizer,
    scheduler,
    optimizer_step: int,
    value: float,
    higher_is_better: bool = True,
    telemetry_state=None,
) -> Path:
    return manager.save(
        trainable_modules={"model": model},
        optimizer=optimizer,
        scheduler=scheduler,
        progress=_progress(optimizer_step=optimizer_step),
        bindings=BINDINGS,
        recurrent_state=None,
        active_memory=None,
        telemetry_state=telemetry_state,
        best_validation=ValidationMetric(
            metric_name="validation_score",
            value=value,
            higher_is_better=higher_is_better,
        ),
        lineage=("test-run",),
        termination_reason=None,
        gradient_accumulation=1,
    )


def _linear_setup(seed: int = 11):
    random.seed(seed)
    torch.manual_seed(seed)
    model = torch.nn.Linear(3, 1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.5)
    return model, optimizer, scheduler


def test_checkpoint_schedule_uses_steps_or_elapsed_seconds() -> None:
    schedule = CheckpointSchedule(every_steps=500, every_seconds=1_800)
    assert schedule.due(step=500, last_step=0, now=10.0, last_time=0.0)
    assert schedule.due(step=2, last_step=0, now=1_800.0, last_time=0.0)
    assert not schedule.due(step=499, last_step=0, now=1_799.0, last_time=0.0)


def test_time_triggered_request_waits_for_next_optimizer_boundary() -> None:
    schedule = CheckpointSchedule(
        every_steps=500,
        every_seconds=1_800,
        clock=lambda: 5_000.0,
    )
    pending = dict(
        optimizer_step=10,
        last_saved_step=10,
        last_saved_time=0.0,
        gradient_accumulation=4,
    )
    assert not schedule.should_save(microbatch=43, **pending)
    assert schedule.should_save(microbatch=44, **pending)


def test_step_triggered_request_waits_for_next_optimizer_boundary() -> None:
    schedule = CheckpointSchedule(every_steps=500, every_seconds=1_800)
    assert not schedule.should_save(
        optimizer_step=500,
        last_saved_step=0,
        last_saved_time=0.0,
        microbatch=2_001,
        gradient_accumulation=4,
        now=10.0,
    )
    assert schedule.should_save(
        optimizer_step=500,
        last_saved_step=0,
        last_saved_time=0.0,
        microbatch=2_000,
        gradient_accumulation=4,
        now=10.0,
    )


def test_assert_safe_boundary_rejects_mid_accumulation_and_pending_grads() -> None:
    model = torch.nn.Linear(3, 1)
    with pytest.raises(CheckpointError, match="outside optimizer boundary"):
        assert_safe_boundary(
            model.parameters(),
            microbatch=3,
            gradient_accumulation=2,
        )
    model(torch.ones(2, 3)).square().mean().backward()
    with pytest.raises(CheckpointError, match="cleared gradients"):
        assert_safe_boundary(
            model.parameters(),
            microbatch=4,
            gradient_accumulation=2,
        )


def test_save_rejects_pending_gradients(tmp_path: Path) -> None:
    model, optimizer, scheduler = _linear_setup()
    model(torch.ones(2, 3)).square().mean().backward()
    manager = CheckpointManager(tmp_path)
    with pytest.raises(CheckpointError, match="cleared gradients"):
        _save(
            manager,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            optimizer_step=1,
            value=0.5,
        )
    assert not list(tmp_path.glob("checkpoint-*.pt"))


def test_save_rejects_microbatch_outside_optimizer_boundary(tmp_path: Path) -> None:
    model, optimizer, scheduler = _linear_setup()
    manager = CheckpointManager(tmp_path)
    with pytest.raises(CheckpointError, match="outside optimizer boundary"):
        manager.save(
            trainable_modules={"model": model},
            optimizer=optimizer,
            scheduler=scheduler,
            progress=_progress(optimizer_step=1, microbatch=3),
            bindings=BINDINGS,
            recurrent_state=None,
            active_memory=None,
            telemetry_state=None,
            best_validation=ValidationMetric(
                metric_name="validation_score",
                value=0.5,
                higher_is_better=True,
            ),
            lineage=(),
            termination_reason=None,
            gradient_accumulation=2,
        )


def test_checkpoint_restores_model_optimizer_scheduler_progress_and_rng(
    tmp_path: Path,
) -> None:
    model, optimizer, scheduler = _linear_setup()
    model(torch.ones(2, 3)).square().mean().backward()
    optimizer.step()
    scheduler.step()
    optimizer.zero_grad(set_to_none=True)

    manager = CheckpointManager(tmp_path)
    checkpoint = _save(
        manager,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        optimizer_step=5,
        value=0.6,
        telemetry_state={"losses": [0.5, 0.4]},
    )
    trained_state = {
        key: value.detach().clone() for key, value in model.state_dict().items()
    }
    expected_python = random.random()
    expected_torch = torch.rand(1)
    expected_scheduler = dict(scheduler.state_dict())

    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    fresh_model, fresh_optimizer, fresh_scheduler = _linear_setup(seed=99)
    restored = manager.load(
        checkpoint,
        trainable_modules={"model": fresh_model},
        optimizer=fresh_optimizer,
        scheduler=fresh_scheduler,
        expected_bindings=BINDINGS,
    )
    assert restored.progress == _progress(optimizer_step=5)
    assert restored.bindings == BINDINGS
    assert restored.telemetry_state == {"losses": [0.5, 0.4]}
    assert restored.best_validation == ValidationMetric(
        metric_name="validation_score",
        value=0.6,
        higher_is_better=True,
    )
    assert restored.lineage == ("test-run",)
    assert restored.termination_reason is None
    assert restored.gradient_accumulation == 1
    assert random.random() == expected_python
    assert torch.equal(torch.rand(1), expected_torch)
    assert fresh_scheduler.state_dict() == expected_scheduler
    for key, value in trained_state.items():
        assert torch.equal(value, fresh_model.state_dict()[key]), key
    assert any(parameter.abs().sum() > 0 for parameter in fresh_model.parameters())


def test_save_deduplicates_shared_core_and_strips_prefix(tmp_path: Path) -> None:
    torch.manual_seed(7)
    core = SharedPneumaCore()
    junction = JunctionAdapter(hidden_size=16, shared_core=core, microsteps=4)
    optimizer = torch.optim.AdamW(junction.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.5)
    manager = CheckpointManager(tmp_path)
    checkpoint = manager.save(
        trainable_modules={"shared_core": core, "junction_primary": junction},
        optimizer=optimizer,
        scheduler=scheduler,
        progress=_progress(optimizer_step=1),
        bindings=BINDINGS,
        recurrent_state={"recurrent_state": core.recurrent_state.clone()},
        active_memory=None,
        telemetry_state=None,
        best_validation=ValidationMetric(
            metric_name="validation_score",
            value=0.5,
            higher_is_better=True,
        ),
        lineage=(),
        termination_reason=None,
        gradient_accumulation=1,
    )
    payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
    assert payload["format"] == "pneuma-foundation-checkpoint/0.2.0"
    assert set(payload["modules"]) == {"shared_core", "junction_primary"}
    assert not any(
        key.startswith("shared_core.") for key in payload["modules"]["junction_primary"]
    )
    assert set(payload["modules"]["shared_core"]) == set(core.state_dict())

    fresh_core = SharedPneumaCore()
    fresh_junction = JunctionAdapter(
        hidden_size=16,
        shared_core=fresh_core,
        microsteps=4,
    )
    fresh_optimizer = torch.optim.AdamW(fresh_junction.parameters(), lr=1e-3)
    fresh_scheduler = torch.optim.lr_scheduler.StepLR(
        fresh_optimizer,
        step_size=2,
        gamma=0.5,
    )
    restored = manager.load(
        checkpoint,
        trainable_modules={
            "shared_core": fresh_core,
            "junction_primary": fresh_junction,
        },
        optimizer=fresh_optimizer,
        scheduler=fresh_scheduler,
        expected_bindings=BINDINGS,
    )
    for key, value in core.state_dict().items():
        assert torch.equal(value, fresh_core.state_dict()[key]), key
    for key, value in junction.state_dict().items():
        assert torch.equal(value, fresh_junction.state_dict()[key]), key
    assert torch.equal(
        restored.recurrent_state["recurrent_state"],
        core.recurrent_state,
    )


def test_projection_shell_requires_its_shared_core_once(tmp_path: Path) -> None:
    torch.manual_seed(7)
    core = SharedPneumaCore()
    junction = JunctionAdapter(hidden_size=16, shared_core=core, microsteps=4)
    optimizer = torch.optim.AdamW(junction.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.5)
    with pytest.raises(CheckpointError, match="shared core"):
        CheckpointManager(tmp_path).save(
            trainable_modules={"junction_primary": junction},
            optimizer=optimizer,
            scheduler=scheduler,
            progress=_progress(optimizer_step=1),
            bindings=BINDINGS,
            recurrent_state=None,
            active_memory=None,
            telemetry_state=None,
            best_validation=ValidationMetric(
                metric_name="validation_score",
                value=0.5,
                higher_is_better=True,
            ),
            lineage=(),
            termination_reason=None,
            gradient_accumulation=1,
        )


def test_save_refuses_frozen_base_weights(tmp_path: Path) -> None:
    class FrozenBaseLike(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.embed_tokens = torch.nn.Embedding(8, 4)
            self.lm_head = torch.nn.Linear(4, 8)

    model = FrozenBaseLike()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.5)
    with pytest.raises(CheckpointError, match="frozen"):
        _save(
            CheckpointManager(tmp_path),
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            optimizer_step=1,
            value=0.5,
        )


def test_lora_modules_save_only_permitted_lora_keys(tmp_path: Path) -> None:
    class TinyLora(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.lora_A = torch.nn.Parameter(torch.zeros(2, 2))
            self.lora_B = torch.nn.Parameter(torch.zeros(2, 2))

    class LeakyLora(TinyLora):
        def __init__(self) -> None:
            super().__init__()
            self.base_weight = torch.nn.Parameter(torch.zeros(2, 2))

    manager = CheckpointManager(tmp_path)
    tiny = TinyLora()
    optimizer = torch.optim.AdamW(tiny.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.5)
    checkpoint = manager.save(
        trainable_modules={"lora": tiny},
        optimizer=optimizer,
        scheduler=scheduler,
        progress=_progress(optimizer_step=1),
        bindings=BINDINGS,
        recurrent_state=None,
        active_memory=None,
        telemetry_state=None,
        best_validation=ValidationMetric(
            metric_name="validation_score",
            value=0.5,
            higher_is_better=True,
        ),
        lineage=(),
        termination_reason=None,
        gradient_accumulation=1,
    )
    # a module named lora saves only lora_* keys; anything else refuses
    leaky = LeakyLora()
    leaky_optimizer = torch.optim.AdamW(leaky.parameters(), lr=1e-3)
    leaky_scheduler = torch.optim.lr_scheduler.StepLR(
        leaky_optimizer,
        step_size=2,
        gamma=0.5,
    )
    with pytest.raises(CheckpointError, match="LoRA"):
        manager.save(
            trainable_modules={"lora": leaky},
            optimizer=leaky_optimizer,
            scheduler=leaky_scheduler,
            progress=_progress(optimizer_step=2),
            bindings=BINDINGS,
            recurrent_state=None,
            active_memory=None,
            telemetry_state=None,
            best_validation=ValidationMetric(
                metric_name="validation_score",
                value=0.5,
                higher_is_better=True,
            ),
            lineage=(),
            termination_reason=None,
            gradient_accumulation=1,
        )
    payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
    assert set(payload["modules"]["lora"]) == {"lora_A", "lora_B"}


def test_load_rejects_legacy_format(tmp_path: Path) -> None:
    model, optimizer, scheduler = _linear_setup()
    legacy = tmp_path / "checkpoint-00000001.pt"
    torch.save(
        {
            "format": "pneuma-foundation-checkpoint/0.1.0",
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "progress": {"step": 1},
        },
        legacy,
    )
    with pytest.raises(CheckpointError, match="format"):
        CheckpointManager(tmp_path).load(
            legacy,
            trainable_modules={"model": model},
            optimizer=optimizer,
            scheduler=scheduler,
            expected_bindings=BINDINGS,
        )


def test_checkpoint_retains_last_three_plus_best_higher_is_better(
    tmp_path: Path,
) -> None:
    model, optimizer, scheduler = _linear_setup()
    manager = CheckpointManager(tmp_path, keep_last=3)
    for step, score in enumerate((0.1, 0.9, 0.2, 0.3, 0.4), start=1):
        _save(
            manager,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            optimizer_step=step,
            value=score,
            higher_is_better=True,
        )
    checkpoints = sorted(path.name for path in tmp_path.glob("checkpoint-*.pt"))
    assert checkpoints == [
        "checkpoint-00000002.pt",
        "checkpoint-00000003.pt",
        "checkpoint-00000004.pt",
        "checkpoint-00000005.pt",
    ]


def test_checkpoint_retention_honors_lower_is_better(tmp_path: Path) -> None:
    model, optimizer, scheduler = _linear_setup()
    manager = CheckpointManager(tmp_path, keep_last=3)
    for step, score in enumerate((0.9, 0.1, 0.8, 0.7, 0.6), start=1):
        _save(
            manager,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            optimizer_step=step,
            value=score,
            higher_is_better=False,
        )
    checkpoints = sorted(path.name for path in tmp_path.glob("checkpoint-*.pt"))
    assert checkpoints == [
        "checkpoint-00000002.pt",
        "checkpoint-00000003.pt",
        "checkpoint-00000004.pt",
        "checkpoint-00000005.pt",
    ]


def test_index_is_written_before_pruned_files_are_unlinked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, optimizer, scheduler = _linear_setup()
    manager = CheckpointManager(tmp_path, keep_last=3)
    for step, score in enumerate((0.1, 0.9, 0.2), start=1):
        _save(
            manager,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            optimizer_step=step,
            value=score,
        )

    observed: dict[str, object] = {}
    real_unlink = Path.unlink

    def crashing_unlink(self: Path, *args, **kwargs):
        if self.name.startswith("checkpoint-") and self.suffix == ".pt":
            index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
            observed["indexed_steps"] = sorted(
                record["optimizer_step"] for record in index["checkpoints"]
            )
            observed["pruned"] = self.name
            raise OSError("simulated crash during pruning")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", crashing_unlink)
    with pytest.raises(OSError, match="simulated crash"):
        _save(
            manager,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            optimizer_step=4,
            value=0.3,
        )
    monkeypatch.setattr(Path, "unlink", real_unlink)

    # At the instant of the first unlink the on-disk index already excluded
    # the pruned record, so a crash can never leave ghost index entries.
    assert observed["pruned"] == "checkpoint-00000001.pt"
    assert observed["indexed_steps"] == [2, 3, 4]

    # After the crash: every indexed record resolves to a real file, and the
    # unpruned step-1 file is a harmless unreferenced orphan.
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    for record in index["checkpoints"]:
        assert (tmp_path / record["path"]).exists()
    assert (tmp_path / "checkpoint-00000001.pt").exists()

    # A re-opened manager keeps retention integrity: the surviving best
    # (step 2, score 0.9) is protected on the next save.
    fresh = CheckpointManager(tmp_path, keep_last=3)
    _save(
        fresh,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        optimizer_step=5,
        value=0.4,
    )
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    steps = sorted(record["optimizer_step"] for record in index["checkpoints"])
    assert steps == [2, 3, 4, 5]
    for record in index["checkpoints"]:
        assert (tmp_path / record["path"]).exists()


def test_load_rejects_shape_mismatch_without_mutation(tmp_path: Path) -> None:
    torch.manual_seed(7)
    core = SharedPneumaCore()
    junction = JunctionAdapter(hidden_size=16, shared_core=core, microsteps=4)
    optimizer = torch.optim.AdamW(junction.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.5)
    manager = CheckpointManager(tmp_path)
    checkpoint = manager.save(
        trainable_modules={"shared_core": core, "junction_primary": junction},
        optimizer=optimizer,
        scheduler=scheduler,
        progress=_progress(optimizer_step=1),
        bindings=BINDINGS,
        recurrent_state=None,
        active_memory=None,
        telemetry_state=None,
        best_validation=ValidationMetric(
            metric_name="validation_score",
            value=0.5,
            higher_is_better=True,
        ),
        lineage=(),
        termination_reason=None,
        gradient_accumulation=1,
    )

    wide_core = SharedPneumaCore()
    wide_junction = JunctionAdapter(
        hidden_size=32,
        shared_core=wide_core,
        microsteps=4,
    )
    wide_optimizer = torch.optim.AdamW(wide_junction.parameters(), lr=1e-3)
    wide_scheduler = torch.optim.lr_scheduler.StepLR(
        wide_optimizer,
        step_size=2,
        gamma=0.5,
    )
    before_core = {
        key: value.detach().clone() for key, value in wide_core.state_dict().items()
    }
    before_junction = {
        key: value.detach().clone() for key, value in wide_junction.state_dict().items()
    }
    with pytest.raises(CheckpointError, match="shapes"):
        manager.load(
            checkpoint,
            trainable_modules={
                "shared_core": wide_core,
                "junction_primary": wide_junction,
            },
            optimizer=wide_optimizer,
            scheduler=wide_scheduler,
            expected_bindings=BINDINGS,
        )
    for key, value in before_core.items():
        assert torch.equal(value, wide_core.state_dict()[key]), key
    for key, value in before_junction.items():
        assert torch.equal(value, wide_junction.state_dict()[key]), key
    assert not wide_optimizer.state_dict()["state"]


def test_load_rejects_mismatched_module_names(tmp_path: Path) -> None:
    model, optimizer, scheduler = _linear_setup()
    manager = CheckpointManager(tmp_path)
    checkpoint = _save(
        manager,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        optimizer_step=1,
        value=0.5,
    )
    with pytest.raises(CheckpointError, match="module names"):
        manager.load(
            checkpoint,
            trainable_modules={"other": model},
            optimizer=optimizer,
            scheduler=scheduler,
            expected_bindings=BINDINGS,
        )


def test_load_rejects_mismatched_state_keys(tmp_path: Path) -> None:
    model, optimizer, scheduler = _linear_setup()
    manager = CheckpointManager(tmp_path)
    checkpoint = _save(
        manager,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        optimizer_step=1,
        value=0.5,
    )
    biasless = torch.nn.Linear(3, 1, bias=False)
    with pytest.raises(CheckpointError, match="state keys"):
        manager.load(
            checkpoint,
            trainable_modules={"model": biasless},
            optimizer=optimizer,
            scheduler=scheduler,
            expected_bindings=BINDINGS,
        )


def test_resaving_an_optimizer_step_replaces_its_index_record(
    tmp_path: Path,
) -> None:
    model, optimizer, scheduler = _linear_setup()
    manager = CheckpointManager(tmp_path)
    _save(
        manager,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        optimizer_step=1,
        value=0.1,
    )
    checkpoint = _save(
        manager,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        optimizer_step=1,
        value=0.7,
    )
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert len(index["checkpoints"]) == 1
    record = index["checkpoints"][0]
    assert record["optimizer_step"] == 1
    assert record["value"] == 0.7
    assert checkpoint.exists()


@pytest.mark.parametrize(
    "payload",
    (
        "not json at all {",
        json.dumps({"checkpoints": "wrong-type"}),
        json.dumps(
            {
                "checkpoints": [
                    {"step": 1, "path": "checkpoint.pt", "validation_score": 0.5}
                ]
            }
        ),
    ),
)
def test_malformed_or_legacy_index_rejects_save(tmp_path: Path, payload: str) -> None:
    model, optimizer, scheduler = _linear_setup()
    (tmp_path / "index.json").write_text(payload, encoding="utf-8")
    with pytest.raises(CheckpointError, match="index"):
        _save(
            CheckpointManager(tmp_path),
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            optimizer_step=1,
            value=0.5,
        )


def test_checkpoint_retention_rejects_metric_identity_changes(tmp_path: Path) -> None:
    model, optimizer, scheduler = _linear_setup()
    manager = CheckpointManager(tmp_path, keep_last=3)
    _save(
        manager,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        optimizer_step=1,
        value=0.5,
        higher_is_better=True,
    )
    with pytest.raises(CheckpointError, match="metric"):
        _save(
            manager,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            optimizer_step=2,
            value=0.5,
            higher_is_better=False,
        )

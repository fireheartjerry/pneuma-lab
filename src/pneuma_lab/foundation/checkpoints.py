"""Atomic PyTorch checkpoints with exact optimizer-boundary resume."""

from __future__ import annotations

import dataclasses
import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

try:
    import torch
    from torch import Tensor, nn
except ImportError as exc:  # pragma: no cover - optional dependency boundary
    raise ImportError(
        "pneuma_lab.foundation.checkpoints requires the foundation torch extra"
    ) from exc

from pneuma_lab.foundation.specs import CORE_LIMITS


CHECKPOINT_FORMAT = "pneuma-foundation-checkpoint/0.2.0"

_SHARED_CORE_NAME = "shared_core"
_SHARED_CORE_PREFIX = "shared_core."
_LORA_MODULE_NAME = "lora"
_LORA_MODULE_PREFIX = "lora_"
_LORA_KEY_MARKER = "lora_"
_INDEX_RECORD_FIELDS = frozenset(
    {"optimizer_step", "path", "metric_name", "value", "higher_is_better"}
)
_FROZEN_BASE_KEY_MARKERS = (
    "embed_tokens",
    "lm_head",
    "self_attn",
    "linear_attn",
    "mlp.gate_proj",
    "mlp.up_proj",
    "mlp.down_proj",
    "input_layernorm",
    "post_attention_layernorm",
    "rotary_emb",
)


class CheckpointError(RuntimeError):
    """Raised when a checkpoint save or resume would be unsafe or inexact."""


@dataclass(frozen=True)
class ResumeBindings:
    """Exact identities a checkpoint is bound to; any change rejects resume."""

    authorization_digest: str
    model_revision: str
    tokenizer_revision: str
    shard_hashes: tuple[str, ...]
    code_commit: str
    optimizer_definition: str
    curriculum_digest: str


@dataclass(frozen=True)
class TrainingProgress:
    """Exact position of a run at one safe optimizer boundary."""

    epoch: int
    sampler_seed: int
    dataset_cursor: int
    microbatch: int
    optimizer_step: int
    tokens_seen: int
    selected_learning_rate: float


@dataclass(frozen=True)
class ValidationMetric:
    """A named validation metric with an explicit improvement direction."""

    metric_name: str
    value: float
    higher_is_better: bool


@dataclass(frozen=True)
class RestoredCheckpoint:
    """Structured result of an exact, binding-verified checkpoint restore."""

    path: Path
    progress: TrainingProgress
    bindings: ResumeBindings
    recurrent_state: Any
    active_memory: Any
    telemetry_state: Any
    best_validation: ValidationMetric
    lineage: tuple[str, ...]
    termination_reason: str | None
    gradient_accumulation: int


def assert_safe_boundary(parameters, *, microbatch, gradient_accumulation):
    """Reject any checkpoint request that is not at a clean optimizer boundary."""

    if gradient_accumulation < 1:
        raise CheckpointError("gradient_accumulation must be positive")
    if microbatch % gradient_accumulation != 0:
        raise CheckpointError("checkpoint requested outside optimizer boundary")
    if any(parameter.grad is not None for parameter in parameters):
        raise CheckpointError("safe-boundary checkpoint requires cleared gradients")


@dataclass(frozen=True)
class CheckpointSchedule:
    """Request a save every N optimizer steps or S seconds, whichever first."""

    every_steps: int = 500
    every_seconds: int = 1_800
    clock: Callable[[], float] = time.monotonic

    def due(
        self,
        *,
        step: int,
        last_step: int,
        now: float,
        last_time: float,
    ) -> bool:
        return (
            step - last_step >= self.every_steps
            or now - last_time >= self.every_seconds
        )

    def should_save(
        self,
        *,
        optimizer_step: int,
        last_saved_step: int,
        last_saved_time: float,
        microbatch: int,
        gradient_accumulation: int,
        now: float | None = None,
    ) -> bool:
        """Defer every step- or time-triggered request to an optimizer boundary.

        A request that becomes due mid-accumulation stays pending because the
        cadence condition remains true at the next optimizer boundary.
        """

        if gradient_accumulation < 1:
            raise CheckpointError("gradient_accumulation must be positive")
        if now is None:
            now = self.clock()
        if microbatch % gradient_accumulation != 0:
            return False
        return self.due(
            step=optimizer_step,
            last_step=last_saved_step,
            now=now,
            last_time=last_saved_time,
        )


def _is_lora_name(name: str) -> bool:
    return name == _LORA_MODULE_NAME or name.startswith(_LORA_MODULE_PREFIX)


def _checkpoint_tree(value, *, label: str):
    """Copy tensors to CPU and keep only weights_only-loadable plain data."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Tensor):
        return value.detach().to("cpu").clone()
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, (str, int)):
                raise CheckpointError(f"{label} keys must be str or int")
            result[key] = _checkpoint_tree(item, label=label)
        return result
    if isinstance(value, (list, tuple)):
        return [_checkpoint_tree(item, label=label) for item in value]
    raise CheckpointError(f"{label} must contain only tensors and plain data")


def _trainable_modules_payload(
    trainable_modules: Mapping[str, nn.Module],
) -> dict[str, dict[str, Tensor]]:
    """Deduplicate the shared core, strip its prefix from projection shells,
    keep only permitted LoRA keys, and refuse frozen Qwen base weights."""

    if not isinstance(trainable_modules, Mapping) or not trainable_modules:
        raise CheckpointError("save requires a named mapping of trainable modules")
    payload: dict[str, dict[str, Tensor]] = {}
    total_elements = 0
    shells_using_core: list[str] = []
    for name, module in trainable_modules.items():
        if not isinstance(name, str) or not name:
            raise CheckpointError("trainable module names must be non-empty strings")
        if not isinstance(module, nn.Module):
            raise CheckpointError(f"trainable module must be an nn.Module: {name}")
        state = module.state_dict()
        for key in state:
            if any(marker in key for marker in _FROZEN_BASE_KEY_MARKERS):
                raise CheckpointError(
                    f"refusing to serialize frozen Qwen base weights: {name}.{key}"
                )
        if name == _SHARED_CORE_NAME:
            selected = dict(state)
        elif _is_lora_name(name):
            refused = sorted(key for key in state if _LORA_KEY_MARKER not in key)
            if refused:
                raise CheckpointError(
                    f"LoRA module {name!r} holds keys outside the permitted "
                    f"LoRA set: {refused}"
                )
            selected = dict(state)
        else:
            selected = {
                key: value
                for key, value in state.items()
                if not key.startswith(_SHARED_CORE_PREFIX)
            }
            if len(selected) != len(state):
                shells_using_core.append(name)
        tensors: dict[str, Tensor] = {}
        for key, value in selected.items():
            if not isinstance(value, Tensor):
                raise CheckpointError(
                    f"module state must contain only tensors: {name}.{key}"
                )
            tensors[key] = value.detach().to("cpu").clone()
            total_elements += value.numel()
        payload[name] = tensors
    if shells_using_core and _SHARED_CORE_NAME not in trainable_modules:
        raise CheckpointError(
            "projection shells require their shared core to be saved exactly "
            f"once: {shells_using_core}"
        )
    if total_elements > CORE_LIMITS.max_trainable_parameters:
        raise CheckpointError(
            "checkpoint exceeds the trainable-parameter ceiling; frozen Qwen "
            "base weights are never serialized"
        )
    return payload


def _missing_key_is_acceptable(name: str, key: str) -> bool:
    """Only projection-shell shared-core keys may be restored elsewhere."""

    if name == _SHARED_CORE_NAME or _is_lora_name(name):
        return False
    return key.startswith(_SHARED_CORE_PREFIX)


def _expected_state_keys(name: str, module: nn.Module) -> set[str]:
    state_keys = set(module.state_dict())
    if name == _SHARED_CORE_NAME:
        return state_keys
    if _is_lora_name(name):
        return {key for key in state_keys if _LORA_KEY_MARKER in key}
    return {key for key in state_keys if not key.startswith(_SHARED_CORE_PREFIX)}


def _bindings_payload(bindings: ResumeBindings) -> dict:
    payload = dataclasses.asdict(bindings)
    payload["shard_hashes"] = list(bindings.shard_hashes)
    return payload


def _bindings_from_payload(payload: Mapping) -> ResumeBindings:
    field_names = {field.name for field in dataclasses.fields(ResumeBindings)}
    if not isinstance(payload, Mapping) or set(payload) != field_names:
        raise CheckpointError("checkpoint resume bindings are malformed")
    values = dict(payload)
    values["shard_hashes"] = tuple(values["shard_hashes"])
    return ResumeBindings(**values)


class CheckpointManager:
    def __init__(self, root: Path, *, keep_last: int = 3) -> None:
        if keep_last < 1:
            raise ValueError("keep_last must be positive")
        self.root = Path(root)
        self.keep_last = keep_last
        self.index_path = self.root / "index.json"

    def _index(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        try:
            value = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CheckpointError("checkpoint index is unreadable") from exc
        records = value.get("checkpoints") if isinstance(value, dict) else None
        if not isinstance(records, list):
            raise CheckpointError("checkpoint index is malformed")
        for record in records:
            if (
                not isinstance(record, dict)
                or set(record) != _INDEX_RECORD_FIELDS
                or not isinstance(record["optimizer_step"], int)
                or not isinstance(record["path"], str)
                or not isinstance(record["metric_name"], str)
                or isinstance(record["value"], bool)
                or not isinstance(record["value"], (int, float))
                or not isinstance(record["higher_is_better"], bool)
            ):
                raise CheckpointError("checkpoint index is malformed")
        return list(records)

    def _write_index(self, records: list[dict]) -> None:
        payload = (json.dumps({"checkpoints": records}, indent=4) + "\n").encode(
            "utf-8"
        )
        temporary = self.index_path.with_suffix(".json.tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, self.index_path)

    @staticmethod
    def _rng_state() -> dict:
        state = {
            "python": random.getstate(),
            "torch_cpu": torch.get_rng_state(),
        }
        if torch.cuda.is_available():
            state["torch_cuda"] = torch.cuda.get_rng_state_all()
        return state

    @staticmethod
    def _restore_rng(state: Mapping) -> None:
        python_state = state["python"]
        random.setstate(
            tuple(
                tuple(part) if isinstance(part, list) else part for part in python_state
            )
        )
        torch.set_rng_state(state["torch_cpu"])
        if "torch_cuda" in state and torch.cuda.is_available():
            torch.cuda.set_rng_state_all(state["torch_cuda"])

    @staticmethod
    def _validate_metric_identity(
        records: Iterable[Mapping],
        metric: ValidationMetric,
    ) -> None:
        for record in records:
            if (
                record["metric_name"] != metric.metric_name
                or record["higher_is_better"] != metric.higher_is_better
            ):
                raise CheckpointError(
                    "validation metric identity changed between checkpoints"
                )

    def save(
        self,
        *,
        trainable_modules: Mapping[str, nn.Module],
        optimizer,
        scheduler,
        progress: TrainingProgress,
        bindings: ResumeBindings,
        recurrent_state=None,
        active_memory=None,
        telemetry_state=None,
        best_validation: ValidationMetric,
        lineage: tuple[str, ...] = (),
        termination_reason: str | None = None,
        gradient_accumulation: int,
    ) -> Path:
        """Write one exact safe-boundary checkpoint and apply retention."""

        if not isinstance(progress, TrainingProgress):
            raise CheckpointError("progress must be a TrainingProgress")
        if not isinstance(bindings, ResumeBindings):
            raise CheckpointError("bindings must be a ResumeBindings")
        if not isinstance(best_validation, ValidationMetric):
            raise CheckpointError("best_validation must be a ValidationMetric")
        if termination_reason is not None and not isinstance(termination_reason, str):
            raise CheckpointError("termination_reason must be a string or None")
        if any(not isinstance(entry, str) for entry in lineage):
            raise CheckpointError("lineage entries must be strings")
        parameters = [
            parameter
            for module in trainable_modules.values()
            for parameter in module.parameters()
        ]
        assert_safe_boundary(
            parameters,
            microbatch=progress.microbatch,
            gradient_accumulation=gradient_accumulation,
        )
        records = self._index()
        self._validate_metric_identity(records, best_validation)
        modules_payload = _trainable_modules_payload(trainable_modules)

        step = progress.optimizer_step
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"checkpoint-{step:08d}.pt"
        temporary = path.with_suffix(".pt.tmp")
        torch.save(
            {
                "format": CHECKPOINT_FORMAT,
                "modules": modules_payload,
                "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(),
                "progress": dataclasses.asdict(progress),
                "bindings": _bindings_payload(bindings),
                "rng": self._rng_state(),
                "recurrent_state": _checkpoint_tree(
                    recurrent_state, label="recurrent_state"
                ),
                "active_memory": _checkpoint_tree(active_memory, label="active_memory"),
                "telemetry_state": _checkpoint_tree(
                    telemetry_state, label="telemetry_state"
                ),
                "best_validation": dataclasses.asdict(best_validation),
                "lineage": [str(entry) for entry in lineage],
                "termination_reason": termination_reason,
                "gradient_accumulation": int(gradient_accumulation),
            },
            temporary,
        )
        os.replace(temporary, path)

        records = [record for record in records if record["optimizer_step"] != step]
        records.append(
            {
                "optimizer_step": step,
                "path": path.name,
                "metric_name": best_validation.metric_name,
                "value": float(best_validation.value),
                "higher_is_better": bool(best_validation.higher_is_better),
            }
        )
        records.sort(key=lambda item: item["optimizer_step"])
        if best_validation.higher_is_better:
            best = max(
                records,
                key=lambda item: (item["value"], -item["optimizer_step"]),
            )
        else:
            best = min(
                records,
                key=lambda item: (item["value"], item["optimizer_step"]),
            )
        keep_steps = {record["optimizer_step"] for record in records[-self.keep_last :]}
        keep_steps.add(best["optimizer_step"])
        retained = [
            record for record in records if record["optimizer_step"] in keep_steps
        ]
        # Publish the pruned index BEFORE unlinking files: a crash inside the
        # pruning loop then leaves only unreferenced orphan .pt files, never an
        # index that references deleted checkpoints.
        self._write_index(retained)
        for record in records:
            if record["optimizer_step"] not in keep_steps:
                candidate = self.root / record["path"]
                if candidate.exists():
                    candidate.unlink()
        return path

    def load(
        self,
        path: Path,
        *,
        trainable_modules: Mapping[str, nn.Module],
        optimizer,
        scheduler,
        expected_bindings: ResumeBindings,
    ) -> RestoredCheckpoint:
        """Verify bindings, then restore modules, optimizer, scheduler, RNG."""

        if not isinstance(expected_bindings, ResumeBindings):
            raise CheckpointError("expected_bindings must be a ResumeBindings")
        path = Path(path)
        payload = torch.load(path, map_location="cpu", weights_only=True)
        if (
            not isinstance(payload, Mapping)
            or payload.get("format") != CHECKPOINT_FORMAT
        ):
            raise CheckpointError(
                f"unsupported checkpoint format: expected {CHECKPOINT_FORMAT}"
            )
        saved_bindings = _bindings_from_payload(payload["bindings"])
        if saved_bindings != expected_bindings:
            changed = sorted(
                field.name
                for field in dataclasses.fields(ResumeBindings)
                if getattr(saved_bindings, field.name)
                != getattr(expected_bindings, field.name)
            )
            raise CheckpointError("resume bindings changed: " + ", ".join(changed))
        modules_payload = payload["modules"]
        if set(modules_payload) != set(trainable_modules):
            raise CheckpointError("trainable module names do not match the checkpoint")
        plans = []
        for name, module in trainable_modules.items():
            expected_keys = _expected_state_keys(name, module)
            saved_state = modules_payload[name]
            if set(saved_state) != expected_keys:
                raise CheckpointError(
                    f"module state keys do not match the checkpoint: {name}"
                )
            live_state = module.state_dict()
            for key, tensor in saved_state.items():
                if (
                    not isinstance(tensor, Tensor)
                    or tensor.shape != live_state[key].shape
                ):
                    raise CheckpointError(
                        f"module tensor shapes do not match the checkpoint: {name}.{key}"
                    )
            plans.append((name, module, saved_state))

        # All checks passed; only now mutate the live objects. Optimizer
        # tensors are moved back onto their parameter devices by torch's
        # optimizer state casting during load_state_dict.
        for name, module, saved_state in plans:
            result = module.load_state_dict(saved_state, strict=False)
            unrestored = [
                key
                for key in result.missing_keys
                if not _missing_key_is_acceptable(name, key)
            ]
            if result.unexpected_keys or unrestored:
                raise CheckpointError(f"module state restore was incomplete: {name}")
        optimizer.load_state_dict(payload["optimizer"])
        scheduler.load_state_dict(payload["scheduler"])
        self._restore_rng(payload["rng"])
        return RestoredCheckpoint(
            path=path,
            progress=TrainingProgress(**payload["progress"]),
            bindings=saved_bindings,
            recurrent_state=payload["recurrent_state"],
            active_memory=payload["active_memory"],
            telemetry_state=payload["telemetry_state"],
            best_validation=ValidationMetric(**payload["best_validation"]),
            lineage=tuple(payload["lineage"]),
            termination_reason=payload["termination_reason"],
            gradient_accumulation=int(payload["gradient_accumulation"]),
        )

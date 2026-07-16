"""Integrated preflight, train, and resume runner for one authorized stage.

The runner is a thin, dependency-injected orchestration surface: every
external effect (authorization verification, snapshot verification, the
environment probe, git inspection, tokenizer/model loading, junction
installation, optimizer/scheduler construction, telemetry, and the clock)
arrives through :class:`RunnerDependencies`. Preflight performs every
fail-closed check without allocating a model; the safe-boundary loop trains
in exact 32-microbatch windows, samples telemetry, consults the resource
guard, and checkpoints only at clean optimizer boundaries. Every termination
writes a safe checkpoint and a schema-valid run manifest with its reason.

Torch-dependent modules (checkpoints, dataset, optimizer, authorization) are
imported lazily so importing this module never requires the foundation extra.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import math
import signal
import subprocess
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pneuma_lab.foundation.doctor import doctor_report
from pneuma_lab.foundation.resources import (
    ACTION_CONTINUE,
    ACTION_FAIL,
    ResourceGuard,
)
from pneuma_lab.foundation.run_manifest import RunManifestWriter
from pneuma_lab.foundation.specs import CORE_LIMITS
from pneuma_lab.foundation.telemetry import TelemetryError
from pneuma_lab.foundation.training import (
    DEFAULT_TRAINING_CONFIG,
    FoundationRunError,
    FoundationTrainingRequest,
    configure_quantized_training_model,
    validate_training_request,
)

if TYPE_CHECKING:  # pragma: no cover - typing-only imports
    from pneuma_lab.foundation.authorization import (
        VerifiedFoundationAuthorization,
    )
    from pneuma_lab.foundation.checkpoints import (
        RestoredCheckpoint,
        TrainingProgress,
    )
    from pneuma_lab.foundation.model_cache import CachedSnapshot


_COMPLETED = "completed"
_VALIDATION_METRIC_NAME = "language_loss"
# Recorded when no validation loss has been observed yet. The value is a
# finite lower-is-better sentinel so the checkpoint index stays strict JSON
# (never ``Infinity``) and any real loss immediately replaces it as best.
_UNMEASURED_VALIDATION_LOSS = 1.0e30
# Collation runs in-process because sealed EffectiveTrainingRecords refuse to
# cross process boundaries; the manifest records this effective worker count.
_EFFECTIVE_DATA_LOADER_WORKERS = 0


@dataclass(frozen=True)
class FoundationRunRequest:
    repo_root: Path
    authorization_path: Path
    registry_path: Path
    suite_path: Path
    cache_root: Path
    run_root: Path
    stage: str
    learning_rate: float
    execution_profile: str = "local"
    seed: int = 20260713
    checkpoint_path: Path | None = None


@dataclass(frozen=True)
class FoundationPreflightResult:
    ready: bool
    authorization: "VerifiedFoundationAuthorization"
    cache: "CachedSnapshot"
    environment: Mapping


@dataclass(frozen=True)
class FoundationRunResult:
    run_id: str
    status: str
    progress: "TrainingProgress"
    last_checkpoint: Path | None
    run_manifest_path: Path


@dataclass(frozen=True)
class RunnerDependencies:
    verify_authorization: Callable
    verify_cache: Callable
    environment_probe: Callable
    clean_commit: Callable
    tokenizer_loader: Callable
    model_loader: Callable
    junction_installer: Callable
    optimizer_builder: Callable
    scheduler_builder: Callable
    telemetry_factory: Callable
    clock: Callable


class PauseSignal:
    """A pause request set by a signal handler and consumed at a boundary."""

    __slots__ = ("requested",)

    def __init__(self) -> None:
        self.requested = False

    def request(self, *_arguments) -> None:
        self.requested = True


@contextlib.contextmanager
def pause_signals(pause_signal: PauseSignal) -> Iterator[PauseSignal]:
    """Route SIGINT/SIGTERM into a pause flag; never checkpoint in a handler.

    The handler only records the request; the training loop consumes it at
    the next safe optimizer boundary, so an interrupt can never write a
    checkpoint mid-accumulation. Previous handlers are always restored.
    """

    def handler(_signum, _frame) -> None:
        pause_signal.request()

    previous: list[tuple[int, Any]] = []
    for name in ("SIGINT", "SIGTERM"):
        signum = getattr(signal, name, None)
        if signum is None:
            continue
        try:
            previous.append((signum, signal.signal(signum, handler)))
        except (OSError, RuntimeError, ValueError):
            # Signal handlers are only available on the main thread.
            continue
    try:
        yield pause_signal
    finally:
        for signum, previous_handler in previous:
            try:
                signal.signal(signum, previous_handler)
            except (OSError, RuntimeError, ValueError):  # pragma: no cover
                continue


def assert_clean_commit(repo_root: Path, *, expected: str) -> None:
    """Require HEAD to be exactly the authorized commit with no local edits."""

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise FoundationRunError(f"cannot inspect the git checkout: {exc}") from exc
    if head != expected or status:
        raise FoundationRunError("code commit is dirty or differs from authorization")


def unique_trainable_parameters(installed) -> list:
    """Collect each trainable parameter exactly once from the installed model."""

    model = getattr(installed, "model", installed)
    seen: set[int] = set()
    parameters = []
    for parameter in model.parameters():
        if parameter.requires_grad and id(parameter) not in seen:
            seen.add(id(parameter))
            parameters.append(parameter)
    if not parameters:
        raise FoundationRunError("no trainable parameters were installed")
    return parameters


def default_runner_dependencies() -> RunnerDependencies:
    import torch
    from transformers import AutoTokenizer, get_cosine_schedule_with_warmup

    from pneuma_lab.foundation.authorization import (
        verify_foundation_authorization,
    )
    from pneuma_lab.foundation.doctor import live_probe
    from pneuma_lab.foundation.integration import install_junctions
    from pneuma_lab.foundation.model_cache import verify_pinned_snapshot
    from pneuma_lab.foundation.runtime import load_local_qwen
    from pneuma_lab.foundation.telemetry import LiveResourceSampler

    def verify_authorization(path, *, repo_root, registry_path, suite_path):
        # The committed verifier binds the full suite and registry through
        # the authorization manifest itself; suite_path is accepted for the
        # runner contract and intentionally unused here.
        del suite_path
        return verify_foundation_authorization(
            path,
            repo_root=repo_root,
            registry_path=registry_path,
        )

    def model_loader(model_key, *, allow_download, vision, snapshot_path):
        return load_local_qwen(
            model_key,
            allow_download=allow_download,
            vision=vision,
            snapshot_path=snapshot_path,
        )

    def scheduler_builder(optimizer, token_ceiling):
        total_steps = max(
            1,
            token_ceiling
            // (
                DEFAULT_TRAINING_CONFIG.sequence_length
                * DEFAULT_TRAINING_CONFIG.gradient_accumulation
            ),
        )
        warmup_steps = max(1, int(total_steps * 0.03))
        return get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    return RunnerDependencies(
        verify_authorization=verify_authorization,
        verify_cache=verify_pinned_snapshot,
        environment_probe=live_probe,
        clean_commit=assert_clean_commit,
        tokenizer_loader=AutoTokenizer.from_pretrained,
        model_loader=model_loader,
        junction_installer=install_junctions,
        optimizer_builder=lambda parameters, lr: torch.optim.AdamW(parameters, lr=lr),
        scheduler_builder=scheduler_builder,
        telemetry_factory=LiveResourceSampler,
        clock=time.monotonic,
    )


def _scope_learning_rates(scope: Mapping) -> tuple:
    rates = scope.get("learning_rates")
    if not isinstance(rates, (list, tuple)) or not rates:
        raise FoundationRunError("authorized learning rates are missing from the scope")
    return tuple(rates)


def preflight_foundation_run(
    request: FoundationRunRequest,
    *,
    dependencies: RunnerDependencies | None = None,
) -> FoundationPreflightResult:
    """Run every fail-closed gate in exact order without any allocation."""

    dependencies = dependencies or default_runner_dependencies()
    authorization = dependencies.verify_authorization(
        request.authorization_path,
        repo_root=request.repo_root,
        registry_path=request.registry_path,
        suite_path=request.suite_path,
    )
    scope = authorization.manifest["scope"]
    if scope.get("execution_profile", "local") != request.execution_profile:
        raise FoundationRunError("execution profile differs from the authorized scope")
    if scope.get("stage") != request.stage:
        raise FoundationRunError("stage differs from the authorized scope")
    validate_training_request(
        FoundationTrainingRequest(
            model_key=authorization.model_key,
            token_ceiling=authorization.token_ceiling,
        )
    )
    dependencies.clean_commit(
        request.repo_root,
        expected=scope["code_commit"],
    )
    cache = dependencies.verify_cache(
        authorization.model_key,
        cache_root=request.cache_root,
    )
    environment = doctor_report(
        dependencies.environment_probe(),
        profile=request.execution_profile,
    )
    if not environment["ready"]:
        raise FoundationRunError(f"environment is blocked: {environment['blockers']}")
    if request.learning_rate not in _scope_learning_rates(scope):
        raise FoundationRunError("learning rate is outside the approved scope")
    return FoundationPreflightResult(True, authorization, cache, environment)


def _set_deterministic_seeds(seed: int) -> None:
    import random

    random.seed(seed)
    try:
        import torch
    except ImportError:  # pragma: no cover - optional dependency boundary
        return
    torch.manual_seed(seed)
    if torch.cuda.is_available():  # pragma: no cover - GPU-only
        torch.cuda.manual_seed_all(seed)


def _force_offline() -> None:
    import os

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


def _is_quantized(model) -> bool:
    return bool(
        getattr(model, "is_loaded_in_4bit", False)
        or getattr(model, "is_quantized", False)
    )


def _cast_trainables_to_bf16(configured, installed) -> None:
    """Cast the shared core and projection shells to BF16 on quantized bases."""

    if not _is_quantized(configured):
        return
    import torch

    installed.shared_core.to(dtype=torch.bfloat16)
    for junction in installed.junctions:
        junction.to(dtype=torch.bfloat16)


def _assert_trainable_ceiling(parameters) -> None:
    total = sum(parameter.numel() for parameter in parameters)
    if total > CORE_LIMITS.max_trainable_parameters:
        raise FoundationRunError(
            f"{total} trainable parameters exceed the "
            f"{CORE_LIMITS.max_trainable_parameters} ceiling"
        )


def _allocate_training_stack(
    request: FoundationRunRequest,
    preflight: FoundationPreflightResult,
    dependencies: RunnerDependencies,
):
    """Guarded allocation order shared by fresh training and resume."""

    _set_deterministic_seeds(request.seed)
    _force_offline()
    tokenizer = dependencies.tokenizer_loader(
        preflight.cache.snapshot_path,
        local_files_only=True,
    )
    runtime = dependencies.model_loader(
        preflight.authorization.model_key,
        allow_download=False,
        vision=False,
        snapshot_path=preflight.cache.snapshot_path,
    )
    configured = configure_quantized_training_model(runtime.model)
    installed = dependencies.junction_installer(
        configured,
        runtime.architecture_plan,
    )
    _cast_trainables_to_bf16(configured, installed)
    parameters = unique_trainable_parameters(installed)
    _assert_trainable_ceiling(parameters)
    optimizer = dependencies.optimizer_builder(
        parameters,
        lr=request.learning_rate,
    )
    scheduler = dependencies.scheduler_builder(
        optimizer,
        preflight.authorization.token_ceiling,
    )
    return tokenizer, runtime, installed, optimizer, scheduler


def run_foundation_training(
    request: FoundationRunRequest,
    *,
    dependencies: RunnerDependencies | None = None,
    pause_signal: PauseSignal | None = None,
) -> FoundationRunResult:
    """Preflight first, then allocate in guarded order and train safely."""

    dependencies = dependencies or default_runner_dependencies()
    preflight = preflight_foundation_run(request, dependencies=dependencies)
    tokenizer, runtime, installed, optimizer, scheduler = _allocate_training_stack(
        request,
        preflight,
        dependencies,
    )
    active_signal = pause_signal if pause_signal is not None else PauseSignal()
    with pause_signals(active_signal):
        return execute_safe_boundary_loop(
            request=request,
            preflight=preflight,
            tokenizer=tokenizer,
            runtime=runtime,
            installed=installed,
            optimizer=optimizer,
            scheduler=scheduler,
            dependencies=dependencies,
            pause_signal=active_signal,
        )


def resume_foundation_training(
    request: FoundationRunRequest,
    *,
    dependencies: RunnerDependencies | None = None,
    pause_signal: PauseSignal | None = None,
) -> FoundationRunResult:
    """Re-run preflight, verify every resume binding, and continue exactly."""

    if request.checkpoint_path is None:
        raise FoundationRunError("resume requires an exact checkpoint path")
    dependencies = dependencies or default_runner_dependencies()
    preflight = preflight_foundation_run(request, dependencies=dependencies)
    tokenizer, runtime, installed, optimizer, scheduler = _allocate_training_stack(
        request,
        preflight,
        dependencies,
    )
    from pneuma_lab.foundation.checkpoints import CheckpointManager

    restored = CheckpointManager(_checkpoint_root(request)).load(
        request.checkpoint_path,
        trainable_modules=_trainable_modules(installed),
        optimizer=optimizer,
        scheduler=scheduler,
        expected_bindings=_resume_bindings(request, preflight),
    )
    accumulation = DEFAULT_TRAINING_CONFIG.gradient_accumulation
    if restored.gradient_accumulation != accumulation:
        raise FoundationRunError(
            "checkpoint gradient accumulation differs from the local profile"
        )
    if restored.progress.microbatch % accumulation != 0:
        raise FoundationRunError("checkpoint is not at a safe optimizer boundary")
    if restored.progress.selected_learning_rate != request.learning_rate:
        raise FoundationRunError("learning rate differs from the checkpointed run")
    active_signal = pause_signal if pause_signal is not None else PauseSignal()
    with pause_signals(active_signal):
        return execute_safe_boundary_loop(
            request=request,
            preflight=preflight,
            tokenizer=tokenizer,
            runtime=runtime,
            installed=installed,
            optimizer=optimizer,
            scheduler=scheduler,
            dependencies=dependencies,
            restored=restored,
            pause_signal=active_signal,
            mode="resume",
        )


def _checkpoint_root(request: FoundationRunRequest) -> Path:
    return Path(request.run_root) / "checkpoints"


def _trainable_modules(installed) -> dict:
    modules = {"shared_core": installed.shared_core}
    for index, junction in enumerate(installed.junctions):
        modules[f"junction_{index}"] = junction
    return modules


def _plain_json(value):
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json(item) for item in value]
    return value


def _canonical_digest(value) -> str:
    payload = json.dumps(
        _plain_json(value),
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _artifact_digests(scope: Mapping) -> dict[str, str]:
    artifacts = scope.get("artifacts")
    if not isinstance(artifacts, Mapping) or not artifacts:
        raise FoundationRunError("authorized artifact bindings are missing")
    digests = {}
    for name, binding in artifacts.items():
        digest = binding.get("sha256") if isinstance(binding, Mapping) else None
        if not isinstance(digest, str) or not digest:
            raise FoundationRunError(f"authorized artifact digest is missing: {name}")
        digests[str(name)] = digest
    return digests


def _resume_bindings(
    request: FoundationRunRequest,
    preflight: FoundationPreflightResult,
):
    from pneuma_lab.foundation.checkpoints import ResumeBindings

    authorization = preflight.authorization
    scope = authorization.manifest["scope"]
    artifacts = _artifact_digests(scope)
    shard_hashes = tuple(
        digest
        for name, digest in sorted(artifacts.items())
        if name in {"shard", "shard_manifest"}
    )
    if not shard_hashes:
        raise FoundationRunError("authorized shard digests are missing")
    optimizer_definition = (
        f"adamw(lr={request.learning_rate!r})"
        f"+cosine(token_ceiling={authorization.token_ceiling})"
    )
    curriculum_digest = _canonical_digest(
        {
            "stage": scope["stage"],
            "token_ceiling": authorization.token_ceiling,
            "lane_weights": authorization.authorized_lane_weights,
        }
    )
    return ResumeBindings(
        authorization_digest=authorization.scope_digest,
        model_revision=scope["model"]["revision"],
        tokenizer_revision=scope["model"]["tokenizer_revision"],
        shard_hashes=shard_hashes,
        code_commit=scope["code_commit"],
        optimizer_definition=optimizer_definition,
        curriculum_digest=curriculum_digest,
    )


def _run_id(preflight: FoundationPreflightResult) -> str:
    scope = preflight.authorization.manifest["scope"]
    return f"foundation-{scope['stage']}-{preflight.authorization.scope_digest[:16]}"


def _null_telemetry() -> dict:
    return {
        "peak_process_vram_gb": None,
        "peak_reserved_vram_gb": None,
        "peak_global_vram_used_gb": None,
        "peak_process_ram_gb": None,
        "peak_system_ram_gb": None,
        "peak_gpu_temp_c": None,
        "peak_power_watts": None,
        "thermal_throttle_intervals": 0,
    }


def _build_run_manifest(
    *,
    request: FoundationRunRequest,
    preflight: FoundationPreflightResult,
    run_id: str,
    mode: str,
    status: str,
    termination_reason: str | None,
    progress,
    telemetry_samples,
    wall_time_seconds: float,
    run_tokens: int,
    best_loss: float | None,
    last_loss: float | None,
    last_checkpoint: Path | None,
    lineage: tuple[str, ...],
) -> dict:
    from pneuma_lab.foundation.telemetry import aggregate_telemetry

    authorization = preflight.authorization
    scope = authorization.manifest["scope"]
    config = DEFAULT_TRAINING_CONFIG
    samples = tuple(telemetry_samples)
    telemetry = aggregate_telemetry(samples) if samples else _null_telemetry()
    tokens_per_second = (
        run_tokens / wall_time_seconds
        if wall_time_seconds > 0 and run_tokens > 0
        else None
    )
    budget = scope.get("budget", {})
    return {
        "manifest_kind": "pneuma_foundation_run",
        "manifest_schema_version": "0.2.0",
        "run_id": run_id,
        "status": status,
        "mode": mode,
        "model": {
            key: scope["model"][key]
            for key in (
                "key",
                "model_id",
                "revision",
                "tokenizer_id",
                "tokenizer_revision",
            )
        },
        "bindings": {
            "authorization_sha256": _canonical_digest(authorization.manifest),
            "scope_digest": authorization.scope_digest,
            "code_commit": scope["code_commit"],
            "shard_sha256": _artifact_digests(scope)["shard"],
            "receipts": _artifact_digests(scope),
        },
        "training": {
            "token_ceiling": authorization.token_ceiling,
            "sequence_length": config.sequence_length,
            "microbatch_size": config.microbatch_size,
            "gradient_accumulation": config.gradient_accumulation,
            "data_loader_workers": _EFFECTIVE_DATA_LOADER_WORKERS,
            "quantization": "nf4_double_quant",
            "seed": progress.sampler_seed,
            "learning_rate": request.learning_rate,
        },
        "curriculum": {
            "stage": scope["stage"],
            "lane_weights": _plain_json(authorization.authorized_lane_weights),
        },
        "limits": {
            "max_vram_gb": config.max_vram_gb,
            "max_ram_gb": config.max_ram_gb,
            "max_gpu_temp_c": config.thermal_pause_c,
        },
        "progress": {
            "tokens_seen": progress.tokens_seen,
            "optimizer_steps": progress.optimizer_step,
            "microbatches_seen": progress.microbatch,
            "wall_time_seconds": wall_time_seconds,
            "tokens_per_second": tokens_per_second,
        },
        "latency": {
            "base_p50_ms": None,
            "base_p95_ms": None,
            "core_p50_ms": None,
            "core_p95_ms": None,
        },
        "telemetry": telemetry,
        "validation": {"best_loss": best_loss, "last_loss": last_loss},
        "checkpoints": {
            "last_path": str(last_checkpoint) if last_checkpoint else None,
            "lineage": list(lineage),
        },
        "termination_reason": termination_reason,
        "reports": {"index_path": None, "section_paths": {}},
        "budget": {
            "paid_compute_usd": budget.get("paid_compute_usd", 0),
            "cloud_jobs_used": budget.get("cloud_jobs_used", 0),
        },
    }


def execute_safe_boundary_loop(
    *,
    request: FoundationRunRequest,
    preflight: FoundationPreflightResult,
    tokenizer,
    runtime,
    installed,
    optimizer,
    scheduler,
    dependencies: RunnerDependencies,
    restored: "RestoredCheckpoint | None" = None,
    pause_signal: PauseSignal | None = None,
    mode: str = "train",
) -> FoundationRunResult:
    """Train in complete accumulation windows; act only at safe boundaries.

    Per window boundary: scheduler step, telemetry sample, resource-guard
    evaluation, and checkpoint-schedule bookkeeping. A pause or fail decision
    (or an operator signal) terminates with a safe checkpoint and a manifest
    reason; completion writes the same artifacts with reason ``completed``.
    """

    del runtime
    from pneuma_lab.foundation.authorization import apply_verified_authorization
    from pneuma_lab.foundation.checkpoints import (
        CheckpointManager,
        CheckpointSchedule,
        TrainingProgress,
        ValidationMetric,
    )
    from pneuma_lab.foundation.dataset import (
        DeterministicSampler,
        FoundationCollator,
        FoundationShardDataset,
    )
    from pneuma_lab.foundation.optimizer import FoundationOptimizerLoop

    authorization = preflight.authorization
    config = DEFAULT_TRAINING_CONFIG
    accumulation = config.gradient_accumulation
    run_id = _run_id(preflight)
    started = dependencies.clock()

    dataset = FoundationShardDataset(
        authorization.shard_path,
        authorization.shard_manifest_path,
    )
    token_counts = dataset.token_counts()
    if restored is None:
        progress = TrainingProgress(
            epoch=0,
            sampler_seed=request.seed,
            dataset_cursor=0,
            microbatch=0,
            optimizer_step=0,
            tokens_seen=0,
            selected_learning_rate=request.learning_rate,
        )
    else:
        progress = restored.progress
    sampler = DeterministicSampler(
        progress.sampler_seed,
        epoch=progress.epoch,
        cursor=progress.dataset_cursor,
    )
    collator = FoundationCollator(
        tokenizer,
        sequence_length=config.sequence_length,
    )
    # Microbatches hold sealed EffectiveTrainingRecords, which by design
    # cannot cross process boundaries, so collation runs in-process while
    # the profile's data_loader_workers stays a recorded manifest constant.
    loop = FoundationOptimizerLoop(
        model=installed.model,
        optimizer=optimizer,
        junctions=tuple(installed.junctions),
        shared_core=installed.shared_core,
        gradient_accumulation=accumulation,
    )
    modules = _trainable_modules(installed)
    bindings = _resume_bindings(request, preflight)
    manager = CheckpointManager(_checkpoint_root(request))
    schedule = CheckpointSchedule(
        every_steps=config.checkpoint_every_steps,
        every_seconds=config.checkpoint_every_seconds,
        clock=dependencies.clock,
    )
    telemetry = dependencies.telemetry_factory(output_root=request.run_root)
    guard = ResourceGuard(max_gpu_temp_c=config.thermal_pause_c)
    writer = RunManifestWriter(request.run_root)

    lineage = (
        (*restored.lineage, run_id)
        if restored is not None and run_id not in restored.lineage
        else (restored.lineage if restored is not None else (run_id,))
    )
    best_loss: float | None = None
    if restored is not None and math.isfinite(restored.best_validation.value):
        best_loss = float(restored.best_validation.value)
    last_loss: float | None = None
    last_checkpoint: Path | None = restored.path if restored is not None else None
    last_saved_step = progress.optimizer_step
    last_saved_time = dependencies.clock()
    run_tokens = 0
    status = _COMPLETED
    reason = _COMPLETED

    def manifest_payload(current_status: str, termination: str | None) -> dict:
        return _build_run_manifest(
            request=request,
            preflight=preflight,
            run_id=run_id,
            mode=mode,
            status=current_status,
            termination_reason=termination,
            progress=progress,
            telemetry_samples=telemetry.samples,
            wall_time_seconds=max(dependencies.clock() - started, 0.0),
            run_tokens=run_tokens,
            best_loss=best_loss,
            last_loss=last_loss,
            last_checkpoint=last_checkpoint,
            lineage=lineage,
        )

    def save_checkpoint(termination: str | None) -> Path:
        metric = ValidationMetric(
            metric_name=_VALIDATION_METRIC_NAME,
            value=(best_loss if best_loss is not None else _UNMEASURED_VALIDATION_LOSS),
            higher_is_better=False,
        )
        return manager.save(
            trainable_modules=modules,
            optimizer=optimizer,
            scheduler=scheduler,
            progress=progress,
            bindings=bindings,
            recurrent_state=None,
            active_memory=None,
            telemetry_state=None,
            best_validation=metric,
            lineage=lineage,
            termination_reason=termination,
            gradient_accumulation=accumulation,
        )

    writer.write_manifest(manifest_payload("running", None))
    writer.append_event({"event": "run_started", "run_id": run_id, "mode": mode})

    windows_run = 0
    try:
        windows = sampler.iter_windows(
            token_counts,
            gradient_accumulation=accumulation,
            token_ceiling=authorization.token_ceiling,
            tokens_seen=progress.tokens_seen,
        )
        for window in windows:
            window_started = dependencies.clock()
            window_tokens = 0
            step = None
            for index in window:
                effective = apply_verified_authorization(dataset[index], authorization)
                batch = collator([effective])
                step = loop.train_microbatch(
                    model_inputs={
                        "input_ids": batch.input_ids,
                        "attention_mask": batch.attention_mask,
                        "labels": batch.labels,
                    },
                    forecast_targets=batch.forecast_targets,
                    forecast_masks=batch.forecast_masks,
                    effective_weight=batch.effective_weight,
                    document_count=batch.document_count,
                )
                window_tokens += token_counts[index]
            if step is None or not step.optimizer_stepped:
                raise FoundationRunError(
                    "accumulation window ended outside an optimizer boundary"
                )
            windows_run += 1
            scheduler.step()
            progress = dataclasses.replace(
                progress,
                dataset_cursor=sampler.cursor,
                microbatch=progress.microbatch + accumulation,
                optimizer_step=progress.optimizer_step + 1,
                tokens_seen=progress.tokens_seen + window_tokens,
            )
            run_tokens += window_tokens
            loss_finite = math.isfinite(step.language_loss) and math.isfinite(
                step.forecast_loss
            )
            if loss_finite:
                last_loss = float(step.language_loss)
                best_loss = (
                    last_loss if best_loss is None else min(best_loss, last_loss)
                )
            elapsed = max(dependencies.clock() - window_started, 0.0)
            try:
                telemetry.sample(
                    tokens_per_second=(window_tokens / elapsed if elapsed > 0 else 0.0),
                    steps_per_second=1.0 / elapsed if elapsed > 0 else 0.0,
                    loss_finite=loss_finite,
                )
                boundary_samples = tuple(telemetry.samples)
            except TelemetryError:
                # A transient probe failure must never kill the run: an empty
                # sample set routes through the guard as a missing resource
                # sample, pausing at this safe boundary with a checkpoint.
                boundary_samples = ()
            decision = guard.evaluate(
                boundary_samples,
                operator_interrupt=bool(pause_signal and pause_signal.requested),
            )
            if decision.action != ACTION_CONTINUE:
                reason = decision.reasons[0]
                status = "failed" if decision.action == ACTION_FAIL else "paused"
                break
            if schedule.should_save(
                optimizer_step=progress.optimizer_step,
                last_saved_step=last_saved_step,
                last_saved_time=last_saved_time,
                microbatch=progress.microbatch,
                gradient_accumulation=accumulation,
            ):
                last_checkpoint = save_checkpoint(None)
                last_saved_step = progress.optimizer_step
                last_saved_time = dependencies.clock()
                writer.append_event(
                    {
                        "event": "checkpoint_saved",
                        "optimizer_step": progress.optimizer_step,
                        "path": last_checkpoint.name,
                    }
                )

        if windows_run == 0 and status == _COMPLETED:
            # Every candidate window was absent or skipped for the ceiling;
            # the run completes honestly but the emptiness stays auditable.
            writer.append_event(
                {
                    "event": "no_trainable_window",
                    "run_id": run_id,
                    "tokens_seen": progress.tokens_seen,
                }
            )
        last_checkpoint = save_checkpoint(None if reason == _COMPLETED else reason)
        manifest_path = writer.write_manifest(manifest_payload(status, reason))
        writer.append_event(
            {
                "event": "terminated",
                "status": status,
                "termination_reason": reason,
                "optimizer_step": progress.optimizer_step,
            }
        )
    except BaseException as exc:
        # Best-effort terminal record for unexpected errors: the manifest
        # must never keep claiming "running". The original error always
        # propagates; a checkpoint is attempted only at a safe boundary.
        if progress.microbatch % accumulation == 0:
            with contextlib.suppress(Exception):
                last_checkpoint = save_checkpoint(None)
        with contextlib.suppress(Exception):
            writer.write_manifest(manifest_payload("failed", None))
        with contextlib.suppress(Exception):
            writer.append_event(
                {
                    "event": "terminated",
                    "status": "failed",
                    "termination_reason": None,
                    "error": type(exc).__name__,
                    "optimizer_step": progress.optimizer_step,
                }
            )
        raise
    return FoundationRunResult(
        run_id=run_id,
        status=status,
        progress=progress,
        last_checkpoint=last_checkpoint,
        run_manifest_path=manifest_path,
    )


__all__ = [
    "FoundationPreflightResult",
    "FoundationRunError",
    "FoundationRunRequest",
    "FoundationRunResult",
    "PauseSignal",
    "RunnerDependencies",
    "assert_clean_commit",
    "default_runner_dependencies",
    "execute_safe_boundary_loop",
    "pause_signals",
    "preflight_foundation_run",
    "resume_foundation_training",
    "run_foundation_training",
    "unique_trainable_parameters",
]

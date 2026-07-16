"""Preflight-first foundation runner: exact ordering, guarded allocation, resume."""

from __future__ import annotations

import dataclasses
import hashlib
import itertools
import json
import math
import os
import signal
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest

torch = pytest.importorskip("torch")

from pneuma_lab.foundation.authorization import (  # noqa: E402
    FoundationAuthorizationError,
    VerifiedFoundationAuthorization,
)
from pneuma_lab.foundation.core import (  # noqa: E402
    JunctionAdapter,
    SharedPneumaCore,
)
from pneuma_lab.foundation.doctor import EnvironmentProbe  # noqa: E402
from pneuma_lab.foundation.environment import (  # noqa: E402
    FOUNDATION_VERSION_PINS,
    TRANSFORMERS_COMMIT,
)
from pneuma_lab.foundation.model_cache import CachedSnapshot  # noqa: E402
from pneuma_lab.foundation.records import (  # noqa: E402
    GradientEligibility,
    LaneDisposition,
    TerminalRole,
    render_foundation_record,
)
from pneuma_lab.foundation.resources import ResourceSample  # noqa: E402
from pneuma_lab.foundation.runner import (  # noqa: E402
    FoundationRunRequest,
    PauseSignal,
    RunnerDependencies,
    pause_signals,
    preflight_foundation_run,
    resume_foundation_training,
    run_foundation_training,
)
from pneuma_lab.foundation.specs import MODEL_SPECS  # noqa: E402
from pneuma_lab.foundation.telemetry import TelemetryError  # noqa: E402
from pneuma_lab.schemas import load_schema  # noqa: E402


_REVISION = MODEL_SPECS["2b"].revision
_HIDDEN = 8
_CODE_COMMIT = "c" * 40
_SCOPE_DIGEST = "1" * 64
_LANE_ID = "swe-gym-openhands-sampled"
_BASE_SAMPLE = {
    "sampled_at": 1_752_600_000.0,
    "gpu_temp_c": 65.0,
    "thermal_throttled": False,
    "process_vram_gb": 6.0,
    "reserved_vram_gb": 6.5,
    "global_vram_used_gb": 7.0,
    "global_vram_free_gb": 1.0,
    "process_ram_gb": 18.0,
    "system_ram_gb": 25.0,
    "gpu_utilization_percent": 95.0,
    "power_watts": 70.0,
    "disk_free_gb": 50.0,
}


class FakeTokenizer:
    """Deterministic tokenizer stub with a fixed token count per encode call."""

    eos_token_id = 0

    def __init__(self, tokens_per_call: int = 50) -> None:
        self.tokens_per_call = tokens_per_call

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        del text, add_special_tokens
        return [1] * self.tokens_per_call


class FakeQwenModel(torch.nn.Module):
    """A tiny frozen-base stand-in that routes hidden states through one junction."""

    def __init__(self) -> None:
        super().__init__()
        self.embed = torch.nn.Embedding(4, _HIDDEN)
        self.config = SimpleNamespace(use_cache=True)
        self.junction: JunctionAdapter | None = None
        self.gradient_checkpointing = False

    def gradient_checkpointing_enable(self, **kwargs) -> None:
        del kwargs
        self.gradient_checkpointing = True

    def forward(self, *, input_ids, attention_mask, labels, use_cache=False):
        assert use_cache is False
        del attention_mask
        assert self.junction is not None
        hidden = self.embed(input_ids)
        mapped = self.junction(hidden)
        target = self.embed(labels.clamp(min=0))
        loss = (mapped - target).square().mean()
        return SimpleNamespace(loss=loss)


class FakeSampler:
    """Telemetry stub: healthy samples, with overrides applied to the first one."""

    def __init__(
        self,
        output_root: Path,
        overrides: dict,
        *,
        telemetry_failures: int = 0,
        sample_side_effect=None,
    ) -> None:
        self.output_root = Path(output_root)
        self.samples: list[ResourceSample] = []
        self._overrides = dict(overrides)
        self._telemetry_failures = telemetry_failures
        self._sample_side_effect = sample_side_effect

    def sample(self, *, tokens_per_second, steps_per_second, loss_finite):
        if self._sample_side_effect is not None:
            self._sample_side_effect()
        if self._telemetry_failures > 0:
            self._telemetry_failures -= 1
            raise TelemetryError("transient nvidia-smi failure")
        values = dict(_BASE_SAMPLE)
        values.update(
            tokens_per_second=float(tokens_per_second),
            steps_per_second=float(steps_per_second),
            loss_finite=bool(loss_finite),
        )
        values.update(self._overrides)
        self._overrides = {}
        value = ResourceSample(**values)
        self.samples.append(value)
        return value


def _ready_probe() -> EnvironmentProbe:
    dependencies = {name.replace("-", "_"): True for name in FOUNDATION_VERSION_PINS}
    dependencies["transformers_multimodal"] = True
    return EnvironmentProbe(
        system="Linux",
        release="5.15.167.4-microsoft-standard-WSL2",
        python_version=(3, 12, 11),
        cuda_available=True,
        gpu_total_vram_gb=8.0,
        ram_gb=24.0,
        fts5_available=True,
        dependencies=dependencies,
        gpu_name="NVIDIA GeForce RTX 4060 Laptop GPU",
        cuda_bf16_supported=True,
        transformers_commit=TRANSFORMERS_COMMIT,
        bitsandbytes_cuda_available=True,
        dependency_versions={
            name.replace("-", "_"): version
            for name, version in FOUNDATION_VERSION_PINS.items()
        },
    )


def _blocked_probe() -> EnvironmentProbe:
    return dataclasses.replace(_ready_probe(), cuda_available=False)


def _example(index: int) -> dict:
    return {
        "dataset_family": "swe-gym",
        "dataset_id": _LANE_ID,
        "example_id": f"example-{index:03d}",
        "source_revision": None,
        "target": {"resolved": index % 2 == 0},
        "input": {
            "prefix": "full",
            "trajectory": {"num_messages": 4, "num_agent_steps": 3},
            "observable_summary": {"tool_call_count": 2},
            "objective": {"present": True, "text_length": 40},
            "feature_refs": ["openhands-sampled-training/0.1.0"],
        },
        "split_group": {"repo": "example/repo", "task_id": f"task-{index:03d}"},
    }


def _records(count: int, tokenizer: FakeTokenizer) -> list[dict]:
    disposition = LaneDisposition(
        terminal_role=TerminalRole.TRAIN,
        gradient_eligibility=GradientEligibility.FIRST_STAGE,
        license_disposition="local_research_candidate_no_redistribution",
        privacy_disposition="redaction_verified",
        dual_use_disposition="not_flagged",
        oracle_disposition="target_only",
    )
    records = []
    for index in range(count):
        record = render_foundation_record(
            _example(index),
            lane_disposition=disposition,
            split_assignment={"split_id": "train", "quarantine_id": None},
            tokenizer=tokenizer,
            tokenizer_revision=_REVISION,
            source_receipt_hashes=("a" * 64,),
        )
        records.append(json.loads(json.dumps(record)))
    return records


def _record_digest(record: dict) -> str:
    payload = json.dumps(
        record,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _fake_authorization(
    repo_root: Path,
    *,
    record_count: int,
    tokens_per_call: int,
    scope_digest: str,
) -> VerifiedFoundationAuthorization:
    records = _records(record_count, FakeTokenizer(tokens_per_call))
    shard_root = Path(repo_root) / "build" / "shards"
    shard_root.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        for record in records
    )
    shard_path = shard_root / "shard.jsonl"
    shard_path.write_text(payload, encoding="utf-8")
    shard_digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    manifest_path = shard_root / "shard.manifest.json"
    manifest_payload = json.dumps(
        {"sha256": shard_digest, "example_count": len(records)}
    )
    manifest_path.write_text(manifest_payload, encoding="utf-8")
    manifest_digest = hashlib.sha256(manifest_payload.encode("utf-8")).hexdigest()
    scope = {
        "stage": "100k",
        "token_ceiling": 100_000,
        "code_commit": _CODE_COMMIT,
        "learning_rates": [0.00005, 0.0001, 0.0002],
        "model": {
            "key": "2b",
            "model_id": "Qwen/Qwen3.5-2B",
            "revision": _REVISION,
            "tokenizer_id": "Qwen/Qwen3.5-2B",
            "tokenizer_revision": _REVISION,
        },
        "artifacts": {
            "shard": {
                "path": "build/shards/shard.jsonl",
                "sha256": shard_digest,
                "size": len(payload),
            },
            "shard_manifest": {
                "path": "build/shards/shard.manifest.json",
                "sha256": manifest_digest,
                "size": len(manifest_payload),
            },
            "license_receipt": {
                "path": "build/license_receipt.json",
                "sha256": "b" * 64,
                "size": 2,
            },
        },
        "authorized_lane_weights": {_LANE_ID: 1.0},
        "output_root": "build/foundation/runs/",
        "budget": {"paid_compute_usd": 0, "cloud_jobs_used": 0},
    }
    return VerifiedFoundationAuthorization(
        model_key="2b",
        token_ceiling=100_000,
        shard_path=shard_path,
        shard_manifest_path=manifest_path,
        output_root=Path(repo_root) / "build" / "foundation" / "runs",
        authorized_lane_weights={_LANE_ID: 1.0},
        authorized_record_membership={
            record["record_id"]: _record_digest(record) for record in records
        },
        scope_digest=scope_digest,
        manifest={"scope": scope},
    )


def _runner_dependencies(
    calls: list[str] | None = None,
    *,
    authorization_error: str | None = None,
    resource_action: str = "continue",
    record_count: int = 32,
    tokens_per_call: int = 50,
    scope_digest: str = _SCOPE_DIGEST,
    environment_ready: bool = True,
    clean_commit_error: str | None = None,
    telemetry_failures: int = 0,
    sample_side_effect=None,
) -> RunnerDependencies:
    from pneuma_lab.foundation.runner import FoundationRunError

    calls = calls if calls is not None else []
    overrides = {
        "continue": {},
        "pause": {"gpu_temp_c": 90.0},
        "fail": {"disk_free_gb": 0.5},
    }[resource_action]

    def verify_authorization(path, *, repo_root, registry_path, suite_path):
        del path, registry_path, suite_path
        calls.append("verify_authorization")
        if authorization_error is not None:
            raise FoundationAuthorizationError(authorization_error)
        return _fake_authorization(
            Path(repo_root),
            record_count=record_count,
            tokens_per_call=tokens_per_call,
            scope_digest=scope_digest,
        )

    def verify_cache(model_key, *, cache_root):
        calls.append("verify_cache")
        return CachedSnapshot(
            model_key=model_key,
            snapshot_path=Path(cache_root) / "models" / model_key / _REVISION,
            receipt_path=Path(cache_root) / "receipt.json",
            revision=_REVISION,
        )

    def environment_probe():
        calls.append("environment_probe")
        return _ready_probe() if environment_ready else _blocked_probe()

    def clean_commit(repo_root, *, expected):
        del repo_root
        calls.append("clean_commit")
        if clean_commit_error is not None:
            raise FoundationRunError(clean_commit_error)
        assert expected == _CODE_COMMIT

    def tokenizer_loader(snapshot_path, *, local_files_only):
        del snapshot_path
        calls.append("tokenizer_loader")
        assert local_files_only is True
        return FakeTokenizer(tokens_per_call)

    def model_loader(model_key, *, allow_download, vision, snapshot_path):
        del snapshot_path
        calls.append("load_model")
        assert allow_download is False
        assert vision is False
        return SimpleNamespace(
            model_key=model_key,
            model=FakeQwenModel(),
            processor=None,
            architecture_plan="fake-architecture-plan",
        )

    def junction_installer(model, plan):
        del plan
        calls.append("install_junctions")
        shared = SharedPneumaCore()
        junction = JunctionAdapter(
            hidden_size=_HIDDEN,
            shared_core=shared,
            microsteps=4,
        )
        model.junction = junction
        return SimpleNamespace(
            model=model,
            shared_core=shared,
            junctions=(junction,),
        )

    def optimizer_builder(parameters, lr):
        calls.append("build_optimizer")
        return torch.optim.AdamW(parameters, lr=lr)

    def scheduler_builder(optimizer, token_ceiling):
        del token_ceiling
        calls.append("build_scheduler")
        return torch.optim.lr_scheduler.StepLR(optimizer, step_size=10)

    def telemetry_factory(*, output_root):
        calls.append("telemetry_factory")
        return FakeSampler(
            output_root,
            overrides,
            telemetry_failures=telemetry_failures,
            sample_side_effect=sample_side_effect,
        )

    return RunnerDependencies(
        verify_authorization=verify_authorization,
        verify_cache=verify_cache,
        environment_probe=environment_probe,
        clean_commit=clean_commit,
        tokenizer_loader=tokenizer_loader,
        model_loader=model_loader,
        junction_installer=junction_installer,
        optimizer_builder=optimizer_builder,
        scheduler_builder=scheduler_builder,
        telemetry_factory=telemetry_factory,
        clock=itertools.count(0.0, 1.0).__next__,
    )


def _run_request(tmp_path: Path, **overrides) -> FoundationRunRequest:
    values = dict(
        repo_root=tmp_path,
        authorization_path=tmp_path / "authorization.json",
        registry_path=tmp_path / "registry.json",
        suite_path=tmp_path / "suite.json",
        cache_root=tmp_path / "cache",
        run_root=tmp_path / "run",
        stage="100k",
        learning_rate=0.0001,
    )
    values.update(overrides)
    return FoundationRunRequest(**values)


def test_preflight_never_loads_model_or_constructs_optimizer(tmp_path: Path) -> None:
    calls: list[str] = []
    result = preflight_foundation_run(
        _run_request(tmp_path),
        dependencies=_runner_dependencies(calls),
    )
    assert result.ready is True
    assert "load_model" not in calls
    assert "build_optimizer" not in calls


def test_preflight_runs_exact_dependency_order(tmp_path: Path) -> None:
    calls: list[str] = []
    preflight_foundation_run(
        _run_request(tmp_path),
        dependencies=_runner_dependencies(calls),
    )
    assert calls == [
        "verify_authorization",
        "clean_commit",
        "verify_cache",
        "environment_probe",
    ]


def test_preflight_binds_authorization_cache_and_environment(tmp_path: Path) -> None:
    result = preflight_foundation_run(
        _run_request(tmp_path),
        dependencies=_runner_dependencies(),
    )
    assert result.authorization.model_key == "2b"
    assert result.authorization.token_ceiling == 100_000
    assert result.cache.revision == _REVISION
    assert result.environment["ready"] is True
    assert result.environment["blockers"] == []


def test_run_allocates_only_after_complete_preflight(tmp_path: Path) -> None:
    calls: list[str] = []
    result = run_foundation_training(
        _run_request(tmp_path),
        dependencies=_runner_dependencies(calls),
    )
    assert result.status == "completed"
    assert calls == [
        "verify_authorization",
        "clean_commit",
        "verify_cache",
        "environment_probe",
        "tokenizer_loader",
        "load_model",
        "install_junctions",
        "build_optimizer",
        "build_scheduler",
        "telemetry_factory",
    ]


def test_completed_run_writes_schema_valid_manifest_and_checkpoint(
    tmp_path: Path,
) -> None:
    request = _run_request(tmp_path)
    result = run_foundation_training(
        request,
        dependencies=_runner_dependencies(),
    )
    assert result.status == "completed"
    assert result.progress.microbatch == 32
    assert result.progress.microbatch % 32 == 0
    assert result.progress.optimizer_step == 1
    assert result.last_checkpoint is not None
    assert result.last_checkpoint.exists()
    manifest = json.loads(result.run_manifest_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(
        load_schema("foundation-run-manifest.schema.json")
    ).validate(manifest)
    assert manifest["status"] == "completed"
    assert manifest["mode"] == "train"
    assert manifest["termination_reason"] == "completed"
    assert manifest["run_id"] == result.run_id
    assert manifest["bindings"]["code_commit"] == _CODE_COMMIT
    assert manifest["curriculum"] == {
        "stage": "100k",
        "lane_weights": {_LANE_ID: 1.0},
    }
    assert manifest["training"]["token_ceiling"] == 100_000
    assert manifest["training"]["learning_rate"] == request.learning_rate
    # Collation is deliberately in-process (sealed records cannot cross
    # process boundaries), so the manifest records the effective value.
    assert manifest["training"]["data_loader_workers"] == 0
    assert manifest["progress"]["tokens_seen"] == result.progress.tokens_seen
    assert manifest["progress"]["microbatches_seen"] == 32
    assert manifest["checkpoints"]["last_path"] == str(result.last_checkpoint)
    assert manifest["telemetry"]["thermal_throttle_intervals"] == 0


def test_windows_never_cross_the_token_ceiling(tmp_path: Path) -> None:
    result = run_foundation_training(
        _run_request(tmp_path),
        dependencies=_runner_dependencies(
            record_count=64,
            tokens_per_call=800,
        ),
    )
    assert result.status == "completed"
    # Each record recounts to 1600 tokens, so one 32-record window holds
    # 51,200 tokens and a second complete window would cross the 100k ceiling.
    assert result.progress.optimizer_step == 1
    assert result.progress.tokens_seen == 32 * 1_600
    assert result.progress.tokens_seen <= 100_000


def test_resumed_run_matches_uninterrupted_run_exactly(tmp_path: Path) -> None:
    uninterrupted_request = _run_request(tmp_path / "a")
    uninterrupted = run_foundation_training(
        uninterrupted_request,
        dependencies=_runner_dependencies(record_count=64, tokens_per_call=25),
    )
    assert uninterrupted.status == "completed"
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
    assert paused.progress.optimizer_step == 1
    assert paused.progress.dataset_cursor == 32
    assert paused.last_checkpoint is not None

    resumed = resume_foundation_training(
        dataclasses.replace(
            interrupted_request,
            checkpoint_path=paused.last_checkpoint,
        ),
        dependencies=_runner_dependencies(record_count=64, tokens_per_call=25),
    )
    assert resumed.status == "completed"
    assert resumed.progress == uninterrupted.progress
    manifest = json.loads(resumed.run_manifest_path.read_text(encoding="utf-8"))
    assert manifest["mode"] == "resume"

    left = torch.load(
        uninterrupted.last_checkpoint, map_location="cpu", weights_only=True
    )
    right = torch.load(resumed.last_checkpoint, map_location="cpu", weights_only=True)
    assert left["progress"] == right["progress"]
    assert set(left["modules"]) == set(right["modules"])
    for name in left["modules"]:
        assert set(left["modules"][name]) == set(right["modules"][name])
        for key in left["modules"][name]:
            assert torch.equal(
                left["modules"][name][key],
                right["modules"][name][key],
            ), f"tensor differs: {name}.{key}"


def test_zero_window_run_is_visible_and_keeps_the_index_strict(
    tmp_path: Path,
) -> None:
    request = _run_request(tmp_path)
    # Sixteen records can never form one complete 32-microbatch window.
    result = run_foundation_training(
        request,
        dependencies=_runner_dependencies(record_count=16),
    )
    assert result.status == "completed"
    assert result.progress.optimizer_step == 0
    assert result.progress.tokens_seen == 0
    assert result.last_checkpoint is not None
    events = [
        json.loads(line)
        for line in (request.run_root / "events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert any(event.get("event") == "no_trainable_window" for event in events)
    manifest = json.loads(result.run_manifest_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(
        load_schema("foundation-run-manifest.schema.json")
    ).validate(manifest)
    assert manifest["validation"] == {"best_loss": None, "last_loss": None}

    def reject_constant(value: str) -> None:
        raise AssertionError(f"checkpoint index is not strict JSON: {value}")

    index_text = (request.run_root / "checkpoints" / "index.json").read_text(
        encoding="utf-8"
    )
    index = json.loads(index_text, parse_constant=reject_constant)
    assert all(math.isfinite(record["value"]) for record in index["checkpoints"])


def test_runner_module_imports_without_torch() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src"
    code = (
        "import builtins\n"
        "real_import = builtins.__import__\n"
        "def deny(name, *args, **kwargs):\n"
        "    if name == 'torch' or name.startswith('torch.'):\n"
        "        raise ImportError('torch is blocked for this probe')\n"
        "    return real_import(name, *args, **kwargs)\n"
        "builtins.__import__ = deny\n"
        "import pneuma_lab.foundation.runner\n"
        "print('torch-free-import-ok')\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(source_root)},
    )
    assert completed.returncode == 0, completed.stderr
    assert "torch-free-import-ok" in completed.stdout


def test_pause_signal_handlers_install_and_restore() -> None:
    state = PauseSignal()
    before = signal.getsignal(signal.SIGINT)
    with pause_signals(state) as active:
        assert active is state
        handler = signal.getsignal(signal.SIGINT)
        assert handler is not before
        assert state.requested is False
        handler(signal.SIGINT, None)
        assert state.requested is True
    assert signal.getsignal(signal.SIGINT) is before

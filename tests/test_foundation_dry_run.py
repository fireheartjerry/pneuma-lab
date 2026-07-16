"""No-gradient dry-run gates: parity, optimizer absence, latency, and FLOPs."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

torch = pytest.importorskip("torch")

from torch import nn

from pneuma_lab.foundation import dry_run as dry_run_module
from pneuma_lab.foundation.dry_run import (
    DryRunError,
    DryRunRequest,
    build_required_cache_cases,
    compare_captured_outputs,
    enforce_flops_budget,
    enforce_latency_budget,
    estimate_base_forward_flops,
    estimate_junction_flops,
    percentile_95,
    run_no_gradient_dry_run,
)
from pneuma_lab.foundation.model_cache import CachedSnapshot, prepare_pinned_snapshot
from pneuma_lab.foundation.runtime import CacheBoundary, LoadedRuntime
from pneuma_lab.foundation.specs import (
    ArchitecturePlan,
    MODEL_SPECS,
    validate_pinned_config,
)


_SPEC = MODEL_SPECS["2b"]


def _pinned_config() -> dict:
    return {
        "hidden_size": _SPEC.hidden_size,
        "layer_types": list(_SPEC.expected_layer_types),
        "num_hidden_layers": _SPEC.layer_count,
    }


def _prepare_cache(tmp_path: Path) -> CachedSnapshot:
    def fake_download(**kwargs) -> None:
        local_dir = Path(kwargs["local_dir"])
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "config.json").write_text(
            json.dumps(_pinned_config(), sort_keys=True),
            encoding="utf-8",
        )
        (local_dir / "tokenizer.json").write_text(
            '{"model":{"type":"fixture"}}\n',
            encoding="utf-8",
        )

    return prepare_pinned_snapshot(
        "2b",
        cache_root=tmp_path / "cache",
        snapshot_download=fake_download,
    )


def _dry_run_request(tmp_path: Path, *, model_key: str = "2b") -> DryRunRequest:
    return DryRunRequest(
        model_key=model_key,
        cache_root=tmp_path / "cache",
        output_root=tmp_path / "out",
        stage="stage_a",
    )


class FakeTokenizer:
    def __call__(self, text: str, return_tensors: str = "pt") -> dict:
        assert return_tensors == "pt"
        input_ids = torch.tensor(
            [[(ord(character) % 89) + 5 for character in text[:8]]],
            dtype=torch.long,
        )
        return {
            "input_ids": input_ids,
            "attention_mask": torch.ones_like(input_ids),
        }


class _FakeDecoderLayer(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.gain = nn.Parameter(torch.ones(()))

    def forward(self, hidden):
        return hidden * self.gain


class FakeQwen(nn.Module):
    """Deterministic 24-layer stand-in exposing the real decoder layout."""

    def __init__(
        self,
        *,
        ballast_parameters: int = 8_000_000,
        drift_step: float = 0.0,
    ) -> None:
        super().__init__()
        torch.manual_seed(20260716)
        inner = nn.Module()
        inner.embed_tokens = nn.Embedding(128, _SPEC.hidden_size)
        inner.layers = nn.ModuleList(
            _FakeDecoderLayer() for _ in range(_SPEC.layer_count)
        )
        self.model = inner
        self.lm_head = nn.Linear(_SPEC.hidden_size, 48, bias=False)
        self.ballast = nn.Parameter(
            torch.zeros(ballast_parameters),
            requires_grad=False,
        )
        self.drift_step = drift_step
        self.forward_count = 0

    def forward(
        self,
        input_ids,
        attention_mask=None,
        past_key_values=None,
        use_cache=False,
    ):
        self.forward_count += 1
        hidden = self.model.embed_tokens(input_ids)
        for layer in self.model.layers:
            hidden = layer(hidden)
        logits = self.lm_head(hidden) + self.drift_step * self.forward_count
        cache = ((past_key_values or 0) + 1) if use_cache else None
        return SimpleNamespace(logits=logits, past_key_values=cache)


def _fake_runtime(model: nn.Module) -> LoadedRuntime:
    return LoadedRuntime(
        model_key="2b",
        model=model,
        processor=None,
        architecture_plan=validate_pinned_config(
            _SPEC,
            _pinned_config(),
            source_revision=_SPEC.revision,
        ),
    )


class ManualClock:
    """Deterministic clock: constant step, optionally slower after N calls."""

    def __init__(
        self,
        *,
        step: float = 0.001,
        slow_after: int | None = None,
        slow_step: float = 0.002,
    ) -> None:
        self.step = step
        self.slow_after = slow_after
        self.slow_step = slow_step
        self.value = 0.0
        self.calls = 0

    def __call__(self) -> float:
        self.calls += 1
        current = self.value
        if self.slow_after is not None and self.calls > self.slow_after:
            self.value += self.slow_step
        else:
            self.value += self.step
        return current


def test_dry_run_never_constructs_optimizer_or_gradients(tmp_path: Path) -> None:
    _prepare_cache(tmp_path)
    fake_runtime = _fake_runtime(FakeQwen())
    fake_tokenizer = FakeTokenizer()
    optimizer_factory = Mock(side_effect=AssertionError("optimizer constructed"))
    report = run_no_gradient_dry_run(
        _dry_run_request(tmp_path),
        runtime_loader=lambda *args, **kwargs: fake_runtime,
        tokenizer_loader=lambda *args, **kwargs: fake_tokenizer,
        optimizer_factory=optimizer_factory,
        clock=ManualClock(),
    )
    assert report["optimizer_constructed"] is False
    assert report["backward_called"] is False
    assert report["gradient_tensor_count"] == 0
    optimizer_factory.assert_not_called()


def test_dry_run_report_covers_required_cases_and_gates(tmp_path: Path) -> None:
    prepared = _prepare_cache(tmp_path)
    runtime_calls: list = []
    tokenizer_calls: list = []
    fake_runtime = _fake_runtime(FakeQwen())

    def runtime_loader(model_key, **kwargs):
        runtime_calls.append((model_key, kwargs))
        return fake_runtime

    def tokenizer_loader(path, **kwargs):
        tokenizer_calls.append((path, kwargs))
        return FakeTokenizer()

    request = _dry_run_request(tmp_path)
    report = run_no_gradient_dry_run(
        request,
        runtime_loader=runtime_loader,
        tokenizer_loader=tokenizer_loader,
        clock=ManualClock(),
    )

    assert runtime_calls == [
        (
            "2b",
            {
                "allow_download": False,
                "vision": False,
                "snapshot_path": prepared.snapshot_path,
            },
        )
    ]
    assert tokenizer_calls == [(prepared.snapshot_path, {"local_files_only": True})]
    assert report["report_kind"] == "pneuma_foundation_no_gradient_dry_run"
    assert report["model_key"] == "2b"
    assert report["stage"] == "stage_a"
    assert report["model_revision"] == _SPEC.revision
    assert report["parity"]["case_names"] == [
        "cached",
        "continued",
        "explicit_reset",
        "fresh",
        "packed_reset",
    ]
    assert report["parity"]["max_absolute_error"] == 0.0
    assert report["output_shape"] == [1, 8, 48]
    assert report["junction"] == {
        "latent_width": 256,
        "memory_slots": 64,
        "candidate_plans": 2,
        "total_microsteps": 4,
        "layer_indices": [19],
    }
    assert report["latency"]["overhead_fraction"] == pytest.approx(0.0)
    assert report["latency"]["limit_fraction"] == 0.25
    assert report["flops"]["limit_fraction"] == 0.20
    assert report["flops"]["overhead_fraction"] < 0.20
    written = json.loads(
        (request.output_root / "dry-run-report.json").read_text(encoding="utf-8")
    )
    assert written == report


def test_dry_run_rejects_non_2b_requests(tmp_path: Path) -> None:
    with pytest.raises(DryRunError, match="2b"):
        run_no_gradient_dry_run(
            _dry_run_request(tmp_path, model_key="4b"),
            runtime_loader=lambda *args, **kwargs: pytest.fail("runtime loaded"),
            tokenizer_loader=lambda *args, **kwargs: pytest.fail("tokenizer loaded"),
        )


def test_dry_run_fails_when_disabled_parity_is_broken(tmp_path: Path) -> None:
    _prepare_cache(tmp_path)
    request = _dry_run_request(tmp_path)
    drifting_runtime = _fake_runtime(FakeQwen(drift_step=0.001))
    with pytest.raises(DryRunError, match="parity"):
        run_no_gradient_dry_run(
            request,
            runtime_loader=lambda *args, **kwargs: drifting_runtime,
            tokenizer_loader=lambda *args, **kwargs: FakeTokenizer(),
            clock=ManualClock(),
        )
    assert not (request.output_root / "dry-run-report.json").exists()


def test_dry_run_fails_when_enabled_p95_exceeds_latency_budget(
    tmp_path: Path,
) -> None:
    _prepare_cache(tmp_path)
    request = _dry_run_request(tmp_path)
    slow_enabled_clock = ManualClock(
        step=0.001,
        slow_after=2 * dry_run_module._TIMED_FORWARDS,
        slow_step=0.002,
    )
    with pytest.raises(DryRunError, match="latency"):
        run_no_gradient_dry_run(
            request,
            runtime_loader=lambda *args, **kwargs: _fake_runtime(FakeQwen()),
            tokenizer_loader=lambda *args, **kwargs: FakeTokenizer(),
            clock=slow_enabled_clock,
        )
    assert not (request.output_root / "dry-run-report.json").exists()


def test_dry_run_fails_when_flops_budget_is_exceeded(tmp_path: Path) -> None:
    _prepare_cache(tmp_path)
    request = _dry_run_request(tmp_path)
    light_runtime = _fake_runtime(FakeQwen(ballast_parameters=0))
    with pytest.raises(DryRunError, match="FLOP"):
        run_no_gradient_dry_run(
            request,
            runtime_loader=lambda *args, **kwargs: light_runtime,
            tokenizer_loader=lambda *args, **kwargs: FakeTokenizer(),
            clock=ManualClock(),
        )
    assert not (request.output_root / "dry-run-report.json").exists()


def test_dry_run_rejects_a_junction_off_the_pinned_layer(tmp_path: Path) -> None:
    _prepare_cache(tmp_path)
    plan = validate_pinned_config(
        _SPEC,
        _pinned_config(),
        source_revision=_SPEC.revision,
    )
    off_layer_plan = ArchitecturePlan(
        model_key=plan.model_key,
        hidden_size=plan.hidden_size,
        layer_types=plan.layer_types,
        primary_layer=15,
        secondary_layer=plan.secondary_layer,
        active_layers=(15,),
    )
    runtime = LoadedRuntime(
        model_key="2b",
        model=FakeQwen(),
        processor=None,
        architecture_plan=off_layer_plan,
    )
    with pytest.raises(DryRunError, match="19"):
        run_no_gradient_dry_run(
            _dry_run_request(tmp_path),
            runtime_loader=lambda *args, **kwargs: runtime,
            tokenizer_loader=lambda *args, **kwargs: FakeTokenizer(),
            clock=ManualClock(),
        )


def test_build_required_cache_cases_covers_every_boundary() -> None:
    cases = build_required_cache_cases(FakeTokenizer())
    assert [(name, boundary) for name, boundary, _ in cases] == [
        ("fresh", CacheBoundary.NEW_DOCUMENT),
        ("cached", CacheBoundary.TOOL_TICK),
        ("packed_reset", CacheBoundary.NEW_DOCUMENT),
        ("explicit_reset", CacheBoundary.EXPLICIT_RESET),
        ("continued", CacheBoundary.TOOL_TICK),
    ]
    for _, _, model_inputs in cases:
        assert model_inputs["input_ids"].shape == (1, 8)


def test_compare_captured_outputs_detects_divergence() -> None:
    left = {"fresh": torch.zeros(2, 2)}
    right = {"fresh": torch.zeros(2, 2)}
    parity = compare_captured_outputs(left, right)
    assert parity == {"case_names": ["fresh"], "max_absolute_error": 0.0}
    with pytest.raises(DryRunError, match="case sets differ"):
        compare_captured_outputs(left, {"cached": torch.zeros(2, 2)})
    with pytest.raises(AssertionError):
        compare_captured_outputs(left, {"fresh": torch.full((2, 2), 0.5)})


def test_percentile_95_uses_the_ceiling_rank() -> None:
    assert percentile_95(range(1, 21)) == 19.0
    assert percentile_95([5.0]) == 5.0
    with pytest.raises(DryRunError, match="sample"):
        percentile_95([])


def test_latency_budget_enforces_the_25_percent_limit() -> None:
    assert enforce_latency_budget(enabled_p95=1.0, disabled_p95=1.0) == 0.0
    assert enforce_latency_budget(
        enabled_p95=1.24,
        disabled_p95=1.0,
    ) == pytest.approx(0.24)
    with pytest.raises(DryRunError, match="latency"):
        enforce_latency_budget(enabled_p95=1.26, disabled_p95=1.0)
    with pytest.raises(DryRunError, match="positive"):
        enforce_latency_budget(enabled_p95=1.0, disabled_p95=0.0)


def test_flops_budget_enforces_the_20_percent_limit() -> None:
    assert enforce_flops_budget(additional_flops=20, base_flops=100) == 0.2
    with pytest.raises(DryRunError, match="FLOP"):
        enforce_flops_budget(additional_flops=21, base_flops=100)
    with pytest.raises(DryRunError, match="positive"):
        enforce_flops_budget(additional_flops=1, base_flops=0)


def test_analytic_flop_estimates_match_hand_computation() -> None:
    assert estimate_base_forward_flops(parameter_count=10, sequence_length=3) == 60
    assert (
        estimate_junction_flops(
            sequence_length=2,
            hidden_size=4,
            latent_width=2,
            candidate_plans=2,
            total_microsteps=4,
            memory_slots=3,
        )
        == 408
    )

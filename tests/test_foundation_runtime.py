"""Local runtime selection, generation limits, and native cache continuity."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from pneuma_lab.foundation.runtime import (
    CacheBoundary,
    LocalRuntimeConfig,
    PromotionManager,
    RuntimeLimitError,
    cache_for_boundary,
    load_local_qwen,
    validate_generation_request,
)
from pneuma_lab.foundation import runtime as foundation_runtime
from pneuma_lab.foundation.specs import MODEL_SPECS


def test_runtime_defaults_are_local_quantized_and_text_first() -> None:
    config = LocalRuntimeConfig()
    assert config.paid_api_allowed is False
    assert config.recurring_cloud_allowed is False
    assert config.quantized is True
    assert config.vision_enabled is False
    assert config.max_text_context == 4096
    assert config.max_generated_tokens == 1024


def test_4b_miss_persists_permanent_2b_fallback(tmp_path: Path) -> None:
    manager = PromotionManager(tmp_path / "runtime-selection.json")
    assert manager.select(recurrent_gate_passed=True, four_b_gates_passed=True) == "4b"
    assert manager.select(recurrent_gate_passed=True, four_b_gates_passed=False) == "2b"
    assert manager.select(recurrent_gate_passed=True, four_b_gates_passed=True) == "2b"


def test_runtime_cannot_promote_without_recurrent_gate(tmp_path: Path) -> None:
    manager = PromotionManager(tmp_path / "selection.json")
    assert manager.select(recurrent_gate_passed=False, four_b_gates_passed=True) == "2b"


def test_generation_limits_fail_before_model_execution() -> None:
    validate_generation_request(text_tokens=4096, max_new_tokens=1024)
    with pytest.raises(RuntimeLimitError, match="context"):
        validate_generation_request(text_tokens=4097, max_new_tokens=1)
    with pytest.raises(RuntimeLimitError, match="generated"):
        validate_generation_request(text_tokens=1, max_new_tokens=1025)


def test_native_cache_is_reset_for_documents_and_continued_for_tool_ticks() -> None:
    cache = object()
    assert cache_for_boundary(cache, CacheBoundary.NEW_DOCUMENT) is None
    assert cache_for_boundary(cache, CacheBoundary.EXPLICIT_RESET) is None
    assert cache_for_boundary(cache, CacheBoundary.TOOL_TICK) is cache


def test_loader_validates_pin_and_keeps_vision_off_by_default() -> None:
    spec = MODEL_SPECS["2b"]
    calls = []

    def config_loader(model_id, **kwargs):
        calls.append(("config", model_id, kwargs))
        return {
            "text_config": {
                "hidden_size": spec.hidden_size,
                "num_hidden_layers": spec.layer_count,
                "layer_types": list(spec.expected_layer_types),
            }
        }

    def model_loader(model_id, **kwargs):
        calls.append(("model", model_id, kwargs))
        return object()

    def processor_loader(model_id, **kwargs):
        calls.append(("processor", model_id, kwargs))
        return object()

    loaded = load_local_qwen(
        "2b",
        allow_download=False,
        vision=False,
        config_loader=config_loader,
        model_loader=model_loader,
        processor_loader=processor_loader,
        quantization_factory=lambda: "nf4-config",
    )
    assert loaded.model_key == "2b"
    assert loaded.processor is None
    assert [call[0] for call in calls] == ["config", "model"]
    assert calls[0][2]["revision"] == spec.revision
    assert calls[0][2]["local_files_only"] is True
    assert calls[1][2]["quantization_config"] == "nf4-config"


def test_loader_uses_local_snapshot_offline(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "0")
    spec = MODEL_SPECS["2b"]
    snapshot = tmp_path / "models" / "2b" / spec.revision
    snapshot.mkdir(parents=True)
    calls = []

    def config_loader(source, **kwargs):
        calls.append(
            (
                "config",
                source,
                kwargs,
                os.environ.get("HF_HUB_OFFLINE"),
                os.environ.get("TRANSFORMERS_OFFLINE"),
            )
        )
        return {
            "hidden_size": spec.hidden_size,
            "num_hidden_layers": spec.layer_count,
            "layer_types": list(spec.expected_layer_types),
        }

    def model_loader(source, **kwargs):
        calls.append(("model", source, kwargs, None, None))
        return object()

    loaded = load_local_qwen(
        "2b",
        allow_download=False,
        vision=False,
        snapshot_path=snapshot,
        config_loader=config_loader,
        model_loader=model_loader,
        processor_loader=lambda *args, **kwargs: pytest.fail("vision loaded"),
        quantization_factory=lambda: "nf4-config",
    )
    assert loaded.model_key == "2b"
    assert [call[0] for call in calls] == ["config", "model"]
    for call in calls:
        assert call[1] == str(snapshot)
        assert call[2]["local_files_only"] is True
        assert call[2]["trust_remote_code"] is False
        assert "revision" not in call[2]
    assert calls[0][3] == "1"
    assert calls[0][4] == "1"


def test_loader_rejects_downloads_with_a_pinned_snapshot(tmp_path: Path) -> None:
    with pytest.raises(RuntimeLimitError, match="download"):
        load_local_qwen(
            "2b",
            allow_download=True,
            vision=False,
            snapshot_path=tmp_path,
            config_loader=lambda *args, **kwargs: pytest.fail("config loaded"),
            model_loader=lambda *args, **kwargs: pytest.fail("model loaded"),
            processor_loader=lambda *args, **kwargs: pytest.fail("vision loaded"),
            quantization_factory=lambda: None,
        )


def test_default_loader_uses_official_multimodal_auto_class(monkeypatch) -> None:
    pytest.importorskip("torch")
    multimodal_loader = object()
    fake_transformers = SimpleNamespace(
        AutoConfig=SimpleNamespace(from_pretrained=object()),
        AutoModelForMultimodalLM=SimpleNamespace(from_pretrained=multimodal_loader),
        AutoProcessor=SimpleNamespace(from_pretrained=object()),
        BitsAndBytesConfig=lambda **kwargs: kwargs,
    )
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    _config, model_loader, _processor, _quantization = (
        foundation_runtime._default_loaders()
    )
    assert model_loader is multimodal_loader

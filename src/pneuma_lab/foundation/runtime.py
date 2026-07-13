"""Offline quantized model loading, promotion fallback, and cache boundaries."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

from pneuma_lab.foundation.specs import (
    MODEL_SPECS,
    RUNTIME_LIMITS,
    validate_pinned_config,
)


class RuntimeLimitError(ValueError):
    """Raised before inference when a local runtime limit would be exceeded."""


class CacheBoundary(str, Enum):
    NEW_DOCUMENT = "new_document"
    EXPLICIT_RESET = "explicit_reset"
    TOOL_TICK = "tool_tick"


@dataclass(frozen=True)
class LocalRuntimeConfig:
    paid_api_allowed: bool = False
    recurring_cloud_allowed: bool = False
    quantized: bool = True
    vision_enabled: bool = False
    max_text_context: int = RUNTIME_LIMITS.max_text_context
    max_generated_tokens: int = RUNTIME_LIMITS.max_generated_tokens
    max_vram_gb: float = RUNTIME_LIMITS.max_vram_gb
    max_ram_gb: float = RUNTIME_LIMITS.max_ram_gb


@dataclass(frozen=True)
class LoadedRuntime:
    model_key: str
    model: object
    processor: object | None
    architecture_plan: object


class PromotionManager:
    """Persist a 4B gate miss as an irreversible local 2B fallback."""

    def __init__(self, state_path: Path) -> None:
        self.state_path = Path(state_path)

    def _permanently_fallen_back(self) -> bool:
        if not self.state_path.exists():
            return False
        value = json.loads(self.state_path.read_text(encoding="utf-8"))
        return value.get("permanent_model") == "2b"

    def _persist_fallback(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                {
                    "runtime_selection_schema_version": "0.1.0",
                    "permanent_model": "2b",
                    "reason": "4b_gate_miss",
                },
                indent=4,
            )
            + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.state_path)

    def select(
        self,
        *,
        recurrent_gate_passed: bool,
        four_b_gates_passed: bool,
    ) -> str:
        if self._permanently_fallen_back():
            return "2b"
        if not recurrent_gate_passed:
            return "2b"
        if not four_b_gates_passed:
            self._persist_fallback()
            return "2b"
        return "4b"


def validate_generation_request(*, text_tokens: int, max_new_tokens: int) -> None:
    if text_tokens > RUNTIME_LIMITS.max_text_context:
        raise RuntimeLimitError("text context exceeds the 4K local limit")
    if max_new_tokens > RUNTIME_LIMITS.max_generated_tokens:
        raise RuntimeLimitError("generated token request exceeds the 1K local limit")
    if text_tokens < 0 or max_new_tokens < 1:
        raise RuntimeLimitError(
            "token counts must be non-negative and generation positive"
        )


def cache_for_boundary(previous_cache, boundary: CacheBoundary):
    """Pass native cache objects through only for deliberate tool-tick continuation."""

    if boundary in {CacheBoundary.NEW_DOCUMENT, CacheBoundary.EXPLICIT_RESET}:
        return None
    if boundary is CacheBoundary.TOOL_TICK:
        return previous_cache
    raise RuntimeLimitError(f"unknown cache boundary: {boundary!r}")


def _default_loaders():
    try:
        import torch
        from transformers import (
            AutoConfig,
            AutoModelForMultimodalLM,
            AutoProcessor,
            BitsAndBytesConfig,
        )
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError(
            "install the foundation extra in WSL2 before loading Qwen"
        ) from exc

    def quantization_factory():
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

    return (
        AutoConfig.from_pretrained,
        AutoModelForMultimodalLM.from_pretrained,
        AutoProcessor.from_pretrained,
        quantization_factory,
    )


def load_local_qwen(
    model_key: str,
    *,
    allow_download: bool,
    vision: bool,
    config_loader: Callable | None = None,
    model_loader: Callable | None = None,
    processor_loader: Callable | None = None,
    quantization_factory: Callable | None = None,
) -> LoadedRuntime:
    """Load one pinned model locally; network access is opt-in and 397B is barred."""

    spec = MODEL_SPECS.get(model_key)
    if spec is None:
        raise RuntimeLimitError(f"unknown model key: {model_key!r}")
    if not spec.download_allowed:
        raise RuntimeLimitError(
            "397B is a compatibility reference and cannot be loaded"
        )
    if any(
        loader is None
        for loader in (
            config_loader,
            model_loader,
            processor_loader,
            quantization_factory,
        )
    ):
        defaults = _default_loaders()
        config_loader = config_loader or defaults[0]
        model_loader = model_loader or defaults[1]
        processor_loader = processor_loader or defaults[2]
        quantization_factory = quantization_factory or defaults[3]
    common = {
        "revision": spec.revision,
        "local_files_only": not allow_download,
        "trust_remote_code": False,
    }
    config = config_loader(spec.model_id, **common)
    config_dict = config.to_dict() if hasattr(config, "to_dict") else config
    architecture = validate_pinned_config(
        spec,
        config_dict,
        source_revision=spec.revision,
    )
    model = model_loader(
        spec.model_id,
        **common,
        quantization_config=quantization_factory(),
        device_map="auto",
    )
    processor = processor_loader(spec.model_id, **common) if vision else None
    return LoadedRuntime(
        model_key=model_key,
        model=model,
        processor=processor,
        architecture_plan=architecture,
    )

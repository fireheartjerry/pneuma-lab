"""Pinned model architecture and resource contracts for local foundation work."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence


class PinnedConfigMismatch(ValueError):
    """Raised when a downloaded config does not match its pinned contract."""


def _hybrid_schedule(repetitions: int) -> tuple[str, ...]:
    return tuple(
        layer_type
        for _ in range(repetitions)
        for layer_type in (
            "linear_attention",
            "linear_attention",
            "linear_attention",
            "full_attention",
        )
    )


@dataclass(frozen=True)
class ModelSpec:
    key: str
    model_id: str
    revision: str
    role: str
    hidden_size: int
    layer_count: int
    expected_layer_types: tuple[str, ...]
    download_allowed: bool


@dataclass(frozen=True)
class CoreLimits:
    max_trainable_parameters: int = 25_000_000
    latent_width: int = 256
    memory_slots: int = 64
    candidate_plans: int = 2
    total_microsteps: int = 4
    max_base_forwards: int = 1
    max_flops_overhead: float = 0.20
    max_p95_latency_overhead: float = 0.25


@dataclass(frozen=True)
class RuntimeLimits:
    max_vram_gb: float = 7.5
    max_ram_gb: float = 24.0
    max_text_context: int = 4096
    max_generated_tokens: int = 1024
    vision_on_demand: bool = True


@dataclass(frozen=True)
class ArchitecturePlan:
    model_key: str
    hidden_size: int
    layer_types: tuple[str, ...]
    primary_layer: int
    secondary_layer: int
    active_layers: tuple[int, ...]

    def with_secondary(self) -> "ArchitecturePlan":
        return ArchitecturePlan(
            model_key=self.model_key,
            hidden_size=self.hidden_size,
            layer_types=self.layer_types,
            primary_layer=self.primary_layer,
            secondary_layer=self.secondary_layer,
            active_layers=(self.secondary_layer, self.primary_layer),
        )


MODEL_SPECS: Mapping[str, ModelSpec] = {
    "2b": ModelSpec(
        key="2b",
        model_id="Qwen/Qwen3.5-2B",
        revision="15852e8c16360a2fea060d615a32b45270f8a8fc",
        role="research",
        hidden_size=2048,
        layer_count=24,
        expected_layer_types=_hybrid_schedule(6),
        download_allowed=True,
    ),
    "4b": ModelSpec(
        key="4b",
        model_id="Qwen/Qwen3.5-4B",
        revision="851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a",
        role="promotion_candidate",
        hidden_size=2560,
        layer_count=32,
        expected_layer_types=_hybrid_schedule(8),
        download_allowed=True,
    ),
    "397b": ModelSpec(
        key="397b",
        model_id="Qwen/Qwen3.5-397B-A17B",
        revision="8472618112abcbd45acbcdc58436aff4233c23f7",
        role="compatibility_reference_only",
        hidden_size=4096,
        layer_count=60,
        expected_layer_types=_hybrid_schedule(15),
        download_allowed=False,
    ),
}

CORE_LIMITS = CoreLimits()
RUNTIME_LIMITS = RuntimeLimits()


def _full_attention_layers(layer_types: Sequence[str]) -> tuple[int, ...]:
    layers = tuple(
        index
        for index, layer_type in enumerate(layer_types)
        if layer_type == "full_attention"
    )
    if not layers:
        raise PinnedConfigMismatch("layer_types contains no full_attention blocks")
    return layers


def _quantile_layer(full_layers: Sequence[int], fraction: float) -> int:
    position = max(1, math.ceil(len(full_layers) * fraction))
    return int(full_layers[position - 1])


def derive_junction_layers(
    layer_types: Sequence[str],
    *,
    include_secondary: bool = False,
) -> tuple[int, ...]:
    """Derive full-attention junctions from the live hybrid block schedule.

    Fractions are selected by ceiling so a six-full-attention model places its
    primary junction at the fifth block (layer 19), while the eight-block model
    places it at the sixth (layer 23).
    """

    full_layers = _full_attention_layers(layer_types)
    primary = _quantile_layer(full_layers, 0.75)
    if not include_secondary:
        return (primary,)
    secondary = _quantile_layer(full_layers, 0.50)
    return (secondary, primary)


def _text_config(config: Mapping) -> Mapping:
    nested = config.get("text_config")
    return nested if isinstance(nested, Mapping) else config


def validate_pinned_config(
    spec: ModelSpec,
    config: Mapping,
    *,
    source_revision: str,
) -> ArchitecturePlan:
    """Validate an actual Hugging Face config before any model allocation."""

    if source_revision != spec.revision:
        raise PinnedConfigMismatch(
            f"revision mismatch for {spec.model_id}: {source_revision!r}"
        )
    if not spec.download_allowed:
        raise PinnedConfigMismatch(
            f"{spec.model_id} is a compatibility reference and cannot be loaded"
        )

    text = _text_config(config)
    hidden_size = text.get("hidden_size")
    layer_count = text.get("num_hidden_layers")
    layer_types = text.get("layer_types")
    if not isinstance(layer_types, (list, tuple)):
        raise PinnedConfigMismatch("config is missing an explicit layer_types list")
    normalized = tuple(str(value) for value in layer_types)

    if hidden_size != spec.hidden_size:
        raise PinnedConfigMismatch(
            f"hidden_size changed: expected {spec.hidden_size}, got {hidden_size!r}"
        )
    if layer_count != spec.layer_count or len(normalized) != spec.layer_count:
        raise PinnedConfigMismatch(
            f"layer count changed: expected {spec.layer_count}, got {layer_count!r}"
        )
    if normalized != spec.expected_layer_types:
        raise PinnedConfigMismatch(
            "layer_types changed from the pinned hybrid schedule; refusing hooks"
        )

    secondary, primary = derive_junction_layers(
        normalized,
        include_secondary=True,
    )
    return ArchitecturePlan(
        model_key=spec.key,
        hidden_size=spec.hidden_size,
        layer_types=normalized,
        primary_layer=primary,
        secondary_layer=secondary,
        active_layers=(primary,),
    )

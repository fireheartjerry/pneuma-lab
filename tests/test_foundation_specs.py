"""Pinned Qwen3.5 architecture and local-resource contracts."""

from __future__ import annotations

import pytest

from pneuma_lab.foundation.specs import (
    CORE_LIMITS,
    MODEL_SPECS,
    RUNTIME_LIMITS,
    PinnedConfigMismatch,
    derive_junction_layers,
    validate_pinned_config,
)


def _config(layer_count: int, hidden_size: int) -> dict:
    return {
        "text_config": {
            "hidden_size": hidden_size,
            "num_hidden_layers": layer_count,
            "layer_types": [
                "linear_attention" if index % 4 != 3 else "full_attention"
                for index in range(layer_count)
            ],
        }
    }


def test_pinned_model_specs_match_approved_revisions() -> None:
    assert MODEL_SPECS["2b"].model_id == "Qwen/Qwen3.5-2B"
    assert MODEL_SPECS["2b"].revision == ("15852e8c16360a2fea060d615a32b45270f8a8fc")
    assert MODEL_SPECS["4b"].model_id == "Qwen/Qwen3.5-4B"
    assert MODEL_SPECS["4b"].revision == ("851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a")
    assert MODEL_SPECS["397b"].download_allowed is False


@pytest.mark.parametrize(
    ("model_key", "primary", "secondary"),
    (("2b", 19, 11), ("4b", 23, 15)),
)
def test_junctions_are_derived_from_full_attention_schedule(
    model_key: str,
    primary: int,
    secondary: int,
) -> None:
    spec = MODEL_SPECS[model_key]
    plan = validate_pinned_config(
        spec,
        _config(spec.layer_count, spec.hidden_size),
        source_revision=spec.revision,
    )
    assert plan.primary_layer == primary
    assert plan.secondary_layer == secondary
    assert plan.active_layers == (primary,)
    assert derive_junction_layers(plan.layer_types, include_secondary=True) == (
        secondary,
        primary,
    )


def test_pinned_config_fails_closed_when_schedule_changes() -> None:
    spec = MODEL_SPECS["2b"]
    config = _config(spec.layer_count, spec.hidden_size)
    config["text_config"]["layer_types"][18] = "full_attention"
    with pytest.raises(PinnedConfigMismatch, match="layer_types"):
        validate_pinned_config(
            spec,
            config,
            source_revision=spec.revision,
        )


def test_pinned_config_rejects_wrong_revision() -> None:
    spec = MODEL_SPECS["4b"]
    with pytest.raises(PinnedConfigMismatch, match="revision"):
        validate_pinned_config(
            spec,
            _config(spec.layer_count, spec.hidden_size),
            source_revision="main",
        )


def test_local_limits_encode_the_approved_ceiling() -> None:
    assert CORE_LIMITS.max_trainable_parameters == 25_000_000
    assert CORE_LIMITS.latent_width == 256
    assert CORE_LIMITS.memory_slots == 64
    assert CORE_LIMITS.candidate_plans == 2
    assert CORE_LIMITS.total_microsteps == 4
    assert CORE_LIMITS.max_flops_overhead == pytest.approx(0.20)
    assert CORE_LIMITS.max_p95_latency_overhead == pytest.approx(0.25)
    assert RUNTIME_LIMITS.max_vram_gb == pytest.approx(7.5)
    assert RUNTIME_LIMITS.max_ram_gb == pytest.approx(24.0)
    assert RUNTIME_LIMITS.max_text_context == 4096
    assert RUNTIME_LIMITS.max_generated_tokens == 1024

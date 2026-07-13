"""Executable shape, parity, and supervision tests for the Pneuma junction."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from pneuma_lab.foundation.core import (  # noqa: E402
    FORECAST_TARGETS,
    JunctionAdapter,
    MetacognitiveForecast,
    SharedPneumaCore,
    metacognitive_loss,
    trainable_parameter_count,
)


def test_disabled_junction_is_bit_exact_and_preserves_cache_tuple() -> None:
    shared = SharedPneumaCore(latent_width=256, memory_slots=64, candidate_plans=2)
    junction = JunctionAdapter(hidden_size=32, shared_core=shared, microsteps=4)
    junction.enabled = False
    hidden = torch.randn(2, 5, 32)
    cache = object()
    output = junction.map_layer_output((hidden, cache))
    assert output[0] is hidden
    assert output[1] is cache
    assert torch.equal(output[0], hidden)


def test_core_respects_fixed_width_slots_candidates_and_microsteps() -> None:
    shared = SharedPneumaCore(latent_width=256, memory_slots=64, candidate_plans=2)
    junction = JunctionAdapter(hidden_size=32, shared_core=shared, microsteps=4)
    hidden = torch.randn(2, 5, 32)
    mapped = junction.map_layer_output(hidden)
    assert mapped.shape == hidden.shape
    assert shared.memory.shape == (64, 256)
    assert shared.last_candidate_weights.shape == (2, 2)
    assert shared.last_microsteps == 4
    assert set(junction.last_forecasts) == set(FORECAST_TARGETS)
    assert trainable_parameter_count(shared, junction) < 25_000_000


def test_two_junctions_share_core_and_split_four_microsteps() -> None:
    shared = SharedPneumaCore(latent_width=256, memory_slots=64, candidate_plans=2)
    first = JunctionAdapter(hidden_size=32, shared_core=shared, microsteps=2)
    second = JunctionAdapter(hidden_size=32, shared_core=shared, microsteps=2)
    hidden = torch.randn(1, 3, 32)
    first.map_layer_output(hidden)
    assert shared.last_microsteps == 2
    second.map_layer_output(hidden)
    assert shared.last_microsteps == 2
    assert first.shared_core is second.shared_core


def test_enabled_junction_backpropagates_through_core() -> None:
    shared = SharedPneumaCore(latent_width=256, memory_slots=64, candidate_plans=2)
    junction = JunctionAdapter(hidden_size=32, shared_core=shared, microsteps=4)
    hidden = torch.randn(2, 5, 32, requires_grad=True)
    output = junction(hidden)
    output.square().mean().backward()
    assert hidden.grad is not None
    assert junction.down_projection.weight.grad is not None
    assert shared.recurrent_cell.weight_hh.grad is not None


def test_real_4b_projection_shell_remains_under_parameter_ceiling() -> None:
    shared = SharedPneumaCore(latent_width=256, memory_slots=64, candidate_plans=2)
    junction = JunctionAdapter(hidden_size=2560, shared_core=shared, microsteps=4)
    assert trainable_parameter_count(shared, junction) < 25_000_000


def test_metacognitive_forecast_requires_the_full_masked_contract() -> None:
    head = MetacognitiveForecast(latent_width=256)
    latent = torch.randn(3, 256)
    predictions = head(latent)
    targets = {name: torch.zeros(3) for name in FORECAST_TARGETS}
    masks = {name: torch.ones(3, dtype=torch.bool) for name in FORECAST_TARGETS}
    loss = metacognitive_loss(predictions, targets, masks)
    assert loss.ndim == 0
    assert torch.isfinite(loss)

    targets.pop("intervention_response")
    with pytest.raises(ValueError, match="applicability masks"):
        metacognitive_loss(predictions, targets, masks)


def test_masked_forecast_loss_uses_only_applicable_targets() -> None:
    predictions = {name: torch.tensor([9.0]) for name in FORECAST_TARGETS}
    targets = {name: torch.tensor([0.0]) for name in FORECAST_TARGETS}
    masks = {name: torch.tensor([False]) for name in FORECAST_TARGETS}
    predictions["action_success"] = torch.tensor([2.0])
    masks["action_success"] = torch.tensor([True])
    assert metacognitive_loss(predictions, targets, masks).item() == 4.0
    masks["action_success"] = torch.tensor([False])
    with pytest.raises(ValueError, match="applicable"):
        metacognitive_loss(predictions, targets, masks)

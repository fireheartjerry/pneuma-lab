"""Hybrid-layer hook installation, parity cases, and transferable-core tests."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from pneuma_lab.foundation.integration import (  # noqa: E402
    CoreDisabled,
    install_junctions,
    transfer_shared_core,
)
from pneuma_lab.foundation.parity import ParityCase, assert_numerical_parity  # noqa: E402
from pneuma_lab.foundation.specs import MODEL_SPECS, validate_pinned_config  # noqa: E402


class FakeLayer(torch.nn.Module):
    def __init__(self, *, dtype=torch.float32):
        super().__init__()
        self.anchor = torch.nn.Parameter(torch.zeros(1, dtype=dtype))

    def forward(self, hidden, cache=None):
        return hidden + self.anchor + 0.01, cache


class FakeBackbone(torch.nn.Module):
    def __init__(self, layer_count: int, *, dtype=torch.float32):
        super().__init__()
        self.layers = torch.nn.ModuleList(
            FakeLayer(dtype=dtype) for _ in range(layer_count)
        )


class FakeQwen(torch.nn.Module):
    def __init__(self, layer_count: int, hidden_size: int, *, dtype=torch.float32):
        super().__init__()
        self.model = FakeBackbone(layer_count, dtype=dtype)
        self.base_projection = torch.nn.Linear(hidden_size, hidden_size, dtype=dtype)
        self.forward_calls = 0

    def forward(self, hidden, cache=None):
        self.forward_calls += 1
        current_cache = cache
        for layer in self.model.layers:
            hidden, current_cache = layer(hidden, current_cache)
        return hidden, current_cache


class ParameterlessQwen(torch.nn.Module):
    def __init__(self, layer_count: int):
        super().__init__()
        self.model = torch.nn.Module()
        self.model.layers = torch.nn.ModuleList(
            torch.nn.Identity() for _ in range(layer_count)
        )


def _plan(model_key: str = "2b"):
    spec = MODEL_SPECS[model_key]
    return validate_pinned_config(
        spec,
        {
            "text_config": {
                "hidden_size": spec.hidden_size,
                "num_hidden_layers": spec.layer_count,
                "layer_types": list(spec.expected_layer_types),
            }
        },
        source_revision=spec.revision,
    )


def test_installation_hooks_only_derived_primary_layer_and_freezes_base() -> None:
    plan = _plan()
    model = FakeQwen(plan.layer_types.__len__(), plan.hidden_size)
    installed = install_junctions(model, plan, activate_secondary=False)
    assert installed.layer_indices == (19,)
    assert installed.total_microsteps == 4
    assert all(
        not parameter.requires_grad for parameter in model.base_projection.parameters()
    )
    assert all(
        parameter.requires_grad for parameter in installed.shared_core.parameters()
    )

    hidden = torch.randn(1, 2, plan.hidden_size)
    cache = object()
    output, returned_cache = model(hidden, cache)
    assert output.shape == hidden.shape
    assert returned_cache is cache
    assert model.forward_calls == 1


def test_secondary_requires_gate_and_splits_total_microsteps() -> None:
    plan = _plan()
    model = FakeQwen(len(plan.layer_types), plan.hidden_size)
    with pytest.raises(ValueError, match="falsification gate"):
        install_junctions(model, plan, activate_secondary=True)
    installed = install_junctions(
        model,
        plan,
        activate_secondary=True,
        falsification_gate_passed=True,
    )
    assert installed.layer_indices == (11, 19)
    assert [junction.microsteps for junction in installed.junctions] == [2, 2]
    assert installed.total_microsteps == 4


def test_junctions_inherit_hooked_layer_device_and_floating_dtype() -> None:
    plan = _plan()
    model = FakeQwen(len(plan.layer_types), plan.hidden_size, dtype=torch.float64)
    installed = install_junctions(model, plan)
    parameter = next(installed.junctions[0].down_projection.parameters())
    hooked_parameter = next(model.model.layers[plan.primary_layer].parameters())
    assert parameter.device == hooked_parameter.device
    assert parameter.dtype == hooked_parameter.dtype


def test_secondary_junction_fails_closed_on_mixed_placements() -> None:
    plan = _plan()
    model = FakeQwen(len(plan.layer_types), plan.hidden_size)
    model.model.layers[plan.primary_layer].to(dtype=torch.float64)
    with pytest.raises(ValueError, match="must share one floating device/dtype"):
        install_junctions(
            model,
            plan,
            activate_secondary=True,
            falsification_gate_passed=True,
        )
    assert not hasattr(model, "pneuma_junctions")


def test_junction_installation_fails_without_base_floating_placement() -> None:
    plan = _plan()
    model = ParameterlessQwen(len(plan.layer_types))
    with pytest.raises(ValueError, match="cannot derive a floating device/dtype"):
        install_junctions(model, plan)
    assert not hasattr(model, "pneuma_junctions")


def test_core_disabled_parity_covers_fresh_cached_packed_reset_and_continued() -> None:
    plan = _plan()
    reference = FakeQwen(len(plan.layer_types), plan.hidden_size)
    modified = FakeQwen(len(plan.layer_types), plan.hidden_size)
    modified.load_state_dict(reference.state_dict())
    installed = install_junctions(modified, plan)
    hidden = torch.randn(1, 3, plan.hidden_size)
    cache = {"native": "mamba-cache-object"}
    cases = tuple(
        ParityCase(name=name, args=(hidden,), kwargs={"cache": cache})
        for name in ("fresh", "cached", "packed", "reset", "continued")
    )
    with CoreDisabled(installed):
        report = assert_numerical_parity(reference, modified, cases, atol=0.0, rtol=0.0)
    assert report.case_names == (
        "fresh",
        "cached",
        "packed",
        "reset",
        "continued",
    )
    assert report.max_absolute_error == 0.0


def test_shared_core_transfers_to_new_4b_projection_shell() -> None:
    source_plan = _plan("2b")
    source = install_junctions(
        FakeQwen(len(source_plan.layer_types), source_plan.hidden_size),
        source_plan,
    )
    with torch.no_grad():
        source.shared_core.recurrent_cell.bias_hh.fill_(0.25)
    target_plan = _plan("4b")
    target = install_junctions(
        FakeQwen(len(target_plan.layer_types), target_plan.hidden_size),
        target_plan,
    )
    transfer_shared_core(source.shared_core, target.shared_core)
    assert torch.equal(
        source.shared_core.recurrent_cell.bias_hh,
        target.shared_core.recurrent_cell.bias_hh,
    )
    assert source.junctions[0].down_projection.in_features == 2048
    assert target.junctions[0].down_projection.in_features == 2560
    assert all(
        not parameter.requires_grad for parameter in target.shared_core.parameters()
    )
    assert all(
        parameter.requires_grad
        for parameter in target.junctions[0].down_projection.parameters()
    )

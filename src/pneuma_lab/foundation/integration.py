"""Install bounded junctions without modifying native Qwen cache semantics."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass

try:
    from torch import nn
except ImportError as exc:  # pragma: no cover - optional dependency boundary
    raise ImportError(
        "pneuma_lab.foundation.integration requires the foundation torch extra"
    ) from exc

from pneuma_lab.foundation.core import (
    JunctionAdapter,
    SharedPneumaCore,
    trainable_parameter_count,
)
from pneuma_lab.foundation.specs import ArchitecturePlan, CORE_LIMITS


def _decoder_layers(model):
    candidates = (
        ("model", "layers"),
        ("model", "model", "layers"),
        # The pinned multimodal checkpoint nests the text decoder beside the
        # vision tower: Qwen3_5ForConditionalGeneration.model.language_model.
        ("model", "language_model", "layers"),
        ("language_model", "model", "layers"),
        ("language_model", "layers"),
    )
    for path in candidates:
        value = model
        for part in path:
            value = getattr(value, part, None)
            if value is None:
                break
        if value is not None and isinstance(value, nn.ModuleList):
            return value
    raise ValueError("cannot locate the Qwen decoder ModuleList")


def _floating_placement(module: nn.Module):
    """Return the first floating device/dtype placement exposed by a module."""

    for tensor in (*module.parameters(), *module.buffers()):
        if tensor.is_floating_point():
            return tensor.device, tensor.dtype
    return None


@dataclass(frozen=True)
class InstalledJunctions:
    model: nn.Module
    shared_core: SharedPneumaCore
    junctions: tuple[JunctionAdapter, ...]
    layer_indices: tuple[int, ...]
    hook_handles: tuple[object, ...]

    @property
    def total_microsteps(self) -> int:
        return sum(junction.microsteps for junction in self.junctions)


def install_junctions(
    model: nn.Module,
    plan: ArchitecturePlan,
    *,
    activate_secondary: bool = False,
    falsification_gate_passed: bool = False,
) -> InstalledJunctions:
    """Freeze the base and attach hooks only at validated full-attention layers."""

    if hasattr(model, "pneuma_junctions"):
        raise ValueError("model already has Pneuma junctions installed")
    if activate_secondary and not falsification_gate_passed:
        raise ValueError("secondary junction requires the falsification gate to pass")
    layers = _decoder_layers(model)
    if len(layers) != len(plan.layer_types):
        raise ValueError("live decoder layer count differs from validated config")
    fallback_placement = _floating_placement(model)
    for parameter in model.parameters():
        parameter.requires_grad = False

    layer_indices = (
        (plan.secondary_layer, plan.primary_layer)
        if activate_secondary
        else (plan.primary_layer,)
    )
    microsteps = CORE_LIMITS.total_microsteps // len(layer_indices)
    shared = SharedPneumaCore(
        latent_width=CORE_LIMITS.latent_width,
        memory_slots=CORE_LIMITS.memory_slots,
        candidate_plans=CORE_LIMITS.candidate_plans,
    )
    junctions = tuple(
        JunctionAdapter(
            hidden_size=plan.hidden_size,
            shared_core=shared,
            microsteps=microsteps,
        )
        for _ in layer_indices
    )
    model.pneuma_junctions = nn.ModuleList(junctions)
    placements = tuple(
        _floating_placement(layers[layer_index]) or fallback_placement
        for layer_index in layer_indices
    )
    if any(placement is None for placement in placements):
        delattr(model, "pneuma_junctions")
        raise ValueError("cannot derive a floating device/dtype for Pneuma junctions")
    if len(set(placements)) != 1:
        delattr(model, "pneuma_junctions")
        raise ValueError(
            "active junction layers must share one floating device/dtype placement"
        )
    device, dtype = placements[0]
    model.pneuma_junctions.to(device=device, dtype=dtype)
    handles = []
    for layer_index, junction in zip(layer_indices, junctions):

        def hook(_module, _inputs, output, *, adapter=junction):
            return adapter.map_layer_output(output)

        handles.append(layers[layer_index].register_forward_hook(hook))
    count = trainable_parameter_count(*junctions)
    if count > CORE_LIMITS.max_trainable_parameters:
        for handle in handles:
            handle.remove()
        delattr(model, "pneuma_junctions")
        raise ValueError(
            f"junctions have {count} trainable parameters, above the 25M ceiling"
        )
    return InstalledJunctions(
        model=model,
        shared_core=shared,
        junctions=junctions,
        layer_indices=layer_indices,
        hook_handles=tuple(handles),
    )


def transfer_shared_core(
    source: SharedPneumaCore,
    target: SharedPneumaCore,
    *,
    freeze: bool = True,
) -> None:
    """Copy only the fixed-width core; base-specific projections remain new."""

    target.load_state_dict(source.state_dict())
    if freeze:
        for parameter in target.parameters():
            parameter.requires_grad = False


class CoreDisabled(AbstractContextManager):
    """Temporarily bypass every junction for upstream numerical parity tests."""

    def __init__(self, installed: InstalledJunctions) -> None:
        self.installed = installed
        self.previous: tuple[bool, ...] = ()

    def __enter__(self) -> InstalledJunctions:
        self.previous = tuple(junction.enabled for junction in self.installed.junctions)
        for junction in self.installed.junctions:
            junction.enabled = False
        return self.installed

    def __exit__(self, exc_type, exc, traceback) -> None:
        for junction, enabled in zip(self.installed.junctions, self.previous):
            junction.enabled = enabled

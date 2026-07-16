"""Minimal local optimizer loop for frozen-base junction training."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math

try:
    import torch
    from torch import Tensor
except ImportError as exc:  # pragma: no cover - optional dependency boundary
    raise ImportError(
        "pneuma_lab.foundation.optimizer requires the foundation torch extra"
    ) from exc

from pneuma_lab.foundation.core import (
    FORECAST_TARGETS,
    JunctionAdapter,
    SharedPneumaCore,
    metacognitive_loss,
)


class TrainingBatchError(ValueError):
    """Raised before forward when batch boundaries or targets are unsafe."""


@dataclass(frozen=True)
class OptimizerStep:
    microbatch: int
    optimizer_stepped: bool
    language_loss: float
    forecast_loss: float


def _normalized_forecast_value(value, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrainingBatchError(
            f"forecast target requires finite numeric value: {name}"
        )
    try:
        normalized = float(value)
    except (OverflowError, ValueError) as exc:
        raise TrainingBatchError(
            f"forecast target requires finite numeric value: {name}"
        ) from exc
    if (
        not math.isfinite(normalized)
        or abs(normalized) > torch.finfo(torch.float32).max
    ):
        raise TrainingBatchError(
            f"forecast target requires finite numeric value: {name}"
        )
    return normalized


def _validated_effective_weight(value) -> Tensor:
    """Reject unauthorized weights before any base forward happens."""

    if (
        not isinstance(value, Tensor)
        or value.numel() != 1
        or not torch.is_floating_point(value)
    ):
        raise TrainingBatchError(
            "effective_weight must be a single-element floating-point tensor"
        )
    scale = value.detach().reshape(())
    weight = float(scale)
    if not math.isfinite(weight) or weight <= 0.0:
        raise TrainingBatchError("effective_weight must be a finite positive value")
    return scale


def forecast_tensors(record: Mapping, *, device=None):
    values = record.get("forecast_targets")
    if not isinstance(values, Mapping) or set(values) != set(FORECAST_TARGETS):
        raise TrainingBatchError("all forecast target entries are required")
    normalized_values = {}
    applicability = {}
    expected_fields = {"applicable", "value", "provenance"}
    for name in FORECAST_TARGETS:
        entry = values[name]
        if not isinstance(entry, Mapping) or set(entry) != expected_fields:
            raise TrainingBatchError(
                f"forecast target entries require exact fields: {name}"
            )
        applicable = entry["applicable"]
        if type(applicable) is not bool:
            raise TrainingBatchError(f"forecast target applicable must be bool: {name}")
        value = entry["value"]
        provenance = entry["provenance"]
        if applicable:
            normalized = _normalized_forecast_value(value, name=name)
            if not isinstance(provenance, str) or provenance not in {
                "observed_outcome",
                "specified_intervention",
            }:
                raise TrainingBatchError(
                    f"forecast target is not outcome-derived: {name}"
                )
            normalized_values[name] = normalized
        else:
            if value is not None or provenance is not None:
                raise TrainingBatchError(
                    f"masked forecast target fields must be null: {name}"
                )
            normalized_values[name] = 0.0
        applicability[name] = applicable
    targets = {
        name: torch.tensor(
            [normalized_values[name]],
            dtype=torch.float32,
            device=device,
        )
        for name in FORECAST_TARGETS
    }
    masks = {
        name: torch.tensor(
            [applicability[name]],
            dtype=torch.bool,
            device=device,
        )
        for name in FORECAST_TARGETS
    }
    return targets, masks


class FoundationOptimizerLoop:
    def __init__(
        self,
        *,
        model,
        optimizer,
        junctions: tuple[JunctionAdapter, ...],
        shared_core: SharedPneumaCore,
        gradient_accumulation: int,
        forecast_loss_weight: float = 1.0,
    ) -> None:
        if gradient_accumulation < 1:
            raise ValueError("gradient_accumulation must be positive")
        if not junctions:
            raise ValueError("at least one junction is required")
        self.model = model
        self.optimizer = optimizer
        self.junctions = junctions
        self.shared_core = shared_core
        self.gradient_accumulation = gradient_accumulation
        self.forecast_loss_weight = forecast_loss_weight
        self.microbatch = 0
        self.optimizer.zero_grad(set_to_none=True)

    def train_microbatch(
        self,
        *,
        model_inputs: Mapping[str, Tensor],
        forecast_targets: Mapping[str, Tensor],
        forecast_masks: Mapping[str, Tensor],
        effective_weight: Tensor,
        document_count: int,
    ) -> OptimizerStep:
        if document_count != 1:
            raise TrainingBatchError(
                "packed documents are forbidden because DeltaNet state must reset"
            )
        weight = _validated_effective_weight(effective_weight)
        self.shared_core.reset_state()
        output = self.model(**dict(model_inputs), use_cache=False)
        language_loss = output.loss
        forecast_losses = []
        for junction in self.junctions:
            if set(junction.last_forecasts) != set(FORECAST_TARGETS):
                raise TrainingBatchError("junction did not emit the forecast contract")
            forecast_losses.append(
                metacognitive_loss(
                    junction.last_forecasts,
                    forecast_targets,
                    forecast_masks,
                )
            )
        forecast_loss = torch.stack(forecast_losses).mean()
        combined = (
            language_loss + self.forecast_loss_weight * forecast_loss
        ) * weight.to(device=language_loss.device)
        (combined / self.gradient_accumulation).backward()
        self.microbatch += 1
        stepped = self.microbatch % self.gradient_accumulation == 0
        if stepped:
            self.optimizer.step()
            self.optimizer.zero_grad(set_to_none=True)
        return OptimizerStep(
            microbatch=self.microbatch,
            optimizer_stepped=stepped,
            language_loss=float(language_loss.detach()),
            forecast_loss=float(forecast_loss.detach()),
        )

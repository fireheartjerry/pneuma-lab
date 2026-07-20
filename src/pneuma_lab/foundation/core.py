"""Bounded recurrent junction and outcome-supervised metacognitive forecasts."""

from __future__ import annotations

from collections.abc import Mapping

try:
    import torch
    from torch import Tensor, nn
except ImportError as exc:  # pragma: no cover - exercised by minimal installs
    raise ImportError(
        "pneuma_lab.foundation.core requires the optional foundation dependencies"
    ) from exc


FORECAST_TARGETS = (
    "action_success",
    "expected_error",
    "verifier_outcome",
    "tool_cost",
    "token_cost",
    "latency_cost",
    "retrieval_usefulness",
    "intervention_response",
)


class MetacognitiveForecast(nn.Module):
    """Predict only quantities that can be joined to observed outcomes."""

    def __init__(self, *, latent_width: int) -> None:
        super().__init__()
        self.projection = nn.Linear(latent_width, len(FORECAST_TARGETS))

    def forward(self, latent: Tensor) -> dict[str, Tensor]:
        values = self.projection(latent)
        return {name: values[:, index] for index, name in enumerate(FORECAST_TARGETS)}


def metacognitive_loss(
    predictions: Mapping[str, Tensor],
    targets: Mapping[str, Tensor],
    masks: Mapping[str, Tensor],
) -> Tensor:
    """Average outcome-derived forecast losses over applicable targets only."""

    expected = set(FORECAST_TARGETS)
    if (
        set(predictions) != expected
        or set(targets) != expected
        or set(masks) != expected
    ):
        raise ValueError(
            "forecasts, targets, and applicability masks must match the contract"
        )
    losses = []
    for name in FORECAST_TARGETS:
        prediction = predictions[name]
        target = targets[name]
        mask = masks[name]
        if mask.dtype != torch.bool:
            raise ValueError(f"forecast mask must have dtype torch.bool: {name}")
        if prediction.shape != target.shape or prediction.shape != mask.shape:
            raise ValueError(
                f"forecast prediction, target, and mask shapes must match: {name}"
            )
        mask = mask.to(device=prediction.device)
        if mask.any():
            target = target.to(
                device=prediction.device,
                dtype=prediction.dtype,
            )
            applicable_prediction = prediction[mask]
            applicable_target = target[mask]
            if (
                not torch.isfinite(applicable_prediction).all()
                or not torch.isfinite(applicable_target).all()
            ):
                raise ValueError(
                    f"applicable forecast prediction and target must be finite: {name}"
                )
            losses.append(
                torch.nn.functional.mse_loss(
                    applicable_prediction,
                    applicable_target,
                )
            )
    if not losses:
        raise ValueError("at least one applicable forecast target is required")
    return torch.stack(losses).mean()


class SharedPneumaCore(nn.Module):
    """Fixed-width recurrent core shared by 2B and 4B projection shells."""

    def __init__(
        self,
        *,
        latent_width: int = 256,
        memory_slots: int = 64,
        candidate_plans: int = 2,
    ) -> None:
        super().__init__()
        if latent_width != 256:
            raise ValueError("the transferable core requires latent_width=256")
        if memory_slots != 64:
            raise ValueError("the local contract requires exactly 64 memory slots")
        if candidate_plans != 2:
            raise ValueError("the local contract requires exactly two candidate plans")
        self.latent_width = latent_width
        self.memory_slots = memory_slots
        self.candidate_plans = candidate_plans
        self.candidate_projection = nn.Linear(
            latent_width,
            latent_width * candidate_plans,
        )
        self.candidate_score = nn.Linear(latent_width, 1)
        self.memory_query = nn.Linear(latent_width, latent_width, bias=False)
        self.recurrent_cell = nn.GRUCell(latent_width, latent_width)
        self.forecast = MetacognitiveForecast(latent_width=latent_width)
        self.register_buffer("memory", torch.zeros(memory_slots, latent_width))
        self.register_buffer("recurrent_state", torch.zeros(1, latent_width))
        self.last_candidate_weights = torch.empty(0)
        self.last_microsteps = 0

    def reset_state(self) -> None:
        self.recurrent_state.zero_()

    def forward(
        self, latent: Tensor, *, microsteps: int
    ) -> tuple[Tensor, dict[str, Tensor]]:
        if not 1 <= microsteps <= 4:
            raise ValueError("microsteps must be between one and four")
        batch = latent.shape[0]
        candidates = self.candidate_projection(latent).reshape(
            batch,
            self.candidate_plans,
            self.latent_width,
        )
        scores = self.candidate_score(candidates).squeeze(-1)
        weights = torch.softmax(scores, dim=-1)
        state = torch.sum(candidates * weights.unsqueeze(-1), dim=1)

        # Backward saves these tensors. Compute from snapshots so committing
        # detached persistent state below cannot change their version counters.
        recurrent_snapshot = self.recurrent_state.clone()
        memory_snapshot = self.memory.clone()
        if recurrent_snapshot.shape[0] == 1:
            state = state + recurrent_snapshot.expand(batch, -1)
        query = self.memory_query(state)
        for _ in range(microsteps):
            attention = torch.softmax(
                query @ memory_snapshot.transpose(0, 1) / (self.latent_width**0.5),
                dim=-1,
            )
            retrieved = attention @ memory_snapshot
            state = self.recurrent_cell(state + retrieved, state)
            query = self.memory_query(state)

        with torch.no_grad():
            self.recurrent_state.copy_(state.detach().mean(dim=0, keepdim=True))
            slots = min(batch, self.memory_slots)
            self.memory[:slots].lerp_(state.detach()[:slots], 0.1)
        self.last_candidate_weights = weights.detach()
        self.last_microsteps = microsteps
        return state, self.forecast(state)


class JunctionAdapter(nn.Module):
    """Base-specific projection shell that leaves native caches untouched."""

    def __init__(
        self,
        *,
        hidden_size: int,
        shared_core: SharedPneumaCore,
        microsteps: int,
    ) -> None:
        super().__init__()
        if microsteps not in {2, 4}:
            raise ValueError("one junction uses four steps; two junctions use two each")
        self.hidden_size = hidden_size
        self.shared_core = shared_core
        self.microsteps = microsteps
        self.down_projection = nn.Linear(hidden_size, shared_core.latent_width)
        self.up_projection = nn.Linear(shared_core.latent_width, hidden_size)
        self.residual_scale = nn.Parameter(torch.tensor(0.01))
        self.enabled = True
        self.last_forecasts: dict[str, Tensor] = {}

    def _map_hidden(self, hidden: Tensor) -> Tensor:
        if not self.enabled:
            return hidden
        # The quantized base can emit hidden states in a different floating
        # dtype than the (for example BF16-cast) projection shells; the
        # junction computes in its own dtype and contributes back in the
        # base's dtype so the residual stream is never silently retyped.
        core_dtype = self.down_projection.weight.dtype
        pooled = hidden.mean(dim=1).to(core_dtype)
        latent = self.down_projection(pooled)
        recurrent, forecasts = self.shared_core(latent, microsteps=self.microsteps)
        residual = self.up_projection(recurrent).unsqueeze(1)
        self.last_forecasts = forecasts
        contribution = (self.residual_scale * residual).to(hidden.dtype)
        return hidden + contribution

    def map_layer_output(self, output):
        """Replace only hidden states and preserve every native cache object."""

        if not self.enabled:
            return output
        if isinstance(output, Tensor):
            return self._map_hidden(output)
        if isinstance(output, tuple) and output and isinstance(output[0], Tensor):
            return (self._map_hidden(output[0]), *output[1:])
        if isinstance(output, list) and output and isinstance(output[0], Tensor):
            return [self._map_hidden(output[0]), *output[1:]]
        raise TypeError("decoder layer output must be a tensor, tuple, or list")

    def forward(self, hidden: Tensor) -> Tensor:
        return self._map_hidden(hidden)


def trainable_parameter_count(*modules: nn.Module) -> int:
    """Count unique trainable tensors when modules share the same core."""

    seen: set[int] = set()
    total = 0
    for module in modules:
        for parameter in module.parameters():
            if parameter.requires_grad and id(parameter) not in seen:
                seen.add(id(parameter))
                total += parameter.numel()
    return total

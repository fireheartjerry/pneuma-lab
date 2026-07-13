"""The local optimizer performs one base call and bounded accumulation."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from pneuma_lab.foundation.core import (  # noqa: E402
    FORECAST_TARGETS,
    JunctionAdapter,
    SharedPneumaCore,
)
from pneuma_lab.foundation.optimizer import (  # noqa: E402
    FoundationOptimizerLoop,
    TrainingBatchError,
    forecast_targets_from_record,
)


class FakeLanguageModel(torch.nn.Module):
    def __init__(self, junction: JunctionAdapter):
        super().__init__()
        self.junction = junction
        self.base = torch.nn.Linear(16, 16)
        self.forward_calls = 0

    def forward(self, *, hidden, labels=None, use_cache=False):
        self.forward_calls += 1
        assert use_cache is False
        transformed = self.base(hidden)
        transformed = self.junction(transformed)
        return type("Output", (), {"loss": transformed.square().mean()})()


def _targets(batch: int = 2) -> dict:
    return {name: torch.zeros(batch) for name in FORECAST_TARGETS}


def test_optimizer_accumulates_and_steps_only_at_boundary() -> None:
    shared = SharedPneumaCore()
    junction = JunctionAdapter(hidden_size=16, shared_core=shared, microsteps=4)
    model = FakeLanguageModel(junction)
    for parameter in model.base.parameters():
        parameter.requires_grad = False
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=1e-4,
    )
    loop = FoundationOptimizerLoop(
        model=model,
        optimizer=optimizer,
        junctions=(junction,),
        shared_core=shared,
        gradient_accumulation=2,
    )
    before = junction.down_projection.weight.detach().clone()
    first = loop.train_microbatch(
        model_inputs={"hidden": torch.randn(2, 3, 16)},
        forecast_targets=_targets(),
        document_count=1,
    )
    assert first.optimizer_stepped is False
    second = loop.train_microbatch(
        model_inputs={"hidden": torch.randn(2, 3, 16)},
        forecast_targets=_targets(),
        document_count=1,
    )
    assert second.optimizer_stepped is True
    assert model.forward_calls == 2
    assert not torch.equal(before, junction.down_projection.weight)


def test_optimizer_rejects_multi_document_packing() -> None:
    shared = SharedPneumaCore()
    junction = JunctionAdapter(hidden_size=16, shared_core=shared, microsteps=4)
    model = FakeLanguageModel(junction)
    optimizer = torch.optim.SGD(junction.parameters(), lr=1e-3)
    loop = FoundationOptimizerLoop(
        model=model,
        optimizer=optimizer,
        junctions=(junction,),
        shared_core=shared,
        gradient_accumulation=1,
    )
    with pytest.raises(TrainingBatchError, match="packed documents"):
        loop.train_microbatch(
            model_inputs={"hidden": torch.randn(1, 2, 16)},
            forecast_targets=_targets(batch=1),
            document_count=2,
        )
    assert model.forward_calls == 0


def test_forecast_targets_require_observed_outcome_provenance() -> None:
    record = {
        "forecast_targets": {name: 0.0 for name in FORECAST_TARGETS},
        "forecast_target_provenance": {
            name: "observed_outcome" for name in FORECAST_TARGETS
        },
    }
    assert set(forecast_targets_from_record(record)) == set(FORECAST_TARGETS)
    record["forecast_target_provenance"]["intervention_response"] = "model_guess"
    with pytest.raises(TrainingBatchError, match="outcome-derived"):
        forecast_targets_from_record(record)

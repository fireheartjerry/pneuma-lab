"""The local optimizer performs one base call and bounded accumulation."""

from __future__ import annotations

import math

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
    forecast_tensors,
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


def _masks(batch: int = 2, *, action_success: bool | None = None) -> dict:
    if action_success is None:
        return {name: torch.ones(batch, dtype=torch.bool) for name in FORECAST_TARGETS}
    return {
        name: torch.full((batch,), name == "action_success", dtype=torch.bool)
        for name in FORECAST_TARGETS
    }


def _optimizer_loop(gradient_accumulation: int = 1):
    shared = SharedPneumaCore()
    junction = JunctionAdapter(hidden_size=16, shared_core=shared, microsteps=4)
    model = FakeLanguageModel(junction)
    for parameter in model.base.parameters():
        parameter.requires_grad = False
    optimizer = torch.optim.SGD(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=1e-3,
    )
    loop = FoundationOptimizerLoop(
        model=model,
        optimizer=optimizer,
        junctions=(junction,),
        shared_core=shared,
        gradient_accumulation=gradient_accumulation,
    )
    return loop, model


def _forecast_record() -> dict:
    return {
        "forecast_targets": {
            name: {
                "applicable": name == "action_success",
                "value": 1.0 if name == "action_success" else None,
                "provenance": (
                    "observed_outcome" if name == "action_success" else None
                ),
            }
            for name in FORECAST_TARGETS
        },
    }


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
        forecast_masks=_masks(),
        effective_weight=torch.tensor([1.0]),
        document_count=1,
    )
    assert first.optimizer_stepped is False
    second = loop.train_microbatch(
        model_inputs={"hidden": torch.randn(2, 3, 16)},
        forecast_targets=_targets(),
        forecast_masks=_masks(),
        effective_weight=torch.tensor([1.0]),
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
            forecast_masks=_masks(batch=1),
            effective_weight=torch.tensor([1.0]),
            document_count=2,
        )
    assert model.forward_calls == 0


def test_optimizer_uses_mask_and_authorized_effective_weight() -> None:
    loop, model = _optimizer_loop()
    step = loop.train_microbatch(
        model_inputs={"hidden": torch.randn(1, 3, 16)},
        forecast_targets=_targets(batch=1),
        forecast_masks=_masks(batch=1, action_success=True),
        effective_weight=torch.tensor([1.0]),
        document_count=1,
    )
    assert model.forward_calls == 1
    assert step.forecast_loss >= 0.0


@pytest.mark.parametrize(
    "weight",
    (
        torch.tensor([0.0]),
        torch.tensor([-1.0]),
        torch.tensor([math.nan]),
        torch.tensor([math.inf]),
        torch.tensor([-math.inf]),
        torch.tensor([1.0, 1.0]),
        torch.tensor([1], dtype=torch.long),
        torch.tensor([True]),
        1.0,
        None,
    ),
)
def test_optimizer_rejects_unauthorized_effective_weights(weight) -> None:
    loop, model = _optimizer_loop()
    with pytest.raises(TrainingBatchError, match="effective_weight"):
        loop.train_microbatch(
            model_inputs={"hidden": torch.randn(1, 3, 16)},
            forecast_targets=_targets(batch=1),
            forecast_masks=_masks(batch=1),
            effective_weight=weight,
            document_count=1,
        )
    assert model.forward_calls == 0


def test_effective_weight_scales_accumulated_gradients() -> None:
    gradients = {}
    for weight in (1.0, 2.0):
        torch.manual_seed(0)
        loop, model = _optimizer_loop(gradient_accumulation=2)
        torch.manual_seed(7)
        loop.train_microbatch(
            model_inputs={"hidden": torch.randn(1, 3, 16)},
            forecast_targets=_targets(batch=1),
            forecast_masks=_masks(batch=1),
            effective_weight=torch.tensor([weight]),
            document_count=1,
        )
        gradients[weight] = model.junction.down_projection.weight.grad.detach().clone()
    assert torch.allclose(gradients[2.0], 2.0 * gradients[1.0], rtol=1e-5, atol=1e-8)


def test_optimizer_resets_shared_state_before_each_base_forward() -> None:
    loop, model = _optimizer_loop(gradient_accumulation=2)
    entry_norms = []
    original_forward = model.forward

    def recording_forward(*, hidden, labels=None, use_cache=False):
        entry_norms.append(float(loop.shared_core.recurrent_state.abs().sum()))
        return original_forward(hidden=hidden, labels=labels, use_cache=use_cache)

    model.forward = recording_forward
    for _ in range(2):
        loop.train_microbatch(
            model_inputs={"hidden": torch.randn(1, 3, 16)},
            forecast_targets=_targets(batch=1),
            forecast_masks=_masks(batch=1),
            effective_weight=torch.tensor([1.0]),
            document_count=1,
        )
        assert float(loop.shared_core.recurrent_state.abs().sum()) > 0.0
    assert entry_norms == [0.0, 0.0]


def test_forecast_tensors_include_applicability_masks() -> None:
    record = _forecast_record()

    targets, masks = forecast_tensors(record)

    assert set(targets) == set(masks) == set(FORECAST_TARGETS)
    assert targets["action_success"].item() == 1.0
    assert masks["action_success"].item() is True
    assert targets["tool_cost"].item() == 0.0
    assert masks["tool_cost"].item() is False


def test_forecast_tensors_require_outcome_provenance_when_applicable() -> None:
    record = {
        "forecast_targets": {
            name: {
                "applicable": True,
                "value": 0.0,
                "provenance": "observed_outcome",
            }
            for name in FORECAST_TARGETS
        },
    }
    record["forecast_targets"]["intervention_response"]["provenance"] = "model_guess"
    with pytest.raises(TrainingBatchError, match="outcome-derived"):
        forecast_tensors(record)


@pytest.mark.parametrize("provenance", ([], {}))
def test_forecast_tensors_reject_malformed_applicable_provenance(provenance) -> None:
    record = _forecast_record()
    record["forecast_targets"]["action_success"]["provenance"] = provenance

    with pytest.raises(TrainingBatchError, match="outcome-derived"):
        forecast_tensors(record)


@pytest.mark.parametrize("value", (None, 1, "true"))
def test_forecast_tensors_require_boolean_applicability(value) -> None:
    record = _forecast_record()
    record["forecast_targets"]["action_success"]["applicable"] = value

    with pytest.raises(TrainingBatchError, match="applicable.*bool"):
        forecast_tensors(record)


@pytest.mark.parametrize(
    "value",
    (None, True, "1", math.nan, math.inf, -math.inf),
)
def test_forecast_tensors_require_finite_numeric_applicable_values(value) -> None:
    record = _forecast_record()
    record["forecast_targets"]["action_success"]["value"] = value

    with pytest.raises(TrainingBatchError, match="finite numeric value"):
        forecast_tensors(record)


@pytest.mark.parametrize("mutation", ("missing", "extra"))
def test_forecast_tensors_require_exact_entry_fields(mutation) -> None:
    record = _forecast_record()
    entry = record["forecast_targets"]["tool_cost"]
    if mutation == "missing":
        entry.pop("provenance")
    else:
        entry["extra"] = "forbidden"

    with pytest.raises(TrainingBatchError, match="exact fields"):
        forecast_tensors(record)


@pytest.mark.parametrize(
    ("field", "value"),
    (("value", 0.0), ("provenance", "observed_outcome")),
)
def test_forecast_tensors_require_null_masked_fields(field, value) -> None:
    record = _forecast_record()
    record["forecast_targets"]["tool_cost"][field] = value

    with pytest.raises(TrainingBatchError, match="masked.*null"):
        forecast_tensors(record)


def test_forecast_tensors_require_every_contract_entry() -> None:
    record = {
        "forecast_targets": {
            name: {
                "applicable": False,
                "value": None,
                "provenance": None,
            }
            for name in FORECAST_TARGETS[:-1]
        },
    }
    with pytest.raises(TrainingBatchError, match="all forecast target entries"):
        forecast_tensors(record)


def test_forecast_tensors_reject_extra_contract_entry() -> None:
    record = _forecast_record()
    record["forecast_targets"]["extra"] = {
        "applicable": False,
        "value": None,
        "provenance": None,
    }

    with pytest.raises(TrainingBatchError, match="all forecast target entries"):
        forecast_tensors(record)

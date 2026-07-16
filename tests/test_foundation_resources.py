"""Local RAM, VRAM, disk, thermal, and drift stop-rule classification."""

from __future__ import annotations

import pytest

from pneuma_lab.foundation.resources import ResourceGuard, ResourceSample


def _sample(**overrides) -> ResourceSample:
    values = {
        "sampled_at": 1_752_600_000.0,
        "gpu_temp_c": 70.0,
        "thermal_throttled": False,
        "process_vram_gb": 6.5,
        "reserved_vram_gb": 7.0,
        "global_vram_used_gb": 7.2,
        "global_vram_free_gb": 0.8,
        "process_ram_gb": 20.0,
        "system_ram_gb": 28.0,
        "gpu_utilization_percent": 97.0,
        "tokens_per_second": 25.0,
        "steps_per_second": 0.8,
        "power_watts": 80.0,
        "disk_free_gb": 40.0,
        "loss_finite": True,
    }
    values.update(overrides)
    return ResourceSample(**values)


def test_resource_guard_allows_healthy_local_training() -> None:
    decision = ResourceGuard().evaluate((_sample(),))
    assert decision.action == "continue"
    assert decision.reasons == ()


def test_resource_guard_pauses_over_temperature_or_memory() -> None:
    decision = ResourceGuard().evaluate(
        (_sample(gpu_temp_c=86.0, process_vram_gb=7.6, process_ram_gb=24.1),)
    )
    assert decision.action == "pause"
    assert set(decision.reasons) == {"gpu_temperature", "vram", "ram"}


def test_resource_guard_pauses_exactly_at_the_temperature_limit() -> None:
    assert ResourceGuard().evaluate((_sample(gpu_temp_c=85.0),)).action == "pause"
    assert ResourceGuard().evaluate((_sample(gpu_temp_c=84.9),)).action == "continue"


def test_resource_guard_requires_sustained_throttling() -> None:
    guard = ResourceGuard(sustained_throttle_samples=3)
    assert guard.evaluate((_sample(thermal_throttled=True),)).action == "continue"
    decision = guard.evaluate(tuple(_sample(thermal_throttled=True) for _ in range(3)))
    assert decision.action == "pause"
    assert decision.reasons == ("sustained_thermal_throttling",)


@pytest.mark.parametrize(
    ("sample", "action", "reason"),
    [
        (_sample(gpu_temp_c=86.0), "pause", "gpu_temperature"),
        (_sample(process_vram_gb=7.6), "pause", "vram"),
        (_sample(process_ram_gb=24.1), "pause", "ram"),
        (_sample(loss_finite=False), "fail", "non_finite_loss"),
        (_sample(disk_free_gb=1.0), "fail", "disk_risk"),
    ],
)
def test_resource_decisions_are_classified(sample, action, reason) -> None:
    decision = ResourceGuard().evaluate([sample])
    assert decision.action == action
    assert reason in decision.reasons


def test_resource_guard_fails_on_authorization_budget_or_regression_drift() -> None:
    guard = ResourceGuard()
    decision = guard.evaluate((_sample(),), authorization_unchanged=False)
    assert decision.action == "fail"
    assert decision.reasons == ("authorization_drift",)
    decision = guard.evaluate((_sample(),), budget_ok=False)
    assert decision.action == "fail"
    assert decision.reasons == ("budget_drift",)
    decision = guard.evaluate((_sample(),), regression_ok=False)
    assert decision.action == "fail"
    assert decision.reasons == ("regression_failure",)


def test_resource_guard_pauses_on_operator_interrupt() -> None:
    decision = ResourceGuard().evaluate((_sample(),), operator_interrupt=True)
    assert decision.action == "pause"
    assert decision.reasons == ("operator_interrupt",)


def test_resource_guard_reserves_checkpoint_disk_headroom() -> None:
    guard = ResourceGuard()
    healthy = guard.evaluate(
        (_sample(disk_free_gb=5.0),),
        checkpoint_required_gb=2.0,
    )
    assert healthy.action == "continue"
    decision = guard.evaluate(
        (_sample(disk_free_gb=5.0),),
        checkpoint_required_gb=4.0,
    )
    assert decision.action == "fail"
    assert decision.reasons == ("disk_risk",)


def test_resource_guard_fail_takes_precedence_over_pause() -> None:
    decision = ResourceGuard().evaluate((_sample(gpu_temp_c=86.0, loss_finite=False),))
    assert decision.action == "fail"
    assert {"non_finite_loss", "gpu_temperature"}.issubset(set(decision.reasons))


def test_resource_guard_fails_on_any_non_finite_loss_sample() -> None:
    decision = ResourceGuard().evaluate((_sample(loss_finite=False), _sample()))
    assert decision.action == "fail"
    assert "non_finite_loss" in decision.reasons


def test_resource_guard_pauses_without_any_sample() -> None:
    decision = ResourceGuard().evaluate(())
    assert decision.action == "pause"
    assert decision.reasons == ("missing_resource_sample",)


def test_resource_guard_rejects_non_positive_throttle_window() -> None:
    with pytest.raises(ValueError):
        ResourceGuard(sustained_throttle_samples=0)

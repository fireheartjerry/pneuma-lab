"""Local RAM, VRAM, latency, and thermal stop rules."""

from __future__ import annotations

from pneuma_lab.foundation.resources import ResourceGuard, ResourceSample


def _sample(**overrides) -> ResourceSample:
    values = {
        "gpu_temp_c": 70.0,
        "thermal_throttled": False,
        "vram_gb": 7.0,
        "ram_gb": 20.0,
        "tokens_per_second": 25.0,
        "power_watts": 80.0,
    }
    values.update(overrides)
    return ResourceSample(**values)


def test_resource_guard_allows_healthy_local_training() -> None:
    decision = ResourceGuard().evaluate((_sample(),))
    assert decision.pause is False
    assert decision.reasons == ()


def test_resource_guard_pauses_over_temperature_or_memory() -> None:
    decision = ResourceGuard().evaluate(
        (_sample(gpu_temp_c=86.0, vram_gb=7.6, ram_gb=24.1),)
    )
    assert decision.pause is True
    assert set(decision.reasons) == {"gpu_temperature", "vram", "ram"}


def test_resource_guard_requires_sustained_throttling() -> None:
    guard = ResourceGuard(sustained_throttle_samples=3)
    assert guard.evaluate((_sample(thermal_throttled=True),)).pause is False
    decision = guard.evaluate(tuple(_sample(thermal_throttled=True) for _ in range(3)))
    assert decision.pause is True
    assert decision.reasons == ("sustained_thermal_throttling",)

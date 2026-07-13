"""Local resource measurements and fail-closed pause decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pneuma_lab.foundation.specs import RUNTIME_LIMITS


@dataclass(frozen=True)
class ResourceSample:
    gpu_temp_c: float
    thermal_throttled: bool
    vram_gb: float
    ram_gb: float
    tokens_per_second: float
    power_watts: float | None = None


@dataclass(frozen=True)
class ResourceDecision:
    pause: bool
    reasons: tuple[str, ...]


class ResourceGuard:
    def __init__(
        self,
        *,
        max_gpu_temp_c: float = 85.0,
        sustained_throttle_samples: int = 3,
    ) -> None:
        if sustained_throttle_samples < 1:
            raise ValueError("sustained_throttle_samples must be positive")
        self.max_gpu_temp_c = max_gpu_temp_c
        self.sustained_throttle_samples = sustained_throttle_samples

    def evaluate(self, samples: Iterable[ResourceSample]) -> ResourceDecision:
        values = tuple(samples)
        if not values:
            return ResourceDecision(pause=True, reasons=("missing_resource_sample",))
        latest = values[-1]
        reasons: list[str] = []
        if latest.gpu_temp_c > self.max_gpu_temp_c:
            reasons.append("gpu_temperature")
        if latest.vram_gb > RUNTIME_LIMITS.max_vram_gb:
            reasons.append("vram")
        if latest.ram_gb > RUNTIME_LIMITS.max_ram_gb:
            reasons.append("ram")
        tail = values[-self.sustained_throttle_samples :]
        if len(tail) == self.sustained_throttle_samples and all(
            sample.thermal_throttled for sample in tail
        ):
            reasons.append("sustained_thermal_throttling")
        return ResourceDecision(pause=bool(reasons), reasons=tuple(reasons))

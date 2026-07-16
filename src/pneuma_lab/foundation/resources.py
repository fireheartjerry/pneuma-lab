"""Local resource measurements and fail-closed stop decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pneuma_lab.foundation.specs import RUNTIME_LIMITS


ACTION_CONTINUE = "continue"
ACTION_PAUSE = "pause"
ACTION_FAIL = "fail"

# Pause reasons: recoverable local pressure.
REASON_GPU_TEMPERATURE = "gpu_temperature"
REASON_VRAM = "vram"
REASON_RAM = "ram"
REASON_SUSTAINED_THERMAL_THROTTLING = "sustained_thermal_throttling"
REASON_OPERATOR_INTERRUPT = "operator_interrupt"
REASON_MISSING_RESOURCE_SAMPLE = "missing_resource_sample"

# Fail reasons: unrecoverable state.
REASON_NON_FINITE_LOSS = "non_finite_loss"
REASON_AUTHORIZATION_DRIFT = "authorization_drift"
REASON_DISK_RISK = "disk_risk"
REASON_BUDGET_DRIFT = "budget_drift"
REASON_REGRESSION_FAILURE = "regression_failure"

# Every reason ``ResourceGuard.evaluate`` can emit; the run-manifest schema's
# ``termination_reason`` enum is exactly this set plus ``"completed"``.
GUARD_REASONS = frozenset(
    {
        REASON_GPU_TEMPERATURE,
        REASON_VRAM,
        REASON_RAM,
        REASON_SUSTAINED_THERMAL_THROTTLING,
        REASON_OPERATOR_INTERRUPT,
        REASON_MISSING_RESOURCE_SAMPLE,
        REASON_NON_FINITE_LOSS,
        REASON_AUTHORIZATION_DRIFT,
        REASON_DISK_RISK,
        REASON_BUDGET_DRIFT,
        REASON_REGRESSION_FAILURE,
    }
)

# A safe checkpoint must always fit on disk with headroom to spare.
MIN_FREE_DISK_HEADROOM_GB = 2.0


@dataclass(frozen=True)
class ResourceSample:
    sampled_at: float
    gpu_temp_c: float
    thermal_throttled: bool
    process_vram_gb: float
    reserved_vram_gb: float
    global_vram_used_gb: float
    global_vram_free_gb: float
    process_ram_gb: float
    system_ram_gb: float
    gpu_utilization_percent: float
    tokens_per_second: float
    steps_per_second: float
    power_watts: float | None
    disk_free_gb: float
    loss_finite: bool = True


@dataclass(frozen=True)
class ResourceDecision:
    action: str
    reasons: tuple[str, ...]


class ResourceGuard:
    """Classify live samples into ``continue``, ``pause``, or ``fail``.

    ``pause`` covers recoverable local pressure (temperature, sustained
    throttling, process VRAM/RAM, an operator interrupt, or missing samples);
    ``fail`` covers unrecoverable state (non-finite loss, authorization or
    budget drift, regression failure, or checkpoint disk risk). ``fail``
    always takes precedence over ``pause``.
    """

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

    def evaluate(
        self,
        samples: Iterable[ResourceSample],
        *,
        authorization_unchanged: bool = True,
        operator_interrupt: bool = False,
        budget_ok: bool = True,
        regression_ok: bool = True,
        checkpoint_required_gb: float = 0.0,
    ) -> ResourceDecision:
        values = tuple(samples)
        fail_reasons: list[str] = []
        pause_reasons: list[str] = []

        if not authorization_unchanged:
            fail_reasons.append(REASON_AUTHORIZATION_DRIFT)
        if not budget_ok:
            fail_reasons.append(REASON_BUDGET_DRIFT)
        if not regression_ok:
            fail_reasons.append(REASON_REGRESSION_FAILURE)
        if operator_interrupt:
            pause_reasons.append(REASON_OPERATOR_INTERRUPT)

        if not values:
            pause_reasons.append(REASON_MISSING_RESOURCE_SAMPLE)
        else:
            latest = values[-1]
            if any(not sample.loss_finite for sample in values):
                fail_reasons.append(REASON_NON_FINITE_LOSS)
            required_gb = checkpoint_required_gb + MIN_FREE_DISK_HEADROOM_GB
            if latest.disk_free_gb < required_gb:
                fail_reasons.append(REASON_DISK_RISK)
            if latest.gpu_temp_c >= self.max_gpu_temp_c:
                pause_reasons.append(REASON_GPU_TEMPERATURE)
            if latest.process_vram_gb > RUNTIME_LIMITS.max_vram_gb:
                pause_reasons.append(REASON_VRAM)
            if latest.process_ram_gb > RUNTIME_LIMITS.max_ram_gb:
                pause_reasons.append(REASON_RAM)
            tail = values[-self.sustained_throttle_samples :]
            if len(tail) == self.sustained_throttle_samples and all(
                sample.thermal_throttled for sample in tail
            ):
                pause_reasons.append(REASON_SUSTAINED_THERMAL_THROTTLING)

        if fail_reasons:
            action = ACTION_FAIL
        elif pause_reasons:
            action = ACTION_PAUSE
        else:
            action = ACTION_CONTINUE
        return ResourceDecision(
            action=action,
            reasons=tuple(fail_reasons + pause_reasons),
        )

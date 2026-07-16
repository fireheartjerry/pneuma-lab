"""Live bounded resource sampling and recorded nvidia-smi parsing.

The sampler is a seam for the foundation runner: ``nvidia-smi`` is invoked
through an injectable runner callable and the torch/psutil probes are small
module-level functions, so tests never need a GPU or the foundation extras.
``torch`` and ``psutil`` are imported lazily inside those probes; importing
this module requires neither.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from pneuma_lab.foundation.resources import ResourceSample


NVIDIA_QUERY = (
    "memory.used,memory.free,temperature.gpu,power.draw,utilization.gpu,"
    "clocks_throttle_reasons.active"
)

_NVIDIA_FIELD_COUNT = 6
_MISSING_FIELD_VALUES = frozenset(
    {"[n/a]", "n/a", "[not supported]", "[unknown error]"}
)
_MIB_PER_GB = 1024.0
_BYTES_PER_GB = 1024.0**3
_NVIDIA_SMI_TIMEOUT_SECONDS = 30.0

# NVML nvmlClocksThrottleReasons bits (see nvml.h). Only slowdown bits count
# as thermal throttling: benign bits such as GpuIdle (0x1),
# ApplicationsClocksSetting (0x2), and SwPowerCap (0x4) are routinely active
# during normal full-load operation on power-limited GPUs and must never trip
# the sustained-thermal-throttling pause.
NVML_THROTTLE_HW_SLOWDOWN = 0x0000000000000008
NVML_THROTTLE_SW_THERMAL_SLOWDOWN = 0x0000000000000020
NVML_THROTTLE_HW_THERMAL_SLOWDOWN = 0x0000000000000040
NVML_THROTTLE_HW_POWER_BRAKE_SLOWDOWN = 0x0000000000000080
NVML_THERMAL_THROTTLE_MASK = (
    NVML_THROTTLE_HW_SLOWDOWN
    | NVML_THROTTLE_SW_THERMAL_SLOWDOWN
    | NVML_THROTTLE_HW_THERMAL_SLOWDOWN
    | NVML_THROTTLE_HW_POWER_BRAKE_SLOWDOWN
)


class TelemetryError(RuntimeError):
    """Raised when live telemetry cannot be read or parsed coherently."""


@dataclass(frozen=True)
class NvidiaSmiSample:
    """One parsed whole-GPU row from the pinned nvidia-smi query."""

    global_vram_used_gb: float
    global_vram_free_gb: float
    gpu_temp_c: float
    power_watts: float | None
    gpu_utilization_percent: float
    thermal_throttled: bool


def _parse_float(field: str, *, label: str) -> float:
    try:
        value = float(field)
    except ValueError as exc:
        raise TelemetryError(f"nvidia-smi {label} is not numeric: {field!r}") from exc
    if not math.isfinite(value):
        raise TelemetryError(f"nvidia-smi {label} is not finite: {field!r}")
    return value


def _parse_optional_float(field: str, *, label: str) -> float | None:
    if field.casefold() in _MISSING_FIELD_VALUES:
        return None
    return _parse_float(field, label=label)


def _parse_throttle_flag(field: str) -> bool:
    normalized = field.casefold()
    if normalized in _MISSING_FIELD_VALUES:
        return False
    if normalized == "active":
        return True
    if normalized == "not active":
        return False
    if normalized.startswith("0x"):
        try:
            bitmask = int(normalized, 16)
        except ValueError as exc:
            raise TelemetryError(
                f"nvidia-smi throttle bitmask is malformed: {field!r}"
            ) from exc
        return bool(bitmask & NVML_THERMAL_THROTTLE_MASK)
    raise TelemetryError(f"nvidia-smi throttle flag is not recognized: {field!r}")


def parse_nvidia_smi_line(line: str) -> NvidiaSmiSample:
    """Parse one ``csv,noheader,nounits`` row of the pinned NVIDIA_QUERY."""

    fields = [field.strip() for field in line.strip().split(",")]
    if len(fields) != _NVIDIA_FIELD_COUNT or not all(fields):
        raise TelemetryError(
            f"nvidia-smi line must have {_NVIDIA_FIELD_COUNT} non-empty fields: {line!r}"
        )
    return NvidiaSmiSample(
        global_vram_used_gb=_parse_float(fields[0], label="memory.used") / _MIB_PER_GB,
        global_vram_free_gb=_parse_float(fields[1], label="memory.free") / _MIB_PER_GB,
        gpu_temp_c=_parse_float(fields[2], label="temperature.gpu"),
        power_watts=_parse_optional_float(fields[3], label="power.draw"),
        gpu_utilization_percent=_parse_float(fields[4], label="utilization.gpu"),
        thermal_throttled=_parse_throttle_flag(fields[5]),
    )


def _run_nvidia_smi(command: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            list(command),
            check=True,
            capture_output=True,
            text=True,
            timeout=_NVIDIA_SMI_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise TelemetryError(f"nvidia-smi query failed: {exc}") from exc
    return completed.stdout


def read_nvidia_smi(
    query: str = NVIDIA_QUERY,
    *,
    runner: Callable[[Sequence[str]], str] | None = None,
) -> NvidiaSmiSample:
    """Read the first GPU row of ``query`` through an injectable runner."""

    command = [
        "nvidia-smi",
        f"--query-gpu={query}",
        "--format=csv,noheader,nounits",
    ]
    execute = runner if runner is not None else _run_nvidia_smi
    try:
        output = execute(command)
    except TelemetryError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise TelemetryError(f"nvidia-smi query failed: {exc}") from exc
    lines = [line for line in str(output).splitlines() if line.strip()]
    if not lines:
        raise TelemetryError("nvidia-smi returned no GPU rows")
    return parse_nvidia_smi_line(lines[0])


def _cuda_memory_bytes() -> tuple[int, int]:
    """Live process CUDA memory as ``(allocated, reserved)`` bytes."""

    try:
        import torch
    except ImportError as exc:  # pragma: no cover - optional dependency boundary
        raise TelemetryError(
            "live telemetry requires the foundation torch extra"
        ) from exc
    return int(torch.cuda.memory_allocated()), int(torch.cuda.memory_reserved())


def _process_memory_bytes() -> tuple[int, int]:
    """Live process RSS and system-wide used RAM in bytes."""

    try:
        import psutil
    except ImportError as exc:  # pragma: no cover - optional dependency boundary
        raise TelemetryError(
            "live telemetry requires the foundation psutil extra"
        ) from exc
    return int(psutil.Process().memory_info().rss), int(psutil.virtual_memory().used)


class LiveResourceSampler:
    """Bounded in-memory live resource sampling around one training run."""

    def __init__(
        self,
        *,
        output_root: Path,
        max_samples: int = 720,
        nvidia_smi_reader: Callable[[], NvidiaSmiSample] | None = None,
    ) -> None:
        if max_samples < 1:
            raise ValueError("max_samples must be positive")
        self.output_root = Path(output_root)
        self.samples: deque[ResourceSample] = deque(maxlen=max_samples)
        self.nvidia_smi_reader = nvidia_smi_reader

    def sample(
        self,
        *,
        tokens_per_second: float = 0.0,
        steps_per_second: float = 0.0,
        loss_finite: bool = True,
    ) -> ResourceSample:
        if self.nvidia_smi_reader is not None:
            global_sample = self.nvidia_smi_reader()
        else:
            global_sample = read_nvidia_smi(NVIDIA_QUERY)
        allocated_bytes, reserved_bytes = _cuda_memory_bytes()
        process_bytes, system_bytes = _process_memory_bytes()
        try:
            disk = shutil.disk_usage(self.output_root)
        except OSError as exc:
            raise TelemetryError(
                f"disk usage cannot be read for {self.output_root}: {exc}"
            ) from exc
        value = ResourceSample(
            sampled_at=time.time(),
            gpu_temp_c=global_sample.gpu_temp_c,
            thermal_throttled=global_sample.thermal_throttled,
            process_vram_gb=allocated_bytes / _BYTES_PER_GB,
            reserved_vram_gb=reserved_bytes / _BYTES_PER_GB,
            global_vram_used_gb=global_sample.global_vram_used_gb,
            global_vram_free_gb=global_sample.global_vram_free_gb,
            process_ram_gb=process_bytes / _BYTES_PER_GB,
            system_ram_gb=system_bytes / _BYTES_PER_GB,
            gpu_utilization_percent=global_sample.gpu_utilization_percent,
            tokens_per_second=float(tokens_per_second),
            steps_per_second=float(steps_per_second),
            power_watts=global_sample.power_watts,
            disk_free_gb=disk.free / _BYTES_PER_GB,
            loss_finite=bool(loss_finite),
        )
        self.samples.append(value)
        return value


def percentile(values: Iterable[float], fraction: float) -> float:
    """Nearest-rank percentile over a non-empty value set."""

    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise TelemetryError("percentile requires at least one value")
    if not 0.0 < fraction <= 1.0:
        raise TelemetryError("percentile fraction must be within (0, 1]")
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


def aggregate_telemetry(samples: Iterable[ResourceSample]) -> dict:
    """Aggregate bounded samples into the run-manifest telemetry section."""

    values = tuple(samples)
    if not values:
        raise TelemetryError("telemetry aggregation requires at least one sample")
    power = tuple(
        sample.power_watts for sample in values if sample.power_watts is not None
    )
    intervals = 0
    previously_throttled = False
    for sample in values:
        if sample.thermal_throttled and not previously_throttled:
            intervals += 1
        previously_throttled = sample.thermal_throttled
    return {
        "peak_process_vram_gb": max(sample.process_vram_gb for sample in values),
        "peak_reserved_vram_gb": max(sample.reserved_vram_gb for sample in values),
        "peak_global_vram_used_gb": max(
            sample.global_vram_used_gb for sample in values
        ),
        "peak_process_ram_gb": max(sample.process_ram_gb for sample in values),
        "peak_system_ram_gb": max(sample.system_ram_gb for sample in values),
        "peak_gpu_temp_c": max(sample.gpu_temp_c for sample in values),
        "peak_power_watts": max(power) if power else None,
        "thermal_throttle_intervals": intervals,
    }

"""Read-only WSL2 and optional-dependency readiness checks."""

from __future__ import annotations

import importlib.util
import platform
import sqlite3
import sys
from dataclasses import dataclass
from typing import Mapping

from pneuma_lab.foundation.specs import RUNTIME_LIMITS


@dataclass(frozen=True)
class EnvironmentProbe:
    system: str
    release: str
    python_version: tuple[int, int, int]
    cuda_available: bool
    gpu_total_vram_gb: float
    ram_gb: float
    fts5_available: bool
    dependencies: Mapping[str, bool]


def _fts5_available() -> bool:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
    except sqlite3.OperationalError:
        return False
    finally:
        connection.close()
    return True


def live_probe() -> EnvironmentProbe:
    """Inspect local capabilities without downloading or allocating a model."""

    cuda_available = False
    gpu_vram = 0.0
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    except ImportError:
        pass
    try:
        import psutil

        ram_gb = psutil.virtual_memory().total / (1024**3)
    except ImportError:
        ram_gb = 0.0
    multimodal = False
    try:
        import transformers

        multimodal = hasattr(transformers, "AutoModelForMultimodalLM")
    except ImportError:
        pass
    dependencies = {
        "torch": importlib.util.find_spec("torch") is not None,
        "transformers_multimodal": multimodal,
        "bitsandbytes": importlib.util.find_spec("bitsandbytes") is not None,
        "accelerate": importlib.util.find_spec("accelerate") is not None,
        "peft": importlib.util.find_spec("peft") is not None,
    }
    return EnvironmentProbe(
        system=platform.system(),
        release=platform.release(),
        python_version=(
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        ),
        cuda_available=cuda_available,
        gpu_total_vram_gb=gpu_vram,
        ram_gb=ram_gb,
        fts5_available=_fts5_available(),
        dependencies=dependencies,
    )


def doctor_report(probe: EnvironmentProbe) -> dict:
    blockers: list[str] = []
    if (
        probe.system.casefold() != "linux"
        or "microsoft" not in probe.release.casefold()
    ):
        blockers.append("wsl2_required")
    if probe.python_version < (3, 11, 0):
        blockers.append("python_3_11_required")
    if not probe.cuda_available:
        blockers.append("cuda_required")
    if probe.gpu_total_vram_gb < RUNTIME_LIMITS.max_vram_gb:
        blockers.append("insufficient_gpu_vram")
    if probe.ram_gb < RUNTIME_LIMITS.max_ram_gb:
        blockers.append("insufficient_ram")
    if not probe.fts5_available:
        blockers.append("sqlite_fts5_required")
    for name, available in probe.dependencies.items():
        if not available:
            blockers.append(f"missing_{name}")
    return {
        "ready": not blockers,
        "blockers": blockers,
        "environment": {
            "system": probe.system,
            "release": probe.release,
            "python_version": ".".join(str(value) for value in probe.python_version),
            "cuda_available": probe.cuda_available,
            "gpu_total_vram_gb": probe.gpu_total_vram_gb,
            "ram_gb": probe.ram_gb,
            "fts5_available": probe.fts5_available,
            "dependencies": dict(probe.dependencies),
        },
        "limits": {
            "process_vram_gb": RUNTIME_LIMITS.max_vram_gb,
            "process_ram_gb": RUNTIME_LIMITS.max_ram_gb,
        },
    }


def duration_hours(tokens: int, tokens_per_second: float) -> float:
    if tokens < 0 or tokens_per_second <= 0:
        raise ValueError("tokens must be non-negative and throughput positive")
    return tokens / tokens_per_second / 3600.0

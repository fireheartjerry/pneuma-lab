"""Read-only local and reproducibility-cloud readiness checks."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import math
import platform
import sqlite3
import sys
from dataclasses import dataclass, field
from typing import Mapping

from pneuma_lab.foundation.environment import (
    FOUNDATION_VERSION_PINS,
    MIN_USABLE_WSL_RAM_GB,
    PYTHON_SERIES,
    TRANSFORMERS_COMMIT,
)
from pneuma_lab.foundation.specs import RUNTIME_LIMITS


_DEPENDENCY_IMPORTS: Mapping[str, str] = {
    "torch": "torch",
    "torchvision": "torchvision",
    "bitsandbytes": "bitsandbytes",
    "accelerate": "accelerate",
    "peft": "peft",
    "psutil": "psutil",
    "pillow": "PIL",
    "safetensors": "safetensors",
    "huggingface_hub": "huggingface_hub",
}
_DISTRIBUTIONS: Mapping[str, str] = {
    "pillow": "Pillow",
    "huggingface-hub": "huggingface-hub",
}


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
    gpu_name: str = ""
    cuda_bf16_supported: bool = False
    transformers_commit: str | None = None
    bitsandbytes_cuda_available: bool = False
    dependency_versions: Mapping[str, str] = field(default_factory=dict)


def _fts5_available() -> bool:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
    except sqlite3.OperationalError:
        return False
    finally:
        connection.close()
    return True


def _distribution_version(name: str) -> str | None:
    distribution = _DISTRIBUTIONS.get(name, name)
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _transformers_metadata() -> tuple[bool, str | None]:
    try:
        import transformers
    except ImportError:
        return False, None
    multimodal = any(
        hasattr(transformers, name)
        for name in (
            "AutoModelForImageTextToText",
            "AutoModelForMultimodalLM",
        )
    )
    try:
        direct_url = importlib.metadata.distribution("transformers").read_text(
            "direct_url.json"
        )
        metadata = json.loads(direct_url) if direct_url is not None else {}
        commit = metadata.get("vcs_info", {}).get("commit_id")
    except (
        AttributeError,
        importlib.metadata.PackageNotFoundError,
        json.JSONDecodeError,
        TypeError,
    ):
        commit = None
    return multimodal, commit if isinstance(commit, str) else None


def _bitsandbytes_cuda_available() -> bool:
    try:
        from bitsandbytes.cextension import lib
    except (ImportError, OSError):
        return False
    return bool(getattr(lib, "compiled_with_cuda", False))


def live_probe() -> EnvironmentProbe:
    """Inspect capabilities without downloading or allocating a model."""

    cuda_available = False
    cuda_bf16_supported = False
    gpu_vram = 0.0
    gpu_name = ""
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        if cuda_available:
            properties = torch.cuda.get_device_properties(0)
            gpu_vram = properties.total_memory / (1024**3)
            gpu_name = torch.cuda.get_device_name(0)
            cuda_bf16_supported = bool(torch.cuda.is_bf16_supported())
    except (ImportError, RuntimeError):
        pass
    try:
        import psutil

        ram_gb = psutil.virtual_memory().total / (1024**3)
    except ImportError:
        ram_gb = 0.0
    multimodal, transformers_commit = _transformers_metadata()
    dependencies = {
        name: importlib.util.find_spec(import_name) is not None
        for name, import_name in _DEPENDENCY_IMPORTS.items()
    }
    dependencies["transformers_multimodal"] = multimodal
    versions = {
        name.replace("-", "_"): version
        for name in FOUNDATION_VERSION_PINS
        if (version := _distribution_version(name)) is not None
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
        gpu_name=gpu_name,
        cuda_bf16_supported=cuda_bf16_supported,
        transformers_commit=transformers_commit,
        bitsandbytes_cuda_available=_bitsandbytes_cuda_available(),
        dependency_versions=versions,
    )


def doctor_report(probe: EnvironmentProbe, *, profile: str = "local") -> dict:
    """Return deterministic readiness blockers for one supported profile."""

    if profile not in {"local", "cloud"}:
        return {
            "ready": False,
            "profile": profile,
            "blockers": ["invalid_profile"],
            "environment": {},
            "limits": {
                "process_vram_gb": RUNTIME_LIMITS.max_vram_gb,
                "process_ram_gb": RUNTIME_LIMITS.max_ram_gb,
            },
        }

    blockers: list[str] = []
    system = probe.system.casefold()
    release = probe.release.casefold()
    if profile == "local":
        if system != "linux" or "microsoft" not in release:
            blockers.append("wsl2_required")
    elif system != "linux":
        blockers.append("linux_required")
    if probe.python_version[:2] != PYTHON_SERIES:
        blockers.append("python_3_12_required")
    if not probe.cuda_available:
        blockers.append("cuda_required")
    if not probe.cuda_bf16_supported:
        blockers.append("cuda_bf16_required")
    minimum_vram = RUNTIME_LIMITS.max_vram_gb if profile == "local" else 40.0
    valid_vram = (
        type(probe.gpu_total_vram_gb) in {int, float}
        and math.isfinite(probe.gpu_total_vram_gb)
        and probe.gpu_total_vram_gb >= 0
    )
    if not valid_vram:
        blockers.append("invalid_gpu_vram")
    elif probe.gpu_total_vram_gb < minimum_vram:
        blockers.append("insufficient_gpu_vram")
    valid_ram = (
        type(probe.ram_gb) in {int, float}
        and math.isfinite(probe.ram_gb)
        and probe.ram_gb >= 0
    )
    if not valid_ram:
        blockers.append("invalid_ram")
    elif profile == "local" and probe.ram_gb < MIN_USABLE_WSL_RAM_GB:
        blockers.append("insufficient_ram")
    if profile == "cloud" and probe.gpu_name.casefold() != "nvidia a40":
        blockers.append("nvidia_a40_required")
    if not probe.fts5_available:
        blockers.append("sqlite_fts5_required")
    for name in (*FOUNDATION_VERSION_PINS, "transformers_multimodal"):
        probe_name = name.replace("-", "_")
        if not probe.dependencies.get(probe_name, False):
            blockers.append(f"missing_{probe_name}")
    for name, expected in FOUNDATION_VERSION_PINS.items():
        probe_name = name.replace("-", "_")
        if probe.dependency_versions.get(probe_name) != expected:
            blockers.append(f"dependency_version_mismatch_{probe_name}")
    if probe.transformers_commit != TRANSFORMERS_COMMIT:
        blockers.append("transformers_commit_mismatch")
    if not probe.bitsandbytes_cuda_available:
        blockers.append("bitsandbytes_cuda_required")
    return {
        "ready": not blockers,
        "profile": profile,
        "blockers": blockers,
        "environment": {
            "system": probe.system,
            "release": probe.release,
            "python_version": ".".join(
                str(value) for value in probe.python_version
            ),
            "cuda_available": probe.cuda_available,
            "cuda_bf16_supported": probe.cuda_bf16_supported,
            "gpu_name": probe.gpu_name,
            "gpu_total_vram_gb": probe.gpu_total_vram_gb,
            "ram_gb": probe.ram_gb,
            "fts5_available": probe.fts5_available,
            "dependencies": dict(probe.dependencies),
            "dependency_versions": dict(probe.dependency_versions),
            "transformers_commit": probe.transformers_commit,
            "bitsandbytes_cuda_available": probe.bitsandbytes_cuda_available,
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

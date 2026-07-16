"""WSL2 environment readiness and measured-duration estimates."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pneuma_lab.foundation.doctor import EnvironmentProbe, doctor_report, duration_hours
from pneuma_lab.foundation.__main__ import main


def _healthy_probe(**overrides) -> EnvironmentProbe:
    values = {
        "system": "Linux",
        "release": "5.15.153.1-microsoft-standard-WSL2",
        "python_version": (3, 12, 10),
        "cuda_available": True,
        "gpu_total_vram_gb": 8.0,
        "ram_gb": 22.0,
        "fts5_available": True,
        "dependencies": {
            "torch": True,
            "torchvision": True,
            "transformers_multimodal": True,
            "bitsandbytes": True,
            "accelerate": True,
            "peft": True,
            "psutil": True,
            "pillow": True,
            "safetensors": True,
            "huggingface_hub": True,
        },
        "gpu_name": "NVIDIA GeForce RTX 5060 Laptop GPU",
        "cuda_bf16_supported": True,
        "transformers_commit": "11ed2ff4df5fdfb3117f0e3365ef6ad94081ba69",
        "bitsandbytes_cuda_available": True,
        "dependency_versions": {
            "torch": "2.13.0",
            "torchvision": "0.28.0",
            "bitsandbytes": "0.49.2",
            "accelerate": "1.14.0",
            "peft": "0.19.1",
            "psutil": "7.2.2",
            "pillow": "12.3.0",
            "safetensors": "0.8.0",
            "huggingface_hub": "1.23.0",
        },
    }
    values.update(overrides)
    return EnvironmentProbe(**values)


def test_doctor_accepts_healthy_wsl2_local_stack() -> None:
    report = doctor_report(_healthy_probe(), profile="local")
    assert report["ready"] is True
    assert report["blockers"] == []
    assert report["limits"]["process_vram_gb"] == pytest.approx(7.5)
    assert report["limits"]["process_ram_gb"] == pytest.approx(24.0)


def test_doctor_fails_closed_outside_wsl_or_without_multimodal_transformers() -> None:
    report = doctor_report(
        _healthy_probe(
            system="Windows",
            release="11",
            dependencies={
                "torch": True,
                "torchvision": True,
                "transformers_multimodal": False,
                "bitsandbytes": True,
                "accelerate": True,
                "peft": True,
                "psutil": True,
                "pillow": True,
                "safetensors": True,
                "huggingface_hub": True,
            },
        )
    )
    assert report["ready"] is False
    assert "wsl2_required" in report["blockers"]
    assert "missing_transformers_multimodal" in report["blockers"]


def test_doctor_requires_exact_python_3_12_series() -> None:
    assert doctor_report(_healthy_probe(python_version=(3, 12, 0)))["ready"]
    report = doctor_report(_healthy_probe(python_version=(3, 14, 0)))
    assert report["ready"] is False
    assert "python_3_12_required" in report["blockers"]


def test_local_doctor_requires_wsl_ram_and_vram_at_exact_boundaries() -> None:
    assert doctor_report(_healthy_probe(ram_gb=22.0, gpu_total_vram_gb=7.5))["ready"]
    low_ram = doctor_report(_healthy_probe(ram_gb=21.999))
    low_vram = doctor_report(_healthy_probe(gpu_total_vram_gb=7.499))
    assert "insufficient_ram" in low_ram["blockers"]
    assert "insufficient_gpu_vram" in low_vram["blockers"]


def test_cloud_doctor_accepts_generic_linux_only_for_an_a40() -> None:
    cloud = _healthy_probe(
        release="6.8.0-generic",
        gpu_name="NVIDIA A40",
        gpu_total_vram_gb=44.5,
        ram_gb=1.0,
    )
    assert doctor_report(cloud, profile="cloud")["ready"] is True
    wrong_gpu = doctor_report(
        _healthy_probe(
            release="6.8.0-generic",
            gpu_name="NVIDIA RTX 6000 Ada Generation",
            gpu_total_vram_gb=48.0,
        ),
        profile="cloud",
    )
    assert wrong_gpu["ready"] is False
    assert "nvidia_a40_required" in wrong_gpu["blockers"]


def test_cloud_doctor_rejects_non_linux_and_invalid_profiles() -> None:
    non_linux = doctor_report(
        _healthy_probe(system="Windows", release="11"), profile="cloud"
    )
    assert non_linux["ready"] is False
    assert "linux_required" in non_linux["blockers"]
    invalid = doctor_report(_healthy_probe(), profile="serverless")
    assert invalid["ready"] is False
    assert invalid["blockers"] == ["invalid_profile"]


@pytest.mark.parametrize(
    ("changes", "blocker"),
    (
        ({"cuda_available": False}, "cuda_required"),
        ({"cuda_bf16_supported": False}, "cuda_bf16_required"),
        ({"transformers_commit": None}, "transformers_commit_mismatch"),
        ({"bitsandbytes_cuda_available": False}, "bitsandbytes_cuda_required"),
        ({"fts5_available": False}, "sqlite_fts5_required"),
        (
            {"dependency_versions": {"torch": "2.13.1"}},
            "dependency_version_mismatch_torch",
        ),
    ),
)
def test_doctor_fails_closed_on_acceleration_and_dependency_contracts(
    changes: dict,
    blocker: str,
) -> None:
    report = doctor_report(_healthy_probe(**changes))
    assert report["ready"] is False
    assert blocker in report["blockers"]


@pytest.mark.parametrize(
    ("changes", "blocker"),
    (
        ({"gpu_total_vram_gb": float("nan")}, "invalid_gpu_vram"),
        ({"ram_gb": float("inf")}, "invalid_ram"),
    ),
)
def test_doctor_rejects_nonfinite_capacity_measurements(
    changes: dict,
    blocker: str,
) -> None:
    report = doctor_report(_healthy_probe(**changes))
    assert report["ready"] is False
    assert blocker in report["blockers"]


def _healthy_probe_for_profile(profile: str, **overrides) -> EnvironmentProbe:
    if profile == "cloud":
        return _healthy_probe(
            release="6.8.0-generic",
            gpu_name="NVIDIA A40",
            gpu_total_vram_gb=48.0,
            **overrides,
        )
    return _healthy_probe(**overrides)


@pytest.mark.parametrize("profile", ("local", "cloud"))
@pytest.mark.parametrize(
    ("field_name", "blocker"),
    (
        ("cuda_available", "cuda_required"),
        ("cuda_bf16_supported", "cuda_bf16_required"),
        ("fts5_available", "sqlite_fts5_required"),
        ("bitsandbytes_cuda_available", "bitsandbytes_cuda_required"),
    ),
)
@pytest.mark.parametrize("non_bool", (1, "true", object(), None))
def test_doctor_rejects_non_bool_capability_fields(
    profile: str,
    field_name: str,
    blocker: str,
    non_bool,
) -> None:
    report = doctor_report(
        _healthy_probe_for_profile(profile, **{field_name: non_bool}),
        profile=profile,
    )
    assert report["ready"] is False
    assert blocker in report["blockers"]


@pytest.mark.parametrize("profile", ("local", "cloud"))
@pytest.mark.parametrize("non_bool", (1, "true", object(), None))
def test_doctor_rejects_non_bool_dependency_flags(
    profile: str,
    non_bool,
) -> None:
    baseline = _healthy_probe_for_profile(profile)
    for name in baseline.dependencies:
        dependencies = dict(baseline.dependencies)
        dependencies[name] = non_bool
        report = doctor_report(
            _healthy_probe_for_profile(profile, dependencies=dependencies),
            profile=profile,
        )
        assert report["ready"] is False
        assert f"missing_{name}" in report["blockers"]


@pytest.mark.parametrize("profile", ("local", "cloud"))
def test_doctor_rejects_missing_dependency_flags(profile: str) -> None:
    baseline = _healthy_probe_for_profile(profile)
    for name in baseline.dependencies:
        dependencies = dict(baseline.dependencies)
        dependencies.pop(name)
        report = doctor_report(
            _healthy_probe_for_profile(profile, dependencies=dependencies),
            profile=profile,
        )
        assert report["ready"] is False
        assert f"missing_{name}" in report["blockers"]


def test_duration_uses_measured_tokens_per_second() -> None:
    assert duration_hours(8_000_000, 20.0) == pytest.approx(111.1111, rel=1e-4)
    assert duration_hours(32_000_000, 50.0) == pytest.approx(177.7778, rel=1e-4)
    with pytest.raises(ValueError, match="positive"):
        duration_hours(100_000, 0.0)


def test_duration_cli_prints_hours_without_allocating_a_model(capsys) -> None:
    assert main(["duration", "--tokens", "8000000", "--tps", "20"]) == 0
    assert "111.11 hours" in capsys.readouterr().out


def test_doctor_cli_passes_the_selected_profile(capsys) -> None:
    probe = _healthy_probe(
        release="6.8.0-generic",
        gpu_name="NVIDIA A40",
        gpu_total_vram_gb=48.0,
    )
    with patch("pneuma_lab.foundation.cli.live_probe", return_value=probe):
        assert main(["doctor", "--profile", "cloud", "--json"]) == 0
    assert '"profile": "cloud"' in capsys.readouterr().out

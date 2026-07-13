"""WSL2 environment readiness and measured-duration estimates."""

from __future__ import annotations

import pytest

from pneuma_lab.foundation.doctor import EnvironmentProbe, doctor_report, duration_hours
from pneuma_lab.foundation.__main__ import main


def _healthy_probe(**overrides) -> EnvironmentProbe:
    values = {
        "system": "Linux",
        "release": "5.15.153.1-microsoft-standard-WSL2",
        "python_version": (3, 11, 9),
        "cuda_available": True,
        "gpu_total_vram_gb": 8.0,
        "ram_gb": 31.0,
        "fts5_available": True,
        "dependencies": {
            "torch": True,
            "transformers_multimodal": True,
            "bitsandbytes": True,
            "accelerate": True,
            "peft": True,
        },
    }
    values.update(overrides)
    return EnvironmentProbe(**values)


def test_doctor_accepts_healthy_wsl2_local_stack() -> None:
    report = doctor_report(_healthy_probe())
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
                "transformers_multimodal": False,
                "bitsandbytes": True,
                "accelerate": True,
                "peft": True,
            },
        )
    )
    assert report["ready"] is False
    assert "wsl2_required" in report["blockers"]
    assert "missing_transformers_multimodal" in report["blockers"]


def test_duration_uses_measured_tokens_per_second() -> None:
    assert duration_hours(8_000_000, 20.0) == pytest.approx(111.1111, rel=1e-4)
    assert duration_hours(32_000_000, 50.0) == pytest.approx(177.7778, rel=1e-4)
    with pytest.raises(ValueError, match="positive"):
        duration_hours(100_000, 0.0)


def test_duration_cli_prints_hours_without_allocating_a_model(capsys) -> None:
    assert main(["duration", "--tokens", "8000000", "--tps", "20"]) == 0
    assert "111.11 hours" in capsys.readouterr().out

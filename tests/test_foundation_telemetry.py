"""Recorded nvidia-smi parsing, bounded live sampling, and aggregation."""

from __future__ import annotations

from pathlib import Path

import pytest

from pneuma_lab.foundation import telemetry
from pneuma_lab.foundation.resources import ResourceSample
from pneuma_lab.foundation.telemetry import (
    NVIDIA_QUERY,
    LiveResourceSampler,
    NvidiaSmiSample,
    TelemetryError,
    aggregate_telemetry,
    parse_nvidia_smi_line,
    percentile,
    read_nvidia_smi,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "foundation"
    / "nvidia-smi-sample.csv"
)
TOTAL_FIXTURE_VRAM_GB = 8151 / 1024


def _global_sample(**overrides) -> NvidiaSmiSample:
    values = {
        "global_vram_used_gb": 3458 / 1024,
        "global_vram_free_gb": 4693 / 1024,
        "gpu_temp_c": 81.0,
        "power_watts": None,
        "gpu_utilization_percent": 92.0,
        "thermal_throttled": False,
    }
    values.update(overrides)
    return NvidiaSmiSample(**values)


def _resource_sample(**overrides) -> ResourceSample:
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


def test_nvidia_query_is_pinned() -> None:
    assert NVIDIA_QUERY == (
        "memory.used,memory.free,temperature.gpu,power.draw,utilization.gpu,"
        "clocks_throttle_reasons.active"
    )


def test_nvidia_smi_parser_accepts_missing_power_and_throttle() -> None:
    sample = parse_nvidia_smi_line("3458, 4693, 81, [N/A], 92, Not Active")
    assert sample.global_vram_used_gb == pytest.approx(3458 / 1024)
    assert sample.global_vram_free_gb == pytest.approx(4693 / 1024)
    assert sample.power_watts is None
    assert sample.thermal_throttled is False


def test_nvidia_smi_parser_reads_active_throttle_and_power() -> None:
    sample = parse_nvidia_smi_line("6144, 2007, 84, 118.42, 99, Active")
    assert sample.gpu_temp_c == 84.0
    assert sample.power_watts == pytest.approx(118.42)
    assert sample.gpu_utilization_percent == 99.0
    assert sample.thermal_throttled is True


def test_nvidia_smi_parser_reads_bitmask_throttle_reasons() -> None:
    active = parse_nvidia_smi_line("3458, 4693, 81, 96.5, 92, 0x0000000000000004")
    idle = parse_nvidia_smi_line("3458, 4693, 81, 96.5, 92, 0x0000000000000000")
    assert active.thermal_throttled is True
    assert idle.thermal_throttled is False


@pytest.mark.parametrize(
    "line",
    [
        "",
        "3458, 4693, 81",
        "3458, 4693, 81, [N/A], 92, Not Active, extra",
        "many, 4693, 81, [N/A], 92, Not Active",
        "3458, 4693, 81, [N/A], 92, Sometimes",
        "3458, 4693, , [N/A], 92, Not Active",
    ],
)
def test_nvidia_smi_parser_rejects_malformed_lines(line: str) -> None:
    with pytest.raises(TelemetryError):
        parse_nvidia_smi_line(line)


def test_recorded_fixture_parses_every_line() -> None:
    lines = [
        line
        for line in FIXTURE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    samples = [parse_nvidia_smi_line(line) for line in lines]
    assert len(samples) == 5
    assert samples[0].power_watts is None
    assert samples[0].thermal_throttled is False
    assert samples[1].thermal_throttled is True
    assert samples[1].power_watts == pytest.approx(118.42)
    assert samples[3].gpu_temp_c == 86.0
    assert samples[4].power_watts is None
    assert samples[4].thermal_throttled is False
    for sample in samples:
        assert sample.global_vram_used_gb + sample.global_vram_free_gb == (
            pytest.approx(TOTAL_FIXTURE_VRAM_GB)
        )


def test_read_nvidia_smi_builds_pinned_command_and_parses_first_gpu() -> None:
    commands: list[list[str]] = []

    def runner(command) -> str:
        commands.append(list(command))
        return FIXTURE_PATH.read_text(encoding="utf-8")

    sample = read_nvidia_smi(NVIDIA_QUERY, runner=runner)
    assert commands == [
        [
            "nvidia-smi",
            f"--query-gpu={NVIDIA_QUERY}",
            "--format=csv,noheader,nounits",
        ]
    ]
    assert sample == parse_nvidia_smi_line("3458, 4693, 81, [N/A], 92, Not Active")


def test_read_nvidia_smi_fails_closed_on_empty_or_failing_output() -> None:
    with pytest.raises(TelemetryError):
        read_nvidia_smi(NVIDIA_QUERY, runner=lambda command: "   \n")

    def failing(command) -> str:
        raise OSError("nvidia-smi is unavailable")

    with pytest.raises(TelemetryError):
        read_nvidia_smi(NVIDIA_QUERY, runner=failing)


def test_live_sampler_is_bounded_and_wires_measurements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        telemetry,
        "_cuda_memory_bytes",
        lambda: (2 * 1024**3, 3 * 1024**3),
    )
    monkeypatch.setattr(
        telemetry,
        "_process_memory_bytes",
        lambda: (4 * 1024**3, 10 * 1024**3),
    )
    sampler = LiveResourceSampler(
        output_root=tmp_path,
        max_samples=3,
        nvidia_smi_reader=lambda: _global_sample(
            power_watts=118.5,
            thermal_throttled=True,
        ),
    )
    for _ in range(5):
        value = sampler.sample(tokens_per_second=25.0, steps_per_second=0.8)
    assert len(sampler.samples) == 3
    assert value.process_vram_gb == pytest.approx(2.0)
    assert value.reserved_vram_gb == pytest.approx(3.0)
    assert value.process_ram_gb == pytest.approx(4.0)
    assert value.system_ram_gb == pytest.approx(10.0)
    assert value.global_vram_used_gb == pytest.approx(3458 / 1024)
    assert value.global_vram_free_gb == pytest.approx(4693 / 1024)
    assert value.gpu_temp_c == 81.0
    assert value.power_watts == 118.5
    assert value.thermal_throttled is True
    assert value.gpu_utilization_percent == 92.0
    assert value.tokens_per_second == 25.0
    assert value.steps_per_second == 0.8
    assert value.loss_finite is True
    assert value.sampled_at > 0
    assert value.disk_free_gb > 0


def test_live_sampler_defaults_to_pinned_nvidia_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queries: list[str] = []
    monkeypatch.setattr(telemetry, "_cuda_memory_bytes", lambda: (0, 0))
    monkeypatch.setattr(telemetry, "_process_memory_bytes", lambda: (0, 0))

    def fake_read(query: str) -> NvidiaSmiSample:
        queries.append(query)
        return _global_sample()

    monkeypatch.setattr(telemetry, "read_nvidia_smi", fake_read)
    sampler = LiveResourceSampler(output_root=tmp_path)
    value = sampler.sample(loss_finite=False)
    assert queries == [NVIDIA_QUERY]
    assert value.loss_finite is False
    assert sampler.samples[-1] is value


def test_live_sampler_rejects_non_positive_bounds(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        LiveResourceSampler(output_root=tmp_path, max_samples=0)


def test_aggregate_telemetry_reports_peaks_and_throttle_intervals() -> None:
    samples = (
        _resource_sample(thermal_throttled=False, power_watts=None),
        _resource_sample(
            thermal_throttled=True,
            gpu_temp_c=84.0,
            process_vram_gb=7.2,
            power_watts=121.0,
        ),
        _resource_sample(thermal_throttled=True, reserved_vram_gb=7.4),
        _resource_sample(
            thermal_throttled=False,
            global_vram_used_gb=7.9,
            process_ram_gb=21.5,
        ),
        _resource_sample(
            thermal_throttled=True,
            system_ram_gb=29.0,
            power_watts=96.0,
        ),
    )
    aggregate = aggregate_telemetry(samples)
    assert aggregate == {
        "peak_process_vram_gb": 7.2,
        "peak_reserved_vram_gb": 7.4,
        "peak_global_vram_used_gb": 7.9,
        "peak_process_ram_gb": 21.5,
        "peak_system_ram_gb": 29.0,
        "peak_gpu_temp_c": 84.0,
        "peak_power_watts": 121.0,
        "thermal_throttle_intervals": 2,
    }


def test_aggregate_telemetry_handles_missing_power() -> None:
    aggregate = aggregate_telemetry((_resource_sample(power_watts=None),))
    assert aggregate["peak_power_watts"] is None
    assert aggregate["thermal_throttle_intervals"] == 0


def test_aggregate_telemetry_rejects_empty_input() -> None:
    with pytest.raises(TelemetryError):
        aggregate_telemetry(())


def test_percentile_uses_nearest_rank() -> None:
    values = [5.0, 1.0, 4.0, 2.0, 3.0]
    assert percentile(values, 0.5) == 3.0
    assert percentile(values, 0.95) == 5.0
    assert percentile(values, 1.0) == 5.0
    assert percentile([7.5], 0.5) == 7.5


def test_percentile_rejects_empty_or_out_of_range_input() -> None:
    with pytest.raises(TelemetryError):
        percentile([], 0.5)
    with pytest.raises(TelemetryError):
        percentile([1.0], 0.0)
    with pytest.raises(TelemetryError):
        percentile([1.0], 1.5)

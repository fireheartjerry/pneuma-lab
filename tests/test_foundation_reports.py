"""Materialized run reports stay fixed-section, deterministic, claim-bounded."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.foundation.evaluation import evaluate_run
from pneuma_lab.foundation.reports import (
    REPORT_SECTIONS,
    ReportError,
    materialize_reports,
)


RUN_ID = "run-100k-smoke"


def _run_manifest(stage: str = "100k") -> dict:
    return {
        "manifest_kind": "pneuma_foundation_run",
        "manifest_schema_version": "0.2.0",
        "run_id": RUN_ID,
        "status": "completed",
        "mode": "train",
        "model": {
            "key": "2b",
            "model_id": "Qwen/Qwen3.5-2B",
            "revision": "15852e8c16360a2fea060d615a32b45270f8a8fc",
            "tokenizer_id": "Qwen/Qwen3.5-2B",
            "tokenizer_revision": "15852e8c16360a2fea060d615a32b45270f8a8fc",
        },
        "bindings": {
            "authorization_sha256": "0" * 64,
            "scope_digest": "1" * 64,
            "code_commit": "2" * 40,
            "shard_sha256": "3" * 64,
            "receipts": {"authorization": "4" * 64},
        },
        "training": {
            "token_ceiling": 100_000,
            "sequence_length": 512,
            "microbatch_size": 1,
            "gradient_accumulation": 32,
            "data_loader_workers": 8,
            "quantization": "nf4_double_quant",
            "seed": 7,
            "learning_rate": 0.0001,
        },
        "curriculum": {"stage": stage, "lane_weights": {"swe-verified": 1.0}},
        "limits": {"max_vram_gb": 7.5, "max_ram_gb": 24.0, "max_gpu_temp_c": 85.0},
        "progress": {
            "tokens_seen": 100_000,
            "optimizer_steps": 6,
            "microbatches_seen": 196,
            "wall_time_seconds": 1800.0,
            "tokens_per_second": 55.5,
        },
        "latency": {
            "base_p50_ms": 80.0,
            "base_p95_ms": 100.0,
            "core_p50_ms": 90.0,
            "core_p95_ms": 120.0,
        },
        "telemetry": {
            "peak_process_vram_gb": 6.9,
            "peak_reserved_vram_gb": 7.1,
            "peak_global_vram_used_gb": 7.3,
            "peak_process_ram_gb": 18.0,
            "peak_system_ram_gb": 21.0,
            "peak_gpu_temp_c": 79.0,
            "peak_power_watts": 180.0,
            "thermal_throttle_intervals": 0,
        },
        "validation": {"best_loss": 2.25, "last_loss": 2.25},
        "checkpoints": {"last_path": "checkpoints/step-6", "lineage": ["step-6"]},
        "termination_reason": "completed",
        "reports": {"index_path": None, "section_paths": {}},
        "budget": {"paid_compute_usd": 0.0, "cloud_jobs_used": 0},
    }


def _validation_batches() -> tuple[dict, ...]:
    return (
        {"validation_loss": 2.0, "forecast_mse": 0.5, "token_count": 300},
        {"validation_loss": 3.0, "forecast_mse": 0.25, "token_count": 100},
    )


def _evaluation_report(manifest: dict | None = None) -> dict:
    return evaluate_run(
        manifest if manifest is not None else _run_manifest(),
        validation_batches=_validation_batches(),
        estimated_flops_overhead=0.15,
    )


def test_reports_cannot_emit_level_or_consciousness_claims(tmp_path: Path) -> None:
    paths = materialize_reports(
        _run_manifest(),
        _evaluation_report(),
        output_root=tmp_path,
    )
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in paths.values()
    ).casefold()
    for forbidden in ("level 5", "level 6", "is conscious", "phenomenal consciousness"):
        assert forbidden not in combined


def test_reports_write_fixed_sections_and_index(tmp_path: Path) -> None:
    paths = materialize_reports(
        _run_manifest(),
        _evaluation_report(),
        output_root=tmp_path,
    )
    assert set(paths) == set(REPORT_SECTIONS) | {"index"}
    expected_directory = tmp_path / "foundation" / "runs" / RUN_ID / "reports"
    assert paths["index"] == expected_directory / "index.json"

    for section in REPORT_SECTIONS:
        payload = json.loads(paths[section].read_text(encoding="utf-8"))
        assert payload["report_kind"] == "pneuma_foundation_section_report"
        assert payload["run_id"] == RUN_ID
        assert payload["stage"] == "100k"
        assert payload["section"] == section
        assert payload["no_consciousness_claim"] is True

    index = json.loads(paths["index"].read_text(encoding="utf-8"))
    assert index["report_kind"] == "pneuma_foundation_report_index"
    assert index["sections"] == {
        section: f"{section}.json" for section in REPORT_SECTIONS
    }
    assert index["no_consciousness_claim"] is True
    assert index["claim_status"] == "engineering_and_precaution_only"

    capability = json.loads(paths["capability"].read_text(encoding="utf-8"))
    assert capability["body"]["regression_gate"]["passed"] is True
    assert "validation_loss" in capability["body"]["validation_metrics"]
    assert capability["body"]["throughput_tokens_per_second"] == 55.5

    causal = json.loads(paths["causal"].read_text(encoding="utf-8"))
    assert causal["body"]["falsification_gate"]["status"] == (
        "not_applicable_before_2m"
    )
    assert causal["body"]["parity"] == {"status": "not_measured"}

    governance = json.loads(paths["governance"].read_text(encoding="utf-8"))
    assert governance["body"]["run_status"] == "completed"
    assert governance["body"]["denied_action_classes"] == {"status": "not_measured"}

    memory = json.loads(paths["memory_integrity"].read_text(encoding="utf-8"))
    assert memory["body"]["resume_integrity"] == {"status": "not_measured"}
    assert memory["body"]["checkpoint_lineage_length"] == 1

    resource = json.loads(paths["resource"].read_text(encoding="utf-8"))
    assert resource["body"]["telemetry"]["peak_process_vram_gb"] == 6.9
    assert resource["body"]["limits"]["max_vram_gb"] == 7.5

    welfare = json.loads(paths["precautionary_welfare"].read_text(encoding="utf-8"))
    assert welfare["body"]["no_consciousness_claim"] is True
    assert welfare["body"]["claim_status"] == "engineering_and_precaution_only"


def test_reports_are_byte_deterministic(tmp_path: Path) -> None:
    first = materialize_reports(
        _run_manifest(),
        _evaluation_report(),
        output_root=tmp_path / "a",
    )
    second = materialize_reports(
        _run_manifest(),
        _evaluation_report(),
        output_root=tmp_path / "b",
    )
    assert set(first) == set(second)
    for name in first:
        assert first[name].read_bytes() == second[name].read_bytes()


def test_reports_reject_run_or_stage_mismatch(tmp_path: Path) -> None:
    report = _evaluation_report()

    renamed = _run_manifest()
    renamed["run_id"] = "run-other"
    with pytest.raises(ReportError, match="run_id"):
        materialize_reports(renamed, report, output_root=tmp_path)

    restaged = _run_manifest()
    restaged["curriculum"] = {"stage": "500k", "lane_weights": {"swe-verified": 1.0}}
    with pytest.raises(ReportError, match="stage"):
        materialize_reports(restaged, report, output_root=tmp_path)

    with pytest.raises(ReportError, match="report kind"):
        materialize_reports(_run_manifest(), {"run_id": RUN_ID}, output_root=tmp_path)

    assert not (tmp_path / "foundation").exists()


def test_reports_reject_unsafe_run_ids(tmp_path: Path) -> None:
    manifest = _run_manifest()
    manifest["run_id"] = "../evil"
    report = _evaluation_report()
    report["run_id"] = "../evil"
    with pytest.raises(ReportError, match="run_id"):
        materialize_reports(manifest, report, output_root=tmp_path)
    assert not (tmp_path / "foundation").exists()


def test_reports_fail_closed_on_claim_bearing_payloads(tmp_path: Path) -> None:
    poisoned = _evaluation_report()
    poisoned["checks"] = dict(poisoned["checks"])
    poisoned["checks"]["memory_integrity"] = {"note": "subject is conscious"}
    with pytest.raises(ReportError, match="forbidden claim text"):
        materialize_reports(_run_manifest(), poisoned, output_root=tmp_path)
    assert not (tmp_path / "foundation").exists()

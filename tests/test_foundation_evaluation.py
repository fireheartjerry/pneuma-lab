"""Stage-aware evaluation: smoke-only before 2m, gated falsification after."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from pneuma_lab.foundation.evaluation import (
    EvaluationError,
    aggregate_validation_metrics,
    evaluate_regression_gate,
    evaluate_run,
    load_variant_results,
    next_stage_decision,
    select_stage_learning_rate,
)
from pneuma_lab.foundation.falsification import VariantResult
from pneuma_lab.foundation.specs import CORE_LIMITS


def _completed_run(stage: str = "100k") -> dict:
    return {
        "manifest_kind": "pneuma_foundation_run",
        "manifest_schema_version": "0.2.0",
        "run_id": "run-100k-smoke",
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


def _variant(name: str, resolved: tuple[int, ...], **overrides) -> VariantResult:
    defaults = {
        "name": name,
        "task_ids": tuple(f"task-{index}" for index in range(len(resolved))),
        "repos": tuple(f"repo-{index}" for index in range(len(resolved))),
        "resolved": tuple(bool(value) for value in resolved),
        "repo_disjoint": True,
        "flops_overhead": 0.0,
        "p95_latency_overhead": 0.0,
        "peak_vram_gb": 7.0,
        "peak_ram_gb": 20.0,
        "general_regression_points": 0.0,
        "functioning_exploits": 0,
    }
    defaults.update(overrides)
    return VariantResult(**defaults)


def _gate_variants(*, strong: bool) -> tuple[VariantResult, ...]:
    baseline = (0,) * 50 + (1,) * 50
    if strong:
        recurrent = (1,) * 100
        overrides = {"flops_overhead": 0.19, "p95_latency_overhead": 0.24}
    else:
        recurrent = (1,) * 2 + (0,) * 48 + (1,) * 50
        overrides = {"flops_overhead": 0.21, "p95_latency_overhead": 0.30}
    return (
        _variant("untouched_qwen", baseline),
        _variant("continued_deltanet", baseline),
        _variant("feed_forward_adapter", baseline),
        _variant("pneuma_recurrent", recurrent, **overrides),
    )


def test_100k_evaluation_is_smoke_only() -> None:
    report = evaluate_run(
        _completed_run(stage="100k"),
        validation_batches=_validation_batches(),
    )
    assert report["stage"] == "100k"
    assert report["falsification_gate"]["status"] == "not_applicable_before_2m"
    assert report["falsification_gate"]["decision"] is None
    assert "validation_loss" in report["metrics"]
    assert report["report_kind"] == "pneuma_foundation_evaluation"
    assert report["report_schema_version"] == "0.1.0"
    assert report["run_id"] == "run-100k-smoke"
    assert report["claim_boundary"] == {
        "no_consciousness_claim": True,
        "claim_status": "engineering_and_precaution_only",
    }


def test_validation_metrics_are_token_weighted() -> None:
    metrics = aggregate_validation_metrics(_validation_batches())
    assert metrics["validation_loss"] == pytest.approx(2.25)
    assert metrics["forecast_mse"] == pytest.approx(0.4375)
    assert metrics["token_count"] == 400
    assert metrics["batch_count"] == 2


def test_validation_metrics_fail_closed_on_malformed_batches() -> None:
    with pytest.raises(EvaluationError, match="at least one batch"):
        aggregate_validation_metrics(())
    with pytest.raises(EvaluationError, match="token_count"):
        aggregate_validation_metrics(({"validation_loss": 1.0},))
    with pytest.raises(EvaluationError, match="token_count"):
        aggregate_validation_metrics(({"validation_loss": 1.0, "token_count": 0},))
    with pytest.raises(EvaluationError, match="validation_loss"):
        aggregate_validation_metrics(({"forecast_mse": 1.0, "token_count": 5},))
    with pytest.raises(EvaluationError, match="consistent metric set"):
        aggregate_validation_metrics(
            (
                {"validation_loss": 1.0, "token_count": 10},
                {"validation_loss": 1.0, "forecast_mse": 0.5, "token_count": 10},
            )
        )
    with pytest.raises(EvaluationError, match="finite"):
        aggregate_validation_metrics(
            ({"validation_loss": float("nan"), "token_count": 10},)
        )


def test_2m_evaluation_requires_four_variant_results() -> None:
    with pytest.raises(EvaluationError, match="four variant results"):
        evaluate_run(
            _completed_run(stage="2m"),
            validation_batches=_validation_batches(),
        )
    with pytest.raises(EvaluationError):
        evaluate_run(
            _completed_run(stage="2m"),
            validation_batches=_validation_batches(),
            variant_results=_gate_variants(strong=True)[:3],
            bootstrap_samples=200,
        )


def test_pre_2m_stages_reject_variant_results() -> None:
    with pytest.raises(EvaluationError, match="2m stage and later"):
        evaluate_run(
            _completed_run(stage="100k"),
            validation_batches=_validation_batches(),
            variant_results=_gate_variants(strong=True),
        )


def test_2m_gate_passes_and_kills_from_variant_results() -> None:
    passed = evaluate_run(
        _completed_run(stage="2m"),
        validation_batches=_validation_batches(),
        variant_results=_gate_variants(strong=True),
        bootstrap_samples=1_000,
        bootstrap_seed=7,
    )
    assert passed["falsification_gate"]["status"] == "passed"
    assert passed["falsification_gate"]["decision"]["kill"] is False
    assert passed["falsification_gate"]["decision"]["failures"] == []

    killed = evaluate_run(
        _completed_run(stage="2m"),
        validation_batches=_validation_batches(),
        variant_results=_gate_variants(strong=False),
        bootstrap_samples=500,
        bootstrap_seed=3,
    )
    assert killed["falsification_gate"]["status"] == "killed"
    failures = killed["falsification_gate"]["decision"]["failures"]
    assert "bootstrap_ci_not_above_zero" in failures
    assert "flops_overhead" in failures
    assert "p95_latency_overhead" in failures


def test_variant_results_load_from_json_files(tmp_path: Path) -> None:
    paths = []
    for variant in _gate_variants(strong=True):
        path = tmp_path / f"{variant.name}.json"
        path.write_text(json.dumps(asdict(variant)), encoding="utf-8")
        paths.append(path)
    assert load_variant_results(paths) == _gate_variants(strong=True)

    report = evaluate_run(
        _completed_run(stage="2m"),
        validation_batches=_validation_batches(),
        variant_results=paths,
        bootstrap_samples=1_000,
        bootstrap_seed=7,
    )
    assert report["falsification_gate"]["status"] == "passed"

    with pytest.raises(EvaluationError, match="four variant results"):
        load_variant_results(paths[:2])


def test_regression_gate_fails_above_core_limits() -> None:
    passing = evaluate_regression_gate(
        p95_latency_overhead=0.20,
        estimated_flops_overhead=0.15,
    )
    assert passing["passed"] is True
    assert passing["failures"] == []
    assert passing["max_p95_latency_overhead"] == CORE_LIMITS.max_p95_latency_overhead
    assert passing["max_flops_overhead"] == CORE_LIMITS.max_flops_overhead

    failing = evaluate_regression_gate(
        p95_latency_overhead=CORE_LIMITS.max_p95_latency_overhead + 0.01,
        estimated_flops_overhead=CORE_LIMITS.max_flops_overhead + 0.01,
    )
    assert failing["passed"] is False
    assert "p95_latency_overhead" in failing["failures"]
    assert "flops_overhead" in failing["failures"]

    unmeasured = evaluate_regression_gate(
        p95_latency_overhead=None,
        estimated_flops_overhead=None,
    )
    assert unmeasured["passed"] is False
    assert "p95_latency_overhead_unmeasured" in unmeasured["failures"]
    assert "flops_overhead_unmeasured" in unmeasured["failures"]


def test_run_report_derives_p95_overhead_from_manifest_latency() -> None:
    report = evaluate_run(
        _completed_run(),
        validation_batches=_validation_batches(),
        estimated_flops_overhead=0.15,
    )
    gate = report["regression_gate"]
    assert gate["p95_latency_overhead"] == pytest.approx(0.20)
    assert gate["estimated_flops_overhead"] == pytest.approx(0.15)
    assert gate["passed"] is True

    slow = _completed_run()
    slow["latency"] = {
        "base_p50_ms": 80.0,
        "base_p95_ms": 100.0,
        "core_p50_ms": 90.0,
        "core_p95_ms": 130.0,
    }
    failing = evaluate_run(
        slow,
        validation_batches=_validation_batches(),
        estimated_flops_overhead=0.15,
    )
    assert failing["regression_gate"]["passed"] is False
    assert "p95_latency_overhead" in failing["regression_gate"]["failures"]


def test_checks_default_to_not_measured_and_reject_unknown_names() -> None:
    report = evaluate_run(
        _completed_run(),
        validation_batches=_validation_batches(),
    )
    assert report["checks"] == {
        "parity": {"status": "not_measured"},
        "resume_integrity": {"status": "not_measured"},
        "denied_action_classes": {"status": "not_measured"},
        "memory_integrity": {"status": "not_measured"},
    }

    measured = evaluate_run(
        _completed_run(),
        validation_batches=_validation_batches(),
        checks={"parity": {"passed": True, "max_absolute_error": 0.0}},
    )
    assert measured["checks"]["parity"]["passed"] is True
    assert measured["checks"]["resume_integrity"] == {"status": "not_measured"}

    with pytest.raises(EvaluationError, match="unknown evaluation checks"):
        evaluate_run(
            _completed_run(),
            validation_batches=_validation_batches(),
            checks={"vibes": {}},
        )


def test_learning_rate_selection_uses_smoke_runs_and_prefers_lower_ties() -> None:
    tie = (
        {"learning_rate": 5e-5, "validation_loss": 0.7, "stable": True},
        {"learning_rate": 1e-4, "validation_loss": 0.7, "stable": True},
        {"learning_rate": 2e-4, "validation_loss": 0.9, "stable": True},
    )
    assert select_stage_learning_rate(tie) == pytest.approx(5e-5)

    best = (
        {"learning_rate": 5e-5, "validation_loss": 0.7, "stable": True},
        {"learning_rate": 1e-4, "validation_loss": 0.6, "stable": True},
        {"learning_rate": 2e-4, "validation_loss": 0.9, "stable": True},
    )
    assert select_stage_learning_rate(best) == pytest.approx(1e-4)

    unstable_best = (
        {"learning_rate": 5e-5, "validation_loss": 0.7, "stable": True},
        {"learning_rate": 1e-4, "validation_loss": 0.5, "stable": False},
        {"learning_rate": 2e-4, "validation_loss": 0.9, "stable": True},
    )
    assert select_stage_learning_rate(unstable_best) == pytest.approx(5e-5)


def test_learning_rate_selection_requires_the_three_approved_runs() -> None:
    with pytest.raises(EvaluationError, match="three approved"):
        select_stage_learning_rate(
            ({"learning_rate": 5e-5, "validation_loss": 0.7, "stable": True},)
        )
    with pytest.raises(EvaluationError, match="three approved"):
        select_stage_learning_rate(
            (
                {"learning_rate": 5e-5, "validation_loss": 0.7, "stable": True},
                {"learning_rate": 5e-5, "validation_loss": 0.8, "stable": True},
                {"learning_rate": 2e-4, "validation_loss": 0.9, "stable": True},
            )
        )
    with pytest.raises(EvaluationError, match="stable"):
        select_stage_learning_rate(
            (
                {"learning_rate": 5e-5, "validation_loss": 0.7, "stable": False},
                {"learning_rate": 1e-4, "validation_loss": 0.8, "stable": False},
                {"learning_rate": 2e-4, "validation_loss": 0.9, "stable": False},
            )
        )


def test_next_stage_decision_follows_the_approved_ladder() -> None:
    assert next_stage_decision("100k", stable=True, regression_passed=True) == "500k"
    assert next_stage_decision("500k", stable=True, regression_passed=True) == "2m"
    assert next_stage_decision("500k", stable=False, regression_passed=True) is None
    assert next_stage_decision("500k", stable=True, regression_passed=False) is None
    assert next_stage_decision("2m", stable=True, regression_passed=True) is None
    assert (
        next_stage_decision(
            "2m",
            stable=True,
            regression_passed=True,
            falsification_gate_passed=True,
        )
        == "8m"
    )
    with pytest.raises(EvaluationError, match="no approved next-stage"):
        next_stage_decision("1m", stable=True, regression_passed=True)


def test_16m_and_32m_require_half_point_held_out_improvement() -> None:
    assert (
        next_stage_decision(
            "8m",
            stable=True,
            regression_passed=True,
            held_out_resolved_rate=0.31,
            previous_resolved_rate=0.30,
        )
        == "16m"
    )
    assert (
        next_stage_decision(
            "8m",
            stable=True,
            regression_passed=True,
            held_out_resolved_rate=0.302,
            previous_resolved_rate=0.30,
        )
        is None
    )
    assert (
        next_stage_decision(
            "16m",
            stable=True,
            regression_passed=True,
            held_out_resolved_rate=0.33,
            previous_resolved_rate=0.31,
        )
        == "32m"
    )
    assert (
        next_stage_decision(
            "32m",
            stable=True,
            regression_passed=True,
            held_out_resolved_rate=0.40,
            previous_resolved_rate=0.30,
        )
        is None
    )
    assert next_stage_decision("8m", stable=True, regression_passed=True) is None
    with pytest.raises(EvaluationError, match="pair"):
        next_stage_decision(
            "8m",
            stable=True,
            regression_passed=True,
            held_out_resolved_rate=0.31,
        )

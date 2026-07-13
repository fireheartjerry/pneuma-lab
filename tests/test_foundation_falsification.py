"""The recurrent junction must earn its place against strong baselines."""

from __future__ import annotations

from pneuma_lab.foundation.falsification import (
    FalsificationDecision,
    VariantResult,
    evaluate_early_kill_gate,
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


def test_early_gate_promotes_only_a_significant_bounded_gain() -> None:
    # Fifty paired wins and no paired losses gives a lower CI above zero.
    baseline = (0,) * 50 + (1,) * 50
    recurrent = (1,) * 50 + (1,) * 50
    variants = (
        _variant("untouched_qwen", baseline),
        _variant("continued_deltanet", baseline),
        _variant("feed_forward_adapter", baseline),
        _variant(
            "pneuma_recurrent",
            recurrent,
            flops_overhead=0.19,
            p95_latency_overhead=0.24,
        ),
    )
    decision = evaluate_early_kill_gate(variants, bootstrap_samples=1_000, seed=7)
    assert isinstance(decision, FalsificationDecision)
    assert decision.kill is False
    assert decision.strongest_baseline == "continued_deltanet"
    assert decision.absolute_improvement == 0.5
    assert decision.ci95_lower > 0.0
    assert decision.failures == ()


def test_early_gate_kills_a_small_or_resource_breaching_gain() -> None:
    baseline = (0,) * 50 + (1,) * 50
    recurrent = (1,) * 2 + (0,) * 48 + (1,) * 50
    variants = (
        _variant("untouched_qwen", baseline),
        _variant("continued_deltanet", baseline),
        _variant("feed_forward_adapter", baseline),
        _variant(
            "pneuma_recurrent",
            recurrent,
            flops_overhead=0.21,
            p95_latency_overhead=0.30,
        ),
    )
    decision = evaluate_early_kill_gate(variants, bootstrap_samples=500, seed=3)
    assert decision.kill is True
    assert "bootstrap_ci_not_above_zero" in decision.failures
    assert "flops_overhead" in decision.failures
    assert "p95_latency_overhead" in decision.failures


def test_early_gate_fails_closed_on_non_disjoint_or_exploit_results() -> None:
    baseline = (0,) * 20
    recurrent = (1,) * 20
    decision = evaluate_early_kill_gate(
        (
            _variant("untouched_qwen", baseline),
            _variant("continued_deltanet", baseline),
            _variant("feed_forward_adapter", baseline),
            _variant(
                "pneuma_recurrent",
                recurrent,
                repo_disjoint=False,
                functioning_exploits=1,
            ),
        ),
        bootstrap_samples=200,
        seed=1,
    )
    assert decision.kill is True
    assert "repo_disjointness" in decision.failures
    assert "functioning_exploit" in decision.failures

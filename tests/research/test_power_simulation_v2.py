from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.statistics.power import (
    PriorAnchorError,
    build_prior_grid,
    create_prior_anchor_payload,
    evaluate_selected_tier,
    load_prior_anchor,
    module_sha256,
    monte_carlo_interval,
    select_utility_scope,
    simulate_power,
)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _anchor_payload() -> dict[str, object]:
    return {
        "schema_version": "pneuma-p0-prior-anchor/1.0.0",
        "kind": "governed_prior_anchor",
        "code_sha256": module_sha256(),
        "adapter_reports": [
            {
                "adapter": "open-swe-traces",
                "adapter_version": "0.1.0",
                "report_sha256": "1" * 64,
                "failure_rate": 0.60,
            },
            {
                "adapter": "openhands-sampled",
                "adapter_version": "0.1.0",
                "report_sha256": "2" * 64,
                "failure_rate": 0.90,
            },
            {
                "adapter": "openhands-verifier",
                "adapter_version": "0.1.0",
                "report_sha256": "3" * 64,
                "failure_rate": 0.50,
            },
        ],
        "failure_anchor": 0.60,
        "recurrence_bridge": [
            {"value": 0.25, "weight": 0.25},
            {"value": 0.50, "weight": 0.50},
            {"value": 0.75, "weight": 0.25},
        ],
        "base_harm_support": [
            {"value": 0.15, "weight": 0.25},
            {"value": 0.30, "weight": 0.50},
            {"value": 0.45, "weight": 0.25},
        ],
        "prior_grid": {
            "paired_discordance": [
                {"value": 0.15, "weight": 0.15},
                {"value": 0.20, "weight": 0.35},
                {"value": 0.30, "weight": 0.35},
                {"value": 0.40, "weight": 0.15},
            ],
            "lineage_icc": [
                {"value": 0.05, "weight": 1 / 3},
                {"value": 0.15, "weight": 1 / 3},
                {"value": 0.30, "weight": 1 / 3},
            ],
            "cross_component_correlation": [
                {"value": 0.25, "weight": 1 / 3},
                {"value": 0.50, "weight": 1 / 3},
                {"value": 0.75, "weight": 1 / 3},
            ],
            "nuisance_profiles": [
                {
                    "attrition": 0.00,
                    "evaluator_error": 0.00,
                    "utility_event_rate": 0.05,
                    "utility_discordance": 0.05,
                    "weight": 1 / 3,
                },
                {
                    "attrition": 0.025,
                    "evaluator_error": 0.05,
                    "utility_event_rate": 0.15,
                    "utility_discordance": 0.15,
                    "weight": 1 / 3,
                },
                {
                    "attrition": 0.05,
                    "evaluator_error": 0.10,
                    "utility_event_rate": 0.30,
                    "utility_discordance": 0.30,
                    "weight": 1 / 3,
                },
            ],
        },
    }


def _write_anchor(path: Path) -> str:
    path.write_bytes(_canonical_bytes(_anchor_payload()))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_prior_anchor_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "prior-anchor.json"
    path.write_bytes(_canonical_bytes({"schema_version": "pneuma-p0-prior/1.0"}))

    with pytest.raises(PriorAnchorError, match="digest mismatch"):
        load_prior_anchor(path, expected_sha256="0" * 64)

    assert hashlib.sha256(path.read_bytes()).hexdigest() != "0" * 64


def test_resigned_but_internally_inconsistent_anchor_fails_closed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "prior-anchor.json"
    payload = _anchor_payload()
    payload["failure_anchor"] = 0.70
    path.write_bytes(_canonical_bytes(payload))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    with pytest.raises(PriorAnchorError, match="failure anchor"):
        load_prior_anchor(path, expected_sha256=digest)


def test_prior_grid_is_exactly_governed_and_renormalized(tmp_path: Path) -> None:
    path = tmp_path / "prior-anchor.json"
    digest = _write_anchor(path)

    anchor = load_prior_anchor(path, expected_sha256=digest)
    grid = build_prior_grid(anchor, delta_power=0.10)

    assert grid.pre_rejection_count == 324
    assert all(cell.paired_discordance != 0.10 for cell in grid.cells)
    assert grid.rejected_count > 0
    assert sum(cell.weight for cell in grid.cells) == pytest.approx(1.0)


def test_selected_tier_reruns_iut_and_simultaneous_bound_rule() -> None:
    blocked_by_iut = evaluate_selected_tier(
        h1_component_pvalues={"repeat_harm:base": 0.01, "utility:success": 0.06},
        h2_component_pvalues={"influence_off": 0.01, "full_state_clamp": 0.01},
        behavior_estimates={"repeat_harm:base": 0.08},
        behavior_lower_bounds={"repeat_harm:base": 0.02},
    )
    assert blocked_by_iut.p_h1t == 0.06
    assert blocked_by_iut.p_h2t == 0.01
    assert blocked_by_iut.p_selected == 0.06
    assert blocked_by_iut.passed is False

    blocked_by_bound = evaluate_selected_tier(
        h1_component_pvalues={"repeat_harm:base": 0.01, "utility:success": 0.01},
        h2_component_pvalues={"influence_off": 0.01, "full_state_clamp": 0.01},
        behavior_estimates={"repeat_harm:base": 0.08},
        behavior_lower_bounds={"repeat_harm:base": 0.0},
    )
    assert blocked_by_bound.p_selected == 0.01
    assert blocked_by_bound.passed is False
    assert blocked_by_bound.failure_reason == "simultaneous_lower_bound"


def test_power_simulation_is_joint_deterministic_and_reports_required_fields(
    tmp_path: Path,
) -> None:
    path = tmp_path / "prior-anchor.json"
    digest = _write_anchor(path)
    anchor = load_prior_anchor(path, expected_sha256=digest)
    arguments = {
        "anchor": anchor,
        "seed": 20260724,
        "initial_draws": 256,
        "adaptive_draws": 512,
        "support_counts": (24, 32, 48),
        "delta_values": (0.10,),
        "adapt": False,
    }

    first = simulate_power(**arguments)
    second = simulate_power(**arguments)

    assert first == second
    assert first["config"]["common_random_numbers"] is True
    assert first["config"]["selected_support"] == 48
    assert first["config"]["highlighted_support"] == [24, 32, 48, 64, 80, 96]
    selected = first["results"]["0.10"]["48"]
    assert set(selected) == {"U0", "U1"}
    for scope in selected.values():
        probabilities = scope["tier_probabilities"]
        assert sum(probabilities.values()) == 1.0
        assert all(0.0 <= value <= 1.0 for value in probabilities.values())
        assert set(probabilities) == {"core", "floor", "no-go"}
        assert set(scope["monte_carlo_uncertainty"]) == {
            "core",
            "floor",
            "no-go",
        }
        for tier in ("core", "floor"):
            summary = scope["tiers"][tier]
            assert summary["conjunction_power"] <= min(
                summary["component_marginal_power"].values()
            ) + 1e-12
            assert summary["component_most_responsible_for_failure"]
        assert scope["cell_draws"]["surviving_grid_cells"] == first["grid"][
            "0.10"
        ]["surviving_cells"]
    assert first["selection"]["delta_power"] == 0.10
    assert first["selection"]["support"] == 48


def test_adaptive_interval_and_utility_ladder_are_frozen() -> None:
    low, high = monte_carlo_interval(8_000, 10_000)
    assert low < 0.80 < high
    assert select_utility_scope(0.40, 1.00) == ("U0", "proceed")
    assert select_utility_scope(0.41, 0.40) == ("U1", "proceed")
    assert select_utility_scope(0.41, 0.41) == (None, "P0 no-go")


def test_prior_anchor_payload_uses_median_adapter_failure_and_bridge() -> None:
    records = [
        {
            "adapter": "open-swe-traces",
            "adapter_version": "0.1.0",
            "report_sha256": "1" * 64,
            "resolved_true": 40,
            "resolved_false": 60,
        },
        {
            "adapter": "openhands-sampled",
            "adapter_version": "0.1.0",
            "report_sha256": "2" * 64,
            "resolved_true": 10,
            "resolved_false": 90,
        },
        {
            "adapter": "openhands-verifier",
            "adapter_version": "0.1.0",
            "report_sha256": "3" * 64,
            "resolved_true": 50,
            "resolved_false": 50,
        },
    ]

    payload = create_prior_anchor_payload(records)

    assert payload["failure_anchor"] == pytest.approx(0.60)
    assert [row["value"] for row in payload["base_harm_support"]] == pytest.approx(
        [0.15, 0.30, 0.45]
    )
    assert payload["prior_grid"]["paired_discordance"][0]["value"] == 0.15

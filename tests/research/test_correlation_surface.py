from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.statistics.correlation_surface import (
    CORRELATION_GRID,
    SURFACE_SCHEMA_VERSION,
    IndependenceValidationError,
    build_correlation_surface,
    equicorrelation_eigenvalues,
    validate_independence,
    write_surface_artifact,
)
from pneuma_lab.statistics.power import COMPONENT_COUNT


REPO_ROOT = Path(__file__).parents[2]
ARTIFACT_ROOT = REPO_ROOT / "build" / "research" / "neurips-p0"
SEALED_REPORT = ARTIFACT_ROOT / "p0-power-report.json"
PRIOR_ANCHOR = ARTIFACT_ROOT / "prior-anchor.json"


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


@pytest.fixture(scope="module")
def deterministic_surfaces() -> tuple[dict[str, object], dict[str, object]]:
    arguments = {
        "anchor_path": PRIOR_ANCHOR,
        "sealed_report_path": SEALED_REPORT,
        "seed": 20260724,
        "initial_draws": 10_000,
        "adaptive_draws": 10_000,
        "support_counts": (48,),
        "delta_values": (0.10,),
        "correlations": CORRELATION_GRID,
        "adapt": False,
    }
    return build_correlation_surface(**arguments), build_correlation_surface(**arguments)


def test_extended_grid_is_positive_definite_at_largest_component_count() -> None:
    assert CORRELATION_GRID == (0.0, 0.25, 0.50, 0.75, 0.99)
    for rho in CORRELATION_GRID:
        smallest, largest = equicorrelation_eigenvalues(rho, COMPONENT_COUNT)
        assert smallest > 0.0
        assert largest > 0.0


def test_rho_zero_matches_closed_form_within_monte_carlo_error(
    deterministic_surfaces: tuple[dict[str, object], dict[str, object]],
) -> None:
    surface, _ = deterministic_surfaces
    receipt = surface["rho_zero_closed_form_validation"]

    assert receipt["status"] == "passed"
    assert receipt["failed_comparisons"] == 0
    assert receipt["comparisons"] > 0
    assert receipt["worst_case"]["absolute_discrepancy"] <= receipt["worst_case"][
        "monte_carlo_error_allowance"
    ]
    for row in surface["surface"]:
        if row["rho"] == 0.0:
            assert abs(row["joint_power"] - row["product_bound"]) <= row[
                "rho_zero_monte_carlo_error_allowance"
            ]


def test_surface_is_deterministic_digest_bound_and_has_compact_brackets(
    deterministic_surfaces: tuple[dict[str, object], dict[str, object]],
) -> None:
    first, second = deterministic_surfaces

    assert first == second
    assert first["schema_version"] == SURFACE_SCHEMA_VERSION
    assert first["does_not_supersede_or_amend_sealed_p0_no_go"] is True
    assert first["sealed_p0"]["config_sha256"] == (
        "3cc405670078ad4d57737a4b1224a0afac5362e9f35fb937dee3224bf77120cc"
    )
    assert first["config"]["training_weight"] == 0.0
    assert first["config"]["utility_scopes"] == ["U0", "U1"]
    assert first["config"]["correlations"] == list(CORRELATION_GRID)

    for scope in ("U0", "U1"):
        for tier in ("core", "floor"):
            bracket = first["brackets"][scope][tier]
            assert bracket["G"] == 48
            assert bracket["delta_power"] == 0.10
            assert set(bracket["swept_joint_power"]) == {
                f"{rho:.2f}" for rho in CORRELATION_GRID
            }
            assert bracket["product_bound"] <= bracket["min_marginal_bound"]
            assert 0.0 <= bracket["sealed_weighted_average"] <= 1.0

    payload = dict(first)
    observed_digest = payload.pop("artifact_sha256")
    assert hashlib.sha256(_canonical_bytes(payload)).hexdigest() == observed_digest


def test_writing_surface_leaves_sealed_report_byte_identical(
    tmp_path: Path,
    deterministic_surfaces: tuple[dict[str, object], dict[str, object]],
) -> None:
    before_report = SEALED_REPORT.read_bytes()
    before_anchor = PRIOR_ANCHOR.read_bytes()
    destination = tmp_path / "p0-correlation-surface.json"

    write_surface_artifact(
        deterministic_surfaces[0],
        output_path=destination,
        sealed_report_path=SEALED_REPORT,
        anchor_path=PRIOR_ANCHOR,
    )

    assert destination.read_bytes() == _canonical_bytes(deterministic_surfaces[0])
    assert SEALED_REPORT.read_bytes() == before_report
    assert PRIOR_ANCHOR.read_bytes() == before_anchor


def test_independence_validation_fails_closed_on_material_discrepancy() -> None:
    comparisons = [
        {
            "coordinate": {"delta_power": 0.10, "G": 48, "scope": "U1", "tier": "floor"},
            "draws": 10_000,
            "joint_power": 0.30,
            "product_bound": 0.10,
            "component_marginal_power": {"a": 0.5, "b": 0.2},
        }
    ]

    with pytest.raises(IndependenceValidationError, match="rho=0 closed-form"):
        validate_independence(comparisons)

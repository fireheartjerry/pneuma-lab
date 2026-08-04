from __future__ import annotations

import pytest

from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.power import select_roster_tier


def _rows(*, lower: float, upper: float) -> list[dict[str, object]]:
    return [
        {"family": "alternative", "lower": lower, "upper": 1.0},
        {"family": "null_both", "lower": 0.0, "upper": upper},
        {"family": "null_content", "lower": 0.0, "upper": upper},
        {"family": "null_excess", "lower": 0.0, "upper": upper},
    ]


def test_registered_rule_prefers_c160_when_both_tiers_pass() -> None:
    assert select_roster_tier({120: _rows(lower=0.80, upper=0.05), 160: _rows(lower=0.80, upper=0.05)}) == "C160"


def test_registered_rule_falls_back_to_c120() -> None:
    assert select_roster_tier({120: _rows(lower=0.80, upper=0.05), 160: _rows(lower=0.79, upper=0.05)}) == "C120"


def test_registered_rule_emits_formal_no_go_without_efficacy_fallback() -> None:
    assert select_roster_tier({120: _rows(lower=0.79, upper=0.05), 160: _rows(lower=0.79, upper=0.06)}) == "FEASIBILITY_NO_GO"


@pytest.mark.parametrize(
    "value",
    [
        {120: _rows(lower=0.80, upper=0.05)},
        {120: _rows(lower=0.80, upper=0.05), 160: []},
        {120: _rows(lower=0.80, upper=0.05), 160: _rows(lower=float("nan"), upper=0.05)},
        {120: [{"family": "alternative", "lower": 0.8, "upper": 1.0}], 160: _rows(lower=0.8, upper=0.05)},
    ],
)
def test_registered_rule_rejects_malformed_or_digestless_tier_input(value) -> None:
    with pytest.raises(RecordValidationError):
        select_roster_tier(value)


def test_cli_exposes_roster_finalization_arms_without_running_them() -> None:
    from pneuma_lab.resampling_null.cli import _parser

    args = _parser().parse_args(
        [
            "--run-root",
            "/tmp/pneuma-tier-test",
            "power",
            "finalize",
            "--authority",
            "authority.json",
            "--grid-ref",
            "grid.json",
            "--screen-topology-ref",
            "topology.json",
            "--tier",
            "120",
            "--out",
            "final.json",
            "--completed-roster-bound",
            "--tier-receipt",
            "both-tier-receipt.json",
        ]
    )
    assert args.completed_roster_bound is True
    assert args.tier == 120
    assert args.tier_receipt == "both-tier-receipt.json"

from __future__ import annotations

import pytest

from pneuma_lab.rapid_campaign.spend import SpendError, SpendLedger


def test_campaign_and_version_ceiling_use_the_tighter_bound() -> None:
    ledger = SpendLedger(ceiling_microusd=7_500_000_000)
    ledger.reserve(
        "r2-build",
        version_id="r2",
        amount_microusd=5_000_000_000,
        version_ceiling_microusd=5_100_000_000,
    )
    with pytest.raises(SpendError, match="version ceiling"):
        ledger.reserve(
            "r2-extra",
            version_id="r2",
            amount_microusd=100_000_001,
            version_ceiling_microusd=5_100_000_000,
        )
    ledger.reserve(
        "r3",
        version_id="r3",
        amount_microusd=2_400_000_000,
        version_ceiling_microusd=3_000_000_000,
    )
    with pytest.raises(SpendError, match="campaign ceiling"):
        ledger.reserve(
            "r4",
            version_id="r4",
            amount_microusd=100_000_001,
            version_ceiling_microusd=1_000_000_000,
        )


def test_observation_replaces_reservation_and_unknown_cost_retains_it() -> None:
    ledger = SpendLedger(ceiling_microusd=7_500_000_000)
    ledger.reserve(
        "run",
        version_id="r2",
        amount_microusd=5_100_000_000,
        version_ceiling_microusd=5_100_000_000,
    )
    assert ledger.controlled_total_microusd == 5_100_000_000
    ledger.observe("run", observed_microusd=900_000_000)
    assert ledger.observed_microusd == 900_000_000
    assert ledger.outstanding_microusd == 0
    ledger.reserve(
        "unknown",
        version_id="r3",
        amount_microusd=2_000_000_000,
        version_ceiling_microusd=2_000_000_000,
    )
    ledger.retain_unknown("unknown")
    assert ledger.outstanding_microusd == 2_000_000_000


def test_ledger_round_trip_preserves_accounting() -> None:
    ledger = SpendLedger(ceiling_microusd=7_500_000_000)
    ledger.reserve(
        "x", version_id="r2", amount_microusd=10, version_ceiling_microusd=100
    )
    restored = SpendLedger.from_mapping(ledger.to_mapping())
    assert restored.to_mapping() == ledger.to_mapping()

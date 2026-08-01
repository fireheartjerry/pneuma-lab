from __future__ import annotations

import copy

import pytest

from pneuma_lab.cloud.inventory_discovery import build_inventory_plan, inventory_plan_digest, validate_inventory_plan


def test_inventory_plan_is_exact_metadata_only_bootstrap() -> None:
    plan = build_inventory_plan(frozen_timestamp="2026-08-01T00:00:00Z")
    assert len(plan["sources"]) == 8
    assert plan["region"] == "us-east-1"
    assert plan["cost_ceiling_usd"] == 0
    assert not any((plan["network_policy"][field] for field in ("payload_downloads", "model_weight_downloads", "container_layer_downloads", "experiment_execution")))
    assert inventory_plan_digest(plan) == inventory_plan_digest(copy.deepcopy(plan))


def test_inventory_plan_rejects_order_drift() -> None:
    plan = build_inventory_plan(frozen_timestamp="2026-08-01T00:00:00Z")
    plan["sources"][0], plan["sources"][1] = plan["sources"][1], plan["sources"][0]
    with pytest.raises(ValueError, match="canonically ordered"):
        validate_inventory_plan(plan)

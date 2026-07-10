"""Coherence tests for the blocked / eval-only dataset lanes.

Every dataset lane that is not a training lane must carry a committed reason,
stay non-authorized at training_weight 0.0, and point at a status-review doc.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "data" / "training-readiness" / "dataset-registry.json"

# lane_id -> (expected current_stage, expected training_readiness)
EXPECTED = {
    "swe-chat": ("provenance-blocked", "blocked"),
    "sec-bench-pro": ("provenance-blocked", "blocked"),
    "swe-mera": ("eval-only", "eval-only"),
    "swe-bench": ("eval-only", "eval-only"),
    "swe-bench-pro": ("license-blocked-for-release", "blocked"),
}


def _lanes() -> dict[str, dict]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {lane["lane_id"]: lane for lane in registry["lanes"]}


def test_expected_blocked_lanes_present_with_reason() -> None:
    lanes = _lanes()
    for lane_id, (stage, readiness) in EXPECTED.items():
        assert lane_id in lanes, f"missing lane {lane_id}"
        lane = lanes[lane_id]
        assert lane["current_stage"] == stage
        assert lane["training_readiness"] == readiness
        assert lane["authorization"]["training_authorized"] is False
        assert lane["authorization"]["reason"]
        assert lane["blockers"]
        assert lane["advancement_criteria"]


def test_blocked_lanes_reference_committed_status_docs() -> None:
    lanes = _lanes()
    for lane_id in EXPECTED:
        docs = lanes[lane_id]["references"].get("docs", [])
        assert docs, f"{lane_id} has no status-review doc"
        for ref in docs:
            assert (ROOT / ref["path"]).is_file(), f"missing {ref['path']}"


def test_no_blocked_lane_claims_training_authorized() -> None:
    for lane in _lanes().values():
        if lane.get("current_stage") in {
            "provenance-blocked",
            "license-blocked-for-release",
            "eval-only",
        }:
            assert lane["authorization"]["training_authorized"] is False


def test_all_eleven_families_have_a_lane() -> None:
    """Every dataset_family in the schema enum maps to at least one lane."""
    schema = json.loads(
        (ROOT / "schemas" / "pneuma-training-example.schema.json").read_text(
            encoding="utf-8"
        )
    )
    families = set(schema["properties"]["dataset_family"]["enum"])
    lane_families = {lane["source_family"] for lane in _lanes().values()}
    missing = families - lane_families
    assert missing == set(), f"families with no readiness lane: {sorted(missing)}"

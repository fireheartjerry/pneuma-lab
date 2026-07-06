"""Ported psyche-math unit tests (manifold / drives / authority / hashing)."""

from __future__ import annotations

from pneuma_lab.psyche import authority, drives, manifold
from pneuma_lab.psyche.hashing import state_hash


def test_manifold_moves_tension_up_under_negative_appraisal() -> None:
    a = manifold.new_manifold()
    nxt = manifold.update(
        a,
        appraisal={"tension": 0.8, "valence": -0.7},
        mood={},
        drive_pressure={},
        scars={},
        personality_baseline={},
    )
    assert nxt["tension"] > a["tension"]
    assert nxt["valence"] < a["valence"]
    assert -1.0 <= nxt["tension"] <= 1.0


def test_manifold_is_pure() -> None:
    a = manifold.new_manifold()
    snapshot = dict(a)
    manifold.update(a, {"tension": 0.5}, {}, {}, {}, {})
    assert a == snapshot  # input never mutated


def test_drive_pressure_is_setpoint_minus_level_clamped() -> None:
    d = drives.new_drives()
    d["mastery"]["level"] = 0.2  # setpoint 0.7 → pressure 0.5
    d["curiosity"]["level"] = 0.9  # above setpoint → pressure 0
    p = drives.pressure(d)
    assert abs(p["mastery"] - 0.5) < 1e-9
    assert p["curiosity"] == 0.0


def test_authority_cold_start_floors_at_cosmetic() -> None:
    # High conviction but a weak (cold-start) track record → earned ceiling caps it.
    res = authority.resolve(
        conviction=0.99,
        track={"rate": 0.0, "total": 0},
        domain_ceiling="veto",
        operator_ceiling="veto",
        safety_ceiling="veto",
        verifier_ceiling="veto",
    )
    assert res["granted_tier"] == "cosmetic"
    assert res["binding_cap"] == "earned"


def test_authority_min_over_caps() -> None:
    # Strong earned record, but operator clamps to soft → soft binds.
    res = authority.resolve(
        conviction=0.99,
        track={"rate": 1.0, "total": 50},
        domain_ceiling="veto",
        operator_ceiling="soft",
        safety_ceiling="veto",
        verifier_ceiling="veto",
    )
    assert res["granted_tier"] == "soft"
    assert res["binding_cap"] == "operator"


def test_state_hash_is_stable_and_precision_tolerant() -> None:
    a = {"x": 0.1000001, "y": [1.0, 2.0]}
    b = {"y": [1.0, 2.0], "x": 0.1000002}  # reordered + sub-1e-6 jitter
    assert state_hash(a) == state_hash(b)
    assert state_hash({"x": 0.2}) != state_hash({"x": 0.3})

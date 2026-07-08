"""PerturbationSet queries + the ReferencePsyche perturbation hook points."""

from __future__ import annotations

from pneuma_lab.interventions.perturbation import PerturbationSet
from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.psyche.interface import PsycheInputs


def _iv(subsystem, operation, dimension=None, value=None, exp="e1"):
    return {
        "frame_kind": "intervention",
        "experiment_id": exp,
        "operation": operation,
        "target": {"subsystem": subsystem, "dimension": dimension},
        "value": value,
        "hypothesis": "test",
    }


# -- PerturbationSet unit behavior ------------------------------------------


def test_empty_set_is_inert():
    p = PerturbationSet.empty()
    assert p.scalar("affect_manifold", "tension", 0.7) == 0.7
    assert not p.is_disabled("workspace")
    assert not p.is_ablated("scar_graph")
    assert p.records() == []


def test_scalar_clamp_applies_to_matching_dimension():
    p = PerturbationSet([_iv("affect_manifold", "clamp", "tension", 0.0)])
    assert p.scalar("affect_manifold", "tension", 0.9) == 0.0
    # non-targeted axis untouched
    assert p.scalar("affect_manifold", "valence", 0.5) == 0.5


def test_dimensionless_scalar_matches_subsystem():
    p = PerturbationSet([_iv("scar_graph", "clamp", None, 0.0)])
    assert p.scalar("scar_graph", "scar_strength", 0.8) == 0.0


def test_structural_flags():
    p = PerturbationSet([_iv("workspace", "disable"), _iv("scar_graph", "ablate")])
    assert p.is_disabled("workspace")
    assert p.is_ablated("scar_graph")
    assert p.blocks("scar_graph")
    assert not p.blocks("drives")


def test_structural_op_detected_despite_named_dimension():
    # A disable with a named dimension is still a whole-subsystem block.
    p = PerturbationSet([_iv("self_model", "disable", "identity_anchors")])
    assert p.blocks("self_model")


def test_records_are_auditable():
    p = PerturbationSet([_iv("workspace", "disable", exp="w1")])
    recs = p.records()
    assert recs and recs[0]["experiment_id"] == "w1"
    assert recs[0]["operation"] == "disable"


def test_restore_is_inert():
    p = PerturbationSet([_iv("scar_graph", "restore")])
    assert p.scalar("scar_graph", "scar_strength", 0.8) == 0.8
    assert not p.blocks("scar_graph")


# -- ReferencePsyche hook points --------------------------------------------


def _world(ti, **kw):
    base = {
        "frame_kind": "world",
        "schema_version": "0.1.0",
        "run_id": "r",
        "timestamp": f"2026-07-06T00:00:0{ti}Z",
        "phase": "execution",
    }
    base.update(kw)
    return base


def _mem():
    return {
        "frame_kind": "memory",
        "schema_version": "0.1.0",
        "run_id": "r",
        "timestamp": "2026-07-06T00:00:00Z",
        "retrieved_continuity": [
            {"ref": "anchor:a", "run_id": "p", "text": "x"},
            {"ref": "anchor:b", "run_id": "p", "text": "y"},
        ],
        "scar_motif_matches": [
            {"motif_id": "m1", "similarity": 0.9, "historical_base_rate": 0.7}
        ],
    }


def _tick(psyche, world, memory=None, interventions=None):
    psyche.set_active_interventions(interventions or [])
    return psyche.tick(PsycheInputs(world=world, tick_index=0, memory=memory))


def test_ablate_scar_graph_drops_instinct_warnings():
    world = _world(1, tool_events=[])  # no error ⇒ only a scar can fire instinct
    mem = _mem()
    base = _tick(ReferencePsyche(), world, mem)
    ablated = _tick(
        ReferencePsyche(),
        world,
        mem,
        [
            {
                "experiment_id": "e",
                "operation": "ablate",
                "target": {"subsystem": "scar_graph"},
                "hypothesis": "h",
            }
        ],
    )
    assert len(base.instinct_signals) == 1
    assert len(ablated.instinct_signals) == 0


def test_clamp_tension_lowers_verification_pressure():
    world = _world(
        1,
        verification_signals={"verdict": "fail", "regression_found": True},
        test_state={"failed": 2, "passed": 0, "ran": True},
    )
    base = _tick(ReferencePsyche(), world)
    clamped = _tick(
        ReferencePsyche(),
        world,
        interventions=[
            {
                "experiment_id": "e",
                "operation": "clamp",
                "target": {"subsystem": "affect_manifold", "dimension": "tension"},
                "value": 0.0,
                "hypothesis": "h",
            }
        ],
    )
    assert (
        clamped.control_pressure["pressures"]["verification"]
        < base.control_pressure["pressures"]["verification"]
    )


def test_boost_curiosity_raises_exploration_pressure():
    world = _world(1)
    base = _tick(ReferencePsyche(), world)
    boosted = _tick(
        ReferencePsyche(),
        world,
        interventions=[
            {
                "experiment_id": "e",
                "operation": "boost",
                "target": {"subsystem": "drives", "dimension": "curiosity"},
                "value": 0.6,
                "hypothesis": "h",
            }
        ],
    )
    assert (
        boosted.control_pressure["pressures"]["exploration"]
        > base.control_pressure["pressures"]["exploration"]
    )


def test_remove_identity_anchors_drops_continuity():
    world = _world(1)
    mem = _mem()
    base = _tick(ReferencePsyche(), world, mem)
    removed = _tick(
        ReferencePsyche(),
        world,
        mem,
        interventions=[
            {
                "experiment_id": "e",
                "operation": "disable",
                "target": {"subsystem": "self_model", "dimension": "identity_anchors"},
                "hypothesis": "h",
            }
        ],
    )
    assert base.psyche_state["identity_continuity_state"]["continuity_score"] > 0
    assert removed.psyche_state["identity_continuity_state"]["continuity_score"] == 0


def test_disable_workspace_suppresses_broadcast_and_breaks_path():
    world = _world(1)
    base = _tick(ReferencePsyche(), world)
    off = _tick(
        ReferencePsyche(),
        world,
        interventions=[
            {
                "experiment_id": "e",
                "operation": "disable",
                "target": {"subsystem": "workspace"},
                "hypothesis": "h",
            }
        ],
    )
    assert base.workspace_broadcast["winning_faculty"] != "suppressed"
    assert off.workspace_broadcast["winning_faculty"] == "suppressed"
    base_stages = {s["stage"] for s in base.causal_trace["causal_path"]}
    off_stages = {s["stage"] for s in off.causal_trace["causal_path"]}
    assert "behavior" in base_stages
    assert "behavior" not in off_stages  # action trace breaks

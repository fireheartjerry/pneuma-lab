"""ReferencePsyche output-frame contract tests (single tick, direct)."""

from __future__ import annotations

from pneuma_lab.psyche import PsycheInputs, ReferencePsyche
from pneuma_lab.schemas import validate as V


def _world(**kw) -> dict:
    base = {
        "schema_version": "0.1.0",
        "frame_kind": "world",
        "timestamp": "2026-07-06T00:00:01Z",
        "run_id": "r1",
        "phase": "execution",
    }
    base.update(kw)
    return base


def test_bare_tick_emits_all_always_on_frames_valid() -> None:
    """A minimal world frame (no trace/memory/gov) still yields valid output."""
    out = ReferencePsyche().tick(PsycheInputs(world=_world(), tick_index=0))
    kinds = [f["frame_kind"] for f in out.all_frames()]
    for required in (
        "psyche_state",
        "workspace_broadcast",
        "control_pressure",
        "causal_trace",
        "grounded_self_report",
    ):
        assert required in kinds
    for f in out.all_frames():
        assert V.iter_errors(f) == [], f"invalid {f['frame_kind']}"


def test_pressures_are_bounded_unit_interval() -> None:
    world = _world(
        tool_events=[{"tool": "run", "status": "error"}],
        verification_signals={"verdict": "fail", "regression_found": True},
        stakes={"risk": 1.0, "stakes": 1.0, "reversibility": 0.0},
        diff_size={"net_lines": 900, "added_lines": 900},
    )
    out = ReferencePsyche().tick(PsycheInputs(world=world, tick_index=0))
    for name, val in out.control_pressure["pressures"].items():
        assert 0.0 <= val <= 1.0, f"{name}={val} out of [0,1]"


def test_pressure_is_not_a_command_tier_defaults_low() -> None:
    # With no earned track record, the control pressure tier stays at the floor.
    out = ReferencePsyche().tick(PsycheInputs(world=_world(), tick_index=0))
    assert out.control_pressure["authority_tier"] in {"cosmetic", "soft"}


def test_affect_axes_stay_in_range() -> None:
    world = _world(
        tool_events=[{"tool": "x", "status": "error"}] * 5,
        stakes={"risk": 1.0, "stakes": 1.0, "reversibility": 0.0},
    )
    out = ReferencePsyche().tick(PsycheInputs(world=world, tick_index=0))
    for axis, val in out.psyche_state["affect_manifold"].items():
        assert -1.0 <= val <= 1.0, f"{axis}={val}"


def test_causal_trace_hash_chain_advances_across_ticks() -> None:
    p = ReferencePsyche()
    o0 = p.tick(
        PsycheInputs(world=_world(timestamp="2026-07-06T00:00:01Z"), tick_index=0)
    )
    o1 = p.tick(
        PsycheInputs(
            world=_world(
                timestamp="2026-07-06T00:00:02Z",
                tool_events=[{"tool": "run", "status": "error"}],
            ),
            tick_index=1,
        )
    )
    assert o0.causal_trace["new_state_hash"] == o1.causal_trace["previous_state_hash"]
    assert o1.causal_trace["previous_state_hash"] != o1.causal_trace["new_state_hash"]

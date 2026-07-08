"""InterventionSchedule: duration-window resolution + neutralized null."""

from __future__ import annotations

from pneuma_lab.interventions.schedule import InterventionSchedule


def _world(ti, phase="execution"):
    return {
        "frame_kind": "world",
        "schema_version": "0.1.0",
        "run_id": "r",
        "timestamp": f"2026-07-06T00:00:0{ti}Z",
        "phase": phase,
    }


def _iv(exp, kind, amount=None):
    return {
        "frame_kind": "intervention",
        "schema_version": "0.1.0",
        "experiment_id": exp,
        "operation": "clamp",
        "target": {"subsystem": "affect_manifold", "dimension": "tension"},
        "value": 0.0,
        "hypothesis": "h",
        "duration": {"kind": kind, "amount": amount},
    }


def test_single_tick_default_window():
    frames = [_world(0), _iv("e", "ticks", 1), _world(1)]
    s = InterventionSchedule.from_frames(frames)
    assert [iv["experiment_id"] for iv in s.active(0)] == ["e"]
    assert s.active(1) == []
    assert s.experiment_ids() == {"e"}


def test_ticks_window_spans_n_ticks():
    frames = [_world(0), _iv("e", "ticks", 2), _world(1), _world(2)]
    s = InterventionSchedule.from_frames(frames)
    assert s.active(0) and s.active(1)
    assert s.active(2) == []


def test_run_and_permanent_span_to_end():
    frames = [_world(0), _iv("e", "run"), _world(1), _world(2)]
    s = InterventionSchedule.from_frames(frames)
    assert s.active(0) and s.active(1) and s.active(2)


def test_subtask_window_tracks_phase():
    frames = [
        _world(0, "exec"),
        _iv("e", "subtask"),
        _world(1, "exec"),
        _world(2, "verify"),
    ]
    s = InterventionSchedule.from_frames(frames)
    assert s.active(0) and s.active(1)
    assert s.active(2) == []  # phase changed ⇒ subtask window ended


def test_neutralized_replaces_ops_with_restore():
    frames = [_world(0), _iv("e", "run"), _world(1)]
    s = InterventionSchedule.from_frames(frames)
    neu = s.neutralized()
    assert neu.active(0)[0]["operation"] == "restore"
    assert s.active(0)[0]["operation"] == "clamp"  # original untouched


def test_empty_when_no_interventions():
    s = InterventionSchedule.from_frames([_world(0), _world(1)])
    assert s.is_empty()
    assert s.experiment_ids() == set()

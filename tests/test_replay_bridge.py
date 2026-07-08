from __future__ import annotations

import json
import os

import pytest

from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay.bridge import BridgeError, expand_trace_to_timeline
from pneuma_lab.replay.frames import group_into_ticks
from pneuma_lab.replay.harness import ReplayHarness
from pneuma_lab.schemas import validate

GOLDEN = os.path.join(
    "fixtures", "adapters", "openhands_sampled", "golden", "pneuma_traces.jsonl"
)


def _golden_traces() -> list[dict]:
    with open(GOLDEN, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def test_expansion_shape_and_order():
    trace = _golden_traces()[0]
    n = trace["trajectory"]["num_agent_steps"]
    timeline = expand_trace_to_timeline(trace)
    kinds = [f["frame_kind"] for f in timeline]
    assert kinds[0] == "governance"
    assert kinds[1] == "world"
    assert kinds[2:] == ["world", "agent_trace"] * n
    ticks = group_into_ticks(timeline)
    assert len(ticks) == 1 + n  # preamble + one tick per agent step
    assert ticks[0].agent_trace is None
    assert all(t.agent_trace is not None for t in ticks[1:])
    assert all(t.governance is not None for t in ticks)  # sticky


def test_minted_worlds_valid_and_recorded_frames_untouched():
    for trace in _golden_traces():
        timeline = expand_trace_to_timeline(trace)
        original_agents = [
            f for f in trace["frames"] if f["frame_kind"] == "agent_trace"
        ]
        bridged_agents = [f for f in timeline if f["frame_kind"] == "agent_trace"]
        assert bridged_agents == original_agents  # byte-unchanged pass-through
        for frame in timeline:
            assert validate.iter_errors(frame) == []


def test_error_marker_maps_to_tool_event_status():
    traces = _golden_traces()
    # golden row 2 (fixture-run_2) contains error-marked observations
    trace = next(
        t for t in traces if t["trajectory"]["agent_run_id"] == "fixture-run_2"
    )
    timeline = expand_trace_to_timeline(trace)
    minted = [f for f in timeline if f.get("minted_by") == "replay.bridge"]
    statuses = [e["status"] for w in minted for e in w["tool_events"]]
    assert "error" in statuses
    agent_frames = [f for f in timeline if f["frame_kind"] == "agent_trace"]
    want = [
        "error" if o["error_marker"] else "ok"
        for f in agent_frames
        for o in f["observations"]
    ]
    assert statuses == want


def test_expansion_is_deterministic():
    trace = _golden_traces()[0]
    assert expand_trace_to_timeline(trace) == expand_trace_to_timeline(trace)


def test_task_only_trace_rejected():
    with pytest.raises(BridgeError):
        expand_trace_to_timeline({"trace_id": "ptrace:x", "frames": []})


def test_timeline_replays_through_reference_psyche():
    trace = _golden_traces()[1]  # the failure-shaped fixture run
    timeline = expand_trace_to_timeline(trace)
    result = ReplayHarness(ReferencePsyche(), validate=True).run(timeline)
    n = trace["trajectory"]["num_agent_steps"]
    assert result.tick_count == 1 + n
    assert len(result.tick_outputs) == 1 + n
    # single replay, no interventions: the ladder must stay honest
    assert result.evidence_frame["evidence_level"] <= 3
    # the error-marked steps must be visible to the psyche as tool-event errors
    pressures = [
        o.control_pressure["pressures"].get("verification", 0.0)
        for o in result.tick_outputs
    ]
    assert any(p > 0.0 for p in pressures)


def test_replay_is_deterministic_end_to_end():
    trace = _golden_traces()[1]
    timeline = expand_trace_to_timeline(trace)

    def run_once():
        r = ReplayHarness(ReferencePsyche(), validate=False).run(timeline)
        return json.dumps(r.output_frames, sort_keys=True)

    assert run_once() == run_once()

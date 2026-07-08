"""PneumaTrace v0.2 envelope -> replay-harness timeline (the data->cognition seam).

A trajectory-bearing envelope carries ONE world frame (t0 exteroception), one
governance frame, and N agent-trace frames — but a harness *tick* is one world
frame plus its companions (``replay.frames.group_into_ticks``), so a raw
envelope would collapse to a single tick and the psyche would see one step
instead of N. This module expands the envelope into an honest per-step
timeline:

    governance, world_t0, [world_1 + agent_trace_1], ... [world_N + agent_trace_N]

Honesty rules (binding):

    * every minted world frame is derived ONLY from what the agent observably
      did: ``tool_events`` come from the step's recorded tool calls and
      observation digests; the ``error`` status is the step's lexical
      ``error_marker`` (a declared proxy, see ``adapters.trajectory``), never a
      semantic judgment;
    * the recorded agent-trace frames pass through byte-unchanged;
    * timestamps are copied from the recorded frames (synthetic-ordinal in the
      OpenHands corpus) and their declared provenance is carried along;
    * nothing is injected that the trajectory does not contain: no memory
      frames (the adapters emit none), no test results, no verifier verdicts.

Pure and deterministic: no wall-clock, no randomness, no I/O.
"""

from __future__ import annotations

from ..schemas import validate

FRAME_SCHEMA_VERSION = "0.1.0"


class BridgeError(ValueError):
    """Envelope cannot be expanded into a replay timeline."""


def _agent_frames(envelope: dict) -> list[dict]:
    frames = [
        f
        for f in envelope.get("frames", [])
        if isinstance(f, dict) and f.get("frame_kind") == "agent_trace"
    ]
    return sorted(frames, key=lambda f: f.get("step_index", 0))


def _single_frame(envelope: dict, kind: str) -> dict:
    found = [
        f
        for f in envelope.get("frames", [])
        if isinstance(f, dict) and f.get("frame_kind") == kind
    ]
    if len(found) != 1:
        raise BridgeError(
            f"expected exactly one {kind} frame, found {len(found)} "
            f"(trace {envelope.get('trace_id')!r})"
        )
    return found[0]


def _step_tool_events(agent_frame: dict) -> list[dict]:
    """Observable tool events for one step: name from the recorded call,
    status from the observation's lexical error marker."""
    tool_calls = agent_frame.get("tool_calls") or []
    observations = agent_frame.get("observations") or []
    events: list[dict] = []
    for j, obs in enumerate(observations):
        if j < len(tool_calls):
            tool = tool_calls[j].get("tool") or "unknown"
        elif tool_calls:
            tool = tool_calls[0].get("tool") or "unknown"
        else:
            tool = "unknown"
        events.append(
            {
                "tool": tool,
                "status": "error" if obs.get("error_marker") else "ok",
            }
        )
    return events


def _minted_world(agent_frame: dict, run_id: str) -> dict:
    frame = {
        "schema_version": FRAME_SCHEMA_VERSION,
        "frame_kind": "world",
        "timestamp": agent_frame["timestamp"],
        "run_id": run_id,
        "phase": "execution",
        "tool_events": _step_tool_events(agent_frame),
        "test_state": {"ran": False, "not_yet_run": True},
    }
    provenance = agent_frame.get("timestamp_provenance")
    if provenance is not None:
        frame["timestamp_provenance"] = provenance
    frame["minted_by"] = "replay.bridge"
    return frame


def expand_trace_to_timeline(envelope: dict, *, strict: bool = True) -> list[dict]:
    """Expand a trajectory-bearing PneumaTrace into a flat replay timeline.

    Returns ``[governance, world_t0, world_1, agent_1, ..., world_N, agent_N]``.
    ``strict=True`` (default) schema-validates every MINTED frame; recorded
    frames were validated at adapter build time and pass through unchanged.
    Raises :class:`BridgeError` on task-only traces (no trajectory) or
    malformed envelopes.
    """
    if not isinstance(envelope, dict):
        raise BridgeError(f"envelope is not an object: {type(envelope).__name__}")
    if envelope.get("trajectory") is None:
        raise BridgeError(
            f"task-only trace (no trajectory block): {envelope.get('trace_id')!r}"
        )
    agent_frames = _agent_frames(envelope)
    if not agent_frames:
        raise BridgeError(
            f"trajectory block present but no agent_trace frames: "
            f"{envelope.get('trace_id')!r}"
        )
    world_t0 = _single_frame(envelope, "world")
    governance = _single_frame(envelope, "governance")
    run_id = world_t0.get("run_id") or envelope.get("run_id")

    timeline: list[dict] = [governance, world_t0]
    for agent_frame in agent_frames:
        minted = _minted_world(agent_frame, run_id)
        if strict:
            errors = validate.iter_errors(minted)
            if errors:
                raise BridgeError(
                    f"minted world frame invalid ({envelope.get('trace_id')!r}): "
                    + "; ".join(errors)
                )
        timeline.append(minted)
        timeline.append(agent_frame)
    return timeline


__all__ = ["BridgeError", "expand_trace_to_timeline"]

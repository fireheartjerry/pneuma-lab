"""Determinism: same input ⇒ byte-identical outputs and an identical hash chain."""

from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.psyche.hashing import state_hash
from pneuma_lab.replay import ReplayHarness, load_jsonl

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_run.jsonl"


def _canon(frames: list[dict]) -> str:
    return "\n".join(json.dumps(f, sort_keys=True) for f in frames)


def test_hash_stable_and_precision_tolerant() -> None:
    a = {"x": 0.10000001, "y": [1.0, 2.0]}
    b = {"y": [1.0, 2.0], "x": 0.10000002}
    assert state_hash(a) == state_hash(b)


def test_two_replays_are_byte_identical() -> None:
    frames = load_jsonl(_FIXTURE)
    r1 = ReplayHarness(ReferencePsyche()).run(frames)
    r2 = ReplayHarness(ReferencePsyche()).run(frames)
    assert _canon(r1.output_frames) == _canon(r2.output_frames)
    assert json.dumps(r1.evidence_frame, sort_keys=True) == json.dumps(
        r2.evidence_frame, sort_keys=True
    )


def test_same_psyche_reset_reproduces_hash_chain() -> None:
    frames = load_jsonl(_FIXTURE)
    psyche = ReferencePsyche()
    chain1 = [
        o.psyche_state["state_hash"]
        for o in ReplayHarness(psyche).run(frames).tick_outputs
    ]
    # reuse the SAME psyche instance; run() calls reset() so it must reproduce.
    chain2 = [
        o.psyche_state["state_hash"]
        for o in ReplayHarness(psyche).run(frames).tick_outputs
    ]
    assert chain1 == chain2
    assert len(set(chain1)) == len(chain1), "state should actually change each tick"

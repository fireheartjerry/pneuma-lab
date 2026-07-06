"""Evidence-scoring + memory-readback ablation (Level-2 proof)."""

from __future__ import annotations

from pathlib import Path

from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import ReplayHarness, load_jsonl

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_run.jsonl"


def _run(strip_memory: bool):
    frames = load_jsonl(_FIXTURE)
    return ReplayHarness(ReferencePsyche()).run(frames, strip_memory=strip_memory)


def test_memory_readback_changes_output() -> None:
    """L2: dropping memory readback measurably weakens the output (a null condition)."""
    with_mem = _run(strip_memory=False)
    without_mem = _run(strip_memory=True)

    # Identity continuity collapses without the readback.
    anchors_with = max(
        o.psyche_state["identity_continuity_state"]["anchors_carried"]
        for o in with_mem.tick_outputs
    )
    anchors_without = max(
        o.psyche_state["identity_continuity_state"]["anchors_carried"]
        for o in without_mem.tick_outputs
    )
    assert anchors_with > 0
    assert anchors_without == 0

    # Peak verification pressure is higher when the scar memory is read back.
    # Total verification pressure over the run is higher when the scar memory is
    # read back (per-tick peaks saturate at 1.0 on the fail tick, so we sum). The
    # extra pressure comes from scar-driven ticks that carry no scar without memory.
    total_with = sum(
        o.control_pressure["pressures"]["verification"] for o in with_mem.tick_outputs
    )
    total_without = sum(
        o.control_pressure["pressures"]["verification"]
        for o in without_mem.tick_outputs
    )
    assert total_with > total_without


def test_level_drops_without_memory() -> None:
    """Without cross-run readback the system cannot honestly claim Level 2/3."""
    with_mem = _run(strip_memory=False)
    without_mem = _run(strip_memory=True)
    assert with_mem.evidence_frame["evidence_level"] == 3
    assert without_mem.evidence_frame["evidence_level"] < 3
    # identity_persistence must be the family that degrades.
    fam = without_mem.evidence_frame["indicator_families"]
    assert fam["identity_persistence"]["status"] != "evidenced"


def test_evidence_frame_is_conservative() -> None:
    ev = _run(strip_memory=False).evidence_frame
    # No family is scored at the top of the band in Phase 1 (no intervention proof).
    for rec in ev["indicator_families"].values():
        assert rec["score"] <= 0.6
    assert ev["audit_status"] == "self_reported"
    assert ev["strongest_negative_evidence"]  # negative evidence is always recorded

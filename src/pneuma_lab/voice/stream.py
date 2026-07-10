"""voice_run — drive a subject over a timeline and render its thought stream.

Deterministic (Phase A) mode only: no LLM. The evidence frame produced by the
harness is used verbatim as the authoritative level source and echoed into the
result; the voice never re-scores and never mutates it.
"""

from __future__ import annotations

from dataclasses import asdict

from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import ReplayHarness

from . import extract as _extract
from . import gate as _gate
from . import render_deterministic as _render
from . import sidecar as _sidecar
from .atoms import ThoughtAtom


def voice_run(
    input_frames: list[dict],
    *,
    subject_factory=ReferencePsyche,
    validate: bool = True,
    min_intensity: float = 1e-6,
) -> dict:
    """Render the deterministic thought stream for one replay run."""
    subject = subject_factory()
    result = ReplayHarness(subject, validate=validate).run(input_frames)
    evidence_frame = result.evidence_frame
    run_id = evidence_frame.get("run_id") or (
        result.tick_outputs[0].psyche_state.get("run_id")
        if result.tick_outputs
        else "run"
    )

    per_tick_atoms: list[list[ThoughtAtom]] = []
    all_atoms: list[dict] = []
    all_rendered: list[dict] = []
    for i, out in enumerate(result.tick_outputs):
        prev = result.tick_outputs[i - 1] if i else None
        atoms = _extract.atoms_for_tick(
            out, prev, tick=i, evidence_frame=evidence_frame
        )
        atoms = _gate.gate(atoms, min_intensity=min_intensity)
        per_tick_atoms.append(atoms)
        for atom in atoms:
            all_atoms.append(asdict(atom))
            all_rendered.append(asdict(_render.render(atom)))

    subject_name = type(subject).__name__
    sidecar = _sidecar.build_sidecar(
        run_id=run_id,
        subject=subject_name,
        mode="deterministic",
        evidence_frame=evidence_frame,
        per_tick_atoms=per_tick_atoms,
    )
    return {
        "manifest_kind": "thought_stream",
        "schema_version": "0.1.0",
        "run_id": run_id,
        "subject": subject_name,
        "mode": "deterministic",
        "evidence_level": int(evidence_frame.get("evidence_level", 0)),
        "atoms": all_atoms,
        "rendered": all_rendered,
        "sidecar": sidecar,
        # Echoed for auditing/anti-gaming tests; NOT re-scored by the voice.
        "evidence_frame": evidence_frame,
    }


__all__ = ["voice_run"]

"""voice_run / voice_run_paired — drive a subject and render its thought stream.

The evidence frame produced by the harness/runner is used verbatim as the level
source and echoed into the result; the voice never re-scores and never mutates
it. An optional VoiceSkin makes each tick read naturally, but is accepted only if
verify_voiced passes — otherwise the deterministic text stands.
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
from .ollama import OllamaUnavailable
from .verify import build_grounding_packet, verify_entailment, verify_voiced


def _mark(dicts, status):
    for d in dicts:
        d["text_voiced"] = None
        d["voice_status"] = status
    return dicts


def _render_tick(atoms, skin, judge=None):
    rendered = [_render.render(a) for a in atoms]
    dicts = [asdict(r) for r in rendered]
    if skin is None or not rendered:
        return dicts
    atom_dicts = [asdict(a) for a in atoms]
    try:
        candidate = skin.voice_tick(atom_dicts, dicts)
    except OllamaUnavailable:
        return _mark(dicts, "skin_unavailable")
    except Exception:
        return _mark(dicts, "generation_failed")
    ok, _reasons = verify_voiced(candidate, [d["text_deterministic"] for d in dicts])
    if not ok:
        return _mark(dicts, "rejected_syntactic")
    if judge is not None:
        verdict = verify_entailment(
            candidate, build_grounding_packet(atom_dicts, dicts), judge
        )
        if verdict == "not_entailed":
            return _mark(dicts, "rejected_entailment")
        if verdict != "entailed":
            return _mark(dicts, "judge_failed")
    for d in dicts:
        d["text_voiced"] = candidate
        d["voice_status"] = "voiced"
    return dicts


def _assemble(
    *,
    result,
    evidence_frame,
    subject_name,
    skin,
    min_intensity,
    extra_last_tick_atoms=None,
    judge=None,
):
    run_id = evidence_frame.get("run_id") or (
        result.tick_outputs[0].psyche_state.get("run_id")
        if result.tick_outputs
        else "run"
    )
    per_tick_atoms: list[list[ThoughtAtom]] = []
    all_atoms: list[dict] = []
    all_rendered: list[dict] = []
    last = len(result.tick_outputs) - 1
    for i, out in enumerate(result.tick_outputs):
        prev = result.tick_outputs[i - 1] if i else None
        atoms = _extract.atoms_for_tick(
            out, prev, tick=i, evidence_frame=evidence_frame
        )
        if i == last and extra_last_tick_atoms:
            atoms = atoms + extra_last_tick_atoms
        atoms = _gate.gate(atoms, min_intensity=min_intensity)
        per_tick_atoms.append(atoms)
        for d in _render_tick(atoms, skin, judge):
            all_rendered.append(d)
        for atom in atoms:
            all_atoms.append(asdict(atom))
    mode = "voiced" if skin is not None else "deterministic"
    sidecar = _sidecar.build_sidecar(
        run_id=run_id,
        subject=subject_name,
        mode=mode,
        evidence_frame=evidence_frame,
        per_tick_atoms=per_tick_atoms,
    )
    return {
        "manifest_kind": "thought_stream",
        "schema_version": "0.1.0",
        "run_id": run_id,
        "subject": subject_name,
        "mode": mode,
        "evidence_level": int(evidence_frame.get("evidence_level", 0)),
        "atoms": all_atoms,
        "rendered": all_rendered,
        "sidecar": sidecar,
        "evidence_frame": evidence_frame,
    }


def voice_run(
    input_frames,
    *,
    subject_factory=ReferencePsyche,
    validate=True,
    min_intensity=1e-6,
    skin=None,
    judge=None,
):
    """Deterministic (or voiced) thought stream for a passive replay run."""
    subject = subject_factory()
    result = ReplayHarness(subject, validate=validate).run(input_frames)
    return _assemble(
        result=result,
        evidence_frame=result.evidence_frame,
        subject_name=type(subject).__name__,
        skin=skin,
        min_intensity=min_intensity,
        judge=judge,
    )


def voice_run_paired(
    input_frames,
    *,
    subject_factory=ReferencePsyche,
    min_intensity=1e-6,
    skin=None,
    judge=None,
):
    """Thought stream for a paired replay: renders the treated arm and appends
    intervention_result atoms (the tested counterfactuals) to the final tick."""
    from pneuma_lab.interventions.runner import PairedReplayRunner

    paired = PairedReplayRunner(psyche_factory=subject_factory).run(input_frames)
    evidence_frame = paired.evidence_frame
    treated = paired.treated
    run_id = evidence_frame.get("run_id") or (
        treated.tick_outputs[0].psyche_state.get("run_id")
        if treated.tick_outputs
        else "run"
    )
    timestamp = (
        treated.tick_outputs[-1].psyche_state.get("timestamp", "")
        if treated.tick_outputs
        else ""
    )
    extra = _extract.intervention_result_atoms(
        paired.report,
        run_id=run_id,
        tick=max(0, len(treated.tick_outputs) - 1),
        timestamp=timestamp,
        evidence_frame=evidence_frame,
        start_ordinal=1000,
    )
    return _assemble(
        result=treated,
        evidence_frame=evidence_frame,
        subject_name=type(subject_factory()).__name__,
        skin=skin,
        min_intensity=min_intensity,
        extra_last_tick_atoms=extra,
        judge=judge,
    )


__all__ = ["voice_run", "voice_run_paired"]

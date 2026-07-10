from pneuma_lab.voice import atoms as A


def test_vocabulary_maps_are_complete_and_consistent():
    assert set(A.ATOM_TYPES) == set(A.ATOM_FAMILY)
    assert set(A.ATOM_TYPES) == set(A.MIN_LEVEL)
    assert len(A.ATOM_TYPES) == 14
    for t in ("appraisal", "shift", "pressure", "self_report", "boundary"):
        assert A.ATOM_FAMILY[t] is None
    assert A.ATOM_FAMILY["intervention_result"] == "causal_intervention_robustness"
    assert A.MIN_LEVEL["intervention_result"] == 4
    assert A.MIN_LEVEL["boundary"] == 0


def test_credit_status_for_reads_family_status_or_l1_coupling():
    frame = {
        "evidence_level": 3,
        "indicator_families": {"global_workspace": {"status": "evidenced"}},
    }
    assert A.credit_status_for("competition", frame) == "evidenced"
    assert A.credit_status_for("pressure", frame) == "evidenced"
    assert A.credit_status_for("boundary", {"evidence_level": 0}) == "evidenced"
    assert A.credit_status_for("pressure", {"evidence_level": 0}) == "architecture_only"
    assert A.credit_status_for("competition", {"evidence_level": 3}) == "absent"


def test_atom_and_rendered_are_separable():
    atom = A.ThoughtAtom(
        atom_id="r:0:atom:0",
        type="pressure",
        run_id="r",
        tick=0,
        timestamp="2026-07-06T00:00:01Z",
        receipts=[{"field_path": "control_pressure.verification", "value": 0.42}],
        intensity=0.42,
        crediting_family=None,
        credit_status="evidenced",
        min_level=1,
    )
    assert not any(k.startswith("text") for k in vars(atom))
    rendered = A.RenderedThought(atom_ids=[atom.atom_id], text_deterministic="x")
    assert rendered.voice_status == "deterministic_only"
    assert rendered.text_voiced is None


from pneuma_lab.schemas import load_schema, ALL_SCHEMA_FILES
from pneuma_lab.schemas import validate as V


def test_thought_stream_schema_registered_and_parses():
    assert "thought-stream.schema.json" in ALL_SCHEMA_FILES
    schema = load_schema("thought-stream.schema.json")
    assert schema["x-pneuma-schema-kind"] == "expressive_view"
    assert "thought_atom" in schema["$defs"]


def test_validate_thought_stream_accepts_minimal_and_rejects_junk():
    doc = {
        "manifest_kind": "thought_stream",
        "schema_version": "0.1.0",
        "run_id": "r",
        "subject": "ReferencePsyche",
        "mode": "deterministic",
        "evidence_level": 3,
        "atoms": [],
        "rendered": [],
        "sidecar": {
            "run_id": "r",
            "subject": "ReferencePsyche",
            "mode": "deterministic",
            "evidence_level": 3,
            "indicator_family_status": {},
            "ticks": [],
        },
    }
    assert V.validate_thought_stream(doc) is doc
    import pytest

    with pytest.raises(V.FrameValidationError):
        V.validate_thought_stream({"manifest_kind": "wrong"})


from pathlib import Path
from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import ReplayHarness, load_jsonl
from pneuma_lab.voice import extract as X

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_run.jsonl"


def _reference_result():
    return ReplayHarness(ReferencePsyche()).run(load_jsonl(_FIXTURE))


def test_extract_produces_grounded_atoms_for_tick0():
    result = _reference_result()
    ev = result.evidence_frame
    atoms = X.atoms_for_tick(result.tick_outputs[0], None, tick=0, evidence_frame=ev)
    kinds = {a.type for a in atoms}
    assert "appraisal" in kinds
    assert "competition" in kinds
    assert "pressure" in kinds
    ps = result.tick_outputs[0].psyche_state
    for a in atoms:
        assert a.receipts, f"{a.type} has no receipts"
        assert 0.0 <= a.intensity <= 1.0
        assert a.run_id == ps["run_id"]
        assert a.timestamp == ps["timestamp"]


def test_extract_competition_credit_follows_family_status():
    result = _reference_result()
    ev_evidenced = result.evidence_frame
    atoms = X.atoms_for_tick(
        result.tick_outputs[0], None, tick=0, evidence_frame=ev_evidenced
    )
    comp = next(a for a in atoms if a.type == "competition")
    assert comp.credit_status == "evidenced"
    ev_arch = {
        "evidence_level": 1,
        "indicator_families": {"global_workspace": {"status": "architecture_only"}},
    }
    atoms2 = X.atoms_for_tick(
        result.tick_outputs[0], None, tick=0, evidence_frame=ev_arch
    )
    comp2 = next(a for a in atoms2 if a.type == "competition")
    assert comp2.credit_status == "architecture_only"


from pneuma_lab.voice import gate as G


def test_gate_keeps_observed_atoms_and_ranks_by_intensity():
    result = _reference_result()
    atoms = X.atoms_for_tick(
        result.tick_outputs[0], None, tick=0, evidence_frame=result.evidence_frame
    )
    kept = G.gate(atoms, min_intensity=0.0)
    assert len(kept) == len(atoms)
    intensities = [a.intensity for a in kept]
    assert intensities == sorted(intensities, reverse=True)


def test_gate_drops_only_subepsilon_intensity():
    result = _reference_result()
    atoms = X.atoms_for_tick(
        result.tick_outputs[0], None, tick=0, evidence_frame=result.evidence_frame
    )
    for a in atoms:
        a.intensity = 0.0
    assert G.gate(atoms, min_intensity=1e-6) == []


from pneuma_lab.voice import render_deterministic as R
from pneuma_lab.voice import atoms as A


def _atom(type_, receipts, credit_status, family):
    return A.ThoughtAtom(
        atom_id="r:0:atom:0",
        type=type_,
        run_id="r",
        tick=0,
        timestamp="t",
        receipts=receipts,
        intensity=0.5,
        crediting_family=family,
        credit_status=credit_status,
        min_level=A.MIN_LEVEL[type_],
    )


def test_render_pressure_is_state_grounded_and_hedge_free_when_credited():
    atom = _atom(
        "pressure",
        [{"field_path": "control_pressure.verification", "value": 0.42}],
        "evidenced",
        None,
    )
    rt = R.render(atom)
    assert "0.42" in rt.text_deterministic
    assert "architecture-only" not in rt.text_deterministic
    assert rt.voice_status == "deterministic_only"


def test_render_competition_hedges_when_not_credited():
    atom = _atom(
        "competition",
        [
            {
                "field_path": "workspace_broadcast.winning_faculty",
                "value": "self_model",
            },
            {"field_path": "salience_scores.risk", "value": 3.23},
        ],
        "architecture_only",
        "global_workspace",
    )
    rt = R.render(atom)
    assert "self_model" in rt.text_deterministic
    assert "architecture-only, not promotable evidence" in rt.text_deterministic


def test_render_never_emits_forbidden_phenomenology():
    for t, receipts, fam in [
        (
            "appraisal",
            [{"field_path": "causal_trace.changed_dimensions.count", "value": 6.0}],
            None,
        ),
        (
            "uncertainty",
            [{"field_path": "psyche_state.self_model.predicted_error", "value": 0.48}],
            "higher_order_self_model",
        ),
        (
            "boundary",
            [
                {"field_path": "consciousness_evidence.evidence_level", "value": 3.0},
                {"field_path": "filtered_forbidden_claims.count", "value": 0.0},
            ],
            None,
        ),
    ]:
        rt = R.render(_atom(t, receipts, "evidenced", fam))
        low = rt.text_deterministic.lower()
        for banned in (
            "i feel",
            "i suffer",
            "sentient",
            "phenomenal",
            "conscious experience",
            "qualia",
        ):
            assert banned not in low, f"{t} leaked forbidden phrasing: {banned}"


def test_render_fallback_for_unspecialized_type():
    atom = _atom(
        "instinct",
        [{"field_path": "instinct.severity", "value": 0.7}],
        "evidenced",
        "valenced_learning",
    )
    rt = R.render(atom)  # must NOT raise KeyError
    assert "0.70" in rt.text_deterministic
    assert rt.voice_status == "deterministic_only"


def test_scrub_forbidden_catches_contractions_and_possessives():
    for phrase in (
        "I'm conscious of this",
        "these are my feelings",
        "I am aware",
        "it has qualia",
    ):
        clean, removed = R.scrub_forbidden(phrase)
        assert removed, f"not scrubbed: {phrase}"
        assert "[filtered]" in clean


from pneuma_lab.voice import sidecar as S


def test_sidecar_records_receipts_credit_and_family_status():
    result = _reference_result()
    ev = result.evidence_frame
    per_tick_atoms = []
    for i, out in enumerate(result.tick_outputs):
        prev = result.tick_outputs[i - 1] if i else None
        per_tick_atoms.append(X.atoms_for_tick(out, prev, tick=i, evidence_frame=ev))
    sc = S.build_sidecar(
        run_id=ev["run_id"],
        subject="ReferencePsyche",
        mode="deterministic",
        evidence_frame=ev,
        per_tick_atoms=per_tick_atoms,
    )
    assert sc["evidence_level"] == ev["evidence_level"]
    assert sc["indicator_family_status"]["global_workspace"] in {
        "evidenced",
        "intervention_backed",
        "architecture_only",
        "attempted",
        "absent",
    }
    assert len(sc["ticks"]) == len(result.tick_outputs)
    first = sc["ticks"][0]
    assert first["tick"] == 0
    assert all("credit_status" in a and "receipts" in a for a in first["atoms"])


from pneuma_lab.voice import stream as ST


def test_voice_run_reference_is_l3_and_rich():
    s = ST.voice_run(load_jsonl(_FIXTURE))
    assert s["subject"] == "ReferencePsyche"
    assert s["evidence_level"] == 3
    kinds = {a["type"] for a in s["atoms"]}
    assert {"appraisal", "competition", "counterfactual"} <= kinds
    assert "intervention_result" not in kinds
    assert len(s["atoms"]) == len(s["rendered"])
    # The stream (minus the audit-only evidence_frame echo) is schema-valid.
    doc = {k: v for k, v in s.items() if k != "evidence_frame"}
    assert V.validate_thought_stream(doc) is doc


def test_voice_run_baseline_subject_is_thinner_than_reference():
    from pneuma_lab.nervous_system.subject import BaselinePsycheSubject

    ref = ST.voice_run(load_jsonl(_FIXTURE))
    base = ST.voice_run(load_jsonl(_FIXTURE), subject_factory=BaselinePsycheSubject)
    assert base["subject"] == "BaselinePsycheSubject"
    assert len(base["atoms"]) <= len(ref["atoms"])


def test_voice_never_alters_the_evidence_frame():
    frames = load_jsonl(_FIXTURE)
    bare = ReplayHarness(ReferencePsyche()).run(frames).evidence_frame
    s = ST.voice_run(frames)
    assert s["evidence_level"] == bare["evidence_level"]
    import json

    assert json.dumps(s["evidence_frame"], sort_keys=True) == json.dumps(
        bare, sort_keys=True
    )


from pneuma_lab.voice import transcript as T


def test_transcript_is_byte_deterministic(tmp_path):
    frames = load_jsonl(_FIXTURE)
    a = tmp_path / "a"
    b = tmp_path / "b"
    T.write_transcript(ST.voice_run(frames), a)
    T.write_transcript(ST.voice_run(frames), b)
    for name in ("stream.md", "stream.jsonl", "sidecar.json"):
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_transcript_md_reads_as_a_thought_stream(tmp_path):
    T.write_transcript(ST.voice_run(load_jsonl(_FIXTURE)), tmp_path)
    md = (tmp_path / "stream.md").read_text(encoding="utf-8")
    assert "evidence level 3" in md.lower()
    assert "tick 0" in md.lower()


import pathlib


def test_voice_package_imports_no_9to5_or_verifier():
    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "pneuma_lab" / "voice"
    for py in root.glob("*.py"):
        text = py.read_text(encoding="utf-8").lower()
        assert "9to5" not in text, f"{py.name} references 9to5"
        assert "import verifier" not in text and "from verifier" not in text, py.name


def test_voice_all_submodules_are_lazily_importable():
    import importlib
    import pneuma_lab.voice as v

    for name in v.__all__:
        assert importlib.import_module(f"pneuma_lab.voice.{name}") is getattr(v, name)


from pneuma_lab.voice import voiced as VZ
from pneuma_lab.voice import verify as VF
from pneuma_lab.voice import render_deterministic as R


def _rt(text):
    return {
        "atom_ids": ["a"],
        "text_deterministic": text,
        "text_voiced": None,
        "voice_status": "deterministic_only",
    }


def test_reference_skin_is_deterministic_and_fuses():
    rendered = [
        _rt("Tension climbs to -0.38."),
        _rt("A verification pressure of 0.42 forms and is held there."),
    ]
    skin = VZ.ReferenceVoiceSkin()
    a = skin.voice_tick([], rendered)
    b = skin.voice_tick([], rendered)
    assert a == b
    assert "-0.38" in a and "0.42" in a


def test_verify_accepts_faithful_fusion():
    source = ["Tension climbs to -0.38.", "self_model takes it at salience 1.00."]
    ok, reasons = VF.verify_voiced(
        "Tension climbs to -0.38 while self_model takes it at salience 1.00.", source
    )
    assert ok, reasons


def test_verify_rejects_invented_number():
    source = ["A verification pressure of 0.42 forms."]
    ok, reasons = VF.verify_voiced("A verification pressure of 0.99 forms.", source)
    assert not ok and any("0.99" in r for r in reasons)


def test_verify_rejects_invented_identifier():
    source = ["self_model takes it at salience 1.00."]
    ok, reasons = VF.verify_voiced("risk_instinct takes it at salience 1.00.", source)
    assert not ok and any("risk_instinct" in r for r in reasons)


def test_verify_rejects_forbidden_claim():
    ok, reasons = VF.verify_voiced(
        "I'm conscious of the tension at 0.42.", ["tension at 0.42."]
    )
    assert not ok and any("forbidden" in r.lower() for r in reasons)


def test_verify_rejects_dropped_hedge():
    source = [
        "A workspace race resolved (self_model, 1.00) — architecture-only, not promotable evidence."
    ]
    ok, reasons = VF.verify_voiced(
        "A workspace race resolved (self_model, 1.00).", source
    )
    assert not ok and any("architecture-only" in r for r in reasons)


def test_verify_rejects_bulk_ungrounded_expansion():
    source = ["A verification pressure of 0.42 forms and is held there."]
    voiced = (
        "A verification pressure of 0.42 forms and is held there, and then it "
        "collapses into a wave of panic and an unbearable, crushing dread that "
        "spreads through every corner of the mind without pause or relief."
    )
    ok, reasons = VF.verify_voiced(voiced, source)
    assert not ok and any("expands" in r for r in reasons)


def test_scrub_catches_more_phenomenology():
    for phrase in (
        "I am suffering here",
        "this hurts me deeply",
        "it has subjective experience",
        "we feel uneasy",
    ):
        clean, removed = R.scrub_forbidden(phrase)
        assert removed, f"not scrubbed: {phrase}"


_IV_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "interventions"


def test_paired_stream_has_intervention_result_and_is_l4_capable():
    s = ST.voice_run_paired(load_jsonl(_IV_DIR / "clamp_tension.jsonl"))
    kinds = {a["type"] for a in s["atoms"]}
    assert "intervention_result" in kinds
    ir = next(a for a in s["atoms"] if a["type"] == "intervention_result")
    paths = {r["field_path"] for r in ir["receipts"]}
    assert (
        "intervention.observed_delta" in paths and "intervention.experiment_id" in paths
    )


def test_restore_null_has_no_intervention_result():
    s = ST.voice_run_paired(load_jsonl(_IV_DIR / "restore_null.jsonl"))
    assert "intervention_result" not in {a["type"] for a in s["atoms"]}


def test_skin_cannot_inflate_the_level():
    frames = load_jsonl(_FIXTURE)
    off = ST.voice_run(frames)
    on = ST.voice_run(frames, skin=VZ.ReferenceVoiceSkin())
    import json

    assert json.dumps(off["evidence_frame"], sort_keys=True) == json.dumps(
        on["evidence_frame"], sort_keys=True
    )
    assert off["evidence_level"] == on["evidence_level"]
    assert any(r["voice_status"] == "voiced" for r in on["rendered"])


def test_voiced_falls_back_on_rejected_drift():
    class DriftSkin:
        def voice_tick(self, atoms, rendered):
            return "verification pressure of 0.99999 forms"

    frames = load_jsonl(_FIXTURE)
    on = ST.voice_run(frames, skin=DriftSkin())
    assert all("0.99999" not in (r.get("text_voiced") or "") for r in on["rendered"])
    assert any(r["voice_status"] == "voiced_rejected_fell_back" for r in on["rendered"])

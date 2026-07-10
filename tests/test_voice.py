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

"""Pure frame -> ThoughtAtom extraction. No prose, no scoring, no mutation.

Each helper reads real output-frame fields and returns zero or one atom. The
public ``atoms_for_tick`` assembles them in the fixed ATOM_TYPES order, assigns
deterministic ids, and stamps each atom's credit_status from the evidence frame.
"""

from __future__ import annotations

from pneuma_lab.psyche.hashing import frame_id
from pneuma_lab.psyche.interface import PsycheOutputs

from .atoms import (
    ATOM_FAMILY,
    ATOM_TYPES,
    MIN_LEVEL,
    ThoughtAtom,
    clamp01,
    credit_status_for,
)

_EPS = 1e-9


def _receipt(field_path: str, value, frame_ref: str | None = None) -> dict:
    r = {"field_path": field_path, "value": value}
    if frame_ref is not None:
        r["frame_ref"] = frame_ref
    return r


def _appraisal(out: PsycheOutputs):
    changed = out.causal_trace.get("changed_dimensions", []) or []
    if not changed:
        return None
    receipts = [_receipt("causal_trace.changed_dimensions.count", float(len(changed)))]
    for c in changed[:3]:
        receipts.append(_receipt(f"changed.{c.get('dimension')}", c.get("to")))
    return ("appraisal", receipts, clamp01(len(changed) / 6.0))


def _shift(out: PsycheOutputs):
    changed = out.causal_trace.get("changed_dimensions", []) or []
    best = None
    for c in changed:
        to = c.get("to")
        frm = c.get("from")
        if not isinstance(to, (int, float)):
            continue
        mag = (
            abs(float(to) - float(frm))
            if isinstance(frm, (int, float))
            else abs(float(to))
        )
        if best is None or mag > best[0]:
            best = (mag, c)
    if best is None:
        return None
    _, c = best
    receipts = [_receipt(f"shift.{c.get('dimension')}", c.get("to"))]
    if isinstance(c.get("from"), (int, float)):
        receipts.append(_receipt(f"shift.{c.get('dimension')}.from", c.get("from")))
    return ("shift", receipts, clamp01(best[0]))


def _pressure(out: PsycheOutputs):
    pressures = out.control_pressure.get("pressures", {}) or {}
    numeric = {k: float(v) for k, v in pressures.items() if isinstance(v, (int, float))}
    if not numeric:
        return None
    name = max(sorted(numeric), key=lambda k: numeric[k])
    value = numeric[name]
    if value <= _EPS:
        return None
    receipts = [
        _receipt(f"control_pressure.{name}", value),
        _receipt(
            "control_pressure.authority_tier",
            out.control_pressure.get("authority_tier"),
        ),
    ]
    return ("pressure", receipts, clamp01(value))


def _self_report(out: PsycheOutputs):
    report = out.grounded_self_report
    measurements = report.get("reported_measurements", {}) or {}
    receipts = [
        _receipt(
            "grounded_self_report.affect_state_hash", report.get("affect_state_hash")
        )
    ]
    for k in sorted(measurements):
        receipts.append(_receipt(f"reported_measurements.{k}", measurements[k]))
    intensity = clamp01(1.0 - float(report.get("uncertainty", 0.5)))
    return ("self_report", receipts, intensity)


def _competition(out: PsycheOutputs, prev: PsycheOutputs | None):
    bc = out.workspace_broadcast
    winner = bc.get("winning_faculty")
    if winner in (None, "none", "suppressed") or bc.get("disabled"):
        return None
    salience = bc.get("salience_scores", {}) or {}
    receipts = [_receipt("workspace_broadcast.winning_faculty", winner)]
    for k in sorted(salience):
        if isinstance(salience[k], (int, float)):
            receipts.append(_receipt(f"salience_scores.{k}", float(salience[k])))
    conviction = bc.get("conviction")
    if isinstance(conviction, (int, float)):
        receipts.append(_receipt("workspace_broadcast.conviction", float(conviction)))
    overtook = bool(
        prev and prev.workspace_broadcast.get("winning_faculty") not in (None, winner)
    )
    intensity = clamp01(
        float(conviction) if isinstance(conviction, (int, float)) else 0.5
    )
    return ("competition", receipts, intensity, overtook)


def _memory_activation(out: PsycheOutputs):
    derived = out.psyche_state.get("derived_signals", {}) or {}
    scar = derived.get("scar_strength")
    if not isinstance(scar, (int, float)) or scar <= _EPS:
        return None
    receipts = [_receipt("psyche_state.derived_signals.scar_strength", float(scar))]
    for sig in out.instinct_signals:
        if sig.get("match_type") in ("exact", "near_duplicate", "prefix"):
            receipts.append(_receipt("instinct.motif_id", sig.get("motif_id")))
            break
    return ("memory_activation", receipts, clamp01(float(scar)))


def _uncertainty(out: PsycheOutputs):
    ps = out.psyche_state
    sm = ps.get("self_model", {}) or {}
    pe = sm.get("predicted_error")
    if not isinstance(pe, (int, float)):
        pe = ps.get("self_model_uncertainty")
    if not isinstance(pe, (int, float)) or pe <= _EPS:
        return None
    receipts = [_receipt("psyche_state.self_model.predicted_error", float(pe))]
    manifold = ps.get("affect_manifold", {}) or {}
    if isinstance(manifold.get("certainty"), (int, float)):
        receipts.append(
            _receipt("affect_manifold.certainty", float(manifold["certainty"]))
        )
    return ("uncertainty", receipts, clamp01(float(pe)))


def _counterfactual(out: PsycheOutputs):
    preds = out.causal_trace.get("counterfactual_predictions", []) or []
    if not preds:
        return None
    receipts = []
    for p in preds[:3]:
        receipts.append(_receipt("counterfactual.condition", p.get("condition")))
        receipts.append(
            _receipt("counterfactual.predicted_outcome", p.get("predicted_outcome"))
        )
    return ("counterfactual", receipts, clamp01(len(preds) / 3.0))


def _boundary(out: PsycheOutputs, evidence_frame: dict, tick: int):
    report = out.grounded_self_report
    filtered = report.get("filtered_forbidden_claims", []) or []
    if tick != 0 and not filtered:
        return None
    receipts = [
        _receipt(
            "consciousness_evidence.evidence_level",
            float(evidence_frame.get("evidence_level", 0)),
        ),
        _receipt("filtered_forbidden_claims.count", float(len(filtered))),
    ]
    return ("boundary", receipts, 0.2)


def intervention_result_atoms(
    report: dict,
    *,
    run_id: str,
    tick: int,
    timestamp: str,
    evidence_frame: dict,
    start_ordinal: int,
) -> list[ThoughtAtom]:
    """Run-level atoms for each tested counterfactual (from a paired report).

    Emitted only for tests that genuinely perturbed and passed; the restore/null
    scenario produces none. Attached to the final tick by the paired stream.
    """
    atoms: list[ThoughtAtom] = []
    ordinal = start_ordinal
    for test in report.get("tests", []) or []:
        if (
            not test.get("passed")
            or abs(float(test.get("observed_delta", 0.0))) <= _EPS
        ):
            continue
        receipts = [
            _receipt("intervention.experiment_id", test.get("experiment_id")),
            _receipt("intervention.target_signal", test.get("target_signal")),
            _receipt("intervention.control_value", test.get("control_value")),
            _receipt("intervention.treated_value", test.get("treated_value")),
            _receipt("intervention.observed_delta", test.get("observed_delta")),
            _receipt("intervention.null_delta", test.get("null_delta")),
        ]
        atoms.append(
            ThoughtAtom(
                atom_id=frame_id(run_id, tick, "atom", ordinal),
                type="intervention_result",
                run_id=run_id,
                tick=tick,
                timestamp=timestamp,
                receipts=receipts,
                intensity=clamp01(abs(float(test.get("observed_delta", 0.0)))),
                crediting_family=ATOM_FAMILY["intervention_result"],
                credit_status=credit_status_for("intervention_result", evidence_frame),
                min_level=MIN_LEVEL["intervention_result"],
                changed_from_prev=True,
            )
        )
        ordinal += 1
    return atoms


def atoms_for_tick(
    out: PsycheOutputs,
    prev: PsycheOutputs | None,
    *,
    tick: int,
    evidence_frame: dict,
    intervention_report: dict | None = None,
) -> list[ThoughtAtom]:
    """Extract the observed ThoughtAtoms for one tick (pure, prose-free).

    ``intervention_result`` atoms are produced in Phase B from
    ``intervention_report`` — omitted here (Phase A has no paired arm).
    """
    run_id = out.psyche_state.get("run_id", "run")
    timestamp = out.psyche_state.get("timestamp", "")

    raw: list[tuple] = []
    for producer in (
        _appraisal(out),
        _shift(out),
        _pressure(out),
        _self_report(out),
        _memory_activation(out),
        _uncertainty(out),
        _counterfactual(out),
    ):
        if producer is not None:
            raw.append(producer)
    comp = _competition(out, prev)
    if comp is not None:
        raw.append(comp)
    boundary = _boundary(out, evidence_frame, tick)
    if boundary is not None:
        raw.append(boundary)

    order = {t: i for i, t in enumerate(ATOM_TYPES)}
    raw.sort(key=lambda item: order[item[0]])

    atoms: list[ThoughtAtom] = []
    for ordinal, item in enumerate(raw):
        atom_type, receipts, intensity = item[0], item[1], item[2]
        changed = bool(item[3]) if len(item) > 3 else False
        atoms.append(
            ThoughtAtom(
                atom_id=frame_id(run_id, tick, "atom", ordinal),
                type=atom_type,
                run_id=run_id,
                tick=tick,
                timestamp=timestamp,
                receipts=receipts,
                intensity=float(intensity),
                crediting_family=ATOM_FAMILY[atom_type],
                credit_status=credit_status_for(atom_type, evidence_frame),
                min_level=MIN_LEVEL[atom_type],
                changed_from_prev=changed,
            )
        )
    return atoms


__all__ = ["atoms_for_tick", "intervention_result_atoms"]

"""Drive BaselinePsycheSubject over an input-frame timeline and package bundles.

Reuses ReplayHarness for ticking/validation. The promotable psyche scorer's
evidence frame is intentionally discarded; the bundle carries a conservative
subject_evidence_frame instead. Scars are seeded from and written back to a
persistent store (cross-run memory).
"""

from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.nervous_system import BLOCKED_USES, LIMITATIONS
from pneuma_lab.nervous_system import scar_memory as sm
from pneuma_lab.nervous_system import shadow_evidence as nse
from pneuma_lab.nervous_system.subject import BaselinePsycheSubject
from pneuma_lab.replay.harness import ReplayHarness
from pneuma_lab.schemas import validate

_FAMILIES_EXERCISED = (
    "global_workspace",
    "valenced_learning",
    "identity_persistence",
    "higher_order_self_model",
)


def _governance_of(frames):
    for fr in frames:
        if fr.get("frame_kind") == "governance":
            return fr
    return {}


def _base_timestamp(frames):
    for fr in frames:
        if isinstance(fr.get("timestamp"), str):
            return fr["timestamp"]
    return "2026-07-10T00:00:00Z"


def run_subject(
    input_frames, *, scar_store_path=None, shadow_log_path=None, schedule=None
):
    governance = _governance_of(input_frames)
    run_id = governance.get("run_id", "subj")
    timestamp = _base_timestamp(input_frames)
    log_path = Path(shadow_log_path) if shadow_log_path else None

    def _append(row):
        if log_path is None:
            return
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as h:
            h.write(json.dumps(row, sort_keys=True) + "\n")

    if governance.get("kill_switch_state", "on") != "on":
        _append(
            {
                "status": "suppressed_by_governance",
                "run_id": run_id,
                "kill_switch_state": governance.get("kill_switch_state"),
                "timestamp": timestamp,
            }
        )
        return []

    seed = sm.load(scar_store_path) if scar_store_path else {}
    subject = BaselinePsycheSubject(scars=seed)
    result = ReplayHarness(subject, validate=True).run(input_frames, schedule=schedule)

    # one conservative evidence frame for the whole run slice (no ablation here)
    evidence = nse.subject_evidence_frame(
        ablation_result={"direction_ok": False, "null_holds": True},
        families_exercised=_FAMILIES_EXERCISED,
        run_id=run_id,
        timestamp=timestamp,
    )

    bundles = []
    for o in result.tick_outputs:
        instinct = o.instinct_signals[0] if o.instinct_signals else None
        bundle = {
            "schema_version": "0.1.0",
            "bundle_kind": "pneuma_output",
            "run_id": run_id,
            "timestamp": o.psyche_state["timestamp"],
            "governance_status": "emitted",
            "risk_estimate": None,
            "instinct": instinct,
            "control_pressure": o.control_pressure,
            "causal_trace": o.causal_trace,
            "consciousness_evidence": evidence,
            "psyche_state": o.psyche_state,
            "workspace_broadcast": o.workspace_broadcast,
            "blocked_uses": list(BLOCKED_USES),
            "limitations": list(LIMITATIONS),
        }
        validate.validate_bundle(bundle)
        bundles.append(bundle)
        _append(
            {
                "status": "emitted",
                "run_id": run_id,
                "tick": o.psyche_state["state_hash"],
                "verification": o.control_pressure["pressures"]["verification"],
            }
        )

    if scar_store_path:
        sm.save(scar_store_path, subject.scars)
    return bundles

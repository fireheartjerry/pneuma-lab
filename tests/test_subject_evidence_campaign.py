"""Tests for SubjectEvidenceCampaign-v0: conservative replayable evidence campaigns.

Covers the subject refinement (interventions visible in state/report), the campaign
summary schema, the five evidence slices, deterministic schema-valid artifacts, and
the conservative (no-overclaim) posture.
"""

import json
from pathlib import Path

from pneuma_lab.schemas import validate

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "fixtures" / "nervous_system" / "subject"


def _frames(name):
    return [
        json.loads(x)
        for x in (FIX / name).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]


# --------------------------------------------------------------------------- #
# Task 1: interventions visible in subject state + self-report                #
# --------------------------------------------------------------------------- #
def test_certainty_clamp_changes_state_and_report_but_not_control():
    from pneuma_lab.nervous_system.subject_ablation import run_subject_ablation

    res = run_subject_ablation(
        _frames("clamp_certainty.jsonl"), seed_scars={"m1:regress": 0.5}
    )
    assert res["treated_state"]["state_hash"] != res["control_state"]["state_hash"]
    assert (
        res["treated_report"]["reported_measurements"]["affect_certainty"]
        != res["control_report"]["reported_measurements"]["affect_certainty"]
    )
    assert res["null_holds"] is True
    assert (
        res["control_report"]["affect_state_hash"] == res["control_state"]["state_hash"]
    )

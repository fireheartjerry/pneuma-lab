"""Tests for CertifiedSubjectFactory-v0: the honest promotable subject-factory path.

Covers the snapshot/clone-equivalence certification protocol, the runner eligibility
wiring, the CertifiedBaselineSubjectFactory, and the certified promotable-path
evidence campaign (real provenance, conservative no-overclaim output).
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


class _BaselineFactory:
    """A stable-identity callable factory over BaselinePsycheSubject."""

    def __init__(self, seed):
        self._seed = dict(seed)

    def __call__(self):
        from pneuma_lab.nervous_system.subject import BaselinePsycheSubject

        return BaselinePsycheSubject(scars=dict(self._seed))


# --------------------------------------------------------------------------- #
# Task 1: certification protocol + registry + runner eligibility              #
# --------------------------------------------------------------------------- #
def test_certify_passes_for_deterministic_factory_and_registers():
    from pneuma_lab.interventions import certified_subjects as cs

    cs.clear_registry()
    factory = _BaselineFactory({"m1:regress": 0.5})
    assert cs.is_certified(factory) is False
    result = cs.certify(factory, _frames("ablate_scar.jsonl"))
    assert result["passed"] is True
    assert result["clone_equivalent"] is True
    assert result["reset_deterministic"] is True
    assert result["ordinal_invariant"] is True
    assert result["implements_interface"] is True
    assert cs.is_certified(factory) is True


def test_certify_rejects_nondeterministic_factory():
    from pneuma_lab.interventions import certified_subjects as cs
    from pneuma_lab.nervous_system.subject import BaselinePsycheSubject

    cs.clear_registry()
    counter = {"n": 0}

    class _Flaky(BaselinePsycheSubject):
        def tick(self, inputs):
            counter["n"] += 1
            out = super().tick(inputs)
            out.grounded_self_report["report_text"] += f" nonce={counter['n']}"
            return out

    def flaky_factory():
        return _Flaky(scars={"m1:regress": 0.5})

    result = cs.certify(flaky_factory, _frames("ablate_scar.jsonl"))
    assert result["passed"] is False
    assert result["clone_equivalent"] is False
    assert cs.is_certified(flaky_factory) is False


def test_runner_eligibility_tracks_certification():
    from pneuma_lab.interventions import certified_subjects as cs
    from pneuma_lab.interventions.runner import PairedReplayRunner

    cs.clear_registry()
    factory = _BaselineFactory({"m1:regress": 0.5})
    frames = _frames("ablate_scar.jsonl")
    ev = PairedReplayRunner(psyche_factory=factory).run(frames).evidence_frame
    assert ev["paired_replay_provenance"]["subject_factory_eligible"] is False
    cs.certify(factory, frames)
    ev2 = PairedReplayRunner(psyche_factory=factory).run(frames).evidence_frame
    assert ev2["paired_replay_provenance"]["subject_factory_eligible"] is True
    assert ev2["paired_replay_provenance"]["status"] == "runner_verified"
    # ...but the level stays honestly capped below 3 (no faked promotion)
    assert ev2["evidence_level"] < 3


# --------------------------------------------------------------------------- #
# Task 2: CertifiedBaselineSubjectFactory + certify helper                    #
# --------------------------------------------------------------------------- #
def test_certified_baseline_factory_is_byte_stable_and_earns_eligibility():
    from pneuma_lab.interventions import certified_subjects as cs
    from pneuma_lab.interventions.provenance import output_frames_sha256
    from pneuma_lab.nervous_system.certified_subject import (
        CertifiedBaselineSubjectFactory,
        certify_baseline_subject,
    )
    from pneuma_lab.replay.harness import ReplayHarness

    cs.clear_registry()
    factory = CertifiedBaselineSubjectFactory(seed_scars={"m1:regress": 0.5})
    a = output_frames_sha256(
        ReplayHarness(factory(), validate=True).run(_frames("base.jsonl")).tick_outputs
    )
    b = output_frames_sha256(
        ReplayHarness(factory(), validate=True).run(_frames("base.jsonl")).tick_outputs
    )
    assert a == b
    h = ReplayHarness(factory(), validate=True)
    assert output_frames_sha256(
        h.run(_frames("base.jsonl")).tick_outputs
    ) == output_frames_sha256(h.run(_frames("base.jsonl")).tick_outputs)
    cs.clear_registry()
    certified_factory, result = certify_baseline_subject(seed_scars={"m1:regress": 0.5})
    assert result["passed"] is True
    assert cs.is_certified(certified_factory) is True
    assert "CertifiedBaselineSubjectFactory" in result["subject_factory"]


# --------------------------------------------------------------------------- #
# Task 3: campaign schema optional provenance fields                          #
# --------------------------------------------------------------------------- #
def test_campaign_schema_accepts_provenance_and_certified_overall():
    from pneuma_lab import schemas

    schema = schemas.load_schema("subject-evidence-campaign.schema.json")
    slice_props = schema["properties"]["slices"]["items"]["properties"]
    assert "provenance" in slice_props
    assert "scorer_diagnostic" in slice_props
    overall_props = schema["properties"]["overall"]["properties"]
    assert "certified" in overall_props
    assert "promotion_blocked_by" in overall_props

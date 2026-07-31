"""Narrow tests for the adversarial-review machinery.

These tests exercise the REVIEW MACHINERY ONLY, against a synthetic
non-scientific widget fixture. They deliberately do not run the hostile
campaign against PLACEBO, do not read any scientific artifact, and produce no
scientific evidence of any kind.

    python -m pytest tests/adversarial_review -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.adversarial_review import (
    NON_AUTHORIZATION_NOTICE,
    Claim,
    EvidenceRef,
    Finding,
    Override,
    REVIEWER_ROLE_IDS,
    ROLES,
    render,
    run_campaign,
    write_campaign,
)
from pneuma_lab.adversarial_review.campaign import STAGE_PRE_LAUNCH
from pneuma_lab.adversarial_review.canonical import canonical_json, digest_value
from pneuma_lab.adversarial_review.chair import convert, underspecified_items
from pneuma_lab.adversarial_review.cli import main as cli_main
from pneuma_lab.adversarial_review.conflicts import detect_conflicts
from pneuma_lab.adversarial_review.disposition import (
    LAUNCH_BLOCKED,
    LAUNCH_BLOCKED_BY_CONFLICT,
    NO_BLOCKING_FINDINGS,
    verify_seal,
)
from pneuma_lab.adversarial_review.errors import (
    InputContractError,
    OverrideContractError,
    StaleInputError,
)
from pneuma_lab.adversarial_review.matrix import build_matrix
from pneuma_lab.adversarial_review.records import ReviewerReport, SubprocessReceipt
from pneuma_lab.adversarial_review.severity import BLOCKER, MAJOR, SPECULATION
from pneuma_lab.adversarial_review.subprocess_adapter import ReplaySource, parse_proposal
from pneuma_lab.adversarial_review.validation import verify_finding

from .conftest import FIXTURE_ROLE_IDS, load_fixture_campaign

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "adversarial_review" / "synthetic_campaign"


# --------------------------------------------------------------------------
# Role contract
# --------------------------------------------------------------------------


def test_twelve_roles_exist_with_the_required_mandates() -> None:
    assert len(ROLES) == 12
    assert len(REVIEWER_ROLE_IDS) == 10
    ids = {role.role_id for role in ROLES}
    assert "R11-editor" in ids and "R12-chair" in ids


def test_every_role_prompt_states_the_no_invented_evidence_rule() -> None:
    for role in ROLES:
        prompt = role.prompt()
        assert "may not invent" in prompt
        assert "speculation" in prompt
        assert "UNTRUSTED PROPOSAL" in prompt
        assert "You do not authorize anything." in prompt


def test_mandate_digest_changes_when_the_mandate_changes() -> None:
    from dataclasses import replace

    original = ROLES[0]
    mutated = replace(original, mandate=original.mandate + " Additionally, ...")
    assert original.mandate_digest != mutated.mandate_digest


# --------------------------------------------------------------------------
# Fail-closed input contract
# --------------------------------------------------------------------------


def test_campaign_fails_closed_when_a_declared_input_is_stale(tmp_path: Path) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    (inputs.root / "design.md").write_text("mutated after declaration\n", encoding="utf-8")
    with pytest.raises(StaleInputError):
        run_campaign(
            campaign_id=inputs.campaign_id,
            stage=STAGE_PRE_LAUNCH,
            inputs=inputs,
            claims=claims,
            source=source,
            role_ids=("R02-identification",),
        )


def test_campaign_fails_closed_when_a_required_input_slot_is_absent(tmp_path: Path) -> None:
    from dataclasses import replace

    inputs, claims, source = load_fixture_campaign(tmp_path)
    trimmed = replace(
        inputs,
        objects=tuple(item for item in inputs.objects if item.slot != "design"),
    )
    with pytest.raises(InputContractError, match="missing required input slots"):
        run_campaign(
            campaign_id=trimmed.campaign_id,
            stage=STAGE_PRE_LAUNCH,
            inputs=trimmed,
            claims=claims,
            source=source,
            role_ids=("R02-identification",),
        )


def test_replay_refuses_a_transcript_produced_under_a_different_mandate(
    tmp_path: Path,
) -> None:
    inputs, claims, _ = load_fixture_campaign(tmp_path)
    transcripts = tmp_path / "transcripts"
    path = transcripts / "R02-identification.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["prompt_digest"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(InputContractError, match="different"):
        run_campaign(
            campaign_id=inputs.campaign_id,
            stage=STAGE_PRE_LAUNCH,
            inputs=inputs,
            claims=claims,
            source=ReplaySource(transcript_dir=transcripts),
            role_ids=("R02-identification",),
        )


def test_unknown_stage_is_rejected(tmp_path: Path) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    with pytest.raises(InputContractError, match="unknown campaign stage"):
        run_campaign(
            campaign_id=inputs.campaign_id,
            stage="whenever",
            inputs=inputs,
            claims=claims,
            source=source,
        )


# --------------------------------------------------------------------------
# Evidence grounding: invented evidence cannot block
# --------------------------------------------------------------------------


def test_finding_citing_a_nonexistent_line_is_downgraded_not_deleted(
    tmp_path: Path,
) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    result = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        role_ids=FIXTURE_ROLE_IDS,
    )
    by_id = {item.finding_id: item for item in result.all_findings()}
    assert "F-ST-02" in by_id, "an unverifiable finding must be preserved, not deleted"
    downgraded = by_id["F-ST-02"]
    assert downgraded.severity == SPECULATION
    assert "DOWNGRADED from blocker" in downgraded.statement
    assert downgraded.digest not in result.disposition.blocking_finding_digests


def test_external_source_must_be_registered(tmp_path: Path) -> None:
    inputs, _, _ = load_fixture_campaign(tmp_path)
    finding = Finding(
        finding_id="F-X",
        role_id="R01-novelty",
        severity=BLOCKER,
        title="Prior art",
        statement="Already done.",
        failure_mode="No contribution remains.",
        evidence=(
            EvidenceRef(
                kind="external_source",
                locator="arXiv:2699.99999",
                detail="an unregistered source",
            ),
        ),
        what_would_refute="A reading of the cited paper showing a different scope.",
    )
    outcome = verify_finding(finding, inputs)
    assert not outcome.admissible
    assert any("not in the campaign's declared source list" in item for item in outcome.failures)


def test_quoted_text_absent_from_the_cited_span_fails_grounding(tmp_path: Path) -> None:
    inputs, _, _ = load_fixture_campaign(tmp_path)
    finding = Finding(
        finding_id="F-Q",
        role_id="R09-manuscript",
        severity=MAJOR,
        title="Misquote",
        statement="The design says something it does not say.",
        failure_mode="The criticism attacks a sentence that was never written.",
        evidence=(
            EvidenceRef(
                kind="repo_line",
                locator="design.md",
                start_line=1,
                end_line=2,
                detail="quote check",
                quoted="a sentence that is not in the file",
            ),
        ),
        what_would_refute="Reading the cited lines.",
    )
    outcome = verify_finding(finding, inputs)
    assert not outcome.admissible
    assert any("quotes text absent" in item for item in outcome.failures)


def test_severity_requiring_evidence_cannot_be_asserted_bare(tmp_path: Path) -> None:
    inputs, _, _ = load_fixture_campaign(tmp_path)
    finding = Finding(
        finding_id="F-B",
        role_id="R05-benchmarks",
        severity=BLOCKER,
        title="Bare assertion",
        statement="It is contaminated.",
        failure_mode="Every number is invalid.",
        evidence=(),
        what_would_refute="A contamination audit.",
    )
    outcome = verify_finding(finding, inputs)
    assert not outcome.admissible
    assert any("requires at least one evidence reference" in item for item in outcome.failures)


# --------------------------------------------------------------------------
# Dissent, minority, and the claim matrix
# --------------------------------------------------------------------------


def test_speculation_is_preserved_but_never_attacks_a_claim(tmp_path: Path) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    result = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        role_ids=FIXTURE_ROLE_IDS,
    )
    speculation = [item for item in result.all_findings() if item.severity == SPECULATION]
    assert speculation, "the fixture carries an explicit speculation finding"
    assert any("cherry-picked" in item.title for item in speculation)

    c3 = next(row for row in result.synthesis.claim_matrix if row.claim_id == "C3")
    assert c3.attacking_findings == (), "speculation must not register as an attack"
    assert any("barred from blocking" in note for note in result.synthesis.dissent_notes)


def test_minority_findings_survive_synthesis(tmp_path: Path) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    result = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        role_ids=FIXTURE_ROLE_IDS,
    )
    assert result.synthesis.minority_findings
    argument = result.synthesis.strongest_rejection_argument
    assert "Minority findings, preserved and not averaged away" in argument


def test_claim_without_supporting_evidence_is_marked_unsupported() -> None:
    rows = build_matrix(
        (
            Claim(claim_id="A", text="asserted", kind="claim_of_record"),
            Claim(
                claim_id="B",
                text="supported",
                kind="claim_of_record",
                supporting_evidence=("receipt:r1",),
            ),
        ),
        (),
    )
    assert rows[0].unsupported is True
    assert rows[1].unsupported is False


# --------------------------------------------------------------------------
# Conflict of interest
# --------------------------------------------------------------------------


def _report(role_id: str, prompt_digest: str, dependencies: tuple[str, ...] = ()) -> ReviewerReport:
    from pneuma_lab.adversarial_review.roles import ROLES_BY_ID

    return ReviewerReport(
        role_id=role_id,
        role_title=ROLES_BY_ID[role_id].title,
        mandate_digest=ROLES_BY_ID[role_id].mandate_digest,
        findings=(),
        declared_dependencies=dependencies,
        receipt=SubprocessReceipt(
            role_id=role_id,
            engine="fixture",
            model="m",
            task="t",
            prompt_digest=prompt_digest,
            response_digest="0" * 64,
        ),
    )


def test_shared_context_within_a_conflict_group_blocks() -> None:
    conflicts = detect_conflicts(
        (
            _report("R02-identification", "a" * 64),
            _report("R03-statistics", "a" * 64),
        )
    )
    assert conflicts
    assert conflicts[0].kind == "shared_context"
    assert conflicts[0].blocking is True


def test_peer_dependency_between_stage_one_reviewers_blocks() -> None:
    conflicts = detect_conflicts(
        (_report("R05-benchmarks", "b" * 64, dependencies=("R02-identification",)),)
    )
    assert any(item.kind == "declared_dependency" and item.blocking for item in conflicts)


def test_a_blocking_conflict_invalidates_the_campaign_verdict(tmp_path: Path) -> None:
    from pneuma_lab.adversarial_review.disposition import decide
    from pneuma_lab.adversarial_review.editor import synthesize

    reports = (
        _report("R02-identification", "c" * 64),
        _report("R03-statistics", "c" * 64),
    )
    synthesis = synthesize(reports, ())
    disposition = decide(
        campaign_id="conflicted",
        stage=STAGE_PRE_LAUNCH,
        inputs_digest="0" * 64,
        reports=reports,
        synthesis=synthesis,
        items=(),
        conflicts=detect_conflicts(reports),
    )
    assert disposition.verdict == LAUNCH_BLOCKED_BY_CONFLICT


# --------------------------------------------------------------------------
# Falsification chair
# --------------------------------------------------------------------------


def test_chair_converts_blockers_into_owned_blocking_tests(tmp_path: Path) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    result = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        role_ids=FIXTURE_ROLE_IDS,
    )
    blocking = [item for item in result.falsification if item.disposition == "blocking"]
    assert len(blocking) == 1
    item = blocking[0]
    assert item.owner == "design-owner"
    assert item.gate == "pre_launch"
    assert item.test_statement.startswith("Test: ")
    assert "PASS means" in item.test_statement and "FAIL means" in item.test_statement


def test_chair_flags_a_finding_with_no_refutation_condition() -> None:
    finding = Finding(
        finding_id="F-U",
        role_id="R06-infrastructure",
        severity=MAJOR,
        title="Something feels wrong about resume",
        statement="Unspecified.",
        failure_mode="Unspecified.",
        evidence=(),
        what_would_refute="",
    )
    items = convert((finding,))
    assert underspecified_items(items)


def test_speculation_never_enters_the_falsification_schedule() -> None:
    finding = Finding(
        finding_id="F-S",
        role_id="R01-novelty",
        severity=SPECULATION,
        title="Probably not novel",
        statement="No source cited.",
        failure_mode="Unclear.",
        evidence=(),
    )
    assert convert((finding,)) == ()


# --------------------------------------------------------------------------
# Disposition, overrides, sealing
# --------------------------------------------------------------------------


def test_disposition_is_hash_bound_and_authorizes_nothing(tmp_path: Path) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    result = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        role_ids=FIXTURE_ROLE_IDS,
    )
    assert result.disposition.verdict == LAUNCH_BLOCKED
    assert verify_seal(result.disposition)
    assert result.disposition.non_authorization_notice == NON_AUTHORIZATION_NOTICE
    assert "authorizes nothing" in NON_AUTHORIZATION_NOTICE
    for forbidden in ("authorized", "approved", "cleared_to_launch"):
        assert result.disposition.verdict != forbidden


def test_tampering_with_a_sealed_disposition_is_detectable(tmp_path: Path) -> None:
    from dataclasses import replace

    inputs, claims, source = load_fixture_campaign(tmp_path)
    result = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        role_ids=FIXTURE_ROLE_IDS,
    )
    tampered = replace(result.disposition, verdict=NO_BLOCKING_FINDINGS)
    assert not verify_seal(tampered)


def test_signed_override_unblocks_without_erasing_the_finding(tmp_path: Path) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    baseline = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        role_ids=FIXTURE_ROLE_IDS,
    )
    blocker_digest = baseline.disposition.blocking_finding_digests[0]
    override = Override(
        finding_digest=blocker_digest,
        signer="J. Reviewer",
        signer_role="principal-investigator",
        rationale=(
            "The toy fixture has no assignment mechanism because it is a "
            "fixture; the risk is accepted for machinery testing only."
        ),
        signature="synthetic-signature-not-a-real-key",
        accepted_risk="No causal claim may be made from this fixture.",
    )
    overridden = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        overrides=(override,),
        role_ids=FIXTURE_ROLE_IDS,
    )
    assert overridden.disposition.verdict == NO_BLOCKING_FINDINGS
    assert blocker_digest in overridden.disposition.overridden_finding_digests
    digests = {item.digest for item in overridden.all_findings()}
    assert blocker_digest in digests, "an override must never erase the finding"
    assert blocker_digest in render(overridden)


def test_override_of_an_unknown_finding_is_rejected(tmp_path: Path) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    override = Override(
        finding_digest="f" * 64,
        signer="Someone",
        signer_role="unknown",
        rationale="A rationale long enough to pass the substantive-statement floor.",
        signature="sig",
        accepted_risk="none stated",
    )
    with pytest.raises(OverrideContractError, match="unknown finding"):
        run_campaign(
            campaign_id=inputs.campaign_id,
            stage=STAGE_PRE_LAUNCH,
            inputs=inputs,
            claims=claims,
            source=source,
            role_ids=FIXTURE_ROLE_IDS,
            overrides=(override,),
        )


def test_override_requires_a_substantive_signed_rationale() -> None:
    with pytest.raises(InputContractError, match="substantive signed statement"):
        Override(
            finding_digest="a" * 64,
            signer="S",
            signer_role="pi",
            rationale="fine",
            signature="sig",
            accepted_risk="none",
        )


# --------------------------------------------------------------------------
# Determinism and artifacts
# --------------------------------------------------------------------------


def test_campaign_replays_byte_identically(tmp_path: Path) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    first = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        role_ids=FIXTURE_ROLE_IDS,
    )
    second = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        role_ids=FIXTURE_ROLE_IDS,
    )
    assert canonical_json(first.to_canonical()) == canonical_json(second.to_canonical())
    assert render(first) == render(second)
    assert first.disposition.disposition_digest == second.disposition.disposition_digest


def test_written_artifacts_are_canonical_and_complete(tmp_path: Path) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    result = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        role_ids=FIXTURE_ROLE_IDS,
    )
    out = tmp_path / "out"
    digests = write_campaign(result, out)
    for name in (
        "campaign.json",
        "findings.json",
        "claim-matrix.json",
        "falsification.json",
        "disposition.json",
    ):
        assert (out / name).is_file()
        assert name in digests
    payload = json.loads((out / "campaign.json").read_text(encoding="utf-8"))
    assert payload["disposition"]["disposition_digest"] == (
        result.disposition.disposition_digest
    )
    assert digest_value(payload["synthesis"]["claim_matrix"]) == digests["claim-matrix.json"]


def test_report_names_the_verdict_and_preserves_dissent(tmp_path: Path) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    result = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        role_ids=FIXTURE_ROLE_IDS,
    )
    text = render(result)
    assert "**Verdict:** `launch_blocked`" in text
    assert "## Preserved dissent" in text
    assert "## Evidence-to-claim matrix" in text
    assert "## Subprocess receipts" in text
    assert "authorizes nothing" in text


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_cli_exits_nonzero_when_blocked(tmp_path: Path, capsys) -> None:
    out = tmp_path / "cli-out"
    code = cli_main(
        ["run", "--spec", str(FIXTURE / "campaign-spec.json"), "--out", str(out)]
    )
    assert code == 1
    assert (out / "rejection-report.md").is_file()
    assert "verdict: launch_blocked" in capsys.readouterr().out


def test_cli_fails_closed_on_a_missing_spec(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        cli_main(["run", "--spec", str(tmp_path / "nope.json"), "--out", str(tmp_path)])


def test_cli_prompt_renders_one_role(capsys) -> None:
    assert cli_main(["prompt", "--role", "R03-statistics"]) == 0
    assert "Statistical validity" in capsys.readouterr().out


# --------------------------------------------------------------------------
# The system reviews nothing scientific by accident
# --------------------------------------------------------------------------


def test_fixture_is_non_scientific(tmp_path: Path) -> None:
    """The committed fixture must not reference real study artifacts."""

    text = (FIXTURE / "campaign-spec.json").read_text(encoding="utf-8")
    for forbidden in ("resampling", "swe-bench", "tau2", "Qwen", "placebo"):
        assert forbidden.lower() not in text.lower()


def test_parse_proposal_rejects_a_role_mismatch() -> None:
    from pneuma_lab.adversarial_review.roles import ROLES_BY_ID

    receipt = SubprocessReceipt(
        role_id="R01-novelty",
        engine="fixture",
        model="m",
        task="t",
        prompt_digest="0" * 64,
        response_digest="0" * 64,
    )
    with pytest.raises(InputContractError, match="claims role"):
        parse_proposal(
            ROLES_BY_ID["R01-novelty"],
            json.dumps({"role_id": "R09-manuscript", "findings": []}),
            receipt,
        )


def test_parse_proposal_rejects_non_json_output() -> None:
    from pneuma_lab.adversarial_review.roles import ROLES_BY_ID

    receipt = SubprocessReceipt(
        role_id="R01-novelty",
        engine="fixture",
        model="m",
        task="t",
        prompt_digest="0" * 64,
        response_digest="0" * 64,
    )
    with pytest.raises(InputContractError):
        parse_proposal(ROLES_BY_ID["R01-novelty"], "I think this paper is bad.", receipt)

"""Campaign orchestration for the two-stage adversarial review.

Stage one runs the ten independent reviewers. Stage two runs the editor and
the falsification chair over the sealed stage-one reports. The two stages are
separated so that no reviewer can read a peer's findings, which is the only
thing that makes twelve reviews more informative than one.

The whole campaign is deterministic given the same inputs and the same sealed
proposals: canonical ordering everywhere, no clocks in the record, and a
disposition digest that binds every component.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical import canonical_json, digest_value
from .chair import convert
from .conflicts import ConflictFinding, detect_conflicts
from .disposition import decide
from .editor import synthesize
from .errors import InputContractError
from .inputs import CampaignInputs, preflight, required_slots_for
from .matrix import Claim
from .records import (
    EditorSynthesis,
    FalsificationItem,
    Finding,
    Override,
    ReadinessDisposition,
    ReviewerReport,
    VerificationOutcome,
)
from .roles import REVIEWER_ROLE_IDS, ROLES_BY_ID
from .subprocess_adapter import ProposalSource, parse_proposal
from .validation import duplicate_finding_ids, verify_all

STAGE_PRE_LAUNCH = "stage_1_pre_launch"
STAGE_PRE_SUBMISSION = "stage_2_pre_submission"
STAGES = (STAGE_PRE_LAUNCH, STAGE_PRE_SUBMISSION)


@dataclass(frozen=True)
class CampaignResult:
    """Everything one campaign produced."""

    campaign_id: str
    stage: str
    inputs_digest: str
    reports: tuple[ReviewerReport, ...]
    verifications: tuple[VerificationOutcome, ...]
    conflicts: tuple[ConflictFinding, ...]
    synthesis: EditorSynthesis
    falsification: tuple[FalsificationItem, ...]
    disposition: ReadinessDisposition

    def to_canonical(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "stage": self.stage,
            "inputs_digest": self.inputs_digest,
            "reports": [item.to_canonical() for item in self.reports],
            "verifications": [item.to_canonical() for item in self.verifications],
            "conflicts": [item.to_canonical() for item in self.conflicts],
            "synthesis": self.synthesis.to_canonical(),
            "falsification": [item.to_canonical() for item in self.falsification],
            "disposition": {
                **self.disposition.to_canonical(),
                "disposition_digest": self.disposition.disposition_digest,
            },
        }

    def all_findings(self) -> tuple[Finding, ...]:
        return tuple(item for report in self.reports for item in report.findings)


def run_campaign(
    *,
    campaign_id: str,
    stage: str,
    inputs: CampaignInputs,
    claims: Sequence[Claim],
    source: ProposalSource,
    role_ids: Sequence[str] = REVIEWER_ROLE_IDS,
    overrides: Sequence[Override] = (),
    discharged: Mapping[str, str] | None = None,
) -> CampaignResult:
    """Run one complete two-stage campaign and return its sealed result."""

    if stage not in STAGES:
        raise InputContractError(f"unknown campaign stage {stage!r}")
    if inputs.stage != stage:
        raise InputContractError(
            f"input bundle declares stage {inputs.stage!r} but campaign is {stage!r}"
        )
    unknown = [item for item in role_ids if item not in ROLES_BY_ID]
    if unknown:
        raise InputContractError(f"unknown reviewer roles: {sorted(unknown)}")

    preflight(inputs, required_slots_for(role_ids))

    reports: list[ReviewerReport] = []
    verifications: list[VerificationOutcome] = []
    for role_id in sorted(role_ids):
        role = ROLES_BY_ID[role_id]
        text, receipt = source.run(role, role.prompt())
        proposal = parse_proposal(role, text, receipt)
        recorded, outcomes = verify_all(proposal.findings, inputs)
        duplicates = duplicate_finding_ids(recorded)
        if duplicates:
            raise InputContractError(
                f"role {role_id} emitted duplicate finding ids: {list(duplicates)}"
            )
        verifications.extend(outcomes)
        reports.append(
            ReviewerReport(
                role_id=proposal.role_id,
                role_title=proposal.role_title,
                mandate_digest=proposal.mandate_digest,
                findings=recorded,
                coverage_notes=proposal.coverage_notes,
                declared_dependencies=proposal.declared_dependencies,
                receipt=proposal.receipt,
            )
        )

    sealed_reports = tuple(sorted(reports, key=lambda item: item.role_id))
    conflicts = detect_conflicts(sealed_reports)

    synthesis = synthesize(sealed_reports, claims)
    findings = tuple(item for report in sealed_reports for item in report.findings)
    items = convert(findings, results_exist=stage == STAGE_PRE_SUBMISSION)

    disposition = decide(
        campaign_id=campaign_id,
        stage=stage,
        inputs_digest=inputs.digest,
        reports=sealed_reports,
        synthesis=synthesis,
        items=items,
        conflicts=conflicts,
        overrides=overrides,
        discharged=discharged,
    )

    return CampaignResult(
        campaign_id=campaign_id,
        stage=stage,
        inputs_digest=inputs.digest,
        reports=sealed_reports,
        verifications=tuple(verifications),
        conflicts=conflicts,
        synthesis=synthesis,
        falsification=items,
        disposition=disposition,
    )


def write_campaign(result: CampaignResult, out_dir: Path) -> dict[str, str]:
    """Write the machine-readable campaign artifacts, returning path digests."""

    out_dir.mkdir(parents=True, exist_ok=True)
    payload = result.to_canonical()
    written: dict[str, str] = {}
    for name, value in (
        ("campaign.json", payload),
        ("findings.json", payload["reports"]),
        ("claim-matrix.json", payload["synthesis"]["claim_matrix"]),
        ("falsification.json", payload["falsification"]),
        ("disposition.json", payload["disposition"]),
    ):
        text = canonical_json(value)
        (out_dir / name).write_text(text, encoding="utf-8")
        written[name] = digest_value(value)
    return written

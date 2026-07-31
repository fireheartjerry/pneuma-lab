"""Record types for the PLACEBO adversarial-review system.

Every record is a frozen dataclass with an explicit canonical mapping. Records
are the only currency of the system: reviewer subprocesses emit *proposals*
that are parsed into these types and then verified, and nothing that fails
parsing or verification is ever promoted into a campaign artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .canonical import digest_value, is_sha256_hex
from .errors import InputContractError
from .severity import SEVERITIES, is_valid_severity

#: The kinds of evidence a finding may cite. A finding whose evidence is not
#: one of these kinds cannot be verified and is therefore not admissible.
EVIDENCE_KINDS = (
    "repo_line",  # exact file + line range inside the pinned commit
    "receipt",  # a digest-bound artifact receipt in the campaign bundle
    "artifact_digest",  # a raw file digest inside the declared artifact root
    "external_source",  # a primary external source: DOI, arXiv id, or URL
    "command",  # a reproduction command with expected observable outcome
    "manuscript_span",  # a located span in the manuscript sources
)

#: Dispositions the falsification chair may assign to a finding.
CHAIR_DISPOSITIONS = (
    "blocking",  # must be discharged before the gated action
    "non_blocking_tracked",  # recorded, owner assigned, does not block
    "refuted",  # discharged by counter-evidence at review time
    "deferred_post_results",  # only testable after results exist
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InputContractError(message)


def _require_text(value: object, label: str) -> str:
    _require(isinstance(value, str) and value.strip() != "", f"{label} must be non-empty text")
    assert isinstance(value, str)
    return value


@dataclass(frozen=True)
class EvidenceRef:
    """One verifiable pointer supporting a finding.

    ``locator`` meaning depends on ``kind``:

    ``repo_line``        repository-relative path, with ``start_line``/``end_line``
    ``receipt``          receipt id as it appears in the campaign receipt index
    ``artifact_digest``  artifact-root-relative path
    ``external_source``  a DOI, ``arXiv:NNNN.NNNNN``, or absolute ``https`` URL
    ``command``          the exact shell command
    ``manuscript_span``  manuscript-relative path, with line range
    """

    kind: str
    locator: str
    detail: str
    start_line: int | None = None
    end_line: int | None = None
    expected_digest: str | None = None
    quoted: str | None = None

    def __post_init__(self) -> None:
        _require(self.kind in EVIDENCE_KINDS, f"unknown evidence kind {self.kind!r}")
        _require_text(self.locator, "evidence locator")
        _require_text(self.detail, "evidence detail")
        if self.kind in ("repo_line", "manuscript_span"):
            _require(
                isinstance(self.start_line, int) and self.start_line >= 1,
                f"{self.kind} evidence requires a 1-indexed start_line",
            )
            end = self.end_line if self.end_line is not None else self.start_line
            _require(
                isinstance(end, int) and end >= int(self.start_line or 0),
                f"{self.kind} evidence requires end_line >= start_line",
            )
        if self.expected_digest is not None:
            _require(
                is_sha256_hex(self.expected_digest),
                "expected_digest must be lowercase hex sha256",
            )

    def to_canonical(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "locator": self.locator,
            "detail": self.detail,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "expected_digest": self.expected_digest,
            "quoted": self.quoted,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "EvidenceRef":
        return cls(
            kind=str(payload.get("kind", "")),
            locator=str(payload.get("locator", "")),
            detail=str(payload.get("detail", "")),
            start_line=payload.get("start_line"),
            end_line=payload.get("end_line"),
            expected_digest=payload.get("expected_digest"),
            quoted=payload.get("quoted"),
        )


@dataclass(frozen=True)
class Finding:
    """One adversarial finding from one reviewer role.

    A finding is an *accusation with a receipt*. ``claim_ids`` binds it to the
    manuscript or design claims it attacks, which is what makes the
    evidence-to-claim matrix computable rather than editorial.
    """

    finding_id: str
    role_id: str
    severity: str
    title: str
    statement: str
    failure_mode: str
    evidence: tuple[EvidenceRef, ...]
    claim_ids: tuple[str, ...] = ()
    reproduction: tuple[str, ...] = ()
    what_would_refute: str = ""
    confidence: str = "asserted"

    def __post_init__(self) -> None:
        _require_text(self.finding_id, "finding_id")
        _require_text(self.role_id, "role_id")
        _require(is_valid_severity(self.severity), f"severity must be one of {SEVERITIES}")
        _require_text(self.title, "finding title")
        _require_text(self.statement, "finding statement")
        _require_text(self.failure_mode, "failure_mode")
        _require(
            isinstance(self.evidence, tuple),
            "evidence must be a tuple of EvidenceRef",
        )

    def to_canonical(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "role_id": self.role_id,
            "severity": self.severity,
            "title": self.title,
            "statement": self.statement,
            "failure_mode": self.failure_mode,
            "evidence": [ref.to_canonical() for ref in self.evidence],
            "claim_ids": list(self.claim_ids),
            "reproduction": list(self.reproduction),
            "what_would_refute": self.what_would_refute,
            "confidence": self.confidence,
        }

    @property
    def digest(self) -> str:
        """Content digest, used as the tamper-evident identity of the finding."""

        return digest_value(self.to_canonical())

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "Finding":
        raw_evidence = payload.get("evidence", ())
        _require(isinstance(raw_evidence, Sequence), "evidence must be a sequence")
        return cls(
            finding_id=str(payload.get("finding_id", "")),
            role_id=str(payload.get("role_id", "")),
            severity=str(payload.get("severity", "")),
            title=str(payload.get("title", "")),
            statement=str(payload.get("statement", "")),
            failure_mode=str(payload.get("failure_mode", "")),
            evidence=tuple(EvidenceRef.from_mapping(item) for item in raw_evidence),
            claim_ids=tuple(str(item) for item in payload.get("claim_ids", ())),
            reproduction=tuple(str(item) for item in payload.get("reproduction", ())),
            what_would_refute=str(payload.get("what_would_refute", "")),
            confidence=str(payload.get("confidence", "asserted")),
        )


@dataclass(frozen=True)
class SubprocessReceipt:
    """Compact, cost-bounded receipt for one reviewer subprocess invocation.

    Recorded whether or not the subprocess produced admissible findings. A
    campaign with an unrecorded subprocess is not replayable and fails closed.
    """

    role_id: str
    engine: str
    model: str
    task: str
    prompt_digest: str
    response_digest: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd_upper_bound: float = 0.0
    wall_clock_seconds: float | None = None
    exit_status: str = "ok"

    def to_canonical(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "engine": self.engine,
            "model": self.model,
            "task": self.task,
            "prompt_digest": self.prompt_digest,
            "response_digest": self.response_digest,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd_upper_bound": self.cost_usd_upper_bound,
            "wall_clock_seconds": self.wall_clock_seconds,
            "exit_status": self.exit_status,
        }


@dataclass(frozen=True)
class ReviewerReport:
    """The complete output of one reviewer role."""

    role_id: str
    role_title: str
    mandate_digest: str
    findings: tuple[Finding, ...]
    coverage_notes: tuple[str, ...] = ()
    declared_dependencies: tuple[str, ...] = ()
    receipt: SubprocessReceipt | None = None

    def to_canonical(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_title": self.role_title,
            "mandate_digest": self.mandate_digest,
            "findings": [item.to_canonical() for item in self.findings],
            "coverage_notes": list(self.coverage_notes),
            "declared_dependencies": list(self.declared_dependencies),
            "receipt": self.receipt.to_canonical() if self.receipt else None,
        }


@dataclass(frozen=True)
class VerificationOutcome:
    """Result of grounding one finding against the declared inputs."""

    finding_digest: str
    admissible: bool
    checked_refs: int
    failures: tuple[str, ...] = ()
    downgraded_to: str | None = None

    def to_canonical(self) -> dict[str, Any]:
        return {
            "finding_digest": self.finding_digest,
            "admissible": self.admissible,
            "checked_refs": self.checked_refs,
            "failures": list(self.failures),
            "downgraded_to": self.downgraded_to,
        }


@dataclass(frozen=True)
class ClaimRow:
    """One row of the evidence-to-claim matrix."""

    claim_id: str
    claim_text: str
    supporting_evidence: tuple[str, ...]
    attacking_findings: tuple[str, ...]
    unsupported: bool

    def to_canonical(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "supporting_evidence": list(self.supporting_evidence),
            "attacking_findings": list(self.attacking_findings),
            "unsupported": self.unsupported,
        }


@dataclass(frozen=True)
class FalsificationItem:
    """A finding converted into a concrete, ownable falsification test."""

    finding_digest: str
    role_id: str
    severity: str
    test_statement: str
    required_evidence: tuple[str, ...]
    owner: str
    disposition: str
    gate: str

    def __post_init__(self) -> None:
        _require(
            self.disposition in CHAIR_DISPOSITIONS,
            f"chair disposition must be one of {CHAIR_DISPOSITIONS}",
        )

    def to_canonical(self) -> dict[str, Any]:
        return {
            "finding_digest": self.finding_digest,
            "role_id": self.role_id,
            "severity": self.severity,
            "test_statement": self.test_statement,
            "required_evidence": list(self.required_evidence),
            "owner": self.owner,
            "disposition": self.disposition,
            "gate": self.gate,
        }


@dataclass(frozen=True)
class Override:
    """A signed human override of one finding's blocking effect.

    An override NEVER deletes the finding. It records that a named human, with
    a rationale, accepted the risk. The original finding, its evidence, and its
    severity remain in the artifact verbatim.
    """

    finding_digest: str
    signer: str
    signer_role: str
    rationale: str
    signature: str
    accepted_risk: str

    def __post_init__(self) -> None:
        _require_text(self.finding_digest, "override finding_digest")
        _require_text(self.signer, "override signer")
        _require_text(self.signer_role, "override signer_role")
        _require(
            isinstance(self.rationale, str) and len(self.rationale.strip()) >= 40,
            "override rationale must be a substantive signed statement (>= 40 chars)",
        )
        _require_text(self.signature, "override signature")
        _require_text(self.accepted_risk, "override accepted_risk")

    def to_canonical(self) -> dict[str, Any]:
        return {
            "finding_digest": self.finding_digest,
            "signer": self.signer,
            "signer_role": self.signer_role,
            "rationale": self.rationale,
            "signature": self.signature,
            "accepted_risk": self.accepted_risk,
        }


@dataclass(frozen=True)
class EditorSynthesis:
    """The editor's strongest-rejection case, with dissent preserved."""

    strongest_rejection_argument: str
    ordered_finding_digests: tuple[str, ...]
    minority_findings: tuple[str, ...]
    dissent_notes: tuple[str, ...] = ()
    claim_matrix: tuple[ClaimRow, ...] = ()

    def to_canonical(self) -> dict[str, Any]:
        return {
            "strongest_rejection_argument": self.strongest_rejection_argument,
            "ordered_finding_digests": list(self.ordered_finding_digests),
            "minority_findings": list(self.minority_findings),
            "dissent_notes": list(self.dissent_notes),
            "claim_matrix": [row.to_canonical() for row in self.claim_matrix],
        }


@dataclass(frozen=True)
class ReadinessDisposition:
    """The hash-bound campaign outcome.

    ``verdict`` is deliberately negative-framed. The system can say
    ``launch_blocked`` or ``no_blocking_findings``; it can never say
    ``authorized``, because authorising an experiment, a spend, a claim, or a
    submission is outside this system's power.
    """

    campaign_id: str
    stage: str
    verdict: str
    inputs_digest: str
    reports_digest: str
    synthesis_digest: str
    falsification_digest: str
    blocking_finding_digests: tuple[str, ...]
    overridden_finding_digests: tuple[str, ...]
    non_authorization_notice: str
    disposition_digest: str = field(default="", compare=False)

    def to_canonical(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "stage": self.stage,
            "verdict": self.verdict,
            "inputs_digest": self.inputs_digest,
            "reports_digest": self.reports_digest,
            "synthesis_digest": self.synthesis_digest,
            "falsification_digest": self.falsification_digest,
            "blocking_finding_digests": list(self.blocking_finding_digests),
            "overridden_finding_digests": list(self.overridden_finding_digests),
            "non_authorization_notice": self.non_authorization_notice,
        }

    def sealed(self) -> "ReadinessDisposition":
        """Return a copy whose ``disposition_digest`` binds every other field."""

        return ReadinessDisposition(
            campaign_id=self.campaign_id,
            stage=self.stage,
            verdict=self.verdict,
            inputs_digest=self.inputs_digest,
            reports_digest=self.reports_digest,
            synthesis_digest=self.synthesis_digest,
            falsification_digest=self.falsification_digest,
            blocking_finding_digests=self.blocking_finding_digests,
            overridden_finding_digests=self.overridden_finding_digests,
            non_authorization_notice=self.non_authorization_notice,
            disposition_digest=digest_value(self.to_canonical()),
        )

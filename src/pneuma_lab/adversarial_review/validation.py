"""Mechanical grounding of reviewer findings against the declared inputs.

A reviewer's output is an untrusted proposal. This module is the only thing
standing between "a plausible-sounding criticism" and "a finding in the
campaign record". Each evidence reference is resolved against the pinned
inputs; a reference that does not resolve is invented evidence.

The consequence of failure is deliberately asymmetric. A finding whose
evidence does not resolve is not deleted — deletion would let a reviewer's
sloppiness erase a real defect and would violate the dissent-preservation
rule. It is DOWNGRADED to ``speculation`` and recorded with the exact
verification failures attached, which strips its blocking power while keeping
it readable.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Sequence

from .inputs import CampaignInputs
from .records import EvidenceRef, Finding, VerificationOutcome
from .severity import SPECULATION, requires_evidence

_ARXIV = re.compile(r"^arXiv:\d{4}\.\d{4,5}(v\d+)?$")
_DOI = re.compile(r"^10\.\d{4,9}/\S+$")
_URL = re.compile(r"^https://\S+$")


def verify_evidence(ref: EvidenceRef, inputs: CampaignInputs) -> tuple[str, ...]:
    """Return the verification failures for one evidence reference.

    An empty tuple means the reference resolved.
    """

    if ref.kind in ("repo_line", "manuscript_span"):
        return _verify_span(ref, inputs)
    if ref.kind == "receipt":
        if ref.locator not in inputs.receipt_index:
            return (f"receipt {ref.locator!r} is not in the campaign receipt index",)
        expected = inputs.receipt_index[ref.locator]
        if ref.expected_digest is not None and ref.expected_digest != expected:
            return (
                f"receipt {ref.locator!r} digest mismatch: cited "
                f"{ref.expected_digest}, index holds {expected}",
            )
        return ()
    if ref.kind == "artifact_digest":
        return _verify_artifact(ref, inputs)
    if ref.kind == "external_source":
        if _ARXIV.match(ref.locator) or _DOI.match(ref.locator) or _URL.match(ref.locator):
            if ref.locator in inputs.external_sources:
                return ()
            return (
                f"external source {ref.locator!r} is not in the campaign's "
                "declared source list; a reviewer may not introduce an "
                "unregistered source",
            )
        return (
            f"external source {ref.locator!r} is not a DOI, arXiv id, or https URL",
        )
    if ref.kind == "command":
        if not ref.locator.strip():
            return ("command evidence must carry the exact command",)
        if not ref.detail.strip():
            return ("command evidence must state the expected observable outcome",)
        return ()
    return (f"unhandled evidence kind {ref.kind!r}",)  # pragma: no cover


def _verify_span(ref: EvidenceRef, inputs: CampaignInputs) -> tuple[str, ...]:
    path = _resolve_within_root(ref.locator, inputs)
    if path is None:
        return (f"{ref.kind} evidence path {ref.locator!r} does not resolve inside the campaign root",)
    if not path.is_file():
        return (f"{ref.kind} evidence path {ref.locator!r} is not a file",)
    try:
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    except UnicodeDecodeError:
        return (f"{ref.kind} evidence path {ref.locator!r} is not UTF-8 text",)
    start = int(ref.start_line or 0)
    end = int(ref.end_line or start)
    if start < 1 or end > len(lines):
        return (
            f"{ref.kind} evidence cites lines {start}-{end} of {ref.locator!r}, "
            f"which has {len(lines)} lines",
        )
    if ref.quoted:
        window = "\n".join(lines[start - 1 : end])
        if ref.quoted.strip() not in window:
            return (
                f"{ref.kind} evidence quotes text absent from "
                f"{ref.locator}:{start}-{end}",
            )
    return ()


def _verify_artifact(ref: EvidenceRef, inputs: CampaignInputs) -> tuple[str, ...]:
    from .canonical import digest_file

    path = _resolve_within_root(ref.locator, inputs)
    if path is None or not path.is_file():
        return (f"artifact {ref.locator!r} does not resolve to a file in the campaign root",)
    if ref.expected_digest is None:
        return ("artifact_digest evidence must cite the expected sha256",)
    actual = digest_file(str(path))
    if actual != ref.expected_digest:
        return (
            f"artifact {ref.locator!r} digest mismatch: cited "
            f"{ref.expected_digest}, observed {actual}",
        )
    return ()


def _resolve_within_root(locator: str, inputs: CampaignInputs) -> Path | None:
    root = inputs.root.resolve()
    candidate = (root / locator).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def verify_finding(finding: Finding, inputs: CampaignInputs) -> VerificationOutcome:
    """Ground one finding, downgrading it to speculation when evidence fails."""

    failures: list[str] = []
    for index, ref in enumerate(finding.evidence):
        for message in verify_evidence(ref, inputs):
            failures.append(f"evidence[{index}]: {message}")

    if requires_evidence(finding.severity) and not finding.evidence:
        failures.append(
            f"severity {finding.severity!r} requires at least one evidence reference"
        )
    if requires_evidence(finding.severity) and not finding.what_would_refute.strip():
        failures.append(
            f"severity {finding.severity!r} requires a stated refutation condition"
        )

    admissible = not failures
    return VerificationOutcome(
        finding_digest=finding.digest,
        admissible=admissible,
        checked_refs=len(finding.evidence),
        failures=tuple(failures),
        downgraded_to=None if admissible else SPECULATION,
    )


def apply_outcome(finding: Finding, outcome: VerificationOutcome) -> Finding:
    """Return the finding as it enters the record, after verification.

    The original severity is preserved in the statement so the downgrade is
    auditable rather than silent.
    """

    if outcome.admissible or outcome.downgraded_to is None:
        return finding
    note = (
        f" [DOWNGRADED from {finding.severity} to {outcome.downgraded_to}: "
        + "; ".join(outcome.failures)
        + "]"
    )
    return Finding(
        finding_id=finding.finding_id,
        role_id=finding.role_id,
        severity=outcome.downgraded_to,
        title=finding.title,
        statement=finding.statement + note,
        failure_mode=finding.failure_mode,
        evidence=finding.evidence,
        claim_ids=finding.claim_ids,
        reproduction=finding.reproduction,
        what_would_refute=finding.what_would_refute,
        confidence="unverified",
    )


def verify_all(
    findings: Sequence[Finding], inputs: CampaignInputs
) -> tuple[tuple[Finding, ...], tuple[VerificationOutcome, ...]]:
    """Verify a sequence of findings, returning recorded findings and outcomes."""

    recorded: list[Finding] = []
    outcomes: list[VerificationOutcome] = []
    for finding in findings:
        outcome = verify_finding(finding, inputs)
        outcomes.append(outcome)
        recorded.append(apply_outcome(finding, outcome))
    return tuple(recorded), tuple(outcomes)


def duplicate_finding_ids(findings: Iterable[Finding]) -> tuple[str, ...]:
    """Return finding ids that appear more than once."""

    seen: dict[str, int] = {}
    for finding in findings:
        seen[finding.finding_id] = seen.get(finding.finding_id, 0) + 1
    return tuple(sorted(key for key, count in seen.items() if count > 1))

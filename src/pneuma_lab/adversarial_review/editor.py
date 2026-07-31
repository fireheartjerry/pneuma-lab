"""The editor: deterministic strongest-rejection synthesis with dissent kept.

The editor is mechanical on purpose. A narrative editor is exactly the
component that would quietly average away a lone reviewer's decisive finding,
so the ordering, the minority set, and the sufficient rejection set are all
computed by rule. The prose the editor emits is assembled from those computed
facts, not the other way round.

Ordering rule, applied in sequence:

1. severity rank (blocker, major, minor, speculation);
2. number of distinct claims attacked, descending — a finding that defeats
   three claims outranks one that dents one;
3. number of verified evidence references, descending;
4. finding digest, ascending, for determinism.

Minority rule: a finding is *minority* when it is the only admissible finding
attacking a given claim, or when its role is the only role reporting at its
severity against that claim. Minority findings are listed separately and are
never dropped from the ordered case.
"""

from __future__ import annotations

from typing import Sequence

from .matrix import Claim, build_matrix, orphan_claim_ids, unsupported_rows
from .records import EditorSynthesis, Finding, ReviewerReport
from .severity import BLOCKER, MAJOR, SPECULATION, severity_rank


def _sort_key(finding: Finding) -> tuple[int, int, int, str]:
    return (
        severity_rank(finding.severity),
        -len(set(finding.claim_ids)),
        -len(finding.evidence),
        finding.digest,
    )


def collect_findings(reports: Sequence[ReviewerReport]) -> tuple[Finding, ...]:
    """Return every finding across reports in canonical order."""

    findings = [finding for report in reports for finding in report.findings]
    return tuple(sorted(findings, key=_sort_key))


def minority_findings(findings: Sequence[Finding]) -> tuple[str, ...]:
    """Return digests of findings that no other role corroborates."""

    admissible = [item for item in findings if item.severity != SPECULATION]
    by_claim: dict[str, list[Finding]] = {}
    for finding in admissible:
        for claim_id in finding.claim_ids or ("<unbound>",):
            by_claim.setdefault(claim_id, []).append(finding)

    minority: set[str] = set()
    for claim_id, group in by_claim.items():
        roles = {item.role_id for item in group}
        if len(group) == 1:
            minority.add(group[0].digest)
            continue
        for finding in group:
            peers = [
                other
                for other in group
                if other.digest != finding.digest and other.severity == finding.severity
            ]
            if not peers and len(roles) > 1:
                minority.add(finding.digest)
    return tuple(sorted(minority))


def sufficient_rejection_set(findings: Sequence[Finding]) -> tuple[str, ...]:
    """Return the smallest ordered set of findings sufficient to reject.

    Any single blocker is sufficient, so the set is the ordered blockers. With
    no blocker, the set is the ordered majors up to the quorum; below quorum
    the set is empty and the campaign does not construct a rejection case.
    """

    from .severity import MAJOR_QUORUM

    blockers = [item.digest for item in findings if item.severity == BLOCKER]
    if blockers:
        return tuple(blockers)
    majors = [item.digest for item in findings if item.severity == MAJOR]
    if len(majors) >= MAJOR_QUORUM:
        return tuple(majors[:MAJOR_QUORUM])
    return ()


def synthesize(
    reports: Sequence[ReviewerReport],
    claims: Sequence[Claim],
) -> EditorSynthesis:
    """Build the editor synthesis from sealed reviewer reports."""

    findings = collect_findings(reports)
    rows = build_matrix(claims, findings)
    minority = minority_findings(findings)
    sufficient = sufficient_rejection_set(findings)
    orphans = orphan_claim_ids(claims, findings)
    unsupported = unsupported_rows(rows)

    by_digest = {finding.digest: finding for finding in findings}
    lines: list[str] = []

    if sufficient:
        lines.append(
            "The strongest case for rejection rests on "
            f"{len(sufficient)} finding(s), each independently sufficient or "
            "jointly at quorum:"
        )
        for digest in sufficient:
            finding = by_digest[digest]
            lines.append(
                f"- [{finding.severity}] {finding.role_id}: {finding.title}. "
                f"If true: {finding.failure_mode} "
                f"Discharged only by: {finding.what_would_refute or 'unstated'}."
            )
    else:
        lines.append(
            "No admissible finding, and no quorum of major findings, supports "
            "rejection on this input set. This is not an endorsement: it is a "
            "statement about what the reviewers were able to ground against "
            "the exact inputs declared for this campaign."
        )

    if unsupported:
        lines.append("")
        lines.append(
            "Claims carrying no declared supporting evidence, which require no "
            "reviewer to defeat:"
        )
        lines.extend(f"- {row.claim_id}: {row.claim_text}" for row in unsupported)

    if minority:
        lines.append("")
        lines.append(
            "Minority findings, preserved and not averaged away. Each is the "
            "sole admissible attack on its claim or the sole finding at its "
            "severity:"
        )
        for digest in minority:
            finding = by_digest[digest]
            lines.append(f"- [{finding.severity}] {finding.role_id}: {finding.title}")

    dissent: list[str] = []
    for finding in findings:
        if finding.severity == SPECULATION:
            dissent.append(
                f"{finding.role_id} raised, without groundable evidence: "
                f"{finding.title}. Recorded, barred from blocking."
            )
    for claim_id in orphans:
        dissent.append(
            f"A finding attacked claim id {claim_id!r}, which no declared claim "
            "provides; the reviewer inferred a claim the authors did not state."
        )

    return EditorSynthesis(
        strongest_rejection_argument="\n".join(lines),
        ordered_finding_digests=tuple(item.digest for item in findings),
        minority_findings=minority,
        dissent_notes=tuple(dissent),
        claim_matrix=rows,
    )

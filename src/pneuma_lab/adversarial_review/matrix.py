"""The evidence-to-claim matrix.

Every claim the manuscript or design makes is declared with a stable
``claim_id``. The matrix answers two questions mechanically, with no editorial
discretion:

1. which admissible evidence supports the claim, and
2. which admissible findings attack it.

A claim with no supporting evidence is marked ``unsupported`` regardless of how
confidently it is written. That is the single most useful output of the whole
system, because an unsupported claim needs no reviewer to defeat it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .records import ClaimRow, Finding
from .severity import SPECULATION


@dataclass(frozen=True)
class Claim:
    """One declared claim under review."""

    claim_id: str
    text: str
    kind: str  # "claim_of_record" | "contribution" | "non_claim" | "quantitative"
    supporting_evidence: tuple[str, ...] = ()

    def to_canonical(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "kind": self.kind,
            "supporting_evidence": list(self.supporting_evidence),
        }


def build_matrix(
    claims: Sequence[Claim], findings: Sequence[Finding]
) -> tuple[ClaimRow, ...]:
    """Return the claim matrix, sorted by ``claim_id``.

    Speculation never counts as an attack: an ungrounded concern cannot make a
    claim look contested. It is still preserved elsewhere in the record.
    """

    attacks: dict[str, list[str]] = {}
    for finding in findings:
        if finding.severity == SPECULATION:
            continue
        for claim_id in finding.claim_ids:
            attacks.setdefault(claim_id, []).append(finding.digest)

    rows: list[ClaimRow] = []
    for claim in claims:
        rows.append(
            ClaimRow(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                supporting_evidence=tuple(sorted(claim.supporting_evidence)),
                attacking_findings=tuple(sorted(attacks.get(claim.claim_id, ()))),
                unsupported=not claim.supporting_evidence and claim.kind != "non_claim",
            )
        )
    return tuple(sorted(rows, key=lambda row: row.claim_id))


def orphan_claim_ids(
    claims: Sequence[Claim], findings: Sequence[Finding]
) -> tuple[str, ...]:
    """Return claim ids cited by findings that no declared claim provides.

    A finding that attacks a claim nobody declared is attacking something the
    reviewer inferred. That is recorded, not silently dropped.
    """

    declared = {claim.claim_id for claim in claims}
    cited: set[str] = set()
    for finding in findings:
        cited.update(finding.claim_ids)
    return tuple(sorted(cited - declared))


def unsupported_rows(rows: Sequence[ClaimRow]) -> tuple[ClaimRow, ...]:
    """Return the rows whose claims have no supporting evidence."""

    return tuple(row for row in rows if row.unsupported)


def load_claims(payload: Sequence[Mapping[str, Any]]) -> tuple[Claim, ...]:
    """Parse a declared-claims document into ``Claim`` records."""

    return tuple(
        Claim(
            claim_id=str(item["claim_id"]),
            text=str(item["text"]),
            kind=str(item.get("kind", "claim_of_record")),
            supporting_evidence=tuple(str(ref) for ref in item.get("supporting_evidence", ())),
        )
        for item in payload
    )

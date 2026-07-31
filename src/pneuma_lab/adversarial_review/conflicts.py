"""Conflict-of-interest detection between reviewer roles.

Independence is the only reason twelve reviews are worth more than one. Two
reviewers who read the same cached transcript, ran on the same model instance
with a shared context, or inherited each other's declared dependencies are one
reviewer wearing two labels — and their agreement is not corroboration.

Three conflicts are detected:

``shared_context``
    Two roles in the same ``conflict_group`` whose subprocess receipts share a
    prompt digest, meaning the same context was replayed.

``declared_dependency``
    A role that names another role in ``declared_dependencies``. A stage-one
    reviewer may never depend on another stage-one reviewer.

``cross_role_citation``
    A finding that cites another reviewer's report as its evidence, which
    launders an unverified claim into a second reviewer's authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .records import ReviewerReport
from .roles import ROLES_BY_ID, REVIEWER_ROLE_IDS


@dataclass(frozen=True)
class ConflictFinding:
    """One detected independence violation."""

    kind: str
    role_ids: tuple[str, ...]
    detail: str
    blocking: bool

    def to_canonical(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "role_ids": list(self.role_ids),
            "detail": self.detail,
            "blocking": self.blocking,
        }


def detect_conflicts(reports: Sequence[ReviewerReport]) -> tuple[ConflictFinding, ...]:
    """Return every detected conflict across ``reports``, sorted canonically."""

    conflicts: list[ConflictFinding] = []
    conflicts.extend(_shared_context(reports))
    conflicts.extend(_declared_dependencies(reports))
    conflicts.extend(_cross_role_citations(reports))
    return tuple(
        sorted(conflicts, key=lambda item: (not item.blocking, item.kind, item.role_ids))
    )


def _shared_context(reports: Sequence[ReviewerReport]) -> list[ConflictFinding]:
    by_prompt: dict[str, list[str]] = {}
    for report in reports:
        if report.receipt is None:
            continue
        by_prompt.setdefault(report.receipt.prompt_digest, []).append(report.role_id)

    conflicts: list[ConflictFinding] = []
    for prompt_digest, role_ids in sorted(by_prompt.items()):
        if len(role_ids) < 2:
            continue
        groups = {
            ROLES_BY_ID[role_id].conflict_group
            for role_id in role_ids
            if role_id in ROLES_BY_ID
        }
        conflicts.append(
            ConflictFinding(
                kind="shared_context",
                role_ids=tuple(sorted(role_ids)),
                detail=(
                    f"roles share subprocess prompt digest {prompt_digest[:16]}...; "
                    f"conflict groups {sorted(groups)}"
                ),
                blocking=len(groups) == 1,
            )
        )
    return conflicts


def _declared_dependencies(reports: Sequence[ReviewerReport]) -> list[ConflictFinding]:
    conflicts: list[ConflictFinding] = []
    for report in reports:
        if report.role_id not in REVIEWER_ROLE_IDS:
            continue
        for dependency in report.declared_dependencies:
            if dependency in REVIEWER_ROLE_IDS and dependency != report.role_id:
                conflicts.append(
                    ConflictFinding(
                        kind="declared_dependency",
                        role_ids=(report.role_id, dependency),
                        detail=(
                            f"stage-one role {report.role_id} declared a dependency on "
                            f"peer reviewer {dependency}; stage-one reviews must be "
                            "independent"
                        ),
                        blocking=True,
                    )
                )
    return conflicts


def _cross_role_citations(reports: Sequence[ReviewerReport]) -> list[ConflictFinding]:
    conflicts: list[ConflictFinding] = []
    for report in reports:
        if report.role_id not in REVIEWER_ROLE_IDS:
            continue
        for finding in report.findings:
            for ref in finding.evidence:
                for peer in REVIEWER_ROLE_IDS:
                    if peer == report.role_id:
                        continue
                    if peer in ref.locator:
                        conflicts.append(
                            ConflictFinding(
                                kind="cross_role_citation",
                                role_ids=(report.role_id, peer),
                                detail=(
                                    f"finding {finding.finding_id} cites "
                                    f"{ref.locator!r}, which is peer reviewer "
                                    f"{peer}'s output rather than a campaign input"
                                ),
                                blocking=True,
                            )
                        )
    return conflicts


def blocking_conflicts(
    conflicts: Sequence[ConflictFinding],
) -> tuple[ConflictFinding, ...]:
    """Return only the conflicts that invalidate the campaign."""

    return tuple(item for item in conflicts if item.blocking)

"""Severity taxonomy and blocking rules for adversarial-review findings.

Four severities exist and they are not a continuum of opinion strength; they
are a contract about what the finding licenses.

``blocker``
    A defect that, if real, makes the launched experiment or the submitted
    manuscript scientifically invalid, unverifiable, or misleading. A blocker
    must be discharged, refuted with evidence, or explicitly overridden with a
    signed rationale. It can never be averaged away by other reviewers.

``major``
    A defect that materially weakens a claim, a control, or the reproduction
    path, but that a competent reader could route around if it were disclosed.
    Majors do not block launch by themselves; a configured quorum of them does.

``minor``
    A correctness, clarity, or hygiene defect with no effect on validity.

``speculation``
    A concern the reviewer could not ground in cited evidence. Speculation is
    RECORDED — dissent is never deleted — but it is structurally barred from
    contributing to any blocking decision and from entering the strongest
    rejection argument.
"""

from __future__ import annotations

from typing import Final

BLOCKER: Final = "blocker"
MAJOR: Final = "major"
MINOR: Final = "minor"
SPECULATION: Final = "speculation"

SEVERITIES: Final = (BLOCKER, MAJOR, MINOR, SPECULATION)

#: Severities that must be grounded in at least one verifiable evidence
#: reference. A reviewer that cannot ground a claim must downgrade it to
#: ``speculation`` rather than assert it.
EVIDENCE_REQUIRED: Final = frozenset({BLOCKER, MAJOR, MINOR})

#: Severities that may contribute to a blocking disposition.
BLOCKING_ELIGIBLE: Final = frozenset({BLOCKER, MAJOR})

#: Number of unresolved ``major`` findings that together block, absent any
#: blocker. Chosen so that a single dimension's cluster of majors cannot be
#: dismissed as reviewer noise.
MAJOR_QUORUM: Final = 3

_RANK: Final = {BLOCKER: 0, MAJOR: 1, MINOR: 2, SPECULATION: 3}


def is_valid_severity(value: object) -> bool:
    """Return whether ``value`` is one of the four contract severities."""

    return value in SEVERITIES


def severity_rank(severity: str) -> int:
    """Return a sort rank where ``blocker`` sorts first."""

    return _RANK[severity]


def requires_evidence(severity: str) -> bool:
    """Return whether a finding at ``severity`` must cite verifiable evidence."""

    return severity in EVIDENCE_REQUIRED


def blocks(severity: str) -> bool:
    """Return whether a single unresolved finding at ``severity`` blocks alone."""

    return severity == BLOCKER

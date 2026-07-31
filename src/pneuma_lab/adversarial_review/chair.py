"""The falsification chair.

The chair's job is to make every serious finding *decidable*. A criticism that
cannot be turned into a test with a defined pass and a defined fail is either
not a finding or not yet specified, and the chair says which.

Gate assignment is by role, because the gate a finding attaches to is a
property of what it threatens, not of how alarming it sounds.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from .records import FalsificationItem, Finding
from .severity import BLOCKER, MAJOR, MINOR, SPECULATION

#: Gate each role's findings attach to by default.
ROLE_GATES: Mapping[str, str] = {
    "R01-novelty": "pre_submission",
    "R02-identification": "pre_launch",
    "R03-statistics": "pre_launch",
    "R04-blinding": "pre_execution",
    "R05-benchmarks": "pre_launch",
    "R06-infrastructure": "pre_execution",
    "R07-feasibility": "pre_execution",
    "R08-reproducibility": "pre_submission",
    "R09-manuscript": "pre_submission",
    "R10-compliance": "pre_submission",
}

#: Owner each role's findings are assigned to. Named roles, never "the team".
ROLE_OWNERS: Mapping[str, str] = {
    "R01-novelty": "manuscript-owner",
    "R02-identification": "design-owner",
    "R03-statistics": "analysis-owner",
    "R04-blinding": "controller-owner",
    "R05-benchmarks": "roster-owner",
    "R06-infrastructure": "execution-owner",
    "R07-feasibility": "operations-owner",
    "R08-reproducibility": "release-owner",
    "R09-manuscript": "manuscript-owner",
    "R10-compliance": "submission-owner",
}

DEFAULT_GATE = "pre_launch"
DEFAULT_OWNER = "design-owner"


def _disposition(finding: Finding) -> str:
    if finding.severity == BLOCKER:
        return "blocking"
    if finding.severity == MAJOR:
        return "non_blocking_tracked"
    if finding.severity == MINOR:
        return "non_blocking_tracked"
    return "non_blocking_tracked"


def _test_statement(finding: Finding) -> str:
    refutation = finding.what_would_refute.strip()
    if not refutation:
        return (
            f"UNDER-SPECIFIED: {finding.title}. The finding states no condition "
            "that would discharge it, so it cannot be converted into a test. "
            "The reviewer must supply a refutation condition or the finding "
            "remains recorded without a falsification path."
        )
    return (
        f"Test: {refutation} "
        f"PASS means the finding is discharged and the claim survives. "
        f"FAIL means the stated failure mode stands: {finding.failure_mode}"
    )


def _required_evidence(finding: Finding) -> tuple[str, ...]:
    required = [
        f"{ref.kind}:{ref.locator}"
        + (f":{ref.start_line}-{ref.end_line or ref.start_line}" if ref.start_line else "")
        for ref in finding.evidence
    ]
    required.extend(f"command:{command}" for command in finding.reproduction)
    if not required:
        required.append(
            "NONE CITED — the chair cannot state required evidence for an "
            "ungrounded finding"
        )
    return tuple(required)


def convert(
    findings: Sequence[Finding],
    *,
    results_exist: bool = False,
) -> tuple[FalsificationItem, ...]:
    """Convert findings into falsification items in canonical order.

    ``results_exist`` distinguishes the two campaign stages. Before results,
    any finding whose refutation depends on measured outcomes is deferred
    rather than declared blocking, because it cannot be tested yet.
    """

    items: list[FalsificationItem] = []
    for finding in findings:
        if finding.severity == SPECULATION:
            continue
        disposition = _disposition(finding)
        gate = ROLE_GATES.get(finding.role_id, DEFAULT_GATE)
        if not results_exist and _needs_results(finding):
            disposition = "deferred_post_results"
            gate = "pre_submission"
        items.append(
            FalsificationItem(
                finding_digest=finding.digest,
                role_id=finding.role_id,
                severity=finding.severity,
                test_statement=_test_statement(finding),
                required_evidence=_required_evidence(finding),
                owner=ROLE_OWNERS.get(finding.role_id, DEFAULT_OWNER),
                disposition=disposition,
                gate=gate,
            )
        )
    return tuple(sorted(items, key=lambda item: (item.gate, item.severity, item.finding_digest)))


_RESULT_WORDS = (
    "observed effect",
    "measured effect",
    "reported estimate",
    "post-unblind",
    "the results show",
)


def _needs_results(finding: Finding) -> bool:
    haystack = " ".join(
        (finding.statement, finding.what_would_refute, finding.failure_mode)
    ).lower()
    return any(word in haystack for word in _RESULT_WORDS)


def blocking_items(items: Sequence[FalsificationItem]) -> tuple[FalsificationItem, ...]:
    """Return only the items the chair marked blocking."""

    return tuple(item for item in items if item.disposition == "blocking")


def underspecified_items(
    items: Sequence[FalsificationItem],
) -> tuple[FalsificationItem, ...]:
    """Return items the chair could not convert into a decidable test."""

    return tuple(item for item in items if item.test_statement.startswith("UNDER-SPECIFIED"))

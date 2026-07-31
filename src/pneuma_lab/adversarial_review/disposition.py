"""Hash-bound launch-readiness disposition and the human-override contract.

What this module can say
------------------------

``launch_blocked``
    At least one blocking falsification item is undischarged and unoverridden,
    or a blocking independence conflict exists.

``launch_blocked_by_conflict``
    The campaign itself is invalid — reviewers were not independent — so no
    statement about the science is made at all.

``no_blocking_findings``
    Every blocking item is discharged or carries a signed override, and no
    quorum of majors stands.

What this module can never say
------------------------------

Anything that authorizes an experiment, a spend, a scientific claim, or a
submission. ``no_blocking_findings`` is the absence of a recorded objection
from twelve hostile readers against one declared input set. It is not
permission, and the emitted notice says so in the artifact itself.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from .canonical import digest_value
from .conflicts import ConflictFinding, blocking_conflicts
from .errors import OverrideContractError
from .records import (
    EditorSynthesis,
    FalsificationItem,
    Override,
    ReadinessDisposition,
    ReviewerReport,
)
from .severity import MAJOR, MAJOR_QUORUM

LAUNCH_BLOCKED = "launch_blocked"
LAUNCH_BLOCKED_BY_CONFLICT = "launch_blocked_by_conflict"
NO_BLOCKING_FINDINGS = "no_blocking_findings"

NON_AUTHORIZATION_NOTICE = (
    "This disposition records the outcome of an adversarial review against one "
    "declared, digest-bound input set. It authorizes nothing. It does not "
    "authorize an experiment, a provider action, a spend, a scientific claim, "
    "or a submission. A verdict of no_blocking_findings means twelve hostile "
    "reviewers could not ground a blocking objection against these exact "
    "inputs; it is not evidence that the study is correct."
)


def validate_overrides(
    overrides: Sequence[Override],
    items: Sequence[FalsificationItem],
) -> None:
    """Reject overrides that target nothing or attempt to erase a finding."""

    known = {item.finding_digest for item in items}
    seen: set[str] = set()
    for override in overrides:
        if override.finding_digest not in known:
            raise OverrideContractError(
                f"override targets unknown finding {override.finding_digest[:16]}...; "
                "an override may only attach to a recorded finding"
            )
        if override.finding_digest in seen:
            raise OverrideContractError(
                f"duplicate override for finding {override.finding_digest[:16]}..."
            )
        seen.add(override.finding_digest)


def decide(
    *,
    campaign_id: str,
    stage: str,
    inputs_digest: str,
    reports: Sequence[ReviewerReport],
    synthesis: EditorSynthesis,
    items: Sequence[FalsificationItem],
    conflicts: Sequence[ConflictFinding] = (),
    overrides: Sequence[Override] = (),
    discharged: Mapping[str, str] | None = None,
) -> ReadinessDisposition:
    """Compute the sealed readiness disposition.

    ``discharged`` maps a finding digest to the receipt id that discharged it.
    A discharge without a receipt id is not a discharge.
    """

    validate_overrides(overrides, items)
    discharged = dict(discharged or {})

    overridden = tuple(sorted(item.finding_digest for item in overrides))
    blocking = []
    for item in items:
        if item.disposition != "blocking":
            continue
        if discharged.get(item.finding_digest):
            continue
        if item.finding_digest in overridden:
            continue
        blocking.append(item.finding_digest)

    standing_majors = [
        item
        for item in items
        if item.severity == MAJOR
        and item.finding_digest not in overridden
        and not discharged.get(item.finding_digest)
    ]

    hard_conflicts = blocking_conflicts(conflicts)
    if hard_conflicts:
        verdict = LAUNCH_BLOCKED_BY_CONFLICT
    elif blocking or len(standing_majors) >= MAJOR_QUORUM:
        verdict = LAUNCH_BLOCKED
    else:
        verdict = NO_BLOCKING_FINDINGS

    if not blocking and len(standing_majors) >= MAJOR_QUORUM:
        blocking = [item.finding_digest for item in standing_majors[:MAJOR_QUORUM]]

    disposition = ReadinessDisposition(
        campaign_id=campaign_id,
        stage=stage,
        verdict=verdict,
        inputs_digest=inputs_digest,
        reports_digest=digest_value([report.to_canonical() for report in reports]),
        synthesis_digest=digest_value(synthesis.to_canonical()),
        falsification_digest=digest_value([item.to_canonical() for item in items]),
        blocking_finding_digests=tuple(sorted(blocking)),
        overridden_finding_digests=overridden,
        non_authorization_notice=NON_AUTHORIZATION_NOTICE,
    )
    return disposition.sealed()


def verify_seal(disposition: ReadinessDisposition) -> bool:
    """Return whether the disposition digest still binds its own content."""

    return disposition.disposition_digest == digest_value(disposition.to_canonical())

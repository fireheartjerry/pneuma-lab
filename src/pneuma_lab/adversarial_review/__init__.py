"""PLACEBO adversarial-review system.

A reusable, fail-closed review harness whose sole objective is to construct the
strongest evidence-based case for REJECTING the PLACEBO Trial and its
manuscript. Twelve independent roles attack the work across novelty, causal
identification, statistics, blinding, benchmarks, infrastructure, feasibility,
reproducibility, manuscript rhetoric, and venue compliance; an editor
synthesises the strongest rejection without averaging away minority findings;
and a falsification chair converts every serious finding into an ownable test
with a blocking disposition.

The system authorizes nothing. See ``disposition.NON_AUTHORIZATION_NOTICE``.

Operating procedure, input contracts, blocking rules, and the human-override
policy are documented in ``docs/research/placebo-review/00-operating-procedure.md``.
"""

from __future__ import annotations

from .campaign import CampaignResult, run_campaign, write_campaign
from .disposition import (
    LAUNCH_BLOCKED,
    LAUNCH_BLOCKED_BY_CONFLICT,
    NO_BLOCKING_FINDINGS,
    NON_AUTHORIZATION_NOTICE,
)
from .inputs import CampaignInputs, EnvironmentPin, InputObject
from .matrix import Claim
from .records import EvidenceRef, Finding, Override, ReviewerReport
from .report import render
from .roles import ROLES, ROLES_BY_ID, REVIEWER_ROLE_IDS, SYNTHESIS_ROLE_IDS
from .severity import BLOCKER, MAJOR, MINOR, SPECULATION

__all__ = [
    "BLOCKER",
    "CampaignInputs",
    "CampaignResult",
    "Claim",
    "EnvironmentPin",
    "EvidenceRef",
    "Finding",
    "InputObject",
    "LAUNCH_BLOCKED",
    "LAUNCH_BLOCKED_BY_CONFLICT",
    "MAJOR",
    "MINOR",
    "NON_AUTHORIZATION_NOTICE",
    "NO_BLOCKING_FINDINGS",
    "Override",
    "REVIEWER_ROLE_IDS",
    "ROLES",
    "ROLES_BY_ID",
    "ReviewerReport",
    "SPECULATION",
    "SYNTHESIS_ROLE_IDS",
    "render",
    "run_campaign",
    "write_campaign",
]

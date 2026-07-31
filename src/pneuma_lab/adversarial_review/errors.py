"""Fail-closed error taxonomy for the PLACEBO adversarial-review system.

Every error in this module means the review campaign STOPS. The system never
degrades to a partial verdict: a missing, stale, or unverifiable input is a
refusal to review, not a review with caveats.
"""

from __future__ import annotations


class AdversarialReviewError(Exception):
    """Base class for every adversarial-review failure."""


class InputContractError(AdversarialReviewError):
    """A required campaign input is missing, malformed, or unreadable."""


class StaleInputError(AdversarialReviewError):
    """A declared input digest does not match the bytes on disk."""


class EvidenceGroundingError(AdversarialReviewError):
    """A finding cites evidence that cannot be resolved or verified."""


class InventedEvidenceError(EvidenceGroundingError):
    """A finding cites a file, line, receipt, or source that does not exist."""


class ConflictOfInterestError(AdversarialReviewError):
    """Two reviewer roles share a disqualifying dependency."""


class OverrideContractError(AdversarialReviewError):
    """A human override is unsigned, unattributed, or attempts to erase a finding."""


class DispositionError(AdversarialReviewError):
    """A readiness disposition could not be produced or is internally inconsistent."""


class SubprocessBudgetError(AdversarialReviewError):
    """A reviewer subprocess exceeded its bounded cost or wall-clock allowance."""

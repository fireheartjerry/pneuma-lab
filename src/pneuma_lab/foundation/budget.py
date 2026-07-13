"""Persistent policy objects for the optional one-job cloud allowance."""

from __future__ import annotations

from dataclasses import dataclass


MAX_LIFETIME_CLOUD_USD = 45.0


class BudgetViolation(ValueError):
    """Raised when paid compute would exceed the approved project budget."""


@dataclass(frozen=True)
class BudgetState:
    completed_cloud_jobs: int = 0
    paid_compute_usd: float = 0.0


@dataclass(frozen=True)
class CloudQuote:
    compute_usd: float
    storage_usd: float
    taxes_usd: float

    @property
    def total_usd(self) -> float:
        return self.compute_usd + self.storage_usd + self.taxes_usd


@dataclass(frozen=True)
class CloudAuthorization:
    total_usd: float
    purpose: str


def authorize_optional_cloud_job(
    state: BudgetState,
    quote: CloudQuote,
    *,
    purpose: str = "reproducibility_only",
    local_gates_passed: bool,
) -> CloudAuthorization:
    if purpose != "reproducibility_only":
        raise BudgetViolation("cloud use is restricted to one reproducibility job")
    if not local_gates_passed:
        raise BudgetViolation("all local gates must pass before cloud verification")
    if state.completed_cloud_jobs != 0:
        raise BudgetViolation("only one lifetime cloud job is permitted")
    if min(quote.compute_usd, quote.storage_usd, quote.taxes_usd) < 0:
        raise BudgetViolation("cloud quote components cannot be negative")
    if state.paid_compute_usd + quote.total_usd > MAX_LIFETIME_CLOUD_USD:
        raise BudgetViolation("cloud quote exceeds the $45 lifetime limit")
    return CloudAuthorization(total_usd=quote.total_usd, purpose=purpose)


def record_cloud_job(
    state: BudgetState,
    authorization: CloudAuthorization,
    *,
    actual_total_usd: float,
) -> BudgetState:
    if state.completed_cloud_jobs != 0:
        raise BudgetViolation("only one lifetime cloud job is permitted")
    if actual_total_usd < 0 or actual_total_usd > authorization.total_usd:
        raise BudgetViolation("actual cloud cost must be non-negative and within quote")
    if state.paid_compute_usd + actual_total_usd > MAX_LIFETIME_CLOUD_USD:
        raise BudgetViolation("completed cloud cost exceeds the $45 lifetime limit")
    return BudgetState(
        completed_cloud_jobs=1,
        paid_compute_usd=state.paid_compute_usd + actual_total_usd,
    )

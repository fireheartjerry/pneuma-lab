"""Persistent policy objects for the optional one-job cloud allowance.

Two complementary gates live here:

- ``authorize_optional_cloud_job`` guards the lifetime ledger with an
  itemized quote (compute, storage, taxes) once local gates have passed.
- ``authorize_reproduction_quote`` validates one human-provided, current
  RunPod-style quote for the optional reproduction run. It is quote-only:
  it never contacts a provider, never creates a Pod, and never opens a
  network connection. It either raises :class:`BudgetViolation` or returns
  an authorization for exactly one cloud job.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


MAX_LIFETIME_CLOUD_USD = 45.0
MAX_PREPAID_CREDIT_USD = 38.0
MAX_TERMINATION_HOURS = 72
MIN_8M_TOKENS_PER_SECOND = 30.9
REPRODUCTION_STAGE_TOKENS = {"2m": 2_000_000, "8m": 8_000_000}
_FIT_TOLERANCE = 1e-9


class BudgetViolation(ValueError):
    """Raised when paid compute would exceed the approved project budget."""


@dataclass(frozen=True)
class BudgetState:
    completed_cloud_jobs: int = 0
    paid_compute_usd: float = 0.0


@dataclass(frozen=True)
class ItemizedCloudQuote:
    compute_usd: float
    storage_usd: float
    taxes_usd: float

    @property
    def total_usd(self) -> float:
        return self.compute_usd + self.storage_usd + self.taxes_usd


@dataclass(frozen=True)
class CloudQuote:
    """One human-provided, current tax-inclusive reproduction quote."""

    hourly_usd: float
    tax_inclusive_usd: float
    prepaid_credit_usd: float
    auto_pay_enabled: bool
    termination_hours: float
    measured_tokens_per_second: float
    prior_lifetime_spend_usd: float


@dataclass(frozen=True)
class CloudAuthorization:
    total_usd: float
    purpose: str


@dataclass(frozen=True)
class ReproductionQuoteAuthorization:
    """A validated quote for exactly one bounded cloud reproduction job."""

    allowed: bool
    stage: str
    quoted_hourly_usd: float
    quoted_tax_inclusive_usd: float
    lifetime_total_usd: float
    estimated_hours: float
    estimated_compute_usd: float
    cloud_job_ceiling: int


def _require_real_number(value, *, label: str, minimum_exclusive: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BudgetViolation(f"{label} must be a real number")
    number = float(value)
    if not math.isfinite(number):
        raise BudgetViolation(f"{label} must be finite")
    if minimum_exclusive and number <= 0:
        raise BudgetViolation(f"{label} must be positive")
    if not minimum_exclusive and number < 0:
        raise BudgetViolation(f"{label} cannot be negative")
    return number


def authorize_reproduction_quote(
    *,
    stage: str = "2m",
    quoted_hourly_usd: float,
    quoted_tax_inclusive_usd: float,
    prepaid_credit_usd: float,
    auto_pay_enabled: bool,
    termination_hours: float,
    measured_tokens_per_second: float,
    prior_lifetime_spend_usd: float,
) -> ReproductionQuoteAuthorization:
    """Validate one human-provided current quote for one lifetime cloud job.

    Enforces the $45 lifetime tax-inclusive cap including prior spend, at
    most $38 prepaid credit, disabled auto-pay, a 72-hour hard termination,
    the 2M-token default stage, and for the 8M stage at least 30.9 measured
    tokens/second plus an all-in fit inside the quoted total and the
    termination window. It performs no network access of any kind.
    """

    if stage not in REPRODUCTION_STAGE_TOKENS:
        raise BudgetViolation(
            "cloud reproduction supports only the 2m default or the 8m stage"
        )
    hourly = _require_real_number(
        quoted_hourly_usd, label="quoted hourly rate", minimum_exclusive=True
    )
    tax_inclusive = _require_real_number(
        quoted_tax_inclusive_usd,
        label="quoted tax-inclusive total",
        minimum_exclusive=True,
    )
    prepaid = _require_real_number(
        prepaid_credit_usd, label="prepaid credit", minimum_exclusive=False
    )
    window_hours = _require_real_number(
        termination_hours, label="termination hours", minimum_exclusive=True
    )
    tokens_per_second = _require_real_number(
        measured_tokens_per_second,
        label="measured tokens per second",
        minimum_exclusive=True,
    )
    prior_spend = _require_real_number(
        prior_lifetime_spend_usd,
        label="prior lifetime spend",
        minimum_exclusive=False,
    )
    if auto_pay_enabled is not False:
        raise BudgetViolation("cloud reproduction requires auto-pay to stay disabled")
    if window_hours > MAX_TERMINATION_HOURS:
        raise BudgetViolation(
            f"the cloud pod must hard-terminate within {MAX_TERMINATION_HOURS} hours"
        )
    if prepaid > MAX_PREPAID_CREDIT_USD:
        raise BudgetViolation(
            f"prepaid credit may not exceed ${MAX_PREPAID_CREDIT_USD:g}"
        )
    lifetime_total = prior_spend + tax_inclusive
    if lifetime_total > MAX_LIFETIME_CLOUD_USD:
        raise BudgetViolation(
            "the quote plus prior spend exceeds the "
            f"${MAX_LIFETIME_CLOUD_USD:g} lifetime tax-inclusive cap"
        )
    if stage == "8m" and tokens_per_second < MIN_8M_TOKENS_PER_SECOND:
        raise BudgetViolation(
            f"the 8m stage requires at least {MIN_8M_TOKENS_PER_SECOND} "
            "measured tokens/second"
        )
    tokens = REPRODUCTION_STAGE_TOKENS[stage]
    estimated_hours = tokens / (tokens_per_second * 3600.0)
    if estimated_hours > window_hours * (1.0 + _FIT_TOLERANCE):
        raise BudgetViolation(
            f"the estimated {estimated_hours:.2f}-hour run does not fit the "
            f"{window_hours:g}-hour termination window"
        )
    estimated_compute = estimated_hours * hourly
    if estimated_compute > tax_inclusive * (1.0 + _FIT_TOLERANCE):
        raise BudgetViolation(
            "the quoted tax-inclusive total does not cover the estimated "
            f"all-in run cost of ${estimated_compute:.2f}"
        )
    return ReproductionQuoteAuthorization(
        allowed=True,
        stage=stage,
        quoted_hourly_usd=hourly,
        quoted_tax_inclusive_usd=tax_inclusive,
        lifetime_total_usd=lifetime_total,
        estimated_hours=estimated_hours,
        estimated_compute_usd=estimated_compute,
        cloud_job_ceiling=1,
    )


def authorize_optional_cloud_job(
    state: BudgetState,
    quote: ItemizedCloudQuote,
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

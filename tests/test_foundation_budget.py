"""Paid compute remains optional, singular, and bounded for project lifetime."""

from __future__ import annotations

import pytest

from pneuma_lab.foundation.budget import (
    BudgetState,
    BudgetViolation,
    CloudQuote,
    authorize_optional_cloud_job,
    record_cloud_job,
)


def test_zero_cost_local_mode_is_the_default() -> None:
    state = BudgetState()
    assert state.paid_compute_usd == 0.0
    assert state.completed_cloud_jobs == 0


def test_one_reproducibility_quote_may_fit_below_45_total() -> None:
    state = BudgetState()
    quote = CloudQuote(compute_usd=38.0, storage_usd=2.0, taxes_usd=4.0)
    authorization = authorize_optional_cloud_job(
        state,
        quote,
        local_gates_passed=True,
    )
    assert authorization.total_usd == pytest.approx(44.0)
    assert authorization.purpose == "reproducibility_only"
    completed = record_cloud_job(state, authorization, actual_total_usd=43.50)
    assert completed.completed_cloud_jobs == 1
    assert completed.paid_compute_usd == pytest.approx(43.50)


def test_cloud_quote_rejects_over_budget_or_second_job() -> None:
    with pytest.raises(BudgetViolation, match="45"):
        authorize_optional_cloud_job(
            BudgetState(),
            CloudQuote(compute_usd=45.0, storage_usd=1.0, taxes_usd=0.0),
            local_gates_passed=True,
        )
    with pytest.raises(BudgetViolation, match="one lifetime"):
        authorize_optional_cloud_job(
            BudgetState(completed_cloud_jobs=1, paid_compute_usd=20.0),
            CloudQuote(compute_usd=10.0, storage_usd=0.0, taxes_usd=1.0),
            local_gates_passed=True,
        )


def test_cloud_job_cannot_be_exploratory_or_recurring() -> None:
    with pytest.raises(BudgetViolation, match="reproducibility"):
        authorize_optional_cloud_job(
            BudgetState(),
            CloudQuote(compute_usd=10.0, storage_usd=1.0, taxes_usd=1.0),
            purpose="hyperparameter_sweep",
            local_gates_passed=True,
        )


def test_cloud_reproducibility_job_waits_for_all_local_gates() -> None:
    with pytest.raises(BudgetViolation, match="local gates"):
        authorize_optional_cloud_job(
            BudgetState(),
            CloudQuote(compute_usd=10.0, storage_usd=1.0, taxes_usd=1.0),
            local_gates_passed=False,
        )

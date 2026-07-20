"""Paid compute remains optional, singular, and bounded for project lifetime."""

from __future__ import annotations

import pytest

from pneuma_lab.foundation.budget import (
    BudgetState,
    BudgetViolation,
    ItemizedCloudQuote,
    authorize_optional_cloud_job,
    authorize_reproduction_quote,
    record_cloud_job,
)


def _quote_arguments(**overrides) -> dict:
    arguments = {
        "stage": "2m",
        "quoted_hourly_usd": 0.44,
        "quoted_tax_inclusive_usd": 38.0,
        "prepaid_credit_usd": 38.0,
        "auto_pay_enabled": False,
        "termination_hours": 72,
        "measured_tokens_per_second": 20.0,
        "prior_lifetime_spend_usd": 0.0,
    }
    arguments.update(overrides)
    return arguments


def test_zero_cost_local_mode_is_the_default() -> None:
    state = BudgetState()
    assert state.paid_compute_usd == 0.0
    assert state.completed_cloud_jobs == 0


def test_one_reproducibility_quote_may_fit_below_45_total() -> None:
    state = BudgetState()
    quote = ItemizedCloudQuote(compute_usd=38.0, storage_usd=2.0, taxes_usd=4.0)
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
            ItemizedCloudQuote(compute_usd=45.0, storage_usd=1.0, taxes_usd=0.0),
            local_gates_passed=True,
        )
    with pytest.raises(BudgetViolation, match="one lifetime"):
        authorize_optional_cloud_job(
            BudgetState(completed_cloud_jobs=1, paid_compute_usd=20.0),
            ItemizedCloudQuote(compute_usd=10.0, storage_usd=0.0, taxes_usd=1.0),
            local_gates_passed=True,
        )


def test_cloud_job_cannot_be_exploratory_or_recurring() -> None:
    with pytest.raises(BudgetViolation, match="reproducibility"):
        authorize_optional_cloud_job(
            BudgetState(),
            ItemizedCloudQuote(compute_usd=10.0, storage_usd=1.0, taxes_usd=1.0),
            purpose="hyperparameter_sweep",
            local_gates_passed=True,
        )


def test_cloud_reproducibility_job_waits_for_all_local_gates() -> None:
    with pytest.raises(BudgetViolation, match="local gates"):
        authorize_optional_cloud_job(
            BudgetState(),
            ItemizedCloudQuote(compute_usd=10.0, storage_usd=1.0, taxes_usd=1.0),
            local_gates_passed=False,
        )


def test_quote_gate_enforces_lifetime_tax_and_72_hour_caps() -> None:
    authorization = authorize_reproduction_quote(
        stage="2m",
        quoted_hourly_usd=0.44,
        quoted_tax_inclusive_usd=38.0,
        prepaid_credit_usd=38.0,
        auto_pay_enabled=False,
        termination_hours=72,
        measured_tokens_per_second=20.0,
        prior_lifetime_spend_usd=0.0,
    )
    assert authorization.allowed is True
    with pytest.raises(BudgetViolation, match="45"):
        authorize_reproduction_quote(
            stage="2m",
            quoted_hourly_usd=0.44,
            quoted_tax_inclusive_usd=45.01,
            prepaid_credit_usd=38.0,
            auto_pay_enabled=False,
            termination_hours=72,
            measured_tokens_per_second=20.0,
            prior_lifetime_spend_usd=0.0,
        )


def test_quote_gate_authorizes_exactly_one_cloud_job() -> None:
    authorization = authorize_reproduction_quote(**_quote_arguments())
    assert authorization.cloud_job_ceiling == 1
    assert authorization.stage == "2m"
    assert authorization.estimated_hours == pytest.approx(27.7778, rel=1e-3)


def test_quote_gate_counts_prior_lifetime_spend_against_the_45_cap() -> None:
    with pytest.raises(BudgetViolation, match="45"):
        authorize_reproduction_quote(
            **_quote_arguments(
                quoted_tax_inclusive_usd=36.0,
                prior_lifetime_spend_usd=10.0,
            )
        )


def test_quote_gate_rejects_prepaid_credit_above_38() -> None:
    with pytest.raises(BudgetViolation, match="38"):
        authorize_reproduction_quote(**_quote_arguments(prepaid_credit_usd=38.01))


def test_quote_gate_rejects_enabled_auto_pay() -> None:
    with pytest.raises(BudgetViolation, match="auto-pay"):
        authorize_reproduction_quote(**_quote_arguments(auto_pay_enabled=True))


def test_quote_gate_rejects_termination_beyond_72_hours() -> None:
    with pytest.raises(BudgetViolation, match="72"):
        authorize_reproduction_quote(**_quote_arguments(termination_hours=73))


def test_quote_gate_rejects_runs_that_cannot_finish_inside_the_window() -> None:
    with pytest.raises(BudgetViolation, match="72"):
        authorize_reproduction_quote(**_quote_arguments(measured_tokens_per_second=5.0))


def test_quote_gate_requires_the_quote_to_cover_the_all_in_estimate() -> None:
    with pytest.raises(BudgetViolation, match="all-in"):
        authorize_reproduction_quote(
            **_quote_arguments(quoted_hourly_usd=2.0, quoted_tax_inclusive_usd=38.0)
        )


def test_quote_gate_supports_only_the_2m_default_and_8m_stages() -> None:
    with pytest.raises(BudgetViolation, match="2m"):
        authorize_reproduction_quote(**_quote_arguments(stage="100k"))


def test_quote_gate_requires_30_9_tokens_per_second_for_8m() -> None:
    with pytest.raises(BudgetViolation, match="30.9"):
        authorize_reproduction_quote(
            **_quote_arguments(stage="8m", measured_tokens_per_second=30.0)
        )
    authorization = authorize_reproduction_quote(
        **_quote_arguments(stage="8m", measured_tokens_per_second=30.9)
    )
    assert authorization.allowed is True
    assert authorization.estimated_hours <= 72.0 + 1e-6


def test_quote_gate_rejects_nonpositive_or_nonfinite_amounts() -> None:
    with pytest.raises(BudgetViolation, match="positive"):
        authorize_reproduction_quote(**_quote_arguments(quoted_hourly_usd=0.0))
    with pytest.raises(BudgetViolation, match="positive"):
        authorize_reproduction_quote(**_quote_arguments(measured_tokens_per_second=0.0))
    with pytest.raises(BudgetViolation, match="finite"):
        authorize_reproduction_quote(
            **_quote_arguments(quoted_tax_inclusive_usd=float("inf"))
        )
    with pytest.raises(BudgetViolation, match="negative"):
        authorize_reproduction_quote(**_quote_arguments(prior_lifetime_spend_usd=-1.0))

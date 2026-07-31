"""Fail-closed local cost reservations; no price lookup or billing action."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import CloudManifestError


@dataclass(frozen=True, slots=True)
class SpendState:
    provider: str
    provider_balance: float
    provider_settled: float
    provider_reserved: float
    project_settled: float
    project_reserved: float
    tier_stop: float


def reserve(state: SpendState, proposed: float) -> SpendState:
    if proposed <= 0:
        raise CloudManifestError("proposed reservation must be positive")
    if state.provider_settled + state.provider_reserved + proposed > state.provider_balance:
        raise CloudManifestError("provider balance invariant fails")
    if state.project_settled + state.project_reserved + proposed > state.tier_stop:
        raise CloudManifestError("project tier-stop invariant fails")
    return SpendState(state.provider, state.provider_balance, state.provider_settled, state.provider_reserved + proposed, state.project_settled, state.project_reserved + proposed, state.tier_stop)


def settle(state: SpendState, amount: float) -> SpendState:
    if amount <= 0 or amount > state.provider_reserved:
        raise CloudManifestError("unreserved settlement is forbidden")
    return SpendState(state.provider, state.provider_balance, state.provider_settled + amount, state.provider_reserved - amount, state.project_settled + amount, state.project_reserved - amount, state.tier_stop)

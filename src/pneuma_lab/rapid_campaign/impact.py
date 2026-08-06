"""Minimal transitive invalidation for rapid experiment amendments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class ImpactError(ValueError):
    """A proposed change cannot be classified safely."""


_DOMAINS = {
    "C0": frozenset({"paper", "plot", "table", "prose"}),
    "C1": frozenset({"dashboard", "observer", "campaign_policy"}),
    "C2": frozenset({"batch_wiring", "resource_topology", "teardown_adapter"}),
    "C3": frozenset({"model", "benchmark", "task_data", "packet", "assignment", "runtime_image", "runtime_code"}),
    "C4": frozenset({"eligible_roster", "sample_size", "estimand", "effect_target", "allocation", "stopping_rule", "power_rng"}),
}
_REGENERATE = {
    "C0": ("analysis", "paper"),
    "C1": ("campaign_control",),
    "C2": ("provider_binding", "package", "authorization"),
    "C3": ("input_seals", "images", "sboms", "run_spec", "package", "authorization"),
    "C4": ("power", "input_seals", "images", "sboms", "run_spec", "package", "authorization"),
}


@dataclass(frozen=True, slots=True)
class ImpactDecision:
    level: str
    changed_domains: tuple[str, ...]
    regenerate: tuple[str, ...]
    rerun_power: bool
    policy_version: str = "c0-c4-v1"


def classify_change(domains: Iterable[str]) -> ImpactDecision:
    values = frozenset(domains)
    if not values:
        raise ImpactError("at least one changed domain is required")
    known = frozenset().union(*_DOMAINS.values())
    unknown = values - known
    if unknown:
        raise ImpactError(f"unknown change domains: {sorted(unknown)}")
    level = max((name for name, members in _DOMAINS.items() if values & members), key=lambda name: int(name[1:]))
    return ImpactDecision(
        level=level,
        changed_domains=tuple(sorted(values)),
        regenerate=_REGENERATE[level],
        rerun_power=level == "C4",
    )

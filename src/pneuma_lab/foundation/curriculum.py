"""Deterministic local learning-rate and token-curriculum decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


APPROVED_LEARNING_RATES = (5e-5, 1e-4, 2e-4)
TOKEN_STAGES = (100_000, 500_000, 2_000_000, 8_000_000, 16_000_000, 32_000_000)


@dataclass(frozen=True)
class LrTrial:
    learning_rate: float
    validation_loss: float
    stable: bool


def select_learning_rate(trials: Iterable[LrTrial]) -> float:
    """Select the best stable approved smoke trial; ties choose lower LR."""

    values = tuple(trials)
    rates = {trial.learning_rate for trial in values}
    if not rates or not rates.issubset(set(APPROVED_LEARNING_RATES)):
        raise ValueError(
            f"trials must use only approved learning rates {APPROVED_LEARNING_RATES!r}"
        )
    stable = tuple(trial for trial in values if trial.stable)
    if not stable:
        raise ValueError("no stable learning-rate trial is available")
    return min(
        stable, key=lambda item: (item.validation_loss, item.learning_rate)
    ).learning_rate


def next_token_stage(
    current_tokens: int,
    *,
    stable: bool,
    regression_passed: bool,
    falsification_gate_passed: bool = False,
    validation_gain_points: float | None = None,
) -> int | None:
    """Advance one approved stage or stop on any fail-closed condition."""

    if current_tokens not in TOKEN_STAGES:
        raise ValueError(f"unknown token stage: {current_tokens}")
    if not stable or not regression_passed:
        return None
    if current_tokens == 100_000:
        return 500_000
    if current_tokens == 500_000:
        return 2_000_000
    if current_tokens == 2_000_000:
        return 8_000_000 if falsification_gate_passed else None
    if current_tokens in {8_000_000, 16_000_000}:
        if validation_gain_points is None or validation_gain_points < 0.5:
            return None
        return 16_000_000 if current_tokens == 8_000_000 else 32_000_000
    return None

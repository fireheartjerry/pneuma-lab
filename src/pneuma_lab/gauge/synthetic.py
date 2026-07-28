"""Synthetic gauges with known ground truth, for validating the estimator itself.

A measurement-system-analysis tool that has not been checked against a gauge whose
variance components are known by construction is itself an unvalidated instrument.
`python -m pneuma_lab.gauge selftest` runs these offline and reports recovery error,
so anyone can confirm the estimator before trusting a card it produced.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .cube import Response, ResponseCube


@dataclass(frozen=True)
class SyntheticSpec:
    """Ground-truth variance components of a simulated gauge."""

    sd_item: float
    sd_condition: float
    sd_interaction: float
    sd_error: float
    n_items: int = 48
    n_conditions: int = 8
    n_reps: int = 8
    quantum: float = 0.0
    clip: bool = False
    sham_shift: float = 0.0
    name: str = "synthetic"


def syntheticCube(spec: SyntheticSpec, *, seed: int = 20260728) -> ResponseCube:
    """Build a `ResponseCube` whose variance components are known by construction.

    `quantum > 0` rounds emitted values onto a grid, reproducing the coarse response
    scales real models use. `sham_shift` adds a constant offset to a second `sham`
    arm, so the placebo machinery can be tested against a known-inert manipulation.
    """
    rng = random.Random(seed)
    alpha = [rng.gauss(0.0, spec.sd_item) for _ in range(spec.n_items)]
    beta = [rng.gauss(0.0, spec.sd_condition) for _ in range(spec.n_conditions)]
    inter = [
        [rng.gauss(0.0, spec.sd_interaction) for _ in range(spec.n_conditions)]
        for _ in range(spec.n_items)
    ]
    arms = ("base", "sham") if spec.sham_shift else ("base",)

    rows: list[Response] = []
    for i in range(spec.n_items):
        for o in range(spec.n_conditions):
            for arm in arms:
                shift = spec.sham_shift if arm == "sham" else 0.0
                for r in range(spec.n_reps):
                    value = (
                        0.5
                        + alpha[i]
                        + beta[o]
                        + inter[i][o]
                        + rng.gauss(0.0, spec.sd_error)
                        + shift
                    )
                    if spec.quantum > 0.0:
                        value = round(value / spec.quantum) * spec.quantum
                    if spec.clip:
                        value = min(1.0, max(0.0, value))
                    rows.append(
                        Response(
                            item_id=f"i{i:03d}",
                            model=spec.name,
                            wording_id=f"w{o}",
                            scale_id="p2",
                            provenance="synthetic",
                            arm=arm,
                            temperature=0.7,
                            replicate=r,
                            raw_text=f"{value:.6f}",
                            value=value,
                            parse_ok=True,
                        )
                    )
    return ResponseCube(rows)


#: The self-test battery: gauges whose correct verdict is known in advance.
SELFTEST_SPECS: tuple[tuple[SyntheticSpec, str], ...] = (
    (
        SyntheticSpec(
            sd_item=0.30,
            sd_condition=0.02,
            sd_interaction=0.01,
            sd_error=0.02,
            name="good_gauge",
        ),
        "USABLE",
    ),
    (
        SyntheticSpec(
            sd_item=0.00,
            sd_condition=0.05,
            sd_interaction=0.03,
            sd_error=0.20,
            name="pure_noise",
        ),
        "UNINTERPRETABLE",
    ),
    (
        SyntheticSpec(
            sd_item=0.02,
            sd_condition=0.04,
            sd_interaction=0.02,
            sd_error=0.10,
            quantum=0.05,
            name="coarse_low_signal",
        ),
        "UNINTERPRETABLE",
    ),
    (
        SyntheticSpec(
            sd_item=0.0,
            sd_condition=0.0,
            sd_interaction=0.0,
            sd_error=0.0,
            quantum=1.0,
            name="constant_channel",
        ),
        "DEGENERATE",
    ),
)


__all__ = ["SELFTEST_SPECS", "SyntheticSpec", "syntheticCube"]

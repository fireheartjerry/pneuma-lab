"""Measurement-system analysis (MSA) for *elicited* LLM metrics.

An elicited metric is any number produced by prompting a model: self-reported
confidence, an LLM-as-judge score, an elicited eval rating. This package answers
the question that industrial metrology, analytical chemistry, and clinimetrics
require to be answered *before* such a number is allowed into an inference:

    can this gauge tell two different items apart at all?

That is a variance-decomposition question, not a correlation-with-truth question,
and it is prior to calibration. See `docs/gauge-card-standard.md` for the
reporting standard and `docs/research/experiments/g1-gauge-preregistration.md`
for the study that motivated it.

Everything here is stdlib-only and deterministic: same cube in, byte-identical
card out.
"""

from __future__ import annotations

from .anova import VarianceComponents, varianceComponents
from .cube import Response, ResponseCube
from .resolution import (
    GaugeResolution,
    discriminationIndex,
    effectiveSupport,
    gaugeResolution,
    gaugeVerdict,
    resolvingPower,
)
from .stats import Interval, bootstrapCi, normalCdf, normalQuantile, shannonEntropy
from .theory import (
    Ceilings,
    aggregationCurve,
    aurocCeiling,
    ceilings,
    minimumDetectableEffect,
    requiredK,
    validityCeiling,
)

__all__ = [
    "Ceilings",
    "GaugeResolution",
    "Interval",
    "Response",
    "ResponseCube",
    "VarianceComponents",
    "aggregationCurve",
    "aurocCeiling",
    "bootstrapCi",
    "ceilings",
    "discriminationIndex",
    "effectiveSupport",
    "gaugeResolution",
    "gaugeVerdict",
    "minimumDetectableEffect",
    "normalCdf",
    "normalQuantile",
    "requiredK",
    "resolvingPower",
    "shannonEntropy",
    "varianceComponents",
]

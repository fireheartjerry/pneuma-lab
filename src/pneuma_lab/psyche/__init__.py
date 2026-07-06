"""Psyche — the machine-interiority substrate under test (Phase 1).

This sub-package holds:

    - the pure, ported 9to5 psyche math (affect manifold, prototype projection,
    mood homeostat, drive homeostat, earned-authority resolution),
    - deterministic state hashing (``hashing``),
    - the ``PsycheUnderTest`` interface every mind-under-test implements,
    - ``ReferencePsyche``: a deterministic Level-3 mind that wires and exercises
    all nine consciousness-indicator families and emits schema-valid output
    frames with ``CausalTrace`` receipts.

Nothing here imports from 9to5; the math is *ported* provenance (see
``migration/copied-from-9to5/reference-interfaces/``), adapted to drop the 9to5
``config`` dependency by inlining the documented defaults.
"""

from __future__ import annotations

from .interface import PsycheInputs, PsycheOutputs, PsycheUnderTest
from .reference import ReferencePsyche

__all__ = [
    "PsycheInputs",
    "PsycheOutputs",
    "PsycheUnderTest",
    "ReferencePsyche",
]

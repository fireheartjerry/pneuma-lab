"""Fail-closed result-to-paper pipeline for the PLACEBO manuscript.

The manuscript accepts numbers from exactly one object: a verified, sealed
Task 10 evidence package produced under an authority that licenses a
scientific result. Step 4A, unsealed roots, packages with no completed unblind
ceremony, missing receipts, and hand-entered values are refused by name.

Before such a package exists, every generated asset is an explicitly unfilled
scaffold with the final shape, and the preflight blocks. A pre-results draft is
EXPECTED to fail the preflight; the failure list is the submission checklist.
"""

from __future__ import annotations

from .package import SealedPackage, admit
from .preflight import PreflightReport, run
from .render import write_assets

__all__ = [
    "PreflightReport",
    "SealedPackage",
    "admit",
    "run",
    "write_assets",
]

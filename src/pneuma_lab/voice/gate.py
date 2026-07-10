"""The observed-vs-credited gate.

It does NOT hide machinery. Every atom that reached it is already *observed*
(a real frame/field backed it in extract). The gate only drops sub-epsilon
noise and then ranks deterministically. ``credit_status`` was set upstream from
the scorer and is preserved verbatim.
"""

from __future__ import annotations

from .atoms import ThoughtAtom

_DEFAULT_MIN_INTENSITY = 1e-6


def gate(
    atoms: list[ThoughtAtom], *, min_intensity: float = _DEFAULT_MIN_INTENSITY
) -> list[ThoughtAtom]:
    """Drop sub-epsilon atoms; return the rest ranked by (-intensity, atom_id)."""
    kept = [a for a in atoms if a.intensity > min_intensity]
    kept.sort(key=lambda a: (-a.intensity, a.atom_id))
    return kept


__all__ = ["gate"]

"""The receipts spine: one auditable object per run.

Renders nothing; it records the atoms' receipts, each atom's credit_status, the
authoritative evidence_level, and per-family status verbatim from the scorer.
The transcript and (Phase C) the monitor both read from this single source.
"""

from __future__ import annotations

from dataclasses import asdict

from .atoms import ThoughtAtom


def _family_status(evidence_frame: dict) -> dict[str, str]:
    families = evidence_frame.get("indicator_families", {}) or {}
    return {name: rec.get("status", "absent") for name, rec in families.items()}


def build_sidecar(
    *,
    run_id: str,
    subject: str,
    mode: str,
    evidence_frame: dict,
    per_tick_atoms: list[list[ThoughtAtom]],
) -> dict:
    """Assemble the deterministic per-run sidecar from the gated atoms."""
    ticks = []
    for tick_index, tick_atoms in enumerate(per_tick_atoms):
        ticks.append(
            {
                "tick": tick_index,
                "atoms": [asdict(a) for a in tick_atoms],
            }
        )
    return {
        "run_id": run_id,
        "subject": subject,
        "mode": mode,
        "evidence_level": int(evidence_frame.get("evidence_level", 0)),
        "indicator_family_status": _family_status(evidence_frame),
        "confabulation_risk": float(
            evidence_frame.get("roleplay_confabulation_risk", 0.0)
        ),
        "ticks": ticks,
    }


__all__ = ["build_sidecar"]

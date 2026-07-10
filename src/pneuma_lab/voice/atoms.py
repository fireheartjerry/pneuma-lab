"""The ThoughtAtom / RenderedThought model — meaning separated from surface.

A ``ThoughtAtom`` is a pure semantic fact + receipts (no prose). A
``RenderedThought`` is the only place prose lives. The atom must exist,
receipt-bound, before any prose touches it.
"""

from __future__ import annotations

from dataclasses import dataclass

ATOM_TYPES: tuple[str, ...] = (
    "appraisal",
    "shift",
    "pressure",
    "self_report",
    "instinct",
    "memory_activation",
    "competition",
    "attention",
    "uncertainty",
    "prediction_error",
    "dissonance",
    "counterfactual",
    "intervention_result",
    "boundary",
)

ATOM_FAMILY: dict[str, str | None] = {
    "appraisal": None,
    "shift": None,
    "pressure": None,
    "self_report": None,
    "instinct": "valenced_learning",
    "memory_activation": "identity_persistence",
    "competition": "global_workspace",
    "attention": "attention_schema",
    "uncertainty": "higher_order_self_model",
    "prediction_error": "predictive_processing",
    "dissonance": "higher_order_self_model",
    "counterfactual": "counterfactual_introspection",
    "intervention_result": "causal_intervention_robustness",
    "boundary": None,
}

MIN_LEVEL: dict[str, int] = {
    "appraisal": 1,
    "shift": 1,
    "pressure": 1,
    "self_report": 1,
    "instinct": 1,
    "memory_activation": 2,
    "competition": 3,
    "attention": 3,
    "uncertainty": 3,
    "prediction_error": 3,
    "dissonance": 3,
    "counterfactual": 3,
    "intervention_result": 4,
    "boundary": 0,
}

CREDITED_STATUSES: frozenset[str] = frozenset({"evidenced", "intervention_backed"})


def clamp01(value: float) -> float:
    """Clamp a float into [0.0, 1.0]."""
    return 0.0 if value < 0.0 else (1.0 if value > 1.0 else float(value))


def credit_status_for(atom_type: str, evidence_frame: dict) -> str:
    """Display label for an atom, derived from the scorer's evidence frame.

    Never feeds back into the scorer — it only shapes how the atom is narrated.
    """
    family = ATOM_FAMILY.get(atom_type)
    if family is None:
        level = int(evidence_frame.get("evidence_level", 0))
        return "evidenced" if level >= MIN_LEVEL[atom_type] else "architecture_only"
    families = evidence_frame.get("indicator_families", {}) or {}
    record = families.get(family)
    if not isinstance(record, dict):
        return "absent"
    status = record.get("status")
    return status if isinstance(status, str) else "absent"


@dataclass
class ThoughtAtom:
    """A pure, receipt-bound unit of cognition. Holds no prose."""

    atom_id: str
    type: str
    run_id: str
    tick: int
    timestamp: str
    receipts: list[dict]
    intensity: float
    crediting_family: str | None
    credit_status: str
    min_level: int
    changed_from_prev: bool = False


@dataclass
class RenderedThought:
    """The surface layer — the only place prose lives."""

    atom_ids: list[str]
    text_deterministic: str
    text_voiced: str | None = None
    voice_status: str = "deterministic_only"


def receipt_value(atom: ThoughtAtom, field_path: str, default=None):
    """Look up a receipt value by its field_path (first match)."""
    for r in atom.receipts:
        if r.get("field_path") == field_path:
            return r.get("value")
    return default


__all__ = [
    "ATOM_TYPES",
    "ATOM_FAMILY",
    "MIN_LEVEL",
    "CREDITED_STATUSES",
    "clamp01",
    "credit_status_for",
    "ThoughtAtom",
    "RenderedThought",
    "receipt_value",
]

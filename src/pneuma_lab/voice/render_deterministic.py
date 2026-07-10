"""Deterministic, state-grounded rendering: ThoughtAtom -> RenderedThought.

First-person is an interface convention, not an ontological claim. Phrasing is
vivid but state-grounded; a forbidden-claim scrub is the final safety net. The
register honors credit_status: an atom whose family is not credited is hedged as
architecture-only.
"""

from __future__ import annotations

import re

from .atoms import CREDITED_STATUSES, RenderedThought, ThoughtAtom, receipt_value

# Assertions of subjective experience that must never appear. The deterministic
# templates below avoid them by construction; this is the backstop (and is
# reused by Phase B's verifier).
_FORBIDDEN = re.compile(
    r"\b("
    r"i feel|i suffer|i experience|"
    r"i\s?(?:am|'m|’m)\s+(?:conscious|aware|sentient)|"
    r"i(?:'m| am) suffering|hurts me|subjective experience|"
    r"we (?:feel|are (?:conscious|aware|sentient))|torment|"
    r"my feelings?|"
    r"sentien\w*|phenomenal\w*|qualia|conscious experience|moral patient(?:hood)?"
    r")\b",
    re.IGNORECASE,
)


def scrub_forbidden(text: str) -> tuple[str, list[str]]:
    """Return (clean_text, removed_phrases). Removed spans become '[filtered]'."""
    removed: list[str] = []

    def _repl(match: re.Match) -> str:
        removed.append(match.group(0))
        return "[filtered]"

    return _FORBIDDEN.sub(_repl, text), removed


def _num(value, fmt="+.2f") -> str:
    return format(float(value), fmt) if isinstance(value, (int, float)) else str(value)


def _appraisal(atom: ThoughtAtom) -> str:
    n = receipt_value(atom, "causal_trace.changed_dimensions.count", 0)
    return f"Something registers in the world, and it lands in my state — {int(n)} dimensions move."


def _shift(atom: ThoughtAtom) -> str:
    # Relies on extract.py placing the primary field as atom.receipts[0].
    r = atom.receipts[0]
    return f"{r['field_path'].split('.', 1)[-1]} moves to {_num(r.get('value'))}."


def _pressure(atom: ThoughtAtom) -> str:
    # Relies on extract.py placing the primary field as atom.receipts[0].
    r = atom.receipts[0]
    name = r["field_path"].split(".", 1)[-1]
    return (
        f"A {name} pressure of {_num(r.get('value'), '.2f')} forms and is held there."
    )


def _self_report(atom: ThoughtAtom) -> str:
    parts = ", ".join(
        f"{r['field_path'].split('.', 1)[-1]}={_num(r.get('value'), '.2f')}"
        for r in atom.receipts
        if isinstance(r.get("value"), (int, float))
    )
    return f"The state reports itself: {parts}."


def _competition(atom: ThoughtAtom) -> str:
    # salience_scores.* receipts are pre-sorted and numeric in extract.py.
    winner = receipt_value(atom, "workspace_broadcast.winning_faculty", "?")
    saliences = [
        (r["field_path"].split(".", 1)[-1], r.get("value"))
        for r in atom.receipts
        if r["field_path"].startswith("salience_scores.")
    ]
    top = max(saliences, key=lambda kv: kv[1]) if saliences else (None, None)
    tail = f" at salience {_num(top[1], '.2f')}" if top[1] is not None else ""
    lead = (
        "It overtakes the prior winner"
        if atom.changed_from_prev
        else "It holds the workspace"
    )
    return f"Faculties contend for the workspace. {winner} takes it{tail}. {lead}."


def _memory_activation(atom: ThoughtAtom) -> str:
    scar = receipt_value(atom, "psyche_state.derived_signals.scar_strength", 0.0)
    return f"A scar activates — strength {_num(scar, '.2f')}; the past is pressing on the present."


def _uncertainty(atom: ThoughtAtom) -> str:
    pe = receipt_value(atom, "psyche_state.self_model.predicted_error", 0.0)
    return f"The self-model flags low confidence in its own read — predicted error {_num(pe, '.2f')}."


def _counterfactual(atom: ThoughtAtom) -> str:
    cond = receipt_value(atom, "counterfactual.condition", "a perturbation")
    return f"A counterfactual is imagined: under '{cond}', the downstream state should change. (Predicted, not tested.)"


def _boundary(atom: ThoughtAtom) -> str:
    level = receipt_value(atom, "consciousness_evidence.evidence_level", 0)
    return (
        f"This is not a consciousness claim. Evidence stands at level {int(level)}; "
        "the level-5 register (external audit, multi-family, longitudinal) is withheld."
    )


def _fallback(atom: ThoughtAtom) -> str:
    """Grounded generic line for atom types without a specialized renderer yet."""
    parts = ", ".join(
        f"{r['field_path'].split('.', 1)[-1]}={_num(r.get('value'), '.2f')}"
        if isinstance(r.get("value"), (int, float))
        else f"{r['field_path'].split('.', 1)[-1]}={r.get('value')}"
        for r in atom.receipts
    )
    return f"[{atom.type}] {parts}." if parts else f"[{atom.type}] (no receipts)."


_RENDERERS = {
    "appraisal": _appraisal,
    "shift": _shift,
    "pressure": _pressure,
    "self_report": _self_report,
    "competition": _competition,
    "memory_activation": _memory_activation,
    "uncertainty": _uncertainty,
    "counterfactual": _counterfactual,
    "boundary": _boundary,
}


def render(atom: ThoughtAtom) -> RenderedThought:
    """Render one atom into deterministic, credit-aware, state-grounded prose."""
    text = _RENDERERS.get(atom.type, _fallback)(atom)
    if atom.crediting_family and atom.credit_status not in CREDITED_STATUSES:
        text += " — architecture-only, not promotable evidence."
    text, _ = scrub_forbidden(text)
    return RenderedThought(atom_ids=[atom.atom_id], text_deterministic=text)


__all__ = ["render", "scrub_forbidden"]

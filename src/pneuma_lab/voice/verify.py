"""Verify a voiced passage against the deterministic source it must only rephrase.

This is a *syntactic + heuristic* gate, not a semantic-entailment check. It
blocks fabricated fact-tokens (numbers, snake_case/dotted identifiers), forbidden
ontological claims, dropped architecture-only hedges, and gross length expansion
(a proxy for bulk ungrounded content). It does NOT verify that the prose actually
follows from the source in meaning — a faithful-looking but subtly re-slanted
rephrase can still pass. On any violation the caller falls back to deterministic
text. The deterministic ``ReferenceVoiceSkin`` is the guaranteed-safe default;
full semantic verification of a free-text LLM skin is future work. The scorer
never sees prose at all.
"""

from __future__ import annotations

import re

from .render_deterministic import scrub_forbidden

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_IDENT = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[_.][A-Za-z0-9]+)+")
_HEDGE = "architecture-only"


def verify_voiced(text: str, source_texts: list[str]) -> tuple[bool, list[str]]:
    """Return (accepted, reasons). Empty reasons == accepted."""
    source = " ".join(source_texts)
    reasons: list[str] = []

    source_numbers = set(_NUMBER.findall(source))
    for tok in _NUMBER.findall(text):
        if tok not in source_numbers:
            reasons.append(f"invented number: {tok}")

    source_idents = set(_IDENT.findall(source))
    for tok in _IDENT.findall(text):
        if tok not in source_idents:
            reasons.append(f"invented identifier: {tok}")

    _, removed = scrub_forbidden(text)
    if removed:
        reasons.append(f"forbidden claim(s): {removed}")

    if _HEDGE in source and _HEDGE not in text:
        reasons.append("dropped architecture-only hedge")

    n_text = len(text.split())
    n_source = len(source.split())
    if n_text > 1.5 * n_source + 8:
        reasons.append(
            f"voiced text expands source too much ({n_text} vs {n_source} words) "
            "— possible ungrounded content"
        )

    return (not reasons, reasons)


__all__ = ["verify_voiced"]

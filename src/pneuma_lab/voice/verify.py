"""Verify a voiced passage against the deterministic source it must only rephrase.

The skin may make the grounded RenderedThoughts read naturally, but may add no
number, no snake_case/dotted identifier, no forbidden claim, and may not drop an
architecture-only hedge. On any violation the caller falls back to deterministic
text. This gate — not the scorer — is what keeps the vivid voice honest; the
scorer never sees prose at all.
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

    return (not reasons, reasons)


__all__ = ["verify_voiced"]

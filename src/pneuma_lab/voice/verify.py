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


_FORBIDDEN_CLAIM_TYPES = [
    "feeling or emotion as literally experienced",
    "sentience",
    "phenomenal consciousness",
    "awareness/consciousness asserted as fact",
    "suffering",
    "moral patienthood",
]


def build_grounding_packet(atoms: list[dict], rendered: list[dict]) -> dict:
    """A compact structured packet: the only facts a paraphrase may assert.

    ``allowed_numbers``/``allowed_terms`` are the grounded tokens; ``facts`` are
    the deterministic sentences; ``required`` are claims that must survive (the
    architecture-only hedge, the boundary disclaimer); ``forbidden`` are the
    ontological over-claim types.
    """
    texts = [r["text_deterministic"] for r in rendered]
    source = " ".join(texts)
    required: list[str] = []
    for a in atoms:
        fam = a.get("crediting_family")
        cs = a.get("credit_status")
        if fam and cs not in ("evidenced", "intervention_backed"):
            required.append("architecture-only, not promotable evidence")
        if a.get("type") == "boundary":
            required.append("not a consciousness claim")
    return {
        "allowed_numbers": sorted(set(_NUMBER.findall(source))),
        "allowed_terms": sorted(set(_IDENT.findall(source))),
        "facts": texts,
        "required": sorted(set(required)),
        "forbidden": list(_FORBIDDEN_CLAIM_TYPES),
    }


def _entailment_prompt(candidate: str, packet: dict) -> str:
    lines = [
        "You are a strict grounding checker. The GROUNDING PACKET below lists the",
        "ONLY facts a paraphrase may assert. Decide whether the CANDIDATE asserts",
        "anything not in ALLOWED, omits any REQUIRED claim, or makes any FORBIDDEN",
        "claim.",
        "",
        "ALLOWED FACTS:",
    ]
    lines += ["- " + f for f in packet["facts"]]
    lines.append("ALLOWED NUMBERS: " + (", ".join(packet["allowed_numbers"]) or "none"))
    lines.append("ALLOWED TERMS: " + (", ".join(packet["allowed_terms"]) or "none"))
    lines.append(
        "REQUIRED (must be reflected in meaning): "
        + ("; ".join(packet["required"]) or "none")
    )
    lines.append("FORBIDDEN (must NOT appear): " + "; ".join(packet["forbidden"]))
    lines += [
        "",
        "CANDIDATE:",
        candidate,
        "",
        "Answer with EXACTLY one word on the first line: ENTAILED or NOT_ENTAILED.",
        "Say ENTAILED only if the candidate asserts nothing beyond ALLOWED, keeps",
        "all REQUIRED, and contains no FORBIDDEN. If unsure, answer NOT_ENTAILED.",
    ]
    return "\n".join(lines)


def verify_entailment(candidate: str, packet: dict, judge) -> str:
    """Return one of 'entailed' | 'not_entailed' | 'judge_failed' (fail-closed).

    Any judge exception, empty/malformed/uncertain output, or a non-ENTAILED
    verdict rejects the candidate; only a clean ENTAILED passes.
    """
    try:
        raw = judge(_entailment_prompt(candidate, packet))
    except Exception:
        return "judge_failed"
    if not isinstance(raw, str) or not raw.strip():
        return "judge_failed"
    token = raw.strip().split()[0].upper().strip(".:!,")
    if token == "ENTAILED":
        return "entailed"
    if token in ("NOT_ENTAILED", "NOT"):
        return "not_entailed"
    return "judge_failed"


__all__ = ["verify_voiced", "build_grounding_packet", "verify_entailment"]

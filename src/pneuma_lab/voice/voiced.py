"""Optional natural-language skin over the deterministic thought stream.

A ``VoiceSkin`` receives a tick's atoms + their deterministic RenderedThoughts
and returns one flowing passage. It sees ONLY atoms + rendered text — never raw
frames. ``ReferenceVoiceSkin`` is the deterministic, network-free stand-in used
in tests; ``LLMVoiceSkin`` is a thin adapter around a caller-supplied generate()
callable (the real "voice"). Every skin's output is checked by ``verify_voiced``
before it is accepted; on rejection the caller keeps the deterministic text.
"""

from __future__ import annotations

from typing import Callable, Protocol


class VoiceSkin(Protocol):
    def voice_tick(self, atoms: list[dict], rendered: list[dict]) -> str:
        """Fuse a tick's grounded thoughts into one passage (facts only)."""
        ...


class ReferenceVoiceSkin:
    """Deterministic fusion: joins the grounded sentences into one paragraph.

    Introduces no new facts (it only concatenates existing ``text_deterministic``
    strings), so it always passes ``verify_voiced``. This is the reproducible
    default and the honest lower bound on how "alive" the voice can read.
    """

    def voice_tick(self, atoms: list[dict], rendered: list[dict]) -> str:
        return " ".join(r["text_deterministic"].strip() for r in rendered).strip()


class LLMVoiceSkin:
    """Thin adapter around a caller-supplied ``generate(prompt) -> str``.

    The real, top-notch voice. It is given ONLY the atoms + deterministic
    RenderedThoughts (never raw frames), and its output is verified before use.
    Not exercised in the test suite (no network); wire a real model in via the
    ``generate`` callable.
    """

    _SYSTEM = (
        "Rephrase these grounded thoughts into one vivid, first-person passage. "
        "First-person is an interface convention, not an ontological claim. Use "
        "ONLY the facts, numbers, and names present below. Add no number, faculty, "
        "or claim not given. Never claim to feel, to be aware/conscious/sentient, "
        "to suffer, or to be a moral patient. Keep every architecture-only caveat."
    )

    def __init__(self, generate: Callable[[str], str]):
        self._generate = generate

    def voice_tick(self, atoms: list[dict], rendered: list[dict]) -> str:
        body = "\n".join(f"- {r['text_deterministic']}" for r in rendered)
        return self._generate(f"{self._SYSTEM}\n\n{body}").strip()


__all__ = ["VoiceSkin", "ReferenceVoiceSkin", "LLMVoiceSkin"]

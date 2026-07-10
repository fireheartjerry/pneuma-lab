"""PneumaVoice-v0 — the expressive surface over the nervous system.

Read-only and additive: it consumes the existing output frames + the run's
ConsciousnessEvidenceFrame and renders a deterministic, receipt-bound thought
stream. It mutates no frame, grants no authority, contacts no verifier, and the
evidence scorer never reads its prose. Submodules are imported lazily to avoid a
cycle with ``psyche``/``replay``.
"""

from __future__ import annotations

__all__ = [
    "atoms",
    "extract",
    "gate",
    "render_deterministic",
    "sidecar",
    "stream",
    "transcript",
    "voiced",
    "verify",
]


def __getattr__(name: str):  # pragma: no cover - thin lazy loader
    if name in __all__:
        import importlib

        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

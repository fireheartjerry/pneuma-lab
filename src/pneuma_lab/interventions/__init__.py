"""Level-4 intervention harness: perturb internal psyche state and causally test it.

This subpackage turns Pneuma Lab from passive logging into intervention-based
evaluation. It supplies:

    - :mod:`operations` — pure operation math (clamp/disable/boost/noise/ablate/restore),
    - :class:`PerturbationSet` — the surface a psyche consults during a treated replay,
    - :class:`InterventionSchedule` — resolves ``duration`` windows to per-tick sets,
    - report helpers — expected-vs-observed delta scoring,
    - :class:`PairedReplayRunner` — counterbalanced control/treated/null replay,
      digest provenance, and honest Level-4 scoring.

Only the two leaf modules (``operations``, ``perturbation``) are imported eagerly.
The heavier modules (``schedule``, ``report``, ``runner``) reach back into
``replay``/``psyche``/``evals`` and are loaded lazily via :pep:`562` ``__getattr__``
so that ``psyche.reference`` can import the perturbation surface without a cycle.
"""

from __future__ import annotations

from .operations import OPERATIONS, apply_scalar, deterministic_noise
from .perturbation import Perturbable, PerturbationSet

__all__ = [
    "OPERATIONS",
    "apply_scalar",
    "deterministic_noise",
    "Perturbable",
    "PerturbationSet",
    "InterventionSchedule",
    "build_intervention_report",
    "evaluate_intervention",
    "extract_signal",
    "PairedReplayResult",
    "PairedReplayRunner",
]

# Lazily-resolved names -> defining submodule (avoids an import cycle at package init).
_LAZY = {
    "InterventionSchedule": "schedule",
    "build_intervention_report": "report",
    "evaluate_intervention": "report",
    "extract_signal": "report",
    "PairedReplayResult": "runner",
    "PairedReplayRunner": "runner",
}


def __getattr__(name: str):
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    mod = importlib.import_module(f".{module}", __name__)
    return getattr(mod, name)

"""Pilot admission protocol checks; never submits or authorizes a pilot."""

from __future__ import annotations

from collections.abc import Mapping

from .errors import CloudManifestError


# Both candidates use the approved g6e.2xlarge's sole L40S.  The admission
# cannot grow into TP2 or substitute an H100; Azure remains separately governed.
RUNG_NAMES = ("l40s-tp1-32768", "l40s-tp1-65536")
SELECTION_GATES = frozenset({"oom", "tool_call", "output_parity", "p10_throughput"})


def validate_protocol(protocol: Mapping[str, object]) -> None:
    if tuple(protocol.get("rungs", ())) != RUNG_NAMES:
        raise CloudManifestError("protocol must freeze the exact approved one-GPU rung set")


def select_rung(protocol: Mapping[str, object], measurements: Mapping[str, Mapping[str, bool]]) -> str:
    validate_protocol(protocol)
    for name, gates in measurements.items():
        if name not in RUNG_NAMES or set(gates) - SELECTION_GATES:
            raise CloudManifestError("pilot selection may use only named non-efficacy gates")
    passing = [name for name in RUNG_NAMES if set(measurements.get(name, {})) == SELECTION_GATES and all(measurements[name].values())]
    if not passing:
        raise CloudManifestError("no frozen pilot rung passes")
    return passing[-1]


def require_within_protocol(protocol: Mapping[str, object], *, cost: float, runtime: int, retries: int, samples: int) -> None:
    if cost > protocol["max_cost_usd"] or runtime > protocol["max_runtime_minutes"] or retries > protocol["max_retries"] or samples > protocol["max_samples"]:
        raise CloudManifestError("pilot would exceed frozen protocol")

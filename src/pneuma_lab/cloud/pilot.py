"""Pilot admission protocol checks; never submits or authorizes a pilot."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .errors import CloudManifestError


# Both candidates use the approved g6e.2xlarge's sole L40S.  The admission
# cannot grow into TP2 or substitute an H100; Azure remains separately governed.
RUNG_NAMES = ("l40s-tp1-32768", "l40s-tp1-65536")
SELECTION_GATES = frozenset({"oom", "tool_call", "output_parity", "p10_throughput"})
MINIMUM_P10_OUTPUT_TOKENS_PER_SECOND = 8.0


def validate_protocol(protocol: Mapping[str, object]) -> None:
    if tuple(protocol.get("rungs", ())) != RUNG_NAMES:
        raise CloudManifestError("protocol must freeze the exact approved one-GPU rung set")
    threshold = protocol.get("minimum_p10_output_tokens_per_second")
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or threshold <= 0:
        raise CloudManifestError("protocol lacks a positive preregistered p10-throughput threshold")
    if float(threshold) != MINIMUM_P10_OUTPUT_TOKENS_PER_SECOND:
        raise CloudManifestError(
            "protocol p10-throughput threshold must equal the DL-165 registered floor"
        )


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
    validate_protocol(protocol)
    if cost > protocol["max_cost_usd"] or runtime > protocol["max_runtime_minutes"] or retries > protocol["max_retries"] or samples > protocol["max_samples"]:
        raise CloudManifestError("pilot would exceed frozen protocol")


def protocol_digest(protocol: Mapping[str, object]) -> str:
    """Return the canonical digest a one-GPU receipt must bind."""

    validate_protocol(protocol)
    return hashlib.sha256(
        json.dumps(dict(protocol), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def require_receipt_within_protocol(
    receipt: Mapping[str, Any], protocol: Mapping[str, object]
) -> dict[str, Any]:
    """Require a structurally valid receipt to match the frozen p10 gate.

    A receipt stores only the protocol digest. This gate has the exact
    protocol bytes and therefore prevents a positive p10 observation from
    self-certifying a passing throughput result.
    """

    from .manifests import validate_pilot_admission_receipt

    verified = validate_pilot_admission_receipt(receipt)
    if verified["protocol_sha256"] != protocol_digest(protocol):
        raise CloudManifestError("pilot receipt is not bound to the exact frozen protocol")
    threshold = protocol["minimum_p10_output_tokens_per_second"]
    observed = verified["measurements"]["p10_output_tokens_per_second"]
    if verified["gates"]["p10_throughput"] != (observed >= threshold):
        raise CloudManifestError("p10-throughput gate contradicts the frozen protocol threshold")
    if verified["rung"] not in protocol["rungs"]:
        raise CloudManifestError("pilot receipt rung is not in the frozen protocol")
    return verified

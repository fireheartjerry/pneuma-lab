"""Compile raw two-worker qualification measurements into admission receipts.

This module is intentionally provider-free. A VPS worker records raw
non-efficacy measurements; this compiler binds the exact input bytes to the
typed receipt and refuses any attempt to turn one worker into two by relabeling
it. It never launches an instance, starts a model, or authorizes a pilot.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from .errors import CloudManifestError
from .manifests import validate_pilot_admission_receipt, validate_worker_admission_measurement
from .pilot import (
    MINIMUM_P10_OUTPUT_TOKENS_PER_SECOND,
    RUNG_NAMES,
    protocol_digest,
    require_receipt_within_protocol,
    require_worker_receipts_within_protocol,
    select_rung,
)


_MEASUREMENT_HASH_FIELDS = (
    "architecture_sha256",
    "authorization_sha256",
    "image_sha256",
    "input_lock_sha256",
    "code_sha256",
)


def measurement_evidence_digest(raw_bytes: bytes) -> str:
    """Return the SHA-256 of the exact raw measurement bytes retained by the worker."""

    if not isinstance(raw_bytes, bytes) or not raw_bytes:
        raise CloudManifestError("raw worker measurement evidence must be nonempty bytes")
    return hashlib.sha256(raw_bytes).hexdigest()


def _rung_gates(rung: Mapping[str, Any]) -> dict[str, bool]:
    tool_cases = int(rung["tool_call_cases"])
    tool_passes = int(rung["tool_call_passes"])
    parity_cases = int(rung["output_parity_cases"])
    parity_passes = int(rung["output_parity_passes"])
    if tool_passes > tool_cases or parity_passes > parity_cases:
        raise CloudManifestError("raw worker measurement has impossible passing-case counts")
    return {
        "oom": float(rung["peak_gpu_memory_gib"]) <= 44.0,
        "tool_call": tool_passes == tool_cases,
        "output_parity": parity_passes == parity_cases,
        "p10_throughput": float(rung["p10_output_tokens_per_second"])
        >= MINIMUM_P10_OUTPUT_TOKENS_PER_SECOND,
    }


def compile_worker_admission(
    measurement: Mapping[str, Any],
    protocol: Mapping[str, object],
    *,
    evidence_sha256: str,
) -> dict[str, Any]:
    """Compile one complete raw measurement into its selected-rung receipt.

    The output is a receipt only when at least one frozen rung passes all four
    gates. A raw no-go remains raw evidence and cannot be promoted by choosing
    a different rung or altering a count.
    """

    raw = validate_worker_admission_measurement(measurement)
    if raw["protocol_sha256"] != protocol_digest(protocol):
        raise CloudManifestError("raw worker measurement is not bound to the frozen pilot protocol")
    if not isinstance(evidence_sha256, str) or len(evidence_sha256) != 64:
        raise CloudManifestError("raw worker measurement digest must be a SHA-256 hex string")

    rung_gates = {name: _rung_gates(raw["rungs"][name]) for name in RUNG_NAMES}
    selected_rung = select_rung(protocol, rung_gates)
    selected = raw["rungs"][selected_rung]
    receipt = {
        "record_kind": "cloud_pilot_admission_receipt",
        "schema_version": "0.3.0",
        "protocol_sha256": raw["protocol_sha256"],
        "worker_index": raw["worker_index"],
        "instance_id": raw["instance_id"],
        "measurement_evidence_sha256": evidence_sha256,
        "rung": selected_rung,
        "compute": {
            "instance_type": "g6e.2xlarge",
            "vcpus": 8,
            "gpu_count": 1,
            "usable_gpu_memory_gib": 44,
        },
        "gates": rung_gates[selected_rung],
        "measurements": dict(selected),
    }
    for field in _MEASUREMENT_HASH_FIELDS:
        receipt[field] = raw[field]
    verified = validate_pilot_admission_receipt(receipt)
    return require_receipt_within_protocol(verified, protocol)


def compile_dual_worker_admissions(
    measurements: Mapping[int, tuple[Mapping[str, Any], str]],
    protocol: Mapping[str, object],
) -> dict[int, dict[str, Any]]:
    """Compile and validate the two independently sourced worker receipts."""

    if set(measurements) != {0, 1}:
        raise CloudManifestError("dual-worker compilation requires raw measurements for worker indexes 0 and 1")
    receipts = {
        index: compile_worker_admission(record, protocol, evidence_sha256=evidence_sha256)
        for index, (record, evidence_sha256) in measurements.items()
    }
    return require_worker_receipts_within_protocol(receipts, protocol)

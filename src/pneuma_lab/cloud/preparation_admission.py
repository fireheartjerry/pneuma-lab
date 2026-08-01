"""Two-layer authority gate for bounded pre-experiment provider actions."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .authorization_keys import Clock, canonical_bytes, instant, trusted_now, verify_ledger_binding, verify_signature
from .errors import CloudManifestError
from .manifests import _validate


_BOUND_FIELDS = ("ledger_row_id", "ledger_row_sha256", "human_authorization")


def _validate_authority_state(record: Mapping[str, Any], *, kind: str) -> dict[str, Any]:
    validated = _validate(record, expected_kind=kind)
    present = sum(validated[field] is not None for field in _BOUND_FIELDS)
    if validated["status"] == "authorized":
        if present != len(_BOUND_FIELDS):
            raise CloudManifestError(f"authorized {kind} requires a ledger binding and human signature")
    elif present:
        raise CloudManifestError(f"candidate {kind} must carry no ledger binding or human signature")
    return validated


def validate_preparation_envelope(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_authority_state(record, kind="cloud_preparation_envelope")


def validate_preparation_admission(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_authority_state(record, kind="cloud_preparation_admission")


def envelope_digest(record: Mapping[str, Any]) -> str:
    """Return the exact canonical digest admissions must bind."""

    return hashlib.sha256(canonical_bytes(validate_preparation_envelope(record))).hexdigest()


def require_preparation_admission(
    envelope_record: Mapping[str, Any],
    admission_record: Mapping[str, Any],
    *,
    key_registry: Mapping[str, Any],
    ledger_path: Path,
    expected_action_id: str,
    expected_action_class: str,
    expected_provider: str,
    expected_region: str,
    expected_manifest_sha256: str,
    expected_input_lock_sha256: str | None,
    expected_projected_cost_usd: float,
    expected_max_retries: int,
    spend_history_sha256: str,
    clock: Clock = trusted_now,
) -> dict[str, Any]:
    """Verify both signed layers and every exact execution-time binding."""

    envelope = validate_preparation_envelope(envelope_record)
    admission = validate_preparation_admission(admission_record)
    if envelope["status"] != "authorized" or admission["status"] != "authorized":
        raise CloudManifestError("provider preparation requires an authorized envelope and exact authorized admission")
    now = clock()
    verify_signature(envelope, key_registry, now=now)
    verify_signature(admission, key_registry, now=now)
    verify_ledger_binding(envelope, ledger_path)
    verify_ledger_binding(admission, ledger_path)
    if now > instant(envelope["expires_timestamp"]) or now > instant(admission["expires_timestamp"]):
        raise CloudManifestError("preparation authority has expired")
    if admission["preparation_envelope_sha256"] != envelope_digest(envelope):
        raise CloudManifestError("preparation admission is not bound to this exact envelope")
    if admission["provider"] != envelope["provider"]:
        raise CloudManifestError("preparation admission provider differs from its envelope")
    if admission["provider"] != expected_provider or admission["region"] != expected_region:
        raise CloudManifestError("preparation admission does not bind the requested provider and region")
    if admission["action_id"] != expected_action_id:
        raise CloudManifestError("preparation admission does not bind the requested action id")
    if admission["action_class"] not in envelope["allowed_action_classes"]:
        raise CloudManifestError("preparation action class is outside the envelope")
    if admission["action_class"] != expected_action_class:
        raise CloudManifestError("preparation admission does not authorize the requested action class")
    if admission["manifest_sha256"] != expected_manifest_sha256:
        raise CloudManifestError("preparation admission does not bind the requested manifest")
    if admission["input_lock_sha256"] != expected_input_lock_sha256:
        raise CloudManifestError("preparation admission does not bind the requested input lock")
    if admission["spend_history_sha256"] != spend_history_sha256:
        raise CloudManifestError("preparation admission does not bind the current spend history")
    if float(admission["projected_cost_usd"]) != expected_projected_cost_usd:
        raise CloudManifestError("preparation admission does not bind the requested projected cost")
    if int(admission["max_retries"]) != expected_max_retries:
        raise CloudManifestError("preparation admission does not bind the requested retry ceiling")
    if float(admission["prior_envelope_spend_usd"]) + float(admission["projected_cost_usd"]) > float(envelope["total_cost_ceiling_usd"]):
        raise CloudManifestError("preparation action exceeds its envelope cost ceiling")
    return admission

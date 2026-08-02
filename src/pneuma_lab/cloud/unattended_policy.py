"""Standing low-risk spend authority with controller-internal hash receipts.

Operators approve a readable envelope once. They never type or repeat a digest.
The controller still binds each admission to the exact policy and job inputs in
its receipt. This module performs local admission only; it has no provider client.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from .errors import CloudManifestError
from .manifests import _validate

_SCIENTIFIC_ACTIONS = frozenset({"canonical_experiment", "scientific_replication", "training", "result_promotion"})


def _parse_timestamp(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise CloudManifestError(f"{field} must be an RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CloudManifestError(f"{field} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise CloudManifestError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def policy_digest(policy: Mapping[str, object]) -> str:
    """Return the controller-owned evidence binding for a validated policy."""

    encoded = json.dumps(dict(policy), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_unattended_policy(record: Mapping[str, Any]) -> dict[str, Any]:
    policy = _validate(record, expected_kind="cloud_unattended_spend_policy")
    starts = _parse_timestamp(policy["valid_from"], field="valid_from")
    expires = _parse_timestamp(policy["expires_at"], field="expires_at")
    if expires <= starts:
        raise CloudManifestError("policy expiry must follow activation")
    if policy["per_job_ceiling_usd"] > policy["rolling_ceiling_usd"]:
        raise CloudManifestError("per-job ceiling cannot exceed rolling ceiling")
    approval = policy["operator_approval"]
    if approval is not None and approval["statement"] != _summary(policy):
        raise CloudManifestError("operator approval must equal the complete readable policy summary")
    return policy


def _summary(checked: Mapping[str, Any]) -> str:
    providers = ", ".join(checked["providers"])
    actions = ", ".join(checked["allowed_action_classes"])
    return (
        f"Allow {actions} on {providers}, up to USD {checked['per_job_ceiling_usd']:.2f} per job "
        f"and USD {checked['rolling_ceiling_usd']:.2f} per {checked['rolling_window_days']} days, "
        f"until {checked['expires_at']}."
    )


def readable_policy_summary(policy: Mapping[str, Any]) -> str:
    return _summary(validate_unattended_policy(policy))


def admit_unattended_job(
    policy: Mapping[str, Any],
    request: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
    *,
    now: datetime,
) -> dict[str, Any]:
    """Admit one bounded job or fail before any provider action.

    ``history`` must contain controller receipts, not caller-estimated totals.
    A caller assertion still cannot authenticate external billing data; live
    execution must pair this gate with the provider-side watchdog and ledger.
    """

    checked = validate_unattended_policy(policy)
    instant = now.astimezone(timezone.utc)
    if checked["status"] != "active" or checked["operator_approval"] is None:
        raise CloudManifestError("unattended policy is not active")
    if not (_parse_timestamp(checked["valid_from"], field="valid_from") <= instant < _parse_timestamp(checked["expires_at"], field="expires_at")):
        raise CloudManifestError("unattended policy is not currently valid")

    provider = request.get("provider")
    action = request.get("action_class")
    projected = request.get("projected_cost_usd")
    retries = request.get("retry_count")
    binding = request.get("input_binding_sha256")
    if provider not in checked["providers"]:
        raise CloudManifestError("provider is outside unattended authority")
    if action in _SCIENTIFIC_ACTIONS or action not in checked["allowed_action_classes"]:
        raise CloudManifestError("action class requires separate human-readable authority")
    if not isinstance(projected, (int, float)) or isinstance(projected, bool) or projected <= 0:
        raise CloudManifestError("projected cost must be positive")
    if projected > checked["per_job_ceiling_usd"]:
        raise CloudManifestError("job exceeds unattended per-job ceiling")
    if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0 or retries > checked["max_retries_per_job"]:
        raise CloudManifestError("job retry count exceeds unattended policy")
    if not isinstance(binding, str) or len(binding) != 64 or any(char not in "0123456789abcdef" for char in binding):
        raise CloudManifestError("job inputs require an internal SHA-256 binding")

    digest = policy_digest(checked)
    window_start = instant - timedelta(days=checked["rolling_window_days"])
    consumed = 0.0
    for receipt in history:
        if receipt.get("policy_id") != checked["policy_id"]:
            continue
        occurred = _parse_timestamp(receipt.get("recorded_at"), field="history.recorded_at")
        if occurred > instant:
            raise CloudManifestError("future-dated spend receipt is forbidden")
        if occurred >= window_start and receipt.get("state") in {"reserved", "settled"}:
            amount = receipt.get("amount_usd")
            if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount < 0:
                raise CloudManifestError("spend history contains an invalid amount")
            consumed += float(amount)
    if consumed + float(projected) > checked["rolling_ceiling_usd"]:
        raise CloudManifestError("job exceeds unattended rolling ceiling")

    request_digest = hashlib.sha256(
        json.dumps(dict(request), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "record_kind": "cloud_unattended_admission_receipt",
        "policy_id": checked["policy_id"],
        "policy_sha256": digest,
        "request_sha256": request_digest,
        "input_binding_sha256": binding,
        "reserved_usd": float(projected),
        "recorded_at": instant.isoformat().replace("+00:00", "Z"),
    }

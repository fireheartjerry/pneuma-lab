"""Fail-closed checks for the signed AWS preparation envelope."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .authorization_keys import instant, verify_ledger_binding, verify_signature
from .errors import CloudManifestError
from .input_lock import require_real_candidate_lock
from .inputs import verify_input_lock
from .manifests import _validate


_RETRIEVAL_IMAGE_ACTIONS = frozenset({"immutable_input_retrieval", "licence_contamination_audit", "container_build", "storage"})
_SMOKE_PILOT_ACTIONS = frozenset({"non_scientific_smoke", "bounded_api_pilot"})


def validate_preparation_authorization(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the fixed-shape envelope before inspecting its signature."""

    authorization = _validate(record, expected_kind="cloud_preparation_authorization")
    if instant(authorization["window_end"]) <= instant(authorization["window_start"]):
        raise CloudManifestError("preparation authorization has an empty rolling window")
    return authorization


def _digest(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def validate_preparation_admission(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a concrete admission request before authenticating it."""

    return _validate(record, expected_kind="cloud_preparation_admission")


def _rolling_aws_spend_history(ledger_bytes: bytes, *, window_start: str, at: str) -> float:
    """Derive the bounded envelope's AWS cost from its exact ledger snapshot.

    This deliberately parses the append-only action table rather than accepting
    a number from the caller.  Each applicable row contributes its settled
    economic cost plus any live reservation; a pending row is conservatively
    treated as a reservation too.  The signed admission binds the same bytes,
    so a later ledger edit invalidates admission before a provider operation.
    """

    total = Decimal("0")
    start = instant(window_start)
    end = instant(at)
    for raw_line in ledger_bytes.decode("utf-8").splitlines():
        if not raw_line.startswith("| CL-"):
            continue
        cells = [cell.strip() for cell in raw_line.strip().strip("|").split("|")]
        if len(cells) != 12:
            raise CloudManifestError("malformed spend-history action-ledger row")
        _, timestamp, provider, _, _, _, _, reserved, settled, _, state, _ = cells
        if "aws" not in provider.lower():
            continue
        moment = instant(timestamp)
        if not (start <= moment <= end):
            continue
        try:
            settled_cost = Decimal(settled.replace(",", ""))
            reservation = Decimal(reserved.replace(",", ""))
        except InvalidOperation as exc:
            raise CloudManifestError("spend-history row has a non-numeric cost") from exc
        if settled_cost < 0 or reservation < 0:
            raise CloudManifestError("spend-history row has a negative cost")
        total += settled_cost
        if state.lower() in {"active", "pending"}:
            total += reservation
    return float(total)


def require_preparation_admission(
    record: Mapping[str, Any], *, key_registry: Mapping[str, Any], ledger_path: Path,
    at: str, provider: str, action: str, input_lock_sha256: str, scopes: Sequence[str],
    projected_cost_usd: float, retries: int, spend_history_complete: bool,
    spent_or_reserved_usd: float, teardown_protected: bool,
) -> dict[str, Any]:
    """Admit one bounded preparation action or fail before provider activity.

    The caller must supply a complete settled-plus-reserved history rather than
    letting an unknown balance be treated as zero.  Input lock and scopes are
    required even for build/storage work, preventing a generic envelope from
    becoming a transferable cloud blank cheque.
    """

    authorization = validate_preparation_authorization(record)
    if provider != authorization["provider"]:
        raise CloudManifestError("preparation authorization provider drift")
    if action not in authorization["allowed_actions"]:
        raise CloudManifestError("action is outside the preparation authorization")
    if not input_lock_sha256 or len(input_lock_sha256) != 64 or not scopes:
        raise CloudManifestError("admission requires an exact input lock and nonempty scopes")
    if not spend_history_complete:
        raise CloudManifestError("incomplete spend history; no preparation action permitted")
    if not teardown_protected:
        raise CloudManifestError("missing teardown protection; no preparation action permitted")
    if projected_cost_usd < 0 or spent_or_reserved_usd < 0:
        raise CloudManifestError("negative cost accounting is invalid")
    if retries < 0 or retries > authorization["max_retries_per_job"]:
        raise CloudManifestError("retry count exceeds the preparation authorization")
    if action in _RETRIEVAL_IMAGE_ACTIONS:
        per_job_ceiling = authorization["per_job_ceiling_usd"]["retrieval_or_image_build"]
    elif action in _SMOKE_PILOT_ACTIONS:
        per_job_ceiling = authorization["per_job_ceiling_usd"]["smoke_or_bounded_api_pilot"]
    else:  # Schema protects this, but retain the refusal at the executable gate.
        raise CloudManifestError("unclassified preparation action")
    if projected_cost_usd > per_job_ceiling:
        raise CloudManifestError("projected action cost exceeds its per-job ceiling")
    if spent_or_reserved_usd + projected_cost_usd > authorization["rolling_ceiling_usd"]:
        raise CloudManifestError("projected action exceeds the rolling preparation ceiling")
    moment = instant(at)
    if not (instant(authorization["window_start"]) <= moment <= instant(authorization["window_end"])):
        raise CloudManifestError("preparation authorization is outside its rolling window")
    verify_signature(authorization, key_registry, at=at)
    verify_ledger_binding(authorization, ledger_path)
    return authorization


def require_signed_preparation_admission(
    envelope: Mapping[str, Any], admission: Mapping[str, Any], *, key_registry: Mapping[str, Any],
    ledger_path: Path, at: str, input_lock: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify one immutable admission under the signed rolling envelope.

    The generic envelope cannot itself authorize a provider action: this
    function requires the separate signed admission record whose body binds the
    action's exact input lock, scopes, projected cost, evidence-history digest,
    teardown assertion, and expiry.  A digest string or rolling total supplied
    by a caller is never enough: the candidate lock and complete on-disk ledger
    bytes are re-hashed at the decision boundary, and the rolling AWS spend is
    derived from those exact bytes.
    """

    authorized = validate_preparation_authorization(envelope)
    concrete = validate_preparation_admission(admission)
    verified_lock = require_real_candidate_lock(input_lock)
    if concrete["input_lock_sha256"] != verify_input_lock(verified_lock):
        raise CloudManifestError("admission is not bound to the supplied exact input lock")
    if not ledger_path.is_file():
        raise CloudManifestError("complete spend-history ledger is missing")
    spend_history_bytes = ledger_path.read_bytes()
    if concrete["spend_history_sha256"] != hashlib.sha256(spend_history_bytes).hexdigest():
        raise CloudManifestError("admission is not bound to the current complete spend-history ledger")
    if concrete["envelope_sha256"] != _digest(authorized):
        raise CloudManifestError("admission is not bound to this exact preparation envelope")
    require_preparation_admission(
        authorized,
        key_registry=key_registry,
        ledger_path=ledger_path,
        at=at,
        provider=concrete["provider"],
        action=concrete["action"],
        input_lock_sha256=concrete["input_lock_sha256"],
        scopes=concrete["scopes"],
        projected_cost_usd=concrete["projected_cost_usd"],
        retries=concrete["retries"],
        spend_history_complete=concrete["spend_history_complete"],
        spent_or_reserved_usd=_rolling_aws_spend_history(
            spend_history_bytes, window_start=authorized["window_start"], at=at,
        ),
        teardown_protected=concrete["teardown_protected"],
    )
    verify_signature(concrete, key_registry, at=at)
    verify_ledger_binding(concrete, ledger_path)
    return concrete

"""Sign and verify the exact two-stage Step 5B inventory admission.

This script is intended to run only in the CloudShell that holds the registered
private key. It never generates a key and never prints private material.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pneuma_lab.cloud.authorization_keys import (
    authorization_body_digest,
    canonical_bytes,
    canonical_ledger_digest,
    ledger_row,
    signed_body,
)
from pneuma_lab.cloud.inventory_discovery import inventory_plan_digest, validate_inventory_plan
from pneuma_lab.cloud.preparation_admission import envelope_digest, require_preparation_admission


def _private_key(path: Path) -> Ed25519PrivateKey:
    raw = path.read_bytes()
    try:
        loaded = serialization.load_pem_private_key(raw, password=None)
    except ValueError:
        compact = raw.strip()
        try:
            compact = bytes.fromhex(compact.decode("ascii"))
        except (UnicodeDecodeError, ValueError):
            pass
        if len(compact) != 32:
            raise ValueError("private key must be Ed25519 PEM, 32 raw bytes, or 64 hex characters") from None
        return Ed25519PrivateKey.from_private_bytes(compact)
    if not isinstance(loaded, Ed25519PrivateKey):
        raise ValueError("private key is not Ed25519")
    return loaded


def _approval(granted: str, expires: str) -> dict[str, Any]:
    return {
        "approver_id": "jerry-mathos-ai",
        "key_id": "pneuma-b1-20260731",
        "granted_timestamp": granted,
        "expires_timestamp": expires,
        "body_sha256": "0" * 64,
        "signature_ed25519": "0" * 128,
    }


def _sign(private: Ed25519PrivateKey, record: dict[str, Any]) -> dict[str, Any]:
    body = canonical_bytes(signed_body(record))
    record["human_authorization"]["body_sha256"] = hashlib.sha256(body).hexdigest()
    record["human_authorization"]["signature_ed25519"] = private.sign(body).hex()
    return record


def build_signed_records(
    *, private: Ed25519PrivateKey, plan: dict[str, Any], ledger_path: Path,
    granted_timestamp: str, expires_timestamp: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = validate_inventory_plan(plan)
    plan_sha256 = inventory_plan_digest(plan)
    envelope_row = ledger_row(ledger_path, "CL-034")
    admission_row = ledger_row(ledger_path, "CL-035")
    envelope = _sign(private, {
        "record_kind": "cloud_preparation_envelope",
        "schema_version": "0.1.0",
        "frozen_timestamp": granted_timestamp,
        "status": "authorized",
        "provider": "aws",
        "allowed_action_classes": ["input_retrieval"],
        "total_cost_ceiling_usd": 0.0,
        "expires_timestamp": expires_timestamp,
        "ledger_row_id": "CL-034",
        "ledger_row_sha256": hashlib.sha256(envelope_row.encode("utf-8")).hexdigest(),
        "human_authorization": _approval(granted_timestamp, expires_timestamp),
    })
    admission = _sign(private, {
        "record_kind": "cloud_preparation_admission",
        "schema_version": "0.1.0",
        "frozen_timestamp": granted_timestamp,
        "status": "authorized",
        "preparation_envelope_sha256": envelope_digest(envelope),
        "action_id": plan["action_id"],
        "action_class": "input_retrieval",
        "provider": plan["provider"],
        "region": plan["region"],
        "input_lock_sha256": None,
        "manifest_sha256": plan_sha256,
        "prior_envelope_spend_usd": 0.0,
        "projected_cost_usd": 0.0,
        "max_retries": plan["max_retries"],
        "spend_history_sha256": canonical_ledger_digest(ledger_path),
        "teardown_protected": True,
        "expires_timestamp": expires_timestamp,
        "ledger_row_id": "CL-035",
        "ledger_row_sha256": hashlib.sha256(admission_row.encode("utf-8")).hexdigest(),
        "human_authorization": _approval(granted_timestamp, expires_timestamp),
    })
    return envelope, admission


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--key-registry", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--expires", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    granted = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    registry = json.loads(args.key_registry.read_text(encoding="utf-8"))
    envelope, admission = build_signed_records(
        private=_private_key(args.private_key), plan=plan, ledger_path=args.ledger,
        granted_timestamp=granted, expires_timestamp=args.expires,
    )
    require_preparation_admission(
        envelope, admission, key_registry=registry, ledger_path=args.ledger,
        expected_action_id=plan["action_id"], expected_action_class="input_retrieval",
        expected_provider=plan["provider"], expected_region=plan["region"],
        expected_manifest_sha256=inventory_plan_digest(plan), expected_input_lock_sha256=None,
        expected_projected_cost_usd=0.0, expected_max_retries=plan["max_retries"],
        spend_history_sha256=admission["spend_history_sha256"],
    )
    package = {
        "record_kind": "step5b_inventory_signing_package",
        "plan_sha256": inventory_plan_digest(plan),
        "envelope_body_sha256": authorization_body_digest(envelope),
        "admission_body_sha256": authorization_body_digest(admission),
        "envelope": envelope,
        "admission": admission,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(package) + b"\n")
    print(json.dumps({key: package[key] for key in ("plan_sha256", "envelope_body_sha256", "admission_body_sha256")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

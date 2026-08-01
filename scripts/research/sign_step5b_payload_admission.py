"""Sign and verify the exact Step 5B payload-mirroring admission.

Run only in the CloudShell that holds the registered private key. The script
never generates a key, never prints private material, and refuses a plan whose
price, lifecycle proof, or bound executor surface is stale.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pneuma_lab.cloud.authorization_keys import (
    authorization_body_digest,
    canonical_bytes,
    canonical_ledger_digest,
    ledger_row,
)
from pneuma_lab.cloud.payload_inventory import validate_payload_manifest_semantics
from pneuma_lab.cloud.payload_pricing import validate_payload_pricing_semantics
from pneuma_lab.cloud.payload_retrieval_plan import (
    executor_sources_digest,
    payload_retrieval_plan_digest,
    validate_payload_retrieval_plan_semantics,
)
from pneuma_lab.cloud.preparation_admission import envelope_digest, require_preparation_admission
from pneuma_lab.cloud.step5b_lifecycle import step5b_lifecycle_receipt_digest
try:
    from scripts.research.sign_step5b_inventory_admission import _approval, _private_key, _sign
except ModuleNotFoundError:  # Direct script execution puts scripts/research on sys.path.
    from sign_step5b_inventory_admission import _approval, _private_key, _sign


ENVELOPE_LEDGER_ROW = "CL-045"
ADMISSION_LEDGER_ROW = "CL-046"


def build_signed_records(
    *, private: Ed25519PrivateKey, plan: dict[str, Any], ledger_path: Path,
    projected_cost_usd: float, granted_timestamp: str, expires_timestamp: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    plan_sha256 = payload_retrieval_plan_digest(plan)
    envelope_row = ledger_row(ledger_path, ENVELOPE_LEDGER_ROW)
    admission_row = ledger_row(ledger_path, ADMISSION_LEDGER_ROW)
    envelope = _sign(private, {
        "record_kind": "cloud_preparation_envelope",
        "schema_version": "0.1.0",
        "frozen_timestamp": granted_timestamp,
        "status": "authorized",
        "provider": plan["provider"],
        "allowed_action_classes": ["input_retrieval"],
        "total_cost_ceiling_usd": plan["cost_ceiling_usd"],
        "expires_timestamp": expires_timestamp,
        "ledger_row_id": ENVELOPE_LEDGER_ROW,
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
        "projected_cost_usd": projected_cost_usd,
        "max_retries": plan["max_retries"],
        "spend_history_sha256": canonical_ledger_digest(ledger_path),
        "teardown_protected": True,
        "expires_timestamp": expires_timestamp,
        "ledger_row_id": ADMISSION_LEDGER_ROW,
        "ledger_row_sha256": hashlib.sha256(admission_row.encode("utf-8")).hexdigest(),
        "human_authorization": _approval(granted_timestamp, expires_timestamp),
    })
    return envelope, admission


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pricing", type=Path, required=True)
    parser.add_argument("--lifecycle-receipt", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--key-registry", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--expires", required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = validate_payload_manifest_semantics(json.loads(args.manifest.read_text(encoding="utf-8")))
    plan = validate_payload_retrieval_plan_semantics(json.loads(args.plan.read_text(encoding="utf-8")), manifest)
    pricing = validate_payload_pricing_semantics(json.loads(args.pricing.read_text(encoding="utf-8")), manifest)
    lifecycle = json.loads(args.lifecycle_receipt.read_text(encoding="utf-8"))
    if plan["status"] != "ready_for_signature":
        raise ValueError("payload plan is not ready for signature")
    if hashlib.sha256(args.pricing.read_bytes()).hexdigest() != plan["pricing_receipt_sha256"]:
        raise ValueError("pricing receipt bytes do not match the payload plan")
    if step5b_lifecycle_receipt_digest(lifecycle, plan) != plan["lifecycle_live_receipt_sha256"]:
        raise ValueError("live lifecycle receipt does not match the payload plan")
    if executor_sources_digest(args.repo_root) != plan["executor_sources_sha256"]:
        raise ValueError("executor source surface does not match the payload plan")

    granted = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    registry = json.loads(args.key_registry.read_text(encoding="utf-8"))
    envelope, admission = build_signed_records(
        private=_private_key(args.private_key), plan=plan, ledger_path=args.ledger,
        projected_cost_usd=float(pricing["projected_cost_usd"]),
        granted_timestamp=granted, expires_timestamp=args.expires,
    )
    require_preparation_admission(
        envelope, admission, key_registry=registry, ledger_path=args.ledger,
        expected_action_id=plan["action_id"], expected_action_class="input_retrieval",
        expected_provider=plan["provider"], expected_region=plan["region"],
        expected_manifest_sha256=payload_retrieval_plan_digest(plan), expected_input_lock_sha256=None,
        expected_projected_cost_usd=float(pricing["projected_cost_usd"]),
        expected_max_retries=plan["max_retries"], spend_history_sha256=canonical_ledger_digest(args.ledger),
    )
    package = {
        "record_kind": "step5b_payload_signing_package",
        "plan_sha256": payload_retrieval_plan_digest(plan),
        "pricing_receipt_sha256": plan["pricing_receipt_sha256"],
        "lifecycle_live_receipt_sha256": plan["lifecycle_live_receipt_sha256"],
        "executor_sources_sha256": plan["executor_sources_sha256"],
        "envelope_body_sha256": authorization_body_digest(envelope),
        "admission_body_sha256": authorization_body_digest(admission),
        "envelope": envelope,
        "admission": admission,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(package) + b"\n")
    print(json.dumps({key: package[key] for key in (
        "plan_sha256", "pricing_receipt_sha256", "lifecycle_live_receipt_sha256",
        "executor_sources_sha256", "envelope_body_sha256", "admission_body_sha256",
    )}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

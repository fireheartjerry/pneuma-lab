"""Sign one exact bounded preparation action using the registered CloudShell key."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pneuma_lab.cloud.authorization_keys import (
    authorization_body_digest,
    canonical_bytes,
    canonical_ledger_digest,
    ledger_row,
)
from pneuma_lab.cloud.preparation_admission import envelope_digest, require_preparation_admission
try:
    from scripts.research.sign_step5b_inventory_admission import _approval, _private_key, _sign
except ModuleNotFoundError:
    from sign_step5b_inventory_admission import _approval, _private_key, _sign


def plan_digest(plan: dict[str, Any]) -> str:
    body = dict(plan)
    body.pop("plan_sha256", None)
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--key-registry", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--expires", required=True)
    parser.add_argument("--envelope-ledger-row", required=True)
    parser.add_argument("--admission-ledger-row", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    digest = plan_digest(plan)
    if digest != plan["plan_sha256"]:
        raise ValueError("plan_sha256 does not match canonical plan bytes with that field removed")
    granted = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    private = _private_key(args.private_key)
    envelope_row = ledger_row(args.ledger, args.envelope_ledger_row)
    admission_row = ledger_row(args.ledger, args.admission_ledger_row)
    envelope = _sign(private, {
        "record_kind": "cloud_preparation_envelope", "schema_version": "0.1.0",
        "frozen_timestamp": granted, "status": "authorized", "provider": plan["provider"],
        "allowed_action_classes": [plan["action_class"]],
        "total_cost_ceiling_usd": plan["cost_ceiling_usd"], "expires_timestamp": args.expires,
        "ledger_row_id": args.envelope_ledger_row,
        "ledger_row_sha256": hashlib.sha256(envelope_row.encode()).hexdigest(),
        "human_authorization": _approval(granted, args.expires),
    })
    admission = _sign(private, {
        "record_kind": "cloud_preparation_admission", "schema_version": "0.1.0",
        "frozen_timestamp": granted, "status": "authorized",
        "preparation_envelope_sha256": envelope_digest(envelope), "action_id": plan["action_id"],
        "action_class": plan["action_class"], "provider": plan["provider"], "region": plan["region"],
        "input_lock_sha256": plan["input_lock_sha256"], "manifest_sha256": digest,
        "prior_envelope_spend_usd": 0.0, "projected_cost_usd": plan["projected_cost_usd"],
        "max_retries": plan["max_retries"], "spend_history_sha256": canonical_ledger_digest(args.ledger),
        "teardown_protected": True, "expires_timestamp": args.expires,
        "ledger_row_id": args.admission_ledger_row,
        "ledger_row_sha256": hashlib.sha256(admission_row.encode()).hexdigest(),
        "human_authorization": _approval(granted, args.expires),
    })
    registry = json.loads(args.key_registry.read_text(encoding="utf-8"))
    require_preparation_admission(
        envelope, admission, key_registry=registry, ledger_path=args.ledger,
        expected_action_id=plan["action_id"], expected_action_class=plan["action_class"],
        expected_provider=plan["provider"], expected_region=plan["region"],
        expected_manifest_sha256=digest, expected_input_lock_sha256=plan["input_lock_sha256"],
        expected_projected_cost_usd=plan["projected_cost_usd"], expected_max_retries=plan["max_retries"],
        spend_history_sha256=canonical_ledger_digest(args.ledger),
    )
    package = {"record_kind": "cloud_preparation_signing_package", "plan_sha256": digest,
               "envelope_body_sha256": authorization_body_digest(envelope),
               "admission_body_sha256": authorization_body_digest(admission),
               "envelope": envelope, "admission": admission}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(package) + b"\n")
    print(json.dumps({key: package[key] for key in ("plan_sha256", "envelope_body_sha256", "admission_body_sha256")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

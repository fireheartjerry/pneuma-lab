from __future__ import annotations

import json
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pneuma_lab.cloud.authorization_keys import canonical_ledger_digest
from pneuma_lab.cloud.inventory_discovery import build_inventory_plan, inventory_plan_digest
from pneuma_lab.cloud.preparation_admission import require_preparation_admission
from scripts.research.sign_step5b_inventory_admission import build_signed_records


def test_two_stage_inventory_ceremony_binds_exact_plan(tmp_path) -> None:
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw().hex()
    ledger = tmp_path / "ledger.md"
    ledger.write_text(
        "| CL-034 | envelope |\n| CL-035 | admission |\n", encoding="utf-8"
    )
    plan = build_inventory_plan(frozen_timestamp="2026-08-01T00:00:00Z")
    envelope, admission = build_signed_records(
        private=private, plan=plan, ledger_path=ledger,
        granted_timestamp="2026-08-01T00:00:00Z", expires_timestamp="2026-08-08T00:00:00Z",
    )
    registry = {
        "record_kind": "cloud_approver_key_registry", "schema_version": "0.1.0",
        "frozen_timestamp": "2026-08-01T00:00:00Z", "keys": [{
            "key_id": "pneuma-b1-20260731", "approver_id": "jerry-mathos-ai",
            "algorithm": "ed25519", "public_key_hex": public,
            "not_before": "2026-08-01T00:00:00Z", "not_after": "2027-08-01T00:00:00Z",
            "status": "active", "revoked_timestamp": None, "revocation_reason": None,
        }],
    }
    result = require_preparation_admission(
        envelope, admission, key_registry=registry, ledger_path=ledger,
        expected_action_id=plan["action_id"], expected_action_class="input_retrieval",
        expected_provider="aws", expected_region="us-east-1",
        expected_manifest_sha256=inventory_plan_digest(plan), expected_input_lock_sha256=None,
        expected_projected_cost_usd=0.0, expected_max_retries=1,
        spend_history_sha256=canonical_ledger_digest(ledger),
        clock=lambda: datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    assert result["preparation_envelope_sha256"]
    assert json.loads(json.dumps(result))["manifest_sha256"] == inventory_plan_digest(plan)


def test_spend_history_digest_is_crlf_portable(tmp_path) -> None:
    lf = tmp_path / "lf.md"
    crlf = tmp_path / "crlf.md"
    lf.write_bytes(b"| CL-034 | envelope |\n| CL-035 | admission |\n")
    crlf.write_bytes(b"| CL-034 | envelope |\r\n| CL-035 | admission |\r\n")
    assert canonical_ledger_digest(lf) == canonical_ledger_digest(crlf)

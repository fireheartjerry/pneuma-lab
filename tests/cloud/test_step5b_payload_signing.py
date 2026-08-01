from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pneuma_lab.cloud.authorization_keys import canonical_ledger_digest
from pneuma_lab.cloud.payload_retrieval_plan import payload_retrieval_plan_digest
from pneuma_lab.cloud.preparation_admission import require_preparation_admission
from scripts.research.sign_step5b_payload_admission import build_signed_records


ROOT = Path(__file__).resolve().parents[2]


def test_payload_ceremony_binds_exact_ready_plan_and_cost(tmp_path: Path) -> None:
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw().hex()
    ledger = tmp_path / "ledger.md"
    ledger.write_text("| CL-045 | envelope |\n| CL-046 | admission |\n", encoding="utf-8")
    plan = json.loads((ROOT / "fixtures/cloud/payload-retrieval-plan-ready.json").read_text(encoding="utf-8"))
    envelope, admission = build_signed_records(
        private=private, plan=plan, ledger_path=ledger, projected_cost_usd=3.78,
        granted_timestamp="2026-08-01T10:00:00Z", expires_timestamp="2026-08-08T10:00:00Z",
    )
    registry = {
        "record_kind": "cloud_approver_key_registry", "schema_version": "0.1.0",
        "frozen_timestamp": "2026-08-01T00:00:00Z", "keys": [{
            "key_id": "pneuma-b1-20260801-r1", "approver_id": "jerry-mathos-ai",
            "algorithm": "ed25519", "public_key_hex": public,
            "not_before": "2026-08-01T00:00:00Z", "not_after": "2027-08-01T00:00:00Z",
            "status": "active", "revoked_timestamp": None, "revocation_reason": None,
        }],
    }
    result = require_preparation_admission(
        envelope, admission, key_registry=registry, ledger_path=ledger,
        expected_action_id=plan["action_id"], expected_action_class="input_retrieval",
        expected_provider="aws", expected_region="us-east-1",
        expected_manifest_sha256=payload_retrieval_plan_digest(plan), expected_input_lock_sha256=None,
        expected_projected_cost_usd=3.78, expected_max_retries=1,
        spend_history_sha256=canonical_ledger_digest(ledger),
        clock=lambda: datetime(2026, 8, 1, 10, tzinfo=timezone.utc),
    )
    assert result["manifest_sha256"] == "9334ffebd443dd4aee2a1a566ae5b29479b40a2856afe825a71e0c09ff74606a"
    assert envelope["total_cost_ceiling_usd"] == 5.0
    assert admission["projected_cost_usd"] == 3.78

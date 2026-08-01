from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.cloud.input_lock import REAL_CANDIDATE, classify_input_lock
from pneuma_lab.cloud.inputs import verify_input_lock, verify_input_receipts


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "research" / "neurips-2026-workshop" / "evidence" / "step5b-real-input-lock-20260801"


def test_sealed_step5b_input_lock_is_real_and_self_verifying() -> None:
    lock = json.loads((EVIDENCE / "input-lock.json").read_text(encoding="utf-8"))
    assert classify_input_lock(lock) == REAL_CANDIDATE
    assert verify_input_lock(lock) == "e6746ad843b0da9a6144fa84a5a231dd350b6845a321ffaff171df4540f67b84"
    assert len(verify_input_receipts(lock, EVIDENCE)) == 9


def test_source_licenses_are_bound_to_mirrored_payload_objects() -> None:
    audit = json.loads((EVIDENCE / "receipts" / "source-license-audit.json").read_text(encoding="utf-8"))
    mirror = json.loads((EVIDENCE.parent / "step5b-payload-mirror-receipt-20260801.json").read_text(encoding="utf-8"))
    objects = {item["object_id"]: item for item in mirror["objects"]}
    assert {item["license"] for item in audit["evidence"]} == {"Apache-2.0", "MIT"}
    for item in audit["evidence"]:
        observed = objects[item["evidence_object_id"]]
        assert observed["payload_sha256"] == item["payload_sha256"]
        assert observed["size_bytes"] == item["size_bytes"]

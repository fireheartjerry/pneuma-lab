from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.payload_mirror import object_key
from pneuma_lab.cloud.payload_mirror_receipt import validate_payload_mirror_semantics


ROOT = Path(__file__).resolve().parents[2]


def _records():
    manifest = json.loads((ROOT / "docs/research/neurips-2026-workshop/evidence/step5b-payload-retrieval-manifest-20260801.json").read_text())
    plan = json.loads((ROOT / "fixtures/cloud/payload-retrieval-plan-lifecycle-pending.json").read_text())
    pricing = json.loads((ROOT / "docs/research/neurips-2026-workshop/evidence/step5b-payload-pricing-receipt-20260801.json").read_text())
    objects = []
    for item in manifest["objects"]:
        if not item["retrieval_required"]:
            continue
        objects.append({"object_id": item["object_id"], "consumers": item["consumers"], "key": object_key(plan["destination"]["prefix"], item), "version_id": "v-" + item["object_id"], "etag": item["object_id"], "upstream_identity_algorithm": item["identity_algorithm"], "upstream_identity": item["identity"], "payload_sha256": item["object_id"], "size_bytes": item["size_bytes"]})
    receipt = {"record_kind": "cloud_payload_mirror_receipt", "schema_version": "0.1.0", "generated_timestamp": "2026-08-01T12:00:00Z", "plan_sha256": "a7452d6f99ad7129a8088586553b9240d792885d4ec2cfc201682804cdb4fcf4", "payload_manifest_sha256": plan["payload_manifest_sha256"], "pricing_receipt_sha256": plan["pricing_receipt_sha256"], "identity": {"account_id": "892077329800", "arn": "arn:aws:iam::892077329800:root", "region": "us-east-1"}, "bucket_controls": {"encryption": "AES256", "versioning": "Enabled", "lifecycle_rule_id": "expire-step5b-payloads", "lifecycle_prefix": "runs/step5b/payloads/"}, "request_counts": {"tier1_put": 2772, "tier1_list": 0, "tier2_get": 3416}, "object_count": len(objects), "payload_bytes": sum(item["size_bytes"] for item in objects), "objects": objects}
    return receipt, plan, manifest, pricing


def test_complete_payload_receipt_recomputes_every_binding() -> None:
    receipt, plan, manifest, pricing = _records()
    # Use the current generated plan digest rather than pinning the test helper.
    from pneuma_lab.cloud.payload_retrieval_plan import payload_retrieval_plan_digest

    receipt["plan_sha256"] = payload_retrieval_plan_digest(plan)
    assert validate_payload_mirror_semantics(receipt, plan, manifest, pricing)["object_count"] == 1705


def test_missing_object_and_wrong_payload_total_fail_closed() -> None:
    receipt, plan, manifest, pricing = _records()
    from pneuma_lab.cloud.payload_retrieval_plan import payload_retrieval_plan_digest

    receipt["plan_sha256"] = payload_retrieval_plan_digest(plan)
    receipt["objects"].pop()
    with pytest.raises(CloudManifestError, match="roster"):
        validate_payload_mirror_semantics(receipt, plan, manifest, pricing)
    receipt, plan, manifest, pricing = _records()
    receipt["plan_sha256"] = payload_retrieval_plan_digest(plan)
    receipt["payload_bytes"] += 1
    with pytest.raises(CloudManifestError, match="byte count"):
        validate_payload_mirror_semantics(receipt, plan, manifest, pricing)

"""Build and verify the exact candidate for real Step 5B payload mirroring."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from .authorization_keys import canonical_bytes
from .errors import CloudManifestError
from .manifests import validate_payload_retrieval_plan
from .payload_inventory import payload_manifest_digest, validate_payload_manifest_semantics


ALLOWED_HOSTS = (
    "auth.docker.io",
    "huggingface.co",
    "raw.githubusercontent.com",
    "registry-1.docker.io",
    "s3.us-east-1.amazonaws.com",
)
FORBIDDEN_ACTIONS = (
    "container_execution",
    "ec2_or_batch_provisioning",
    "experiment_execution",
    "gpu_use",
    "model_loading",
    "result_promotion",
)


def payload_retrieval_plan_digest(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(validate_payload_retrieval_plan(record))).hexdigest()


def build_payload_retrieval_plan(
    manifest_record: Mapping[str, Any], *, pricing_receipt_sha256: str | None = None
) -> dict[str, Any]:
    manifest = validate_payload_manifest_semantics(manifest_record)
    manifest_sha256 = payload_manifest_digest(manifest)
    ready = pricing_receipt_sha256 is not None
    record = {
        "record_kind": "cloud_payload_retrieval_plan",
        "schema_version": "0.1.0",
        "status": "ready_for_signature" if ready else "candidate",
        "action_id": "step5b-payload-mirror-001",
        "frozen_timestamp": manifest["frozen_timestamp"],
        "provider": "aws",
        "account_id": "892077329800",
        "region": "us-east-1",
        "payload_manifest_sha256": manifest_sha256,
        "inventory_receipt_sha256": manifest["inventory_receipt_sha256"],
        "retrieval_object_count": manifest["retrieval_object_count"],
        "retrieval_byte_ceiling_bytes": manifest["retrieval_byte_ceiling_bytes"],
        "destination": {
            "bucket": "pneuma-phase-b-892077329800",
            "prefix": f"runs/step5b/payloads/{manifest_sha256}",
            "encryption": "AES256",
            "versioning": "Enabled",
            "content_addressed": True,
        },
        "retention_days": 35,
        "max_retries": 1,
        "cost_ceiling_usd": 5.0,
        "pricing_receipt_sha256": pricing_receipt_sha256,
        "allowed_hosts": list(ALLOWED_HOSTS),
        "forbidden_actions": list(FORBIDDEN_ACTIONS),
    }
    return validate_payload_retrieval_plan_semantics(record, manifest)


def validate_payload_retrieval_plan_semantics(
    record: Mapping[str, Any], manifest_record: Mapping[str, Any]
) -> dict[str, Any]:
    plan = validate_payload_retrieval_plan(record)
    manifest = validate_payload_manifest_semantics(manifest_record)
    manifest_sha256 = payload_manifest_digest(manifest)
    expected = {
        "payload_manifest_sha256": manifest_sha256,
        "inventory_receipt_sha256": manifest["inventory_receipt_sha256"],
        "retrieval_object_count": manifest["retrieval_object_count"],
        "retrieval_byte_ceiling_bytes": manifest["retrieval_byte_ceiling_bytes"],
    }
    for field, value in expected.items():
        if plan[field] != value:
            raise CloudManifestError(f"payload plan {field} does not match the manifest")
    if plan["destination"]["prefix"] != f"runs/step5b/payloads/{manifest_sha256}":
        raise CloudManifestError("payload destination prefix is not content-addressed by the manifest")
    if tuple(plan["allowed_hosts"]) != ALLOWED_HOSTS or tuple(plan["forbidden_actions"]) != FORBIDDEN_ACTIONS:
        raise CloudManifestError("payload plan network or execution boundary is not canonical")
    if (plan["status"] == "ready_for_signature") != (plan["pricing_receipt_sha256"] is not None):
        raise CloudManifestError("only a price-receipted payload plan may be ready for signature")
    return plan

"""Offline semantic verification for an exact payload-mirror receipt."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from .authorization_keys import canonical_bytes
from .errors import CloudManifestError
from .manifests import validate_payload_mirror_receipt
from .payload_inventory import validate_payload_manifest_semantics
from .payload_mirror import object_key
from .payload_pricing import validate_payload_pricing_semantics
from .payload_retrieval_plan import payload_retrieval_plan_digest, validate_payload_retrieval_plan_semantics


def validate_payload_mirror_semantics(
    receipt_record: Mapping[str, Any], plan_record: Mapping[str, Any],
    manifest_record: Mapping[str, Any], pricing_record: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = validate_payload_mirror_receipt(receipt_record)
    manifest = validate_payload_manifest_semantics(manifest_record)
    plan = validate_payload_retrieval_plan_semantics(plan_record, manifest)
    pricing = validate_payload_pricing_semantics(pricing_record, manifest)
    bindings = {
        "plan_sha256": payload_retrieval_plan_digest(plan),
        "payload_manifest_sha256": plan["payload_manifest_sha256"],
        "pricing_receipt_sha256": plan["pricing_receipt_sha256"],
    }
    for field, expected in bindings.items():
        if receipt[field] != expected:
            raise CloudManifestError(f"payload mirror receipt {field} is unbound")
    expected_objects = {item["object_id"]: item for item in manifest["objects"] if item["retrieval_required"]}
    ids = [item["object_id"] for item in receipt["objects"]]
    if ids != sorted(ids) or len(ids) != len(set(ids)) or set(ids) != set(expected_objects):
        raise CloudManifestError("payload mirror receipt object roster is incomplete, duplicated, or unordered")
    for item in receipt["objects"]:
        expected = expected_objects[item["object_id"]]
        exact = {
            "consumers": expected["consumers"],
            "key": object_key(plan["destination"]["prefix"], expected),
            "upstream_identity_algorithm": expected["identity_algorithm"],
            "upstream_identity": expected["identity"],
            "size_bytes": expected["size_bytes"],
        }
        for field, value in exact.items():
            if item[field] != value:
                raise CloudManifestError(f"payload mirror object {item['object_id']} has unbound {field}")
    if receipt["object_count"] != len(receipt["objects"]):
        raise CloudManifestError("payload mirror object count contradicts its roster")
    if receipt["payload_bytes"] != sum(item["size_bytes"] for item in receipt["objects"]):
        raise CloudManifestError("payload mirror byte count contradicts its roster")
    for kind, observed in receipt["request_counts"].items():
        if observed > pricing["request_ceilings"][kind]:
            raise CloudManifestError(f"payload mirror {kind} requests exceed the price-qualified ceiling")
    return receipt


def payload_mirror_receipt_digest(
    receipt_record: Mapping[str, Any], plan_record: Mapping[str, Any],
    manifest_record: Mapping[str, Any], pricing_record: Mapping[str, Any],
) -> str:
    verified = validate_payload_mirror_semantics(receipt_record, plan_record, manifest_record, pricing_record)
    return hashlib.sha256(canonical_bytes(verified)).hexdigest()

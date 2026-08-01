"""Derive a truthful payload manifest from sealed Step 5B metadata."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .authorization_keys import canonical_bytes
from .errors import CloudManifestError
from .inventory_discovery import inventory_plan_digest, validate_inventory_plan
from .manifests import validate_payload_retrieval_manifest


def payload_manifest_digest(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(validate_payload_manifest_semantics(record))).hexdigest()


def _object_id(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require_hex(value: object, length: int, field: str) -> str:
    text = str(value)
    if len(text) != length or any(char not in "0123456789abcdef" for char in text):
        raise CloudManifestError(f"{field} must be {length}-hex")
    return text


def validate_payload_manifest_semantics(record: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute every derived field in a payload manifest."""

    validated = validate_payload_retrieval_manifest(record)
    objects = validated["objects"]
    ids = [item["object_id"] for item in objects]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise CloudManifestError("payload objects must have unique object IDs in canonical order")
    consumers: set[str] = set()
    for item in objects:
        if item["consumers"] != sorted(item["consumers"]):
            raise CloudManifestError("payload object consumers must be canonically ordered")
        consumers.update(item["consumers"])
        core = {key: value for key, value in item.items() if key not in {"object_id", "consumers"}}
        if item["object_id"] != _object_id(core):
            raise CloudManifestError("payload object ID does not match its canonical identity fields")
        expected_length = 40 if item["identity_algorithm"] == "git_sha1" else 64
        _require_hex(item["identity"], expected_length, "payload object identity")
        if item["object_kind"] == "gitlink":
            if item["retrieval_required"] or item["size_bytes"] is not None or "gitlink_target_role" not in item:
                raise CloudManifestError("gitlink must be non-retrievable, sizeless, and roster-resolved")
        elif not item["retrieval_required"] or not isinstance(item["size_bytes"], int) or "gitlink_target_role" in item:
            raise CloudManifestError("payload object retrieval fields contradict its object kind")
    retrieval = [item for item in objects if item["retrieval_required"]]
    checks = {
        "source_count": len(consumers),
        "upstream_entry_count": sum(len(item["consumers"]) for item in objects),
        "unique_object_count": len(objects),
        "retrieval_object_count": len(retrieval),
        "retrieval_byte_ceiling_bytes": sum(item["size_bytes"] for item in retrieval),
    }
    for field, expected in checks.items():
        if validated[field] != expected:
            raise CloudManifestError(f"{field} contradicts the payload object list")
    return validated


def derive_payload_retrieval_manifest(
    plan_record: Mapping[str, Any], inventory_bytes: bytes
) -> dict[str, Any]:
    """Bind every upstream object without claiming its payload was downloaded.

    Git blobs retain Git SHA-1 identities, LFS/OCI objects retain SHA-256, and
    gitlinks are lineage objects rather than fake zero-byte downloads. Repeated
    consumers of one exact object are merged, most importantly the subject
    model and tokenizer roles that share one frozen Hugging Face snapshot.
    """

    plan = validate_inventory_plan(plan_record)
    try:
        inventory = json.loads(inventory_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudManifestError("inventory receipt is not UTF-8 JSON") from exc
    if inventory_bytes != canonical_bytes(inventory) + b"\n":
        raise CloudManifestError("inventory receipt bytes are not canonical JSON plus LF")
    if inventory.get("record_kind") != "step5b_inventory_metadata":
        raise CloudManifestError("unexpected inventory receipt kind")
    plan_sha256 = inventory_plan_digest(plan)
    if inventory.get("plan_sha256") != plan_sha256:
        raise CloudManifestError("inventory receipt is not bound to the supplied plan")

    expected_sources = [
        {key: source[key] for key in ("role", "service", "repository", "revision", "inventory_operation")}
        for source in plan["sources"]
    ]
    observed_sources = [
        {key: source.get(key) for key in ("role", "service", "repository", "revision", "inventory_operation")}
        for source in inventory.get("sources", [])
    ]
    if observed_sources != expected_sources:
        raise CloudManifestError("inventory sources do not exactly match the frozen plan order")

    source_by_revision = {source["revision"]: source["role"] for source in plan["sources"]}
    merged: dict[tuple[str, str, str, str | None, str], dict[str, Any]] = {}
    upstream_count = 0
    for source in inventory["sources"]:
        seen_paths: set[str] = set()
        for item in source.get("items", []):
            upstream_count += 1
            if source["service"] == "docker_registry":
                digest = str(item.get("digest", ""))
                identity = _require_hex(digest.removeprefix("sha256:"), 64, "OCI identity")
                kind = str(item.get("role"))
                if kind not in {"config", "layer"}:
                    raise CloudManifestError("OCI inventory item has an unknown role")
                path = None
                size = item.get("size")
                algorithm = "sha256"
            else:
                path = str(item.get("path", ""))
                if not path or path in seen_paths:
                    raise CloudManifestError(f"inventory paths must be nonempty and unique within {source['role']}")
                seen_paths.add(path)
                kind = "gitlink" if item.get("type") == "commit" else str(item.get("type", "file"))
                if kind not in {"file", "blob", "gitlink"}:
                    raise CloudManifestError("inventory item has an unknown object type")
                algorithm = str(item.get("identity_algorithm"))
                identity = _require_hex(item.get("identity"), 40 if algorithm == "git_sha1" else 64, "object identity")
                size = item.get("size_bytes")
            retrieval_required = kind != "gitlink"
            if retrieval_required and (not isinstance(size, int) or isinstance(size, bool) or size < 0):
                raise CloudManifestError("retrievable inventory object requires a nonnegative authenticated size")
            if not retrieval_required and size is not None:
                raise CloudManifestError("gitlink size must be null")

            identity_core = {
                "service": source["service"], "repository": source["repository"],
                "revision": source["revision"], "path": path, "object_kind": kind,
                "identity_algorithm": algorithm, "identity": identity,
                "size_bytes": size, "retrieval_required": retrieval_required,
            }
            if kind == "gitlink":
                target_role = source_by_revision.get(identity)
                if target_role is None:
                    raise CloudManifestError("gitlink target is absent from the frozen source roster")
                identity_core["gitlink_target_role"] = target_role
            key = (source["service"], source["repository"], source["revision"], path, identity)
            existing = merged.get(key)
            if existing is None:
                merged[key] = {"object_id": _object_id(identity_core), "consumers": [source["role"]], **identity_core}
            else:
                if {k: existing[k] for k in identity_core} != identity_core:
                    raise CloudManifestError("duplicate object locator carries conflicting metadata")
                existing["consumers"].append(source["role"])

    objects = sorted(merged.values(), key=lambda item: item["object_id"])
    for item in objects:
        item["consumers"].sort()
    retrieval = [item for item in objects if item["retrieval_required"]]
    record = {
        "record_kind": "cloud_payload_retrieval_manifest",
        "schema_version": "0.1.0",
        "frozen_timestamp": inventory["generated_timestamp"],
        "plan_sha256": plan_sha256,
        "inventory_receipt_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
        "source_count": len(inventory["sources"]),
        "upstream_entry_count": upstream_count,
        "unique_object_count": len(objects),
        "retrieval_object_count": len(retrieval),
        "retrieval_byte_ceiling_bytes": sum(item["size_bytes"] for item in retrieval),
        "objects": objects,
    }
    return validate_payload_manifest_semantics(record)

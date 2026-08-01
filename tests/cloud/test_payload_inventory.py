from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.payload_inventory import (
    derive_payload_retrieval_manifest,
    payload_manifest_digest,
    validate_payload_manifest_semantics,
)


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "fixtures/cloud/input-inventory-plan-candidate.json"
INVENTORY = ROOT / "docs/research/neurips-2026-workshop/evidence/step5b-inventory-metadata-20260801.json"


def _derive() -> dict:
    return derive_payload_retrieval_manifest(json.loads(PLAN.read_text(encoding="utf-8")), INVENTORY.read_bytes())


def test_real_inventory_derives_a_deduplicated_truthful_payload_manifest() -> None:
    record = _derive()
    assert record["source_count"] == 8
    assert record["upstream_entry_count"] == 1762
    assert record["unique_object_count"] < record["upstream_entry_count"]
    assert record["retrieval_object_count"] == record["unique_object_count"] - 1
    assert len(payload_manifest_digest(record)) == 64
    shared = [item for item in record["objects"] if item["consumers"] == ["subject_model", "tokenizer"]]
    assert len(shared) == 56
    gitlinks = [item for item in record["objects"] if item["object_kind"] == "gitlink"]
    assert len(gitlinks) == 1
    assert gitlinks[0]["retrieval_required"] is False
    assert gitlinks[0]["gitlink_target_role"] == "repo_launcher"


def test_inventory_receipt_bytes_must_remain_canonical() -> None:
    with pytest.raises(CloudManifestError, match="canonical JSON plus LF"):
        derive_payload_retrieval_manifest(json.loads(PLAN.read_text()), INVENTORY.read_bytes().replace(b"\n", b"\r\n"))


def test_unrostered_gitlink_fails_closed() -> None:
    inventory = json.loads(INVENTORY.read_text())
    link = next(item for source in inventory["sources"] for item in source["items"] if item.get("type") == "commit")
    link["identity"] = "0" * 40
    from pneuma_lab.cloud.authorization_keys import canonical_bytes

    with pytest.raises(CloudManifestError, match="gitlink target"):
        derive_payload_retrieval_manifest(json.loads(PLAN.read_text()), canonical_bytes(inventory) + b"\n")


@pytest.mark.parametrize("field", ["source_count", "upstream_entry_count", "unique_object_count", "retrieval_object_count", "retrieval_byte_ceiling_bytes"])
def test_derived_totals_cannot_be_asserted(field: str) -> None:
    record = _derive()
    record[field] += 1
    with pytest.raises(CloudManifestError, match=field):
        validate_payload_manifest_semantics(record)


def test_object_identity_and_order_are_recomputed() -> None:
    record = _derive()
    identity = record["objects"][0]["identity"]
    record["objects"][0]["identity"] = identity[:-1] + ("0" if identity[-1] != "0" else "1")
    with pytest.raises(CloudManifestError, match="object ID"):
        validate_payload_manifest_semantics(record)
    record = _derive()
    record["objects"].reverse()
    with pytest.raises(CloudManifestError, match="canonical order"):
        validate_payload_manifest_semantics(record)

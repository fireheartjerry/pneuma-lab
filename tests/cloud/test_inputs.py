from __future__ import annotations

import copy
import hashlib

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.inputs import build_retrieval_plan, verify_input_lock, verify_input_receipts


_HEX = "a" * 64
_REV = "b" * 40


def input_lock() -> dict:
    receipt = {"relative_path": "receipts/source.json", "sha256": _HEX}
    pin = {"repository": "org/model", "revision": _REV, "license": "Apache-2.0", "snapshot_receipt": receipt}
    benchmark = {**pin, "repository": "org/benchmark", "dataset_revision": "c" * 40, "task_manifest_sha256": "d" * 64}
    return {
        "record_kind": "cloud_input_lock", "schema_version": "0.1.0", "frozen_timestamp": "2026-07-31T00:00:00Z",
        "provenance": {"design_sha256": _HEX, "code_sha256": _HEX}, "model_pins": [pin], "tokenizer_pin": {**pin, "repository": "org/tokenizer"},
        "benchmark_pins": [benchmark], "container_bases": [{"repository": "registry.example/base", "digest": "linux/amd64@sha256:" + _HEX}],
        "verifier_sources": [{**pin, "repository": "org/verifier"}], "contamination_receipts": [receipt], "license_receipts": [receipt],
    }


def test_fixture_lock_is_digest_stable_and_network_free() -> None:
    record = input_lock()
    assert verify_input_lock(record) == verify_input_lock(copy.deepcopy(record))
    assert build_retrieval_plan(record) == (
        {"kind": "model", "repository": "org/model", "revision": _REV},
        {"kind": "tokenizer", "repository": "org/tokenizer", "revision": _REV},
        {"kind": "benchmark", "repository": "org/benchmark", "revision": _REV},
        {"kind": "dataset", "repository": "org/benchmark", "revision": "c" * 40},
        {"kind": "verifier", "repository": "org/verifier", "revision": _REV},
        {"kind": "container", "repository": "registry.example/base", "digest": "linux/amd64@sha256:" + _HEX},
    )


@pytest.mark.parametrize("field,value", [("revision", "main"), ("revision", "latest"), ("license", "")])
def test_mutable_or_incomplete_input_fails_closed(field: str, value: str) -> None:
    record = input_lock()
    record["model_pins"][0][field] = value
    with pytest.raises(CloudManifestError):
        verify_input_lock(record)


def test_mutable_container_tag_and_digest_mismatch_fail_closed() -> None:
    record = input_lock()
    record["container_bases"][0]["digest"] = "latest"
    with pytest.raises(CloudManifestError):
        build_retrieval_plan(record)


def test_every_referenced_receipt_is_hash_verified(tmp_path) -> None:
    record = input_lock()
    payload = b"receipt bytes\n"
    receipt_path = tmp_path / "receipts" / "source.json"
    receipt_path.parent.mkdir()
    receipt_path.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()
    for pin in record["model_pins"] + [record["tokenizer_pin"]] + record["benchmark_pins"] + record["verifier_sources"]:
        pin["snapshot_receipt"]["sha256"] = expected
    for item in record["contamination_receipts"] + record["license_receipts"]:
        item["sha256"] = expected
    assert verify_input_receipts(record, tmp_path) == ("receipts/source.json",)
    receipt_path.write_bytes(b"changed\n")
    with pytest.raises(CloudManifestError, match="digest mismatch"):
        verify_input_receipts(record, tmp_path)

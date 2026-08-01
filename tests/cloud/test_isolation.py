from __future__ import annotations

import copy
import hashlib

import pytest

from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.isolation import (
    isolation_receipt_digest,
    require_isolation_receipt,
    validate_isolation_receipt,
)


HEX = "a" * 64
SPLITS = {"swe": ("c", "cpp", "cs", "go", "java", "js", "rust", "ts"), "tau2": ("airline", "telecom", "banking")}


def receipt() -> dict:
    pairs = []
    for family, splits in SPLITS.items():
        for split in splits:
            for index in range(3):
                pairs.append({
                    "pair_id": f"{family}-{split}-{index}", "family": family, "split": split,
                    "unit_id": f"{family}-{split}-unit-{index}",
                    "image_reference": f"registry/{family}@sha256:{HEX}", "image_digest": f"sha256:{HEX}",
                    "container_a_id": "a" * 64, "container_b_id": "b" * 64,
                    "assertions": {name: True for name in (
                        "immutable_image_digest", "linux_amd64", "network_none", "capabilities_dropped",
                        "no_new_privileges", "fresh_pair_clean", "a_marker_absent_from_b",
                        "b_marker_absent_from_a", "recreated_a_clean")},
                })
    return {
        "record_kind": "cloud_isolation_qualification_receipt", "schema_version": "0.1.0",
        "frozen_timestamp": "2026-08-01T15:00:00Z", "tier": "C120", "input_lock_sha256": HEX,
        "case_manifest": {"sha256": "b" * 64, "input_lock_sha256": HEX},
        "host": {"os": "linux", "architecture": "x86_64", "docker_version": "29.1.3", "instance_id": "i-test"},
        "pairs": pairs, "qualification_only": True,
    }


def test_complete_receipt_is_canonical_and_accepted() -> None:
    record = receipt()
    assert validate_isolation_receipt(record) == record
    assert isolation_receipt_digest(record) == hashlib.sha256(canonical_bytes(record)).hexdigest()
    assert require_isolation_receipt(
        record, expected_case_manifest_sha256="b" * 64, expected_input_lock_sha256=HEX
    ) == record


def test_valid_but_wrong_ancestry_rejects() -> None:
    with pytest.raises(CloudManifestError, match="frozen case manifest"):
        require_isolation_receipt(
            receipt(), expected_case_manifest_sha256="c" * 64, expected_input_lock_sha256=HEX
        )


@pytest.mark.parametrize("failure", ["network_none", "a_marker_absent_from_b", "recreated_a_clean"])
def test_any_failed_observation_rejects(failure: str) -> None:
    record = receipt()
    record["pairs"][0]["assertions"][failure] = False
    with pytest.raises(CloudManifestError, match="failed"):
        validate_isolation_receipt(record)


def test_duplicate_units_do_not_count_as_independent_pairs() -> None:
    record = receipt()
    record["pairs"][1]["unit_id"] = record["pairs"][0]["unit_id"]
    with pytest.raises(CloudManifestError, match="distinct units"):
        validate_isolation_receipt(record)


def test_missing_split_cannot_be_replaced_by_an_extra_pair() -> None:
    record = receipt()
    replacement = copy.deepcopy(record["pairs"][0])
    replacement["pair_id"] = "extra"
    record["pairs"][-1] = replacement
    with pytest.raises(CloudManifestError, match="coverage mismatch|exactly three"):
        validate_isolation_receipt(record)

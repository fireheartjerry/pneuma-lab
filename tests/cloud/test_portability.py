from __future__ import annotations

import copy
import json

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.portability import build_portability_bundle, verify_portability_bundle

from .test_inputs import input_lock


def _audit(family: str) -> dict:
    return {
        "record_kind": "cloud_qualification_audit",
        "schema_version": "0.2.0",
        "frozen_timestamp": "2026-07-31T00:00:00Z",
        "provenance": {"design_sha256": "a" * 64, "code_sha256": "b" * 64},
        "benchmark_family": family,
        "tier": "C120",
        "evidence_class": "proxy_metadata" if family == "swe" else "audited_qualified",
        "proxy_basis": "current_repository_metadata" if family == "swe" else "pinned_objective_pool",
        "input_lock_sha256": None if family == "swe" else "c" * 64,
        "splits": [{
            "split": "C" if family == "swe" else "airline",
            "proxy_units": 20,
            "eligible_units": 0,
            "confirmation_quota": 1,
            "pilot_units": 1,
            "fixed_reserve": 0,
            "hamilton_allocation": None,
            "registered_minimum_units": None,
            "three_pair_audit": {"pairs_attempted": 0, "pairs_independent_pass": 0},
            "isolation_evidence": None,
            "license_evidence": None,
        }],
    }


def test_bundle_is_byte_identical_and_verifies_offline(tmp_path) -> None:
    receipts = {"linux/gpu.json": b'{"qualified":true}\n', "shared/source.txt": b"a\r\nb\r\n"}
    records = [_audit("tau2"), _audit("swe")]
    first = build_portability_bundle(
        frozen_timestamp="2026-07-31T00:00:00Z", input_lock=input_lock(),
        roster_records=records, receipt_payloads=receipts,
    )
    second = build_portability_bundle(
        frozen_timestamp="2026-07-31T00:00:00Z", input_lock=copy.deepcopy(input_lock()),
        roster_records=list(reversed(copy.deepcopy(records))), receipt_payloads=dict(reversed(receipts.items())),
    )
    assert first == second
    for relative, payload in receipts.items():
        path = tmp_path.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    assert verify_portability_bundle(first, input_lock=input_lock(), roster_records=records, receipt_root=tmp_path) == __import__("hashlib").sha256(first).hexdigest()


def test_bundle_rejects_platform_and_byte_drift(tmp_path) -> None:
    records = [_audit("swe"), _audit("tau2")]
    with pytest.raises(CloudManifestError, match="POSIX"):
        build_portability_bundle(
            frozen_timestamp="2026-07-31T00:00:00Z", input_lock=input_lock(),
            roster_records=records, receipt_payloads={"linux\\gpu.json": b"x"},
        )
    payload = b"line1\nline2\n"
    bundle = build_portability_bundle(
        frozen_timestamp="2026-07-31T00:00:00Z", input_lock=input_lock(),
        roster_records=records, receipt_payloads={"shared/receipt.txt": payload},
    )
    path = tmp_path / "shared" / "receipt.txt"
    path.parent.mkdir()
    path.write_bytes(payload.replace(b"\n", b"\r\n"))
    with pytest.raises(CloudManifestError, match="bytes mismatch"):
        verify_portability_bundle(bundle, input_lock=input_lock(), roster_records=records, receipt_root=tmp_path)
    noncanonical = json.dumps(json.loads(bundle), indent=2).encode("utf-8") + b"\n"
    with pytest.raises(CloudManifestError, match="canonical JSON"):
        verify_portability_bundle(noncanonical, input_lock=input_lock(), roster_records=records, receipt_root=tmp_path)
    duplicate = bundle.replace(b'{"frozen_timestamp":', b'{"record_kind":"duplicate","frozen_timestamp":', 1)
    with pytest.raises(CloudManifestError, match="UTF-8 JSON"):
        verify_portability_bundle(duplicate, input_lock=input_lock(), roster_records=records, receipt_root=tmp_path)

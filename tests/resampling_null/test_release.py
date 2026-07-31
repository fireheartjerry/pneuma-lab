"""Focused Task-10 release-preparation checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


def _sealed_fixture(
    root: Path, *, authority: str, decision: str, kind: str = "completed_chain",
    reason: str | None = None,
) -> tuple[Path, Path]:
    receipt = root / "p0-core-receipt.json"
    power = root / "power-final.json"
    power.write_text(json.dumps({"payload": {
        "stage": "final", "decision_authority": authority,
        "finalization": {"kind": kind, "decision": decision, **({"reason": reason} if reason else {})},
    }}), encoding="utf-8")
    receipt.write_text(json.dumps({
        "study_id": "fixture-study",
        "payload": {"root_sha256": "a" * 64, "entries": [{
            "document_kind": "resampling_power_report", "relative_path": "power-final.json",
        }]},
    }), encoding="utf-8")
    return receipt, power


def test_release_inspection_keeps_implementation_authority_out_of_scientific_claims(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pneuma_lab.resampling_null import release

    receipt, _power = _sealed_fixture(
        tmp_path, authority="implementation_verification", decision="IMPLEMENTATION_VERIFICATION_ONLY",
    )
    monkeypatch.setattr(release, "verify_artifact_root", lambda *args, **kwargs: None)
    monkeypatch.setattr(release, "verify_release_bytes_independently", lambda *args, **kwargs: None)

    descriptor = release.inspect_sealed_release(tmp_path, receipt, required_document_kinds=[])

    assert descriptor["classification"] == "implementation_fixture"
    assert descriptor["claim_boundary"] == "not_a_scientific_result"
    assert descriptor["failure_classification"] is None
    assert descriptor["receipt_sha256"] == hashlib.sha256(receipt.read_bytes()).hexdigest()


def test_release_inspection_rejects_nonresult_authority_with_promoted_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pneuma_lab.resampling_null import release
    from pneuma_lab.resampling_null.errors import RecordValidationError

    receipt, _power = _sealed_fixture(tmp_path, authority="synthetic_validation", decision="GO")
    monkeypatch.setattr(release, "verify_artifact_root", lambda *args, **kwargs: None)
    monkeypatch.setattr(release, "verify_release_bytes_independently", lambda *args, **kwargs: None)

    with pytest.raises(RecordValidationError, match="invalid terminal decision"):
        release.inspect_sealed_release(tmp_path, receipt, required_document_kinds=[])


def test_release_inspection_classifies_a_registered_canonical_no_go_without_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pneuma_lab.resampling_null import release

    receipt, _power = _sealed_fixture(
        tmp_path, authority="roster_bound_selection", decision="NO_GO",
        kind="feasibility_no_go", reason="runtime_bound_exceeded",
    )
    monkeypatch.setattr(release, "verify_artifact_root", lambda *args, **kwargs: None)
    monkeypatch.setattr(release, "verify_release_bytes_independently", lambda *args, **kwargs: None)

    descriptor = release.inspect_sealed_release(tmp_path, receipt, required_document_kinds=[])

    assert descriptor["classification"] == "registered_no_go"
    assert descriptor["failure_classification"] == "runtime_bound_exceeded"
    assert descriptor["claim_boundary"] == "requires_step4b_release_authorization"


def test_independent_release_byte_verifier_rejects_tampered_entry(tmp_path: Path) -> None:
    from pneuma_lab.foundation.artifacts import canonical_json_bytes
    from pneuma_lab.resampling_null.errors import RecordValidationError
    from pneuma_lab.resampling_null.release import verify_release_bytes_independently

    artifact = tmp_path / "artifact.json"
    artifact.write_bytes(b'{"immutable":true}')
    entry = {
        "relative_path": "artifact.json", "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "byte_count": artifact.stat().st_size, "entry_kind": "referenced_blob",
        "document_kind": None, "role": "fixture", "media_type": "application/json",
    }
    receipt = tmp_path / "p0-core-receipt.json"
    receipt.write_bytes(canonical_json_bytes({
        "record_kind": "resampling_artifact_root", "payload": {
            "entries": [entry], "root_sha256": hashlib.sha256(canonical_json_bytes([entry], indent=None)).hexdigest(),
        },
    }, indent=None))
    verify_release_bytes_independently(tmp_path, receipt)
    artifact.write_bytes(b'{"immutable":false}')
    with pytest.raises(RecordValidationError, match="bytes differ"):
        verify_release_bytes_independently(tmp_path, receipt)


def test_external_release_package_is_content_addressed_and_never_replaces_a_file(tmp_path: Path) -> None:
    from pneuma_lab.resampling_null.release import write_external_release_package

    descriptor = {
        "contract_id": "resampling-null-task10-release-v1",
        "receipt_sha256": "a" * 64,
        "root_sha256": "b" * 64,
        "study_id": "fixture-study",
        "decision_authority": "implementation_verification",
        "terminal_decision": "IMPLEMENTATION_VERIFICATION_ONLY",
        "classification": "implementation_fixture",
        "claim_boundary": "not_a_scientific_result",
        "failure_classification": None,
    }
    output = tmp_path / "package" / "release.json"
    digest = write_external_release_package(descriptor, output=output)
    assert digest == hashlib.sha256(output.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        write_external_release_package(descriptor, output=output)

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.inputs import verify_input_lock
from pneuma_lab.cloud.retrieval import (
    authorization_binding_digest,
    build_audit_plan,
    build_receipt_verification_plan,
    missing_scopes,
    require_authorized,
    require_complete_scopes,
    retrieve_and_verify,
    validate_retrieval_authorization,
    verify_local_bytes,
    verify_mirrored_file,
)

from .test_inputs import _HEX, input_lock


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures" / "cloud"


def candidate() -> dict:
    return json.loads((FIXTURES / "retrieval-authorization-candidate.json").read_text())


def sign(record: dict, *, approver: str = "principal-investigator") -> dict:
    """Attach a correctly bound human authorization, as a signer would."""

    record["status"] = "authorized"
    record["ledger_row_id"] = "CL-026"
    record["human_authorization"] = {"approver_id": approver, "granted_timestamp": "2026-07-31T00:00:00Z", "signature_sha256": "0" * 64}
    record["human_authorization"]["signature_sha256"] = authorization_binding_digest(record)
    return record


def authorized() -> dict:
    return sign(candidate())


def test_committed_candidate_is_valid_and_authorizes_nothing() -> None:
    record = validate_retrieval_authorization(candidate())
    assert record["provenance"] == {
        "design_sha256": hashlib.sha256((REPO_ROOT / "docs/research/neurips-2026-workshop/38-experiment-design-freeze.md").read_bytes()).hexdigest(),
        "code_sha256": hashlib.sha256((REPO_ROOT / "src/pneuma_lab/cloud/retrieval.py").read_bytes()).hexdigest(),
    }
    assert record["status"] == "candidate"
    assert record["ledger_row_id"] is None and record["human_authorization"] is None
    with pytest.raises(CloudManifestError):
        require_authorized(record, input_lock())


def test_committed_candidate_is_bound_to_the_fixture_lock_not_a_real_one() -> None:
    """The candidate demonstrates shape; its lock is explicitly synthetic."""

    fixture_lock = json.loads((FIXTURES / "input-lock-fixture.json").read_text())
    assert candidate()["input_lock_sha256"] == verify_input_lock(fixture_lock)
    assert fixture_lock["model_pins"][0]["repository"] == "org/model"


@pytest.mark.parametrize("field,value", [("ledger_row_id", "CL-026"), ("human_authorization", {"approver_id": "x", "granted_timestamp": "2026-07-31T00:00:00Z", "signature_sha256": _HEX})])
def test_partially_signed_candidate_fails_closed(field: str, value: object) -> None:
    record = candidate()
    record[field] = value
    with pytest.raises(CloudManifestError):
        validate_retrieval_authorization(record)


def test_free_text_signature_is_refused() -> None:
    record = candidate()
    record["status"] = "authorized"
    record["ledger_row_id"] = "CL-999"
    record["human_authorization"] = {"approver_id": "anyone", "granted_timestamp": "2026-07-31T00:00:00Z", "signature_sha256": "f" * 64}
    with pytest.raises(CloudManifestError):
        validate_retrieval_authorization(record)


@pytest.mark.parametrize("field,value", [("scopes", ["model"]), ("byte_ceiling_bytes", 1), ("input_lock_sha256", "c" * 64)])
def test_signature_does_not_survive_a_record_edit(field: str, value: object) -> None:
    record = authorized()
    record[field] = value
    with pytest.raises(CloudManifestError):
        validate_retrieval_authorization(record)


def test_signature_cannot_be_lifted_from_another_record() -> None:
    donor = authorized()
    record = candidate()
    record["status"] = "authorized"
    record["ledger_row_id"] = "CL-026"
    record["byte_ceiling_bytes"] = donor["byte_ceiling_bytes"] * 2
    record["human_authorization"] = copy.deepcopy(donor["human_authorization"])
    with pytest.raises(CloudManifestError):
        validate_retrieval_authorization(record)


def test_authorized_record_must_bind_the_exact_lock_digest() -> None:
    record = authorized()
    assert require_authorized(record, input_lock())["status"] == "authorized"
    other = copy.deepcopy(input_lock())
    other["model_pins"][0]["repository"] = "org/other-model"
    with pytest.raises(CloudManifestError):
        require_authorized(record, other)


def test_plan_covers_every_retrievable_scope_including_the_verifier() -> None:
    plan = build_audit_plan(input_lock(), candidate())
    assert [step["kind"] for step in plan] == ["model", "tokenizer", "benchmark", "benchmark_dataset", "verifier", "container"]
    assert all(step["expected_sha256"] in {_HEX, "d" * 64} for step in plan)
    assert plan[-1]["reference"] == "linux/amd64@sha256:" + _HEX
    assert all(step["mirror_path"].startswith("mirror/step5b/") for step in plan)

    narrowed = candidate()
    narrowed["scopes"] = ["container_base"]
    assert [step["kind"] for step in build_audit_plan(input_lock(), narrowed)] == ["container"]


def test_plan_covers_the_pinned_dataset_revision_and_task_manifest() -> None:
    """The bytes the roster counts derive from must not be silently skipped."""

    plan = build_audit_plan(input_lock(), candidate())
    dataset = next(step for step in plan if step["kind"] == "benchmark_dataset")
    assert dataset["reference"] == input_lock()["benchmark_pins"][0]["dataset_revision"]
    assert dataset["expected_sha256"] == input_lock()["benchmark_pins"][0]["task_manifest_sha256"]


def test_incomplete_scopes_are_reported_and_refused() -> None:
    assert missing_scopes(input_lock(), candidate()) == ()
    assert require_complete_scopes(input_lock(), candidate())["status"] == "candidate"

    narrowed = candidate()
    narrowed["scopes"] = ["model"]
    assert missing_scopes(input_lock(), narrowed) == ("benchmark", "container_base", "contamination", "license", "tokenizer", "verifier")
    with pytest.raises(CloudManifestError):
        require_complete_scopes(input_lock(), narrowed)


def test_plan_mirror_paths_never_collide() -> None:
    plan = build_audit_plan(input_lock(), candidate())
    paths = [step["mirror_path"] for step in plan]
    assert len(set(paths)) == len(paths)
    receipts = build_receipt_verification_plan(input_lock(), candidate())
    combined = paths + [step["mirror_path"] for step in receipts]
    assert len(set(combined)) == len(combined)


def test_receipt_plan_covers_license_and_contamination_and_binds_the_lock() -> None:
    steps = build_receipt_verification_plan(input_lock(), candidate())
    assert [step["kind"] for step in steps] == ["license", "contamination"]

    unbound = candidate()
    unbound["input_lock_sha256"] = "0" * 64
    with pytest.raises(CloudManifestError):
        build_receipt_verification_plan(input_lock(), unbound)


def test_retrieval_refuses_without_fresh_authorization() -> None:
    def fetcher(step: dict) -> bytes:
        raise AssertionError("fetcher must not run without authorization")

    with pytest.raises(CloudManifestError):
        retrieve_and_verify(input_lock(), candidate(), fetcher)


def _payload_bound_lock(payload: bytes) -> tuple[dict, dict]:
    """Return a lock whose receipts match `payload`, plus an authorization for it."""

    digest = hashlib.sha256(payload).hexdigest()
    raw = json.dumps(input_lock()).replace(_HEX, digest).replace("d" * 64, digest)
    lock = json.loads(raw)
    lock["container_bases"][0]["digest"] = "linux/amd64@sha256:" + digest
    record = candidate()
    record["input_lock_sha256"] = verify_input_lock(lock)
    return lock, sign(record)


def test_authorized_retrieval_verifies_every_artifact_and_fails_on_a_swap() -> None:
    payload = b"pinned-bytes"
    lock, record = _payload_bound_lock(payload)
    receipts = retrieve_and_verify(lock, record, lambda step: payload)
    assert [item["kind"] for item in receipts] == ["model", "tokenizer", "benchmark", "benchmark_dataset", "verifier", "container"]
    assert {item["sha256"] for item in receipts} == {hashlib.sha256(payload).hexdigest()}

    with pytest.raises(CloudManifestError):
        retrieve_and_verify(lock, record, lambda step: b"substituted-bytes")


def test_declared_size_over_ceiling_is_refused_before_any_fetch() -> None:
    payload = b"pinned-bytes"
    lock, record = _payload_bound_lock(payload)
    record["byte_ceiling_bytes"] = 10
    record = sign(record)
    calls: list[str] = []

    def fetcher(step: dict) -> bytes:
        calls.append(step["kind"])
        return payload

    with pytest.raises(CloudManifestError):
        retrieve_and_verify(lock, record, fetcher, declared_sizes={hashlib.sha256(payload).hexdigest(): 1_000_000})
    assert calls == []


def test_post_fetch_ceiling_backstops_an_undeclared_overrun() -> None:
    record = authorized()
    record["byte_ceiling_bytes"] = 1
    record = sign(record)
    calls: list[str] = []

    def fetcher(step: dict) -> bytes:
        calls.append(step["kind"])
        return b"xx"

    with pytest.raises(CloudManifestError):
        retrieve_and_verify(input_lock(), record, fetcher)
    assert calls == ["model"]


def test_local_byte_verification_fails_closed(tmp_path: Path) -> None:
    payload = b"pinned-bytes"
    digest = hashlib.sha256(payload).hexdigest()
    assert verify_local_bytes(payload, digest) == digest
    with pytest.raises(CloudManifestError):
        verify_local_bytes(payload, _HEX)

    path = tmp_path / "artifact.bin"
    path.write_bytes(payload)
    assert verify_mirrored_file(path, digest) == digest
    with pytest.raises(CloudManifestError):
        verify_mirrored_file(tmp_path / "absent.bin", digest)

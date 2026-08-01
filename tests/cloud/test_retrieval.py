from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.provenance import canonical_text_digest
from pneuma_lab.cloud.inputs import verify_input_lock
from pneuma_lab.cloud.retrieval import (
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
    return json.loads((FIXTURES / "retrieval-authorization-candidate.json").read_text(encoding="utf-8"))


def test_committed_candidate_is_valid_and_authorizes_nothing() -> None:
    record = validate_retrieval_authorization(candidate())
    assert record["provenance"] == {
        "design_sha256": canonical_text_digest(REPO_ROOT / "docs/research/neurips-2026-workshop/38-experiment-design-freeze.md"),
        "code_sha256": canonical_text_digest(REPO_ROOT / "src/pneuma_lab/cloud/retrieval.py"),
    }
    assert record["status"] == "candidate"
    assert record["ledger_row_id"] is None and record["human_authorization"] is None
    with pytest.raises(CloudManifestError):
        require_authorized(
            record,
            input_lock(),
            key_registry={},
            ledger_path=REPO_ROOT / "docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md",
        )


def test_committed_candidate_is_bound_to_the_fixture_lock_not_a_real_one() -> None:
    """The candidate demonstrates shape; its lock is explicitly synthetic."""

    fixture_lock = json.loads((FIXTURES / "input-lock-fixture.json").read_text(encoding="utf-8"))
    assert candidate()["input_lock_sha256"] == verify_input_lock(fixture_lock)
    assert fixture_lock["model_pins"][0]["repository"] == "org/model"


@pytest.mark.parametrize("field,value", [
    ("ledger_row_id", "CL-026"),
    ("ledger_row_sha256", _HEX),
    ("human_authorization", {
        "approver_id": "x", "key_id": "x-key", "granted_timestamp": "2026-07-31T00:00:00Z",
        "expires_timestamp": "2026-08-01T00:00:00Z", "body_sha256": _HEX,
        "signature_ed25519": "a" * 128,
    }),
])
def test_partially_signed_candidate_fails_closed(field: str, value: object) -> None:
    record = candidate()
    record[field] = value
    with pytest.raises(CloudManifestError):
        validate_retrieval_authorization(record)


def test_plan_covers_every_retrievable_scope_including_the_verifier() -> None:
    plan = build_audit_plan(input_lock(), candidate())
    assert [step["kind"] for step in plan] == ["model", "tokenizer", "benchmark", "benchmark_dataset", "verifier", "container"]
    assert all(step["expected_sha256"] in {_HEX, "d" * 64} for step in plan)
    # Every step carries an authenticated size, so the ceiling can be enforced
    # before and during transfer rather than after it.
    assert all(step["expected_size_bytes"] == 1024 for step in plan)
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


def test_retrieval_refuses_without_fresh_authorization(tmp_path: Path) -> None:
    def fetcher(step):
        raise AssertionError("fetcher must not run without authorization")
        yield b""  # pragma: no cover - generator marker

    with pytest.raises(CloudManifestError):
        retrieve_and_verify(
            input_lock(),
            candidate(),
            fetcher,
            key_registry={},
            ledger_path=REPO_ROOT / "docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md",
            mirror_root=tmp_path / "mirror",
        )
    # Nothing was created for an unauthorized attempt.
    assert not (tmp_path / "mirror").exists() or not any((tmp_path / "mirror").rglob("*"))


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

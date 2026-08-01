from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from pneuma_lab.cloud.authorization_keys import canonical_bytes, signed_body
from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.inputs import verify_input_lock
from pneuma_lab.cloud.preparation import (
    require_preparation_admission,
    require_signed_preparation_admission,
)


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md"
FIXTURES = ROOT / "fixtures" / "cloud"
NOW = "2026-08-01T00:00:00Z"


def _private() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(b"\x03" * 32)


def _registry(private: Ed25519PrivateKey) -> dict:
    return {"record_kind": "cloud_approver_key_registry", "schema_version": "0.1.0", "frozen_timestamp": "2026-07-31T00:00:00Z", "keys": [{"key_id": "prep-key", "approver_id": "jerry", "algorithm": "ed25519", "public_key_hex": private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), "not_before": "2026-01-01T00:00:00Z", "not_after": "2027-01-01T00:00:00Z", "status": "active", "revoked_timestamp": None, "revocation_reason": None}]}


def _record(private: Ed25519PrivateKey) -> dict:
    row = next(line for line in LEDGER.read_text().splitlines() if line.startswith("| CL-026 |"))
    record = {"record_kind": "cloud_preparation_authorization", "schema_version": "0.1.0", "frozen_timestamp": "2026-07-31T00:00:00Z", "status": "authorized", "provider": "aws", "window_start": "2026-07-31T00:00:00Z", "window_end": "2026-08-30T00:00:00Z", "rolling_ceiling_usd": 250.0, "per_job_ceiling_usd": {"retrieval_or_image_build": 75.0, "smoke_or_bounded_api_pilot": 25.0}, "max_retries_per_job": 2, "allowed_actions": ["immutable_input_retrieval", "licence_contamination_audit", "container_build", "storage", "non_scientific_smoke", "bounded_api_pilot"], "ledger_row_id": "CL-026", "ledger_row_sha256": hashlib.sha256(row.encode()).hexdigest(), "human_authorization": {"approver_id": "jerry", "key_id": "prep-key", "granted_timestamp": "2026-07-31T00:00:00Z", "expires_timestamp": "2026-08-30T00:00:00Z", "body_sha256": "0" * 64, "signature_ed25519": "0" * 128}}
    body = canonical_bytes(signed_body(record))
    record["human_authorization"]["body_sha256"] = hashlib.sha256(body).hexdigest()
    record["human_authorization"]["signature_ed25519"] = private.sign(body).hex()
    return record


def _real_lock() -> dict:
    """In-memory shape only: identities look immutable but assert no retrieval."""
    digest = "0123456789abcdef" * 4
    artifact = {"relative_path": "inventory.json", "sha256": digest}
    pin = {
        "repository": "github.com/pneuma-lab/test-inputs",
        "revision": "0123456789abcdef0123456789abcdef01234567",
        "license": "Apache-2.0",
        "snapshot_receipt": artifact,
        "artifacts": [artifact],
    }
    return {
        "record_kind": "cloud_input_lock", "schema_version": "0.1.0",
        "frozen_timestamp": "2026-07-31T00:00:00Z",
        "provenance": {"design_sha256": digest, "code_sha256": digest},
        "model_pins": [pin], "tokenizer_pin": pin,
        "benchmark_pins": [{**pin, "dataset_revision": "89abcdef0123456789abcdef0123456789abcdef", "task_manifest_sha256": digest}],
        "container_bases": [{"repository": "docker.io/library/python", "digest": f"linux/amd64@sha256:{digest}"}],
        "verifier_sources": [pin],
        "contamination_receipts": [{"relative_path": "contamination.json", "sha256": digest}],
        "license_receipts": [{"relative_path": "licence.json", "sha256": digest}],
    }


def _admit(**overrides: object) -> dict:
    private = _private()
    kwargs: dict[str, object] = {"key_registry": _registry(private), "ledger_path": LEDGER, "at": NOW, "provider": "aws", "action": "container_build", "input_lock_sha256": "a" * 64, "scopes": ["container_base"], "projected_cost_usd": 75.0, "retries": 2, "spend_history_complete": True, "spent_or_reserved_usd": 175.0, "teardown_protected": True}
    kwargs.update(overrides)
    return require_preparation_admission(_record(private), **kwargs)  # type: ignore[arg-type]


def test_signed_envelope_admits_only_exactly_bounded_preparation() -> None:
    assert _admit()["provider"] == "aws"


def test_committed_preparation_envelope_is_authentic_and_currently_bounded() -> None:
    record = json.loads((FIXTURES / "preparation-authorization.json").read_text())
    registry = json.loads((FIXTURES / "approver-key-registry.json").read_text())
    admitted = require_preparation_admission(
        record,
        key_registry=registry,
        ledger_path=LEDGER,
        at=NOW,
        provider="aws",
        action="container_build",
        input_lock_sha256="a" * 64,
        scopes=["container_base"],
        projected_cost_usd=75.0,
        retries=2,
        spend_history_complete=True,
        spent_or_reserved_usd=175.0,
        teardown_protected=True,
    )
    assert admitted["ledger_row_id"] == "CL-028"


def test_concrete_admission_is_signed_and_bound_to_the_exact_envelope() -> None:
    private = _private()
    envelope = _record(private)
    row = next(line for line in LEDGER.read_text().splitlines() if line.startswith("| CL-026 |"))
    lock = _real_lock()
    history = LEDGER.read_bytes()
    admission = {
        "record_kind": "cloud_preparation_admission",
        "schema_version": "0.1.0",
        "envelope_sha256": hashlib.sha256(json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "provider": "aws",
        "action": "container_build",
        "input_lock_sha256": verify_input_lock(lock),
        "scopes": ["container_base"],
        "projected_cost_usd": 75.0,
        "retries": 2,
        "spend_history_sha256": hashlib.sha256(history).hexdigest(),
        "spend_history_complete": True,
        "teardown_protected": True,
        "ledger_row_id": "CL-026",
        "ledger_row_sha256": hashlib.sha256(row.encode()).hexdigest(),
        "human_authorization": {
            "approver_id": "jerry",
            "key_id": "prep-key",
            "granted_timestamp": "2026-07-31T00:00:00Z",
            "expires_timestamp": "2026-08-07T00:00:00Z",
            "body_sha256": "0" * 64,
            "signature_ed25519": "0" * 128,
        },
    }
    body = canonical_bytes(signed_body(admission))
    admission["human_authorization"]["body_sha256"] = hashlib.sha256(body).hexdigest()
    admission["human_authorization"]["signature_ed25519"] = private.sign(body).hex()
    assert require_signed_preparation_admission(
        envelope, admission, key_registry=_registry(private), ledger_path=LEDGER, at=NOW,
        input_lock=lock,
    )["action"] == "container_build"
    admission["input_lock_sha256"] = "c" * 64
    with pytest.raises(CloudManifestError, match="exact input lock"):
        require_signed_preparation_admission(
            envelope, admission, key_registry=_registry(private), ledger_path=LEDGER, at=NOW,
            input_lock=lock,
        )


def test_concrete_admission_refuses_lock_or_spend_history_substitution(tmp_path: Path) -> None:
    private = _private()
    envelope = _record(private)
    row = next(line for line in LEDGER.read_text().splitlines() if line.startswith("| CL-026 |"))
    lock = _real_lock()
    history = LEDGER.read_bytes()
    admission = {
        "record_kind": "cloud_preparation_admission", "schema_version": "0.1.0",
        "envelope_sha256": hashlib.sha256(json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "provider": "aws", "action": "container_build", "input_lock_sha256": verify_input_lock(lock),
        "scopes": ["container_base"], "projected_cost_usd": 75.0, "retries": 2,
        "spend_history_sha256": hashlib.sha256(history).hexdigest(), "spend_history_complete": True,
        "teardown_protected": True, "ledger_row_id": "CL-026", "ledger_row_sha256": hashlib.sha256(row.encode()).hexdigest(),
        "human_authorization": {"approver_id": "jerry", "key_id": "prep-key", "granted_timestamp": "2026-07-31T00:00:00Z", "expires_timestamp": "2026-08-07T00:00:00Z", "body_sha256": "0" * 64, "signature_ed25519": "0" * 128},
    }
    body = canonical_bytes(signed_body(admission))
    admission["human_authorization"]["body_sha256"] = hashlib.sha256(body).hexdigest()
    admission["human_authorization"]["signature_ed25519"] = private.sign(body).hex()
    altered_ledger = tmp_path / "ledger.md"
    altered_ledger.write_bytes(history + b"\n<!-- later ledger history -->\n")
    with pytest.raises(CloudManifestError, match="current complete spend-history ledger"):
        require_signed_preparation_admission(
            envelope, admission, key_registry=_registry(private), ledger_path=altered_ledger, at=NOW,
            input_lock=lock,
        )


@pytest.mark.parametrize("overrides, message", [
    ({"projected_cost_usd": 75.01}, "per-job ceiling"),
    ({"spent_or_reserved_usd": 175.01}, "rolling preparation ceiling"),
    ({"retries": 3}, "retry count"),
    ({"spend_history_complete": False}, "incomplete spend history"),
    ({"teardown_protected": False}, "missing teardown protection"),
    ({"provider": "azure"}, "provider drift"),
    ({"action": "training"}, "outside the preparation authorization"),
    ({"scopes": []}, "exact input lock"),
])
def test_preparation_refuses_policy_drift(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(CloudManifestError, match=message):
        _admit(**overrides)

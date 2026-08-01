from __future__ import annotations

import copy

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.preparation_admission import (
    envelope_digest,
    require_preparation_admission,
    validate_preparation_admission,
    validate_preparation_envelope,
)

from .test_authorization_keys import LEDGER, NOW, _clock, _keypair, _ledger_row_digest, _registry, _sign


def _approval() -> dict:
    return {
        "approver_id": "jerry",
        "key_id": "approver-primary",
        "granted_timestamp": "2026-07-31T00:00:00Z",
        "expires_timestamp": "2026-08-07T00:00:00Z",
        "body_sha256": "0" * 64,
        "signature_ed25519": "0" * 128,
    }


def _records():
    private = _keypair()
    envelope = _sign(private, {
        "record_kind": "cloud_preparation_envelope",
        "schema_version": "0.1.0",
        "frozen_timestamp": NOW,
        "status": "authorized",
        "provider": "aws",
        "allowed_action_classes": ["input_retrieval", "image_build", "gpu_smoke"],
        "total_cost_ceiling_usd": 100.0,
        "expires_timestamp": "2026-08-07T00:00:00Z",
        "ledger_row_id": "CL-026",
        "ledger_row_sha256": _ledger_row_digest(),
        "human_authorization": _approval(),
    })
    admission = _sign(private, {
        "record_kind": "cloud_preparation_admission",
        "schema_version": "0.1.0",
        "frozen_timestamp": NOW,
        "status": "authorized",
        "preparation_envelope_sha256": envelope_digest(envelope),
        "action_id": "step5b-input-retrieval-001",
        "action_class": "input_retrieval",
        "provider": "aws",
        "region": "us-west-2",
        "input_lock_sha256": "1" * 64,
        "manifest_sha256": "2" * 64,
        "prior_envelope_spend_usd": 10.0,
        "projected_cost_usd": 3.25,
        "max_retries": 1,
        "spend_history_sha256": "3" * 64,
        "teardown_protected": True,
        "expires_timestamp": "2026-08-07T00:00:00Z",
        "ledger_row_id": "CL-026",
        "ledger_row_sha256": _ledger_row_digest(),
        "human_authorization": _approval(),
    })
    return private, envelope, admission


def _require(envelope, admission):
    private = _keypair()
    return require_preparation_admission(
        envelope, admission, key_registry=_registry(private), ledger_path=LEDGER,
        expected_action_id="step5b-input-retrieval-001",
        expected_action_class="input_retrieval", expected_manifest_sha256="2" * 64,
        expected_provider="aws", expected_region="us-west-2",
        expected_input_lock_sha256="1" * 64, spend_history_sha256="3" * 64,
        expected_projected_cost_usd=3.25, expected_max_retries=1,
        clock=_clock(),
    )


def test_two_signed_layers_admit_one_exact_action() -> None:
    _, envelope, admission = _records()
    assert validate_preparation_envelope(envelope)["status"] == "authorized"
    assert validate_preparation_admission(admission)["status"] == "authorized"
    assert _require(envelope, admission)["action_id"] == "step5b-input-retrieval-001"


@pytest.mark.parametrize("field,value,match", [
    ("manifest_sha256", "9" * 64, "requested manifest"),
    ("input_lock_sha256", "9" * 64, "requested input lock"),
    ("spend_history_sha256", "9" * 64, "current spend history"),
    ("action_class", "image_build", "requested action class"),
])
def test_exact_action_drift_is_refused(field, value, match) -> None:
    _, envelope, admission = _records()
    changed = copy.deepcopy(admission)
    changed[field] = value
    with pytest.raises(CloudManifestError, match="canonical signed body"):
        _require(envelope, changed)


def test_candidate_or_over_ceiling_action_is_refused() -> None:
    private, envelope, admission = _records()
    candidate = {**admission, "status": "candidate", "ledger_row_id": None, "ledger_row_sha256": None, "human_authorization": None}
    with pytest.raises(CloudManifestError, match="authorized envelope and exact authorized admission"):
        _require(envelope, candidate)
    expensive = copy.deepcopy(admission)
    expensive["prior_envelope_spend_usd"] = 97.0
    expensive = _sign(private, expensive)
    with pytest.raises(CloudManifestError, match="cost ceiling"):
        _require(envelope, expensive)

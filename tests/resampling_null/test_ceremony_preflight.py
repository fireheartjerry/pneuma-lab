from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.preflight import (
    DRAND_MAINNET_CHAIN_HASH,
    ConfirmationPreflightRegistry,
    ConfirmationRosterCeremonyCapability,
)


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _bundle(root: Path) -> tuple[Path, Path, Path, dict[str, object]]:
    root.mkdir(parents=True, exist_ok=True)
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw().hex()
    study_id = "p0-ceremony-test"
    randomness = bytes.fromhex("ab" * 32)
    eligibility = {
        "record_kind": "resampling_eligibility_manifest_v1",
        "schema_version": "1",
        "study_id": study_id,
        "precommit_sha256": _sha("precommit"),
        "beacon_receipt": {
            "chain_hash": DRAND_MAINNET_CHAIN_HASH,
            "round": 123,
            "randomness_hex": randomness.hex(),
        },
    }
    eligibility_path = root / "eligibility.json"
    eligibility_path.write_bytes(canonical_json_bytes(eligibility, indent=None))
    policy = {
        "record_kind": "resampling_roster_ceremony_policy_v1",
        "schema_version": "1",
        "study_id": study_id,
        "qualification_universe_sha256": _sha("qualification"),
        "selection_program_sha256": _sha("selection"),
        "precommit_sha256": _sha("precommit"),
        "drand": {
            "chain_hash": DRAND_MAINNET_CHAIN_HASH,
            "scheme": "pedersen-bls-chained",
            "client_version": "drand-client==1.4.2",
            "group_hash": _sha("drand-group"),
            "genesis_time": 0,
            "period": 30,
        },
        "sigstore": {
            "contract_id": "sigstore-bundle-verification-v1",
            "verifier_source_sha256": _sha("sigstore-verifier"),
            "required_rekor_log": "rekor-public-good",
            "bundle_format": "sigstore-bundle-v0.3",
        },
        "node": {
            "contract_id": "node-roster-selection-v1",
            "program_sha256": _sha("node-program"),
            "runtime": "nodejs-22",
            "output_schema": "resampling-eligibility-manifest-v1",
        },
        "public_key_ed25519_hex": public,
    }
    policy_path = root / "policy.json"
    policy_path.write_bytes(canonical_json_bytes(policy, indent=None))
    eligibility_digest = hashlib.sha256(eligibility_path.read_bytes()).hexdigest()
    policy_digest = hashlib.sha256(policy_path.read_bytes()).hexdigest()
    receipt: dict[str, object] = {
        "record_kind": "resampling_roster_ceremony_receipt_v1",
        "schema_version": "1",
        "study_id": study_id,
        "qualification_universe_sha256": policy["qualification_universe_sha256"],
        "selection_program_sha256": policy["selection_program_sha256"],
        "precommit_sha256": policy["precommit_sha256"],
        "anchor_sha256": _sha("anchor"),
        "reveal_sha256": _sha("reveal"),
        "eligibility_manifest_sha256": eligibility_digest,
        "ceremony_policy_sha256": policy_digest,
        "sigstore": {
            "verified": True,
            "bundle_sha256": _sha("bundle"),
            "rekor_entry_sha256": _sha("rekor"),
            "artifact_sha256": _sha("artifact"),
            "verifier_source_sha256": policy["sigstore"]["verifier_source_sha256"],
        },
        "drand": {
            "verified": True,
            "chain_hash": DRAND_MAINNET_CHAIN_HASH,
            "round": 123,
            "randomness_hex": randomness.hex(),
            "randomness_sha256": hashlib.sha256(randomness).hexdigest(),
            "proof_sha256": _sha("proof"),
        },
        "node": {
            "verified": True,
            "program_sha256": policy["node"]["program_sha256"],
            "output_sha256": eligibility_digest,
        },
        "signature_ed25519_hex": "0" * 128,
    }
    signed = copy.deepcopy(receipt)
    del signed["signature_ed25519_hex"]
    receipt["signature_ed25519_hex"] = private.sign(canonical_json_bytes(signed, indent=None)).hex()
    receipt_path = root / "receipt.json"
    receipt_path.write_bytes(canonical_json_bytes(receipt, indent=None))
    return eligibility_path, policy_path, receipt_path, receipt


def test_compact_live_ceremony_bundle_mints_only_opaque_capability(tmp_path: Path) -> None:
    eligibility, policy, receipt, _ = _bundle(tmp_path)
    capability = ConfirmationPreflightRegistry().claim_roster_ceremony_from_manifest(
        eligibility_source=eligibility,
        ceremony_policy_source=policy,
        ceremony_receipt_source=receipt,
        study_id="p0-ceremony-test",
    )
    assert isinstance(capability, ConfirmationRosterCeremonyCapability)
    assert capability.receipt_sha256 == hashlib.sha256(receipt.read_bytes()).hexdigest()
    with pytest.raises(TypeError, match="no public constructor"):
        ConfirmationRosterCeremonyCapability()


def test_ceremony_rejects_missing_mismatch_and_synthetic_authority(tmp_path: Path) -> None:
    eligibility, policy, receipt, _ = _bundle(tmp_path)
    with pytest.raises(RecordValidationError):
        ConfirmationPreflightRegistry().claim_roster_ceremony_from_manifest(
            eligibility_source=eligibility,
            ceremony_policy_source=policy,
            ceremony_receipt_source=tmp_path / "missing.json",
            study_id="p0-ceremony-test",
        )

    mutated = json.loads(policy.read_text(encoding="utf-8"))
    mutated["selection_program_sha256"] = _sha("different-selection")
    policy.write_bytes(canonical_json_bytes(mutated, indent=None))
    with pytest.raises(RecordValidationError, match="does not bind manifest-owned bytes"):
        ConfirmationPreflightRegistry().claim_roster_ceremony_from_manifest(
            eligibility_source=eligibility,
            ceremony_policy_source=policy,
            ceremony_receipt_source=receipt,
            study_id="p0-ceremony-test",
        )

    eligibility, policy, receipt, _ = _bundle(tmp_path / "synthetic")
    synthetic = json.loads(eligibility.read_text(encoding="utf-8"))
    synthetic["record_kind"] = "test_only_eligibility_fixture"
    eligibility.write_bytes(canonical_json_bytes(synthetic, indent=None))
    with pytest.raises(RecordValidationError, match="synthetic"):
        ConfirmationPreflightRegistry().claim_roster_ceremony_from_manifest(
            eligibility_source=eligibility,
            ceremony_policy_source=policy,
            ceremony_receipt_source=receipt,
            study_id="p0-ceremony-test",
        )

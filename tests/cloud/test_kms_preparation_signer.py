from __future__ import annotations

import base64
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.research import sign_preparation_action


def _public_response(private: Ed25519PrivateKey) -> dict[str, object]:
    public_der = private.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return {
        "KeyUsage": "SIGN_VERIFY",
        "SigningAlgorithms": ["ED25519_SHA_512"],
        "PublicKey": base64.b64encode(public_der).decode("ascii"),
    }


def test_kms_signer_matches_registry_and_returns_offline_verifiable_signature(monkeypatch) -> None:
    private = Ed25519PrivateKey.generate()
    calls: list[list[str]] = []

    def fake_aws(arguments: list[str]) -> dict[str, object]:
        calls.append(arguments)
        if arguments[1] == "get-public-key":
            return _public_response(private)
        message_path = next(value.removeprefix("fileb://") for value in arguments if value.startswith("fileb://"))
        signature = private.sign(Path(message_path).read_bytes())
        return {"Signature": base64.b64encode(signature).decode("ascii")}

    monkeypatch.setattr(sign_preparation_action, "_aws_json", fake_aws)
    public_hex = private.public_key().public_bytes_raw().hex()
    signer = sign_preparation_action._kms_signer(
        key_id="alias/pneuma-approver", region="us-east-1", expected_public_key_hex=public_hex,
    )
    body = b'canonical-body'
    private.public_key().verify(signer(body), body)
    assert calls[1][-2:] == ["--signing-algorithm", "ED25519_SHA_512"]


def test_kms_signer_rejects_key_not_committed_in_registry(monkeypatch) -> None:
    private = Ed25519PrivateKey.generate()
    monkeypatch.setattr(sign_preparation_action, "_aws_json", lambda arguments: _public_response(private))
    with pytest.raises(ValueError, match="does not match"):
        sign_preparation_action._kms_signer(
            key_id="alias/pneuma-approver", region="us-east-1", expected_public_key_hex="00" * 32,
        )

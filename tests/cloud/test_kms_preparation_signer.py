from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import subprocess

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.research import sign_preparation_action

from pneuma_lab.cloud.qualification_execution import (
    parse_terraform_show,
    terraform_plan_binding_digest,
)

from .test_ephemeral_runner import terraform_show


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


def test_execution_manifest_digest_binds_saved_plan_and_show_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = tmp_path / "qualification.tfplan"
    saved.write_bytes(b"exact-plan-bytes")
    show = terraform_show()
    show_sha = parse_terraform_show(show)["terraform_show_sha256"]
    plan = {
        "saved_plan_path": str(saved),
        "saved_plan_sha256": hashlib.sha256(saved.read_bytes()).hexdigest(),
        "terraform_show_sha256": show_sha,
    }

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, json.dumps(show).encode(), b"")

    monkeypatch.setattr(sign_preparation_action.subprocess, "run", fake_run)
    assert sign_preparation_action.execution_manifest_digest(plan) == (
        terraform_plan_binding_digest(plan["saved_plan_sha256"], show_sha)
    )
    saved.write_bytes(b"tampered-plan-bytes")
    with pytest.raises(ValueError, match="saved Terraform plan bytes"):
        sign_preparation_action.execution_manifest_digest(plan)

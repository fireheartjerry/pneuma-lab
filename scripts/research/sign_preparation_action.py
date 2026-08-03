"""Sign one exact bounded preparation action using the registered CloudShell key."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from pneuma_lab.cloud.authorization_keys import (
    authorization_body_digest,
    canonical_bytes,
    canonical_ledger_digest,
    ledger_row,
    signed_body,
    validate_key_registry,
)
from pneuma_lab.cloud.preparation_admission import envelope_digest, require_preparation_admission
from pneuma_lab.cloud.qualification_execution import (
    parse_terraform_show_json,
    terraform_plan_binding_digest,
)
try:
    from scripts.research.sign_step5b_inventory_admission import _private_key
except ModuleNotFoundError:
    from sign_step5b_inventory_admission import _private_key


def plan_digest(plan: dict[str, Any]) -> str:
    body = dict(plan)
    body.pop("plan_sha256", None)
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def execution_manifest_digest(plan: dict[str, Any]) -> str:
    """Bind the exact saved Terraform plan and show bytes for execution."""

    saved_sha = plan.get("saved_plan_sha256")
    show_sha = plan.get("terraform_show_sha256")
    if saved_sha is None and show_sha is None:
        return plan_digest(plan)
    if not isinstance(saved_sha, str) or not isinstance(show_sha, str):
        raise ValueError(
            "Terraform execution binding requires saved_plan_sha256 and "
            "terraform_show_sha256 together"
        )
    saved_path_value = plan.get("saved_plan_path")
    if not isinstance(saved_path_value, str) or not saved_path_value:
        raise ValueError("Terraform execution binding lacks saved_plan_path")
    saved_path = Path(saved_path_value)
    observed_saved_sha = hashlib.sha256(saved_path.read_bytes()).hexdigest()
    if observed_saved_sha != saved_sha:
        raise ValueError("saved Terraform plan bytes do not match the signing plan")
    directory = plan.get(
        "terraform_directory", "infra/terraform/qualification"
    )
    if not isinstance(directory, str) or not directory:
        raise ValueError("Terraform execution binding has an invalid directory")
    result = subprocess.run(
        [
            "terraform",
            f"-chdir={directory}",
            "show",
            "-json",
            str(saved_path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise ValueError("terraform show failed while binding the signing plan")
    observed_show_sha = parse_terraform_show_json(result.stdout)[
        "terraform_show_sha256"
    ]
    if observed_show_sha != show_sha:
        raise ValueError("Terraform show bytes do not match the signing plan")
    return terraform_plan_binding_digest(saved_sha, show_sha)


def _aws_json(arguments: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        ["aws", *arguments, "--output", "json"], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    return json.loads(completed.stdout)


def _kms_signer(*, key_id: str, region: str, expected_public_key_hex: str) -> Callable[[bytes], bytes]:
    public = _aws_json(["kms", "get-public-key", "--region", region, "--key-id", key_id])
    if public.get("KeyUsage") != "SIGN_VERIFY" or "ED25519_SHA_512" not in public.get("SigningAlgorithms", []):
        raise ValueError("KMS key is not an Ed25519 SIGN_VERIFY key")
    loaded = serialization.load_der_public_key(base64.b64decode(public["PublicKey"]))
    if not isinstance(loaded, Ed25519PublicKey):
        raise ValueError("KMS public key is not Ed25519")
    observed = loaded.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    if observed != expected_public_key_hex:
        raise ValueError("KMS public key does not match the committed approver registry")

    def sign(body: bytes) -> bytes:
        if len(body) > 4096:
            raise ValueError("KMS RAW signing body exceeds the 4096-byte service limit")
        with tempfile.TemporaryDirectory() as directory:
            message = Path(directory) / "canonical-body.bin"
            message.write_bytes(body)
            result = _aws_json([
                "kms", "sign", "--region", region, "--key-id", key_id,
                "--message", f"fileb://{message}", "--message-type", "RAW",
                "--signing-algorithm", "ED25519_SHA_512",
            ])
        return base64.b64decode(result["Signature"])

    return sign


def _approval_for(key: dict[str, Any], granted: str, expires: str) -> dict[str, Any]:
    return {
        "approver_id": key["approver_id"], "key_id": key["key_id"],
        "granted_timestamp": granted, "expires_timestamp": expires,
        "body_sha256": "0" * 64, "signature_ed25519": "0" * 128,
    }


def _sign_with(signer: Callable[[bytes], bytes], record: dict[str, Any]) -> dict[str, Any]:
    body = canonical_bytes(signed_body(record))
    record["human_authorization"]["body_sha256"] = hashlib.sha256(body).hexdigest()
    signature = signer(body)
    if len(signature) != 64:
        raise ValueError("Ed25519 signer returned a non-64-byte signature")
    record["human_authorization"]["signature_ed25519"] = signature.hex()
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--key-registry", type=Path, required=True)
    signer_group = parser.add_mutually_exclusive_group(required=True)
    signer_group.add_argument("--private-key", type=Path)
    signer_group.add_argument("--kms-key-id")
    parser.add_argument("--kms-region", default="us-east-1")
    parser.add_argument("--registry-key-id", default="pneuma-b1-20260801-r1")
    parser.add_argument("--expires", required=True)
    parser.add_argument("--envelope-ledger-row", required=True)
    parser.add_argument("--admission-ledger-row", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    digest = plan_digest(plan)
    if digest != plan["plan_sha256"]:
        raise ValueError("plan_sha256 does not match canonical plan bytes with that field removed")
    manifest_sha256 = execution_manifest_digest(plan)
    granted = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    registry = validate_key_registry(json.loads(args.key_registry.read_text(encoding="utf-8")))
    registered = next((key for key in registry["keys"] if key["key_id"] == args.registry_key_id), None)
    if registered is None or registered["status"] != "active":
        raise ValueError("requested signer key is not active in the committed registry")
    if args.private_key is not None:
        private = _private_key(args.private_key)
        signer = private.sign
        observed_public = private.public_key().public_bytes_raw().hex()
        if observed_public != registered["public_key_hex"]:
            raise ValueError("private key does not match the committed approver registry")
    else:
        signer = _kms_signer(
            key_id=args.kms_key_id, region=args.kms_region,
            expected_public_key_hex=registered["public_key_hex"],
        )
    envelope_row = ledger_row(args.ledger, args.envelope_ledger_row)
    admission_row = ledger_row(args.ledger, args.admission_ledger_row)
    envelope = _sign_with(signer, {
        "record_kind": "cloud_preparation_envelope", "schema_version": "0.1.0",
        "frozen_timestamp": granted, "status": "authorized", "provider": plan["provider"],
        "allowed_action_classes": [plan["action_class"]],
        "total_cost_ceiling_usd": plan["cost_ceiling_usd"], "expires_timestamp": args.expires,
        "ledger_row_id": args.envelope_ledger_row,
        "ledger_row_sha256": hashlib.sha256(envelope_row.encode()).hexdigest(),
        "human_authorization": _approval_for(registered, granted, args.expires),
    })
    admission = _sign_with(signer, {
        "record_kind": "cloud_preparation_admission", "schema_version": "0.1.0",
        "frozen_timestamp": granted, "status": "authorized",
        "preparation_envelope_sha256": envelope_digest(envelope), "action_id": plan["action_id"],
        "action_class": plan["action_class"], "provider": plan["provider"], "region": plan["region"],
        "input_lock_sha256": plan["input_lock_sha256"], "manifest_sha256": digest,
        "prior_envelope_spend_usd": 0.0, "projected_cost_usd": plan["projected_cost_usd"],
        "max_retries": plan["max_retries"], "spend_history_sha256": canonical_ledger_digest(args.ledger),
        "teardown_protected": True, "expires_timestamp": args.expires,
        "ledger_row_id": args.admission_ledger_row,
        "ledger_row_sha256": hashlib.sha256(admission_row.encode()).hexdigest(),
        "human_authorization": _approval_for(registered, granted, args.expires),
    })
    require_preparation_admission(
        envelope, admission, key_registry=registry, ledger_path=args.ledger,
        expected_action_id=plan["action_id"], expected_action_class=plan["action_class"],
        expected_provider=plan["provider"], expected_region=plan["region"],
        expected_manifest_sha256=manifest_sha256,
        expected_input_lock_sha256=plan["input_lock_sha256"],
        expected_projected_cost_usd=plan["projected_cost_usd"], expected_max_retries=plan["max_retries"],
        spend_history_sha256=canonical_ledger_digest(args.ledger),
    )
    package = {"record_kind": "cloud_preparation_signing_package", "plan_sha256": digest,
               "saved_plan_sha256": plan.get("saved_plan_sha256"),
               "terraform_show_sha256": plan.get("terraform_show_sha256"),
               "terraform_plan_binding_sha256": manifest_sha256,
               "envelope_body_sha256": authorization_body_digest(envelope),
               "admission_body_sha256": authorization_body_digest(admission),
               "envelope": envelope, "admission": admission}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(package) + b"\n")
    print(json.dumps({key: package[key] for key in ("plan_sha256", "envelope_body_sha256", "admission_body_sha256")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

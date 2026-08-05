"""Verify the human-produced Sigstore anchor for the roster precommit.

This verifier is intentionally an adapter around the installed Sigstore
implementation.  It does not create bundles, contact Rekor, or mint study
authority.  The JSON checks below make the exact v0.3 evidence shape explicit
before the CLI verifier is trusted by the ceremony runner.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

from cryptography import x509


IDENTITY = "fireheartjerry@gmail.com"
ISSUER = "https://accounts.google.com"


def _regular(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"not one regular non-symlink file: {path}")
    return path.read_bytes()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify(bundle_path: Path, artifact_path: Path) -> dict[str, Any]:
    bundle_raw = _regular(bundle_path)
    artifact_raw = _regular(artifact_path)
    bundle = json.loads(bundle_raw)
    if not isinstance(bundle, Mapping) or bundle.get("mediaType") != "application/vnd.dev.sigstore.bundle.v0.3+json":
        raise ValueError("Sigstore bundle is not v0.3")
    material = bundle.get("verificationMaterial")
    if not isinstance(material, Mapping):
        raise ValueError("Sigstore verification material is missing")
    certificate = material.get("certificate")
    if not isinstance(certificate, Mapping) or not isinstance(certificate.get("rawBytes"), str):
        raise ValueError("Sigstore Fulcio certificate is missing")
    cert = x509.load_der_x509_certificate(base64.b64decode(certificate["rawBytes"], validate=True))
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound as exc:
        raise ValueError("Fulcio certificate has no subject alternative name") from exc
    if IDENTITY not in san.get_values_for_type(x509.RFC822Name):
        raise ValueError("Fulcio certificate identity does not match the registered OIDC identity")
    issuer_extension = cert.extensions.get_extension_for_oid(x509.ObjectIdentifier("1.3.6.1.4.1.57264.1.1"))
    issuer = bytes(getattr(issuer_extension.value, "value", issuer_extension.value)).decode("utf-8")
    if issuer != ISSUER:
        raise ValueError("Fulcio certificate OIDC issuer does not match the registered issuer")
    entries = material.get("tlogEntries")
    if not isinstance(entries, list) or len(entries) != 1:
        raise ValueError("Sigstore bundle must contain exactly one Rekor entry")
    entry = entries[0]
    if not isinstance(entry, Mapping) or not isinstance(entry.get("inclusionProof"), Mapping):
        raise ValueError("Sigstore bundle lacks a public Rekor inclusion proof")
    proof = entry["inclusionProof"]
    if not proof.get("rootHash") or not proof.get("treeSize") or not isinstance(proof.get("hashes"), list):
        raise ValueError("Rekor inclusion proof is incomplete")
    timestamps = material.get("timestampVerificationData", {}).get("rfc3161Timestamps", [])
    if not isinstance(timestamps, list) or len(timestamps) != 1:
        raise ValueError("Sigstore bundle must contain exactly one RFC3161 timestamp")
    message = bundle.get("messageSignature")
    digest = message.get("messageDigest") if isinstance(message, Mapping) else None
    if not isinstance(digest, Mapping) or digest.get("algorithm") != "SHA2_256":
        raise ValueError("Sigstore message digest is not SHA2-256")
    expected_b64 = base64.b64encode(bytes.fromhex(_sha(artifact_raw))).decode("ascii")
    if digest.get("digest") != expected_b64:
        raise ValueError("Sigstore bundle does not bind the exact precommit bytes")
    command = [
        "sigstore", "verify", "identity", "--offline", "--bundle", str(bundle_path),
        "--cert-identity", IDENTITY, "--cert-oidc-issuer", ISSUER, str(artifact_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ValueError(f"installed Sigstore verifier rejected the bundle: {result.stderr[-2000:]}")
    return {
        "bundle_sha256": _sha(bundle_raw),
        "artifact_sha256": _sha(artifact_raw),
        "rekor_entry_sha256": _sha(json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()),
        "certificate_sha256": _sha(base64.b64decode(certificate["rawBytes"])),
        "verifier": "sigstore verify identity --offline",
        "identity": IDENTITY,
        "issuer": ISSUER,
        "bundle_format": "sigstore-bundle-v0.3",
        "rekor_inclusion_proof": True,
        "rfc3161_timestamp_count": 1,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.bundle, args.artifact), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

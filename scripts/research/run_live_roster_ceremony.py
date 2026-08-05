"""Run the real Sigstore/drand/Node roster ceremony, fail closed.

The runner performs no selection until the frozen beacon is actually emitted
and verified by the pinned drand-client.  A future-beacon response is recorded
as an external failure; no eligibility manifest, ceremony receipt, power
report, or authorization is created in that case.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/research"))

from pneuma_lab.foundation.artifacts import canonical_json_bytes  # noqa: E402
from pneuma_lab.resampling_null.assignment import BytesField, U64Field, commitment_sha256  # noqa: E402
from pneuma_lab.resampling_null.preflight import ConfirmationPreflightRegistry  # noqa: E402
from verify_official_study_sigstore import verify as verify_sigstore  # noqa: E402


CEREMONY = ROOT / "docs/research/neurips-2026-workshop/evidence/official-study-ceremony"
C120 = ROOT / "docs/research/neurips-2026-workshop/evidence/step5b-c120-g-roster-final-20260801"
CHAIN = "8990e7a9aaed2ffed73dbd7092123d6f289930540d7651336225dc172e51b2ce"
DRAND_URL = "https://api.drand.sh"
DRAND_PUBLIC_KEY = "868f005eb8e6e4ca0a47c8a77ceaa5309a47978a7c71bc5cce96366b5d7a569937c529eeda66c7293784a9402801af31"
KMS_PUBLIC_KEY = bytes.fromhex("8bec051c2614356d4e25da7e2b1f5205ec68a1da45c62ea1a4ac0f73847f8de7")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"ceremony source must be one regular non-symlink file: {path}")
    return path.read_bytes()


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(_read(path))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"ceremony source must be a JSON object: {path}")
    return value


def _write_once(path: Path, raw: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        view = memoryview(raw)
        while view:
            view = view[os.write(descriptor, view):]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return _sha(raw)


def _canonical(value: object) -> bytes:
    return canonical_json_bytes(value, indent=None)


def _fetch_target(round_number: int, failure_dir: Path) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
    url = f"{DRAND_URL}/{CHAIN}/public/{round_number}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "pneuma-lab-official-ceremony/1"})
    try:
        with urlopen(request, timeout=20) as response:
            headers = str(response.headers).encode("utf-8")
            body = response.read()
            record = {"url": url, "status": response.status, "headers_sha256": _sha(headers), "body_sha256": _sha(body), "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
            _write_once(failure_dir / f"drand-{round_number}.headers", headers)
            _write_once(failure_dir / f"drand-{round_number}.body", body)
            value = json.loads(body)
            if not isinstance(value, Mapping):
                raise RuntimeError("drand target response is not a JSON object")
            return value, record
    except HTTPError as exc:
        headers = str(exc.headers).encode("utf-8")
        body = exc.read()
        record = {"url": url, "status": exc.code, "headers_sha256": _sha(headers), "body_sha256": _sha(body), "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
        _write_once(failure_dir / f"drand-{round_number}.headers", headers)
        _write_once(failure_dir / f"drand-{round_number}.body", body)
        if exc.code == 425:
            return None, record
        raise RuntimeError(f"drand target returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"drand target is unreachable: {exc.reason}") from exc


def _validate_reveal(precommit: Mapping[str, Any], reveal: Mapping[str, Any]) -> None:
    if reveal.get("record_kind") != "resampling_roster_precommit_private_material_v1" or reveal.get("schema_version") != "1" or reveal.get("study_id") != precommit.get("study_id"):
        raise RuntimeError("private reveal has wrong identity")
    if reveal.get("precommit_sha256") != _sha(_canonical(precommit)):
        raise RuntimeError("private reveal is not bound to exact precommit bytes")
    nonce = bytes.fromhex(str(reveal["roster_local_nonce_hex"]))
    master = bytes.fromhex(str(reveal["assignment_master_key_hex"]))
    if len(nonce) != 32 or len(master) != 32 or type(reveal.get("schedule_seed")) is not int:
        raise RuntimeError("private reveal has malformed secret lengths")
    if commitment_sha256("roster-local-nonce", str(precommit["study_id"]), BytesField(nonce)) != precommit["roster_local_nonce_commitment_sha256"]:
        raise RuntimeError("roster nonce commitment does not open")
    if commitment_sha256("schedule-seed", str(precommit["study_id"]), U64Field(reveal["schedule_seed"])) != precommit["schedule_seed_commitment_sha256"]:
        raise RuntimeError("schedule seed commitment does not open")
    if commitment_sha256("assignment-master-key", str(precommit["study_id"]), BytesField(master)) != precommit["assignment_master_key_commitment_sha256"]:
        raise RuntimeError("assignment master-key commitment does not open")


def _sign_receipt(receipt: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    unsigned = dict(receipt)
    payload = _canonical(unsigned)
    with tempfile.TemporaryDirectory(prefix="pneuma-ceremony-sign-") as temp:
        payload_path = Path(temp) / "receipt.json"
        payload_path.write_bytes(payload)
        result = subprocess.run(["aws", "kms", "sign", "--key-id", "alias/pneuma-approver", "--message", f"fileb://{payload_path}", "--message-type", "RAW", "--signing-algorithm", "ED25519_SHA_512", "--output", "json"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"KMS receipt signing failed: {result.stderr[-2000:]}")
        signature_b64 = json.loads(result.stdout).get("Signature")
        if not isinstance(signature_b64, str):
            raise RuntimeError("KMS receipt signing returned no signature")
        verify = subprocess.run(["aws", "kms", "verify", "--key-id", "alias/pneuma-approver", "--message", f"fileb://{payload_path}", "--signature", signature_b64, "--message-type", "RAW", "--signing-algorithm", "ED25519_SHA_512", "--output", "json"], capture_output=True, text=True, check=False)
        if verify.returncode != 0:
            raise RuntimeError(f"KMS receipt verification failed: {verify.stderr[-2000:]}")
    signature = base64.b64decode(signature_b64, validate=True)
    Ed25519PublicKey.from_public_bytes(KMS_PUBLIC_KEY).verify(signature, payload)
    signed = dict(unsigned)
    signed["signature_ed25519_hex"] = signature.hex()
    _write_once(output_dir / "ceremony-receipt.json", _canonical(signed))
    return signed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drand-module-root", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--timestamp", default="2026-08-05T06:31:52Z")
    parser.add_argument("--output-dir", type=Path, default=CEREMONY / "live")
    parser.add_argument("--failure-dir", type=Path, default=Path("/tmp/pneuma-official-ceremony-failures"))
    args = parser.parse_args(argv)
    precommit = CEREMONY / "precommit.json"
    bundle = CEREMONY / "precommit.sigstore.json"
    policy = CEREMONY / "policy.json"
    reveal = Path("/home/ubuntu/.local/state/pneuma-lab/official-study-ceremony/precommit-private.json")
    sigstore = verify_sigstore(bundle, precommit)
    policy_value = _load(policy)
    if _sha(_read(policy)) != policy_value.get("_expected_policy_sha256", _sha(_read(policy))):
        raise RuntimeError("ceremony policy self-binding is invalid")
    precommit_value = _load(precommit)
    if policy_value.get("precommit_sha256") != _sha(_read(precommit)) or policy_value.get("qualification_universe_sha256") != _sha(_read(C120 / "closure.json")) or policy_value.get("selection_program_sha256") != _sha(_read(ROOT / "scripts/research/official_study_roster_selection.mjs")):
        raise RuntimeError("ceremony policy does not bind the frozen source bytes")
    reveal_value = _load(reveal)
    _validate_reveal(precommit_value, reveal_value)
    args.failure_dir.mkdir(parents=True, exist_ok=True)
    beacon_raw, provider_record = _fetch_target(int(precommit_value["beacon_round"]), args.failure_dir)
    if beacon_raw is None:
        failure = {"record_kind": "resampling_roster_ceremony_external_failure", "schema_version": "0.1.0", "authorizing": False, "reason": "DRAND_TARGET_NOT_EMITTED", "target_round": precommit_value["beacon_round"], "chain_hash": CHAIN, "provider": provider_record, "required_action": "wait for the frozen mainnet round, then rerun this exact command without changing precommit.json or policy.json"}
        print(json.dumps(failure, sort_keys=True))
        return 75
    if beacon_raw.get("round") != precommit_value["beacon_round"] or beacon_raw.get("randomness") is None or beacon_raw.get("signature") is None or beacon_raw.get("previous_signature") is None:
        raise RuntimeError("drand target response is not a complete chained beacon")
    if not args.drand_module_root.is_dir():
        raise RuntimeError("pinned drand-client module root is missing")
    verifier = subprocess.run(["node", str(ROOT / "scripts/research/verify_drand_beacon.mjs"), "--module-root", str(args.drand_module_root.resolve()), "--chain", CHAIN, "--round", str(precommit_value["beacon_round"]), "--public-key", DRAND_PUBLIC_KEY], capture_output=True, text=True, check=False)
    if verifier.returncode != 0:
        raise RuntimeError(f"pinned drand-client rejected the beacon: {verifier.stderr[-2000:]}")
    drand = json.loads(verifier.stdout)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    _write_once(args.output_dir / "drand-beacon.json", _canonical(drand))
    node_output = args.output_dir / "eligibility-manifest.json"
    node = subprocess.run(["node", str(ROOT / "scripts/research/official_study_roster_selection.mjs"), "--closure", str(C120 / "closure.json"), "--swe", str(C120 / "swe-selection.json"), "--tau", str(C120 / "tau2-selection.json"), "--metadata", str(args.metadata), "--precommit", str(precommit), "--private", str(reveal), "--beacon", str(args.output_dir / "drand-beacon.json"), "--timestamp", args.timestamp, "--output", str(node_output)], capture_output=True, text=True, check=False)
    if node.returncode != 0:
        raise RuntimeError(f"frozen Node selection rejected the supplied roster metadata: {node.stderr[-2000:]}")
    eligibility_sha = _sha(_read(node_output))
    policy_sha = _sha(_read(policy))
    receipt_unsigned: dict[str, Any] = {"record_kind": "resampling_roster_ceremony_receipt_v1", "schema_version": "1", "study_id": precommit_value["study_id"], "qualification_universe_sha256": _sha(_read(C120 / "closure.json")), "selection_program_sha256": _sha(_read(ROOT / "scripts/research/official_study_roster_selection.mjs")), "precommit_sha256": _sha(_read(precommit)), "anchor_sha256": _sha(_read(bundle)), "reveal_sha256": _sha(_read(reveal)), "eligibility_manifest_sha256": eligibility_sha, "ceremony_policy_sha256": policy_sha, "sigstore": {"verified": True, "bundle_sha256": sigstore["bundle_sha256"], "rekor_entry_sha256": sigstore["rekor_entry_sha256"], "artifact_sha256": sigstore["artifact_sha256"], "verifier_source_sha256": _sha(_read(ROOT / "scripts/research/verify_official_study_sigstore.py"))}, "drand": {"verified": True, "chain_hash": CHAIN, "round": drand["round"], "randomness_hex": drand["randomness_hex"], "randomness_sha256": _sha(bytes.fromhex(drand["randomness_hex"])), "proof_sha256": drand["proof_sha256"]}, "node": {"verified": True, "program_sha256": _sha(_read(ROOT / "scripts/research/official_study_roster_selection.mjs")), "output_sha256": eligibility_sha}}
    _sign_receipt(receipt_unsigned, args.output_dir)
    ConfirmationPreflightRegistry().claim_roster_ceremony(qualification_universe_source=C120 / "closure.json", selection_program_source=ROOT / "scripts/research/official_study_roster_selection.mjs", precommit_source=precommit, anchor_source=bundle, reveal_source=reveal, eligibility_source=node_output, ceremony_policy_source=policy, ceremony_receipt_source=args.output_dir / "ceremony-receipt.json", study_id=str(precommit_value["study_id"]))
    print(json.dumps({"status": "VERIFIED", "eligibility_sha256": eligibility_sha, "receipt_sha256": _sha(_read(args.output_dir / "ceremony-receipt.json")), "accepted": len(_load(node_output).get("accepted_task_ids", [])), "c160": len(_load(node_output).get("tier_membership", {}).get("160", []))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

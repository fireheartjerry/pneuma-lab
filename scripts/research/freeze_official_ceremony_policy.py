"""Freeze the manifest-owned policy for the real roster ceremony.

This writes a non-authorizing policy only.  It never contacts Sigstore, drand,
AWS, or the benchmark and refuses to overwrite an existing policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from pneuma_lab.foundation.artifacts import canonical_json_bytes


CHAIN = "8990e7a9aaed2ffed73dbd7092123d6f289930540d7651336225dc172e51b2ce"
GROUP = "176f93498eac9ca337150b46d21dd58673ea4e3581185f869672e59fa4cb390a"
PUBLIC_KEY = "8bec051c2614356d4e25da7e2b1f5205ec68a1da45c62ea1a4ac0f73847f8de7"


def sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"source must be one regular non-symlink file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(*, root: Path, output: Path) -> str:
    ceremony = root / "docs/research/neurips-2026-workshop/evidence/official-study-ceremony"
    c120 = root / "docs/research/neurips-2026-workshop/evidence/step5b-c120-g-roster-final-20260801"
    precommit = ceremony / "precommit.json"
    bundle = ceremony / "precommit.sigstore.json"
    closure = c120 / "closure.json"
    program = root / "scripts/research/official_study_roster_selection.mjs"
    verifier = root / "scripts/research/verify_official_study_sigstore.py"
    precommit_value = json.loads(precommit.read_text(encoding="utf-8"))
    if precommit_value.get("study_id") != "neurips-2026-resampling-null" or precommit_value.get("beacon_chain_hash") != CHAIN or precommit_value.get("beacon_round") != 6355105:
        raise ValueError("frozen precommit differs from the registered ceremony target")
    if sha(closure) != precommit_value["qualification_universe_sha256"]:
        raise ValueError("qualification closure does not match the frozen precommit")
    if sha(bundle) == sha(precommit):
        raise ValueError("Sigstore anchor must be a distinct bundle")
    record: dict[str, Any] = {
        "record_kind": "resampling_roster_ceremony_policy_v1",
        "schema_version": "1",
        "study_id": "neurips-2026-resampling-null",
        "qualification_universe_sha256": sha(closure),
        "selection_program_sha256": sha(program),
        "precommit_sha256": sha(precommit),
        "drand": {"chain_hash": CHAIN, "scheme": "pedersen-bls-chained", "client_version": "drand-client==1.4.2", "group_hash": GROUP, "genesis_time": 1595431050, "period": 30},
        "sigstore": {"contract_id": "sigstore-bundle-verification-v1", "verifier_source_sha256": sha(verifier), "required_rekor_log": "rekor-public-good", "bundle_format": "sigstore-bundle-v0.3"},
        "node": {"contract_id": "node-roster-selection-v1", "program_sha256": sha(program), "runtime": "nodejs-22", "output_schema": "resampling-eligibility-manifest-v1"},
        "public_key_ed25519_hex": PUBLIC_KEY,
    }
    payload = canonical_json_bytes(record, indent=None)
    output.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(output, flags, 0o644)
    try:
        view = memoryview(payload)
        while view:
            view = view[os.write(descriptor, view):]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return hashlib.sha256(payload).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps({"policy_sha256": freeze(root=args.root.resolve(), output=args.output.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

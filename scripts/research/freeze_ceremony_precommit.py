"""Freeze the real, unsigned roster-ceremony precommit.

This command only commits already-registered inputs and fresh private
commitments. It never contacts Sigstore, Rekor, drand, AWS, or a benchmark.
The output is refused if it already exists, so the bytes can be externally
timestamped without a later local rewrite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import time
from typing import Any

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.assignment import (
    BytesField,
    U64Field,
    commitment_sha256,
)


CHAIN_HASH = "8990e7a9aaed2ffed73dbd7092123d6f289930540d7651336225dc172e51b2ce"
GENESIS_TIME = 1595431050
PERIOD = 30
PREFERRED_FUTURE_ROUNDS = 5760


def _sha256_file(path: Path) -> str:
    resolved = path.resolve(strict=True)
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError(f"source must be a regular non-symlink file: {path}")
    return hashlib.sha256(resolved.read_bytes()).hexdigest()


def _write_exclusive(path: Path, payload: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, mode)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor != -1:
            os.close(descriptor)


def freeze_precommit(
    *,
    study_id: str,
    qualification_source: Path,
    output: Path,
    secret_store: Path,
    now_unix: int | None = None,
) -> tuple[str, int]:
    if type(study_id) is not str or not study_id:
        raise ValueError("study_id must be non-empty text")
    qualification_sha256 = _sha256_file(qualification_source)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing to rewrite frozen precommit: {output}")
    if secret_store.exists() or secret_store.is_symlink():
        raise FileExistsError(f"refusing to rewrite private ceremony material: {secret_store}")

    nonce = secrets.token_bytes(32)
    schedule_seed = int.from_bytes(secrets.token_bytes(8), "big")
    assignment_master_key = secrets.token_bytes(32)
    commitments = {
        "roster_local_nonce_commitment_sha256": commitment_sha256(
            "roster-local-nonce", study_id, BytesField(nonce)
        ),
        "schedule_seed_commitment_sha256": commitment_sha256(
            "schedule-seed", study_id, U64Field(schedule_seed)
        ),
        "assignment_master_key_commitment_sha256": commitment_sha256(
            "assignment-master-key", study_id, BytesField(assignment_master_key)
        ),
    }
    current = int(time.time()) if now_unix is None else now_unix
    current_round = math.floor((current - GENESIS_TIME) / PERIOD)
    beacon_round = max(current_round + 1, current_round + PREFERRED_FUTURE_ROUNDS)
    precommit: dict[str, Any] = {
        "assignment_master_key_commitment_sha256": commitments[
            "assignment_master_key_commitment_sha256"
        ],
        "beacon_chain_hash": CHAIN_HASH,
        "beacon_round": beacon_round,
        "qualification_universe_sha256": qualification_sha256,
        "roster_local_nonce_commitment_sha256": commitments[
            "roster_local_nonce_commitment_sha256"
        ],
        "schedule_seed_commitment_sha256": commitments[
            "schedule_seed_commitment_sha256"
        ],
        "study_id": study_id,
    }
    payload = canonical_json_bytes(precommit, indent=None)
    private_payload = canonical_json_bytes(
        {
            "record_kind": "resampling_roster_precommit_private_material_v1",
            "schema_version": "1",
            "study_id": study_id,
            "precommit_sha256": hashlib.sha256(payload).hexdigest(),
            "roster_local_nonce_hex": nonce.hex(),
            "schedule_seed": schedule_seed,
            "assignment_master_key_hex": assignment_master_key.hex(),
        },
        indent=None,
    )
    _write_exclusive(secret_store, private_payload, 0o600)
    try:
        _write_exclusive(output, payload, 0o644)
    except Exception:
        secret_store.unlink(missing_ok=True)
        raise
    return hashlib.sha256(payload).hexdigest(), beacon_round


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-id", default="neurips-2026-resampling-null")
    parser.add_argument("--qualification-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--secret-store", type=Path, required=True)
    args = parser.parse_args()
    digest, round_number = freeze_precommit(
        study_id=args.study_id,
        qualification_source=args.qualification_source,
        output=args.output,
        secret_store=args.secret_store,
    )
    print(json.dumps({"precommit_sha256": digest, "beacon_round": round_number}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

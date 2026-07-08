"""Dataset-agnostic PneumaTrace envelope helpers.

Deterministic by construction: canonical JSON, identity ids, and a content hash
that excludes self-referential fields. No wall-clock, no randomness.
"""

from __future__ import annotations

import copy
import hashlib
import json

SCHEMA_VERSION = "0.1.0"
ENVELOPE_SCHEMA_FILE = "pneuma-trace.schema.json"


def canonical_json(obj) -> str:
    """Byte-stable JSON: sorted keys, compact separators, UTF-8, no ASCII escaping."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _identity_hash(dataset: str, instance_id: str, hf_revision: str) -> str:
    payload = f"{dataset}\x00{instance_id}\x00{hf_revision}".encode("utf-8")
    return hashlib.blake2b(payload, digest_size=16).hexdigest()


def derive_ids(dataset: str, instance_id: str, hf_revision: str) -> dict[str, str]:
    """Sibling ids from one identity hash: trace (artifact) + run (execution)."""
    h = _identity_hash(dataset, instance_id, hf_revision)
    return {"trace_id": f"ptrace:{h}", "run_id": f"run:{h}"}


def content_hash(trace: dict) -> str:
    """Integrity hash over the trace with build.content_hash blanked and no validation."""
    clone = copy.deepcopy(trace)
    if isinstance(clone.get("build"), dict):
        clone["build"]["content_hash"] = ""
    clone.pop("validation", None)
    return hashlib.blake2b(
        canonical_json(clone).encode("utf-8"), digest_size=32
    ).hexdigest()


__all__ = [
    "SCHEMA_VERSION",
    "ENVELOPE_SCHEMA_FILE",
    "canonical_json",
    "derive_ids",
    "content_hash",
]

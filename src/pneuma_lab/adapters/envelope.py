"""Dataset-agnostic PneumaTrace envelope helpers.

Deterministic by construction: canonical JSON, identity ids, and a content hash
that excludes self-referential fields. No wall-clock, no randomness.
"""

from __future__ import annotations

import copy
import hashlib
import json
from functools import lru_cache

from jsonschema import Draft202012Validator

from pneuma_lab.schemas import load_schema

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


@lru_cache(maxsize=1)
def _envelope_validator() -> Draft202012Validator:
    return Draft202012Validator(load_schema(ENVELOPE_SCHEMA_FILE))


def envelope_errors(trace: dict) -> list[str]:
    """Human-readable envelope-schema errors (empty list = valid)."""
    if not isinstance(trace, dict):
        return [f"trace is not an object: {type(trace).__name__}"]
    out: list[str] = []
    for err in sorted(
        _envelope_validator().iter_errors(trace), key=lambda e: list(e.path)
    ):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        out.append(f"{loc}: {err.message}")
    return out


__all__ = [
    "SCHEMA_VERSION",
    "ENVELOPE_SCHEMA_FILE",
    "canonical_json",
    "derive_ids",
    "content_hash",
    "envelope_errors",
]

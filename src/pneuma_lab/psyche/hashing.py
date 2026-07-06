"""Deterministic hashing + ID minting for auditable, replayable frames.

Determinism is a hard Phase-1 requirement (evaluation-guide Layer H: "deterministic
replay"). Two rules make it hold:

    1. State hashes are computed from *canonical* JSON — keys sorted, floats
    rounded to a fixed precision so 1e-9 arithmetic jitter never changes a hash.
    2. Frame IDs are derived from ``(run_id, tick_index, kind, ordinal)`` — never
    from wall-clock time or randomness.

Same inputs in ⇒ same hashes and IDs out ⇒ an external auditor can re-run the
replay and diff the bytes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# Round floats to this many decimals before hashing. Well below any meaningful
# psyche resolution, but above float round-trip noise.
_FLOAT_PRECISION = 6


def _canonicalize(obj: Any) -> Any:
    """Recursively round floats so hashing is stable against tiny fp jitter."""
    if isinstance(obj, float):
        # Normalize -0.0 to 0.0 and round; keep as float for JSON.
        rounded = round(obj, _FLOAT_PRECISION)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(obj, dict):
        return {k: _canonicalize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_canonicalize(v) for v in obj]
    return obj


def canonical_json(obj: Any) -> str:
    """Deterministic JSON string: sorted keys, no whitespace, rounded floats."""
    return json.dumps(
        _canonicalize(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def state_hash(obj: Any) -> str:
    """Content hash of ``obj`` as ``"sha256:<hex>"`` (stable across runs)."""
    digest = hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def frame_id(run_id: str, tick_index: int, kind: str, ordinal: int = 0) -> str:
    """Stable, human-readable frame id: ``<run>:<tick>:<kind>:<ordinal>``."""
    return f"{run_id}:{tick_index}:{kind}:{ordinal}"


__all__ = ["canonical_json", "state_hash", "frame_id"]

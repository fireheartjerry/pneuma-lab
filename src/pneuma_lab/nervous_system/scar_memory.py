"""Small persistent scar/memory store for the baseline psyche subject.

Deterministic JSON on disk: sorted keys, rounded floats. This is the cross-run
memory the subject seeds from and writes back to; it is NOT the per-tick input
MemoryFrame (which is read-only observation).
"""

from __future__ import annotations

import json
from pathlib import Path


def load(path) -> dict:
    """Load the scar store, or {} when absent."""
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save(path, scars: dict) -> None:
    """Persist the scar store deterministically."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rounded = {k: round(float(v), 6) for k, v in sorted(scars.items())}
    p.write_text(json.dumps(rounded, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def motif_of(memory_frame):
    """Return (motif_id, similarity) for the strongest scar match, else None."""
    if not isinstance(memory_frame, dict):
        return None
    matches = memory_frame.get("scar_motif_matches") or []
    best = None
    for m in matches:
        sim = float(m.get("similarity", 0.0))
        motif = m.get("motif_id")
        if motif is None:
            continue
        if best is None or sim > best[1] or (sim == best[1] and motif < best[0]):
            best = (motif, sim)
    return best

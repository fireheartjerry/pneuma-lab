"""Deterministic writers for the thought stream: stream.md / .jsonl / sidecar.json.

Byte-determinism uses the same recipe as demo.py: json.dumps(sort_keys=True,
ensure_ascii=False), explicit '\\n' newlines, no wall-clock values.
"""

from __future__ import annotations

import json
from pathlib import Path


def _json_text(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _jsonl_text(rows: list[dict]) -> str:
    return "".join(
        json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows
    )


def render_markdown(stream: dict) -> str:
    """Human transcript: one section per tick, each rendered line + its atom type."""
    lines: list[str] = [
        f"# Pneuma Voice — {stream['subject']} (evidence level {stream['evidence_level']})",
        "",
    ]
    by_tick: dict[int, list[tuple[dict, dict]]] = {}
    for atom, rendered in zip(stream["atoms"], stream["rendered"]):
        by_tick.setdefault(atom["tick"], []).append((atom, rendered))
    for tick in sorted(by_tick):
        lines.append(f"## Tick {tick}")
        lines.append("")
        for atom, rendered in by_tick[tick]:
            lines.append(
                f"- _{atom['type']}_ ({atom['credit_status']}): {rendered['text_deterministic']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def write_transcript(stream: dict, out_dir: str | Path) -> None:
    """Write stream.md, stream.jsonl (atoms), and sidecar.json deterministically."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "stream.md").write_text(
        render_markdown(stream), encoding="utf-8", newline="\n"
    )
    (out / "stream.jsonl").write_text(
        _jsonl_text(stream["atoms"]), encoding="utf-8", newline="\n"
    )
    (out / "sidecar.json").write_text(
        _json_text(stream["sidecar"]), encoding="utf-8", newline="\n"
    )


__all__ = ["render_markdown", "write_transcript"]

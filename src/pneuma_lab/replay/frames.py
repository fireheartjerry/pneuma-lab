"""Frame IO + tick grouping for the replay harness.

Input frames are recorded as JSON Lines (one frame object per line). A *tick* is
the unit the psyche consumes: exactly one ``WorldFrame`` plus whatever
``AgentTraceFrame`` / ``MemoryFrame`` / ``GovernanceFrame`` / ``InterventionFrame``
accompany it (share its ``run_id`` and immediately precede/follow it before the
next world frame). Governance is *sticky*: once seen it carries forward to later
ticks until replaced, matching how an operator constitution persists across a run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


def load_jsonl(path: str | Path) -> list[dict]:
    """Load a JSONL file into a list of frame dicts (blank lines skipped)."""
    frames: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                frames.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
    return frames


def dump_jsonl(frames: list[dict], path: str | Path) -> None:
    """Write frame dicts to a JSONL file (deterministic: sorted keys)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="\n") as fh:
        for frame in frames:
            fh.write(json.dumps(frame, sort_keys=True, ensure_ascii=False))
            fh.write("\n")


@dataclass
class Tick:
    """One unit of replay: a world frame plus its accompanying input frames."""

    index: int
    world: dict
    agent_trace: dict | None = None
    memory: dict | None = None
    governance: dict | None = None
    interventions: list[dict] = field(default_factory=list)


def group_into_ticks(frames: list[dict]) -> list[Tick]:
    """Group a flat input-frame stream into ordered ticks.

    A ``world`` frame opens a new tick. Any ``agent_trace``/``memory``/
    ``governance``/``intervention`` frames are attached to the current (most
    recent) world frame. Governance is sticky across ticks until replaced.
    """
    ticks: list[Tick] = []
    sticky_governance: dict | None = None
    current: Tick | None = None

    for frame in frames:
        kind = frame.get("frame_kind")
        if kind == "world":
            current = Tick(index=len(ticks), world=frame, governance=sticky_governance)
            ticks.append(current)
        elif kind == "governance":
            sticky_governance = frame
            if current is not None:
                current.governance = frame
        elif current is None:
            # Pre-world frames (e.g. an opening governance handled above); ignore
            # a stray trace/memory that has no world to attach to.
            continue
        elif kind == "agent_trace":
            current.agent_trace = frame
        elif kind == "memory":
            current.memory = frame
        elif kind == "intervention":
            current.interventions.append(frame)
    return ticks


__all__ = ["load_jsonl", "dump_jsonl", "Tick", "group_into_ticks"]

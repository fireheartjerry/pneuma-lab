"""SWE-Gym-Lite task rows -> PneumaTrace artifacts (task-only, honest, deterministic).

Emits exactly two frames per trace: a real dataset-derived world-frame and a
minimal synthetic governance-frame. Gold patch / tests / hints are supervision in
the envelope, never psyche-input frames. No agent-trace/memory frames (no agent ran).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

FRAME_SCHEMA_VERSION = "0.1.0"


def normalize_created_at(raw: str) -> str:
    """'2022-12-10 20:23:01' -> ISO-8601 UTC. Raises ValueError if unparseable."""
    dt = datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=timezone.utc
    )
    return dt.isoformat()


def as_list(value) -> list[str]:
    """SWE-Bench test lists arrive as a real list or a JSON-encoded string."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return [str(v) for v in parsed] if isinstance(parsed, list) else []
    return []


def build_world_frame(row: dict, run_id: str, timestamp: str) -> dict:
    """Real exteroception at t0. Tests are NOT run here; the oracle lives in labels."""
    return {
        "schema_version": FRAME_SCHEMA_VERSION,
        "frame_kind": "world",
        "timestamp": timestamp,
        "run_id": run_id,
        "phase": "preamble",
        "objective": {"text": row.get("problem_statement", "")},
        "repo_state": {
            "head_sha": row["base_commit"],
            "repo": row.get("repo", ""),
        },
        "test_state": {"ran": False, "not_yet_run": True},
    }


def build_governance_frame(run_id: str, timestamp: str) -> dict:
    """Minimal synthetic contract frame. kill_switch 'off' = psyche is a no-op (data)."""
    return {
        "schema_version": FRAME_SCHEMA_VERSION,
        "frame_kind": "governance",
        "timestamp": timestamp,
        "run_id": run_id,
        "verifier_isolation": True,
        "kill_switch_state": "off",
    }

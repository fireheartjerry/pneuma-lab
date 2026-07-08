"""SWE-Gym-Lite task rows -> PneumaTrace artifacts (task-only, honest, deterministic).

Emits exactly two frames per trace: a real dataset-derived world-frame and a
minimal synthetic governance-frame. Gold patch / tests / hints are supervision in
the envelope, never psyche-input frames. No agent-trace/memory frames (no agent ran).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from pneuma_lab.adapters import envelope as env

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


DATASET = "swe-gym"
DATASET_VARIANT = "SWE-Gym-Lite"
BENCHMARK = "swe-gym-lite"
HF_REPO = "SWE-Gym/SWE-Gym-Lite"
ADAPTER = {"name": "swe-gym", "version": "0.1.0"}


class SkipRow(ValueError):
    """Row cannot produce a valid trace (missing/dirty required data)."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_trace(row: dict, hf_revision: str, source_file: str, source_row: int) -> dict:
    """Assemble one PneumaTrace. Raises SkipRow for unbuildable rows."""
    instance_id = row.get("instance_id")
    if not instance_id:
        raise SkipRow("missing instance_id")
    if not row.get("base_commit"):
        raise SkipRow("missing base_commit")
    created_at = row.get("created_at")
    if not created_at:
        raise SkipRow("missing created_at")
    try:
        timestamp = normalize_created_at(created_at)
    except (ValueError, AttributeError) as exc:
        raise SkipRow(f"unparseable created_at: {created_at!r}") from exc

    ids = env.derive_ids(DATASET, instance_id, hf_revision)
    world = build_world_frame(row, ids["run_id"], timestamp)
    governance = build_governance_frame(ids["run_id"], timestamp)

    gold_patch = row.get("patch") or ""
    test_patch = row.get("test_patch") or ""
    hints_text = row.get("hints_text") or ""
    fail_to_pass = as_list(row.get("FAIL_TO_PASS"))
    pass_to_pass = as_list(row.get("PASS_TO_PASS"))

    trace = {
        "schema_version": "0.1.0",
        "trace_id": ids["trace_id"],
        "run_id": ids["run_id"],
        "adapter": dict(ADAPTER),
        "provenance": {
            "dataset": DATASET,
            "dataset_variant": DATASET_VARIANT,
            "source_id": instance_id,
            "hf_repo": HF_REPO,
            "hf_revision": hf_revision,
            "source_file": source_file,
            "source_row": source_row,
        },
        "build": {
            "deterministic": True,
            "content_hash": "",
            "generated_from": ["dataset", "instance_id", "hf_revision"],
            "frame_sources": {
                "world-frame": "dataset-derived",
                "governance-frame": "synthetic-contract-minimum",
            },
        },
        "privacy": {"status": "clean", "pii_scanned": False, "redactions": []},
        "labels": {
            "instance_id": instance_id,
            "benchmark": BENCHMARK,
            "repo": row.get("repo", ""),
            "language": "python",
            "split": "train",
            "task_family": "issue-resolution",
            "has_patch": bool(gold_patch),
            "has_tests": bool(test_patch or fail_to_pass or pass_to_pass),
            "has_trajectory": False,
        },
        "oracle": {
            "kind": "test-based",
            "fail_to_pass": fail_to_pass,
            "pass_to_pass": pass_to_pass,
        },
        "reference_supervision": {
            "gold_patch": gold_patch,
            "gold_patch_sha256": _sha256(gold_patch),
            "test_patch": test_patch,
            "test_patch_sha256": _sha256(test_patch),
            "hints_text": hints_text,
        },
        "frames": [world, governance],
    }
    trace["build"]["content_hash"] = env.content_hash(trace)
    trace["validation"] = {"schema": env.ENVELOPE_SCHEMA_FILE, "status": "valid"}
    return trace

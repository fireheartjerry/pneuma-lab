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


# frame_sources values that mark a frame as coming from a real recording rather
# than adapter synthesis. Anything else on a cognition-bearing frame kind is
# treated as fabricated cognition and rejected.
TRAJECTORY_SOURCE = "dataset-derived-trajectory"
_COGNITION_FRAME_KINDS = {"agent_trace": "agent-trace-frame", "memory": "memory-frame"}


def consistency_errors(trace: dict) -> list[str]:
    """Anti-fake-cognition cross-checks the JSON Schema cannot express.

    Rules (v0.2 envelope contract):
      * agent_trace frames are allowed ONLY when a real trajectory exists:
        ``trajectory`` block present, ``labels.has_trajectory`` true, and
        ``build.frame_sources['agent-trace-frame'] == 'dataset-derived-trajectory'``;
      * ``trajectory.num_agent_steps`` must equal the number of agent_trace frames;
      * a task-only trace (no trajectory block) must carry NO agent_trace or
        memory frames and must not claim ``has_trajectory``;
      * memory frames likewise require a real recorded source declared in
        ``frame_sources['memory-frame']``.
    """
    if not isinstance(trace, dict):
        return [f"trace is not an object: {type(trace).__name__}"]
    out: list[str] = []
    frames = trace.get("frames") or []
    labels = trace.get("labels") or {}
    sources = (trace.get("build") or {}).get("frame_sources") or {}
    trajectory = trace.get("trajectory")
    has_traj_label = labels.get("has_trajectory") is True
    n_agent = sum(
        1
        for f in frames
        if isinstance(f, dict) and f.get("frame_kind") == "agent_trace"
    )
    n_memory = sum(
        1 for f in frames if isinstance(f, dict) and f.get("frame_kind") == "memory"
    )

    if trajectory is not None:
        if not has_traj_label:
            out.append(
                "trajectory: block present but labels.has_trajectory is not true"
            )
        if n_agent == 0:
            out.append("trajectory: block present but no agent_trace frame emitted")
        declared = trajectory.get("num_agent_steps")
        if declared != n_agent:
            out.append(
                f"trajectory: num_agent_steps={declared!r} but "
                f"{n_agent} agent_trace frame(s) present"
            )
    else:
        if has_traj_label:
            out.append("labels: has_trajectory is true but no trajectory block exists")
        if n_agent:
            out.append(
                f"frames: {n_agent} agent_trace frame(s) present without a real "
                "trajectory block (fabricated cognition)"
            )

    if n_agent and sources.get("agent-trace-frame") != TRAJECTORY_SOURCE:
        out.append(
            "build.frame_sources: agent-trace-frame must be declared "
            f"'{TRAJECTORY_SOURCE}' when agent_trace frames are present"
        )
    if n_memory and sources.get("memory-frame") != TRAJECTORY_SOURCE:
        out.append(
            "build.frame_sources: memory-frame must be declared "
            f"'{TRAJECTORY_SOURCE}' when memory frames are present"
        )
    return out


__all__ = [
    "SCHEMA_VERSION",
    "ENVELOPE_SCHEMA_FILE",
    "TRAJECTORY_SOURCE",
    "canonical_json",
    "derive_ids",
    "content_hash",
    "envelope_errors",
    "consistency_errors",
]

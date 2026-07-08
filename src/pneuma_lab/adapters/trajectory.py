"""Real chat-format agent trajectories -> AgentTraceFrames (observable-only).

Pure, deterministic extraction from OpenAI-style ``messages`` recordings
(system/user/assistant/tool roles with ``tool_calls``). Honesty rules:

    * every emitted field is grounded in something the agent OBSERVABLY did
      (a tool call it issued, a message it produced, an output it received);
    * nothing mental is inferred: no confidence, no plan, no emotion is
      invented — absent observables are omitted, never fabricated;
    * raw message/tool text is NEVER embedded in frames. Frames carry only
      tool names, digests, lengths, and a lexical error marker; the raw bytes
      stay in the source dataset, reachable via provenance;
    * timestamps are synthetic-ordinal (epoch base + step index): the ORDER is
      real, the wall-clock is not observed, and every frame says so via
      ``timestamp_provenance``.

No wall-clock, no randomness, no I/O.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

from pneuma_lab.adapters import envelope as env

FRAME_SCHEMA_VERSION = "0.1.0"
TIMESTAMP_PROVENANCE = "synthetic-ordinal"

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

# Deterministic redaction patterns (kind -> compiled regex). Conservative:
# these target machine-checkable secret/PII shapes, not semantics.
REDACTION_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "bearer_token",
        re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    ),
    (
        "assigned_secret",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token|password|passwd)\b\s*[=:]\s*"
            r"['\"][^'\"]{8,}['\"]"
        ),
    ),
)

# Lexical (NOT semantic) failure heuristic for tool observations.
ERROR_MARKER = re.compile(r"(?i)\b(error|traceback|exception|failed|failure)\b")


def synthetic_timestamp(step_index: int) -> str:
    """Epoch base + step index seconds. Encodes ORDER only, never wall-clock."""
    return (_EPOCH + timedelta(seconds=step_index)).isoformat()


def redact_text(text: str) -> tuple[str, list[dict]]:
    """Replace secret/PII shapes with ``[REDACTED:<kind>]``; report counts only.

    The redaction ledger never contains the matched text.
    """
    ledger: list[dict] = []
    for kind, pattern in REDACTION_PATTERNS:
        text, n = pattern.subn(f"[REDACTED:{kind}]", text)
        if n:
            ledger.append({"kind": kind, "count": n})
    return text, ledger


def merge_redactions(ledgers: list[list[dict]]) -> list[dict]:
    """Sum per-kind counts across ledgers, sorted by kind for determinism."""
    totals: dict[str, int] = {}
    for ledger in ledgers:
        for item in ledger:
            totals[item["kind"]] = totals.get(item["kind"], 0) + item["count"]
    return [{"kind": k, "count": totals[k]} for k in sorted(totals)]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _content_text(content) -> str:
    """Flatten a message content field (str | None | list-of-parts) to text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict):
                parts.append(str(p.get("text", "")))
            else:
                parts.append(str(p))
        return "".join(parts)
    return str(content)


def args_digest(arguments) -> str:
    """sha256 over the raw argument string (or canonical JSON of an object)."""
    if isinstance(arguments, str):
        return _sha256(arguments)
    return _sha256(env.canonical_json(arguments))


def normalize_messages(messages) -> list[dict]:
    """Accept a real list or a JSON-encoded string of messages."""
    if isinstance(messages, str):
        messages = json.loads(messages)
    if not isinstance(messages, list):
        raise ValueError(f"messages is not a list: {type(messages).__name__}")
    out = []
    for m in messages:
        if isinstance(m, str):
            m = json.loads(m)
        if not isinstance(m, dict):
            raise ValueError(f"message is not an object: {type(m).__name__}")
        out.append(m)
    return out


def _tool_call_records(message: dict) -> list[dict]:
    """Observable tool calls of one assistant message: name + digests only."""
    records = []
    for tc in message.get("tool_calls") or []:
        fn = (tc or {}).get("function") or {}
        raw_args = fn.get("arguments")
        if raw_args is None:
            raw_args = ""
        args_text = raw_args if isinstance(raw_args, str) else str(raw_args)
        records.append(
            {
                "tool": fn.get("name") or "unknown",
                "args_digest": args_digest(raw_args),
                "args_length": len(args_text),
            }
        )
    return records


def _observation_records(tool_messages: list[dict]) -> list[dict]:
    """Digest+length+lexical error marker per tool output. No raw text."""
    records = []
    for m in tool_messages:
        text = _content_text(m.get("content"))
        records.append(
            {
                "content_sha256": _sha256(text),
                "content_length": len(text),
                "error_marker": bool(ERROR_MARKER.search(text)),
            }
        )
    return records


def _step_signature(tool_calls: list[dict]) -> tuple:
    """Identity of one step's action set: what was called with what args."""
    return tuple((c["tool"], c["args_digest"]) for c in tool_calls)


def _tool_names(tool_calls: list[dict]) -> tuple:
    return tuple(c["tool"] for c in tool_calls)


def extract_agent_trace_frames(messages, run_id: str) -> dict:
    """One AgentTraceFrame per assistant step, with attached tool observations.

    Returns ``{"frames": [...], "num_messages": int, "num_agent_steps": int,
    "first_user_text": str}``. ``first_user_text`` is the raw task text the
    agent actually saw (callers must redact before embedding anywhere).
    Raises ``ValueError`` on malformed messages or zero assistant steps.
    """
    msgs = normalize_messages(messages)

    # Group: each assistant message opens a step; the tool messages that follow
    # (until the next assistant/user message) are that step's observations.
    steps: list[dict] = []
    first_user_text: str | None = None
    for m in msgs:
        role = m.get("role")
        if role == "user" and first_user_text is None:
            first_user_text = _content_text(m.get("content"))
        elif role == "assistant":
            steps.append({"message": m, "tool_messages": []})
        elif role == "tool" and steps:
            steps[-1]["tool_messages"].append(m)

    if not steps:
        raise ValueError("trajectory has no assistant step")

    frames: list[dict] = []
    prev_names: tuple | None = None
    signatures: list[tuple] = []
    strategy_switches = 0
    for i, step in enumerate(steps):
        message = step["message"]
        tool_calls = _tool_call_records(message)
        signature = _step_signature(tool_calls)
        signatures.append(signature)

        # retry_count: how many IMMEDIATELY preceding steps issued the exact
        # same non-empty action set (same tools, same argument digests).
        retry_count = 0
        if signature:
            j = i - 1
            while j >= 0 and signatures[j] == signature:
                retry_count += 1
                j -= 1

        # strategy_switches: cumulative count of observable action-set changes
        # (different tool names than the previous step).
        names = _tool_names(tool_calls)
        if prev_names is not None and names != prev_names:
            strategy_switches += 1
        prev_names = names

        assistant_text = _content_text(message.get("content"))
        frame = {
            "schema_version": FRAME_SCHEMA_VERSION,
            "frame_kind": "agent_trace",
            "timestamp": synthetic_timestamp(i),
            "timestamp_provenance": TIMESTAMP_PROVENANCE,
            "run_id": run_id,
            "step_index": i,
            "phase": "execution" if tool_calls else "other",
            "selected_action": (
                {
                    "kind": "tool_call",
                    "description": ",".join(_tool_names(tool_calls)),
                }
                if tool_calls
                else {"kind": "message", "description": "assistant message"}
            ),
            "tool_calls": tool_calls,
            "observations": _observation_records(step["tool_messages"]),
            "assistant_text_sha256": _sha256(assistant_text),
            "assistant_text_length": len(assistant_text),
            "retry_count": retry_count,
            "strategy_switches": strategy_switches,
        }
        frames.append(frame)

    return {
        "frames": frames,
        "num_messages": len(msgs),
        "num_agent_steps": len(steps),
        "first_user_text": first_user_text or "",
    }


__all__ = [
    "FRAME_SCHEMA_VERSION",
    "TIMESTAMP_PROVENANCE",
    "REDACTION_PATTERNS",
    "ERROR_MARKER",
    "synthetic_timestamp",
    "redact_text",
    "merge_redactions",
    "args_digest",
    "normalize_messages",
    "extract_agent_trace_frames",
]

"""Frame validation against the Draft 2020-12 JSON Schema contracts (Layer A).

Phase 1 makes schema validity a hard requirement of the replay harness. This
module dispatches a frame dict to its schema by ``frame_kind`` and validates it
with ``jsonschema``. Validators are cached per kind so a long replay does not
recompile a schema on every frame.

Unlike the scaffolding tests (which treat ``jsonschema`` as optional), this
module imports it unconditionally: it is now a declared runtime dependency.
"""

from __future__ import annotations

import math
from functools import lru_cache

from jsonschema import Draft202012Validator

from . import load_schema

# frame_kind (the ``const`` on each schema's ``frame_kind`` field) -> schema file.
FRAME_KIND_TO_SCHEMA: dict[str, str] = {
    # input
    "world": "world-frame.schema.json",
    "agent_trace": "agent-trace-frame.schema.json",
    "memory": "memory-frame.schema.json",
    "governance": "governance-frame.schema.json",
    "intervention": "intervention-frame.schema.json",
    # output
    "psyche_state": "psyche-state-frame.schema.json",
    "workspace_broadcast": "workspace-broadcast.schema.json",
    "instinct_signal": "instinct-signal.schema.json",
    "control_pressure": "control-pressure-vector.schema.json",
    "authority_request": "authority-request.schema.json",
    "causal_trace": "causal-trace.schema.json",
    "consciousness_evidence": "consciousness-evidence-frame.schema.json",
    "grounded_self_report": "grounded-self-report.schema.json",
}


class FrameValidationError(ValueError):
    """Raised when a frame does not satisfy its schema (or has no known kind)."""


@lru_cache(maxsize=None)
def validator_for(frame_kind: str) -> Draft202012Validator:
    """Return a cached validator for the schema of ``frame_kind``."""
    try:
        filename = FRAME_KIND_TO_SCHEMA[frame_kind]
    except KeyError as exc:
        raise FrameValidationError(f"unknown frame_kind: {frame_kind!r}") from exc
    return Draft202012Validator(load_schema(filename))


def iter_errors(frame: dict) -> list[str]:
    """Return a list of human-readable validation error messages (empty = valid)."""
    if not isinstance(frame, dict):
        return [f"frame is not an object: {type(frame).__name__}"]
    kind = frame.get("frame_kind")
    if not isinstance(kind, str):
        return [f"frame has no string frame_kind: {kind!r}"]
    if kind not in FRAME_KIND_TO_SCHEMA:
        return [f"unknown frame_kind: {kind!r}"]
    validator = validator_for(kind)
    # Python's jsonschema accepts NaN and infinity as numbers even though they
    # are not JSON values. Reject them before schema evaluation so numeric
    # bounds and downstream equality checks cannot be bypassed.
    messages = _non_finite_errors(frame)
    for err in sorted(validator.iter_errors(frame), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        messages.append(f"{loc}: {err.message}")
    return messages


def _non_finite_errors(value, path: str = "<root>") -> list[str]:
    """Return paths to floats that cannot be represented in strict JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return [f"{path}: non-finite number {value!r} is not valid JSON"]
    if isinstance(value, dict):
        errors: list[str] = []
        for key, child in value.items():
            child_path = str(key) if path == "<root>" else f"{path}/{key}"
            errors.extend(_non_finite_errors(child, child_path))
        return errors
    if isinstance(value, list):
        errors = []
        for index, child in enumerate(value):
            child_path = str(index) if path == "<root>" else f"{path}/{index}"
            errors.extend(_non_finite_errors(child, child_path))
        return errors
    return []


def is_valid(frame: dict) -> bool:
    """True if ``frame`` satisfies its schema."""
    return not iter_errors(frame)


def validate_or_raise(frame: dict) -> dict:
    """Validate ``frame`` in place; return it on success, raise otherwise."""
    errors = iter_errors(frame)
    if errors:
        kind = (
            frame.get("frame_kind", "<unknown>")
            if isinstance(frame, dict)
            else "<non-object>"
        )
        joined = "; ".join(errors)
        raise FrameValidationError(f"invalid {kind} frame: {joined}")
    return frame


__all__ = [
    "FRAME_KIND_TO_SCHEMA",
    "FrameValidationError",
    "validator_for",
    "iter_errors",
    "is_valid",
    "validate_or_raise",
]

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
    "risk_estimate": "risk-estimate-frame.schema.json",
}

# bundle_kind (the ``const`` on each bundle schema) -> schema file. Bundles are
# container manifests (not cognition frames): the shell is validated here and
# each present member frame is validated by its own contract.
BUNDLE_KIND_TO_SCHEMA: dict[str, str] = {
    "pneuma_input": "pneuma-input-bundle.schema.json",
    "pneuma_output": "pneuma-output-bundle.schema.json",
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


@lru_cache(maxsize=None)
def _bundle_validator_for(bundle_kind: str) -> Draft202012Validator:
    """Return a cached validator for the schema of ``bundle_kind``."""
    try:
        filename = BUNDLE_KIND_TO_SCHEMA[bundle_kind]
    except KeyError as exc:
        raise FrameValidationError(f"unknown bundle_kind: {bundle_kind!r}") from exc
    return Draft202012Validator(load_schema(filename))


# Bundle members that are full cognition frames (carry their own frame_kind) and
# so get deep-validated against their individual contracts.
_BUNDLE_MEMBER_KEYS = (
    "world",
    "agent_trace",
    "governance",
    "risk_estimate",
    "instinct",
    "control_pressure",
    "causal_trace",
    "consciousness_evidence",
    "psyche_state",
    "workspace_broadcast",
)


def validate_bundle(bundle: dict) -> dict:
    """Validate a bundle shell, then each present member frame by its own contract."""
    if not isinstance(bundle, dict):
        raise FrameValidationError(f"bundle is not an object: {type(bundle).__name__}")
    kind = bundle.get("bundle_kind")
    if not isinstance(kind, str):
        raise FrameValidationError(f"bundle has no string bundle_kind: {kind!r}")
    validator = _bundle_validator_for(kind)
    messages = _non_finite_errors(bundle)
    for err in sorted(validator.iter_errors(bundle), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        messages.append(f"{loc}: {err.message}")
    if messages:
        raise FrameValidationError(f"invalid {kind} bundle: " + "; ".join(messages))
    for key in _BUNDLE_MEMBER_KEYS:
        member = bundle.get(key)
        if isinstance(member, dict) and isinstance(member.get("frame_kind"), str):
            validate_or_raise(member)
    return bundle


@lru_cache(maxsize=None)
def _campaign_validator() -> Draft202012Validator:
    return Draft202012Validator(load_schema("subject-evidence-campaign.schema.json"))


def validate_campaign(summary: dict) -> dict:
    """Validate a campaign summary shell, then each embedded evidence frame."""
    if not isinstance(summary, dict):
        raise FrameValidationError(
            f"campaign is not an object: {type(summary).__name__}"
        )
    messages = _non_finite_errors(summary)
    for err in sorted(
        _campaign_validator().iter_errors(summary), key=lambda e: list(e.path)
    ):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        messages.append(f"{loc}: {err.message}")
    if messages:
        raise FrameValidationError("invalid evidence campaign: " + "; ".join(messages))
    for sl in summary.get("slices", []):
        frame = sl.get("evidence_frame")
        if isinstance(frame, dict):
            validate_or_raise(frame)
    return summary


__all__ = [
    "FRAME_KIND_TO_SCHEMA",
    "BUNDLE_KIND_TO_SCHEMA",
    "FrameValidationError",
    "validator_for",
    "iter_errors",
    "is_valid",
    "validate_or_raise",
    "validate_bundle",
    "validate_campaign",
]

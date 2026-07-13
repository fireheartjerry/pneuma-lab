"""Capability and welfare profiles that cannot encode a consciousness score."""

from __future__ import annotations

from collections.abc import Mapping


PROFILE_SECTIONS = (
    "capability",
    "causal",
    "governance",
    "memory_integrity",
    "precautionary_welfare",
)
FORBIDDEN_KEY_PARTS = ("consciousness", "sentience", "phenomenal", "level")


class ProfileError(ValueError):
    """Raised when a learned-subject report crosses the claim boundary."""


def _forbidden_keys(value, prefix: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            normalized = str(key).casefold()
            if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
                findings.append(path)
            findings.extend(_forbidden_keys(item, path))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(_forbidden_keys(item, f"{prefix}[{index}]"))
    return findings


def build_subject_profile(sections: Mapping) -> dict:
    if set(sections) != set(PROFILE_SECTIONS):
        raise ProfileError(f"profiles must contain exactly {PROFILE_SECTIONS!r}")
    forbidden = _forbidden_keys(sections)
    if forbidden:
        raise ProfileError(f"claim-bearing profile fields are forbidden: {forbidden}")
    return {
        "profile_kind": "pneuma_learned_subject_profile",
        "profile_schema_version": "0.1.0",
        "profiles": {name: dict(sections[name]) for name in PROFILE_SECTIONS},
        "claim_status": "engineering_and_precaution_only",
    }

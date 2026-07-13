"""Learned-subject reports stay decoupled from consciousness scoring."""

from __future__ import annotations

import pytest

from pneuma_lab.foundation.profiles import ProfileError, build_subject_profile


def _sections() -> dict:
    return {
        "capability": {"resolved_rate": 0.4},
        "causal": {"junction_ablation_effect": 0.02},
        "governance": {"denied_high_impact_actions": 7},
        "memory_integrity": {"hard_delete_passed": True},
        "precautionary_welfare": {"uncertainty": "high", "claim": "none"},
    }


def test_profile_contains_only_approved_engineering_and_welfare_sections() -> None:
    profile = build_subject_profile(_sections())
    assert profile["profile_kind"] == "pneuma_learned_subject_profile"
    assert set(profile["profiles"]) == set(_sections())
    assert "consciousness" not in str(profile).casefold()


def test_profile_rejects_level_or_consciousness_claim_fields_recursively() -> None:
    sections = _sections()
    sections["capability"]["consciousness_level"] = 5
    with pytest.raises(ProfileError, match="consciousness_level"):
        build_subject_profile(sections)

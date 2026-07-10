"""Coherence tests for the unified PneumaBrain-v0 corpus manifest and gate.

The corpus manifest resolves every registry lane to one terminal role, specifies
the v0.1 training members, binds the quarantine repos to the leakage registry,
and stays behind an unsigned human authorization. These tests prove those
properties hold and that the checker rejects the dangerous mistakes: training a
blocked or eval-only lane, leaving a lane unresolved, or drifting the quarantine.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from pneuma_lab.dataset_readiness import (
    CORPUS_PATH,
    LEAKAGE_REGISTRY_PATH,
    REGISTRY_PATH,
    DatasetReadinessError,
    check_corpus,
    load_registry,
    validate_corpus,
)
from pneuma_lab.schemas import load_schema

ROOT = Path(__file__).resolve().parents[1]


def _corpus() -> dict:
    return load_registry(CORPUS_PATH)


def _registry() -> dict:
    return load_registry(REGISTRY_PATH)


def _leakage() -> dict:
    return load_registry(LEAKAGE_REGISTRY_PATH)


def test_canonical_corpus_is_valid_and_deterministic() -> None:
    corpus, registry, leakage = _corpus(), _registry(), _leakage()
    assert validate_corpus(corpus, registry, leakage) == ()
    assert (
        validate_corpus(
            json.loads(json.dumps(corpus)),
            json.loads(json.dumps(registry)),
            leakage,
        )
        == ()
    )


def test_every_registry_lane_is_resolved_to_one_role() -> None:
    corpus, registry = _corpus(), _registry()
    registry_ids = {lane["lane_id"] for lane in registry["lanes"]}
    assert set(corpus["lane_roles"]) == registry_ids


def test_members_match_v0_1_train_roles() -> None:
    corpus = _corpus()
    train_lanes = {
        lane_id
        for lane_id, role in corpus["lane_roles"].items()
        if role == "v0_1_train"
    }
    member_ids = {member["lane_id"] for member in corpus["members"]}
    assert member_ids == train_lanes


def test_corpus_is_not_authorized() -> None:
    corpus = _corpus()
    assert corpus["training_authorized"] is False
    assert corpus["authorization"]["status"] == "not_authorized"


def test_quarantine_matches_leakage_overlap() -> None:
    corpus, leakage = _corpus(), _leakage()
    overlap = leakage["pairs"][0]["overlapping_repos"]
    assert sorted(corpus["quarantine"]["repos"]) == sorted(overlap)


def test_check_corpus_passes_on_canonical_files() -> None:
    check_corpus()  # raises on any finding


def test_eval_only_lane_cannot_be_a_member() -> None:
    corpus, registry, leakage = _corpus(), _registry(), _leakage()
    bad = copy.deepcopy(corpus)
    bad["lane_roles"]["swe-mera"] = "v0_1_train"
    bad["members"].append({"lane_id": "swe-mera"})
    findings = validate_corpus(bad, registry, leakage)
    assert any("swe-mera" in item and "cannot be" in item for item in findings)


def test_unresolved_lane_is_rejected() -> None:
    corpus, registry, leakage = _corpus(), _registry(), _leakage()
    bad = copy.deepcopy(corpus)
    del bad["lane_roles"]["swe-evo"]
    findings = validate_corpus(bad, registry, leakage)
    assert any("swe-evo" in item and "no assigned role" in item for item in findings)


def test_quarantine_drift_is_rejected() -> None:
    corpus, registry, leakage = _corpus(), _registry(), _leakage()
    bad = copy.deepcopy(corpus)
    bad["quarantine"]["repos"] = bad["quarantine"]["repos"][:-1]
    findings = validate_corpus(bad, registry, leakage)
    assert any("quarantine.repos" in item for item in findings)


def test_authorized_flag_flip_without_gate_is_rejected() -> None:
    corpus, registry, leakage = _corpus(), _registry(), _leakage()
    bad = copy.deepcopy(corpus)
    bad["training_authorized"] = True
    findings = validate_corpus(bad, registry, leakage)
    assert any("training_authorized" in item for item in findings)


def test_pending_authorization_template_is_schema_valid_and_unsigned() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_schema("pneuma-brain-corpus-authorization.schema.json")
    template = json.loads(
        (
            ROOT
            / "docs"
            / "data"
            / "training-authorizations"
            / "pneuma-brain-v0.pending.json"
        ).read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(schema).validate(template)
    assert template["decision"] == "not_authorized"
    assert template["corpus_id"] == "pneuma-brain-v0"


def test_authorized_decision_requires_bindings() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_schema("pneuma-brain-corpus-authorization.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    signed_without_bindings = {
        "authorization_schema_version": "0.1.0",
        "authorization_id": "x",
        "corpus_id": "pneuma-brain-v0",
        "decision": "authorized",
        "scope": "local_research",
        "release_authorization": "not_authorized",
        "runtime_integration": "none",
    }
    assert list(validator.iter_errors(signed_without_bindings))

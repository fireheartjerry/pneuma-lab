"""All-ten foundation suite policy and completeness-report tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from pneuma_lab import schemas as pls
from pneuma_lab.foundation.data import ACTIVE_DATASET_GROUPS
from pneuma_lab.foundation.suite import (
    SuitePolicyError,
    assert_payload_read_allowed,
    build_suite_completeness_report,
    load_suite_policy,
    validate_suite_policy,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/data/training-readiness/pneuma-foundation-v0-suite.json"
REGISTRY = ROOT / "docs/data/training-readiness/dataset-registry.json"


def _suite_fixture() -> dict:
    return load_suite_policy(POLICY)


def test_suite_has_exactly_ten_coherent_family_roles() -> None:
    policy = load_suite_policy(POLICY)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert validate_suite_policy(policy, registry) == ACTIVE_DATASET_GROUPS
    assert policy["first_stage"]["authorized_lane_candidates"] == [
        "swe-gym-openhands-sampled"
    ]


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown"])
def test_suite_family_membership_fails_closed(mutation: str) -> None:
    policy = _suite_fixture()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if mutation == "missing":
        policy["families"].pop()
    elif mutation == "duplicate":
        policy["families"][-1] = copy.deepcopy(policy["families"][0])
    else:
        policy["families"][-1]["family"] = "unknown-family"
    with pytest.raises(SuitePolicyError, match="each active family exactly once"):
        validate_suite_policy(policy, registry)


def test_suite_policy_shape_errors_are_domain_errors() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    policy = _suite_fixture()
    policy["families"][0] = "multi-swe-bench"
    with pytest.raises(SuitePolicyError, match="family entries must be objects"):
        validate_suite_policy(policy, registry)

    policy = _suite_fixture()
    policy["first_stage"].pop("authorized_lane_candidates")
    with pytest.raises(SuitePolicyError, match="authorized lane candidates"):
        validate_suite_policy(policy, registry)


def test_load_suite_policy_rejects_invalid_json_and_non_object(
    tmp_path: Path,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(SuitePolicyError, match="valid JSON"):
        load_suite_policy(malformed)

    non_object = tmp_path / "array.json"
    non_object.write_text("[]", encoding="utf-8")
    with pytest.raises(SuitePolicyError, match="JSON object"):
        load_suite_policy(non_object)


def test_payload_guard_denies_governance_lanes_before_open(tmp_path: Path) -> None:
    policy = _suite_fixture()
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        assert_payload_read_allowed(
            policy,
            stage="100k",
            family="sec-bench-pro",
            lane_id=None,
            path=tmp_path / "processed/sec-bench-pro/records.jsonl",
        )


def test_payload_guard_allows_only_the_approved_first_stage_lane(
    tmp_path: Path,
) -> None:
    policy = _suite_fixture()
    approved = tmp_path / "processed/swe-gym/openhands-sampled/records.jsonl"
    assert_payload_read_allowed(
        policy,
        stage="100k",
        family="swe-gym",
        lane_id="swe-gym-openhands-sampled",
        path=approved,
    )
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        assert_payload_read_allowed(
            policy,
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-verifier",
            path=approved,
        )


def test_payload_guard_allows_only_declared_identity_metadata(
    tmp_path: Path,
) -> None:
    policy = _suite_fixture()
    metadata = tmp_path / "processed/swe-bench/normalized_metadata.jsonl"
    assert_payload_read_allowed(
        policy,
        stage="100k",
        family="swe-bench",
        lane_id=None,
        path=metadata,
    )
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        assert_payload_read_allowed(
            policy,
            stage="100k",
            family="swe-bench",
            lane_id=None,
            path=tmp_path / "processed/swe-bench/records.jsonl",
        )


@pytest.mark.parametrize(
    ("stage", "family"),
    [("1m", "swe-gym"), ("100k", "unknown-family")],
)
def test_payload_guard_unknown_stage_or_family_fails_closed(
    tmp_path: Path,
    stage: str,
    family: str,
) -> None:
    with pytest.raises(SuitePolicyError):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage=stage,
            family=family,
            lane_id=None,
            path=tmp_path / "payload.jsonl",
        )


def test_completeness_report_is_schema_valid_and_lists_all_families(
    tmp_path: Path,
) -> None:
    report = build_suite_completeness_report(_suite_fixture(), tmp_path)
    schema = pls.load_schema("foundation-suite-report.schema.json")
    Draft202012Validator(schema).validate(report)
    assert tuple(item["family"] for item in report["families"]) == (
        ACTIVE_DATASET_GROUPS
    )
    assert all(item["payload_opened"] is False for item in report["families"])


def test_suite_report_schema_rejects_duplicate_family_and_extra_fields(
    tmp_path: Path,
) -> None:
    schema = pls.load_schema("foundation-suite-report.schema.json")
    validator = Draft202012Validator(schema)
    report = build_suite_completeness_report(_suite_fixture(), tmp_path)
    report["families"][-1] = copy.deepcopy(report["families"][0])
    with pytest.raises(ValidationError):
        validator.validate(report)

    report = build_suite_completeness_report(_suite_fixture(), tmp_path)
    report["unexpected"] = True
    with pytest.raises(ValidationError):
        validator.validate(report)

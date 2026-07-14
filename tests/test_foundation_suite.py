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

EXPECTED_FAMILY_MATRIX = {
    "multi-swe-bench": ("train", "later", "metadata_only", None),
    "open-swe-traces": ("train", "later", "metadata_only", None),
    "sec-bench-pro": ("governance", "never", "metadata_only", None),
    "swe-bench": (
        "eval",
        "never",
        "identity_metadata_only",
        "processed/swe-bench/normalized_metadata.jsonl",
    ),
    "swe-bench-pro": ("eval", "never", "metadata_only", None),
    "swe-chat": ("governance", "never", "metadata_only", None),
    "swe-evo": ("train", "later", "metadata_only", None),
    "swe-gym": ("train", "first_stage", "approved_processed_lane_only", None),
    "swe-mera": (
        "eval",
        "never",
        "identity_metadata_only",
        "processed/swe-mera/normalized_metadata.jsonl",
    ),
    "swe-polybench": (
        "eval",
        "later",
        "identity_metadata_only",
        "processed/swe-polybench/normalized_metadata.jsonl",
    ),
}


def _matrix_mutations() -> tuple[tuple[str, str, str], ...]:
    cases = []
    for family, (_role, _gradient, _access, identity_path) in (
        EXPECTED_FAMILY_MATRIX.items()
    ):
        for field in (
            "terminal_role",
            "gradient_eligibility",
            "payload_access_100k",
        ):
            for mutation in ("missing", "wrong_value", "wrong_type"):
                cases.append((family, field, mutation))
        if identity_path is None:
            cases.append((family, "identity_metadata_relative_path", "unexpected"))
        else:
            for mutation in ("missing", "wrong_value", "wrong_type"):
                cases.append((family, "identity_metadata_relative_path", mutation))
    return tuple(cases)


def _wrong_value(field: str) -> str:
    return {
        "terminal_role": "other",
        "gradient_eligibility": "sometimes",
        "payload_access_100k": "payload_allowed",
        "identity_metadata_relative_path": "processed/wrong/metadata.jsonl",
    }[field]


def _suite_fixture() -> dict:
    return load_suite_policy(POLICY)


def test_suite_has_exactly_ten_coherent_family_roles() -> None:
    policy = load_suite_policy(POLICY)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert validate_suite_policy(policy, registry) == ACTIVE_DATASET_GROUPS
    assert policy["first_stage"]["authorized_lane_candidates"] == [
        "swe-gym-openhands-sampled"
    ]


@pytest.mark.parametrize(
    ("family", "field", "mutation"),
    _matrix_mutations(),
    ids=lambda value: str(value),
)
def test_suite_requires_exact_family_policy_matrix(
    family: str,
    field: str,
    mutation: str,
) -> None:
    policy = _suite_fixture()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    item = next(entry for entry in policy["families"] if entry["family"] == family)
    if mutation == "missing":
        item.pop(field)
    elif mutation == "wrong_type":
        item[field] = ["wrong-type"]
    elif mutation == "unexpected":
        item[field] = f"processed/{family}/unexpected.jsonl"
    else:
        item[field] = _wrong_value(field)
    with pytest.raises(SuitePolicyError, match="exact policy matrix"):
        validate_suite_policy(policy, registry)


def test_suite_requires_documented_family_order() -> None:
    policy = _suite_fixture()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    policy["families"][0], policy["families"][1] = (
        policy["families"][1],
        policy["families"][0],
    )
    with pytest.raises(SuitePolicyError, match="documented order"):
        validate_suite_policy(policy, registry)


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


@pytest.mark.parametrize(
    "first_stage",
    [
        None,
        [],
        {
            "stage": 100_000,
            "authorized_lane_candidates": ["swe-gym-openhands-sampled"],
        },
        {"stage": "100k", "authorized_lane_candidates": "swe-gym-openhands-sampled"},
        {"stage": "100k", "authorized_lane_candidates": [123]},
    ],
)
def test_suite_rejects_malformed_first_stage(first_stage: object) -> None:
    policy = _suite_fixture()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    policy["first_stage"] = first_stage
    with pytest.raises(SuitePolicyError):
        validate_suite_policy(policy, registry)


@pytest.mark.parametrize("families", [None, {}, "families"])
def test_suite_rejects_malformed_families_container(families: object) -> None:
    policy = _suite_fixture()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    policy["families"] = families
    with pytest.raises(SuitePolicyError):
        validate_suite_policy(policy, registry)


@pytest.mark.parametrize("family", [None, [], 7])
def test_suite_rejects_malformed_family_name(family: object) -> None:
    policy = _suite_fixture()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    policy["families"][0]["family"] = family
    with pytest.raises(SuitePolicyError):
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


@pytest.mark.parametrize(
    "path",
    [
        "processed/SWE-Gym/openhands-sampled/records.jsonl",
        "processed/swe-gym/OpenHands-Sampled/records.jsonl",
        "processed/swe-gym/openhands-sampled/../records.jsonl",
        "processed/swe-gym/./openhands-sampled/records.jsonl",
        "processed/archive/processed/swe-gym/openhands-sampled/records.jsonl",
        "processed-copy/swe-gym/openhands-sampled/records.jsonl",
        "processed/swe-gym-copy/openhands-sampled/records.jsonl",
        "processed/swe-gym/openhands-sampled-copy/records.jsonl",
        "processed/swe-gym/not-openhands-sampled/records.jsonl",
    ],
)
def test_payload_guard_rejects_ambiguous_approved_lane_paths(path: str) -> None:
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            path=path,
        )


def test_payload_guard_accepts_exact_relative_approved_lane_path() -> None:
    assert_payload_read_allowed(
        _suite_fixture(),
        stage="100k",
        family="swe-gym",
        lane_id="swe-gym-openhands-sampled",
        path="processed/swe-gym/openhands-sampled/records.jsonl",
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
    "path",
    [
        "processed/SWE-Bench/normalized_metadata.jsonl",
        "processed/swe-bench/Normalized_Metadata.jsonl",
        "processed/swe-bench/../normalized_metadata.jsonl",
        "processed/./swe-bench/normalized_metadata.jsonl",
        "processed/archive/processed/swe-bench/normalized_metadata.jsonl",
        "processed-copy/swe-bench/normalized_metadata.jsonl",
        "processed/swe-bench-copy/normalized_metadata.jsonl",
        "processed/swe-bench/not-normalized_metadata.jsonl",
        "processed/swe-bench/normalized_metadata.jsonl.bak",
        "processed/swe-bench/normalized_metadata.jsonl/descendant",
    ],
)
def test_payload_guard_rejects_ambiguous_identity_paths(path: str) -> None:
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-bench",
            lane_id=None,
            path=path,
        )


def test_payload_guard_accepts_exact_relative_identity_path() -> None:
    assert_payload_read_allowed(
        _suite_fixture(),
        stage="100k",
        family="swe-bench",
        lane_id=None,
        path="processed/swe-bench/normalized_metadata.jsonl",
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


@pytest.mark.parametrize("path", [None, object(), ""])
def test_payload_guard_rejects_missing_or_non_path_values(path: object) -> None:
    with pytest.raises(SuitePolicyError):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            path=path,
        )


def test_payload_guard_rejects_malformed_family_without_builtin_error() -> None:
    with pytest.raises(SuitePolicyError):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family=[],
            lane_id="swe-gym-openhands-sampled",
            path="processed/swe-gym/openhands-sampled/records.jsonl",
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

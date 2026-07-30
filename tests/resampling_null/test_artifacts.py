"""Milestone claims: canonical digests, schema closure, and tamper detection."""

from __future__ import annotations

import pytest

from pneuma_lab.resampling_null.artifacts import (
    RecordValidationError,
    canonical_digest,
    validate_record,
    verify_digest_link,
)


pytestmark = pytest.mark.milestone


def test_canonical_digest_is_independent_of_mapping_insertion_order() -> None:
    left = {"b": {"y": 2, "x": 1}, "a": [3, 4]}
    right = {"a": [3, 4], "b": {"x": 1, "y": 2}}

    assert canonical_digest(left) == canonical_digest(right)


def test_nested_parent_tamper_invalidates_digest_link() -> None:
    parent = {"payload": {"outcomes": [{"success": 0}]}}
    child = {"parent_sha256": canonical_digest(parent)}
    verify_digest_link(child, "parent_sha256", parent)
    parent["payload"]["outcomes"][0]["success"] = 1  # type: ignore[index]

    with pytest.raises(RecordValidationError, match="parent_sha256"):
        verify_digest_link(child, "parent_sha256", parent)


def test_unknown_record_kind_fails_closed() -> None:
    with pytest.raises(RecordValidationError, match="record_kind"):
        validate_record({"record_kind": "forged"})


def test_artifact_digest_changes_with_semantic_content() -> None:
    assert canonical_digest({"success": 0}) != canonical_digest({"success": 1})

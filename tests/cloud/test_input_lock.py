from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.input_lock import (
    REAL_CANDIDATE,
    SYNTHETIC,
    build_candidate_input_lock,
    classify_input_lock,
    real_candidate_findings,
    require_real_candidate_lock,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures" / "cloud"


def _sha(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _rev(seed: str) -> str:
    return hashlib.sha1(seed.encode()).hexdigest()  # noqa: S324 - a git object id, not a security digest


def _payload(name: str) -> bytes:
    return name.encode()


def _receipt(name: str) -> dict:
    payload = _payload(name)
    return {"relative_path": f"receipts/{name}.json", "sha256": _sha(name), "size_bytes": len(payload)}


def _real_parts() -> dict:
    """Structurally real identities, used only to exercise the classifier.

    These are well-formed but not retrieved: no byte behind any of them has
    been fetched or verified, which is exactly the state a real candidate lock
    describes before the Step 5B audit runs.
    """

    return {
        "frozen_timestamp": "2026-07-31T00:00:00Z",
        "provenance": {"design_sha256": _sha("design"), "code_sha256": _sha("code")},
        "model_pins": [{
            "repository": "Qwen/Qwen3.6-35B-A3B-FP8",
            "revision": _rev("model"),
            "license": "Apache-2.0",
            "snapshot_receipt": _receipt("model"),
        }],
        "tokenizer_pin": {
            "repository": "Qwen/Qwen3.6-35B-A3B-FP8",
            "revision": _rev("tokenizer"),
            "license": "Apache-2.0",
            "snapshot_receipt": _receipt("tokenizer"),
        },
        "benchmark_pins": [{
            "repository": "microsoft/SWE-bench-Live",
            "revision": _rev("benchmark"),
            "license": "MIT",
            "snapshot_receipt": _receipt("benchmark"),
            "dataset_revision": _rev("dataset"),
            "task_manifest_sha256": _sha("task-manifest"),
            "task_manifest_size_bytes": len(_payload("task-manifest")),
        }],
        "container_bases": [{
            "repository": "docker.io/vllm/vllm-openai",
            "digest": f"linux/amd64@sha256:{_sha('image')}",
            "manifest_size_bytes": len(_payload("image")),
        }],
        "verifier_sources": [{
            "repository": "sierra-research/tau2-bench",
            "revision": _rev("verifier"),
            "license": "MIT",
            "snapshot_receipt": _receipt("verifier"),
        }],
        "contamination_receipts": [_receipt("contamination")],
        "license_receipts": [_receipt("licence")],
    }


def _committed_fixture() -> dict:
    return json.loads((FIXTURES / "input-lock-fixture.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The committed Step 5A fixture is a demonstration and must be reported as one.
# ---------------------------------------------------------------------------


def test_committed_step5a_fixture_is_classified_synthetic() -> None:
    """The whole point: a green schema check is not evidence of real inputs."""

    record = _committed_fixture()
    assert classify_input_lock(record) == SYNTHETIC
    with pytest.raises(CloudManifestError, match="synthetic demonstration, not a real candidate"):
        require_real_candidate_lock(record)


def test_findings_name_the_specific_placeholder_fields() -> None:
    fields = {finding["field"] for finding in real_candidate_findings(_committed_fixture())}
    # Placeholder repositories, filler digests, and the one shared receipt path.
    assert "model_pins[0].repository" in fields
    assert "tokenizer_pin.repository" in fields
    assert "container_bases[0].digest" in fields
    assert "benchmark_pins[0].task_manifest_sha256" in fields
    assert any(field.endswith(".relative_path") for field in fields)


# ---------------------------------------------------------------------------
# A structurally real lock classifies as a candidate.
# ---------------------------------------------------------------------------


def test_structurally_real_identities_classify_as_a_real_candidate() -> None:
    record = build_candidate_input_lock(**_real_parts())
    assert classify_input_lock(record) == REAL_CANDIDATE
    assert real_candidate_findings(record) == ()
    assert record["record_kind"] == "cloud_input_lock"


def test_builder_covers_every_required_identity_class() -> None:
    """Model, tokenizer, dataset, task manifest, verifier, and OCI digest."""

    record = build_candidate_input_lock(**_real_parts())
    assert record["model_pins"] and record["tokenizer_pin"]
    assert record["benchmark_pins"][0]["dataset_revision"]
    assert record["benchmark_pins"][0]["task_manifest_sha256"]
    assert record["verifier_sources"]
    assert record["container_bases"][0]["digest"].startswith("linux/amd64@sha256:")


# ---------------------------------------------------------------------------
# Each placeholder family is rejected individually.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("repository", ["org/model", "registry.example/base", "example.com/thing", "bare-name", "acme/tokenizer", "owner/repo"])
def test_placeholder_repositories_are_refused(repository: str) -> None:
    parts = _real_parts()
    parts["model_pins"][0]["repository"] = repository
    with pytest.raises(CloudManifestError, match="placeholder or reserved-namespace"):
        build_candidate_input_lock(**parts)


@pytest.mark.parametrize("revision", ["a" * 40, "0" * 40, "ab" * 20, "0123" * 10])
def test_filler_revisions_are_refused(revision: str) -> None:
    parts = _real_parts()
    parts["model_pins"][0]["revision"] = revision
    with pytest.raises(CloudManifestError, match="filler rather than a commit identity"):
        build_candidate_input_lock(**parts)


def test_a_mutable_tag_cannot_stand_in_for_a_revision() -> None:
    parts = _real_parts()
    parts["model_pins"][0]["revision"] = "main"
    # The schema pins the 40-hex shape, so a tag is refused before classification.
    with pytest.raises(CloudManifestError):
        build_candidate_input_lock(**parts)


def test_a_floating_image_tag_cannot_stand_in_for_a_digest() -> None:
    parts = _real_parts()
    parts["container_bases"][0]["digest"] = "linux/amd64@sha256:" + "a" * 64
    with pytest.raises(CloudManifestError, match="filler rather than a manifest digest"):
        build_candidate_input_lock(**parts)


def test_dataset_revision_and_task_manifest_must_be_real() -> None:
    for field, message in (("dataset_revision", "immutable 40-hex commit"), ("task_manifest_sha256", "filler rather than a content digest")):
        parts = _real_parts()
        length = 40 if field == "dataset_revision" else 64
        parts["benchmark_pins"][0][field] = "b" * length
        with pytest.raises(CloudManifestError, match=message):
            build_candidate_input_lock(**parts)


def test_two_artifacts_may_not_share_one_receipt_path() -> None:
    parts = _real_parts()
    parts["tokenizer_pin"]["snapshot_receipt"] = dict(parts["model_pins"][0]["snapshot_receipt"])
    with pytest.raises(CloudManifestError, match="is already used by"):
        build_candidate_input_lock(**parts)


def test_the_verifier_source_is_a_required_identity() -> None:
    parts = _real_parts()
    parts["verifier_sources"] = []
    with pytest.raises(CloudManifestError):
        build_candidate_input_lock(**parts)


# ---------------------------------------------------------------------------
# The classification is derived, never asserted.
# ---------------------------------------------------------------------------


def test_classification_cannot_be_asserted_by_the_record() -> None:
    """No field can declare a lock real; the schema refuses the attempt."""

    record = _committed_fixture()
    record["lock_class"] = REAL_CANDIDATE
    with pytest.raises(CloudManifestError):
        classify_input_lock(record)


def test_builder_refuses_to_emit_a_placeholder_lock() -> None:
    """The constructor is not a laundering route for the shape demonstration."""

    fixture = _committed_fixture()
    parts = {key: fixture[key] for key in (
        "frozen_timestamp", "provenance", "model_pins", "tokenizer_pin", "benchmark_pins",
        "container_bases", "verifier_sources", "contamination_receipts", "license_receipts",
    )}
    with pytest.raises(CloudManifestError, match="synthetic demonstration"):
        build_candidate_input_lock(**parts)


def test_real_candidate_is_not_a_claim_that_bytes_were_retrieved() -> None:
    """A candidate lock is a proposal for the audit, not the audit's result.

    Nothing in this module reads a network or a mirror, so classification can
    only ever speak to the *form* of an identity. This test exists so that
    property is pinned rather than merely documented.
    """

    record = build_candidate_input_lock(**_real_parts())
    assert classify_input_lock(record) == REAL_CANDIDATE
    # No receipt bytes exist anywhere, and the classifier never asked for any.
    for pin in record["model_pins"]:
        assert not (REPO_ROOT / pin["snapshot_receipt"]["relative_path"]).exists()

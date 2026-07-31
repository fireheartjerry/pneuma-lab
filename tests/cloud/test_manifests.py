from __future__ import annotations

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.inputs import verify_input_lock
from pneuma_lab.cloud.manifests import validate_experiment_manifest

from .test_inputs import _HEX, input_lock


def test_unpromoted_experiment_manifest_binds_lock_digest() -> None:
    manifest = {"record_kind": "cloud_experiment_manifest", "schema_version": "0.1.0", "frozen_timestamp": "2026-07-31T00:00:00Z", "provenance": {"design_sha256": _HEX, "code_sha256": _HEX}, "input_lock_sha256": verify_input_lock(input_lock()), "tier": "tier-agnostic", "promotion_state": "unpromoted"}
    assert validate_experiment_manifest(manifest)["input_lock_sha256"] == manifest["input_lock_sha256"]


def test_promoted_fixture_manifest_fails_closed() -> None:
    manifest = {"record_kind": "cloud_experiment_manifest", "schema_version": "0.1.0", "frozen_timestamp": "2026-07-31T00:00:00Z", "provenance": {"design_sha256": _HEX, "code_sha256": _HEX}, "input_lock_sha256": _HEX, "tier": "tier-agnostic", "promotion_state": "promoted"}
    with pytest.raises(CloudManifestError):
        validate_experiment_manifest(manifest)

"""Integrity and honesty checks for the pre-preflight E1/E2 artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RECORD_PATH = (
    REPO_ROOT
    / "docs/data/training-readiness/estimator-e1-e2-historical-record.json"
)


def test_historical_record_does_not_retroactively_authorize_models() -> None:
    record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    assert record["record_kind"] == "post_hoc_classification_not_authorization"
    assert record["classification"] == "historical_local_research"
    assert record["authorization_at_run"] == "not_recorded"
    assert record["retroactive_authorization"] is False
    assert record["source"]["source_binding"] == (
        "inferred_not_cryptographically_recorded"
    )
    assert record["source"]["source_traces_sha256"] is None
    assert record["source"]["adapter_report_sha256"] is None
    assert record["deployment_status"] == "blocked"
    assert record["release_status"] == "blocked_license_and_lineage_review"
    assert record["runtime_integration"] == "none"


def test_historical_artifact_hashes_match_the_committed_files() -> None:
    record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    for relative_path, expected in record["artifact_hashes"].items():
        artifact = REPO_ROOT / relative_path
        actual = "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()
        assert actual == expected, relative_path

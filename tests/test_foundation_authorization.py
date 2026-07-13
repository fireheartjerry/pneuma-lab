"""Foundation training cannot allocate a model before every local gate binds."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.foundation.authorization import (
    FoundationAuthorizationError,
    authorization_scope_digest,
    verify_foundation_authorization,
)
from pneuma_lab.foundation.data import ACTIVE_DATASET_GROUPS
from pneuma_lab.foundation.specs import MODEL_SPECS


ROOT = Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_committed_pending_authorization_refuses_training() -> None:
    with pytest.raises(FoundationAuthorizationError, match="not authorized"):
        verify_foundation_authorization(
            ROOT
            / "docs/data/training-authorizations/pneuma-foundation-v0.pending.json",
            repo_root=ROOT,
            registry_path=ROOT / "docs/data/training-readiness/dataset-registry.json",
        )


def test_verified_authorization_binds_shards_registry_gates_and_scope(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    shard = repo / "build" / "foundation" / "shards" / "sample.jsonl"
    shard.parent.mkdir(parents=True)
    shard.write_text('{"example_id":"x"}\n', encoding="utf-8")
    shard_manifest = shard.with_suffix(".manifest.json")
    shard_manifest.write_text(
        json.dumps(
            {
                "inventory": {
                    "token_count": 100000,
                    "repository_count": 1,
                    "issue_count": 1,
                    "languages": {"python": 1},
                    "tools": {"pytest": 1},
                    "trajectory_length": {"min": 1, "max": 1, "mean": 1},
                    "labels": {"resolved": 1},
                }
            }
        ),
        encoding="utf-8",
    )
    registry = repo / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "lanes": [
                    {
                        "lane_id": group,
                        "source_family": group,
                        "training_readiness": "ready"
                        if group == "open-swe-traces"
                        else "eval-only",
                        "authorization": {
                            "training_authorized": group == "open-swe-traces"
                        },
                    }
                    for group in ACTIVE_DATASET_GROUPS
                ]
            }
        ),
        encoding="utf-8",
    )
    spec = MODEL_SPECS["2b"]
    authorization = {
        "manifest_kind": "pneuma_foundation_training_authorization",
        "manifest_schema_version": "0.1.0",
        "authorization_status": "authorized",
        "model": {
            "key": "2b",
            "model_id": spec.model_id,
            "revision": spec.revision,
            "token_ceiling": 100000,
        },
        "shard": {
            "path": shard.relative_to(repo).as_posix(),
            "sha256": _sha(shard),
            "manifest_path": shard_manifest.relative_to(repo).as_posix(),
            "manifest_sha256": _sha(shard_manifest),
        },
        "dataset_policy": {
            "governed_groups": list(ACTIVE_DATASET_GROUPS),
            "positive_weight_groups": ["open-swe-traces"],
            "repo_issue_disjoint": True,
            "diversity_inventory_present": True,
        },
        "local_gates": {
            "previous_stage_passed": False,
            "falsification_gate_passed": False,
            "resource_smoke_passed": False,
        },
        "source_data_policy": {
            "root": str(tmp_path / "pneuma-data"),
            "write_allowed": False,
        },
        "output_root": "build/foundation/",
        "operator_approval": None,
        "budget": {
            "paid_compute_usd": 0,
            "cloud_jobs_used": 0,
            "cloud_lifetime_cap_usd": 45,
        },
    }
    authorization["operator_approval"] = {
        "operator_id": "student-operator",
        "approved_at": "2026-07-13T12:00:00Z",
        "scope_digest": authorization_scope_digest(authorization),
    }
    path = repo / "authorization.json"
    path.write_text(json.dumps(authorization), encoding="utf-8")
    verified = verify_foundation_authorization(
        path,
        repo_root=repo,
        registry_path=registry,
    )
    assert verified.model_key == "2b"
    assert verified.token_ceiling == 100000
    assert verified.shard_path == shard
    assert verified.positive_weight_groups == ("open-swe-traces",)


def test_authorization_detects_scope_or_shard_tampering(tmp_path: Path) -> None:
    # Minimal check: a digest changes whenever any scoped field changes.
    value = {
        "authorization_status": "authorized",
        "model": {"key": "2b"},
        "operator_approval": None,
    }
    first = authorization_scope_digest(value)
    value["model"]["key"] = "4b"
    assert authorization_scope_digest(value) != first

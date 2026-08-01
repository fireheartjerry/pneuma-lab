"""Deterministic bootstrap plan for a real Step 5B input inventory.

The input lock cannot be signed until every snapshot file has a digest and
size. This plan authorizes only discovery of that immutable metadata. It does
not authorize downloading payload bytes, model weights, OCI layers, or running
an experiment.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from .authorization_keys import canonical_bytes
from .manifests import _validate


FROZEN_SOURCES = (
    ("subject_model", "Qwen/Qwen3.6-35B-A3B-FP8", "95a723d08a9490559dae23d0cff1d9466213d989", "huggingface", "list_revision_tree_with_lfs_oids"),
    ("tokenizer", "Qwen/Qwen3.6-35B-A3B-FP8", "95a723d08a9490559dae23d0cff1d9466213d989", "huggingface", "list_revision_tree_with_lfs_oids"),
    ("simulator_model", "Qwen/Qwen3.5-9B", "c202236235762e1c871ad0ccb60c8ee5ba337b9a", "huggingface", "list_revision_tree_with_lfs_oids"),
    ("swe_harness", "microsoft/SWE-bench-Live", "70ec57e852e3f2d195790fe71f553e272c691833", "github", "list_git_tree_with_blob_oids"),
    ("swe_dataset", "SWE-bench-Live/MultiLang", "608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b", "huggingface", "list_revision_tree_with_lfs_oids"),
    ("repo_launcher", "microsoft/RepoLaunch", "7735b1e7363dd3bbc69bd0ef80db646a2ae391fd", "github", "list_git_tree_with_blob_oids"),
    ("tau2_harness", "sierra-research/tau2-bench", "fc0055dc4e0a316c3f83133267fbd6faaa770992", "github", "list_git_tree_with_blob_oids"),
    ("worker_base", "docker.io/vllm/vllm-openai", "sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90", "docker_registry", "read_oci_manifest"),
)


def build_inventory_plan(*, frozen_timestamp: str, region: str = "us-east-1") -> dict[str, Any]:
    sources = sorted([
        {"role": role, "repository": repository, "revision": revision, "service": service, "inventory_operation": operation}
        for role, repository, revision, service, operation in FROZEN_SOURCES
    ], key=lambda source: (source["role"], source["repository"], source["revision"]))
    record = {
        "record_kind": "cloud_input_inventory_plan",
        "schema_version": "0.1.0",
        "frozen_timestamp": frozen_timestamp,
        "action_id": "step5b-inventory-metadata-001",
        "provider": "aws",
        "region": region,
        "purpose": "resolve_inventory_metadata_only",
        "sources": sources,
        "outputs": [
            "receipts/step5b/inventory-metadata.json",
            "receipts/step5b/inventory-metadata.sha256",
        ],
        "network_policy": {
            "allowed_hosts": ["api.github.com", "huggingface.co", "registry-1.docker.io", "auth.docker.io"],
            "payload_downloads": False,
            "model_weight_downloads": False,
            "container_layer_downloads": False,
            "experiment_execution": False,
        },
        "cost_ceiling_usd": 0.0,
        "max_retries": 1,
    }
    return validate_inventory_plan(record)


def validate_inventory_plan(record: Mapping[str, Any]) -> dict[str, Any]:
    plan = _validate(record, expected_kind="cloud_input_inventory_plan")
    identities = [(source["role"], source["repository"], source["revision"]) for source in plan["sources"]]
    if identities != sorted(identities):
        raise ValueError("inventory sources must be canonically ordered")
    if len(identities) != len(set(identities)):
        raise ValueError("inventory source identities must be unique")
    return plan


def inventory_plan_digest(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(validate_inventory_plan(record))).hexdigest()

"""Static, tier-agnostic AWS architecture contract checks."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import CloudManifestError


_CONTROLLER_FORBIDDEN = frozenset({"dynamodb:UpdateItem", "dynamodb:PutItem"})
_REQUIRED_CONTROLLER = frozenset({"dynamodb:GetItem", "s3:GetObject", "s3:PutObject"})
_REQUIRED_WATCHER = frozenset({"dynamodb:UpdateItem", "ec2:TerminateInstances"})

# The approved AWS primary path is exactly two independent, one-GPU workers.
# Keep these values beside the manifest checks so a Terraform-only edit cannot
# silently change capacity, co-locate replicas, or reduce official throughput.
PRIMARY_INSTANCE_TYPE = "g6e.2xlarge"
PRIMARY_WORKER_COUNT = 2
PRIMARY_WORKER_VCPUS = 8
PRIMARY_WORKER_GPU_COUNT = 1
PRIMARY_TOTAL_VCPUS = PRIMARY_WORKER_COUNT * PRIMARY_WORKER_VCPUS
PRIMARY_TOTAL_GPU_COUNT = PRIMARY_WORKER_COUNT * PRIMARY_WORKER_GPU_COUNT
PRIMARY_USABLE_GPU_MEMORY_GIB = 44
PRIMARY_ALLOCATION_STRATEGY = "SPOT_PRICE_CAPACITY_OPTIMIZED"
PRIMARY_PARTITIONING = "canonical_round_robin"
PRIMARY_INTERRUPTION_POLICY = "freeze_and_resume"


def validate_architecture(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed on tier constants, lease renewal, or shared identities."""

    from .manifests import _validate

    record = _validate(manifest, expected_kind="cloud_architecture_manifest")
    controller = set(record["controller_policy"]["actions"])
    watcher = set(record["watcher_policy"]["actions"])
    if _CONTROLLER_FORBIDDEN & controller or not _REQUIRED_CONTROLLER <= controller:
        raise CloudManifestError("controller policy must be read-only for the lease")
    if not _REQUIRED_WATCHER <= watcher:
        raise CloudManifestError("watcher policy lacks termination authority")
    if record["controller_policy"]["identity"] == record["watcher_policy"]["identity"]:
        raise CloudManifestError("controller and watcher identities must differ")
    if record["tier"] in {"C120", "C160"}:
        raise CloudManifestError("architecture must be tier-agnostic")
    compute = record["compute"]
    expected = {
        "instance_type": PRIMARY_INSTANCE_TYPE,
        "max_vcpus": PRIMARY_TOTAL_VCPUS,
        "worker_count": PRIMARY_WORKER_COUNT,
        "worker_vcpus": PRIMARY_WORKER_VCPUS,
        "worker_gpu_count": PRIMARY_WORKER_GPU_COUNT,
        "total_gpu_count": PRIMARY_TOTAL_GPU_COUNT,
        "usable_gpu_memory_gib": PRIMARY_USABLE_GPU_MEMORY_GIB,
        "allocation_strategy": PRIMARY_ALLOCATION_STRATEGY,
        "partitioning": PRIMARY_PARTITIONING,
        "interruption_policy": PRIMARY_INTERRUPTION_POLICY,
    }
    if any(compute[key] != value for key, value in expected.items()):
        raise CloudManifestError("architecture must use the approved two-worker L40S Spot topology")
    return record

"""Static, tier-agnostic AWS architecture contract checks."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import CloudManifestError


_CONTROLLER_FORBIDDEN = frozenset({"dynamodb:UpdateItem", "dynamodb:PutItem"})
_REQUIRED_CONTROLLER = frozenset({"dynamodb:GetItem", "s3:GetObject", "s3:PutObject"})
_REQUIRED_WATCHER = frozenset({"dynamodb:UpdateItem", "ec2:TerminateInstances"})

# The approved AWS primary path is deliberately a one-node, one-GPU shape.
# Keep these values beside the manifest checks so a Terraform-only edit cannot
# silently turn the admission contract back into a multi-GPU deployment.
PRIMARY_INSTANCE_TYPE = "g6e.2xlarge"
PRIMARY_VCPUS = 8
PRIMARY_GPU_COUNT = 1
PRIMARY_USABLE_GPU_MEMORY_GIB = 44


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
        "max_vcpus": PRIMARY_VCPUS,
        "gpu_count": PRIMARY_GPU_COUNT,
        "usable_gpu_memory_gib": PRIMARY_USABLE_GPU_MEMORY_GIB,
    }
    if any(compute[key] != value for key, value in expected.items()):
        raise CloudManifestError("architecture must use the approved one-GPU L40S topology")
    return record

"""Offline verification and retrieval-plan derivation for immutable input locks."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .errors import CloudManifestError
from .manifests import validate_input_lock


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def verify_input_lock(record: Mapping[str, Any]) -> str:
    """Return the canonical lock digest after fail-closed local validation."""

    return _digest(validate_input_lock(record))


def build_retrieval_plan(record: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    """Derive immutable retrieval targets without network or tag resolution."""

    lock = validate_input_lock(record)
    targets: list[dict[str, str]] = []
    for model in lock["model_pins"]:
        targets.append({"kind": "model", "repository": model["repository"], "revision": model["revision"]})
    for benchmark in lock["benchmark_pins"]:
        targets.append({"kind": "benchmark", "repository": benchmark["repository"], "revision": benchmark["revision"]})
    for base in lock["container_bases"]:
        targets.append({"kind": "container", "repository": base["repository"], "digest": base["digest"]})
    if len({tuple(sorted(item.items())) for item in targets}) != len(targets):
        raise CloudManifestError("retrieval targets must be unique")
    return tuple(targets)

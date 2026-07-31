"""Offline verification and retrieval-plan derivation for immutable input locks."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
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
    tokenizer = lock["tokenizer_pin"]
    targets.append({"kind": "tokenizer", "repository": tokenizer["repository"], "revision": tokenizer["revision"]})
    for benchmark in lock["benchmark_pins"]:
        targets.append({"kind": "benchmark", "repository": benchmark["repository"], "revision": benchmark["revision"]})
        targets.append({"kind": "dataset", "repository": benchmark["repository"], "revision": benchmark["dataset_revision"]})
    for verifier in lock["verifier_sources"]:
        targets.append({"kind": "verifier", "repository": verifier["repository"], "revision": verifier["revision"]})
    for base in lock["container_bases"]:
        targets.append({"kind": "container", "repository": base["repository"], "digest": base["digest"]})
    if len({tuple(sorted(item.items())) for item in targets}) != len(targets):
        raise CloudManifestError("retrieval targets must be unique")
    return tuple(targets)


def verify_input_receipts(record: Mapping[str, Any], receipt_root: Path) -> tuple[str, ...]:
    """Hash-verify every receipt referenced by an input lock under one root."""

    lock = validate_input_lock(record)
    root = receipt_root.resolve(strict=True)
    receipts: list[Mapping[str, str]] = []
    receipts.extend(item["snapshot_receipt"] for item in lock["model_pins"])
    receipts.append(lock["tokenizer_pin"]["snapshot_receipt"])
    receipts.extend(item["snapshot_receipt"] for item in lock["benchmark_pins"])
    receipts.extend(item["snapshot_receipt"] for item in lock["verifier_sources"])
    receipts.extend(lock["contamination_receipts"])
    receipts.extend(lock["license_receipts"])

    verified: dict[str, str] = {}
    for receipt in receipts:
        relative_path = receipt["relative_path"]
        candidate = receipt_root / relative_path
        resolved = candidate.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise CloudManifestError(f"receipt escapes root: {relative_path}") from exc
        if candidate.is_symlink() or not resolved.is_file():
            raise CloudManifestError(f"receipt must be a regular non-symlink file: {relative_path}")
        observed = hashlib.sha256(resolved.read_bytes()).hexdigest()
        expected = receipt["sha256"]
        if observed != expected:
            raise CloudManifestError(f"receipt digest mismatch: {relative_path}")
        previous = verified.setdefault(relative_path, expected)
        if previous != expected:
            raise CloudManifestError(f"conflicting receipt digest: {relative_path}")
    return tuple(sorted(verified))

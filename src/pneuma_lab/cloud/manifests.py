"""Strict validation of fixture-only cloud input and experiment manifests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from jsonschema import Draft202012Validator

from pneuma_lab import schemas

from .errors import CloudManifestError


_SCHEMA_BY_KIND = {
    "cloud_input_lock": "cloud-input-lock.schema.json",
    "cloud_experiment_manifest": "cloud-experiment-manifest.schema.json",
    "cloud_architecture_manifest": "cloud-architecture-manifest.schema.json",
}


def _validate(record: Mapping[str, Any], *, expected_kind: str) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("record_kind") != expected_kind:
        raise CloudManifestError(f"record_kind must be {expected_kind!r}")
    schema = schemas.load_schema(_SCHEMA_BY_KIND[expected_kind])
    errors = sorted(Draft202012Validator(schema).iter_errors(dict(record)), key=str)
    if errors:
        raise CloudManifestError(errors[0].message)
    return dict(record)


def validate_input_lock(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a local fixture input lock without retrieving any input."""

    return _validate(record, expected_kind="cloud_input_lock")


def validate_experiment_manifest(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an unpromoted experiment manifest bound to an input-lock digest."""

    return _validate(record, expected_kind="cloud_experiment_manifest")

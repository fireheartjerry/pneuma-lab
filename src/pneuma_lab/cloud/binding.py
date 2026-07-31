"""Exact local result binding checks for code, image, manifest, and lease."""

from __future__ import annotations

from collections.abc import Mapping

from .errors import CloudManifestError


def verify_binding(binding: Mapping[str, object], *, code: str, image: str, manifest: str, lease_id: str) -> None:
    expected = {"code_sha256": code, "image_sha256": image, "manifest_sha256": manifest, "lease_id": lease_id}
    if any(binding.get(key) != value for key, value in expected.items()):
        raise CloudManifestError("result binding substitution detected")

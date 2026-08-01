"""Static image-recipe inspection; never pulls or builds an image."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .errors import CloudManifestError


def recipe_digest(paths: Sequence[Path]) -> str:
    """Hash named recipe files in a fixed path-and-byte order."""

    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        digest.update(path.as_posix().encode("utf-8") + b"\0" + path.read_bytes())
    return digest.hexdigest()


def validate_image_manifest(record: Mapping[str, Any]) -> dict[str, Any]:
    """Reject swapped images, duplicate roles, or fixture promotion."""

    from .manifests import _validate

    manifest = _validate(record, expected_kind="cloud_image_manifest")
    images = manifest["images"]
    names = {image["name"] for image in images}
    if names != {"controller", "model-server", "benchmark-worker"}:
        raise CloudManifestError("image manifest must bind exactly three roles")
    if any(image["image_digest"] is not None or image["sbom_sha256"] is not None for image in images):
        raise CloudManifestError("Step 7A manifest cannot claim a built image or SBOM")
    return manifest


def validate_image_build_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate Step 7B double-build evidence without performing a build."""

    from .manifests import _validate

    receipt = _validate(record, expected_kind="cloud_image_build_receipt")
    digests = receipt["build_image_digests"]
    observed_reproducible = digests[0] == digests[1]
    if receipt["reproducible"] != observed_reproducible:
        raise CloudManifestError("reproducible must equal the two-digest comparison")
    return receipt


def validate_image_build_set(records: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Require a complete, single-recipe, reproducible three-role build set."""

    receipts = tuple(validate_image_build_receipt(record) for record in records)
    if {record["role"] for record in receipts} != {"controller", "model-server", "benchmark-worker"}:
        raise CloudManifestError("Step 7B requires exactly one receipt for each image role")
    if len(receipts) != 3 or len({record["recipe_sha256"] for record in receipts}) != 1:
        raise CloudManifestError("Step 7B build receipts must bind one recipe exactly once per role")
    if len({record["input_lock_sha256"] for record in receipts}) != 1:
        raise CloudManifestError("Step 7B build receipts must bind one exact Step 5B input lock")
    if not all(record["reproducible"] for record in receipts):
        raise CloudManifestError("Step 7B remains blocked by a non-reproducible image")
    return receipts


def inspect_dockerfile(path: Path) -> None:
    """Enforce immutable base syntax and no unpinned pip install."""

    lines = path.read_text(encoding="utf-8").splitlines()
    if not any(line.startswith("FROM ") and "@sha256:" in line for line in lines):
        raise CloudManifestError("Dockerfile requires a digest-pinned FROM")
    for line in lines:
        if "pip install" in line and "==" not in line and "--require-hashes -r" not in line:
            raise CloudManifestError("Dockerfile has an unpinned pip install")

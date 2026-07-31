from __future__ import annotations

from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.images import inspect_dockerfile, validate_image_manifest


ROOT = Path(__file__).resolve().parents[2]
HEX = "a" * 64


def image_manifest() -> dict:
    return {"record_kind": "cloud_image_manifest", "schema_version": "0.1.0", "recipe_sha256": HEX, "images": [{"name": name, "dockerfile": f"infra/docker/{name}/Dockerfile", "base_digest": "sha256:" + letter * 64, "lock_sha256": letter * 64, "image_digest": None, "sbom_sha256": None} for name, letter in (("controller", "a"), ("model-server", "b"), ("benchmark-worker", "c"))]}


def test_every_recipe_is_digest_pinned_and_has_no_unpinned_install() -> None:
    for image in image_manifest()["images"]:
        inspect_dockerfile(ROOT / image["dockerfile"])


def test_fixture_manifest_is_bound_but_cannot_claim_build_evidence() -> None:
    assert validate_image_manifest(image_manifest())["recipe_sha256"] == HEX
    forged = image_manifest(); forged["images"][0]["image_digest"] = "sha256:" + HEX
    with pytest.raises(CloudManifestError): validate_image_manifest(forged)


def test_build_recipe_names_determinism_controls() -> None:
    recipe = (ROOT / "infra/docker/README.md").read_text(encoding="utf-8")
    for control in ("SOURCE_DATE_EPOCH", "PYTHONHASHSEED", "UTC", "digest comparison"):
        assert control in recipe

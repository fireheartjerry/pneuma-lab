from __future__ import annotations

from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.images import (
    inspect_dockerfile,
    validate_image_build_receipt,
    validate_image_build_set,
    validate_image_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
HEX = "a" * 64


def image_manifest() -> dict:
    return {"record_kind": "cloud_image_manifest", "schema_version": "0.1.0", "recipe_sha256": HEX, "images": [{"name": name, "dockerfile": f"infra/docker/{name}/Dockerfile", "base_digest": "sha256:" + letter * 64, "lock_sha256": letter * 64, "image_digest": None, "sbom_sha256": None} for name, letter in (("controller", "a"), ("model-server", "b"), ("benchmark-worker", "c"))]}


def test_every_recipe_is_digest_pinned_and_has_no_unpinned_install() -> None:
    for image in image_manifest()["images"]:
        inspect_dockerfile(ROOT / image["dockerfile"])


def test_fixture_manifest_is_bound_but_cannot_claim_build_evidence() -> None:
    assert validate_image_manifest(image_manifest())["recipe_sha256"] == HEX
    forged = image_manifest()
    forged["images"][0]["image_digest"] = "sha256:" + HEX
    with pytest.raises(CloudManifestError):
        validate_image_manifest(forged)


def test_build_recipe_names_determinism_controls() -> None:
    recipe = (ROOT / "infra/docker/README.md").read_text(encoding="utf-8")
    for control in ("SOURCE_DATE_EPOCH", "PYTHONHASHSEED", "UTC", "digest comparison"):
        assert control in recipe


def test_step7b_recipes_are_real_role_probes_not_fixture_bases() -> None:
    for role in ("controller", "model-server", "benchmark-worker"):
        recipe = (ROOT / "infra" / "docker" / role / "Dockerfile").read_text(encoding="utf-8")
        assert "registry.invalid" not in recipe
        assert "vllm/vllm-openai@sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90" in recipe
        assert f'"{role}"]' in recipe
        assert "production_runtime.py" in recipe


def build_receipt(role: str, letter: str = "a") -> dict:
    return {
        "record_kind": "cloud_image_build_receipt",
        "schema_version": "0.1.0",
        "role": role,
        "recipe_sha256": HEX,
        "dockerfile_sha256": letter * 64,
        "base_digest": "sha256:" + letter * 64,
        "lock_sha256": letter * 64,
        "input_lock_sha256": "9" * 64,
        "builder_sha256": "d" * 64,
        "build_image_digests": ["sha256:" + "e" * 64] * 2,
        "sbom_sha256": "f" * 64,
        "reproducible": True,
    }


def test_step7b_requires_two_equal_builds_and_all_roles() -> None:
    records = [build_receipt(role, letter) for role, letter in (("controller", "a"), ("model-server", "b"), ("benchmark-worker", "c"))]
    assert len(validate_image_build_set(records)) == 3
    records[0]["build_image_digests"][1] = "sha256:" + "0" * 64
    with pytest.raises(CloudManifestError, match="reproducible"):
        validate_image_build_receipt(records[0])


def test_step7b_refuses_builds_bound_to_different_input_locks() -> None:
    records = [build_receipt(role, letter) for role, letter in (("controller", "a"), ("model-server", "b"), ("benchmark-worker", "c"))]
    records[2]["input_lock_sha256"] = "8" * 64
    with pytest.raises(CloudManifestError, match="one exact Step 5B input lock"):
        validate_image_build_set(records)

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.images import (
    inspect_dockerfile,
    require_qualification_image_binding,
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
        "action_id": "step7b-aws-builder-001",
        "plan_sha256": "c" * 64,
        "role": role,
        "recipe_sha256": HEX,
        "dockerfile_sha256": letter * 64,
        "base_digest": "sha256:" + letter * 64,
        "lock_sha256": letter * 64,
        "input_lock_sha256": "9" * 64,
        "runtime_sha256": "a" * 64,
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


def qualification_receipt(source_commit: str = "a" * 40) -> dict:
    fresh_config = {
        "status": "pass",
        "image_digest": "sha256:" + "b" * 64,
        "inspect_sha256": "c" * 64,
    }
    fresh_config["receipt_sha256"] = hashlib.sha256(
        canonical_bytes(fresh_config)
    ).hexdigest()
    fresh_fixture = {
        "status": "pass",
        "worker_indices": [0, 1],
        "runtime_sha256": "d" * 64,
    }
    fresh_fixture["receipt_sha256"] = hashlib.sha256(
        canonical_bytes(fresh_fixture)
    ).hexdigest()
    receipt = {
        "record_kind": "cloud_qualification_image_build_receipt",
        "schema_version": "0.1.0",
        "action_class": "image_build",
        "action_id": "qualification-image-build-001",
        "region": "us-east-1",
        "status": "COMPLETE",
        "provider": "aws",
        "source": {"commit": source_commit},
        "target": {
            "ecr_image_digest": "sha256:" + "b" * 64,
            "fresh_read_digest_match": True,
            "repository_tag_mutability": "IMMUTABLE",
        },
        "local_checks": {
            "source_revision_label": source_commit,
            "image_entrypoint": "/opt/pneuma/fixed_admission_entrypoint.sh",
            "image_entrypoint_check": "pass",
            "image_cmd_override": "absent",
            "fresh_ecr_read": "pass",
            "fresh_ecr_image_config": fresh_config,
            "fresh_ecr_image_digest": "sha256:" + "b" * 64,
            "fresh_ecr_fixture_runtime": fresh_fixture,
            "fresh_ecr_sidecar_sha256": hashlib.sha256(
                canonical_bytes(
                    {
                        "fresh_ecr_image_config": fresh_config,
                        "fresh_ecr_fixture_runtime": fresh_fixture,
                    }
                )
            ).hexdigest(),
            "runtime_schema": "/opt/schemas/cloud-worker-admission-measurement.schema.json present",
            "aws_cli": {"check": "pass", "version": "aws-cli/2.36.14"},
            "package_import": {"pneuma_lab": "pass"},
            "fixture_runtime": {
                "network": "none",
                "gpu": False,
                "model_download": False,
                "model_loaded": False,
                "immutable_worker_indexed_artifacts": ["worker-0", "worker-1"],
                "all_five_inputs_materialized_as_readable_local_files": True,
                "retrieved_bytes_match": True,
            },
        },
        "teardown": {"builder": "terminated", "fresh_provider_absence": True},
    }
    receipt["receipt_sha256"] = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
    return receipt


def test_qualification_image_binding_requires_current_source_revision(tmp_path: Path) -> None:
    receipt = qualification_receipt()
    (tmp_path / "qualification-image-build-001-receipt-20260803.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    bound = require_qualification_image_binding(
        tmp_path,
        image_digest="sha256:" + "b" * 64,
        source_commit="a" * 40,
    )
    assert bound["source"]["commit"] == "a" * 40
    with pytest.raises(CloudManifestError, match="different source revision"):
        require_qualification_image_binding(
            tmp_path,
            image_digest="sha256:" + "b" * 64,
            source_commit="c" * 40,
        )


def test_qualification_image_binding_accepts_ancestor_for_unchanged_runtime_tree(
    tmp_path: Path,
) -> None:
    import subprocess

    repository_root = Path(__file__).resolve().parents[2]
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository_root, text=True
    ).strip()
    ancestor = subprocess.check_output(
        ["git", "rev-list", "--max-parents=0", head],
        cwd=repository_root,
        text=True,
    ).splitlines()[-1]
    runtime_diff = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            ancestor,
            head,
            "--",
            "infra/docker/qualification-worker/**",
            "schemas/**",
            "src/pneuma_lab/**",
            ":!src/pneuma_lab/cloud/ephemeral_runner.py",
            ":!src/pneuma_lab/cloud/images.py",
        ],
        cwd=repository_root,
        check=False,
    )
    if runtime_diff.returncode != 0:
        pytest.skip("this checkout has changed image-runtime files since its root commit")
    receipt = qualification_receipt(ancestor)
    (tmp_path / "qualification-image-build-001-receipt-20260803.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    bound = require_qualification_image_binding(
        tmp_path,
        image_digest="sha256:" + "b" * 64,
        source_commit=head,
    )
    assert bound["source"]["commit"] == ancestor


def test_qualification_image_binding_rejects_tampered_receipt_bytes(tmp_path: Path) -> None:
    receipt = qualification_receipt()
    receipt["target"]["fresh_read_digest_match"] = False
    (tmp_path / "qualification-image-build-001-receipt-20260803.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    with pytest.raises(CloudManifestError, match="receipt digest"):
        require_qualification_image_binding(
            tmp_path,
            image_digest="sha256:" + "b" * 64,
            source_commit="a" * 40,
        )


def test_qualification_image_binding_requires_both_worker_fixture_artifacts(
    tmp_path: Path,
) -> None:
    receipt = qualification_receipt()
    receipt["local_checks"]["fixture_runtime"][
        "immutable_worker_indexed_artifacts"
    ] = ["worker-0"]
    receipt["receipt_sha256"] = hashlib.sha256(
        canonical_bytes({key: value for key, value in receipt.items() if key != "receipt_sha256"})
    ).hexdigest()
    (tmp_path / "qualification-image-build-001-receipt-20260803.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    with pytest.raises(CloudManifestError, match="fixture-only runtime evidence"):
        require_qualification_image_binding(
            tmp_path,
            image_digest="sha256:" + "b" * 64,
            source_commit="a" * 40,
        )

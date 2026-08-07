from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile

import pytest

from pneuma_lab.cloud.production_runtime import _extract_package


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "submit_official_batch", ROOT / "scripts/research/submit_official_batch.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_official_multicontainer_resources_fill_one_whole_worker() -> None:
    images = {
        role: (
            "892077329800.dkr.ecr.us-east-1.amazonaws.com/"
            f"pneuma-official-production-{role}@sha256:" + letter * 64
        )
        for role, letter in (
            ("controller", "1"),
            ("model-server", "2"),
            ("benchmark-worker", "3"),
        )
    }
    rows = MODULE._official_containers(
        images=images,
        package_uri="s3://example/package.tar.gz",
        package_sha256="4" * 64,
        run_spec_sha256="5" * 64,
        controller_environment=[],
        common_environment=[],
        benchmark_environment=[],
    )
    resources = [row["resourceRequirements"] for row in rows]
    assert (
        sum(
            int(item["value"])
            for group in resources
            for item in group
            if item["type"] == "VCPU"
        )
        == 8
    )
    assert (
        sum(
            int(item["value"])
            for group in resources
            for item in group
            if item["type"] == "MEMORY"
        )
        == 62000
    )
    assert (
        sum(
            int(item["value"])
            for group in resources
            for item in group
            if item["type"] == "GPU"
        )
        == 1
    )
    assert rows[2]["privileged"] is True
    assert rows[1]["mountPoints"][0]["readOnly"] is False


def test_image_set_loader_rejects_mutable_tags(tmp_path: Path) -> None:
    path = tmp_path / "images.json"
    path.write_text(
        json.dumps(
            {
                "roles": [
                    {
                        "role": role,
                        "image_ref": (
                            "892077329800.dkr.ecr.us-east-1.amazonaws.com/"
                            f"pneuma-official-production-{role}:latest"
                        ),
                    }
                    for role in ("controller", "model-server", "benchmark-worker")
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="mutable or foreign"):
        MODULE._load_images(path)


def test_package_extraction_rejects_parent_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "package.tar.gz"
    payload = b"bad"
    with tarfile.open(archive, "w:gz") as handle:
        info = tarfile.TarInfo("../escape")
        info.size = len(payload)
        handle.addfile(info, io.BytesIO(payload))
    with pytest.raises(ValueError, match="escapes"):
        _extract_package(archive, tmp_path / "run")


def test_submit_refuses_reused_network_resource_from_another_action() -> None:
    value = {"Tags": [{"Key": "ActionId", "Value": "action-a"}]}
    MODULE._require_owned(value, "action-a", "test resource")
    with pytest.raises(RuntimeError, match="not owned"):
        MODULE._require_owned(value, "action-b", "test resource")


def test_tag_rows_override_without_duplicate_keys() -> None:
    rows = MODULE._tag_rows(
        {"Project": "pneuma-lab", "Purpose": "official-p0-step4b"},
        overrides={"Purpose": "official-public-egress"},
    )
    assert rows == [
        {"Key": "Project", "Value": "pneuma-lab"},
        {"Key": "Purpose", "Value": "official-public-egress"},
    ]


class _ExistingPackageS3:
    def __init__(self, *, size: int, digest: str, action_id: str) -> None:
        self.size = size
        self.digest = digest
        self.action_id = action_id
        self.put_calls = 0

    def head_object(self, **_: object) -> dict[str, object]:
        return {
            "ContentLength": self.size,
            "Metadata": {"sha256": self.digest, "action-id": self.action_id},
        }

    def put_object(self, **_: object) -> None:
        self.put_calls += 1


def test_package_staging_accepts_only_identical_existing_object(tmp_path: Path) -> None:
    package = tmp_path / "package.tar.gz"
    package.write_bytes(b"authorized-package")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    s3 = _ExistingPackageS3(
        size=package.stat().st_size, digest=digest, action_id="action-r4"
    )
    MODULE._ensure_package_object(
        s3,
        bucket="bucket",
        key="key",
        package=package,
        package_sha256=digest,
        action_id="action-r4",
    )
    assert s3.put_calls == 0

    s3.digest = "0" * 64
    with pytest.raises(RuntimeError, match="differs"):
        MODULE._ensure_package_object(
            s3,
            bucket="bucket",
            key="key",
            package=package,
            package_sha256=digest,
            action_id="action-r4",
        )

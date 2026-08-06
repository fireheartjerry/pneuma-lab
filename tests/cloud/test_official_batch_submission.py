from __future__ import annotations

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
    rows = [
        MODULE._container(
            name="controller",
            image=images["controller"],
            command=["--protocol", "stage"],
            vcpus=1,
            memory=2000,
            essential=False,
            environment=[],
            depends_on=[],
        ),
        MODULE._container(
            name="model-server",
            image=images["model-server"],
            command=["--protocol", "production"],
            vcpus=1,
            memory=46000,
            essential=False,
            environment=[],
            depends_on=[{"containerName": "controller", "condition": "SUCCESS"}],
            gpu=True,
        ),
        MODULE._container(
            name="benchmark-worker",
            image=images["benchmark-worker"],
            command=["--protocol", "production"],
            vcpus=6,
            memory=12000,
            essential=True,
            environment=[],
            depends_on=[{"containerName": "model-server", "condition": "START"}],
            privileged=True,
        ),
    ]
    resources = [row["resourceRequirements"] for row in rows]
    assert sum(
        int(item["value"])
        for group in resources
        for item in group
        if item["type"] == "VCPU"
    ) == 8
    assert sum(
        int(item["value"])
        for group in resources
        for item in group
        if item["type"] == "MEMORY"
    ) == 60000
    assert sum(
        int(item["value"])
        for group in resources
        for item in group
        if item["type"] == "GPU"
    ) == 1
    assert rows[2]["privileged"] is True


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

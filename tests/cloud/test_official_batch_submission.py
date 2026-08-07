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


def test_official_runtime_enables_batch_invariance() -> None:
    rows = MODULE._official_runtime_environment(
        action_id="official-action",
        run_spec_sha256="5" * 64,
        output_uri="s3://bucket/outputs",
    )
    environment = {row["name"]: row["value"] for row in rows}
    assert environment["VLLM_BATCH_INVARIANT"] == "1"


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


class _BatchAutoScaling:
    def __init__(self) -> None:
        self.update = None

    def describe_auto_scaling_groups(self, **kwargs):
        assert kwargs == {}
        return {
            "AutoScalingGroups": [
                {
                    "AutoScalingGroupName": "batch-generated-asg",
                    "Tags": [{"Key": "ActionId", "Value": "action-r5"}],
                    "MixedInstancesPolicy": {
                        "LaunchTemplate": {
                            "LaunchTemplateSpecification": {
                                "LaunchTemplateId": "lt-123",
                                "LaunchTemplateName": "duplicate-provider-field",
                                "Version": "1",
                            },
                            "Overrides": [{"InstanceType": "g6e.2xlarge"}],
                        },
                        "InstancesDistribution": {
                            "OnDemandPercentageAboveBaseCapacity": 0,
                            "SpotAllocationStrategy": "price-capacity-optimized",
                            "SpotMaxPrice": "2.24208",
                        },
                    },
                }
            ]
        }

    def update_auto_scaling_group(self, **kwargs):
        self.update = kwargs


def test_batch_spot_cap_is_pinned_without_losing_generated_policy() -> None:
    autoscaling = _BatchAutoScaling()

    name = MODULE._pin_batch_spot_price(autoscaling, "action-r5", deadline=float("inf"))

    assert name == "batch-generated-asg"
    assert autoscaling.update["AutoScalingGroupName"] == name
    policy = autoscaling.update["MixedInstancesPolicy"]
    assert policy["InstancesDistribution"]["SpotMaxPrice"] == "5.00000"
    assert policy["InstancesDistribution"]["OnDemandPercentageAboveBaseCapacity"] == 0
    specification = policy["LaunchTemplate"]["LaunchTemplateSpecification"]
    assert specification == {"LaunchTemplateId": "lt-123", "Version": "1"}
    assert policy["LaunchTemplate"]["Overrides"] == [{"InstanceType": "g6e.2xlarge"}]


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


def _write_package(
    tmp_path: Path, *, package_action_id: str, run_spec_action_id: str
) -> tuple[Path, str, str]:
    """Build a minimal package archive with independently settable action IDs."""

    root = tmp_path / "package-root"
    root.mkdir()
    run_spec = {"action_id": run_spec_action_id, "record_kind": "cloud_production_run_spec"}
    run_spec_bytes = (
        json.dumps(run_spec, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    (root / "run-spec.json").write_bytes(run_spec_bytes)
    run_spec_sha256 = hashlib.sha256(run_spec_bytes).hexdigest()
    package_record = {
        "record_kind": "cloud_official_final_package",
        "status": "AUTHORIZED_READY_TO_SUBMIT",
        "action_id": package_action_id,
        "run_spec_ref": {
            "role": "run_spec",
            "relative_path": "run-spec.json",
            "sha256": run_spec_sha256,
            "byte_count": len(run_spec_bytes),
            "media_type": "application/json",
        },
    }
    (root / "official-package.json").write_bytes(
        (
            json.dumps(package_record, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
    )
    archive = tmp_path / "package.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        for item in sorted(root.rglob("*")):
            handle.add(item, arcname=item.relative_to(root).as_posix())
    return archive, hashlib.sha256(archive.read_bytes()).hexdigest(), run_spec_sha256


def test_direct_path_rejects_a_stale_package_action_id(tmp_path: Path) -> None:
    """Regression: r8 submitted a package whose embedded action ID was r4."""

    archive, package_sha256, run_spec_sha256 = _write_package(
        tmp_path,
        package_action_id="official-p0-step4b-c120-20260806-r4",
        run_spec_action_id="official-p0-step4b-c120-20260806-r4",
    )

    with pytest.raises(ValueError, match="official package action differs"):
        MODULE._verify_package_action_identity(
            action_id="official-p0-step4b-c120-20260807-r8",
            package=archive,
            package_sha256=package_sha256,
            run_spec_sha256=run_spec_sha256,
        )


def test_direct_path_rejects_a_stale_run_spec_action_id(tmp_path: Path) -> None:
    archive, package_sha256, run_spec_sha256 = _write_package(
        tmp_path,
        package_action_id="official-p0-step4b-c120-20260807-r9",
        run_spec_action_id="official-p0-step4b-c120-20260806-r4",
    )

    with pytest.raises(ValueError, match="run spec action differs"):
        MODULE._verify_package_action_identity(
            action_id="official-p0-step4b-c120-20260807-r9",
            package=archive,
            package_sha256=package_sha256,
            run_spec_sha256=run_spec_sha256,
        )


def test_direct_path_accepts_a_consistently_bound_package(tmp_path: Path) -> None:
    archive, package_sha256, run_spec_sha256 = _write_package(
        tmp_path,
        package_action_id="official-p0-step4b-c120-20260807-r9",
        run_spec_action_id="official-p0-step4b-c120-20260807-r9",
    )

    preflight = MODULE._verify_package_action_identity(
        action_id="official-p0-step4b-c120-20260807-r9",
        package=archive,
        package_sha256=package_sha256,
        run_spec_sha256=run_spec_sha256,
    )

    assert preflight["package_record_action_id"] == "official-p0-step4b-c120-20260807-r9"
    assert preflight["run_spec_action_id"] == "official-p0-step4b-c120-20260807-r9"


def test_direct_path_rejects_a_tampered_package_digest(tmp_path: Path) -> None:
    archive, _, run_spec_sha256 = _write_package(
        tmp_path,
        package_action_id="official-p0-step4b-c120-20260807-r9",
        run_spec_action_id="official-p0-step4b-c120-20260807-r9",
    )

    with pytest.raises(ValueError, match="differ from the supplied digest"):
        MODULE._verify_package_action_identity(
            action_id="official-p0-step4b-c120-20260807-r9",
            package=archive,
            package_sha256="0" * 64,
            run_spec_sha256=run_spec_sha256,
        )

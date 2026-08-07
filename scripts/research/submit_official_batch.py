"""Create the bounded official C120 Batch surface and submit one size-two job.

The caller supplies an already KMS-authorized immutable package. This command
does no scientific analysis or unblinding; it performs the final launch line.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import tempfile
import time
from typing import Any

from botocore.exceptions import ClientError

from pneuma_lab.cloud.production_run import ProductionRunSpec
from pneuma_lab.cloud.production_runtime import _extract_package


REGION = "us-east-1"
ACCOUNT = "892077329800"
BUCKET = "pneuma-phase-b-892077329800"
PAYLOAD_PREFIX = (
    "runs/step5b/payloads/"
    "1f738eff8667f0b863cdd8259c7bfa071ec3a37b2d9963e999f11e7dda1087e4"
)
INSTANCE_PROFILE = "arn:aws:iam::892077329800:instance-profile/pneuma-c160-worker"
BATCH_SERVICE_ROLE = "arn:aws:iam::892077329800:role/pneuma-c160-batch-service"
VPC_ID = "vpc-0577decd080525e86"
PUBLIC_SUBNET_SPECS = (
    ("us-east-1a", "10.42.100.0/24"),
    ("us-east-1b", "10.42.101.0/24"),
    ("us-east-1c", "10.42.102.0/24"),
    ("us-east-1d", "10.42.103.0/24"),
)
IMAGE_RE = re.compile(
    r"^892077329800\.dkr\.ecr\.us-east-1\.amazonaws\.com/"
    r"pneuma-official-production-(controller|model-server|benchmark-worker)"
    r"@sha256:[0-9a-f]{64}$"
)
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
ACTION_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")
CONTROLLER_MEMORY_MIB = 4_000
MODEL_SERVER_MEMORY_MIB = 46_000
BENCHMARK_WORKER_MEMORY_MIB = 12_000


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _load_images(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    roles = value.get("roles") if isinstance(value, dict) else None
    if not isinstance(roles, list):
        raise ValueError("image set has no role receipts")
    result = {
        str(row["role"]): str(row["image_ref"])
        for row in roles
        if isinstance(row, dict)
    }
    if set(result) != {"controller", "model-server", "benchmark-worker"}:
        raise ValueError("image set must bind exactly three roles")
    if any(IMAGE_RE.fullmatch(image) is None for image in result.values()):
        raise ValueError("image set contains a mutable or foreign image reference")
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tags(value: dict[str, Any]) -> dict[str, str]:
    return {
        str(row["Key"]): str(row["Value"])
        for row in value.get("Tags", [])
        if isinstance(row, dict) and "Key" in row and "Value" in row
    }


def _tag_rows(
    tags: dict[str, str], *, overrides: dict[str, str] | None = None
) -> list[dict[str, str]]:
    """Return one deterministic row per tag key, applying explicit overrides."""

    merged = dict(tags)
    merged.update(overrides or {})
    return [{"Key": key, "Value": merged[key]} for key in sorted(merged)]


def _require_owned(value: dict[str, Any], action_id: str, label: str) -> None:
    if _tags(value).get("ActionId") != action_id:
        raise RuntimeError(f"existing {label} is not owned by this action")


def _bound_json(root: Path, binding: object, label: str) -> dict[str, object]:
    if not isinstance(binding, dict):
        raise ValueError(f"{label} binding is missing")
    relative = binding.get("relative_path")
    digest = binding.get("sha256")
    byte_count = binding.get("byte_count")
    if not isinstance(relative, str) or not isinstance(digest, str):
        raise ValueError(f"{label} binding is malformed")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise ValueError(f"{label} path escapes or is absent")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest or len(raw) != byte_count:
        raise ValueError(f"{label} bytes differ from their binding")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not an object")
    return value


def _verify_authorized_package(
    *,
    action_id: str,
    package: Path,
    package_sha256: str,
    run_spec_sha256: str,
    images: dict[str, str],
) -> dict[str, object]:
    """Verify every launch-critical binding before the first AWS mutation."""

    if _sha256(package) != package_sha256:
        raise ValueError("local package bytes differ from the authorized digest")
    with tempfile.TemporaryDirectory(prefix="pneuma-official-submit-") as temporary:
        root = Path(temporary).resolve()
        _extract_package(package, root)
        package_record = json.loads((root / "official-package.json").read_text("utf-8"))
        if (
            not isinstance(package_record, dict)
            or package_record.get("record_kind") != "cloud_official_final_package"
            or package_record.get("status") != "AUTHORIZED_READY_TO_SUBMIT"
            or package_record.get("action_id") != action_id
        ):
            raise ValueError("official package is not authorized for this action")
        run_binding = package_record.get("run_spec_ref")
        run_value = _bound_json(root, run_binding, "run spec")
        if (
            not isinstance(run_binding, dict)
            or run_binding.get("sha256") != run_spec_sha256
        ):
            raise ValueError("run-spec argument differs from the package binding")
        spec = ProductionRunSpec.from_mapping(run_value)
        if spec.digest != run_spec_sha256 or spec.value.get("action_id") != action_id:
            raise ValueError("run spec is not bound to the requested action")
        spec.verify_official_authorization(run_root=root)
        launch = _bound_json(root, package_record.get("launch_plan_ref"), "launch plan")
        required_launch = {
            "action_id": action_id,
            "region": REGION,
            "array_size": 2,
            "instance_type": "g6e.2xlarge",
            "max_spot_vcpus": 16,
            "attempts": 1,
            "max_duration_seconds": 604_800,
            "max_usd": 5100.0,
            "container_resources": {
                "controller": {
                    "vcpus": 1,
                    "memory_mib": CONTROLLER_MEMORY_MIB,
                    "gpus": 0,
                },
                "model-server": {"vcpus": 1, "memory_mib": 46_000, "gpus": 1},
                "benchmark-worker": {"vcpus": 6, "memory_mib": 12_000, "gpus": 0},
            },
        }
        for key, expected in required_launch.items():
            if launch.get(key) != expected:
                raise ValueError(
                    f"launch plan {key} differs from the registered surface"
                )
        if launch.get("submission_source_sha256") != _sha256(Path(__file__).resolve()):
            raise ValueError("launch plan is not bound to this submission source")
        cleanup_source = Path(__file__).resolve().with_name("cleanup_official_batch.py")
        if launch.get("cleanup_source_sha256") != _sha256(cleanup_source):
            raise ValueError("launch plan is not bound to the teardown source")
        planned_images = {
            str(row.get("role")): str(row.get("image_digest"))
            for row in launch.get("images", [])
            if isinstance(row, dict)
        }
        supplied_images = {
            role: image.rsplit("@", 1)[1] for role, image in images.items()
        }
        if planned_images != supplied_images:
            raise ValueError("image set differs from the authorized launch plan")
        authorization = _bound_json(
            root, package_record.get("authorization_ref"), "authorization"
        )
        if authorization.get("action_id") != action_id:
            raise ValueError("authorization action differs from the launch action")
        return {
            "official_package_sha256": package_sha256,
            "run_spec_sha256": run_spec_sha256,
            "launch_plan_sha256": hashlib.sha256(
                (
                    root / str(package_record["launch_plan_ref"]["relative_path"])
                ).read_bytes()
            ).hexdigest(),
            "authorization_sha256": hashlib.sha256(
                (
                    root / str(package_record["authorization_ref"]["relative_path"])
                ).read_bytes()
            ).hexdigest(),
        }


def _wait_compute(batch: Any, name: str, *, deadline: float) -> str:
    while time.monotonic() < deadline:
        values = batch.describe_compute_environments(computeEnvironments=[name]).get(
            "computeEnvironments", []
        )
        if values:
            item = values[0]
            if item.get("status") == "VALID":
                return str(item["computeEnvironmentArn"])
            if item.get("status") == "INVALID":
                raise RuntimeError(
                    f"compute environment invalid: {item.get('statusReason')}"
                )
        time.sleep(10)
    raise TimeoutError("compute environment did not become valid")


def _wait_queue(batch: Any, name: str, *, deadline: float) -> str:
    while time.monotonic() < deadline:
        values = batch.describe_job_queues(jobQueues=[name]).get("jobQueues", [])
        if values:
            item = values[0]
            if item.get("status") == "VALID":
                return str(item["jobQueueArn"])
            if item.get("status") == "INVALID":
                raise RuntimeError(f"job queue invalid: {item.get('statusReason')}")
        time.sleep(5)
    raise TimeoutError("job queue did not become valid")


def _ensure_package_object(
    s3: Any,
    *,
    bucket: str,
    key: str,
    package: Path,
    package_sha256: str,
    action_id: str,
) -> None:
    """Create once, or accept only the byte-identical action-owned object."""

    def verify_existing() -> None:
        head = s3.head_object(Bucket=bucket, Key=key)
        metadata = head.get("Metadata", {})
        if (
            head.get("ContentLength") != package.stat().st_size
            or metadata.get("sha256") != package_sha256
            or metadata.get("action-id") != action_id
        ):
            raise RuntimeError("existing official package object differs")

    try:
        verify_existing()
        return
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in {
            "404",
            "NoSuchKey",
            "NotFound",
        }:
            raise
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=package.read_bytes(),
            ServerSideEncryption="AES256",
            ContentType="application/gzip",
            IfNoneMatch="*",
            Metadata={"sha256": package_sha256, "action-id": action_id},
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in {
            "PreconditionFailed",
            "412",
        }:
            raise
        verify_existing()


def _ensure_public_network(
    ec2: Any, action_id: str, tags: dict[str, str]
) -> tuple[list[str], list[str]]:
    tag_rows = _tag_rows(tags)
    public_egress_tags = _tag_rows(
        tags, overrides={"Purpose": "official-public-egress"}
    )
    gateways = ec2.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [VPC_ID]}]
    ).get("InternetGateways", [])
    if gateways:
        gateway_id = str(gateways[0]["InternetGatewayId"])
    else:
        gateway_id = str(
            ec2.create_internet_gateway()["InternetGateway"]["InternetGatewayId"]
        )
        ec2.create_tags(Resources=[gateway_id], Tags=tag_rows)
        ec2.attach_internet_gateway(InternetGatewayId=gateway_id, VpcId=VPC_ID)

    route_tables = ec2.describe_route_tables(
        Filters=[
            {"Name": "vpc-id", "Values": [VPC_ID]},
            {"Name": "tag:ActionId", "Values": [action_id]},
            {"Name": "tag:Purpose", "Values": ["official-public-egress"]},
        ]
    ).get("RouteTables", [])
    if route_tables:
        route_table_id = str(route_tables[0]["RouteTableId"])
    else:
        route_table_id = str(
            ec2.create_route_table(VpcId=VPC_ID)["RouteTable"]["RouteTableId"]
        )
        ec2.create_tags(
            Resources=[route_table_id],
            Tags=public_egress_tags,
        )
    routes = ec2.describe_route_tables(RouteTableIds=[route_table_id])["RouteTables"][
        0
    ].get("Routes", [])
    default_route = next(
        (row for row in routes if row.get("DestinationCidrBlock") == "0.0.0.0/0"),
        None,
    )
    if default_route is None:
        ec2.create_route(
            RouteTableId=route_table_id,
            DestinationCidrBlock="0.0.0.0/0",
            GatewayId=gateway_id,
        )
    elif default_route.get("GatewayId") != gateway_id:
        ec2.replace_route(
            RouteTableId=route_table_id,
            DestinationCidrBlock="0.0.0.0/0",
            GatewayId=gateway_id,
        )

    subnet_ids: list[str] = []
    for az, cidr in PUBLIC_SUBNET_SPECS:
        matches = ec2.describe_subnets(
            Filters=[
                {"Name": "vpc-id", "Values": [VPC_ID]},
                {"Name": "cidr-block", "Values": [cidr]},
            ]
        ).get("Subnets", [])
        if matches:
            _require_owned(matches[0], action_id, "official public subnet")
            subnet_id = str(matches[0]["SubnetId"])
            if matches[0].get("AvailabilityZone") != az:
                raise RuntimeError("official public subnet CIDR is in the wrong AZ")
        else:
            subnet_id = str(
                ec2.create_subnet(
                    VpcId=VPC_ID,
                    AvailabilityZone=az,
                    CidrBlock=cidr,
                    TagSpecifications=[
                        {
                            "ResourceType": "subnet",
                            "Tags": public_egress_tags,
                        }
                    ],
                )["Subnet"]["SubnetId"]
            )
        ec2.modify_subnet_attribute(
            SubnetId=subnet_id, MapPublicIpOnLaunch={"Value": True}
        )
        associations = ec2.describe_route_tables(
            Filters=[{"Name": "association.subnet-id", "Values": [subnet_id]}]
        ).get("RouteTables", [])
        if not associations:
            ec2.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_id)
        elif associations[0]["RouteTableId"] != route_table_id:
            association = next(
                (
                    row
                    for row in associations[0].get("Associations", [])
                    if row.get("SubnetId") == subnet_id
                ),
                None,
            )
            if not isinstance(association, dict) or not association.get(
                "RouteTableAssociationId"
            ):
                raise RuntimeError("official public subnet route is ambiguous")
            ec2.replace_route_table_association(
                AssociationId=association["RouteTableAssociationId"],
                RouteTableId=route_table_id,
            )
        subnet_ids.append(subnet_id)

    group_name = f"{action_id}-egress"[:255]
    groups = ec2.describe_security_groups(
        Filters=[
            {"Name": "vpc-id", "Values": [VPC_ID]},
            {"Name": "group-name", "Values": [group_name]},
        ]
    ).get("SecurityGroups", [])
    if groups:
        _require_owned(groups[0], action_id, "official worker security group")
        group_id = str(groups[0]["GroupId"])
    else:
        group_id = str(
            ec2.create_security_group(
                GroupName=group_name,
                Description="Official study egress-only worker group",
                VpcId=VPC_ID,
                TagSpecifications=[
                    {"ResourceType": "security-group", "Tags": tag_rows}
                ],
            )["GroupId"]
        )
    if ec2.describe_security_groups(GroupIds=[group_id])["SecurityGroups"][0].get(
        "IpPermissions"
    ):
        raise RuntimeError("official worker security group unexpectedly has ingress")
    return subnet_ids, [group_id]


def _ensure_launch_template(
    ec2: Any, action_id: str, tags: dict[str, str]
) -> tuple[str, str]:
    name = f"{action_id}-worker"[:128]
    templates = ec2.describe_launch_templates(
        Filters=[{"Name": "launch-template-name", "Values": [name]}]
    ).get("LaunchTemplates", [])
    if templates:
        _require_owned(templates[0], action_id, "official worker launch template")
        template_id = str(templates[0]["LaunchTemplateId"])
        version = str(templates[0]["LatestVersionNumber"])
        return template_id, version
    tag_rows = [{"Key": key, "Value": value} for key, value in tags.items()]
    user_data = """MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="PNEUMA_BATCH"

--PNEUMA_BATCH
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -euo pipefail
if ! swapon --show=NAME --noheadings | grep -qx /swapfile; then
  fallocate -l 64G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
fi
--PNEUMA_BATCH--
"""
    response = ec2.create_launch_template(
        LaunchTemplateName=name,
        VersionDescription="official-c120-v1",
        TagSpecifications=[{"ResourceType": "launch-template", "Tags": tag_rows}],
        LaunchTemplateData={
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": True,
                        "Encrypted": True,
                        "VolumeSize": 1000,
                        "VolumeType": "gp3",
                        "Iops": 3000,
                        "Throughput": 250,
                    },
                }
            ],
            "MetadataOptions": {
                "HttpEndpoint": "enabled",
                "HttpTokens": "required",
                "HttpPutResponseHopLimit": 2,
            },
            "Monitoring": {"Enabled": True},
            "UserData": base64.b64encode(user_data.encode()).decode("ascii"),
            "TagSpecifications": [
                {
                    "ResourceType": "instance",
                    "Tags": tag_rows,
                },
                {
                    "ResourceType": "volume",
                    "Tags": tag_rows,
                },
            ],
        },
    )
    template = response["LaunchTemplate"]
    return str(template["LaunchTemplateId"]), str(template["LatestVersionNumber"])


def _container(
    *,
    name: str,
    image: str,
    command: list[str],
    vcpus: int,
    memory: int,
    essential: bool,
    environment: list[dict[str, str]],
    depends_on: list[dict[str, str]],
    gpu: bool = False,
    privileged: bool = False,
) -> dict[str, object]:
    resources = [
        {"type": "VCPU", "value": str(vcpus)},
        {"type": "MEMORY", "value": str(memory)},
    ]
    if gpu:
        resources.append({"type": "GPU", "value": "1"})
    return {
        "name": name,
        "image": image,
        "command": command,
        "essential": essential,
        "environment": environment,
        "dependsOn": depends_on,
        "privileged": privileged,
        "resourceRequirements": resources,
        "mountPoints": [
            {
                "sourceVolume": "run-root",
                "containerPath": "/run/pneuma",
                "readOnly": False,
            },
            *(
                [
                    {
                        "sourceVolume": "docker-socket",
                        "containerPath": "/var/run/docker.sock",
                        "readOnly": False,
                    }
                ]
                if name == "benchmark-worker"
                else []
            ),
        ],
    }


def _official_containers(
    *,
    images: dict[str, str],
    package_uri: str,
    package_sha256: str,
    run_spec_sha256: str,
    controller_environment: list[dict[str, str]],
    common_environment: list[dict[str, str]],
    benchmark_environment: list[dict[str, str]],
) -> list[dict[str, object]]:
    """Return the exact registered 8-vCPU/60,000-MiB/one-GPU task surface."""

    return [
        _container(
            name="controller",
            image=images["controller"],
            command=[
                "--protocol",
                "stage",
                "--package-s3-uri",
                package_uri,
                "--package-sha256",
                package_sha256,
                "--run-root",
                "/run/pneuma",
            ],
            vcpus=1,
            memory=CONTROLLER_MEMORY_MIB,
            essential=False,
            environment=controller_environment,
            depends_on=[],
        ),
        _container(
            name="model-server",
            image=images["model-server"],
            command=[
                "--protocol",
                "production",
                "--run-spec",
                "/run/pneuma/run-spec.json",
                "--run-spec-sha256",
                run_spec_sha256,
                "--run-root",
                "/run/pneuma",
            ],
            vcpus=1,
            memory=MODEL_SERVER_MEMORY_MIB,
            essential=False,
            environment=common_environment,
            depends_on=[{"containerName": "controller", "condition": "SUCCESS"}],
            gpu=True,
        ),
        _container(
            name="benchmark-worker",
            image=images["benchmark-worker"],
            command=[
                "--protocol",
                "production",
                "--run-spec",
                "/run/pneuma/run-spec.json",
                "--run-spec-sha256",
                run_spec_sha256,
                "--run-root",
                "/run/pneuma",
            ],
            vcpus=6,
            memory=BENCHMARK_WORKER_MEMORY_MIB,
            essential=True,
            environment=benchmark_environment,
            depends_on=[
                {"containerName": "controller", "condition": "SUCCESS"},
                {"containerName": "model-server", "condition": "START"},
            ],
            privileged=True,
        ),
    ]


def submit(
    *,
    action_id: str,
    package: Path,
    package_sha256: str,
    run_spec_sha256: str,
    image_set: Path,
) -> dict[str, object]:
    import boto3

    if ACTION_RE.fullmatch(action_id) is None:
        raise ValueError("invalid action ID")
    if (
        DIGEST_RE.fullmatch(package_sha256) is None
        or DIGEST_RE.fullmatch(run_spec_sha256) is None
    ):
        raise ValueError("invalid package/run-spec digest")
    images = _load_images(image_set)
    preflight = _verify_authorized_package(
        action_id=action_id,
        package=package,
        package_sha256=package_sha256,
        run_spec_sha256=run_spec_sha256,
        images=images,
    )
    s3 = boto3.client("s3", region_name=REGION)
    batch = boto3.client("batch", region_name=REGION)
    ec2 = boto3.client("ec2", region_name=REGION)
    iam = boto3.client("iam", region_name=REGION)
    package_key = f"runs/official/{action_id}/inputs/package.tar.gz"
    output_prefix = f"runs/official/{action_id}/outputs"
    package_uri = f"s3://{BUCKET}/{package_key}"
    output_uri = f"s3://{BUCKET}/{output_prefix}"
    policy_name = f"official-{action_id}"[:128]
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "OfficialInputReads",
                "Effect": "Allow",
                "Action": ["s3:GetObject"],
                "Resource": [
                    f"arn:aws:s3:::{BUCKET}/{package_key}",
                    f"arn:aws:s3:::{BUCKET}/{PAYLOAD_PREFIX}/objects/*",
                ],
            },
            {
                "Sid": "OfficialOutputReadWrite",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject"],
                "Resource": f"arn:aws:s3:::{BUCKET}/{output_prefix}/*",
            },
            {
                "Sid": "OfficialOutputList",
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": f"arn:aws:s3:::{BUCKET}",
                "Condition": {"StringLike": {"s3:prefix": [f"{output_prefix}/*"]}},
            },
        ],
    }
    _ensure_package_object(
        s3,
        bucket=BUCKET,
        key=package_key,
        package=package,
        package_sha256=package_sha256,
        action_id=action_id,
    )
    iam.put_role_policy(
        RoleName="pneuma-c160-worker",
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy, separators=(",", ":")),
    )

    tags = {
        "Project": "pneuma-lab",
        "Purpose": "official-p0-step4b",
        "ActionId": action_id,
        "RunSpecSHA256": run_spec_sha256,
    }
    subnets, security_groups = _ensure_public_network(ec2, action_id, tags)
    launch_template_id, launch_template_version = _ensure_launch_template(
        ec2, action_id, tags
    )
    compute_name = f"{action_id}-ce"
    queue_name = f"{action_id}-queue"
    definition_name = f"{action_id}-job"
    batch.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="MANAGED",
        state="ENABLED",
        serviceRole=BATCH_SERVICE_ROLE,
        computeResources={
            "type": "SPOT",
            "allocationStrategy": "SPOT_PRICE_CAPACITY_OPTIMIZED",
            "bidPercentage": 100,
            "minvCpus": 0,
            "maxvCpus": 16,
            "desiredvCpus": 0,
            "instanceTypes": ["g6e.2xlarge"],
            "subnets": subnets,
            "securityGroupIds": security_groups,
            "instanceRole": INSTANCE_PROFILE,
            "launchTemplate": {
                "launchTemplateId": launch_template_id,
                "version": launch_template_version,
            },
            "tags": tags,
            "ec2Configuration": [{"imageType": "ECS_AL2023_NVIDIA"}],
        },
        tags=tags,
    )
    deadline = time.monotonic() + 900
    compute_arn = _wait_compute(batch, compute_name, deadline=deadline)
    batch.create_job_queue(
        jobQueueName=queue_name,
        state="ENABLED",
        priority=100,
        computeEnvironmentOrder=[{"order": 1, "computeEnvironment": compute_arn}],
        tags=tags,
    )
    queue_arn = _wait_queue(batch, queue_name, deadline=deadline)
    common_environment = [
        {"name": "PNEUMA_RUN_SPEC_SHA256", "value": run_spec_sha256},
        {"name": "PNEUMA_OUTPUT_S3_URI", "value": output_uri},
        {"name": "PNEUMA_HOST_RUN_ROOT", "value": f"/var/lib/{action_id}"},
        {"name": "VLLM_BATCH_INVARIANT", "value": "1"},
    ]
    controller_environment = [
        *common_environment,
        {"name": "PNEUMA_PAYLOAD_BUCKET", "value": BUCKET},
        {"name": "PNEUMA_PAYLOAD_PREFIX", "value": PAYLOAD_PREFIX},
    ]
    benchmark_environment = [
        *common_environment,
        {
            "name": "PNEUMA_BENCHMARK_WORKER_IMAGE_REF",
            "value": images["benchmark-worker"],
        },
    ]
    containers = _official_containers(
        images=images,
        package_uri=package_uri,
        package_sha256=package_sha256,
        run_spec_sha256=run_spec_sha256,
        controller_environment=controller_environment,
        common_environment=common_environment,
        benchmark_environment=benchmark_environment,
    )
    definition = batch.register_job_definition(
        jobDefinitionName=definition_name,
        type="container",
        platformCapabilities=["EC2"],
        ecsProperties={
            "taskProperties": [
                {
                    "containers": containers,
                    "volumes": [
                        {
                            "name": "run-root",
                            "host": {"sourcePath": f"/var/lib/{action_id}"},
                        },
                        {
                            "name": "docker-socket",
                            "host": {"sourcePath": "/var/run/docker.sock"},
                        },
                    ],
                }
            ]
        },
        retryStrategy={"attempts": 1},
        timeout={"attemptDurationSeconds": 604_800},
        propagateTags=True,
        tags=tags,
    )
    definition_arn = str(definition["jobDefinitionArn"])
    submitted = batch.submit_job(
        jobName=action_id,
        jobQueue=queue_arn,
        jobDefinition=definition_arn,
        arrayProperties={"size": 2},
        propagateTags=True,
        tags=tags,
    )
    receipt = {
        "record_kind": "cloud_official_batch_submission_receipt",
        "schema_version": "0.1.0",
        "action_id": action_id,
        "region": REGION,
        "package_s3_uri": package_uri,
        "package_sha256": package_sha256,
        "run_spec_sha256": run_spec_sha256,
        "compute_environment_arn": compute_arn,
        "job_queue_arn": queue_arn,
        "job_definition_arn": definition_arn,
        "array_job_id": submitted["jobId"],
        "array_size": 2,
        "max_spot_vcpus": 16,
        "public_subnets": subnets,
        "security_group_ids": security_groups,
        "launch_template_id": launch_template_id,
        "launch_template_version": launch_template_version,
        "root_volume_gib": 1000,
        "attempts": 1,
        "preflight": preflight,
        "status": "SUBMITTED",
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--package-sha256", required=True)
    parser.add_argument("--run-spec-sha256", required=True)
    parser.add_argument("--image-set", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = submit(
        action_id=args.action_id,
        package=args.package,
        package_sha256=args.package_sha256,
        run_spec_sha256=args.run_spec_sha256,
        image_set=args.image_set,
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_bytes(_canonical(receipt))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

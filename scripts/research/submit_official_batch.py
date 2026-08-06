"""Create the bounded official C120 Batch surface and submit one size-two job.

The caller supplies an already KMS-authorized immutable package. This command
does no scientific analysis or unblinding; it performs the final launch line.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any


REGION = "us-east-1"
ACCOUNT = "892077329800"
BUCKET = "pneuma-phase-b-892077329800"
PAYLOAD_PREFIX = (
    "runs/step5b/payloads/"
    "1f738eff8667f0b863cdd8259c7bfa071ec3a37b2d9963e999f11e7dda1087e4"
)
INSTANCE_PROFILE = "arn:aws:iam::892077329800:instance-profile/pneuma-c160-worker"
BATCH_SERVICE_ROLE = "arn:aws:iam::892077329800:role/pneuma-c160-batch-service"
SUBNETS = ["subnet-042e433905daddc0b", "subnet-0a0e7c9c04b87ba58"]
SECURITY_GROUPS = ["sg-08428ae82a7e2fd35"]
IMAGE_RE = re.compile(
    r"^892077329800\.dkr\.ecr\.us-east-1\.amazonaws\.com/"
    r"pneuma-official-production-(controller|model-server|benchmark-worker)"
    r"@sha256:[0-9a-f]{64}$"
)
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
ACTION_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")


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


def _wait_compute(batch: Any, name: str, *, deadline: float) -> str:
    while time.monotonic() < deadline:
        values = batch.describe_compute_environments(
            computeEnvironments=[name]
        ).get("computeEnvironments", [])
        if values:
            item = values[0]
            if item.get("status") == "VALID":
                return str(item["computeEnvironmentArn"])
            if item.get("status") == "INVALID":
                raise RuntimeError(f"compute environment invalid: {item.get('statusReason')}")
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
                "readOnly": name == "model-server",
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
    if DIGEST_RE.fullmatch(package_sha256) is None or DIGEST_RE.fullmatch(
        run_spec_sha256
    ) is None:
        raise ValueError("invalid package/run-spec digest")
    if hashlib.sha256(package.read_bytes()).hexdigest() != package_sha256:
        raise ValueError("local package bytes differ from the authorized digest")
    images = _load_images(image_set)
    s3 = boto3.client("s3", region_name=REGION)
    batch = boto3.client("batch", region_name=REGION)
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
                "Sid": "OfficialOutputWrites",
                "Effect": "Allow",
                "Action": ["s3:PutObject"],
                "Resource": f"arn:aws:s3:::{BUCKET}/{output_prefix}/*",
            },
        ],
    }
    s3.put_object(
        Bucket=BUCKET,
        Key=package_key,
        Body=package.read_bytes(),
        ServerSideEncryption="AES256",
        ContentType="application/gzip",
        IfNoneMatch="*",
        Metadata={"sha256": package_sha256, "action-id": action_id},
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
            "minvCpus": 0,
            "maxvCpus": 16,
            "desiredvCpus": 0,
            "instanceTypes": ["g6e.2xlarge"],
            "subnets": SUBNETS,
            "securityGroupIds": SECURITY_GROUPS,
            "instanceRole": INSTANCE_PROFILE,
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
    ]
    controller_environment = [
        *common_environment,
        {"name": "PNEUMA_PAYLOAD_BUCKET", "value": BUCKET},
        {"name": "PNEUMA_PAYLOAD_PREFIX", "value": PAYLOAD_PREFIX},
    ]
    containers = [
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
            memory=2000,
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
            memory=46000,
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
            memory=12000,
            essential=True,
            environment=common_environment,
            depends_on=[
                {"containerName": "controller", "condition": "SUCCESS"},
                {"containerName": "model-server", "condition": "START"},
            ],
            privileged=True,
        ),
    ]
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
        timeout={"attemptDurationSeconds": 1_200_000},
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
        "attempts": 1,
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

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.authorization_keys import canonical_ledger_digest
from pneuma_lab.cloud import fixed_admission_probe
from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.fixed_admission_probe import (
    build_probe_argv,
    build_raw_measurement,
    run_probe,
)
from pneuma_lab.cloud.interruption import run_canonical_interruption_drill
from pneuma_lab.cloud.qualification_execution import (
    AwsCliAdapter,
    input_manifest_digest,
    materialize_authenticated_inputs,
    parse_s3_uri,
    parse_terraform_show,
    publish_raw_measurement,
    require_array_evidence,
    require_two_succeeded_children,
    retrieve_raw_measurement,
    verify_provider_bindings,
    worker_artifact_uri,
)

from .test_authorization_keys import LEDGER, _authorization, _keypair, _lock, _registry


class FakeAwsTransport:
    """In-memory S3/provider transport with the same boundaries as AWS CLI."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.get_calls: list[tuple[str, str]] = []
        self.put_calls: list[tuple[str, str, str]] = []
        self.submissions: list[dict] = []
        self.jobs: list[dict] = []
        self.freeze_calls = 0
        self.restore_calls = 0
        self.residual: list[dict] = []

    def get_object(self, bucket: str, key: str) -> bytes:
        self.get_calls.append((bucket, key))
        try:
            return self.objects[(bucket, key)]
        except KeyError as exc:
            raise CloudManifestError(
                f"missing fake object s3://{bucket}/{key}"
            ) from exc

    def put_object(
        self, bucket: str, key: str, payload: bytes, *, if_none_match: str
    ) -> None:
        if if_none_match != "*":
            raise CloudManifestError(
                "fake transport requires immutable object publication"
            )
        if (bucket, key) in self.objects:
            raise CloudManifestError("fake S3 object already exists")
        self.objects[(bucket, key)] = payload
        self.put_calls.append((bucket, key, hashlib.sha256(payload).hexdigest()))

    def submit_array_job(self, **kwargs):
        self.submissions.append(kwargs)
        return {
            "jobId": "parent-001",
            "arrayProperties": {"size": kwargs["array_size"]},
        }

    def describe_jobs(self, job_ids):
        return list(self.jobs)

    def get_caller_identity(self):
        return {
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:role/qualification-reader",
        }

    def get_role(self, role_name):
        roles = {
            "pneuma-worker": "arn:aws:iam::123456789012:role/pneuma-worker",
            "pneuma-batch": "arn:aws:iam::123456789012:role/pneuma-batch",
            "pneuma-spot": "arn:aws:iam::123456789012:role/pneuma-spot",
        }
        return {
            "Role": {
                "RoleName": role_name,
                "Arn": roles[role_name],
            }
        }

    def get_instance_profile(self, profile_name):
        return {
            "InstanceProfile": {
                "InstanceProfileName": profile_name,
                "Arn": f"arn:aws:iam::123456789012:instance-profile/{profile_name}",
                "Roles": [
                    {
                        "RoleName": "pneuma-worker",
                        "Arn": "arn:aws:iam::123456789012:role/pneuma-worker",
                    }
                ],
            }
        }

    def describe_subnets(self, subnet_ids):
        return [
            {
                "SubnetId": value,
                "VpcId": "vpc-12345678",
                "AvailabilityZone": f"us-east-1{chr(ord('a') + index)}",
                "State": "available",
            }
            for index, value in enumerate(subnet_ids)
        ]

    def describe_security_groups(self, group_ids):
        return [
            {"GroupId": value, "VpcId": "vpc-12345678", "IpPermissions": []}
            for value in group_ids
        ]

    def freeze(self, *, job_ids, boundary):
        self.freeze_calls += 1
        return {"completed": True, "boundary": boundary}

    def restore(self, *, job_ids, boundary):
        self.restore_calls += 1
        return {
            "completed": True,
            "boundary": boundary,
            "all_arm_visible_bytes_match": True,
        }

    def list_tagged_resources(self, *, action_id):
        return list(self.residual)


def adapter(transport: FakeAwsTransport) -> AwsCliAdapter:
    return AwsCliAdapter(transport=transport)


def _rungs() -> dict[str, dict]:
    samples = [
        {
            "index": index,
            "elapsed_seconds": 1.0,
            "generated_tokens": 128,
            "output_token_ids_sha256": "1" * 64,
        }
        for index in range(10)
    ]
    tool_calls = [
        {
            "fixture_id": f"fixture-{index}",
            "raw_response_text": "{}",
            "name": "qualification_call",
            "arguments": {},
        }
        for index in range(4)
    ]
    parity = [
        {
            "fixture_id": f"parity-{index}",
            "first_output_token_ids": list(range(32)),
            "second_output_token_ids": list(range(32)),
        }
        for index in range(4)
    ]
    return {
        name: {
            "peak_allocated_bytes": 40,
            "throughput": {
                "p10_method": "nearest_rank",
                "warmup_samples": 1,
                "output_tokens_per_sample": 128,
                "samples": samples,
            },
            "tool_calls": tool_calls,
            "output_parity": parity,
        }
        for name in ("l40s-tp1-32768", "l40s-tp1-65536")
    }


def test_s3_is_an_object_locator_and_worker_outputs_are_distinct() -> None:
    assert (
        parse_s3_uri("s3://bucket/runs/action/input.json").key
        == "runs/action/input.json"
    )
    with pytest.raises(CloudManifestError):
        parse_s3_uri("s3://bucket/runs/../input.json")
    assert worker_artifact_uri("s3://bucket/runs/action", 0).endswith(
        "worker-0/raw-measurement.json"
    )
    assert worker_artifact_uri("s3://bucket/runs/action", 1).endswith(
        "worker-1/raw-measurement.json"
    )


def test_authenticated_inputs_materialize_as_readable_local_files(
    tmp_path: Path,
) -> None:
    transport = FakeAwsTransport()
    remote = b"authenticated input bytes"
    artifact = {
        "s3_uri": "s3://bucket/runs/action/input.bin",
        "relative_path": "inputs/input.bin",
        "size_bytes": len(remote),
        "sha256": hashlib.sha256(remote).hexdigest(),
    }
    location = parse_s3_uri(artifact["s3_uri"])
    transport.objects[(location.bucket, location.key)] = remote
    lock = _lock()
    private = _keypair()
    authorization = _authorization(
        private,
        lock,
        input_manifest_sha256=input_manifest_digest([artifact]),
        spend_history_sha256=canonical_ledger_digest(LEDGER),
    )
    installed = materialize_authenticated_inputs(
        [artifact],
        destination=tmp_path / "materialized",
        adapter=adapter(transport),
        authorization=authorization,
        lock=lock,
        key_registry=_registry(private),
        ledger_path=LEDGER,
    )
    path = installed["inputs/input.bin"]
    assert path.is_file() and path.read_bytes() == remote
    assert not str(path).startswith("s3://")
    assert transport.get_calls == [("bucket", "runs/action/input.bin")]


def test_input_digest_or_spend_authority_tampering_is_rejected(tmp_path: Path) -> None:
    transport = FakeAwsTransport()
    payload = b"authorized"
    artifact = {
        "s3_uri": "s3://bucket/runs/action/input.bin",
        "relative_path": "input.bin",
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    location = parse_s3_uri(artifact["s3_uri"])
    transport.objects[(location.bucket, location.key)] = payload
    lock = _lock()
    private = _keypair()
    authorization = _authorization(
        private,
        lock,
        input_manifest_sha256=input_manifest_digest([artifact]),
        spend_history_sha256="0" * 64,
    )
    with pytest.raises(CloudManifestError, match="spend history"):
        materialize_authenticated_inputs(
            [artifact],
            destination=tmp_path / "materialized",
            adapter=adapter(transport),
            authorization=authorization,
            lock=lock,
            key_registry=_registry(private),
            ledger_path=LEDGER,
        )
    assert transport.get_calls == []


def test_raw_measurements_are_immutable_and_retrievable_per_worker() -> None:
    transport = FakeAwsTransport()
    client = adapter(transport)
    prefix = "s3://bucket/runs/action"

    def raw(worker_index: int) -> bytes:
        return json.dumps(
            {
                "record_kind": "cloud_worker_admission_measurement",
                "schema_version": "0.2.0",
                "protocol_sha256": "a" * 64,
                "architecture_sha256": "b" * 64,
                "authorization_sha256": "c" * 64,
                "image_sha256": "d" * 64,
                "input_lock_sha256": "e" * 64,
                "code_sha256": "f" * 64,
                "worker_index": worker_index,
                "instance_id": f"i-0123456789abcdef{worker_index}",
                "qualification_code_sha256": "0" * 64,
                "inputs": [{"path": "input.json", "size_bytes": 2, "sha256": "0" * 64}],
                "runtime": {
                    "model": "fixture",
                    "revision": "fixture",
                    "cuda_name": "NVIDIA L40S",
                    "cuda_total_memory_bytes": 1,
                    "torch_version": "fixture",
                    "vllm_version": "fixture",
                },
                "rungs": _rungs(),
            },
            sort_keys=True,
        ).encode()

    first = raw(0)
    second = raw(1)
    first_receipt = publish_raw_measurement(
        client, artifact_prefix=prefix, worker_index=0, raw_bytes=first
    )
    second_receipt = publish_raw_measurement(
        client, artifact_prefix=prefix, worker_index=1, raw_bytes=second
    )
    assert first_receipt["uri"] != second_receipt["uri"]
    assert (
        retrieve_raw_measurement(client, artifact_prefix=prefix, worker_index=0)
        == first
    )
    assert (
        retrieve_raw_measurement(client, artifact_prefix=prefix, worker_index=1)
        == second
    )
    with pytest.raises(CloudManifestError, match="already exists"):
        publish_raw_measurement(
            client, artifact_prefix=prefix, worker_index=0, raw_bytes=first
        )


def test_probe_requires_code_local_inputs_and_worker_specific_publication(
    tmp_path: Path,
) -> None:
    transport = FakeAwsTransport()
    input_path = tmp_path / "input.json"
    input_path.write_text("{}", encoding="utf-8")
    prefix = "s3://bucket/runs/action"
    output_uri = worker_artifact_uri(prefix, 1)
    payload = run_probe(
        code="signed-code",
        worker_index=1,
        instance_id="i-0123456789abcdef0",
        protocol_sha256="a" * 64,
        architecture_sha256="b" * 64,
        authorization_sha256="c" * 64,
        image_sha256="d" * 64,
        input_lock_sha256="e" * 64,
        code_sha256="f" * 64,
        input_paths=[input_path],
        rungs=_rungs(),
        output=tmp_path / "raw.json",
        adapter=adapter(transport),
        output_uri=output_uri,
        artifact_prefix=prefix,
    )
    assert (
        json.loads(payload)["qualification_code_sha256"]
        == hashlib.sha256(b"signed-code").hexdigest()
    )
    assert (
        "bucket",
        "runs/action/worker-1/raw-measurement.json",
        hashlib.sha256(payload).hexdigest(),
    ) in transport.put_calls
    with pytest.raises(CloudManifestError, match="--code"):
        build_probe_argv("")
    with pytest.raises(CloudManifestError, match="local file"):
        run_probe(
            code="signed-code",
            worker_index=0,
            instance_id="i-0123456789abcdef0",
            protocol_sha256="a" * 64,
            architecture_sha256="b" * 64,
            authorization_sha256="c" * 64,
            image_sha256="d" * 64,
            input_lock_sha256="e" * 64,
            code_sha256="f" * 64,
            input_paths=["s3://bucket/runs/action/input.json"],
            rungs={"l40s-tp1-32768": {}, "l40s-tp1-65536": {}},
            output=tmp_path / "bad.json",
        )


def test_fixed_entrypoint_materializes_bound_files_and_publishes_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = FakeAwsTransport()
    client = adapter(transport)
    prefix = "s3://bucket/runs/action"
    code_uri = f"{prefix}/qualification.py"
    bindings = {
        "QUALIFICATION_CODE": code_uri,
        "QUALIFICATION_PROTOCOL": f"{prefix}/protocol.json",
        "QUALIFICATION_ARCHITECTURE": f"{prefix}/architecture.json",
        "QUALIFICATION_AUTHORIZATION": f"{prefix}/authorization.json",
        "QUALIFICATION_IMAGE": f"{prefix}/image.json",
        "QUALIFICATION_INPUT_LOCK": f"{prefix}/input-lock.json",
    }
    payloads = {
        code_uri: b"signed qualification fixture\n",
        bindings["QUALIFICATION_PROTOCOL"]: b"protocol\n",
        bindings["QUALIFICATION_ARCHITECTURE"]: b"architecture\n",
        bindings["QUALIFICATION_AUTHORIZATION"]: b"authorization\n",
        bindings["QUALIFICATION_IMAGE"]: b"image\n",
        bindings["QUALIFICATION_INPUT_LOCK"]: b"input-lock\n",
    }
    for uri, payload in payloads.items():
        location = parse_s3_uri(uri)
        transport.objects[(location.bucket, location.key)] = payload

    environment = {
        **bindings,
        "AWS_BATCH_JOB_ARRAY_INDEX": "1",
        "QUALIFICATION_ARTIFACT_PREFIX": prefix,
        "QUALIFICATION_MODEL": "fixture-only-cuda",
        "QUALIFICATION_MODEL_REVISION": "fixture-only-v1",
    }
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(fixed_admission_probe, "AwsCliAdapter", lambda: client)

    def fake_probe() -> None:
        def option(flag: str) -> Path:
            index = sys.argv.index(flag)
            return Path(sys.argv[index + 1])

        code_path = option("--code")
        input_paths = [
            option(flag)
            for flag in (
                "--protocol",
                "--architecture",
                "--authorization",
                "--image",
                "--input-lock",
            )
        ]
        assert all(path.is_file() for path in (code_path, *input_paths))
        assert all(
            not str(path).startswith("s3://")
            for path in (code_path, *input_paths)
        )
        record = build_raw_measurement(
            code=code_path.read_text(encoding="utf-8"),
            worker_index=1,
            instance_id="i-0123456789abcdef1",
            protocol_sha256=hashlib.sha256(input_paths[0].read_bytes()).hexdigest(),
            architecture_sha256=hashlib.sha256(input_paths[1].read_bytes()).hexdigest(),
            authorization_sha256=hashlib.sha256(input_paths[2].read_bytes()).hexdigest(),
            image_sha256=hashlib.sha256(input_paths[3].read_bytes()).hexdigest(),
            input_lock_sha256=hashlib.sha256(input_paths[4].read_bytes()).hexdigest(),
            code_sha256=hashlib.sha256(code_path.read_bytes()).hexdigest(),
            input_paths=input_paths,
            rungs=_rungs(),
        )
        output = option("--output")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_bytes(record) + b"\n")

    from pneuma_lab.cloud import dual_worker_admission_probe

    monkeypatch.setattr(dual_worker_admission_probe, "main", fake_probe)
    assert fixed_admission_probe.main(["--code", code_uri]) == 0

    retrieved = retrieve_raw_measurement(
        client,
        artifact_prefix=prefix,
        worker_index=1,
    )
    assert json.loads(retrieved)["worker_index"] == 1
    assert len(transport.put_calls) == 1
    assert transport.put_calls[0][1] == "runs/action/worker-1/raw-measurement.json"


def test_submit_and_children_are_exactly_two_successful_first_attempts() -> None:
    transport = FakeAwsTransport()
    response = adapter(transport).submit_array_job(
        job_name="fixed-admission",
        job_queue="queue",
        job_definition="definition",
        environment={
            "QUALIFICATION_CODE": "code",
            "QUALIFICATION_ACTION_ID": "action",
            "QUALIFICATION_ARTIFACT_PREFIX": "s3://bucket/runs/action",
        },
    )
    assert response["arrayProperties"]["size"] == 2
    assert "command" not in transport.submissions[0]
    children = [
        {
            "jobId": "child-0",
            "status": "SUCCEEDED",
            "arrayProperties": {"index": 0},
            "attempts": [{}],
        },
        {
            "jobId": "child-1",
            "status": "SUCCEEDED",
            "arrayProperties": {"index": 1},
            "attempts": [{}],
        },
    ]
    transport.jobs = [{"jobId": "parent-001", "status": "SUCCEEDED"}, *children]
    assert (
        require_array_evidence(
            adapter(transport),
            parent_job_id="parent-001",
            child_job_ids=["child-0", "child-1"],
        )[1]["index"]
        == 1
    )
    assert (
        require_two_succeeded_children(children, parent_status="SUCCEEDED")[0]["job_id"]
        == "child-0"
    )
    transport.jobs = [{"jobId": "parent-001", "status": "SUCCEEDED"}]
    with pytest.raises(CloudManifestError, match="missing"):
        require_array_evidence(
            adapter(transport),
            parent_job_id="parent-001",
            child_job_ids=["child-0", "child-1"],
        )
    with pytest.raises(CloudManifestError, match="exactly one attempt"):
        require_two_succeeded_children(
            [{**children[0], "attempts": [{}, {}]}, children[1]],
            parent_status="SUCCEEDED",
        )
    with pytest.raises(CloudManifestError, match="succeeded array parent"):
        require_two_succeeded_children(children, parent_status=None)


def test_terraform_and_image_contract_preserve_qualification_tags_and_entrypoint() -> (
    None
):
    terraform = Path(__file__).resolve().parents[2] / "infra/terraform/main.tf"
    dockerfile = terraform.parent.parent / "docker/qualification-worker/Dockerfile"
    entrypoint = dockerfile.parent / "fixed_admission_entrypoint.sh"
    main = terraform.read_text(encoding="utf-8")
    assert "qualification_tags" in main
    assert "QualificationCode" in main and "QualificationActionId" in main
    assert 'resource_type = "volume"' in main
    assert 'resource_type = "instance"' in main
    assert 'name = "QUALIFICATION_CODE"' in main
    assert "command = []" not in main
    assert 'CMD ["inspect"]' not in dockerfile.read_text(encoding="utf-8")
    dockerfile_text = dockerfile.read_text(encoding="utf-8")
    assert "https://archive.ubuntu.com" in dockerfile_text
    assert "https://security.ubuntu.com" in dockerfile_text
    assert "apt-get install --yes --no-install-recommends" in dockerfile_text
    assert "awscli-exe-linux-x86_64.zip" in dockerfile_text
    assert "--install-dir /usr/local/aws-cli" in dockerfile_text
    assert "COPY schemas /opt/schemas" in dockerfile_text
    assert "cloud-worker-admission-measurement.schema.json" in dockerfile_text
    assert (
        'ENTRYPOINT ["/opt/pneuma/fixed_admission_entrypoint.sh"]' in dockerfile_text
    )
    assert '--code "$QUALIFICATION_CODE"' in entrypoint.read_text(encoding="utf-8")


def test_provider_checks_are_explicit_and_plan_values_bind_action_id() -> None:
    document = {
        "format_version": "1.0",
        "variables": {
            "region": {"value": "us-east-1"},
            "qualification_code": {"value": "signed-code"},
            "qualification_action_id": {"value": "fixed-admission-001"},
            "instance_role_arn": {
                "value": "arn:aws:iam::123456789012:instance-profile/pneuma-worker"
            },
            "batch_service_role_arn": {
                "value": "arn:aws:iam::123456789012:role/pneuma-batch"
            },
            "spot_fleet_role_arn": {
                "value": "arn:aws:iam::123456789012:role/pneuma-spot"
            },
            "gpu_worker_image": {
                "value": "registry.example.invalid/worker@sha256:" + "a" * 64
            },
            "qualification_model": {"value": "fixture-only-cuda"},
            "qualification_model_revision": {"value": "fixture-only-v1"},
            "protocol_path": {
                "value": "s3://bucket/runs/qualification/fixed-admission-001/inputs/protocol.json"
            },
            "architecture_path": {
                "value": "s3://bucket/runs/qualification/fixed-admission-001/inputs/architecture.json"
            },
            "authorization_path": {
                "value": "s3://bucket/runs/qualification/fixed-admission-001/inputs/authorization.json"
            },
            "image_path": {
                "value": "s3://bucket/runs/qualification/fixed-admission-001/inputs/image.json"
            },
            "input_lock_path": {
                "value": "s3://bucket/runs/qualification/fixed-admission-001/inputs/input-lock.json"
            },
            "output_path": {
                "value": "s3://bucket/runs/qualification/fixed-admission-001/outputs/"
            },
            "subnet_ids": {
                "value": [
                    "subnet-0123456789abcdef0",
                    "subnet-0123456789abcdef1",
                    "subnet-0123456789abcdef2",
                    "subnet-0123456789abcdef3",
                ]
            },
            "security_group_ids": {"value": ["sg-0123456789abcdef0"]},
        },
        "planned_values": {
            "root_module": {
                "resources": [
                    {
                        "address": "aws_batch_compute_environment.worker[0]",
                        "values": {
                            "compute_resources": [
                                {
                                    "type": "SPOT",
                                    "allocation_strategy": "SPOT_PRICE_CAPACITY_OPTIMIZED",
                                    "min_vcpus": 0,
                                    "desired_vcpus": 0,
                                    "instance_type": ["g6e.2xlarge"],
                                    "max_vcpus": 16,
                                    "instance_role": "arn:aws:iam::123456789012:instance-profile/pneuma-worker",
                                    "spot_iam_fleet_role": "arn:aws:iam::123456789012:role/pneuma-spot",
                                    "subnets": [
                                        "subnet-0123456789abcdef0",
                                        "subnet-0123456789abcdef1",
                                        "subnet-0123456789abcdef2",
                                        "subnet-0123456789abcdef3",
                                    ],
                                    "security_group_ids": ["sg-0123456789abcdef0"],
                                    "tags": {
                                        "QualificationCode": "signed-code",
                                        "QualificationActionId": "fixed-admission-001",
                                    },
                                }
                            ],
                            "service_role": "arn:aws:iam::123456789012:role/pneuma-batch",
                        },
                    },
                    {
                        "address": "aws_batch_job_definition.gpu_worker",
                        "values": {
                            "tags": {
                                "QualificationCode": "signed-code",
                                "QualificationActionId": "fixed-admission-001",
                            },
                            "timeout": [{"attempt_duration_seconds": 3600}],
                            "retry_strategy": [{"attempts": 1}],
                            "container_properties": json.dumps(
                                {
                                    "image": "registry.example.invalid/worker@sha256:"
                                    + "a" * 64,
                                    "resourceRequirements": [
                                        {"type": "GPU", "value": "1"},
                                        {"type": "VCPU", "value": "8"},
                                        {"type": "MEMORY", "value": "60000"},
                                    ],
                                    "environment": [
                                        {
                                            "name": "QUALIFICATION_CODE",
                                            "value": "signed-code",
                                        },
                                        {
                                            "name": "QUALIFICATION_ACTION_ID",
                                            "value": "fixed-admission-001",
                                        },
                                        {
                                            "name": "QUALIFICATION_ARTIFACT_PREFIX",
                                            "value": "s3://bucket/runs/qualification/fixed-admission-001/outputs/",
                                        },
                                        {"name": "QUALIFICATION_MODEL", "value": "fixture-only-cuda"},
                                        {"name": "QUALIFICATION_MODEL_REVISION", "value": "fixture-only-v1"},
                                        {"name": "QUALIFICATION_PROTOCOL", "value": "s3://bucket/runs/qualification/fixed-admission-001/inputs/protocol.json"},
                                        {"name": "QUALIFICATION_ARCHITECTURE", "value": "s3://bucket/runs/qualification/fixed-admission-001/inputs/architecture.json"},
                                        {"name": "QUALIFICATION_AUTHORIZATION", "value": "s3://bucket/runs/qualification/fixed-admission-001/inputs/authorization.json"},
                                        {"name": "QUALIFICATION_IMAGE", "value": "s3://bucket/runs/qualification/fixed-admission-001/inputs/image.json"},
                                        {"name": "QUALIFICATION_INPUT_LOCK", "value": "s3://bucket/runs/qualification/fixed-admission-001/inputs/input-lock.json"},
                                        {"name": "QUALIFICATION_OUTPUT_ROOT", "value": "s3://bucket/runs/qualification/fixed-admission-001/outputs/"},
                                    ],
                                }
                            ),
                        },
                    },
                    {
                        "address": "aws_launch_template.worker",
                        "values": {
                            "image_id": None,
                            "tag_specifications": [
                                {
                                    "resource_type": "instance",
                                    "tags": {
                                        "QualificationCode": "signed-code",
                                        "QualificationActionId": "fixed-admission-001",
                                    },
                                },
                                {
                                    "resource_type": "volume",
                                    "tags": {
                                        "QualificationCode": "signed-code",
                                        "QualificationActionId": "fixed-admission-001",
                                    },
                                },
                            ]
                        },
                    },
                    {
                        "address": "aws_batch_job_queue.qualification",
                        "values": {
                            "tags": {
                                "QualificationCode": "signed-code",
                                "QualificationActionId": "fixed-admission-001",
                            }
                        },
                    },
                    {
                        "address": "aws_iam_role.worker",
                        "values": {"name": "pneuma-worker", "arn": None},
                    },
                ]
            }
        },
        "resource_changes": [
            {
                "address": "aws_batch_compute_environment.worker[0]",
                "change": {"actions": ["create"]},
            },
            {
                "address": "aws_batch_job_definition.gpu_worker[0]",
                "change": {"actions": ["create"]},
            },
            {
                "address": "aws_launch_template.worker",
                "change": {"actions": ["create"]},
            },
            {"address": "aws_iam_role.worker", "change": {"actions": ["create"]}},
        ],
    }
    plan = parse_terraform_show(document)
    transport = FakeAwsTransport()
    verified = verify_provider_bindings(adapter(transport), plan)
    assert verified["role"]["RoleName"] == "pneuma-worker"
    tampered = copy.deepcopy(document)
    tampered_container = json.loads(
        tampered["planned_values"]["root_module"]["resources"][1]["values"][
            "container_properties"
        ]
    )
    tampered_container["environment"][0]["value"] = "different"
    tampered["planned_values"]["root_module"]["resources"][1]["values"][
        "container_properties"
    ] = json.dumps(tampered_container)
    with pytest.raises(CloudManifestError, match="QUALIFICATION_"):
        parse_terraform_show(tampered)


def test_recovery_requires_freeze_restore_and_validates_receipt() -> None:
    class DescribeOnly:
        def describe_jobs(self, job_ids):
            return [{"jobId": "job-1", "status": "SUCCEEDED"}]

    with pytest.raises(CloudManifestError, match="freeze"):
        run_canonical_interruption_drill(
            DescribeOnly(),
            plan_sha256="a" * 64,
            input_lock_sha256="b" * 64,
            account_id="123456789012",
            region="us-east-1",
            drill_id="fixed-admission-001",
            controller_identity_arn="arn:aws:iam::123456789012:role/controller",
            watcher_identity_arn="arn:aws:iam::123456789012:role/watcher",
            lease={
                "key": "k",
                "issued_timestamp": "2026-08-01T00:00:00Z",
                "expires_timestamp": "2026-08-01T00:01:00Z",
                "watcher_observed_timestamp": "2026-08-01T00:01:01Z",
                "controller_renewal_count": 0,
            },
            job_ids=["job-1"],
            completed_boundary=b"boundary",
            resources_before=[
                {
                    "resource_id": "i-0123456789abcdef0",
                    "resource_type": "compute",
                    "state_before": "running",
                }
            ],
        )

    transport = FakeAwsTransport()
    transport.jobs = [{"jobId": "job-1", "status": "SUCCEEDED"}]
    receipt = run_canonical_interruption_drill(
        adapter(transport),
        plan_sha256="a" * 64,
        input_lock_sha256="b" * 64,
        account_id="123456789012",
        region="us-east-1",
        drill_id="fixed-admission-001",
        controller_identity_arn="arn:aws:iam::123456789012:role/controller",
        watcher_identity_arn="arn:aws:iam::123456789012:role/watcher",
        lease={
            "key": "k",
            "issued_timestamp": "2026-08-01T00:00:00Z",
            "expires_timestamp": "2026-08-01T00:01:00Z",
            "watcher_observed_timestamp": "2026-08-01T00:01:01Z",
            "controller_renewal_count": 0,
        },
        job_ids=["job-1"],
        completed_boundary=b"boundary",
        resources_before=[
            {
                "resource_id": "i-0123456789abcdef0",
                "resource_type": "compute",
                "state_before": "running",
            }
        ],
    )
    assert receipt["drill"]["operations"][1:3] == [
        "freeze_completed_boundary",
        "restore_completed_boundary",
    ]
    assert transport.freeze_calls == 1 and transport.restore_calls == 1

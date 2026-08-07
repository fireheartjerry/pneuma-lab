"""Build and KMS-sign the exact official C120 run specification/package."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
from typing import Mapping

from pneuma_lab.cloud.authorization_keys import (
    authorization_body_digest,
    canonical_bytes as authorization_bytes,
    verify_signature,
)
from pneuma_lab.cloud.manifests import validate_official_study_authorization
from pneuma_lab.cloud.production_run import (
    ProductionRunSpec,
    canonical_bytes,
    official_authorization_subject_digest,
)


ROOT = Path(__file__).resolve().parents[2]
KEY_REGISTRY = ROOT / "fixtures/cloud/approver-key-registry.json"
LEDGER = ROOT / "docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md"
ROLE_ORDER = ("controller", "model-server", "benchmark-worker")
MODEL_REVISION = "95a723d08a9490559dae23d0cff1d9466213d989"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _ref(
    root: Path, path: Path, role: str, media_type: str = "application/json"
) -> dict[str, object]:
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    return {
        "role": role,
        "relative_path": relative,
        "sha256": _sha(path),
        "byte_count": path.stat().st_size,
        "media_type": media_type,
    }


def _images(path: Path) -> tuple[dict[str, str], dict[str, Mapping[str, object]]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    rows = value.get("roles") if isinstance(value, dict) else None
    if not isinstance(rows, list):
        raise ValueError("image set has no role receipts")
    receipts = {str(row["role"]): row for row in rows if isinstance(row, Mapping)}
    if set(receipts) != set(ROLE_ORDER):
        raise ValueError("image set role closure differs")
    digests = {role: str(receipts[role]["image_digest"]) for role in ROLE_ORDER}
    return digests, receipts


def _provider_binding() -> dict[str, object]:
    return {
        "record_kind": "cloud_production_provider_binding",
        "schema_version": "0.2.0",
        "provider": "aws",
        "region": "us-east-1",
        "production_deployment": {
            "deployment_id": "aws-batch-two-independent-g6e-spot-workers-v1",
            "instance_type": "g6e.2xlarge",
            "worker_count": 2,
            "spot_only": True,
            "max_attempts": 1,
            "official_topology": "two-independent-8-vcpu-one-l40s-workers",
            "allowed_actions": [
                "official_model",
                "approved_benchmark",
                "canonical_p0_grid",
                "task_block_execution",
                "sealed_output_publication",
            ],
        },
        "bounded_surface_deployment": {
            "deployment_id": "aws-ec2-ssm-cpu-production-role-surface-v2",
            "instance_type": "m7i.large",
            "capacity_type": "on-demand",
            "max_duration_seconds": 900,
            "max_usd": 3.0,
            "network": "private-action-subnet-approved-endpoints-only",
            "metadata_options": "IMDSv2-required",
            "role_sandbox": "network-none-read-only-cap-drop-all-no-new-privileges",
            "vpc_id": "vpc-0577decd080525e86",
            "availability_zone": "us-east-1a",
            "subnet_cidr": "10.42.2.0/24",
            "ami_id": "ami-0b416d150bdde5ea2",
            "ami_owner_id": "591542846629",
            "architecture": "x86_64",
            "root_device_type": "ebs",
            "approved_endpoints": [
                "ecr.api",
                "ecr.dkr",
                "ssm",
                "ssmmessages",
                "ec2messages",
                "s3",
            ],
            "custom_ssm_document": {
                "contract": "fixed-status-read-v1",
                "version": "1",
                "caller_parameters": False,
            },
            "external_watchdog": True,
        },
        "forbidden_actions_scope": "bounded_surface_deployment_only",
        "forbidden_actions": [
            "official_model",
            "approved_benchmark",
            "pilot",
            "canonical_p0_grid",
            "scientific_analysis",
            "unblind",
        ],
        "teardown": {
            "required": True,
            "active_resource_absence": True,
            "retained_artifacts": [
                "immutable_ecr_images",
                "sbom_records",
                "compact_receipts",
            ],
        },
        "image_registry": {
            "repository_prefix": "pneuma-official-production",
            "tag_mutability": "IMMUTABLE",
            "scan_on_push": True,
            "encryption": "AES256",
        },
    }


def _append_ledger_row(
    *, action_id: str, subject_sha256: str, timestamp: str, row_id: str
) -> tuple[str, str, str]:
    if re.fullmatch(r"CL-[1-9][0-9]*", row_id) is None:
        raise ValueError("ledger row ID must be CL-<positive integer>")

    def line_for(value: str) -> str:
        return (
            f"| {row_id} | {value} | AWS | Official C120 P0/Step-4B launch "
            f"`{action_id}` | `{subject_sha256}` | AWS KMS `alias/pneuma-approver`; "
            "exact final authorization | ceiling USD 5,100.00 | 5,100.00 | 0.00 | "
            "authorized | One size-two Batch array, two `g6e.2xlarge` Spot workers "
            "(16 Spot vCPUs total), one attempt, 120 SWE and 120 TAU tasks, frozen "
            "four-arm task-block plan, immutable images/package, durable outputs, and "
            "mandatory post-run teardown. |"
        )

    line = line_for(timestamp)
    text = LEDGER.read_text(encoding="utf-8")
    prefix = f"| {row_id} |"
    matches = [item for item in text.splitlines() if item.startswith(prefix)]
    if matches:
        if len(matches) != 1:
            raise ValueError(f"{row_id} exists more than once")
        fields = matches[0].split("|")
        existing_timestamp = fields[2].strip() if len(fields) > 2 else ""
        if matches[0] != line_for(existing_timestamp):
            raise ValueError(f"{row_id} already exists with different content")
        return (
            row_id,
            hashlib.sha256(matches[0].encode("utf-8")).hexdigest(),
            existing_timestamp,
        )
    if not matches:
        marker = "\n## Totals\n"
        if marker not in text:
            raise ValueError("ledger totals marker is missing")
        LEDGER.write_text(
            text.replace(marker, f"\n{line}\n{marker}", 1), encoding="utf-8"
        )
    return row_id, hashlib.sha256(line.encode("utf-8")).hexdigest(), timestamp


def _signed_authorization(
    body: dict[str, object], *, kms_key_id: str, granted: str, expires: str
) -> dict[str, object]:
    import boto3

    body["human_authorization"] = {
        "approver_id": "jerry-mathos-ai",
        "key_id": "pneuma-kms-20260801-r1",
        "granted_timestamp": granted,
        "expires_timestamp": expires,
        "body_sha256": "0" * 64,
        "signature_ed25519": "0" * 128,
    }
    digest = authorization_body_digest(body)
    approval = dict(body["human_authorization"])
    approval["body_sha256"] = digest
    body["human_authorization"] = approval
    message = authorization_bytes(
        {
            **{
                key: value
                for key, value in body.items()
                if key != "human_authorization"
            },
            "approval": {
                "approver_id": approval["approver_id"],
                "key_id": approval["key_id"],
                "granted_timestamp": approval["granted_timestamp"],
                "expires_timestamp": approval["expires_timestamp"],
            },
        }
    )
    if hashlib.sha256(message).hexdigest() != digest:
        raise ValueError("authorization body digest construction differs")
    kms = boto3.client("kms", region_name="us-east-1")
    signed = kms.sign(
        KeyId=kms_key_id,
        Message=message,
        MessageType="RAW",
        SigningAlgorithm="ED25519_SHA_512",
    )
    signature = bytes(signed["Signature"])
    verified = kms.verify(
        KeyId=kms_key_id,
        Message=message,
        MessageType="RAW",
        Signature=signature,
        SigningAlgorithm="ED25519_SHA_512",
    )
    if verified.get("SignatureValid") is not True or len(signature) != 64:
        raise ValueError("KMS signature verification failed")
    approval["signature_ed25519"] = signature.hex()
    body["human_authorization"] = approval
    validate_official_study_authorization(body)
    return body


def _archive(root: Path, destination: Path) -> str:
    with (
        destination.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as archive,
    ):
        for path in sorted(
            root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
        ):
            relative = path.relative_to(root).as_posix()
            info = archive.gettarinfo(str(path), arcname=relative)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            if path.is_file():
                with path.open("rb") as handle:
                    archive.addfile(info, handle)
            else:
                archive.addfile(info)
    return _sha(destination)


def finalize(args: argparse.Namespace) -> dict[str, object]:
    source = args.source_package.resolve()
    output = args.output_dir.resolve()
    if output.exists():
        raise ValueError("final package directory must be new")
    output.mkdir(parents=True)
    shutil.copytree(source / "inputs", output / "inputs")
    shutil.copytree(source / "sealed", output / "sealed")
    shutil.copy2(args.power_report, output / "power-final.json")
    shutil.copy2(args.image_set, output / "images.json")
    shutil.copytree(args.image_set.parent / "images", output / "image-evidence")
    (output / "governance").mkdir()
    _write(
        output / "governance/approver-key-registry.json",
        json.loads(KEY_REGISTRY.read_text(encoding="utf-8")),
    )

    provider_path = output / "inputs/provider-binding.json"
    _write(provider_path, _provider_binding())
    image_digests, image_receipts = _images(output / "images.json")
    launch_plan = {
        "record_kind": "cloud_official_batch_launch_plan",
        "schema_version": "0.1.0",
        "action_id": args.action_id,
        "region": "us-east-1",
        "array_size": 2,
        "instance_type": "g6e.2xlarge",
        "max_spot_vcpus": 16,
        "attempts": 1,
        "max_duration_seconds": 604_800,
        "max_usd": 5100.0,
        "images": [
            {"role": role, "image_digest": image_digests[role]} for role in ROLE_ORDER
        ],
        "submission_source_sha256": _sha(
            ROOT / "scripts/research/submit_official_batch.py"
        ),
        "cleanup_source_sha256": _sha(
            ROOT / "scripts/research/cleanup_official_batch.py"
        ),
        "container_resources": {
            "controller": {"vcpus": 1, "memory_mib": 4000, "gpus": 0},
            "model-server": {"vcpus": 1, "memory_mib": 46000, "gpus": 1},
            "benchmark-worker": {"vcpus": 6, "memory_mib": 12000, "gpus": 0},
        },
    }
    launch_path = output / "launch-plan.json"
    _write(launch_path, launch_plan)
    surface = {
        "record_kind": "cloud_production_execution_surface",
        "schema_version": "0.2.0",
        "surface_class": "provenance_verified_official_batch_plan",
        "input_lock_sha256": _sha(output / "inputs/input-lock.json"),
        "source_commit": args.source_commit,
        "provider_binding_sha256": _sha(provider_path),
        "launch_plan_sha256": _sha(launch_path),
        "roles": [
            {
                "role": role,
                "image_digest": image_digests[role],
                "entrypoint": [
                    "python3",
                    "-m",
                    "pneuma_lab.cloud.production_runtime",
                    role,
                ],
                "source_sha256": str(
                    image_receipts[role]["source_closure"]["manifest_sha256"]
                ),
                "sbom_sha256": str(image_receipts[role]["sbom"]["sha256"]),
                "provenance_descriptor_digest": str(
                    image_receipts[role]["provenance"]["descriptor_digest"]
                ),
            }
            for role in ROLE_ORDER
        ],
    }
    surface_path = output / "execution-surface.json"
    _write(surface_path, surface)

    secret_root = args.secret_root.resolve()
    seed_names = (
        "roster",
        "schedule",
        "assignment",
        "packet",
        "model",
        "benchmark",
        "unblind",
    )
    seed_bytes = {
        name: (secret_root / f"{name}-seed.bin").read_bytes() for name in seed_names
    }
    rng = {
        "contract_id": "official-study-rng-v1",
        "root_u64": int.from_bytes(seed_bytes["model"][:8], "big"),
        "draw_domains": list(seed_names),
        "seeds": {
            name: hashlib.sha256(value).hexdigest()
            for name, value in seed_bytes.items()
        },
        "status": "sealed",
        "commitment_ref": _ref(
            output,
            output / "inputs/rng-commitment.json",
            "rng_commitment",
        ),
    }
    task_path = output / "inputs/task-registry.json"
    task_ref = _ref(output, task_path, "task_manifest")
    bindings = [
        {"role": role, "image_digest": image_digests[role]} for role in ROLE_ORDER
    ]
    placeholder = {
        "role": "placeholder",
        "relative_path": "governance/placeholder.json",
        "sha256": "0" * 64,
        "byte_count": 0,
        "media_type": "application/json",
    }
    spec: dict[str, object] = {
        "record_kind": "cloud_production_run_spec",
        "schema_version": "0.1.0",
        "action_id": args.action_id,
        "study_id": "neurips-2026-resampling-null",
        "run_mode": "official",
        "code_commit": args.source_commit,
        "image_bindings": bindings,
        "execution_surface_ref": _ref(output, surface_path, "execution_surface"),
        "provider_binding_ref": _ref(output, provider_path, "provider_binding"),
        "input_lock_ref": _ref(output, output / "inputs/input-lock.json", "input_lock"),
        "model": {
            "repository": "Qwen/Qwen3.6-35B-A3B-FP8",
            "revision": MODEL_REVISION,
            "tokenizer_revision": MODEL_REVISION,
            "serving_engine": "vllm",
            "serving_engine_version": "0.19.0",
            "sampling": {
                "temperature": 0.6,
                "top_p": 0.95,
                "top_k": 20,
                "presence_penalty": 0.0,
                "repetition_penalty": 1.0,
                "thinking_mode": True,
                "reasoning_parser": "qwen3",
                "tool_call_parser": "qwen3_coder",
            },
            "sampling_by_benchmark": {
                "swe_multilang": {
                    "temperature": 0.6,
                    "top_p": 0.95,
                    "top_k": 20,
                    "presence_penalty": 0.0,
                    "repetition_penalty": 1.0,
                    "thinking_mode": True,
                    "reasoning_parser": "qwen3",
                    "tool_call_parser": "qwen3_coder",
                },
                "tau2": {
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "top_k": 20,
                    "presence_penalty": 1.5,
                    "repetition_penalty": 1.0,
                    "thinking_mode": True,
                    "reasoning_parser": "qwen3",
                    "tool_call_parser": "qwen3_coder",
                },
            },
        },
        "benchmarks": [
            {
                "benchmark_id": "swe_multilang",
                "repository": "microsoft/SWE-bench-Live",
                "revision": "70ec57e852e3f2d195790fe71f553e272c691833",
                "dataset_repository": "SWE-bench-Live/MultiLang",
                "dataset_revision": "608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b",
                "task_manifest_sha256": task_ref["sha256"],
                "task_manifest_size_bytes": task_ref["byte_count"],
            },
            {
                "benchmark_id": "tau2",
                "repository": "sierra-research/tau2-bench",
                "revision": "fc0055dc4e0a316c3f83133267fbd6faaa770992",
                "dataset_repository": "sierra-research/tau2-bench",
                "dataset_revision": "fc0055dc4e0a316c3f83133267fbd6faaa770992",
                "task_manifest_sha256": task_ref["sha256"],
                "task_manifest_size_bytes": task_ref["byte_count"],
            },
        ],
        "task_manifest_ref": task_ref,
        "roster_ref": _ref(output, output / "sealed/roster.json", "roster"),
        "assignment_ref": _ref(
            output, output / "sealed/assignment.controller-only.json", "assignment"
        ),
        "prelaunch_root_ref": _ref(
            output, output / "sealed/prelaunch-root.json", "prelaunch_root"
        ),
        "execution_seed_openings_ref": _ref(
            output,
            output / "sealed/execution-seeds.controller-only.json",
            "execution_seed_openings",
        ),
        "execution_assets_ref": _ref(
            output,
            output / "inputs/execution/swe-tasks.controller-only.json",
            "swe_execution_assets",
        ),
        "rng": rng,
        "worker_topology": {
            "worker_ids": ["worker-0", "worker-1"],
            "instance_type": "g6e.2xlarge",
            "vcpus_per_worker": 8,
            "gpus_per_worker": 1,
            "allocation_contract_id": "two-l40s-swe-dual-tau-subject-simulator-v1",
        },
        "budget": {
            "max_usd": 5100.0,
            "max_duration_seconds": 604_800,
            "max_attempts": 1,
            "spot_only": True,
        },
        "output": {
            "root": f"outputs/{args.action_id}",
            "worker_evidence_template": f"outputs/{args.action_id}/{{worker_id}}.evidence.json",
            "controller_state_path": f"outputs/{args.action_id}/controller.json",
        },
        "analysis_graph_ref": _ref(
            output, output / "inputs/analysis-graph.json", "analysis_graph"
        ),
        "power_report_ref": _ref(output, output / "power-final.json", "power_report"),
        "power_tier": 120,
        "official_authorization_ref": placeholder,
        "official_key_registry_ref": placeholder,
        "model_server": {
            "endpoint": "http://127.0.0.1:8000",
            "launch_argv": [
                "python3",
                "-m",
                "vllm.entrypoints.openai.api_server",
                "--model",
                "/run/pneuma/payloads/subject-model",
                "--served-model-name",
                "Qwen/Qwen3.6-35B-A3B-FP8",
                "--revision",
                MODEL_REVISION,
                "--tokenizer",
                "/run/pneuma/payloads/subject-model",
                "--tokenizer-revision",
                MODEL_REVISION,
                "--max-model-len",
                "65536",
                "--host",
                "0.0.0.0",
                "--gpu-memory-utilization",
                "0.92",
                "--max-num-seqs",
                "4",
                "--language-model-only",
                "--reasoning-parser",
                "qwen3",
                "--tool-call-parser",
                "qwen3_coder",
                "--enable-auto-tool-choice",
                "--no-enable-prefix-caching",
            ],
            "simulator_launch_argv": [
                "python3",
                "-m",
                "vllm.entrypoints.openai.api_server",
                "--model",
                "/run/pneuma/payloads/simulator-model",
                "--served-model-name",
                "Qwen/Qwen3.5-9B",
                "--revision",
                "c202236235762e1c871ad0ccb60c8ee5ba337b9a",
                "--tokenizer",
                "/run/pneuma/payloads/simulator-model",
                "--tokenizer-revision",
                "c202236235762e1c871ad0ccb60c8ee5ba337b9a",
                "--max-model-len",
                "32768",
                "--host",
                "0.0.0.0",
                "--gpu-memory-utilization",
                "0.92",
                "--max-num-seqs",
                "4",
                "--language-model-only",
                "--reasoning-parser",
                "qwen3",
                "--tool-call-parser",
                "qwen3_coder",
                "--enable-auto-tool-choice",
                "--no-enable-prefix-caching",
            ],
            "simulator_revision": "c202236235762e1c871ad0ccb60c8ee5ba337b9a",
            "readiness_timeout_seconds": 1800,
            "request_timeout_seconds": 3600,
        },
        "benchmark_adapter": {
            "adapter_id": "registered-swe-live-tau2-v1",
            "entrypoint": [
                "python3",
                "-m",
                "pneuma_lab.cloud.registered_benchmark_adapter",
            ],
            "timeout_seconds": 3600,
            "adapter_manifest_ref": _ref(
                output,
                output / "inputs/benchmark-adapter-manifest.json",
                "adapter_manifest",
            ),
        },
    }
    ProductionRunSpec.from_mapping(spec)
    subject_sha256 = official_authorization_subject_digest(spec)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    granted = now.isoformat().replace("+00:00", "Z")
    row_id, row_digest, granted = _append_ledger_row(
        action_id=args.action_id,
        subject_sha256=subject_sha256,
        timestamp=granted,
        row_id=args.ledger_row_id,
    )
    granted_time = datetime.fromisoformat(granted.replace("Z", "+00:00"))
    expires = (granted_time + timedelta(days=21)).isoformat().replace("+00:00", "Z")
    shutil.copy2(LEDGER, output / "governance/cloud-spend-ledger.md")
    ledger_ref = _ref(
        output,
        output / "governance/cloud-spend-ledger.md",
        "cloud_spend_ledger",
        "text/markdown",
    )
    authorization = {
        "record_kind": "cloud_official_study_authorization",
        "schema_version": "0.1.0",
        "status": "authorized",
        "scope": "official_p0_step4b",
        "action_id": args.action_id,
        "study_id": "neurips-2026-resampling-null",
        "run_spec_subject_sha256": subject_sha256,
        "input_lock_sha256": spec["input_lock_ref"]["sha256"],
        "task_manifest_sha256": task_ref["sha256"],
        "max_usd": 5100.0,
        "code_commit": args.source_commit,
        "image_bindings": bindings,
        "power_report_sha256": spec["power_report_ref"]["sha256"],
        "analysis_graph_sha256": spec["analysis_graph_ref"]["sha256"],
        "selected_tier": 120,
        "max_attempts": 1,
        "spot_only": True,
        "teardown_protected": True,
        "ledger_ref": ledger_ref,
        "ledger_row_id": row_id,
        "ledger_row_sha256": row_digest,
    }
    authorization = _signed_authorization(
        authorization,
        kms_key_id=args.kms_key_id,
        granted=granted,
        expires=expires,
    )
    authorization_path = output / "governance/official-authorization.json"
    _write(authorization_path, authorization)
    spec["official_authorization_ref"] = _ref(
        output, authorization_path, "official_authorization"
    )
    spec["official_key_registry_ref"] = _ref(
        output,
        output / "governance/approver-key-registry.json",
        "approver_key_registry",
    )
    spec_path = output / "run-spec.json"
    _write(spec_path, spec)
    loaded = ProductionRunSpec.load(spec_path, expected_sha256=_sha(spec_path))
    if loaded.authorization_subject_digest != subject_sha256:
        raise ValueError("final authorization subject changed")
    loaded.verify_official_authorization(run_root=output)
    registry = json.loads(
        (output / "governance/approver-key-registry.json").read_text(encoding="utf-8")
    )
    verify_signature(authorization, registry, now=now)
    package_record = {
        "record_kind": "cloud_official_final_package",
        "schema_version": "0.1.0",
        "status": "AUTHORIZED_READY_TO_SUBMIT",
        "action_id": args.action_id,
        "run_spec_ref": _ref(output, spec_path, "run_spec"),
        "authorization_ref": _ref(output, authorization_path, "official_authorization"),
        "launch_plan_ref": _ref(output, launch_path, "launch_plan"),
        "prelaunch_root_ref": _ref(
            output, output / "sealed/prelaunch-root.json", "prelaunch_root"
        ),
    }
    _write(output / "official-package.json", package_record)
    package_sha256 = _archive(output, args.archive.resolve())
    return {
        "action_id": args.action_id,
        "run_spec_sha256": _sha(spec_path),
        "run_spec_subject_sha256": subject_sha256,
        "authorization_sha256": _sha(authorization_path),
        "package_sha256": package_sha256,
        "package": args.archive.resolve().as_posix(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-package", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--image-set", type=Path, required=True)
    parser.add_argument("--power-report", type=Path, required=True)
    parser.add_argument("--secret-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--ledger-row-id", required=True)
    parser.add_argument("--kms-key-id", default="alias/pneuma-approver")
    args = parser.parse_args()
    print(json.dumps(finalize(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

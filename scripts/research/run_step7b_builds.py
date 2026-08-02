"""Execute the sealed, build-only Step 7B role-image qualification.

The caller must perform preparation-admission verification before invoking this
program.  This program intentionally has no AWS calls, no registry push, no GPU
arguments, and no benchmark execution path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROLES = ("controller", "model-server", "benchmark-worker")
BUILDX_VERSION = "v0.13.1"
BUILDX_SHA256 = "3e2bc8ed25a9125d6aeec07df4e0211edea6288e075b524160ef3fd305d3d74c"
BUILDKIT_VERSION = "v0.13.2"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan_digest(plan: dict[str, Any]) -> str:
    body = dict(plan)
    body.pop("plan_sha256", None)
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def run(
    arguments: list[str],
    *,
    capture: bool = False,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, check=True, text=True, capture_output=capture, env=environment)


def image_id(tag: str) -> str:
    value = run(["docker", "image", "inspect", "--format", "{{.Id}}", tag], capture=True).stdout.strip()
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"Docker returned a non-content-addressed image id for {tag!r}")
    return value


def require_plan(plan: dict[str, Any], root: Path) -> None:
    action_id = plan.get("action_id")
    if not isinstance(action_id, str) or re.fullmatch(r"step7b-aws-builder-[0-9]{3}", action_id) is None:
        raise ValueError("executor only accepts one numbered Step 7B AWS builder action")
    if plan.get("max_retries") != 0 or plan.get("action_class") != "image_build":
        raise ValueError("Step 7B successor must remain a zero-retry image build")
    if plan_digest(plan) != plan.get("plan_sha256"):
        raise ValueError("plan_sha256 does not bind canonical plan bytes")
    if plan.get("executor_sha256") != sha256_file(Path(__file__)):
        raise ValueError("executor bytes do not match the sealed plan")
    buildx = plan.get("buildx")
    if not isinstance(buildx, dict) or buildx.get("version") != BUILDX_VERSION or buildx.get("sha256") != BUILDX_SHA256:
        raise ValueError("plan does not bind the pinned Buildx executable")
    buildkit = plan.get("buildkit")
    if not isinstance(buildkit, dict) or buildkit.get("version") != BUILDKIT_VERSION:
        raise ValueError("plan does not bind the pinned BuildKit version")
    buildkit_image = buildkit.get("image")
    if not isinstance(buildkit_image, str) or "@sha256:" not in buildkit_image:
        raise ValueError("plan does not bind a content-addressed BuildKit image")
    required = {"cloud_build", "ecr_push", "gpu_use", "benchmark_execution", "model_download"}
    if not required.issubset(set(plan["requirements"]["forbidden"])):
        raise ValueError("plan does not prohibit every non-build Step 7B action")
    surface = plan.get("production_surface")
    if surface is not None:
        if not isinstance(surface, dict) or surface.get("record_kind") != "cloud_production_e2e_harness":
            raise ValueError("production surface must bind a canonical E2E harness")
        if surface.get("schema_version") != "0.1.0" or surface.get("controller_privileged") is not True:
            raise ValueError("production surface must bind the sealed controller privilege boundary")
        request = surface.get("request")
        if not isinstance(request, dict) or not request.get("request_id") or not request.get("prompt"):
            raise ValueError("production surface request is incomplete")
        if type(request.get("max_tokens")) is not int or not 1 <= request["max_tokens"] <= 16:
            raise ValueError("production surface max_tokens is outside the bounded range")
        if type(request.get("temperature")) is not float or request["temperature"] != 0.0:
            raise ValueError("production surface temperature must be exactly 0.0")
        if "benchmark_execution" not in plan["requirements"]["forbidden"]:
            raise ValueError("production surface cannot authorize benchmark execution")
    for role in ROLES:
        paths = plan["roles"][role]
        for key in ("dockerfile", "lock"):
            path = root / paths[key]["path"]
            if not path.is_file() or sha256_file(path) != paths[key]["sha256"]:
                raise ValueError(f"{role} {key} does not match the sealed plan")
    runtime = root / plan["runtime"]["path"]
    if not runtime.is_file() or sha256_file(runtime) != plan["runtime"]["sha256"]:
        raise ValueError("sealed runtime bytes are absent or changed")
    dependency = plan.get("runtime_dependency")
    if not isinstance(dependency, dict):
        raise ValueError("sealed provider runtime dependency lock is missing")
    dependency_path = root / dependency.get("path", "")
    if not dependency_path.is_file() or sha256_file(dependency_path) != dependency.get("sha256"):
        raise ValueError("sealed provider runtime dependency lock is absent or changed")
    if dependency.get("python") != "3.9" or dependency.get("install_target") != "/opt/pneuma-step7b/python-deps":
        raise ValueError("provider runtime dependency lock is not the sealed Python 3.9 target")


def require_free_storage(plan: dict[str, Any], path: Path) -> None:
    minimum_gib = plan["requirements"]["minimum_verified_free_storage_gib"]
    if not isinstance(minimum_gib, int) or minimum_gib <= 0:
        raise ValueError("minimum verified free storage must be a positive integer")
    free_bytes = shutil.disk_usage(path).free
    if free_bytes < minimum_gib * 1024**3:
        raise ValueError(f"builder free storage is below the sealed {minimum_gib} GiB floor")


def build_role(plan: dict[str, Any], root: Path, output: Path, role: str, builder: str) -> dict[str, Any]:
    role_plan = plan["roles"][role]
    dockerfile = root / role_plan["dockerfile"]["path"]
    harness = output / f"{role}-harness.json"
    harness.write_bytes(canonical_bytes({"action_id": plan["action_id"], "input_lock_sha256": plan["input_lock_sha256"], "role": role}) + b"\n")
    harness_digest = sha256_file(harness)
    tags = [f"pneuma-step7b-{role}:build-{index}" for index in (1, 2)]
    digests: list[str] = []
    build_environment = dict(os.environ)
    build_environment["SOURCE_DATE_EPOCH"] = str(plan["source_date_epoch"])
    for tag in tags:
        run(
            [
                "docker",
                "buildx",
                "build",
                "--builder",
                builder,
                "--no-cache",
                "--pull=false",
                "--provenance=false",
                "--sbom=false",
                "--platform",
                "linux/amd64",
                "--output",
                "type=docker,rewrite-timestamp=true",
                "--build-arg",
                f"SOURCE_DATE_EPOCH={plan['source_date_epoch']}",
                "--file",
                str(dockerfile),
                "--tag",
                tag,
                str(root),
            ],
            environment=build_environment,
        )
        digests.append(image_id(tag))
    if digests[0] != digests[1]:
        raise ValueError(f"{role} double-build image config digests differ")
    positive = run(["docker", "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp", "--volume", f"{harness}:/work/harness.json:ro", tags[0], "--harness", "/work/harness.json", "--harness-sha256", harness_digest], capture=True)
    wrong = subprocess.run(["docker", "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp", "--volume", f"{harness}:/work/harness.json:ro", tags[0], "--harness", "/work/harness.json", "--harness-sha256", "0" * 64], text=True, capture_output=True, check=False)
    if wrong.returncode != 2:
        raise ValueError(f"{role} did not fail closed for the wrong harness digest")
    sbom = output / f"{role}.spdx.json"
    syft_tmp = output.parent / "syft-tmp"
    syft_tmp.mkdir(parents=True, exist_ok=True)
    syft_env = dict(os.environ, TMPDIR=str(syft_tmp))
    with sbom.open("w", encoding="utf-8") as handle:
        subprocess.run(
            ["syft", tags[0], "-o", "spdx-json"],
            check=True,
            text=True,
            stdout=handle,
            env=syft_env,
        )
    (output / f"{role}-positive.json").write_text(positive.stdout, encoding="utf-8")
    (output / f"{role}-wrong-hash.json").write_text(wrong.stdout, encoding="utf-8")
    return {
        "record_kind": "cloud_image_build_receipt", "schema_version": "0.1.0",
        "action_id": plan["action_id"], "plan_sha256": plan["plan_sha256"], "role": role,
        "recipe_sha256": plan["recipe_sha256"], "dockerfile_sha256": role_plan["dockerfile"]["sha256"],
        "base_digest": role_plan["base_digest"], "lock_sha256": role_plan["lock"]["sha256"],
        "input_lock_sha256": plan["input_lock_sha256"], "runtime_sha256": plan["runtime"]["sha256"],
        "builder_sha256": plan["executor_sha256"],
        "build_image_digests": digests, "sbom_sha256": sha256_file(sbom), "reproducible": True,
    }


def create_builder(plan: dict[str, Any], output: Path) -> str:
    buildx_version = run(["docker", "buildx", "version"], capture=True).stdout.strip()
    if BUILDX_VERSION not in buildx_version:
        raise ValueError(f"Buildx version does not match the sealed {BUILDX_VERSION}: {buildx_version!r}")
    (output / "buildx-version.txt").write_text(buildx_version + "\n", encoding="utf-8")
    builder = f"pneuma-step7b-{plan['action_id']}"
    run(
        [
            "docker",
            "buildx",
            "create",
            "--name",
            builder,
            "--driver",
            "docker-container",
            "--driver-opt",
            f"image={plan['buildkit']['image']}",
            "--use",
            "--bootstrap",
        ],
        capture=True,
    )
    inspection_result = subprocess.run(
        ["docker", "buildx", "inspect", builder, "--bootstrap"],
        check=False,
        text=True,
        capture_output=True,
    )
    inspection = inspection_result.stdout
    (output / "buildx-builder.txt").write_text(inspection, encoding="utf-8")
    (output / "buildx-builder-stderr.txt").write_text(inspection_result.stderr, encoding="utf-8")
    if inspection_result.returncode != 0:
        raise ValueError(f"BuildKit inspection failed with exit code {inspection_result.returncode}")
    if not re.search(rf"BuildKit(?: version)?:\s*{re.escape(BUILDKIT_VERSION)}(?:\b|$)", inspection, re.MULTILINE):
        raise ValueError(f"BuildKit version does not match the sealed {BUILDKIT_VERSION}")
    return builder


def remove_builder(builder: str) -> None:
    subprocess.run(
        ["docker", "buildx", "rm", "--force", builder],
        check=False,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    args = parser.parse_args()
    if shutil.which("docker") is None or shutil.which("syft") is None:
        raise SystemExit("Docker and the sealed Syft executable are required")
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    root = args.source_root.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    require_plan(plan, root)
    require_free_storage(plan, output)
    builder = create_builder(plan, output)
    try:
        receipts = [build_role(plan, root, output, role, builder) for role in ROLES]
        (output / "step7b-build-receipts.json").write_bytes(canonical_bytes(receipts) + b"\n")
        surface = plan.get("production_surface")
        if surface is not None:
            harness = {
                "record_kind": surface["record_kind"],
                "schema_version": surface["schema_version"],
                "action_id": plan["action_id"],
                "input_lock_sha256": plan["input_lock_sha256"],
                "request": surface["request"],
            }
            harness_path = output / "production-surface-harness.json"
            harness_path.write_bytes(canonical_bytes(harness) + b"\n")
            harness_digest = sha256_file(harness_path)
            expected_digest = surface.get("harness_sha256")
            if expected_digest is not None and expected_digest != harness_digest:
                raise ValueError("production surface harness digest does not match the sealed plan")
            image_args = [
                item
                for role, receipt in zip(ROLES, receipts)
                for item in ("--image", f"{role}=pneuma-step7b-{role}:build-1", "--image-digest", f"{role}={receipt['build_image_digests'][0]}")
            ]
            command = [
                "python3",
                str(root / "scripts/research/run_production_surface_e2e.py"),
                "--harness",
                str(harness_path),
                "--harness-sha256",
                harness_digest,
                "--output-dir",
                str(output / "production-surface"),
                "--source-root",
                str(root),
                "--source-commit",
                plan["source_commit"],
                "--controller-privileged",
                *image_args,
            ]
            child_environment = dict(os.environ)
            source_pythonpath = str(root / "src")
            child_environment["PYTHONPATH"] = (
                source_pythonpath
                if not child_environment.get("PYTHONPATH")
                else source_pythonpath + os.pathsep + child_environment["PYTHONPATH"]
            )
            completed = subprocess.run(command, check=False, text=True, capture_output=True, env=child_environment)
            (output / "production-surface-command.json").write_text(
                json.dumps(
                    {
                        "command": command,
                        "returncode": completed.returncode,
                        "stdout": completed.stdout,
                        "stderr": completed.stderr,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            if completed.returncode != 0:
                raise RuntimeError(f"production surface command failed with exit code {completed.returncode}")
    finally:
        remove_builder(builder)
    print(json.dumps({"receipt_sha256": sha256_file(output / "step7b-build-receipts.json"), "roles": list(ROLES)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

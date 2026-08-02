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


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan_digest(plan: dict[str, Any]) -> str:
    body = dict(plan)
    body.pop("plan_sha256", None)
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def run(arguments: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, check=True, text=True, capture_output=capture)


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
    required = {"cloud_build", "ecr_push", "gpu_use", "benchmark_execution", "model_download"}
    if not required.issubset(set(plan["requirements"]["forbidden"])):
        raise ValueError("plan does not prohibit every non-build Step 7B action")
    for role in ROLES:
        paths = plan["roles"][role]
        for key in ("dockerfile", "lock"):
            path = root / paths[key]["path"]
            if not path.is_file() or sha256_file(path) != paths[key]["sha256"]:
                raise ValueError(f"{role} {key} does not match the sealed plan")
    runtime = root / plan["runtime"]["path"]
    if not runtime.is_file() or sha256_file(runtime) != plan["runtime"]["sha256"]:
        raise ValueError("sealed runtime bytes are absent or changed")


def require_free_storage(plan: dict[str, Any], path: Path) -> None:
    minimum_gib = plan["requirements"]["minimum_verified_free_storage_gib"]
    if not isinstance(minimum_gib, int) or minimum_gib <= 0:
        raise ValueError("minimum verified free storage must be a positive integer")
    free_bytes = shutil.disk_usage(path).free
    if free_bytes < minimum_gib * 1024**3:
        raise ValueError(f"builder free storage is below the sealed {minimum_gib} GiB floor")


def build_role(plan: dict[str, Any], root: Path, output: Path, role: str) -> dict[str, Any]:
    role_plan = plan["roles"][role]
    dockerfile = root / role_plan["dockerfile"]["path"]
    harness = output / f"{role}-harness.json"
    harness.write_bytes(canonical_bytes({"action_id": plan["action_id"], "input_lock_sha256": plan["input_lock_sha256"], "role": role}) + b"\n")
    harness_digest = sha256_file(harness)
    tags = [f"pneuma-step7b-{role}:build-{index}" for index in (1, 2)]
    digests: list[str] = []
    for tag in tags:
        run(["docker", "build", "--no-cache", "--pull=false", "--provenance=false", "--sbom=false", "--build-arg", f"SOURCE_DATE_EPOCH={plan['source_date_epoch']}", "--file", str(dockerfile), "--tag", tag, str(root)])
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
    receipts = [build_role(plan, root, output, role) for role in ROLES]
    (output / "step7b-build-receipts.json").write_bytes(canonical_bytes(receipts) + b"\n")
    print(json.dumps({"receipt_sha256": sha256_file(output / "step7b-build-receipts.json"), "roles": list(ROLES)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

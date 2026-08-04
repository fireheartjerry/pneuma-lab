"""Build and publish the three immutable production role images.

This is the production image lane, deliberately separate from the historical
Step 7B qualification builder.  It never runs a model, benchmark, pilot, or
official controller; it only builds role images and records immutable image,
SBOM, and provenance bindings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from pneuma_lab.cloud.manifests import validate_production_image_receipt


ROOT = Path(__file__).resolve().parents[2]
ROLES = ("controller", "model-server", "benchmark-worker")
DOCKERFILES = {role: ROOT / "infra/docker" / role / "Dockerfile" for role in ROLES}
BASE_DIGEST = "sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90"
SYFT_URL = "https://github.com/anchore/syft/releases/download/v1.50.0/syft_1.50.0_linux_amd64.tar.gz"
SYFT_TAR_SHA256 = "bf7b29ff57f06da30918266a0e1c2885a8f99784798d1bdb1628886aa015d788"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _run(command: list[str], *, cwd: Path = ROOT, input_text: str | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, input=input_text, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stderr[-4000:]}")
    return result.stdout


def _account_id() -> str:
    value = json.loads(_run(["aws", "sts", "get-caller-identity", "--output", "json"]))
    account = value.get("Account")
    if not isinstance(account, str) or not re.fullmatch(r"[0-9]{12}", account):
        raise RuntimeError("AWS account identity is unavailable")
    return account


def _ensure_repository(repository: str) -> None:
    result = subprocess.run(
        ["aws", "ecr", "describe-repositories", "--repository-names", repository, "--region", "us-east-1", "--output", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        data = json.loads(result.stdout)
        repo = data["repositories"][0]
        if repo.get("imageTagMutability") != "IMMUTABLE" or repo.get("imageScanningConfiguration", {}).get("scanOnPush") is not True:
            raise RuntimeError(f"existing production repository is not immutable/scanned: {repository}")
        return
    _run([
        "aws", "ecr", "create-repository", "--repository-name", repository,
        "--image-tag-mutability", "IMMUTABLE", "--image-scanning-configuration", "scanOnPush=true",
        "--encryption-configuration", "encryptionType=AES256", "--region", "us-east-1", "--output", "json",
    ])


def _login(account: str) -> None:
    password = _run(["aws", "ecr", "get-login-password", "--region", "us-east-1"])
    _run(["docker", "login", "--username", "AWS", "--password-stdin", f"{account}.dkr.ecr.us-east-1.amazonaws.com"], input_text=password)


def _source_date_epoch(commit: str) -> int:
    return int(_run(["git", "show", "-s", "--format=%ct", commit]).strip())


def _build_role(role: str, *, account: str, commit: str, source_date_epoch: int, output: Path, syft: Path) -> dict[str, Any]:
    repository = f"pneuma-official-production-{role}"
    _ensure_repository(repository)
    registry = f"{account}.dkr.ecr.us-east-1.amazonaws.com"
    tag = f"source-{commit[:12]}"
    tag_ref = f"{registry}/{repository}:{tag}"
    metadata_path = output / "images" / f"{role}.build-metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    _run([
        "docker", "buildx", "build", "--platform", "linux/amd64", "--push",
        "--provenance=mode=max", "--sbom=false", "--build-arg", f"SOURCE_DATE_EPOCH={source_date_epoch}",
        "--tag", tag_ref, "--metadata-file", str(metadata_path), "--file", str(DOCKERFILES[role]), ".",
    ])
    inspect = json.loads(_run(["docker", "buildx", "imagetools", "inspect", tag_ref, "--raw"]))
    manifest_digest = inspect.get("manifests", [{}])[0].get("digest") if isinstance(inspect, dict) else None
    if not isinstance(manifest_digest, str) or not manifest_digest.startswith("sha256:"):
        manifest_digest = _run(["docker", "buildx", "imagetools", "inspect", tag_ref]).split("Digest:", 1)[-1].splitlines()[0].strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", manifest_digest):
        raise RuntimeError(f"cannot resolve immutable image digest for {role}")
    image_ref = f"{registry}/{repository}@{manifest_digest}"
    sbom_path = output / "images" / f"{role}.spdx.json"
    sbom_result = subprocess.run([str(syft), image_ref, "-o", "spdx-json"], cwd=ROOT, capture_output=True, check=False)
    if sbom_result.returncode != 0:
        raise RuntimeError(f"syft failed for {role}: {sbom_result.stderr.decode(errors='replace')[-4000:]}")
    sbom_path.write_bytes(sbom_result.stdout)
    if not sbom_path.stat().st_size:
        raise RuntimeError(f"empty SBOM for {role}")
    provenance_payload = metadata_path.read_bytes()
    receipt = {
        "record_kind": "cloud_production_image_receipt",
        "schema_version": "0.1.0",
        "evidence_class": "production_surface_non_scientific",
        "role": role,
        "source_commit": commit,
        "dockerfile": DOCKERFILES[role].relative_to(ROOT).as_posix(),
        "base_image": {"repository": "docker.io/vllm/vllm-openai", "digest": BASE_DIGEST, "platform": "linux/amd64"},
        "image_ref": image_ref,
        "image_digest": manifest_digest,
        "sbom": {"format": "spdx-json", "tool": "syft", "version": "1.50.0", "release_url": SYFT_URL, "release_tar_sha256": SYFT_TAR_SHA256, "sha256": _sha(sbom_path), "byte_count": sbom_path.stat().st_size},
        "provenance": {"attestation_format": "buildkit-in-toto-provenance", "sha256": hashlib.sha256(provenance_payload).hexdigest(), "builder": "docker-buildx-provenance-mode-max", "source_uri": f"git:{commit}"},
        "build": {"platform": "linux/amd64", "tag_mutability": "IMMUTABLE", "scan_on_push": True, "encryption": "AES256", "source_date_epoch": source_date_epoch, "network": "buildkit-default-no-runtime-workload", "model_download": False, "benchmark_execution": False},
        "surface_e2e_status": "pending_bounded_surface_e2e",
    }
    validate_production_image_receipt(receipt)
    receipt_path = output / "images" / f"{role}.receipt.json"
    receipt_path.write_bytes(_canonical(receipt))
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--syft", type=Path, required=True)
    args = parser.parse_args(argv)
    if not COMMIT_RE.fullmatch(args.source_commit):
        parser.error("--source-commit must be a full lowercase commit")
    if not args.syft.is_file():
        parser.error("--syft must point to the pinned Syft executable")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    account = _account_id()
    _login(account)
    epoch = _source_date_epoch(args.source_commit)
    receipts = [_build_role(role, account=account, commit=args.source_commit, source_date_epoch=epoch, output=output, syft=args.syft) for role in ROLES]
    result = {"record_kind": "cloud_production_image_set", "schema_version": "0.1.0", "evidence_class": "production_surface_non_scientific", "source_commit": args.source_commit, "roles": receipts}
    (output / "images.json").write_bytes(_canonical(result))
    print(json.dumps({"source_commit": args.source_commit, "images": {receipt["role"]: receipt["image_digest"] for receipt in receipts}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

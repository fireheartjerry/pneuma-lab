"""Build the three production role images from an immutable source archive.

The receipt keeps five different facts separate: source closure, OCI runtime
digest, BuildKit metadata, and the in-toto provenance descriptor.
An independently KMS-signed digest approval binds the source closure to the
exact runnable child digest.  None of these artifacts authorize science.
"""

from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
from typing import Any, Mapping

from pneuma_lab.cloud.manifests import validate_production_image_receipt


ROOT = Path(__file__).resolve().parents[2]
ROLES = ("controller", "model-server", "benchmark-worker")
DOCKERFILES = {role: ROOT / "infra/docker" / role / "Dockerfile" for role in ROLES}
BASE_DIGEST = "sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


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


def _run(command: list[str], *, cwd: Path = ROOT, input_text: str | None = None) -> str:
    # `text=True` alone decodes with the platform default, which is cp1252 on a
    # Windows builder.  BuildKit progress output carries bytes cp1252 cannot
    # decode, and the failure lands in a `subprocess` reader thread: the thread
    # dies, the main thread keeps going, and the captured output is silently
    # truncated.  A digest parsed from a truncated capture would be wrong rather
    # than absent, so decode explicitly and never let a byte kill the reader.
    result = subprocess.run(
        command,
        cwd=cwd,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stderr[-4000:]}"
        )
    return result.stdout


def _account_id() -> str:
    value = json.loads(_run(["aws", "sts", "get-caller-identity", "--output", "json"]))
    account = value.get("Account")
    if not isinstance(account, str) or not re.fullmatch(r"[0-9]{12}", account):
        raise RuntimeError("AWS account identity is unavailable")
    return account


def _ensure_repository(repository: str) -> None:
    result = subprocess.run(
        [
            "aws",
            "ecr",
            "describe-repositories",
            "--repository-names",
            repository,
            "--region",
            "us-east-1",
            "--output",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        data = json.loads(result.stdout)
        repo = data["repositories"][0]
        if (
            repo.get("imageTagMutability") != "IMMUTABLE"
            or repo.get("imageScanningConfiguration", {}).get("scanOnPush") is not True
        ):
            raise RuntimeError(
                f"existing production repository is not immutable/scanned: {repository}"
            )
        return
    _run(
        [
            "aws",
            "ecr",
            "create-repository",
            "--repository-name",
            repository,
            "--image-tag-mutability",
            "IMMUTABLE",
            "--image-scanning-configuration",
            "scanOnPush=true",
            "--encryption-configuration",
            "encryptionType=AES256",
            "--region",
            "us-east-1",
            "--output",
            "json",
        ]
    )


def _login(account: str) -> None:
    password = _run(["aws", "ecr", "get-login-password", "--region", "us-east-1"])
    _run(
        [
            "docker",
            "login",
            "--username",
            "AWS",
            "--password-stdin",
            f"{account}.dkr.ecr.us-east-1.amazonaws.com",
        ],
        input_text=password,
    )


def _source_date_epoch(commit: str) -> int:
    return int(_run(["git", "show", "-s", "--format=%ct", commit]).strip())


def _source_closure(commit: str, output: Path) -> dict[str, Any]:
    if _run(["git", "rev-parse", "HEAD"]).strip() != commit:
        raise RuntimeError(
            "source HEAD does not equal the authorized image source commit"
        )
    listing = _run(["git", "ls-tree", "-r", "--full-tree", "--long", commit])
    entries: list[dict[str, object]] = []
    for line in listing.splitlines():
        left, path = line.split("\t", 1)
        mode, kind, object_hash, size = left.split()
        entries.append(
            {
                "mode": mode,
                "kind": kind,
                "object_sha256": object_hash,
                "size_bytes": int(size),
                "path": path,
            }
        )
    entries.sort(key=lambda item: str(item["path"]).encode("utf-8"))
    manifest = {
        "record_kind": "cloud_production_source_closure",
        "schema_version": "0.1.0",
        "commit": commit,
        "tree_object_id": _run(["git", "rev-parse", f"{commit}^{{tree}}"]).strip(),
        "files": entries,
    }
    raw = _canonical(manifest)
    manifest_path = output / "source-closure.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(raw)
    manifest["manifest_sha256"] = _sha_bytes(raw)
    return {
        "commit": commit,
        "tree_object_id": manifest["tree_object_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "file_count": len(entries),
        "path": manifest_path.name,
    }


def _archive_checkout(commit: str, destination: Path) -> None:
    archive = subprocess.run(
        ["git", "archive", "--format=tar", commit],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if archive.returncode != 0:
        raise RuntimeError(
            f"git archive failed: {archive.stderr.decode(errors='replace')[-4000:]}"
        )
    with tarfile.open(fileobj=BytesIO(archive.stdout), mode="r:") as handle:
        handle.extractall(destination, filter="data")


def _inspect_digest(text: str) -> str:
    for line in text.splitlines():
        if line.strip().startswith("Digest:"):
            digest = line.split(":", 1)[1].strip()
            if DIGEST_RE.fullmatch(digest):
                return digest
    raise RuntimeError("docker imagetools did not return a root digest")


def _raw_descriptor_digest(raw: bytes, expected: str) -> bool:
    return _sha_bytes(raw) == expected.removeprefix("sha256:") or _sha_bytes(
        raw.rstrip(b"\n")
    ) == expected.removeprefix("sha256:")


def _oci_binding(tag_ref: str) -> dict[str, object]:
    root_text = _run(["docker", "buildx", "imagetools", "inspect", tag_ref])
    root_digest = _inspect_digest(root_text)
    raw_bytes = _run(
        ["docker", "buildx", "imagetools", "inspect", tag_ref, "--raw"]
    ).encode("utf-8")
    raw = json.loads(raw_bytes)
    descriptors = raw.get("manifests") if isinstance(raw, Mapping) else None
    if not isinstance(descriptors, list):
        raise RuntimeError("production image did not publish an OCI root index")
    children = [
        item
        for item in descriptors
        if isinstance(item, Mapping)
        and item.get("platform", {}).get("os") == "linux"
        and item.get("platform", {}).get("architecture") == "amd64"
        and isinstance(item.get("digest"), str)
    ]
    if len(children) != 1:
        raise RuntimeError(
            f"expected exactly one linux/amd64 runtime child, found {len(children)}"
        )
    child = children[0]
    child_digest = str(child["digest"])
    if not DIGEST_RE.fullmatch(child_digest):
        raise RuntimeError("runtime child digest is malformed")
    child_raw = _run(
        [
            "docker",
            "buildx",
            "imagetools",
            "inspect",
            f"{tag_ref}@{child_digest}",
            "--raw",
        ]
    ).encode("utf-8")
    if not _raw_descriptor_digest(child_raw, child_digest):
        raise RuntimeError("runtime child bytes do not match its OCI descriptor digest")
    attestations = [
        item
        for item in descriptors
        if isinstance(item, Mapping)
        and item.get("digest")
        and item.get("annotations", {}).get("vnd.docker.reference.type")
        == "attestation-manifest"
        and item.get("annotations", {}).get("vnd.docker.reference.digest")
        == child_digest
    ]
    if len(attestations) != 1:
        raise RuntimeError(
            "expected exactly one BuildKit in-toto attestation descriptor bound to the runtime child"
        )
    attestation = attestations[0]
    attestation_digest = str(attestation["digest"])
    attestation_raw = _run(
        [
            "docker",
            "buildx",
            "imagetools",
            "inspect",
            f"{tag_ref}@{attestation_digest}",
            "--raw",
        ]
    ).encode("utf-8")
    if not _raw_descriptor_digest(attestation_raw, attestation_digest):
        raise RuntimeError(
            "attestation manifest bytes do not match its descriptor digest"
        )
    attestation_manifest = json.loads(attestation_raw)
    layers = (
        attestation_manifest.get("layers", [])
        if isinstance(attestation_manifest, Mapping)
        else []
    )
    in_toto = [
        layer
        for layer in layers
        if isinstance(layer, Mapping)
        and str(layer.get("mediaType", "")).startswith("application/vnd.in-toto")
        and isinstance(layer.get("digest"), str)
    ]
    if len(in_toto) != 1:
        raise RuntimeError(
            "attestation manifest does not contain exactly one in-toto statement layer"
        )
    layer = in_toto[0]
    return {
        "root_index_digest": root_digest,
        "root_index_media_type": raw.get("mediaType"),
        "child_digest": child_digest,
        "child_media_type": child.get("mediaType"),
        "child_os": child.get("platform", {}).get("os"),
        "child_architecture": child.get("platform", {}).get("architecture"),
        "root_to_child_verified": True,
        "attestation_descriptor_digest": attestation_digest,
        "attestation_media_type": attestation.get("mediaType"),
        "attestation_manifest_sha256": _sha_bytes(attestation_raw),
        "in_toto_statement_digest": layer["digest"],
        "in_toto_statement_media_type": layer["mediaType"],
    }


def _published_tag_exists(tag_ref: str) -> bool:
    """Return whether an immutable ECR tag is already available for receipt work.

    A local timeout can occur after BuildKit has pushed a complete OCI index but
    before KMS receipt generation.  Rebuilding that same immutable tag
    cannot succeed and is unnecessary; the existing OCI/provenance binding is
    subsequently re-verified by ``_oci_binding``.
    """
    result = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", tag_ref],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _kms_approve(
    payload: Mapping[str, object], *, key_id: str, output: Path
) -> dict[str, object]:
    payload_raw = _canonical(payload)
    payload_path = output / f"{payload['role']}.digest-approval.payload.json"
    payload_path.write_bytes(payload_raw)
    result = json.loads(
        _run(
            [
                "aws",
                "kms",
                "sign",
                "--key-id",
                key_id,
                "--message",
                f"fileb://{payload_path}",
                "--message-type",
                "RAW",
                "--signing-algorithm",
                "ED25519_SHA_512",
                "--output",
                "json",
            ]
        )
    )
    signature = result.get("Signature")
    if not isinstance(signature, str):
        raise RuntimeError("KMS did not return a signature")
    approval = dict(payload)
    approval["signature_ed25519_b64"] = signature
    approval["signed_payload_sha256"] = _sha_bytes(payload_raw)
    approval["signer"] = {
        "provider": "aws-kms",
        "key_id": key_id,
        "algorithm": "ED25519_SHA_512",
    }
    approval_path = output / f"{payload['role']}.digest-approval.json"
    _run(
        [
            "aws",
            "kms",
            "verify",
            "--key-id",
            key_id,
            "--message",
            f"fileb://{payload_path}",
            "--signature",
            signature,
            "--message-type",
            "RAW",
            "--signing-algorithm",
            "ED25519_SHA_512",
            "--output",
            "json",
        ]
    )
    approval["record_sha256"] = _sha_bytes(_canonical(approval))
    approval_path.write_bytes(_canonical(approval))
    return approval


def _build_role(
    role: str,
    *,
    account: str,
    commit: str,
    source_date_epoch: int,
    output: Path,
    source_closure: Mapping[str, object],
    context: Path,
    kms_key_id: str,
) -> dict[str, Any]:
    repository = f"pneuma-official-production-{role}"
    _ensure_repository(repository)
    registry = f"{account}.dkr.ecr.us-east-1.amazonaws.com"
    tag_ref = f"{registry}/{repository}:source-{commit[:12]}"
    metadata_path = output / "images" / f"{role}.build-metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    if not _published_tag_exists(tag_ref):
        _run(
            [
                "docker",
                "buildx",
                "build",
                "--platform",
                "linux/amd64",
                "--push",
                "--provenance=mode=max",
                "--sbom=false",
                "--build-arg",
                f"SOURCE_DATE_EPOCH={source_date_epoch}",
                "--tag",
                tag_ref,
                "--metadata-file",
                str(metadata_path),
                "--file",
                str(context / DOCKERFILES[role].relative_to(ROOT)),
                str(context),
            ]
        )
    elif not metadata_path.exists():
        metadata_path.write_bytes(
            _canonical({"resumed_existing_immutable_tag": tag_ref})
        )
    oci = _oci_binding(tag_ref)
    image_ref = f"{registry}/{repository}@{oci['child_digest']}"
    approval_payload = {
        "record_kind": "cloud_production_image_digest_approval",
        "schema_version": "0.1.0",
        "evidence_class": "production_surface_non_scientific",
        "role": role,
        "source_commit": commit,
        "source_closure": dict(source_closure),
        "oci": oci,
    }
    approval = _kms_approve(
        approval_payload, key_id=kms_key_id, output=output / "images"
    )
    receipt = {
        "record_kind": "cloud_production_image_receipt",
        "schema_version": "0.2.0",
        "evidence_class": "production_surface_non_scientific",
        "role": role,
        "source_commit": commit,
        "source_closure": dict(source_closure),
        "dockerfile": f"infra/docker/{role}/Dockerfile",
        "base_image": {
            "repository": "docker.io/vllm/vllm-openai",
            "digest": BASE_DIGEST,
            "platform": "linux/amd64",
        },
        "image_ref": image_ref,
        "image_digest": oci["child_digest"],
        "oci": oci,
        "buildx_metadata_sha256": _sha(metadata_path),
        "provenance": {
            "attestation_format": "buildkit-in-toto-provenance",
            "descriptor_digest": oci["attestation_descriptor_digest"],
            "manifest_sha256": oci["attestation_manifest_sha256"],
            "in_toto_statement_digest": oci["in_toto_statement_digest"],
            "builder": "docker-buildx-provenance-mode-max",
            "source_uri": f"git:{commit}",
        },
        "digest_approval": {
            "record_sha256": approval["record_sha256"],
            "signed_payload_sha256": approval["signed_payload_sha256"],
            "signature_ed25519_b64": approval["signature_ed25519_b64"],
            "signer": approval["signer"],
        },
        "build": {
            "platform": "linux/amd64",
            "tag_mutability": "IMMUTABLE",
            "scan_on_push": True,
            "encryption": "AES256",
            "source_date_epoch": source_date_epoch,
            "network": "buildkit-default-no-runtime-workload",
            "model_download": False,
            "benchmark_execution": False,
        },
        "surface_e2e_status": "pending_bounded_surface_e2e",
    }
    validate_production_image_receipt(receipt)
    (output / "images" / f"{role}.receipt.json").write_bytes(_canonical(receipt))
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--roles", nargs="+", choices=ROLES, default=list(ROLES))
    parser.add_argument("--reuse-image-set", type=Path)
    parser.add_argument("--kms-key-id", default="alias/pneuma-approver")
    args = parser.parse_args(argv)
    if not COMMIT_RE.fullmatch(args.source_commit):
        parser.error("--source-commit must be a full lowercase commit")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    account = _account_id()
    _login(account)
    epoch = _source_date_epoch(args.source_commit)
    with tempfile.TemporaryDirectory(prefix="pneuma-production-build-") as temporary:
        context = Path(temporary)
        _archive_checkout(args.source_commit, context)
        source_closure = _source_closure(args.source_commit, output)
        receipts = [
            _build_role(
                role,
                account=account,
                commit=args.source_commit,
                source_date_epoch=epoch,
                output=output,
                source_closure=source_closure,
                context=context,
                kms_key_id=args.kms_key_id,
            )
            for role in args.roles
        ]
    if args.reuse_image_set:
        existing = json.loads(args.reuse_image_set.read_text(encoding="utf-8"))
        prior_roles = existing.get("roles") if isinstance(existing, Mapping) else None
        if not isinstance(prior_roles, list):
            raise ValueError("reuse image set has no role receipts")
        rebuilt = {receipt["role"] for receipt in receipts}
        for receipt in prior_roles:
            if not isinstance(receipt, Mapping) or receipt.get("role") in rebuilt:
                continue
            validate_production_image_receipt(receipt)
            receipts.append(dict(receipt))
    receipts.sort(key=lambda receipt: ROLES.index(str(receipt["role"])))
    if {receipt["role"] for receipt in receipts} != set(ROLES):
        raise ValueError("image set must contain all three production roles")
    result = {
        "record_kind": "cloud_production_image_set",
        "schema_version": "0.2.0",
        "evidence_class": "production_surface_non_scientific",
        "source_commit": args.source_commit,
        "source_closure": source_closure,
        "roles": receipts,
    }
    (output / "images.json").write_bytes(_canonical(result))
    print(
        json.dumps(
            {
                "source_commit": args.source_commit,
                "source_closure": source_closure,
                "images": {
                    receipt["role"]: receipt["image_digest"] for receipt in receipts
                },
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

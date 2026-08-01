"""Resolve Step 5B benchmark images to immutable linux/amd64 OCI receipts.

Only registry manifests are fetched. Layer blobs are recorded by digest and
size but are not downloaded by this audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


INDEX_MEDIA_TYPES = {
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.index.v1+json",
}
MANIFEST_MEDIA_TYPES = {
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def parse_manifest(value: bytes) -> dict[str, Any]:
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise ValueError("registry document must be an object")
    return decoded


def select_linux_amd64(index: dict[str, Any]) -> str:
    matches = [
        item["digest"]
        for item in index.get("manifests", [])
        if item.get("platform", {}).get("os") == "linux"
        and item.get("platform", {}).get("architecture") == "amd64"
        and not item.get("platform", {}).get("variant")
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one linux/amd64 manifest, found {len(matches)}")
    return matches[0]


def _inspect_raw(reference: str) -> bytes:
    process = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", "--raw", reference],
        capture_output=True,
        check=False,
        timeout=60,
    )
    if process.returncode != 0:
        message = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(message or f"docker inspect exited {process.returncode}")
    return process.stdout


def _resolve_hub_metadata(image: str) -> dict[str, Any]:
    namespace, repository = image.split("/", 1)
    url = f"https://hub.docker.com/v2/repositories/{namespace}/{repository}/tags/latest"
    request = urllib.request.Request(url, headers={"User-Agent": "pneuma-step5b-audit/0.1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        document = json.load(response)
    matches = [
        item
        for item in document.get("images", [])
        if item.get("os") == "linux"
        and item.get("architecture") == "amd64"
        and not item.get("variant")
        and item.get("status") == "active"
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one active linux/amd64 tag image, found {len(matches)}")
    item = matches[0]
    digest = item["digest"]
    return {
        "status": "digest_resolved_metadata_only",
        "image": image,
        "mutable_source_reference": f"docker.io/{image}:latest",
        "platform_reference": f"docker.io/{image}@{digest}",
        "platform": "linux/amd64",
        "manifest_digest": digest,
        "tag_metadata_url": url,
        "declared_compressed_image_bytes": item.get("size"),
        "metadata_limit": "manifest_config_and_layer_receipts_pending",
    }


def resolve_image(image: str) -> tuple[dict[str, Any], bytes | None]:
    mutable_reference = f"docker.io/{image}:latest"
    try:
        raw = _inspect_raw(mutable_reference)
        document = parse_manifest(raw)
        media_type = document.get("mediaType")
        index_sha256 = None
        if media_type in INDEX_MEDIA_TYPES:
            index_sha256 = sha256_bytes(raw)
            child_digest = select_linux_amd64(document)
            raw = _inspect_raw(f"docker.io/{image}@{child_digest}")
            document = parse_manifest(raw)
            if sha256_bytes(raw) != child_digest.removeprefix("sha256:"):
                raise ValueError("selected child bytes do not match the index digest")
        if document.get("mediaType") not in MANIFEST_MEDIA_TYPES:
            raise ValueError(f"unsupported manifest media type {document.get('mediaType')!r}")
        config = document.get("config", {})
        layers = document.get("layers", [])
        if not isinstance(config.get("digest"), str) or not layers:
            raise ValueError("manifest lacks a config digest or layers")
        digest = f"sha256:{sha256_bytes(raw)}"
        return (
            {
                "status": "resolved",
                "image": image,
                "mutable_source_reference": mutable_reference,
                "platform_reference": f"docker.io/{image}@{digest}",
                "platform": "linux/amd64",
                "manifest_digest": digest,
                "manifest_media_type": document["mediaType"],
                "manifest_bytes": len(raw),
                "index_sha256": f"sha256:{index_sha256}" if index_sha256 else None,
                "config_digest": config["digest"],
                "config_size": config.get("size"),
                "layers": [
                    {
                        "digest": layer["digest"],
                        "size": layer.get("size"),
                        "media_type": layer.get("mediaType"),
                    }
                    for layer in layers
                ],
                "compressed_layer_bytes": sum(int(layer.get("size", 0)) for layer in layers),
            },
            raw,
        )
    except (json.JSONDecodeError, OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        registry_error = str(error)
        try:
            receipt = _resolve_hub_metadata(image)
            receipt["registry_manifest_error"] = registry_error
            return receipt, None
        except (json.JSONDecodeError, OSError, urllib.error.URLError, ValueError) as metadata_error:
            metadata_error_type = type(metadata_error).__name__
            metadata_error_message = str(metadata_error)
        return (
            {
                "status": "unresolved",
                "image": image,
                "mutable_source_reference": mutable_reference,
                "error_type": type(error).__name__,
                "error": registry_error,
                "metadata_error_type": metadata_error_type,
                "metadata_error": metadata_error_message,
            },
            None,
        )


def _load_resolved_seeds(paths: list[Path]) -> dict[str, dict[str, Any]]:
    seeds: dict[str, dict[str, Any]] = {}
    for path in paths:
        if not path.exists():
            continue
        audit = json.loads(path.read_text(encoding="utf-8"))
        for item in audit.get("images", []):
            if item.get("status") in {"resolved", "digest_resolved_metadata_only"}:
                seeds[item["image"]] = item
    return seeds


def run(
    licence_audit_path: Path,
    output_dir: Path,
    languages: set[str],
    seed_audits: list[Path],
) -> dict[str, Any]:
    licence_audit = json.loads(licence_audit_path.read_text(encoding="utf-8"))
    rows = [
        row
        for row in licence_audit["rows"]
        if row["licence_status"] == "admissible" and (not languages or row["language"] in languages)
    ]
    images = sorted({row["docker_image"] for row in rows})
    seeds = _load_resolved_seeds(seed_audits)
    pending = [image for image in images if image not in seeds]
    with ThreadPoolExecutor(max_workers=12) as executor:
        fetched = dict(zip(pending, executor.map(resolve_image, pending), strict=True))

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir = output_dir / "manifests"
    manifest_dir.mkdir(exist_ok=True)
    receipts: list[dict[str, Any]] = []
    by_image: dict[str, dict[str, Any]] = {}
    for image in images:
        if image in seeds:
            receipt = dict(seeds[image])
            raw = None
        else:
            receipt, raw = fetched[image]
        if raw is not None:
            path = manifest_dir / f"{receipt['manifest_digest'].removeprefix('sha256:')}.json"
            if path.exists() and path.read_bytes() != raw:
                raise RuntimeError(f"digest collision at {path}")
            path.write_bytes(raw)
            receipt["mirrored_manifest_relative_path"] = path.relative_to(output_dir).as_posix()
        receipts.append(receipt)
        by_image[image] = receipt

    row_receipts = [
        {
            "language": row["language"],
            "repo": row["repo"],
            "instance_id": row["instance_id"],
            "base_commit": row["base_commit"],
            "image": row["docker_image"],
            "oci_status": by_image[row["docker_image"]]["status"],
            "manifest_digest": by_image[row["docker_image"]].get("manifest_digest"),
        }
        for row in rows
    ]
    summary = {
        "record_kind": "step5b_local_oci_audit",
        "schema_version": "0.1.0",
        "licence_audit_sha256": sha256_bytes(licence_audit_path.read_bytes()),
        "languages": sorted(languages),
        "candidate_rows": len(rows),
        "resolved_images": sum(item["status"] == "resolved" for item in receipts),
        "metadata_only_images": sum(item["status"] == "digest_resolved_metadata_only" for item in receipts),
        "unresolved_images": sum(item["status"] == "unresolved" for item in receipts),
        "declared_compressed_layer_bytes": sum(
            int(item.get("compressed_layer_bytes", 0)) for item in receipts
        ),
        "metadata_declared_compressed_image_bytes": sum(
            int(item.get("declared_compressed_image_bytes", 0)) for item in receipts
        ),
        "images": receipts,
        "rows": row_receipts,
    }
    (output_dir / "oci-audit.json").write_bytes(canonical_json(summary))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--licence-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--languages", nargs="*", default=[])
    parser.add_argument("--seed-audit", type=Path, action="append", default=[])
    args = parser.parse_args()
    summary = run(args.licence_audit, args.output_dir, set(args.languages), args.seed_audit)
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "languages",
                    "candidate_rows",
                    "resolved_images",
                    "metadata_only_images",
                    "unresolved_images",
                    "declared_compressed_layer_bytes",
                    "metadata_declared_compressed_image_bytes",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

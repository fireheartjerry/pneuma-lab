"""Resolve the exact selected C160 OCI roster, upgrading metadata-only pins."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from step5b_oci_audit import canonical_json, resolve_image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--seed-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--languages", nargs="+", required=True)
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    seed = json.loads(args.seed_audit.read_text(encoding="utf-8"))
    seed_images = {item["image"]: item for item in seed["images"] if item["status"] == "resolved"}
    rows = [row for row in selection["rows"] if row["language"] in set(args.languages)]
    pending = sorted({row["docker_image"] for row in rows if row["docker_image"] not in seed_images})
    with ThreadPoolExecutor(max_workers=8) as executor:
        fetched = dict(zip(pending, executor.map(resolve_image, pending), strict=True))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifests = args.output_dir / "manifests"
    manifests.mkdir(exist_ok=True)
    images = []
    for image in sorted({row["docker_image"] for row in rows}):
        if image in seed_images:
            receipt = dict(seed_images[image])
            raw = None
        else:
            receipt, raw = fetched[image]
        if raw is not None:
            path = manifests / f"{receipt['manifest_digest'].removeprefix('sha256:')}.json"
            path.write_bytes(raw)
            receipt["mirrored_manifest_relative_path"] = path.relative_to(args.output_dir).as_posix()
        images.append(receipt)
    by_image = {item["image"]: item for item in images}
    result = {
        "record_kind": "step5b_c160_oci_receipt",
        "schema_version": "0.1.0",
        "languages": sorted(set(args.languages)),
        "selection_licence_audit_sha256": selection["licence_audit_sha256"],
        "selection_oci_audit_sha256": selection["oci_audit_sha256"],
        "resolved_images": sum(item["status"] == "resolved" for item in images),
        "metadata_only_images": sum(item["status"] == "digest_resolved_metadata_only" for item in images),
        "unresolved_images": sum(item["status"] == "unresolved" for item in images),
        "images": images,
        "rows": [
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
        ],
    }
    (args.output_dir / "oci-receipt.json").write_bytes(canonical_json(result))
    print(json.dumps({key: result[key] for key in ("languages", "resolved_images", "metadata_only_images", "unresolved_images")}))
    return 0 if result["metadata_only_images"] == result["unresolved_images"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

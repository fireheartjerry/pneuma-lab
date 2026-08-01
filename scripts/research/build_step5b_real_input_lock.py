"""Build the real Step 5B candidate input lock from sealed mirror evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.input_lock import build_candidate_input_lock, classify_input_lock
from pneuma_lab.cloud.inputs import verify_input_lock, verify_input_receipts
from pneuma_lab.cloud.payload_mirror_receipt import validate_payload_mirror_semantics


ROLE_LICENSES = {
    "subject_model": ("Apache-2.0", "qwen36-license.txt"),
    "tokenizer": ("Apache-2.0", "qwen36-license.txt"),
    "simulator_model": ("Apache-2.0", "qwen35-license.txt"),
    "swe_harness": ("MIT", "swe-license.txt"),
    "swe_dataset": ("MIT", "swe-dataset-readme.md"),
    "tau2_harness": ("MIT", "tau2-license.txt"),
    "repo_launcher": ("MIT", "repolaunch-license.txt"),
}
PIN_ROLES = tuple(ROLE_LICENSES)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _write(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    raw = canonical_bytes(record) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"relative_path": path.as_posix(), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def build(args: argparse.Namespace) -> dict[str, Any]:
    manifest = _load(args.manifest)
    plan = _load(args.plan)
    pricing = _load(args.pricing)
    mirror = validate_payload_mirror_semantics(_load(args.mirror_receipt), plan, manifest, pricing)
    sources = {source["role"]: source for source in _load(args.inventory_receipt)["sources"]}
    mirrored = {item["object_id"]: item for item in mirror["objects"]}
    expected = {item["object_id"]: item for item in manifest["objects"] if item["retrieval_required"]}
    root = args.output_dir
    receipt_dir = root / "receipts"

    snapshots: dict[str, dict[str, Any]] = {}
    for role in PIN_ROLES:
        objects = []
        for object_id, item in expected.items():
            if role in item["consumers"]:
                observed = mirrored[object_id]
                objects.append({
                    "object_id": object_id,
                    "path": item.get("path"),
                    "payload_sha256": observed["payload_sha256"],
                    "size_bytes": observed["size_bytes"],
                    "upstream_identity": observed["upstream_identity"],
                    "upstream_identity_algorithm": observed["upstream_identity_algorithm"],
                })
        if not objects:
            raise ValueError(f"role {role} has no mirrored objects")
        source = sources[role]
        record = {
            "record_kind": "step5b_artifact_snapshot_receipt",
            "schema_version": "0.1.0",
            "role": role,
            "service": source["service"],
            "repository": source["repository"],
            "revision": source["revision"],
            "object_count": len(objects),
            "payload_bytes": sum(item["size_bytes"] for item in objects),
            "objects": sorted(objects, key=lambda item: item["object_id"]),
            "payload_mirror_receipt_sha256": hashlib.sha256(args.mirror_receipt.read_bytes()).hexdigest(),
        }
        ref = _write(receipt_dir / f"{role}-snapshot.json", record)
        ref["relative_path"] = f"receipts/{role}-snapshot.json"
        snapshots[role] = ref

    license_evidence = []
    for role, (family, filename) in ROLE_LICENSES.items():
        path = args.source_license_dir / filename
        source = sources[role]
        candidates = [item for item in expected.values() if role in item["consumers"] and item.get("path") in {"LICENSE", "README.md"}]
        match = next((item for item in candidates if mirrored[item["object_id"]]["payload_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()), None)
        if match is None or path.stat().st_size != match["size_bytes"]:
            raise ValueError(f"license evidence for {role} is not bound to a mirrored object")
        license_evidence.append({
            "role": role, "repository": source["repository"], "revision": source["revision"],
            "license": family, "evidence_object_id": match["object_id"],
            "evidence_path": match["path"], "payload_sha256": mirrored[match["object_id"]]["payload_sha256"],
            "size_bytes": match["size_bytes"],
        })
    source_license_ref = _write(receipt_dir / "source-license-audit.json", {
        "record_kind": "step5b_source_license_audit", "schema_version": "0.1.0",
        "payload_mirror_receipt_sha256": hashlib.sha256(args.mirror_receipt.read_bytes()).hexdigest(),
        "evidence": sorted(license_evidence, key=lambda item: item["role"]),
    })
    source_license_ref["relative_path"] = "receipts/source-license-audit.json"

    task_license_target = receipt_dir / "task-license-audit.json"
    contamination_target = receipt_dir / "public-artifact-contamination.json"
    shutil.copyfile(args.task_license_audit, task_license_target)
    shutil.copyfile(args.contamination_receipt, contamination_target)
    task_license_ref = {"relative_path": "receipts/task-license-audit.json", "sha256": hashlib.sha256(task_license_target.read_bytes()).hexdigest(), "size_bytes": task_license_target.stat().st_size}
    contamination_ref = {"relative_path": "receipts/public-artifact-contamination.json", "sha256": hashlib.sha256(contamination_target.read_bytes()).hexdigest(), "size_bytes": contamination_target.stat().st_size}

    def pin(role: str) -> dict[str, Any]:
        source = sources[role]
        return {"repository": source["repository"], "revision": source["revision"], "license": ROLE_LICENSES[role][0], "snapshot_receipt": snapshots[role]}

    dataset_snapshot = receipt_dir / "swe_dataset-snapshot.json"
    lock = build_candidate_input_lock(
        frozen_timestamp=args.frozen_timestamp,
        provenance={"design_sha256": _lf_sha256(args.design), "code_sha256": _lf_sha256(Path(__file__))},
        model_pins=[pin("subject_model"), pin("simulator_model")],
        tokenizer_pin=pin("tokenizer"),
        benchmark_pins=[{
            **pin("swe_harness"),
            "dataset_revision": sources["swe_dataset"]["revision"],
            "task_manifest_sha256": hashlib.sha256(dataset_snapshot.read_bytes()).hexdigest(),
            "task_manifest_size_bytes": dataset_snapshot.stat().st_size,
        }],
        container_bases=[{
            "repository": sources["worker_base"]["repository"],
            "digest": "linux/amd64@" + sources["worker_base"]["revision"],
            "manifest_size_bytes": sources["worker_base"]["pages"][0]["size_bytes"],
        }],
        verifier_sources=[pin("tau2_harness"), pin("repo_launcher")],
        contamination_receipts=[contamination_ref],
        license_receipts=[source_license_ref, task_license_ref],
    )
    args.output.write_bytes(canonical_bytes(lock) + b"\n")
    verify_input_receipts(lock, root)
    return {"classification": classify_input_lock(lock), "input_lock_sha256": verify_input_lock(lock)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--pricing", type=Path, required=True)
    parser.add_argument("--mirror-receipt", type=Path, required=True)
    parser.add_argument("--inventory-receipt", type=Path, required=True)
    parser.add_argument("--source-license-dir", type=Path, required=True)
    parser.add_argument("--task-license-audit", type=Path, required=True)
    parser.add_argument("--contamination-receipt", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--frozen-timestamp", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

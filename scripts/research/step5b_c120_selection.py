"""Select the exact minimum C120 repository-lineage qualification roster."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_REPOSITORIES = {"c": 12, "cpp": 17, "cs": 19, "go": 20, "java": 19, "js": 19, "rust": 19, "ts": 19}
STATUS_RANK = {"resolved": 0, "digest_resolved_metadata_only": 1, "unresolved": 2}


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def select(licence_path: Path, oci_path: Path, authority_path: Path) -> dict[str, Any]:
    licence = json.loads(licence_path.read_text(encoding="utf-8"))
    oci = json.loads(oci_path.read_text(encoding="utf-8"))
    by_image = {row["image"]: row for row in oci["rows"]}
    selected: list[dict[str, Any]] = []
    for language, required in REQUIRED_REPOSITORIES.items():
        candidates = [row for row in licence["rows"] if row["language"] == language and row["licence_status"] == "admissible"]
        candidates.sort(key=lambda row: (STATUS_RANK[by_image[row["docker_image"]]["oci_status"]], row["repo"].lower(), row["instance_id"]))
        seen: set[str] = set()
        for row in candidates:
            if row["repo"].lower() in seen:
                continue
            oci_row = by_image[row["docker_image"]]
            if oci_row["manifest_digest"] is None:
                continue
            selected.append({**row, "oci": oci_row})
            seen.add(row["repo"].lower())
            if len(seen) == required:
                break
        if len(seen) != required:
            raise RuntimeError(f"{language}: needed {required} immutable OCI repositories, found {len(seen)}")
    return {
        "record_kind": "step5b_c120_qualification_selection",
        "schema_version": "0.1.0",
        "authority_sha256": hashlib.sha256(authority_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "licence_audit_sha256": hashlib.sha256(licence_path.read_bytes()).hexdigest(),
        "oci_audit_sha256": hashlib.sha256(oci_path.read_bytes()).hexdigest(),
        "required_repositories": REQUIRED_REPOSITORIES,
        "selection_rule": "admissible distinct repository; immutable OCI digest; resolved status then repository then instance id",
        "rows": selected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--licence-audit", type=Path, required=True)
    parser.add_argument("--oci-audit", type=Path, required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = select(args.licence_audit, args.oci_audit, args.authority)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(result))
    print(json.dumps({"rows": len(result["rows"]), "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

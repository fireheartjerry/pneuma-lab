"""Build the deterministic C120 three-pair isolation case manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pneuma_lab.cloud.authorization_keys import canonical_bytes


LANGUAGE = {"c": "c", "cpp": "cpp", "cs": "cs", "go": "go", "java": "java", "js": "js", "rust": "rust", "ts": "ts"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--swe-selection", type=Path, required=True)
    parser.add_argument("--tau2-selection", type=Path, required=True)
    parser.add_argument("--input-lock-sha256", required=True)
    parser.add_argument("--tau2-sandbox-image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    swe = json.loads(args.swe_selection.read_text(encoding="utf-8"))
    tau2 = json.loads(args.tau2_selection.read_text(encoding="utf-8"))
    cases = []
    by_language = {language: [] for language in LANGUAGE}
    for row in swe["rows"]:
        by_language[row["language"]].append(row)
    for language in LANGUAGE:
        for index, row in enumerate(by_language[language][:3]):
            digest = row["oci"]["manifest_digest"]
            cases.append({"pair_id": f"swe-{language}-{index + 1}", "family": "swe", "split": language,
                          "unit_id": row["instance_id"],
                          "image_reference": f"docker.io/{row['docker_image']}@{digest}"})
    for split in ("airline", "telecom", "banking"):
        task_ids = [row["task_id"] for row in tau2["rows"] if row["domain"] == split]
        for index, task_id in enumerate(task_ids[:3]):
            cases.append({"pair_id": f"tau2-{split}-{index + 1}", "family": "tau2", "split": split,
                          "unit_id": f"{split}:{task_id}", "image_reference": args.tau2_sandbox_image})
    body = {"record_kind": "step5b_isolation_case_manifest", "schema_version": "0.1.0",
            "input_lock_sha256": args.input_lock_sha256, "cases": cases}
    body["manifest_sha256"] = hashlib.sha256(canonical_bytes(body)).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(body) + b"\n")
    print(body["manifest_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

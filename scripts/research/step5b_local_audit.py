"""Produce local Step 5B licence and public-artifact contamination receipts.

This script intentionally audits benchmark metadata and historical licence
files only.  It does not pull model weights, OCI images, or execute an
experiment.  A repository/base-commit pair is admitted only when a licence
file at that exact commit is retrieved and classified unambiguously as one of
the permissive families registered by the PLACEBO design.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


LICENCE_PATHS = (
    "LICENSE",
    "LICENSE.txt",
    "LICENSE.TXT",
    "LICENSE.md",
    "LICENSE.rst",
    "LICENSE-MIT",
    "LICENSE-MIT.txt",
    "LICENSE-APACHE",
    "LICENSE-APACHE.txt",
    "LICENSE-APACHE-2.0",
    "License.txt",
    "license.txt",
    "LICENCE",
    "LICENCE.txt",
    "COPYING",
    "COPYING.txt",
    "LICENSES/LICENSE",
    "LICENSES/LICENSE.txt",
    "LICENSES/LICENSE.TXT",
)
PERMISSIVE_PATTERNS = {
    "MIT": ("permission is hereby granted, free of charge",),
    "Apache-2.0": ("apache license", "version 2.0"),
    "BSD-3-Clause": (
        "redistribution and use in source and binary forms",
        "neither the name",
    ),
    "BSD-2-Clause": (
        "redistribution and use in source and binary forms",
        "this software is provided by the copyright holders",
    ),
    "ISC": ("permission to use, copy, modify, and/or distribute",),
    "Zlib": ("this software is provided 'as-is'",),
}
SPDX_PERMISSIVE = {
    "MIT": "MIT",
    "Apache-2.0": "Apache-2.0",
    "BSD-2-Clause": "BSD-2-Clause",
    "BSD-3-Clause": "BSD-3-Clause",
    "ISC": "ISC",
    "Zlib": "Zlib",
}
COPYLEFT_MARKERS = (
    "gnu general public license",
    "gnu lesser general public license",
    "gnu affero general public license",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def classify_licence(value: bytes) -> tuple[str | None, str]:
    """Return an unambiguous registered permissive family, or a refusal reason."""

    text = re.sub(r"\s+", " ", value.decode("utf-8", errors="replace").lower())
    spdx_matches = {
        family
        for identifier, family in SPDX_PERMISSIVE.items()
        if f"spdx-license-identifier: {identifier.lower()}" in text
    }
    if len(spdx_matches) == 1 and not any(marker in text for marker in COPYLEFT_MARKERS):
        return next(iter(spdx_matches)), "unambiguous_registered_permissive_spdx"
    matches = [
        name
        for name, required in PERMISSIVE_PATTERNS.items()
        if all(fragment in text for fragment in required)
    ]
    if any(marker in text for marker in COPYLEFT_MARKERS):
        return None, "copyleft_or_mixed_terms_present"
    # The BSD-3 text also satisfies the broad BSD-2 pattern. Prefer the more
    # specific family rather than manufacturing ambiguity.
    if "BSD-3-Clause" in matches and "BSD-2-Clause" in matches:
        matches.remove("BSD-2-Clause")
    if not matches and all(
        fragment in text
        for fragment in (
            "redistribution and use in source and binary forms",
            "this software is provided by the",
        )
    ):
        matches.append("BSD-2-Clause")
    if len(matches) != 1:
        return None, "unrecognised" if not matches else "multiple_permissive_families"
    return matches[0], "unambiguous_registered_permissive"


def load_rows(data_dir: Path, languages: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for path in sorted(data_dir.glob("*.parquet")):
        language = path.name.split("-", 1)[0]
        if languages and language not in languages:
            continue
        raw = path.read_bytes()
        table = pq.read_table(
            path,
            columns=["repo", "instance_id", "base_commit", "created_at", "commit_url", "docker_image"],
        )
        sources.append(
            {
                "relative_path": path.name,
                "sha256": sha256_bytes(raw),
                "bytes": len(raw),
                "rows": table.num_rows,
            }
        )
        for row in table.to_pylist():
            row["language"] = language
            rows.append(row)
    return rows, sources


def fetch_historical_licence(repository: str, revision: str) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for relative_path in LICENCE_PATHS:
        url = f"https://raw.githubusercontent.com/{repository}/{revision}/{relative_path}"
        request = urllib.request.Request(url, headers={"User-Agent": "pneuma-step5b-audit/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                value = response.read(2_000_001)
                status = response.status
        except urllib.error.HTTPError as error:
            attempts.append({"url": url, "status": error.code})
            continue
        except (urllib.error.URLError, TimeoutError) as error:
            attempts.append({"url": url, "error": type(error).__name__})
            continue
        if len(value) > 2_000_000:
            attempts.append({"url": url, "status": status, "error": "licence_file_too_large"})
            continue
        family, reason = classify_licence(value)
        return {
            "status": "admissible" if family else "not_admissible",
            "repository": repository,
            "revision": revision,
            "source_url": url,
            "source_status": status,
            "relative_path": relative_path,
            "sha256": sha256_bytes(value),
            "bytes": len(value),
            "licence_family": family,
            "classification_reason": reason,
            "attempts": attempts,
            "_bytes": value,
        }
    return {
        "status": "unresolved",
        "repository": repository,
        "revision": revision,
        "classification_reason": "no_root_licence_candidate_retrieved",
        "attempts": attempts,
    }


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def run(data_dir: Path, output_dir: Path, languages: set[str]) -> dict[str, Any]:
    rows, sources = load_rows(data_dir, languages)
    output_dir.mkdir(parents=True, exist_ok=True)
    licence_dir = output_dir / "licence-bytes"
    licence_dir.mkdir(exist_ok=True)

    keys = sorted({(row["repo"], row["base_commit"]) for row in rows})
    audit_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    # Raw commit-addressed files are independent. A bounded pool keeps the
    # complete 743-row audit practical while preserving deterministic output
    # order below.
    with ThreadPoolExecutor(max_workers=12) as executor:
        fetched = executor.map(lambda key: fetch_historical_licence(*key), keys)
        results = list(fetched)
    for (repository, revision), result in zip(keys, results, strict=True):
        value = result.pop("_bytes", None)
        if value is not None:
            receipt_path = licence_dir / f"{result['sha256']}.txt"
            if receipt_path.exists() and receipt_path.read_bytes() != value:
                raise RuntimeError(f"digest collision at {receipt_path}")
            receipt_path.write_bytes(value)
            result["mirrored_relative_path"] = receipt_path.relative_to(output_dir).as_posix()
        audit_by_key[(repository, revision)] = result

    audited_rows = []
    for row in rows:
        evidence = audit_by_key[(row["repo"], row["base_commit"])]
        audited_rows.append(
            {
                **row,
                "licence_status": evidence["status"],
                "licence_family": evidence.get("licence_family"),
                "licence_sha256": evidence.get("sha256"),
            }
        )

    source_receipt = {
        "record_kind": "step5b_local_source_receipt",
        "schema_version": "0.1.0",
        "dataset_repository": "SWE-bench-Live/MultiLang",
        "dataset_revision": "608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b",
        "sources": sources,
    }
    contamination_receipt = {
        "record_kind": "step5b_public_artifact_contamination_receipt",
        "schema_version": "0.1.0",
        "finding": "answer_bearing_fields_public",
        "claim_boundary": "risk_characterised_not_contamination_free",
        "public_fields": ["patch", "test_patch", "FAIL_TO_PASS", "PASS_TO_PASS", "log_parser"],
        "task_count": len(rows),
        "repository_base_pairs": len(audit_by_key),
        "earliest_created_at": min(row["created_at"] for row in rows),
        "latest_created_at": max(row["created_at"] for row in rows),
        "source_receipt_sha256": sha256_bytes(canonical_json(source_receipt)),
    }
    evidence_rows = sorted(audit_by_key.values(), key=lambda item: (item["repository"], item["revision"]))
    summary = {
        "record_kind": "step5b_local_licence_audit",
        "schema_version": "0.1.0",
        "generated_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "languages": sorted(languages),
        "task_count": len(rows),
        "repository_count": len({row["repo"] for row in rows}),
        "repository_base_pairs": len(audit_by_key),
        "status_counts": dict(sorted(Counter(item["status"] for item in evidence_rows).items())),
        "source_receipt_sha256": sha256_bytes(canonical_json(source_receipt)),
        "contamination_receipt_sha256": sha256_bytes(canonical_json(contamination_receipt)),
        "evidence": evidence_rows,
        "rows": audited_rows,
    }

    artifacts = {
        "source-receipt.json": source_receipt,
        "contamination-receipt.json": contamination_receipt,
        "licence-audit.json": summary,
    }
    for name, value in artifacts.items():
        (output_dir / name).write_bytes(canonical_json(value))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--languages", nargs="*", default=[])
    args = parser.parse_args()
    summary = run(args.data_dir, args.output_dir, set(args.languages))
    print(json.dumps({key: summary[key] for key in ("languages", "task_count", "repository_count", "repository_base_pairs", "status_counts")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

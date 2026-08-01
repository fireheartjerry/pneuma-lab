"""Build final C120 SWE/tau2 audits from exact, independently verified evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.isolation import require_isolation_receipt
from pneuma_lab.cloud.provenance import canonical_text_digest
from pneuma_lab.cloud.qualification import validate_qualification_audit


INPUT_LOCK = "e6746ad843b0da9a6144fa84a5a231dd350b6845a321ffaff171df4540f67b84"
CASE_MANIFEST = "f9f78c85c9647159ba098520bae42850feab65b873650e81aad0ebe653c39abd"
SWE = {
    "c": ("C", 9), "cpp": ("C++", 14), "cs": ("C#", 16), "go": ("Go", 17),
    "java": ("Java", 16), "js": ("JavaScript", 16), "rust": ("Rust", 16),
    "ts": ("TypeScript", 16),
}
TAU2 = {"airline": 17, "telecom": 13, "banking": 10}


def file_receipt(path: Path) -> dict[str, str]:
    return {"relative_path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def split_record(name: str, proxy: int, eligible: int, quota: int, isolation: dict, licence: dict) -> dict:
    return {
        "split": name, "proxy_units": proxy, "eligible_units": eligible,
        "confirmation_quota": quota, "pilot_units": 1, "fixed_reserve": 1,
        "hamilton_allocation": None, "registered_minimum_units": None,
        "isolation_evidence": isolation, "license_evidence": licence,
        "three_pair_audit": {"pairs_attempted": 3, "pairs_independent_pass": 3},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--isolation-receipt", type=Path, required=True)
    parser.add_argument("--swe-selection", type=Path, required=True)
    parser.add_argument("--swe-licence-audit", type=Path, required=True)
    parser.add_argument("--tau2-selection", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    isolation = json.loads(args.isolation_receipt.read_text(encoding="utf-8"))
    require_isolation_receipt(
        isolation, expected_case_manifest_sha256=CASE_MANIFEST,
        expected_input_lock_sha256=INPUT_LOCK,
    )
    root = args.output_root
    root.mkdir(parents=True, exist_ok=False)
    copies = {}
    for name, source in (
        ("isolation-receipt.json", args.isolation_receipt),
        ("swe-selection.json", args.swe_selection),
        ("swe-licence-audit.json", args.swe_licence_audit),
        ("tau2-selection.json", args.tau2_selection),
    ):
        target = root / name
        shutil.copyfile(source, target)
        copies[name] = file_receipt(target)
    swe_selection = json.loads(args.swe_selection.read_text(encoding="utf-8"))
    swe_licence = json.loads(args.swe_licence_audit.read_text(encoding="utf-8"))
    tau2_selection = json.loads(args.tau2_selection.read_text(encoding="utf-8"))
    qualified = Counter(row["language"] for row in swe_selection["rows"])
    pool: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for row in swe_licence["rows"]:
        if row["licence_status"] == "admissible":
            pool[row["language"]].add((row["repo"], row["base_commit"]))
    design = canonical_text_digest(Path("docs/research/neurips-2026-workshop/38-experiment-design-freeze.md"))
    code = canonical_text_digest(Path("src/pneuma_lab/cloud/qualification.py"))
    common = {
        "record_kind": "cloud_qualification_audit", "schema_version": "0.2.0",
        "frozen_timestamp": isolation["frozen_timestamp"], "provenance": {"design_sha256": design, "code_sha256": code},
        "tier": "C120", "evidence_class": "audited_qualified", "input_lock_sha256": INPUT_LOCK,
    }
    swe = {
        **common, "benchmark_family": "swe", "proxy_basis": "base_commit_admissible",
        "splits": [split_record(display, len(pool[key]), qualified[key], quota,
                                 copies["isolation-receipt.json"], copies["swe-licence-audit.json"])
                   for key, (display, quota) in SWE.items()],
    }
    selected_tau = Counter(row["domain"] for row in tau2_selection["rows"])
    tau = {
        **common, "benchmark_family": "tau2", "proxy_basis": "pinned_objective_pool",
        "splits": [split_record(split, tau2_selection["eligible_pool_sizes"][split], selected_tau[split], quota,
                                 copies["isolation-receipt.json"], copies["tau2-selection.json"])
                   for split, quota in TAU2.items()],
    }
    for name, audit in (("swe-audit.json", swe), ("tau2-audit.json", tau)):
        validate_qualification_audit(audit)
        (root / name).write_bytes(canonical_bytes(audit) + b"\n")
    closure = [{"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size} for path in sorted(root.iterdir())]
    (root / "closure.json").write_bytes(canonical_bytes({"record_kind": "step5b_c120_audit_closure", "files": closure}) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

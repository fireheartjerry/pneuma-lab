"""Recompute the provenance digests the committed cloud fixtures bind.

Several committed fixtures bind the exact bytes of the design freeze and of the
module that interprets them, so that a fixture cannot silently outlive the
contract it was derived against. Those digests therefore change whenever the
design document or the module changes, and re-deriving them by hand is both
tedious and easy to get subtly wrong.

This command is the deterministic derivation. It rewrites nothing else: counts,
scopes, ceilings, statuses, and signatures are untouched, so it cannot turn a
candidate into an authorization or move a lineage count. Run it after editing
the design freeze or one of the bound modules, then re-run the focused tests.

    python scripts/refresh_cloud_fixture_provenance.py [--check]

`--check` verifies without writing and exits non-zero on drift, which is what a
CI or pre-commit caller should use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "fixtures" / "cloud"
DESIGN = REPO_ROOT / "docs/research/neurips-2026-workshop/38-experiment-design-freeze.md"

# fixture filename -> module whose bytes that fixture's `code_sha256` binds.
BOUND_CODE = {
    "qualification-audit-c120-proxy.json": "src/pneuma_lab/cloud/qualification.py",
    "qualification-audit-c160-proxy.json": "src/pneuma_lab/cloud/qualification.py",
    "qualification-audit-tau2-c120-proxy.json": "src/pneuma_lab/cloud/qualification.py",
    "qualification-audit-tau2-c160-proxy.json": "src/pneuma_lab/cloud/qualification.py",
    "retrieval-authorization-candidate.json": "src/pneuma_lab/cloud/retrieval.py",
}

# Fixtures that additionally bind a recomputed input-lock digest.
BOUND_LOCK = ("retrieval-authorization-candidate.json",)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh(*, check: bool) -> int:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from pneuma_lab.cloud.inputs import verify_input_lock

    design = _digest(DESIGN)
    lock_digest = verify_input_lock(json.loads((FIXTURES / "input-lock-fixture.json").read_text(encoding="utf-8")))
    drifted: list[str] = []

    for name, module in sorted(BOUND_CODE.items()):
        path = FIXTURES / name
        if not path.is_file():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        expected = {"design_sha256": design, "code_sha256": _digest(REPO_ROOT / module)}
        changed = record.get("provenance") != expected
        record["provenance"] = expected
        if name in BOUND_LOCK and record.get("input_lock_sha256") != lock_digest:
            record["input_lock_sha256"] = lock_digest
            changed = True
        if not changed:
            continue
        drifted.append(name)
        if not check:
            path.write_text(json.dumps(record, indent=4) + "\n", encoding="utf-8")

    if check:
        for name in drifted:
            print(f"stale provenance: {name}", file=sys.stderr)
        return 1 if drifted else 0
    for name in drifted:
        print(f"refreshed {name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify without writing; non-zero exit on drift")
    return refresh(check=parser.parse_args().check)


if __name__ == "__main__":
    raise SystemExit(main())

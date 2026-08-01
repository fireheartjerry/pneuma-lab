"""Minimal executable boundary for the three production image roles.

This is deliberately not a benchmark runner.  It verifies only a supplied,
content-addressed harness byte stream and emits one canonical terminal receipt.
Real E2E qualification must execute this exact entrypoint under a separately
admitted image/action and bind its receipt into the production-surface record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

_ROLES = frozenset({"controller", "model-server", "benchmark-worker"})


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=sorted(_ROLES))
    parser.add_argument("--harness", required=True, type=Path)
    parser.add_argument("--harness-sha256", required=True)
    args = parser.parse_args(argv)
    if len(args.harness_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in args.harness_sha256):
        parser.error("--harness-sha256 must be lowercase SHA-256")
    payload = args.harness.read_bytes()
    observed = hashlib.sha256(payload).hexdigest()
    if observed != args.harness_sha256:
        print(_canonical({"role": args.role, "state": "FAILED", "reason": "harness_sha256_mismatch"}))
        return 2
    print(_canonical({"role": args.role, "state": "READY", "harness_sha256": observed, "harness_bytes": len(payload)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Concrete subprocess boundary for the pinned SWE/tau2 benchmark surfaces.

The official image contains this dispatcher, but not benchmark data or a
fixture evaluator.  An authorized deployment must stage a digest-verified
adapter manifest under ``PNEUMA_BENCHMARK_SURFACE_ROOT``.  Missing or mutable
adapter inputs fail closed; there is deliberately no deterministic fallback.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _load_payload() -> dict[str, Any]:
    value = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("request must be an object")
    return value


def _adapter_manifest(root: Path, benchmark: str) -> tuple[list[str], str]:
    manifest_path = root / "adapter-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("digest-bound benchmark adapter manifest is missing")
    raw = manifest_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != os.environ.get("PNEUMA_BENCHMARK_ADAPTER_MANIFEST_SHA256"):
        raise ValueError("benchmark adapter manifest digest mismatch")
    manifest = json.loads(raw.decode("utf-8"))
    if not isinstance(manifest, dict) or manifest.get("record_kind") != "cloud_registered_benchmark_adapter_manifest":
        raise ValueError("benchmark adapter manifest identity mismatch")
    entry = manifest.get("adapters", {}).get(benchmark)
    if not isinstance(entry, dict) or not isinstance(entry.get("argv"), list) or not entry["argv"]:
        raise ValueError(f"no registered adapter for {benchmark}")
    argv = [item for item in entry["argv"] if isinstance(item, str) and item]
    if len(argv) != len(entry["argv"]):
        raise ValueError("benchmark adapter argv is malformed")
    return argv, hashlib.sha256(raw).hexdigest()


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "evaluate"}:
        print(json.dumps({"error": "operation must be prepare or evaluate"}, sort_keys=True))
        return 2
    try:
        payload = _load_payload()
        task = payload.get("task")
        if not isinstance(task, dict):
            raise ValueError("task object is required")
        benchmark = task.get("benchmark")
        if benchmark not in {"swe_multilang", "tau2"}:
            raise ValueError("task benchmark is not registered")
        root_value = os.environ.get("PNEUMA_BENCHMARK_SURFACE_ROOT")
        if not root_value:
            raise ValueError("PNEUMA_BENCHMARK_SURFACE_ROOT is required")
        argv, manifest_digest = _adapter_manifest(Path(root_value), benchmark)
        result = subprocess.run(
            [*argv, sys.argv[1]],
            input=_canonical(payload),
            capture_output=True,
            check=False,
            timeout=int(os.environ.get("PNEUMA_BENCHMARK_ADAPTER_TIMEOUT_SECONDS", "1800")),
            shell=False,
        )
        if result.returncode != 0:
            sys.stderr.buffer.write(result.stderr[-4096:])
            return result.returncode
        output = json.loads(result.stdout.decode("utf-8"))
        if not isinstance(output, dict):
            raise ValueError("registered benchmark adapter returned a non-object")
        output["_pneuma_adapter_manifest_sha256"] = manifest_digest
        sys.stdout.buffer.write(_canonical(output))
        return 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__}, sort_keys=True), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

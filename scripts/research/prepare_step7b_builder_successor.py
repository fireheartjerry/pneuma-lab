"""Prepare a fresh zero-retry Step 7B builder plan from an exhausted predecessor."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROLES = ("controller", "model-server", "benchmark-worker")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _replace_action(value: str, previous_action: str, next_action: str) -> str:
    if previous_action not in value:
        raise ValueError(f"expected predecessor action in {value!r}")
    return value.replace(previous_action, next_action)


def prepare(
    predecessor: dict[str, Any],
    *,
    root: Path,
    archive: Path,
    action_id: str,
    frozen_timestamp: str,
    expires_timestamp: str,
    source_commit: str,
    production_surface: bool = False,
) -> dict[str, Any]:
    previous_action = predecessor.get("action_id")
    if not isinstance(previous_action, str) or re.fullmatch(r"step7b-aws-builder-[0-9]{3}", previous_action) is None:
        raise ValueError("predecessor has an invalid action id")
    if re.fullmatch(r"step7b-aws-builder-[0-9]{3}", action_id) is None or action_id == previous_action:
        raise ValueError("successor requires a distinct numbered action id")
    plan = json.loads(json.dumps(predecessor))
    plan["action_id"] = action_id
    plan["frozen_timestamp"] = frozen_timestamp
    plan["expires_timestamp"] = expires_timestamp
    plan["source_commit"] = source_commit
    plan["archive"]["s3_uri"] = _replace_action(plan["archive"]["s3_uri"], previous_action, action_id)
    plan["archive"]["sha256"] = sha256_file(archive)
    plan["archive"]["size_bytes"] = archive.stat().st_size
    for key in ("output_s3_uri", "plan_s3_uri"):
        plan["bootstrap"][key] = _replace_action(plan["bootstrap"][key], previous_action, action_id)
    plan["executor_sha256"] = sha256_file(root / "scripts/research/run_step7b_builds.py")
    plan["bootstrap"]["template_sha256"] = sha256_file(root / plan["bootstrap"]["template_path"])
    plan["runtime"]["sha256"] = sha256_file(root / plan["runtime"]["path"])
    for role in ROLES:
        for key in ("dockerfile", "lock"):
            plan["roles"][role][key]["sha256"] = sha256_file(root / plan["roles"][role][key]["path"])
    if production_surface:
        harness = {
            "record_kind": "cloud_production_e2e_harness",
            "schema_version": "0.1.0",
            "action_id": plan["action_id"],
            "input_lock_sha256": plan["input_lock_sha256"],
            "request": {
                "request_id": f"{plan['action_id']}-production-surface",
                "prompt": "bounded production-surface qualification",
                "max_tokens": 4,
                "temperature": 0.0,
            },
        }
        plan["production_surface"] = {
            "record_kind": harness["record_kind"],
            "schema_version": harness["schema_version"],
            "controller_privileged": True,
            "request": harness["request"],
            "harness_sha256": hashlib.sha256((canonical_bytes(harness) + b"\n")).hexdigest(),
        }
    plan.pop("plan_sha256", None)
    plan["plan_sha256"] = hashlib.sha256(canonical_bytes(plan)).hexdigest()
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predecessor", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--frozen-timestamp", required=True)
    parser.add_argument("--expires-timestamp", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--production-surface", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    predecessor = json.loads(args.predecessor.read_text(encoding="utf-8"))
    plan = prepare(
        predecessor,
        root=args.root.resolve(),
        archive=args.archive.resolve(),
        action_id=args.action_id,
        frozen_timestamp=args.frozen_timestamp,
        expires_timestamp=args.expires_timestamp,
        source_commit=args.source_commit,
        production_surface=args.production_surface,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(plan) + b"\n")
    print(json.dumps({"action_id": plan["action_id"], "plan_sha256": plan["plan_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

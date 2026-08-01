"""Select the exact minimum tau2 C120 qualification roster from sealed inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_TASKS = {"airline": 20, "telecom": 16, "banking": 13}


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _sha256(path: Path, *, normalize_lf: bool = False) -> str:
    payload = path.read_bytes()
    if normalize_lf:
        payload = payload.replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def _load_tasks(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise RuntimeError(f"{path}: expected an array of task objects")
    return value


def select(source_dir: Path, authority_path: Path) -> dict[str, Any]:
    airline_path = source_dir / "airline.json"
    banking_path = source_dir / "banking.json"
    telecom_path = source_dir / "telecom.json"
    split_path = source_dir / "telecom-split-tasks.json"

    airline = _load_tasks(airline_path)
    banking = _load_tasks(banking_path)
    telecom = _load_tasks(telecom_path)
    split = json.loads(split_path.read_text(encoding="utf-8"))
    telecom_base = split.get("base")
    if not isinstance(telecom_base, list) or len(telecom_base) != 114 or len(set(telecom_base)) != 114:
        raise RuntimeError("telecom split must contain exactly 114 distinct base task ids")

    pools = {
        "airline": airline,
        "telecom": [row for row in telecom if row.get("id") in set(telecom_base)],
        "banking": [row for row in banking if "DB" in row.get("evaluation_criteria", {}).get("reward_basis", [])],
    }
    expected_pool_sizes = {"airline": 50, "telecom": 114, "banking": 88}
    selected: list[dict[str, str]] = []
    pool_ids: dict[str, list[str]] = {}
    for domain, required in REQUIRED_TASKS.items():
        ids = sorted(str(row["id"]) for row in pools[domain])
        if len(ids) != expected_pool_sizes[domain] or len(set(ids)) != len(ids):
            raise RuntimeError(f"{domain}: expected {expected_pool_sizes[domain]} distinct eligible tasks, found {len(set(ids))}")
        pool_ids[domain] = ids
        selected.extend({"domain": domain, "task_id": task_id} for task_id in ids[:required])

    return {
        "record_kind": "step5b_tau2_c120_qualification_selection",
        "schema_version": "0.1.0",
        "authority_sha256": _sha256(authority_path, normalize_lf=True),
        "source_sha256": {
            "airline.json": _sha256(airline_path),
            "banking.json": _sha256(banking_path),
            "telecom.json": _sha256(telecom_path),
            "telecom-split-tasks.json": _sha256(split_path),
        },
        "eligible_pool_sizes": expected_pool_sizes,
        "eligible_task_ids": pool_ids,
        "required_tasks": REQUIRED_TASKS,
        "selection_rule": "lexicographically first task ids from each sealed admissible objective pool",
        "rows": selected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = select(args.source_dir, args.authority)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(result))
    print(json.dumps({"rows": len(result["rows"]), "sha256": _sha256(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

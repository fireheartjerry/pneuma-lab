#!/usr/bin/env python3
"""Offline verification for the SWE-Gym dataset-acquisition spike.

Confirms the local SWE-Gym sample + inventory exist under the out-of-repo data
root, prints sample counts and disk usage, and validates the inventory JSON.
Requires NO network access.

Usage:
    python scripts/verify_swe_gym_sample.py
    python scripts/verify_swe_gym_sample.py --data-root /c/pneuma-data

Exit code 0 if all checks pass, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

DEFAULT_ROOT = os.environ.get("PNEUMA_DATA_ROOT", "C:/pneuma-data")
MIN_TASK_SAMPLES = 5


def dir_size_bytes(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            fp = os.path.join(root, name)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def human(nbytes):
    value = float(nbytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def main():
    parser = argparse.ArgumentParser(description="Verify local SWE-Gym spike data.")
    parser.add_argument(
        "--data-root",
        default=DEFAULT_ROOT,
        help="Out-of-repo dataset root (default: %(default)s).",
    )
    args = parser.parse_args()
    root = args.data_root

    samples = os.path.join(root, "samples", "swe-gym")
    tasks_dir = os.path.join(samples, "tasks")
    traj_dir = os.path.join(samples, "trajectories")
    inventory = os.path.join(root, "manifests", "swe_gym_inventory.json")

    failures = []

    # 1. sample task files exist
    task_files = []
    if os.path.isdir(tasks_dir):
        task_files = [f for f in os.listdir(tasks_dir) if f.endswith(".json")]
    if len(task_files) < MIN_TASK_SAMPLES:
        failures.append(
            f"expected >= {MIN_TASK_SAMPLES} task samples in {tasks_dir}, "
            f"found {len(task_files)}"
        )

    # 2. at least one trajectory sample exists
    traj_files = []
    if os.path.isdir(traj_dir):
        traj_files = [f for f in os.listdir(traj_dir) if f.endswith(".json")]
    if len(traj_files) < 1:
        failures.append(f"expected >= 1 trajectory sample in {traj_dir}, found 0")

    # 3. inventory JSON exists and parses
    inv = None
    if not os.path.isfile(inventory):
        failures.append(f"inventory JSON missing: {inventory}")
    else:
        try:
            with open(inventory, "r", encoding="utf-8") as fh:
                inv = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"inventory JSON invalid: {exc}")

    # 4. disk usage
    raw_dir = os.path.join(root, "raw", "swe-gym")
    raw_bytes = dir_size_bytes(raw_dir) if os.path.isdir(raw_dir) else 0
    sample_bytes = dir_size_bytes(samples) if os.path.isdir(samples) else 0

    # ---- report ----
    print("SWE-Gym spike verification")
    print(f"  data root        : {root}")
    print(f"  task samples     : {len(task_files)} json under {tasks_dir}")
    print(f"  trajectory samples: {len(traj_files)} json under {traj_dir}")
    print(
        f"  inventory JSON   : {'OK' if inv is not None else 'MISSING/INVALID'}"
        f" ({inventory})"
    )
    if inv is not None:
        ds = inv.get("datasets", [])
        local = [d for d in ds if d.get("local_state") == "downloaded"]
        print(
            f"  inventory records: {len(ds)} datasets ({len(local)} downloaded locally)"
        )
    print(f"  raw disk usage   : {human(raw_bytes)} ({raw_dir})")
    print(f"  sample disk usage: {human(sample_bytes)}")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nPASS: local SWE-Gym sample + inventory present and valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

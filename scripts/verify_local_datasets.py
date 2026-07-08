#!/usr/bin/env python3
"""Offline summary of the local Pneuma SWE dataset suite.

Reads C:/pneuma-data/manifests/global_inventory.json (produced by the acquisition
pipeline) and prints a compact per-dataset status table. Requires NO network.

Usage:
    python scripts/verify_local_datasets.py
    python scripts/verify_local_datasets.py --data-root /c/pneuma-data

Exit 0 if the global inventory exists and parses; 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

DEFAULT_ROOT = os.environ.get("PNEUMA_DATA_ROOT", "C:/pneuma-data")


def human(nbytes):
    value = float(nbytes or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=DEFAULT_ROOT)
    args = ap.parse_args()
    gi = os.path.join(args.data_root, "manifests", "global_inventory.json")

    if not os.path.isfile(gi):
        print(f"MISSING global inventory: {gi}")
        print(
            "Run the acquisition pipeline first "
            "(C:/pneuma-data/logs/build_master_inventory.py)."
        )
        return 1
    try:
        with open(gi, "r", encoding="utf-8") as f:
            inv = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID global inventory: {exc}")
        return 1

    datasets = inv.get("datasets", [])
    print(f"Pneuma SWE dataset suite  (root: {args.data_root})")
    print(f"generated: {inv.get('generated_utc', '?')}")
    print("-" * 78)
    print(f"{'dataset':22s} {'status':12s} {'rows':>10s} {'files':>6s} {'size':>10s}")
    print("-" * 78)
    status_counts = {}
    for d in datasets:
        st = d.get("status", "?")
        status_counts[st] = status_counts.get(st, 0) + 1
        print(
            f"{d.get('dataset_name', '?'):22s} {st:12s} "
            f"{d.get('row_counts', {}).get('total_rows_loaded', 0):>10,} "
            f"{d.get('files', {}).get('total_count', 0):>6} "
            f"{human(d.get('files', {}).get('total_bytes', 0)):>10s}"
        )
    print("-" * 78)
    tot = inv.get("totals", {})
    print(
        f"{'TOTAL':22s} {'':12s} {tot.get('rows_verified', 0):>10,} "
        f"{tot.get('data_files', 0):>6} {human(tot.get('bytes', 0)):>10s}"
    )
    print("\nstatus:", ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items())))
    print(
        "samples/ present for:",
        ", ".join(
            d.get("dataset_name", "?")
            for d in datasets
            if d.get("sample_records", {}).get("sample_count", 0) > 0
        )
        or "(none)",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Emit the exact Step 5B metadata-only inventory discovery plan."""

from __future__ import annotations

import argparse
from pathlib import Path

from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.inventory_discovery import build_inventory_plan, inventory_plan_digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-timestamp", required=True)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = build_inventory_plan(frozen_timestamp=args.frozen_timestamp, region=args.region)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(plan) + b"\n")
    print(inventory_plan_digest(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

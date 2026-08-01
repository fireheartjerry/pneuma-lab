"""Derive the no-authority Step 5B payload manifest from sealed metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.payload_inventory import derive_payload_retrieval_manifest, payload_manifest_digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = derive_payload_retrieval_manifest(
        json.loads(args.plan.read_text(encoding="utf-8")), args.inventory.read_bytes()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(record) + b"\n")
    print(json.dumps({"sha256": payload_manifest_digest(record), "objects": record["unique_object_count"], "bytes": record["retrieval_byte_ceiling_bytes"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

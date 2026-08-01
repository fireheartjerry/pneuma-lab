from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.payload_pricing import build_payload_pricing_receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offer", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = build_payload_pricing_receipt(args.offer.read_bytes(), json.loads(args.manifest.read_text(encoding="utf-8")))
    raw = canonical_bytes(record) + b"\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(json.dumps({"sha256": hashlib.sha256(raw).hexdigest(), "projected_cost_usd": record["projected_cost_usd"], "within_ceiling": record["within_ceiling"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

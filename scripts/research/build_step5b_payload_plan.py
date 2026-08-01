"""Build the bounded, unsigned Step 5B payload action candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.payload_retrieval_plan import (
    build_payload_retrieval_plan,
    executor_sources_digest,
    payload_retrieval_plan_digest,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pricing-receipt-sha256")
    parser.add_argument("--lifecycle-terraform-plan-sha256", required=True)
    parser.add_argument("--lifecycle-live-receipt-sha256")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    plan = build_payload_retrieval_plan(
        manifest, executor_sources_sha256=executor_sources_digest(args.repo_root),
        lifecycle_terraform_plan_sha256=args.lifecycle_terraform_plan_sha256,
        pricing_receipt_sha256=args.pricing_receipt_sha256,
        lifecycle_live_receipt_sha256=args.lifecycle_live_receipt_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(plan) + b"\n")
    print(json.dumps({"sha256": payload_retrieval_plan_digest(plan), "status": plan["status"], "cost_ceiling_usd": plan["cost_ceiling_usd"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

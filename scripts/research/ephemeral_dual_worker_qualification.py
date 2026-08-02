"""Validate an ephemeral dual-worker qualification request locally.

The command is intentionally a package validator, not an AWS launcher.  A
separate authorized runner may consume its JSON output to submit exactly two
fixture-only jobs and must always execute destroy plus post-teardown checks.
"""

from __future__ import annotations

import argparse
import json
import sys

from pneuma_lab.cloud.ephemeral_qualification import (
    MAX_WORKER_RUNTIME_MINUTES,
    MAX_RETRIES,
    SPOT_ALLOCATION_STRATEGY,
    TOTAL_COST_CEILING_USD,
    TOTAL_SPOT_VCPUS,
    WORKER_COUNT,
    WORKER_GPU_COUNT,
    WORKER_INSTANCE_TYPE,
    WORKER_VCPUS,
    validate_plan,
)


def qualification_plan() -> dict[str, object]:
    return {
        "worker_count": WORKER_COUNT,
        "instance_type": WORKER_INSTANCE_TYPE,
        "worker_vcpus": WORKER_VCPUS,
        "worker_gpu_count": WORKER_GPU_COUNT,
        "total_spot_vcpus": TOTAL_SPOT_VCPUS,
        "max_runtime_minutes": MAX_WORKER_RUNTIME_MINUTES,
        "max_retries": MAX_RETRIES,
        "spot_allocation_strategy": SPOT_ALLOCATION_STRATEGY,
        "total_cost_ceiling_usd": TOTAL_COST_CEILING_USD,
        "qualification_only": True,
        "jobs": 2,
        "teardown": "terraform destroy then provider absence verification",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    plan = qualification_plan()
    validate_plan(plan)
    print(
        json.dumps(plan, sort_keys=True) if args.json else "qualification package valid"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

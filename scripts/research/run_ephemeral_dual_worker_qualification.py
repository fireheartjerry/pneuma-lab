"""Concrete future AWS qualification runner; inert unless ``--execute`` is set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from pneuma_lab.cloud.ephemeral_runner import (
    AwsCliAdapter,
    RunnerConfig,
    TerraformAdapter,
    execute,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--action-id")
    parser.add_argument("--envelope", type=Path)
    parser.add_argument("--admission", type=Path)
    parser.add_argument("--key-registry", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--queue")
    parser.add_argument("--job-definition")
    parser.add_argument("--compute-environment")
    parser.add_argument("--output-root")
    args = parser.parse_args()
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "inert",
                    "message": "pass --execute only under a separately authorized action",
                }
            )
        )
        return 0
    required = (
        args.plan,
        args.action_id,
        args.envelope,
        args.admission,
        args.key_registry,
        args.ledger,
        args.queue,
        args.job_definition,
        args.compute_environment,
        args.output_root,
    )
    if any(value is None for value in required):
        parser.error(
            "--execute requires the signed package, exact saved plan, queue, definition, and output root"
        )
    terraform = TerraformAdapter(subprocess.run)
    account_plan = terraform.load_account_plan(args.plan)
    provider = AwsCliAdapter(
        subprocess.run,
        region=args.region,
        queue=args.queue,
        job_definition=args.job_definition,
        compute_environment=args.compute_environment,
        output_root=args.output_root,
    )
    envelope = json.loads(args.envelope.read_text(encoding="utf-8"))
    admission = json.loads(args.admission.read_text(encoding="utf-8"))
    registry = json.loads(args.key_registry.read_text(encoding="utf-8"))
    result = execute(
        RunnerConfig(args.action_id, args.region),
        envelope=envelope,
        admission=admission,
        key_registry=registry,
        ledger_path=args.ledger,
        account_plan=account_plan,
        provider=provider,
        terraform=terraform,
    )
    print(
        json.dumps(
            {"status": "passed", "qualification_only": result["qualification_only"]},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

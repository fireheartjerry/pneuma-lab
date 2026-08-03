"""Concrete future AWS qualification runner; inert unless ``--execute`` is set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from pneuma_lab.cloud.ephemeral_runner import (
    AwsCliAdapter,
    RunnerConfig,
    TerraformAdapter,
    execute,
)
from pneuma_lab.cloud.qualification_execution import worker_artifact_uri


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sanitized_receipt(
    result: dict, *, account_plan: dict, action_id: str, region: str, output_root: str
) -> dict:
    evidence = result.get("evidence") or {}
    children = evidence.get("children") or ()
    child_rows = []
    for child in children:
        child_rows.append(
            {
                "job_id_sha256": _digest_text(str(child.get("jobId", ""))),
                "array_index": (child.get("arrayProperties") or {}).get("index"),
                "status": child.get("status"),
                "attempt_count": len(child.get("attempts") or []),
            }
        )
    raw_rows = []
    raw_evidence = evidence.get("raw_evidence") or {}
    for index in (0, 1):
        payload = raw_evidence.get(index)
        if not isinstance(payload, (bytes, bytearray)) or not payload:
            continue
        raw_rows.append(
            {
                "worker_index": index,
                "uri": worker_artifact_uri(output_root, index),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    return {
        "record_kind": "cloud_ephemeral_dual_worker_qualification_receipt",
        "schema_version": "0.1.0",
        "status": "passed",
        "qualification_only": True,
        "action_id": action_id,
        "provider": "aws",
        "region": region,
        "plan": {
            "saved_plan_sha256": account_plan.get("saved_plan_sha256"),
            "terraform_show_sha256": account_plan.get("terraform_show_sha256"),
            "terraform_plan_binding_sha256": account_plan.get(
                "terraform_plan_binding_sha256"
            ),
        },
        "projected_cost_usd": result.get("projected_cost_usd"),
        "ready": result.get("ready"),
        "parent_job_id_sha256": _digest_text(str(result.get("parent_job_id", ""))),
        "children": child_rows,
        "worker_identity_sha256": [
            _digest_text(str(value)) for value in evidence.get("instance_ids", ())
        ],
        "raw_artifacts": raw_rows,
        "recovery": result.get("recovery"),
        "teardown_absence": result.get("absence"),
    }


def _write_receipt(path: Path | None, receipt: dict) -> None:
    if path is not None:
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    parser.add_argument("--receipt", type=Path)
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
    try:
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
    except Exception as exc:
        receipt = {
            "record_kind": "cloud_ephemeral_dual_worker_qualification_receipt",
            "schema_version": "0.1.0",
            "status": "no_go",
            "qualification_only": True,
            "action_id": args.action_id,
            "provider": "aws",
            "region": args.region,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        _write_receipt(args.receipt, receipt)
        print(json.dumps(receipt, sort_keys=True))
        return 1
    receipt = _sanitized_receipt(
        result,
        account_plan=account_plan,
        action_id=args.action_id,
        region=args.region,
        output_root=args.output_root,
    )
    _write_receipt(args.receipt, receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Concrete AWS qualification runner; inert unless ``--execute`` is set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

from pneuma_lab.cloud.ephemeral_receipt import (
    build_ephemeral_qualification_receipt,
    validate_authority_evidence,
)
from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.images import require_qualification_image_binding
from pneuma_lab.cloud.ephemeral_runner import (
    AwsCliAdapter,
    QualificationExecutionError,
    RunnerConfig,
    TerraformAdapter,
    execute,
    require_account_plan,
    require_fresh_qualification_action,
)


def _json_file(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _qualification_image_digest(plan: Mapping[str, Any]) -> str:
    """Extract the immutable digest from the raw Terraform image binding."""

    image = plan.get("image")
    if not isinstance(image, str) or "@sha256:" not in image:
        raise ValueError("loaded Terraform plan lacks an immutable qualification image")
    return image.rsplit("@", 1)[1]


def _prelaunch_output(action_id: str, exc: Exception) -> dict[str, str]:
    return {
        "record_kind": "cloud_ephemeral_dual_worker_qualification_preflight_no_go",
        "status": "pre_launch_no_go",
        "qualification_only": "true",
        "action_id": action_id,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "receipt_written": "false",
    }


def _postlaunch_receipt_failure(
    action_id: str, context: Mapping[str, Any], receipt_exc: Exception
) -> dict[str, Any]:
    """Retain a sanitized post-submit context if receipt assembly itself fails."""

    plan = context.get("plan") if isinstance(context.get("plan"), Mapping) else {}
    launch = context.get("launch") if isinstance(context.get("launch"), Mapping) else {}
    evidence = (
        context.get("evidence") if isinstance(context.get("evidence"), Mapping) else {}
    )
    absence = (
        context.get("absence") if isinstance(context.get("absence"), Mapping) else {}
    )
    iam = (
        context.get("iam_simulation")
        if isinstance(context.get("iam_simulation"), Mapping)
        else {}
    )
    inventory = iam.get("policy_inventory")
    sanitized = {
        "action_id": action_id,
        "parent_job_id_present": bool(context.get("parent_job_id")),
        "plan": {
            key: plan.get(key)
            for key in (
                "saved_plan_sha256",
                "terraform_show_sha256",
                "terraform_plan_binding_sha256",
                "image",
            )
            if plan.get(key) is not None
        },
        "launch": {
            key: launch.get(key)
            for key in (
                "submit_count_proven",
                "array_size",
                "retry_attempts",
                "submit_event_time_utc",
                "cloudtrail_submit_job_event_id_sha256",
            )
            if launch.get(key) is not None
        },
        "evidence": {
            "parent_status": evidence.get("parent_status"),
            "child_statuses": [
                child.get("status")
                for child in evidence.get("children", ())
                if isinstance(child, Mapping)
            ],
            "worker_count": len(evidence.get("instance_ids", ()))
            if isinstance(evidence.get("instance_ids", ()), (list, tuple))
            else 0,
        },
        "absence": {
            key: absence.get(key)
            for key in (
                "jobs",
                "instances",
                "volumes",
                "launch_template",
                "network_interfaces",
                "security_group",
                "job_definition",
                "queue",
                "compute_environment",
            )
            if key in absence
        },
        "iam_simulation_matrix_sha256": iam.get("matrix_sha256"),
        "iam_policy_inventory_sha256": (
            inventory.get("inventory_sha256")
            if isinstance(inventory, Mapping)
            else None
        ),
        "kms_verification_sha256": (
            context.get("kms_verification", {}).get("verification_sha256")
            if isinstance(context.get("kms_verification"), Mapping)
            else None
        ),
        "failure": {
            "type": type(context.get("failure")).__name__,
            "error": str(context.get("failure")),
        }
        if context.get("failure") is not None
        else None,
        "cleanup_failure": {
            "type": type(context.get("cleanup_failure")).__name__,
            "error": str(context.get("cleanup_failure")),
        }
        if context.get("cleanup_failure") is not None
        else None,
    }
    return {
        "record_kind": "cloud_ephemeral_dual_worker_qualification_receipt_failure",
        "schema_version": "0.1.0",
        "status": "post_launch_receipt_no_go",
        "qualification_only": True,
        "action_id": action_id,
        "terminal_outcome": "post_launch_terminal_no_go",
        "no_retry_after_launch": True,
        "receipt_build_error_type": type(receipt_exc).__name__,
        "receipt_build_error": str(receipt_exc),
        "context_sha256": hashlib.sha256(canonical_bytes(sanitized)).hexdigest(),
        "context_summary": sanitized,
        "receipt_written": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--tfvars", type=Path)
    parser.add_argument("--action-id")
    parser.add_argument("--envelope", type=Path)
    parser.add_argument("--admission", type=Path)
    parser.add_argument("--key-registry", type=Path)
    parser.add_argument("--signed-package", type=Path)
    parser.add_argument("--authority-receipt", type=Path)
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
        args.tfvars,
        args.action_id,
        args.envelope,
        args.admission,
        args.key_registry,
        args.signed_package,
        args.authority_receipt,
        args.ledger,
        args.queue,
        args.job_definition,
        args.compute_environment,
        args.output_root,
    )
    if any(value is None for value in required):
        parser.error(
            "--execute requires the exact plan, signed authority package and receipt evidence, queue, definition, and output root"
        )

    authority: dict[str, Any] | None = None
    evidence_root = (
        Path(__file__).resolve().parents[2]
        / "docs/research/neurips-2026-workshop/evidence"
    )
    try:
        require_fresh_qualification_action(
            args.action_id,
            evidence_root=evidence_root,
            receipt_path=args.receipt,
            ledger_path=args.ledger,
        )
        terraform = TerraformAdapter(subprocess.run, variable_file=args.tfvars)
        terraform.initialize()
        account_plan = terraform.load_account_plan(args.plan)
        envelope = _json_file(args.envelope)
        admission = _json_file(args.admission)
        registry = _json_file(args.key_registry)
        authority_record = _json_file(args.authority_receipt)
        package_bytes = args.signed_package.read_bytes()
        plan_for_binding = account_plan.get("_qualification")
        if not isinstance(plan_for_binding, Mapping):
            raise ValueError("loaded Terraform plan lacks its parsed qualification binding")
        provider = AwsCliAdapter(
            subprocess.run,
            region=args.region,
            queue=args.queue,
            job_definition=args.job_definition,
            compute_environment=args.compute_environment,
            output_root=args.output_root,
        )
        parsed_plan = require_account_plan(
            account_plan,
            action_id=args.action_id,
            provider=provider,
            ledger_path=args.ledger,
        )
        source_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        require_qualification_image_binding(
            evidence_root,
            image_digest=_qualification_image_digest(parsed_plan),
            source_commit=source_revision,
        )
        authority = validate_authority_evidence(
            authority_record,
            package_bytes=package_bytes,
            envelope=envelope,
            admission=admission,
            action_id=args.action_id,
            region=args.region,
            plan=parsed_plan,
            projected_cost_usd=float(authority_record["projected_cost_usd"]),
        )
        result = execute(
            RunnerConfig(
                args.action_id,
                args.region,
                require_receipt_evidence=True,
                action_evidence_root=evidence_root,
                receipt_path=args.receipt,
            ),
            envelope=envelope,
            admission=admission,
            key_registry=registry,
            ledger_path=args.ledger,
            account_plan=account_plan,
            provider=provider,
            terraform=terraform,
            authority_evidence=authority,
        )
        receipt = build_ephemeral_qualification_receipt(
            result,
            action_id=args.action_id,
            region=args.region,
            authority=authority,
            output_root=args.output_root,
        )
        if args.receipt is not None:
            args.receipt.write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except QualificationExecutionError as exc:
        context = exc.context
        if not context.get("parent_job_id"):
            print(json.dumps(_prelaunch_output(args.action_id, exc), sort_keys=True))
            return 1
        if authority is None:
            print(json.dumps(_prelaunch_output(args.action_id, exc), sort_keys=True))
            return 1
        try:
            receipt = build_ephemeral_qualification_receipt(
                context,
                action_id=args.action_id,
                region=args.region,
                authority=authority,
                output_root=args.output_root,
            )
        except Exception as receipt_exc:
            fallback = _postlaunch_receipt_failure(
                args.action_id, context, receipt_exc
            )
            if args.receipt is not None:
                args.receipt.write_text(
                    json.dumps(fallback, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            print(json.dumps(fallback, sort_keys=True))
            return 1
        if args.receipt is not None:
            args.receipt.write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(receipt, sort_keys=True))
        return 1
    except Exception as exc:
        print(json.dumps(_prelaunch_output(args.action_id, exc), sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

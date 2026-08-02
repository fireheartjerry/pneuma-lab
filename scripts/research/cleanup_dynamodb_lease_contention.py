"""Run one signed, zero-retry cleanup of a failed lease qualification item."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from pneuma_lab.cloud.authorization_keys import canonical_bytes, canonical_ledger_digest
from pneuma_lab.cloud.lease_contention import require_lease_contention_cleanup
from pneuma_lab.cloud.preparation_admission import require_preparation_admission


class CleanupError(RuntimeError):
    """A fail-closed cleanup preflight error."""


def plan_digest(plan: dict[str, Any]) -> str:
    body = dict(plan)
    body.pop("plan_sha256", None)
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def _run_aws(plan: dict[str, Any], command: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    env["AWS_PROFILE"] = plan["execution_profile"]
    env["AWS_MAX_ATTEMPTS"] = "1"
    env["AWS_RETRY_MODE"] = "standard"
    env["AWS_PAGER"] = ""
    env["AWS_CLI_AUTO_PROMPT"] = "off"
    try:
        completed = subprocess.run(
            ["aws", *command, "--region", plan["region"], "--output", "json", "--no-cli-pager"],
            env=env, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=int(plan["cli_timeout_seconds"]),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        return {
            "return_code": 124,
            "stdout": stdout if isinstance(stdout, bytes) else str(stdout).encode(),
            "stderr": stderr if isinstance(stderr, bytes) else str(stderr).encode(),
        }
    return {"return_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _json(result: dict[str, Any]) -> dict[str, Any]:
    if result["return_code"] != 0:
        raise CleanupError("AWS read or cleanup returned a non-zero status")
    if not result["stdout"].strip():
        return {}
    try:
        return json.loads(result["stdout"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CleanupError("AWS returned non-JSON output") from exc


def _key(plan: dict[str, Any]) -> str:
    return json.dumps({"lease_key": {"S": plan["lease_key"]}}, sort_keys=True, separators=(",", ":"))


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _base_receipt(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_kind": "cloud_lease_contention_cleanup_receipt",
        "schema_version": "0.1.0",
        "plan_sha256": plan["plan_sha256"],
        "input_lock_sha256": plan.get("input_lock_sha256"),
        "provider": plan["provider"],
        "region": plan["region"],
        "account_id": plan["account_id"],
        "cleanup_id": plan["action_id"],
        "target_action_id": plan["target_action_id"],
        "table_name": plan["table_name"],
        "table_arn": plan["table_arn"],
        "lease_key": plan["lease_key"],
        "expected_owner": plan["expected_owner"],
        "identity_arn": "",
        "preflight": {"table_active": False, "table_arn_exact": False, "item_present": False, "owner_exact": False, "action_id_exact": False},
        "deletion": {"attempted": False, "succeeded": False, "return_code": 1, "stdout_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        "final": {"item_absent": False, "table_count": 0},
        "gates": {"identity_bound": False, "exact_item_bound": False, "delete_succeeded": False, "final_absent": False, "no_retries": True, "no_scientific_action": True},
        "residual_resource_ids": [],
        "no_scientific_action": True,
        "verdict": "failed",
        "failure_reason": None,
    }


def execute(plan: dict[str, Any], package: dict[str, Any], registry: dict[str, Any], ledger: Path) -> dict[str, Any]:
    if plan_digest(plan) != plan["plan_sha256"]:
        raise CleanupError("plan_sha256 does not bind canonical plan bytes")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != plan["executor_sha256"]:
        raise CleanupError("cleanup executor bytes do not match the signed plan")
    if package.get("record_kind") != "cloud_preparation_signing_package" or package.get("plan_sha256") != plan["plan_sha256"]:
        raise CleanupError("cleanup signing package is not bound to this plan")
    source_check = subprocess.run(["git", "merge-base", "--is-ancestor", plan["source_commit"], "HEAD"], check=False)
    if source_check.returncode != 0:
        raise CleanupError("checkout HEAD does not descend from the signed source commit")
    require_preparation_admission(
        package["envelope"], package["admission"], key_registry=registry, ledger_path=ledger,
        expected_action_id=plan["action_id"], expected_action_class=plan["action_class"], expected_provider=plan["provider"],
        expected_region=plan["region"], expected_manifest_sha256=plan["plan_sha256"], expected_input_lock_sha256=plan.get("input_lock_sha256"),
        expected_projected_cost_usd=plan["projected_cost_usd"], expected_max_retries=plan["max_retries"],
        spend_history_sha256=canonical_ledger_digest(ledger),
    )
    receipt = _base_receipt(plan)
    try:
        identity = _json(_run_aws(plan, ["sts", "get-caller-identity"]))
        if identity.get("Account") != plan["account_id"]:
            raise CleanupError("AWS caller account does not match the signed plan")
        receipt["identity_arn"] = identity.get("Arn", "")
        table = _json(_run_aws(plan, ["dynamodb", "describe-table", "--table-name", plan["table_name"]])).get("Table", {})
        receipt["preflight"]["table_active"] = table.get("TableStatus") == "ACTIVE"
        receipt["preflight"]["table_arn_exact"] = table.get("TableArn") == plan["table_arn"]
        if not (receipt["preflight"]["table_active"] and receipt["preflight"]["table_arn_exact"]):
            raise CleanupError("DynamoDB table identity/status is not the signed target")
        item = _json(_run_aws(plan, ["dynamodb", "get-item", "--table-name", plan["table_name"], "--key", _key(plan), "--consistent-read"])).get("Item")
        receipt["preflight"]["item_present"] = item is not None
        receipt["preflight"]["owner_exact"] = item is not None and item.get("owner", {}).get("S") == plan["expected_owner"]
        receipt["preflight"]["action_id_exact"] = item is not None and item.get("action_id", {}).get("S") == plan["target_action_id"]
        if not (receipt["preflight"]["item_present"] and receipt["preflight"]["owner_exact"] and receipt["preflight"]["action_id_exact"]):
            raise CleanupError("signed cleanup target item does not match the failed action")
        result = _run_aws(plan, [
            "dynamodb", "delete-item", "--table-name", plan["table_name"], "--key", _key(plan),
            "--condition-expression", "#owner = :owner", "--expression-attribute-names", json.dumps({"#owner": "owner"}),
            "--expression-attribute-values", json.dumps({":owner": {"S": plan["expected_owner"]}}, sort_keys=True),
            "--return-consumed-capacity", "TOTAL",
        ])
        receipt["deletion"] = {
            "attempted": True,
            "succeeded": result["return_code"] == 0,
            "return_code": result["return_code"],
            "stdout_sha256": _digest(result["stdout"]),
            "stderr_sha256": _digest(result["stderr"]),
        }
        final = _json(_run_aws(plan, ["dynamodb", "get-item", "--table-name", plan["table_name"], "--key", _key(plan), "--consistent-read"]))
        receipt["final"]["item_absent"] = final.get("Item") is None
        count = _json(_run_aws(plan, ["dynamodb", "scan", "--table-name", plan["table_name"], "--select", "COUNT"]))
        receipt["final"]["table_count"] = int(count.get("Count", 0))
        receipt["gates"] = {
            "identity_bound": True,
            "exact_item_bound": all(receipt["preflight"].values()),
            "delete_succeeded": receipt["deletion"]["succeeded"],
            "final_absent": receipt["final"]["item_absent"],
            "no_retries": True,
            "no_scientific_action": True,
        }
        receipt["verdict"] = "passed" if all(receipt["gates"].values()) else "failed"
        if receipt["verdict"] == "passed":
            require_lease_contention_cleanup(receipt)
        else:
            receipt["failure_reason"] = "one or more signed cleanup gates failed"
    except (CleanupError, subprocess.CalledProcessError, KeyError, ValueError) as exc:
        receipt["failure_reason"] = str(exc)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--key-registry", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    package = json.loads(args.package.read_text(encoding="utf-8"))
    registry = json.loads(args.key_registry.read_text(encoding="utf-8"))
    receipt = execute(plan, package, registry, args.ledger)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(receipt) + b"\n")
    print(json.dumps({"verdict": receipt["verdict"], "plan_sha256": receipt["plan_sha256"], "receipt_sha256": hashlib.sha256(canonical_bytes(receipt) + b"\n").hexdigest()}))
    return 0 if receipt["verdict"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

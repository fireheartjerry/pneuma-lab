"""Run one signed, zero-retry DynamoDB conditional-write qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from pneuma_lab.cloud.authorization_keys import canonical_bytes, canonical_ledger_digest
from pneuma_lab.cloud.lease_contention import require_lease_contention_qualification
from pneuma_lab.cloud.preparation_admission import require_preparation_admission


class QualificationError(RuntimeError):
    """A fail-closed preflight or readback error."""


def plan_digest(plan: dict[str, Any]) -> str:
    body = dict(plan)
    body.pop("plan_sha256", None)
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _run_aws(plan: dict[str, Any], command: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    env["AWS_PROFILE"] = plan["execution_profile"]
    env["AWS_MAX_ATTEMPTS"] = "1"
    env["AWS_RETRY_MODE"] = "standard"
    env["AWS_PAGER"] = ""
    env["AWS_CLI_AUTO_PROMPT"] = "off"
    argv = ["aws", *command, "--region", plan["region"], "--output", "json", "--no-cli-pager"]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv, env=env, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=int(plan["cli_timeout_seconds"]),
        )
        stdout = completed.stdout
        stderr = completed.stderr
        return {
            "return_code": completed.returncode,
            "stdout_sha256": _digest_bytes(stdout),
            "stderr_sha256": _digest_bytes(stderr),
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        return {
            "return_code": 124,
            "stdout_sha256": _digest_bytes(stdout if isinstance(stdout, bytes) else str(stdout).encode()),
            "stderr_sha256": _digest_bytes(stderr if isinstance(stderr, bytes) else str(stderr).encode()),
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "timeout": True,
        }


def _json(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("return_code") != 0:
        raise QualificationError("AWS read or mutation returned a non-zero status")
    if not result["stdout"].strip():
        return {}
    try:
        return json.loads(result["stdout"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationError("AWS returned non-JSON output") from exc


def _key(plan: dict[str, Any]) -> str:
    return json.dumps({"lease_key": {"S": plan["lease_key"]}}, sort_keys=True, separators=(",", ":"))


def _contender(plan: dict[str, Any], attempt: int) -> dict[str, Any]:
    owner = f"{plan['action_id']}-worker-{attempt:02d}"
    item = {
        "lease_key": {"S": plan["lease_key"]},
        "owner": {"S": owner},
        "action_id": {"S": plan["action_id"]},
        "attempt": {"N": str(attempt)},
        "expires_at": {"N": str(plan["lease_expires_epoch"])},
    }
    result = _run_aws(plan, [
        "dynamodb", "put-item", "--table-name", plan["table_name"], "--item", json.dumps(item, sort_keys=True),
        "--condition-expression", plan["condition_expression"], "--return-consumed-capacity", "TOTAL",
    ])
    stderr = result["stderr"] if isinstance(result["stderr"], bytes) else str(result["stderr"]).encode()
    if result.get("timeout"):
        outcome = "timeout"
    elif result["return_code"] == 0:
        outcome = "success"
    elif b"ConditionalCheckFailedException" in stderr:
        outcome = "conditional_failed"
    else:
        outcome = "provider_error"
    return {
        "attempt": attempt,
        "owner": owner,
        "outcome": outcome,
        "return_code": result["return_code"],
        "stdout_sha256": result["stdout_sha256"],
        "stderr_sha256": result["stderr_sha256"],
        "duration_ms": result["duration_ms"],
    }


def _base_receipt(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_kind": "cloud_lease_contention_qualification_receipt",
        "schema_version": "0.1.0",
        "plan_sha256": plan["plan_sha256"],
        "input_lock_sha256": plan.get("input_lock_sha256"),
        "provider": plan["provider"],
        "region": plan["region"],
        "account_id": plan["account_id"],
        "qualification_id": plan["action_id"],
        "table_name": plan["table_name"],
        "table_arn": plan["table_arn"],
        "lease_key": plan["lease_key"],
        "identity_arn": "",
        "attempt_count": plan["attempt_count"],
        "max_concurrency": plan["max_concurrency"],
        "condition_expression": plan["condition_expression"],
        "preflight": {"table_active": False, "table_arn_exact": False, "item_absent": False, "table_count": 0},
        "contenders": [],
        "winner": None,
        "cleanup": {"delete_attempted": False, "delete_succeeded": False, "final_item_absent": False, "final_table_count": 0},
        "gates": {
            "table_identity_bound": False,
            "exactly_one_winner": False,
            "all_losers_conditional": False,
            "no_provider_errors": False,
            "winner_readback_exact": False,
            "no_retries": True,
            "exact_teardown": False,
            "no_scientific_action": True,
        },
        "residual_resource_ids": [],
        "no_scientific_action": True,
        "verdict": "failed",
        "failure_reason": None,
    }


def execute(plan: dict[str, Any], package: dict[str, Any], key_registry: dict[str, Any], ledger_path: Path) -> dict[str, Any]:
    if plan_digest(plan) != plan["plan_sha256"]:
        raise QualificationError("plan_sha256 does not bind canonical plan bytes")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != plan["executor_sha256"]:
        raise QualificationError("executor bytes do not match the signed plan")
    if package.get("record_kind") != "cloud_preparation_signing_package" or package.get("plan_sha256") != plan["plan_sha256"]:
        raise QualificationError("signing package is not bound to this plan")
    source_check = subprocess.run(
        ["git", "merge-base", "--is-ancestor", plan["source_commit"], "HEAD"],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if source_check.returncode != 0:
        raise QualificationError("checkout HEAD does not descend from the signed source commit")
    require_preparation_admission(
        package["envelope"], package["admission"], key_registry=key_registry, ledger_path=ledger_path,
        expected_action_id=plan["action_id"], expected_action_class=plan["action_class"],
        expected_provider=plan["provider"], expected_region=plan["region"], expected_manifest_sha256=plan["plan_sha256"],
        expected_input_lock_sha256=plan.get("input_lock_sha256"), expected_projected_cost_usd=plan["projected_cost_usd"],
        expected_max_retries=plan["max_retries"], spend_history_sha256=canonical_ledger_digest(ledger_path),
    )
    receipt = _base_receipt(plan)
    try:
        identity_result = _run_aws(plan, ["sts", "get-caller-identity"])
        identity = _json(identity_result)
        if identity.get("Account") != plan["account_id"]:
            raise QualificationError("AWS caller account does not match the signed plan")
        receipt["identity_arn"] = identity.get("Arn", "")
        table_result = _run_aws(plan, ["dynamodb", "describe-table", "--table-name", plan["table_name"]])
        table = _json(table_result).get("Table", {})
        table_active = table.get("TableStatus") == "ACTIVE"
        table_exact = table.get("TableArn") == plan["table_arn"]
        receipt["preflight"]["table_active"] = table_active
        receipt["preflight"]["table_arn_exact"] = table_exact
        if not (table_active and table_exact):
            raise QualificationError("DynamoDB table identity/status is not the signed target")
        initial_get = _run_aws(plan, ["dynamodb", "get-item", "--table-name", plan["table_name"], "--key", _key(plan), "--consistent-read"])
        initial_item = _json(initial_get).get("Item")
        receipt["preflight"]["item_absent"] = initial_item is None
        initial_scan = _json(_run_aws(plan, ["dynamodb", "scan", "--table-name", plan["table_name"], "--select", "COUNT"]))
        receipt["preflight"]["table_count"] = int(initial_scan.get("Count", 0))
        if initial_item is not None:
            raise QualificationError("signed lease key already exists; refusing to overwrite it")
        with ThreadPoolExecutor(max_workers=plan["max_concurrency"]) as pool:
            futures = [pool.submit(_contender, plan, attempt) for attempt in range(plan["attempt_count"])]
            receipt["contenders"] = [future.result() for future in futures]
        winners = [row for row in receipt["contenders"] if row["outcome"] == "success"]
        losers = [row for row in receipt["contenders"] if row["outcome"] == "conditional_failed"]
        readback_result = _run_aws(plan, ["dynamodb", "get-item", "--table-name", plan["table_name"], "--key", _key(plan), "--consistent-read"])
        readback = _json(readback_result).get("Item")
        if readback is not None:
            observed_owner = readback.get("owner", {}).get("S")
            observed_attempt = int(readback.get("attempt", {}).get("N", "-1"))
            receipt["winner"] = {
                "attempt": observed_attempt,
                "owner": observed_owner or "",
                "item_sha256": hashlib.sha256(canonical_bytes(readback)).hexdigest(),
                "action_id_exact": readback.get("action_id", {}).get("S") == plan["action_id"],
            }
        expected_owner = winners[0]["owner"] if len(winners) == 1 else None
        if readback is not None and observed_owner:
            if observed_owner in {row["owner"] for row in receipt["contenders"]}:
                receipt["cleanup"]["delete_attempted"] = True
                delete_result = _run_aws(plan, [
                    "dynamodb", "delete-item", "--table-name", plan["table_name"], "--key", _key(plan),
                    "--condition-expression", "owner = :owner", "--expression-attribute-values",
                    json.dumps({":owner": {"S": observed_owner}}, sort_keys=True), "--return-values", "ALL_OLD",
                ])
                receipt["cleanup"]["delete_succeeded"] = delete_result["return_code"] == 0
        final_get = _run_aws(plan, ["dynamodb", "get-item", "--table-name", plan["table_name"], "--key", _key(plan), "--consistent-read"])
        receipt["cleanup"]["final_item_absent"] = _json(final_get).get("Item") is None
        final_scan = _json(_run_aws(plan, ["dynamodb", "scan", "--table-name", plan["table_name"], "--select", "COUNT"]))
        receipt["cleanup"]["final_table_count"] = int(final_scan.get("Count", 0))
        gates = receipt["gates"]
        gates["table_identity_bound"] = table_active and table_exact and receipt["preflight"]["item_absent"]
        gates["exactly_one_winner"] = len(winners) == 1
        gates["all_losers_conditional"] = len(losers) == plan["attempt_count"] - 1
        gates["no_provider_errors"] = len(winners) + len(losers) == plan["attempt_count"]
        gates["winner_readback_exact"] = (
            receipt["winner"] is not None and expected_owner == receipt["winner"]["owner"]
            and receipt["winner"]["attempt"] == winners[0]["attempt"] if len(winners) == 1 else False
        )
        gates["exact_teardown"] = receipt["cleanup"]["delete_succeeded"] and receipt["cleanup"]["final_item_absent"]
        receipt["verdict"] = "passed" if all(gates.values()) else "failed"
        if receipt["verdict"] != "passed":
            receipt["failure_reason"] = "one or more signed qualification gates failed"
        else:
            require_lease_contention_qualification(receipt)
    except (QualificationError, subprocess.CalledProcessError, KeyError, ValueError) as exc:
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

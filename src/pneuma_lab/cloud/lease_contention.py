"""Fail-closed validation for a real DynamoDB lease-contention receipt."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import CloudManifestError
from .manifests import validate_lease_contention_cleanup_receipt, validate_lease_contention_qualification_receipt


def require_lease_contention_qualification(record: Mapping[str, Any]) -> dict[str, Any]:
    """Require one conditional-write winner, exact readback, and teardown."""

    receipt = validate_lease_contention_qualification_receipt(record)
    contenders = receipt["contenders"]
    expected_attempts = set(range(receipt["attempt_count"]))
    observed_attempts = {item["attempt"] for item in contenders}
    if len(contenders) != receipt["attempt_count"] or observed_attempts != expected_attempts:
        raise CloudManifestError("contention receipt does not contain exactly one record per attempt")
    if len({item["owner"] for item in contenders}) != len(contenders):
        raise CloudManifestError("contention receipt repeats an owner")
    winners = [item for item in contenders if item["outcome"] == "success"]
    losers = [item for item in contenders if item["outcome"] == "conditional_failed"]
    if len(winners) != 1:
        raise CloudManifestError("DynamoDB conditional contention did not produce exactly one winner")
    if len(losers) != receipt["attempt_count"] - 1:
        raise CloudManifestError("every losing contender must fail with ConditionalCheckFailedException")
    if any(item["outcome"] not in {"success", "conditional_failed"} for item in contenders):
        raise CloudManifestError("contention receipt contains a provider error or timeout")
    winner = receipt["winner"]
    if winner is None or winner["attempt"] != winners[0]["attempt"] or winner["owner"] != winners[0]["owner"]:
        raise CloudManifestError("winner readback is not bound to the sole successful contender")
    if not winner["action_id_exact"]:
        raise CloudManifestError("winner item is not bound to the action id")
    preflight = receipt["preflight"]
    cleanup = receipt["cleanup"]
    if not (preflight["table_active"] and preflight["table_arn_exact"] and preflight["item_absent"]):
        raise CloudManifestError("contention preflight was not clean")
    if not (cleanup["delete_attempted"] and cleanup["delete_succeeded"] and cleanup["final_item_absent"]):
        raise CloudManifestError("contention item teardown was not exact")
    expected_gates = {
        "table_identity_bound": True,
        "exactly_one_winner": True,
        "all_losers_conditional": True,
        "no_provider_errors": True,
        "winner_readback_exact": True,
        "no_retries": True,
        "exact_teardown": True,
        "no_scientific_action": True,
    }
    if receipt["gates"] != expected_gates or receipt["verdict"] != "passed":
        raise CloudManifestError("lease-contention qualification has a failing gate")
    if receipt["residual_resource_ids"]:
        raise CloudManifestError("lease-contention qualification leaves residual resources")
    return receipt


def require_lease_contention_cleanup(record: Mapping[str, Any]) -> dict[str, Any]:
    """Require cleanup of one exact failed-qualification item."""

    receipt = validate_lease_contention_cleanup_receipt(record)
    preflight = receipt["preflight"]
    deletion = receipt["deletion"]
    final = receipt["final"]
    if not (preflight["table_active"] and preflight["table_arn_exact"] and preflight["item_present"]):
        raise CloudManifestError("cleanup preflight did not find the signed target item")
    if not (preflight["owner_exact"] and preflight["action_id_exact"]):
        raise CloudManifestError("cleanup target item is not bound to the failed action")
    if not (deletion["attempted"] and deletion["succeeded"] and final["item_absent"]):
        raise CloudManifestError("cleanup did not prove exact item absence")
    expected_gates = {
        "identity_bound": True,
        "exact_item_bound": True,
        "delete_succeeded": True,
        "final_absent": True,
        "no_retries": True,
        "no_scientific_action": True,
    }
    if receipt["gates"] != expected_gates or receipt["verdict"] != "passed":
        raise CloudManifestError("cleanup qualification has a failing gate")
    if receipt["residual_resource_ids"]:
        raise CloudManifestError("cleanup leaves residual resources")
    return receipt

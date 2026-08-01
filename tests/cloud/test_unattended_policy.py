import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.unattended_policy import (
    admit_unattended_job,
    policy_digest,
    readable_policy_summary,
    validate_unattended_policy,
)

FIXTURE = Path(__file__).parents[2] / "fixtures" / "cloud" / "unattended-spend-policy-candidate.json"
NOW = datetime(2026, 8, 1, tzinfo=UTC)


def candidate() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def active() -> dict:
    policy = candidate()
    statement = readable_policy_summary(policy)
    policy["status"] = "active"
    policy["operator_approval"] = {
        "approval_id": "chat-approval-20260731",
        "approved_by": "operator",
        "statement": statement,
    }
    return policy


def request(**overrides: object) -> dict:
    value = {
        "job_id": "pilot-1",
        "provider": "openai",
        "action_class": "bounded_api_pilot",
        "projected_cost_usd": 4.0,
        "retry_count": 0,
        "input_binding_sha256": "a" * 64,
    }
    value.update(overrides)
    return value


def history(policy: dict, amount: float, *, age_days: int = 0) -> dict:
    return {
        "policy_id": policy["policy_id"],
        "policy_sha256": policy_digest(policy),
        "recorded_at": (NOW - timedelta(days=age_days)).isoformat(),
        "amount_usd": amount,
        "state": "settled",
    }


def test_candidate_is_readable_but_cannot_admit_work() -> None:
    policy = validate_unattended_policy(candidate())
    assert "USD 5.00 per job" in readable_policy_summary(policy)
    with pytest.raises(CloudManifestError, match="not active"):
        admit_unattended_job(policy, request(), [], now=NOW)


def test_active_policy_admits_bounded_job_and_hides_hash_from_operator_statement() -> None:
    policy = active()
    receipt = admit_unattended_job(policy, request(), [], now=NOW)
    assert receipt["reserved_usd"] == 4.0
    assert receipt["policy_sha256"] == policy_digest(policy)
    assert "sha" not in policy["operator_approval"]["statement"].lower()


def test_vague_or_stale_human_statement_cannot_activate_policy() -> None:
    policy = active()
    policy["operator_approval"]["statement"] = "Approve something cheap."
    with pytest.raises(CloudManifestError, match="complete readable policy summary"):
        validate_unattended_policy(policy)


@pytest.mark.parametrize(
    "overrides,error",
    [
        ({"projected_cost_usd": 5.01}, "per-job"),
        ({"retry_count": 3}, "retry"),
        ({"provider": "anthropic"}, "provider"),
        ({"action_class": "canonical_experiment"}, "separate human-readable"),
        ({"action_class": "training"}, "separate human-readable"),
        ({"input_binding_sha256": "operator typed nothing"}, "internal SHA-256"),
    ],
)
def test_policy_fails_closed_on_scope_or_safety_drift(overrides: dict, error: str) -> None:
    with pytest.raises(CloudManifestError, match=error):
        admit_unattended_job(active(), request(**overrides), [], now=NOW)


def test_rolling_window_counts_reserved_and_settled_receipts() -> None:
    policy = active()
    with pytest.raises(CloudManifestError, match="rolling ceiling"):
        admit_unattended_job(policy, request(), [history(policy, 21.01)], now=NOW)
    receipt = admit_unattended_job(policy, request(), [history(policy, 100.0, age_days=31)], now=NOW)
    assert receipt["reserved_usd"] == 4.0


def test_revocation_expiry_and_policy_edits_stop_admission() -> None:
    policy = active()
    revoked = copy.deepcopy(policy)
    revoked["status"] = "revoked"
    with pytest.raises(CloudManifestError, match="not active"):
        admit_unattended_job(revoked, request(), [], now=NOW)
    with pytest.raises(CloudManifestError, match="not currently valid"):
        admit_unattended_job(policy, request(), [], now=datetime(2028, 1, 1, tzinfo=UTC))
    old_receipt = history(policy, 24.0)
    policy["allowed_action_classes"].remove("bounded_retrieval")
    with pytest.raises(CloudManifestError, match="complete readable policy summary"):
        admit_unattended_job(policy, request(), [old_receipt], now=NOW)
    policy["operator_approval"]["statement"] = readable_policy_summary(candidate() | {
        "allowed_action_classes": policy["allowed_action_classes"]
    })
    with pytest.raises(CloudManifestError, match="rolling ceiling"):
        admit_unattended_job(policy, request(), [old_receipt], now=NOW)

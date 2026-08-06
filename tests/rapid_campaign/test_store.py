from __future__ import annotations

import json

import pytest

from pneuma_lab.rapid_campaign.store import CampaignStateStore, StateError


def test_store_hash_chain_round_trip_and_transition_rules(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = CampaignStateStore(path, campaign_id="campaign", version_id="r2")
    assert store.snapshot().phase == "draft"
    store.append("classified", {"impact": "C0"})
    store.append("prepared", {})
    restored = CampaignStateStore(path, campaign_id="campaign", version_id="r2")
    assert restored.snapshot().phase == "prepared"
    assert restored.snapshot().sequence == 3
    with pytest.raises(StateError, match="transition"):
        restored.append("analysed", {})


def test_store_rejects_tampering(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = CampaignStateStore(path, campaign_id="campaign", version_id="r2")
    store.append("classified", {"impact": "C0"})
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["events"][1]["payload"]["impact"] = "C4"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(StateError, match="digest"):
        CampaignStateStore(path, campaign_id="campaign", version_id="r2")


def test_submission_identity_is_immutable_and_idempotent(tmp_path) -> None:
    store = CampaignStateStore(
        tmp_path / "state.json", campaign_id="campaign", version_id="r2"
    )
    store.append("classified", {"impact": "C0"})
    store.append("prepared", {})
    store.append("reserved", {"reservation_id": "run"})
    store.append("submitting", {"client_token": "token"})
    first = store.record_submission(
        parent_job_id="parent", child_job_ids=("a", "b"), receipt_sha256="f" * 64
    )
    assert first.parent_job_id == "parent"
    assert (
        store.record_submission(
            parent_job_id="parent", child_job_ids=("a", "b"), receipt_sha256="f" * 64
        )
        == first
    )
    with pytest.raises(StateError, match="differs"):
        store.record_submission(
            parent_job_id="other", child_job_ids=("a", "b"), receipt_sha256="f" * 64
        )

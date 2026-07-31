from pneuma_lab.cloud.orchestration import LocalLeaseStore
from pneuma_lab.cloud.reconcile import reconcile


def test_restore_mismatch_invalidates_whole_block() -> None:
    store = LocalLeaseStore(); lease = store.acquire("a", "one", 0, 10)
    assert reconcile(store.terminal(lease, 1, restore_matches=False)) == "whole_task_block_invalid"

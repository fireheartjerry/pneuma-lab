import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.orchestration import LocalLeaseStore


def test_duplicate_delivery_has_one_terminal_history() -> None:
    store = LocalLeaseStore(); lease = store.acquire("a", "one", 0, 10)
    assert store.terminal(lease, 1, restore_matches=True).state == "terminal"
    with pytest.raises(CloudManifestError): store.acquire("a", "two", 2, 10)


def test_contention_and_expiry_fail_closed() -> None:
    store = LocalLeaseStore(); lease = store.acquire("a", "one", 0, 1)
    with pytest.raises(CloudManifestError): store.acquire("a", "two", 0, 1)
    with pytest.raises(CloudManifestError): store.terminal(lease, 1, restore_matches=True)

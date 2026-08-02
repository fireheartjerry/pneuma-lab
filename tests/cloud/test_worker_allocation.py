from __future__ import annotations

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.worker_allocation import partition_work_ids, verify_partition


def test_partition_is_canonical_disjoint_and_input_order_independent() -> None:
    expected = {"worker-0": ("task-a", "task-c"), "worker-1": ("task-b", "task-d")}
    allocation = partition_work_ids(["task-d", "task-a", "task-c", "task-b"])

    assert allocation == expected
    assert verify_partition(allocation, expected_work_ids=["task-b", "task-d", "task-a", "task-c"]) == expected


@pytest.mark.parametrize("work_ids", [("task-a", "task-a"), ("task-a",), ("task-a", "")])
def test_partition_rejects_duplicate_or_unserviceable_work(work_ids: tuple[str, ...]) -> None:
    with pytest.raises(CloudManifestError):
        partition_work_ids(work_ids)


def test_partition_verifier_rejects_overlap_or_unexpected_worker() -> None:
    allocation = partition_work_ids(["task-a", "task-b", "task-c", "task-d"])
    allocation["worker-1"] = ("task-a", "task-b")
    with pytest.raises(CloudManifestError, match="canonical disjoint"):
        verify_partition(allocation, expected_work_ids=["task-a", "task-b", "task-c", "task-d"])

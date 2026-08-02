"""Deterministic, disjoint work allocation for the two-worker AWS topology."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .errors import CloudManifestError


WORKER_IDS = ("worker-0", "worker-1")


def partition_work_ids(work_ids: Sequence[str]) -> dict[str, tuple[str, ...]]:
    """Allocate canonical work identifiers round-robin without overlap.

    The scientific controller must supply immutable identifiers from the frozen
    authority. Sorting makes the partition independent of submitter order;
    duplicate or undersized work sets fail before any cloud submission.
    """

    if any(not isinstance(work_id, str) or not work_id for work_id in work_ids):
        raise CloudManifestError("work identifiers must be non-empty strings")
    canonical = tuple(sorted(work_ids))
    if len(set(canonical)) != len(canonical):
        raise CloudManifestError("work identifiers must be unique before worker allocation")
    if len(canonical) < len(WORKER_IDS):
        raise CloudManifestError("two-worker allocation requires work for each worker")
    return {
        worker_id: tuple(canonical[index::len(WORKER_IDS)])
        for index, worker_id in enumerate(WORKER_IDS)
    }


def verify_partition(
    allocation: Mapping[str, Sequence[str]], *, expected_work_ids: Sequence[str]
) -> dict[str, tuple[str, ...]]:
    """Reject overlap, omission, reordered worker identities, or drift."""

    expected = partition_work_ids(expected_work_ids)
    if set(allocation) != set(WORKER_IDS):
        raise CloudManifestError("worker allocation must name exactly the approved workers")
    observed = {worker_id: tuple(allocation[worker_id]) for worker_id in WORKER_IDS}
    if observed != expected:
        raise CloudManifestError("worker allocation is not the canonical disjoint partition")
    return observed

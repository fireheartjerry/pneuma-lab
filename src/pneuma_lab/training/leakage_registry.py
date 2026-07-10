"""Cross-dataset repo leakage registry (foundation).

Before any *joint* training run mixes datasets (e.g. Dataset #1
``swe-gym-openhands-sampled`` and Dataset #2 ``open-swe-traces``), the repos
that back their examples must be checked for overlap: SWE-rebench-V2 and the
SWE-Gym/SWE-bench family share upstream repositories, so a repo appearing in
one dataset's train split and another dataset's test split would leak.

This module is the deterministic checker + a canonicalization scheme so repos
can be compared even when one lane stores raw ``owner/repo`` strings and the
other stores ``sha256:``-prefixed digests (Open-SWE-Traces is digest-only).
It is a *foundation*: it computes overlap over whatever repo sets it is given
and never authorizes training. Populating it with the full real repo sets is a
later, separately gated step (reading every Dataset #1 and Dataset #2 repo).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

REGISTRY_VERSION = "pneuma-cross-dataset-leakage/0.1.0"
DIGEST_PREFIX = "sha256:"


def repo_digest(repo: str) -> str:
    """Canonical repo digest: ``sha256:<hex>`` over the raw repo string.

    Must match ``adapters.open_swe_traces._digest`` so digests line up across
    lanes.
    """
    return DIGEST_PREFIX + hashlib.sha256(repo.encode("utf-8")).hexdigest()


def canonicalize_repo(repo: str) -> str:
    """Map a repo to its digest. Already-digested values pass through unchanged.

    Lets the checker compare a raw-``owner/repo`` lane (Dataset #1) against a
    digest-only lane (Dataset #2) without ever needing the raw string of the
    digest-only side.
    """
    value = str(repo).strip()
    if value.startswith(DIGEST_PREFIX):
        return value
    return repo_digest(value)


def collect_split_group_repos(examples: Iterable[dict]) -> set[str]:
    """Canonical repo digests referenced by a set of training examples."""
    digests: set[str] = set()
    for example in examples:
        repo = (example.get("split_group") or {}).get("repo")
        if isinstance(repo, str) and repo:
            digests.add(canonicalize_repo(repo))
    return digests


def check_overlap(
    dataset_a_repos: Iterable[str],
    dataset_b_repos: Iterable[str],
) -> dict:
    """Deterministic overlap report between two repo sets (order-independent)."""
    a = {canonicalize_repo(r) for r in dataset_a_repos}
    b = {canonicalize_repo(r) for r in dataset_b_repos}
    overlap = sorted(a & b)
    return {
        "registry_version": REGISTRY_VERSION,
        "dataset_a_repo_count": len(a),
        "dataset_b_repo_count": len(b),
        "overlap_count": len(overlap),
        "overlapping_repo_digests": overlap,
        "disjoint": not overlap,
        "joint_training_safe": not overlap,
        "note": (
            "disjoint repo sets are necessary but NOT sufficient for joint "
            "training; other blockers (ToS, authorization) still apply"
        ),
    }


def build_registry_manifest(
    *,
    dataset_a_id: str,
    dataset_b_id: str,
    dataset_a_repos: Iterable[str] | None = None,
    dataset_b_repos: Iterable[str] | None = None,
    populated: bool = False,
) -> dict:
    """Build a metadata manifest describing a cross-dataset leakage check.

    When ``populated`` is False (the default foundation state) the repo sets are
    treated as not-yet-collected and the manifest records that joint training is
    blocked pending population.
    """
    if populated and dataset_a_repos is not None and dataset_b_repos is not None:
        overlap = check_overlap(dataset_a_repos, dataset_b_repos)
        status = "populated"
    else:
        overlap = {
            "registry_version": REGISTRY_VERSION,
            "dataset_a_repo_count": None,
            "dataset_b_repo_count": None,
            "overlap_count": None,
            "overlapping_repo_digests": [],
            "disjoint": None,
            "joint_training_safe": False,
            "note": "repo sets not yet collected; joint training blocked",
        }
        status = "foundation_unpopulated"
    return {
        "leakage_registry_schema_version": "0.1.0",
        "registry_version": REGISTRY_VERSION,
        "status": status,
        "canonicalization": {
            "scheme": "sha256:<hex> over raw repo string",
            "handles_mixed_raw_and_digest_lanes": True,
            "matches_adapter_digest": "adapters.open_swe_traces._digest",
        },
        "datasets": {
            "a": {"dataset_id": dataset_a_id},
            "b": {"dataset_id": dataset_b_id},
        },
        "overlap": overlap,
        "joint_training_authorization": {
            "status": "not_authorized",
            "requires": [
                "populated repo sets for both datasets",
                "verified zero overlap OR an explicit split-quarantine plan",
                "all other per-dataset blockers resolved (e.g. Minimax/Qwen ToS)",
            ],
        },
    }


__all__ = [
    "REGISTRY_VERSION",
    "DIGEST_PREFIX",
    "repo_digest",
    "canonicalize_repo",
    "collect_split_group_repos",
    "check_overlap",
    "build_registry_manifest",
]

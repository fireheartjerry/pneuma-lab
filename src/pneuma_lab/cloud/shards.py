"""Deterministic contiguous shard identities without a results model."""

from __future__ import annotations

from .errors import CloudManifestError


def shard_range(index: int, count: int, total: int) -> range:
    if count <= 0 or total <= 0 or not 0 <= index < count:
        raise CloudManifestError("invalid shard topology")
    start = total * index // count
    return range(start, total * (index + 1) // count)

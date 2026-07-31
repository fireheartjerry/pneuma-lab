"""Fail-closed launch preflight and dry-run teardown planning."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .errors import CloudManifestError


_ORDER = ("jobs", "queue", "compute", "instances", "volumes_endpoints", "registry", "buckets")
PRIMARY_REQUIRED_VCPUS = 8


def require_quota(applied_vcpus: int, required_vcpus: int = PRIMARY_REQUIRED_VCPUS) -> None:
    if applied_vcpus < required_vcpus:
        raise CloudManifestError("applied quota is zero or insufficient")


def teardown_plan(ownership: Mapping[str, Sequence[str]], protected: set[str], tag_matches: set[str]) -> tuple[str, ...]:
    targets: list[str] = []
    for kind in _ORDER:
        for target in sorted(ownership.get(kind, ())):
            if target in protected:
                raise CloudManifestError("protected resource exclusion")
            targets.append(f"{kind}:{target}")
    if not targets:
        raise CloudManifestError("tag-only teardown target is forbidden")
    return tuple(targets)


def residuals(ownership: Mapping[str, Sequence[str]], tag_matches: set[str]) -> tuple[str, ...]:
    owned = {value for values in ownership.values() for value in values}
    return tuple(sorted(tag_matches - owned))

"""Conservative exact-node selection; uncertainty always widens."""

from __future__ import annotations

from collections.abc import Mapping, Set
from dataclasses import dataclass

from .manifest import TestManifest


_STRUCTURAL_NAMES = frozenset(
    {
        "pyproject.toml",
        "uv.lock",
        "tests/smoke/conftest.py",
        "src/pneuma_lab/testd/protocol.py",
        "src/pneuma_lab/testd/selection.py",
        "src/pneuma_lab/testd/worker.py",
    }
)


@dataclass(frozen=True, slots=True)
class Selection:
    node_ids: tuple[str, ...]
    widening_reason: str


def _reachable(path: str, edges: Mapping[str, Set[str]]) -> set[str]:
    result = {path}
    pending = [path]
    while pending:
        current = pending.pop()
        for parent in edges.get(current, set()):
            if parent not in result:
                result.add(parent)
                pending.append(parent)
    return result


def select(
    manifest: TestManifest,
    *,
    dependencies: Mapping[str, Set[str]],
    transitive_edges: Mapping[str, Set[str]],
    changed_paths: tuple[str, ...],
    prior_failures: tuple[str, ...] = (),
    include_forensic: bool = False,
) -> Selection:
    """Select exact known consumers; all uncertainty becomes full smoke."""

    if include_forensic:
        return Selection(manifest.forensic_nodes, "explicit_forensic")
    if prior_failures:
        return Selection(manifest.micro_nodes, "prior_failure")
    if not changed_paths:
        return Selection((), "known_no_change")
    if any(
        path in _STRUCTURAL_NAMES
        or path.endswith("/__init__.py")
        or path.startswith("tests/")
        for path in changed_paths
    ):
        return Selection(manifest.micro_nodes, "structural_change")
    selected: set[str] = set()
    for path in changed_paths:
        consumers: set[str] = set()
        for reachable in _reachable(path, transitive_edges):
            consumers.update(dependencies.get(reachable, set()))
        if not consumers:
            return Selection(manifest.micro_nodes, "unknown_dependency")
        selected.update(consumers)
    return Selection(tuple(sorted(selected)), "known_dependencies")

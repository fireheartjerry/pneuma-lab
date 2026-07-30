"""Immutable exact-node manifest for the retained test tiers."""

from __future__ import annotations

from typing import ClassVar
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TestManifest:
    __test__: ClassVar[bool] = False
    micro_nodes: tuple[str, ...]
    milestone_nodes: tuple[str, ...]
    forensic_nodes: tuple[str, ...]

    def __post_init__(self) -> None:
        all_nodes = self.micro_nodes + self.milestone_nodes + self.forensic_nodes
        if not self.micro_nodes or len(all_nodes) != len(set(all_nodes)):
            raise ValueError("manifest nodes must be non-empty and unique")
        if any(
            not node.startswith("tests/") or "::test_" not in node for node in all_nodes
        ):
            raise ValueError("manifest contains a non-test node id")

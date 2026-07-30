"""Immutable exact-node manifest for the retained test tiers."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
from typing import ClassVar


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


def collect_micro_manifest(repository_root: Path) -> TestManifest:
    """Collect the independent smoke oracle's exact nodes in a disposable process."""
    environment = os.environ.copy()
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    completed = subprocess.run(
        (
            sys.executable,
            "-m",
            "pytest",
            "tests/smoke",
            "--collect-only",
            "-vv",
            "-p",
            "no:cacheprovider",
        ),
        cwd=repository_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    nodes = tuple(
        sorted(
            "tests/smoke/test_micro_gate.py::" + line.partition("<Function ")[2][:-1]
            for line in completed.stdout.splitlines()
            if line.strip().startswith("<Function test_")
        )
    )
    if completed.returncode or not nodes:
        raise RuntimeError("smoke manifest collection failed closed")
    return TestManifest(nodes, (), ())

"""Portable import boundary checks for the default micro-gate dependencies."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_smoke_dependencies_import_without_posix_directory_constant() -> None:
    root = Path(__file__).parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(root / "src")
    program = "\n".join(
        (
            "import os",
            "for name in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_CLOEXEC'):",
            "    if hasattr(os, name):",
            "        delattr(os, name)",
            "import pneuma_lab.resampling_null.packets",
            "import pneuma_lab.resampling_null.synthetic_environment",
        )
    )

    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_assignment_seed_import_avoids_descriptor_publication_module() -> None:
    root = Path(__file__).parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(root / "src")
    program = "\n".join(
        (
            "import sys",
            "from pneuma_lab.resampling_null.assignment import derive_seed",
            'assert derive_seed(7, "task-1", "prefix") == 15058118438168183076',
            'assert "pneuma_lab.resampling_null.publication" not in sys.modules',
        )
    )

    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

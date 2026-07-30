"""Fail-closed disposable launcher for the portable smoke oracle."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from typing import Any


_DEADLINE_SECONDS = 5.0


def build_cold_command(
    checkout: Path,
    *,
    python: str = sys.executable,
) -> tuple[list[str], dict[str, str]]:
    """Return the exact portable smoke command and its isolated environment."""

    root = Path(checkout).resolve()
    environment = dict(os.environ)
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    environment["PYTHONPYCACHEPREFIX"] = str(root / "build/testd/pycache")
    return (
        [
            python,
            "-m",
            "pytest",
            "tests/smoke",
            "-q",
            "-p",
            "no:cacheprovider",
            "--import-mode=importlib",
        ],
        environment,
    )


def _remaining(deadline: float) -> float:
    return max(0.0, deadline - time.monotonic())


def run_cold(
    checkout: Path,
    *,
    python: str = sys.executable,
    runner: Callable[..., Any] = subprocess.run,
) -> int:
    """Run one bounded disposable smoke gate, returning a fail-closed status."""

    root = Path(checkout).resolve()
    command, environment = build_cold_command(root, python=python)
    cache = Path(environment["PYTHONPYCACHEPREFIX"])
    deadline = time.monotonic() + _DEADLINE_SECONDS
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        if not cache.exists():
            cache.mkdir(parents=True, exist_ok=True)
            primed = runner(
                [
                    python,
                    "-m",
                    "compileall",
                    "-q",
                    "--invalidation-mode",
                    "checked-hash",
                    "src",
                    "tests/smoke",
                ],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=_remaining(deadline),
                check=False,
                creationflags=creationflags,
            )
            if not isinstance(primed, subprocess.CompletedProcess) or primed.returncode:
                return 1
        completed = runner(
            command,
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=_remaining(deadline),
            check=False,
            creationflags=creationflags,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1
    if not isinstance(completed, subprocess.CompletedProcess):
        return 1
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return 0 if completed.returncode == 0 else 1


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if any(argument not in {"--cold", "--smoke"} for argument in arguments):
        return 2
    return run_cold(Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    raise SystemExit(main())

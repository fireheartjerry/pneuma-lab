"""Bounded machine-readable benchmark harness for test-gate commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
from collections.abc import Sequence
from typing import Any


def _git_commit(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def benchmark(
    *,
    label: str,
    runs: int,
    output: Path,
    command: Sequence[str],
) -> dict[str, Any]:
    """Run one command repeatedly and write a receipt only if every run passes."""

    if type(label) is not str or not label or type(runs) is not int or runs <= 0:
        raise ValueError("label and runs must be non-empty/positive exact values")
    if not command or any(type(part) is not str or not part for part in command):
        raise ValueError("command must be a non-empty sequence of text")
    root = Path.cwd().resolve()
    durations: list[int] = []
    for _ in range(runs):
        started = time.perf_counter_ns()
        completed = subprocess.run(list(command), cwd=root, check=False)
        duration = time.perf_counter_ns() - started
        if completed.returncode != 0:
            raise RuntimeError(f"benchmark command exited {completed.returncode}")
        durations.append(duration)
    ordered = sorted(durations)
    p95_index = max(0, (len(ordered) * 95 + 99) // 100 - 1)
    receipt: dict[str, Any] = {
        "command": list(command),
        "durations_ns": durations,
        "git_commit": _git_commit(root),
        "label": label,
        "median_ns": int(statistics.median(durations)),
        "p95_ns": ordered[p95_index],
        "platform": platform.platform(),
        "python_cache_tag": sys.implementation.cache_tag,
        "python_version": platform.python_version(),
        "runs": runs,
    }
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)
    command = (
        arguments.command[1:] if arguments.command[:1] == ["--"] else arguments.command
    )
    try:
        benchmark(
            label=arguments.label,
            runs=arguments.runs,
            output=arguments.output,
            command=command,
        )
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

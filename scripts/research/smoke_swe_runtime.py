"""Non-official local smoke lane for the SWE Docker runtime.

This exercises the real ``DockerSweRuntime`` against real SWE task images on
whatever Docker daemon is in reach, so runtime defects surface without paying
for GPU Spot time.  It is deliberately cheap and deliberately not science.

It is NOT an official run and cannot become one:

* it never reads or writes an ``runs/official/`` prefix, and touches no S3 at all;
* it runs no subject model, no simulator, and no four-arm branch assignment;
* it produces no packet, grade of record, unblind, or scientific result;
* its receipt is marked ``NON_OFFICIAL_SMOKE`` and carries no authorization.

It answers one question: does a real task get through pull -> start -> exec ->
snapshot -> grade -> parse -> cleanup, and does any single Docker API call run
long enough that the historical 60-second docker-py default would have killed
the essential worker mid-run?
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ASSETS = (
    ROOT
    / "docs/research/neurips-2026-workshop/evidence"
    / "official-study-final-c120-v5-20260806"
    / "inputs/execution/swe-tasks.controller-only.json"
)
# The exact benchmark-worker image the terminal r8 action ran.
DEFAULT_PARSER_IMAGE = (
    "892077329800.dkr.ecr.us-east-1.amazonaws.com/"
    "pneuma-official-production-benchmark-worker@sha256:"
    "7f967dfee0defa6b0f30e9adac579fe929b5b2f6a061894fa930227139f79fc1"
)
# docker-py's historical default read timeout, and the reason r8 died at task
# 103 of 120.  Any stage slower than this would have raised ReadTimeout.
LEGACY_DOCKER_TIMEOUT_SECONDS = 60.0


def _load_tasks() -> dict[str, dict[str, Any]]:
    document = json.loads(ASSETS.read_text(encoding="utf-8"))
    tasks = document.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise SystemExit(f"no SWE execution assets at {ASSETS}")
    return {str(task["task_id"]): task for task in tasks if isinstance(task, dict)}


def _select(
    tasks: dict[str, dict[str, Any]],
    *,
    task_ids: list[str],
    language: str | None,
    count: int,
) -> list[dict[str, Any]]:
    if task_ids:
        missing = [task_id for task_id in task_ids if task_id not in tasks]
        if missing:
            raise SystemExit(f"unregistered task IDs: {missing}")
        return [tasks[task_id] for task_id in task_ids]
    if language is None:
        # Stratified: `count` tasks per language, so a sample spans the roster.
        by_language: dict[str, list[dict[str, Any]]] = {}
        for task in sorted(tasks.values(), key=lambda row: str(row["task_id"])):
            by_language.setdefault(str(task["language"]).lower(), []).append(task)
        return [
            task
            for key in sorted(by_language)
            for task in by_language[key][:count]
        ]
    pool = [
        task
        for task in tasks.values()
        if str(task["language"]).lower() == language.lower()
    ]
    if not pool:
        raise SystemExit(f"no registered tasks for language {language!r}")
    return sorted(pool, key=lambda task: str(task["task_id"]))[:count]


class _Timed:
    """Record per-stage wall clock so slow Docker calls are visible."""

    def __init__(self) -> None:
        self.stages: list[dict[str, Any]] = []

    def run(self, name: str, action: Any) -> Any:
        started = time.monotonic()
        try:
            result = action()
        except Exception as exc:
            elapsed = time.monotonic() - started
            self.stages.append(
                {
                    "stage": name,
                    "seconds": round(elapsed, 3),
                    "status": "FAILED",
                    "error_type": type(exc).__name__,
                    "error_detail": " ".join(str(exc).split())[:500],
                }
            )
            print(
                f"  {name:<18} {elapsed:8.1f}s  FAILED  {type(exc).__name__}",
                flush=True,
            )
            raise
        elapsed = time.monotonic() - started
        legacy = elapsed > LEGACY_DOCKER_TIMEOUT_SECONDS
        self.stages.append(
            {
                "stage": name,
                "seconds": round(elapsed, 3),
                "status": "OK",
                "exceeds_legacy_timeout": legacy,
            }
        )
        marker = "  <-- would have killed r8" if legacy else ""
        print(f"  {name:<18} {elapsed:8.1f}s  OK{marker}", flush=True)
        return result


def _smoke_one(runtime: Any, task: dict[str, Any], *, grade: bool) -> dict[str, Any]:
    from pneuma_lab.cloud.official_experiment import DockerSweRuntime

    task_id = str(task["task_id"])
    print(f"\n{task_id}  ({task['language']})")
    timed = _Timed()
    container = None
    snapshot = None
    result: dict[str, Any] = {"task_id": task_id, "language": task["language"]}
    try:
        timed.run("pull", lambda: runtime.pull(str(task["image_ref"])))
        container = timed.run("start", lambda: runtime.start(task, suffix="smoke"))
        rc, output = timed.run(
            "exec",
            lambda: DockerSweRuntime.exec(
                container, "ls /testbed | head -5", seconds=60
            ),
        )
        result["exec_rc"] = rc
        result["exec_head"] = output.strip().splitlines()[:5]
        _, mutated = timed.run("state_digest", lambda: runtime.state_digest(container))
        result["mutated"] = mutated
        snapshot = timed.run(
            "commit", lambda: runtime.commit(container, label=f"{task_id}:smoke")
        )
        if grade:
            graded = timed.run(
                "grade", lambda: runtime.grade(snapshot, task, suffix="smoke")
            )
            result["grade"] = {
                "resolved": graded["resolved"],
                "apply_test_patch_rc": graded["apply_test_patch_rc"],
                "registered_check_count": graded["registered_check_count"],
                "observed_check_count": graded["observed_check_count"],
                "elapsed_seconds": round(float(graded["elapsed_seconds"]), 3),
            }
        result["status"] = "OK"
    except Exception as exc:
        result["status"] = "FAILED"
        result["error_type"] = type(exc).__name__
        result["error_detail"] = " ".join(str(exc).split())[:1000]
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                pass
        if snapshot is not None:
            try:
                snapshot.remove(force=True)
            except Exception:
                pass
    result["stages"] = timed.stages
    slow = [row for row in timed.stages if row.get("exceeds_legacy_timeout")]
    result["stages_exceeding_legacy_timeout"] = [row["stage"] for row in slow]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", action="append", default=[])
    parser.add_argument("--language")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--parser-image", default=DEFAULT_PARSER_IMAGE)
    parser.add_argument(
        "--run-root",
        type=Path,
        required=True,
        help="scratch directory for parser sandbox IO; must not be inside the repo",
    )
    parser.add_argument(
        "--host-run-root",
        help="host-visible path for --run-root (defaults to its absolute path)",
    )
    parser.add_argument(
        "--grade",
        action="store_true",
        help="run the full rebuild/test/parse grade (slow, and the real test)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="concurrent task gradings; bounded by host RAM and cores",
    )
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)

    run_root = args.run_root.resolve()
    if ROOT == run_root or ROOT in run_root.parents:
        raise SystemExit("--run-root must live outside the repository")
    run_root.mkdir(parents=True, exist_ok=True)
    host_run_root = args.host_run_root or str(run_root)

    os.environ["PNEUMA_BENCHMARK_WORKER_IMAGE_REF"] = args.parser_image
    os.environ["PNEUMA_HOST_RUN_ROOT"] = host_run_root

    from pneuma_lab.cloud.official_experiment import (
        _DOCKER_API_TIMEOUT_SECONDS,
        DockerSweRuntime,
    )

    tasks = _load_tasks()
    selected = _select(
        tasks, task_ids=args.task_id, language=args.language, count=args.count
    )
    print("NON-OFFICIAL SMOKE LANE - no subject model, no S3, no scientific result")
    print(f"docker transport budget : {_DOCKER_API_TIMEOUT_SECONDS}s")
    print(f"legacy default (r8)     : {LEGACY_DOCKER_TIMEOUT_SECONDS}s")
    print(f"parser image            : {args.parser_image}")
    print(f"grade                   : {args.grade}")
    print(f"tasks                   : {[str(t['task_id']) for t in selected]}")

    runtime = DockerSweRuntime(
        run_root=run_root,
        worker_id="smoke",
        parser_image=args.parser_image,
        host_run_root=host_run_root,
    )
    if args.workers > 1 and len(selected) > 1:
        # Grading a heavy c/cpp task runs a parallel compile, so concurrency here
        # is bounded by host RAM and cores, not by anything in the runtime.
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.workers
        ) as executor:
            futures = [
                executor.submit(_smoke_one, runtime, task, grade=args.grade)
                for task in selected
            ]
            results = [future.result() for future in futures]
    else:
        results = [_smoke_one(runtime, task, grade=args.grade) for task in selected]
    receipt = {
        "record_kind": "cloud_non_official_swe_runtime_smoke",
        "schema_version": "0.1.0",
        "status": "NON_OFFICIAL_SMOKE",
        "authorizing": False,
        "scientific_result": False,
        "docker_api_timeout_seconds": _DOCKER_API_TIMEOUT_SECONDS,
        "legacy_docker_timeout_seconds": LEGACY_DOCKER_TIMEOUT_SECONDS,
        "parser_image": args.parser_image,
        "graded": args.grade,
        "tasks": results,
    }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(
            json.dumps(receipt, indent=4, sort_keys=True) + "\n", encoding="utf-8"
        )
    failed = [row for row in results if row["status"] != "OK"]
    slow = sorted(
        {stage for row in results for stage in row["stages_exceeding_legacy_timeout"]}
    )
    print(f"\n{len(results) - len(failed)}/{len(results)} tasks OK")
    if slow:
        print(f"stages that outran the legacy 60s default: {slow}")
        print("=> the historical docker-py default would have failed this run")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""OpenHands-Sampled-Trajectories rows -> trajectory-bearing PneumaTrace v0.2.

Each source row is one REAL recorded agent run over a SWE-Gym task:
``instance_id``, agent ``run_id``, ``resolved`` (harness outcome), ``messages``
(OpenAI-style chat with tool calls), ``test_result``. The adapter emits:

    world-frame        real exteroception at t0 (task text the agent saw,
                       repo identity; head_sha joined from the SWE-Gym task
                       table when available),
    governance-frame   minimal synthetic contract (same as task-only traces),
    agent-trace-frames one per assistant step, observable-only (see
                       ``adapters.trajectory`` for the honesty rules).

Trajectory/outcome blocks land in the envelope; agent-trace frames exist ONLY
because a real trajectory exists (``envelope.consistency_errors`` enforces it).
Deterministic by construction: canonical JSON, identity ids, synthetic-ordinal
timestamps, content hashes. Raw message text never enters the frames.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

from pneuma_lab.adapters import envelope as env
from pneuma_lab.adapters import trajectory as traj
from pneuma_lab.schemas import validate

ENVELOPE_VERSION = "0.2.0"
FRAME_SCHEMA_VERSION = "0.1.0"

DATASET = "swe-gym"
DATASET_VARIANT = "OpenHands-Sampled-Trajectories"
BENCHMARK = "swe-gym"
HF_REPO = "SWE-Gym/OpenHands-Sampled-Trajectories"
TASK_HF_REPO = "SWE-Gym/SWE-Gym"
ADAPTER = {"name": "openhands-sampled", "version": "0.1.0"}
SOURCE_KIND = "openai-chat-messages"


class SkipRow(ValueError):
    """Row cannot produce a valid trace (missing/dirty required data)."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def repo_from_instance_id(instance_id: str) -> str:
    """SWE-Bench convention: ``owner__repo-1234`` -> ``owner/repo``."""
    head, sep, _ = instance_id.rpartition("-")
    if not sep or "__" not in head:
        return ""
    return head.replace("__", "/", 1)


def build_world_frame(
    objective_text: str, repo: str, run_id: str, task_row: dict | None
) -> dict:
    """Real exteroception at t0: the task text the agent actually saw."""
    frame = {
        "schema_version": FRAME_SCHEMA_VERSION,
        "frame_kind": "world",
        "timestamp": traj.synthetic_timestamp(0),
        "timestamp_provenance": traj.TIMESTAMP_PROVENANCE,
        "run_id": run_id,
        "phase": "preamble",
        "objective": {"text": objective_text},
        "repo_state": {"repo": repo},
        "test_state": {"ran": False, "not_yet_run": True},
    }
    if task_row and task_row.get("base_commit"):
        frame["repo_state"]["head_sha"] = task_row["base_commit"]
    return frame


def build_governance_frame(run_id: str) -> dict:
    """Minimal synthetic contract frame. kill_switch 'off' = psyche is a no-op (data)."""
    return {
        "schema_version": FRAME_SCHEMA_VERSION,
        "frame_kind": "governance",
        "timestamp": traj.synthetic_timestamp(0),
        "timestamp_provenance": traj.TIMESTAMP_PROVENANCE,
        "run_id": run_id,
        "verifier_isolation": True,
        "kill_switch_state": "off",
    }


_REPORT_FLAGS = (
    "resolved",
    "empty_generation",
    "error_eval",
    "failed_apply_patch",
    "test_timeout",
)


def _outcome_block(row: dict) -> dict:
    """Observed harness outcome: booleans + patch digest, never raw output text."""
    outcome: dict = {
        "kind": "swe-gym-harness-report",
        "resolved": bool(row.get("resolved")),
    }
    test_result = row.get("test_result")
    if isinstance(test_result, str):
        try:
            test_result = json.loads(test_result)
        except json.JSONDecodeError:
            test_result = None
    if isinstance(test_result, dict):
        report = test_result.get("report")
        if isinstance(report, dict):
            outcome["report"] = {
                k: bool(report[k]) for k in _REPORT_FLAGS if k in report
            }
        git_patch = test_result.get("git_patch") or ""
        outcome["git_patch_sha256"] = _sha256(git_patch)
        outcome["git_patch_length"] = len(git_patch)
    return outcome


def as_list(value) -> list[str]:
    """Test lists arrive as a real list or a JSON-encoded string."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return [str(v) for v in parsed] if isinstance(parsed, list) else []
    return []


def build_trace(
    row: dict,
    task_row: dict | None,
    hf_revision: str,
    source_file: str,
    source_row: int,
) -> dict:
    """Assemble one trajectory-bearing PneumaTrace. Raises SkipRow when unbuildable."""
    instance_id = row.get("instance_id")
    if not instance_id:
        raise SkipRow("missing instance_id")
    agent_run_id = row.get("run_id")
    if not agent_run_id:
        raise SkipRow("missing run_id")
    if row.get("resolved") is None:
        raise SkipRow("missing resolved label")
    try:
        extraction = traj.extract_agent_trace_frames(
            row.get("messages"),
            run_id="",  # run_id patched after id derivation
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise SkipRow(f"unusable messages: {exc}") from exc

    ids = env.derive_ids(DATASET, f"{instance_id}::{agent_run_id}", hf_revision)
    for frame in extraction["frames"]:
        frame["run_id"] = ids["run_id"]

    objective_text, redactions = traj.redact_text(extraction["first_user_text"])
    repo = (task_row or {}).get("repo") or repo_from_instance_id(instance_id)
    world = build_world_frame(objective_text, repo, ids["run_id"], task_row)
    governance = build_governance_frame(ids["run_id"])

    reference_supervision: dict = {}
    if task_row:
        gold_patch = task_row.get("patch") or ""
        test_patch = task_row.get("test_patch") or ""
        reference_supervision = {
            "gold_patch_sha256": _sha256(gold_patch),
            "test_patch_sha256": _sha256(test_patch),
        }

    trace = {
        "schema_version": ENVELOPE_VERSION,
        "trace_id": ids["trace_id"],
        "run_id": ids["run_id"],
        "adapter": dict(ADAPTER),
        "provenance": {
            "dataset": DATASET,
            "dataset_variant": DATASET_VARIANT,
            "source_id": f"{instance_id}::{agent_run_id}",
            "hf_repo": HF_REPO,
            "hf_revision": hf_revision,
            "source_file": source_file,
            "source_row": source_row,
            "task_join": {
                "hf_repo": TASK_HF_REPO,
                "joined": task_row is not None,
            },
        },
        "build": {
            "deterministic": True,
            "content_hash": "",
            "generated_from": ["dataset", "instance_id::run_id", "hf_revision"],
            "frame_sources": {
                "world-frame": "dataset-derived",
                "governance-frame": "synthetic-contract-minimum",
                "agent-trace-frame": env.TRAJECTORY_SOURCE,
            },
        },
        "privacy": {
            "status": "redacted" if redactions else "clean",
            "pii_scanned": True,
            "redactions": redactions,
        },
        "labels": {
            "instance_id": instance_id,
            "benchmark": BENCHMARK,
            "repo": repo,
            "language": "python",
            "split": "train",
            "task_family": "issue-resolution",
            "has_patch": task_row is not None and bool(task_row.get("patch")),
            "has_tests": task_row is not None
            and bool(
                task_row.get("test_patch")
                or as_list(task_row.get("FAIL_TO_PASS"))
                or as_list(task_row.get("PASS_TO_PASS"))
            ),
            "has_trajectory": True,
            "resolved": bool(row.get("resolved")),
        },
        "oracle": {
            "kind": "test-based",
            "fail_to_pass": as_list((task_row or {}).get("FAIL_TO_PASS")),
            "pass_to_pass": as_list((task_row or {}).get("PASS_TO_PASS")),
        },
        "reference_supervision": reference_supervision,
        "trajectory": {
            "present": True,
            "source_kind": SOURCE_KIND,
            "agent_run_id": agent_run_id,
            "num_messages": extraction["num_messages"],
            "num_agent_steps": extraction["num_agent_steps"],
            "timestamp_provenance": traj.TIMESTAMP_PROVENANCE,
        },
        "outcome": _outcome_block(row),
        "frames": [world, governance] + extraction["frames"],
    }
    trace["build"]["content_hash"] = env.content_hash(trace)
    trace["validation"] = {"schema": env.ENVELOPE_SCHEMA_FILE, "status": "valid"}
    return trace


ADAPTER_REPORT_SCHEMA_VERSION = "0.1.0"


def _index_row(trace: dict) -> dict:
    labels = trace["labels"]
    return {
        "trace_id": trace["trace_id"],
        "run_id": trace["run_id"],
        "source_id": trace["provenance"]["source_id"],
        "repo": labels["repo"],
        "split": labels["split"],
        "benchmark": labels["benchmark"],
        "has_patch": labels["has_patch"],
        "has_tests": labels["has_tests"],
        "has_trajectory": labels["has_trajectory"],
        "resolved": labels["resolved"],
        "num_frames": len(trace["frames"]),
        "num_agent_steps": trace["trajectory"]["num_agent_steps"],
        "oracle_kind": trace["oracle"]["kind"],
        "privacy_status": trace["privacy"]["status"],
        "validation_status": trace["validation"]["status"],
        "content_hash": trace["build"]["content_hash"],
    }


def _jsonl(objs: list[dict]) -> str:
    return "".join(env.canonical_json(o) + "\n" for o in objs)


def run(
    batches: list[tuple[str, list[dict]]],
    task_index: dict[str, dict],
    hf_revision: str,
) -> dict[str, str]:
    """Build all traces from (source_file, rows) batches; return canonical files."""
    flat = [
        (str(row.get("instance_id", "")), str(row.get("run_id", "")), sf, i, row)
        for sf, rows in batches
        for i, row in enumerate(rows)
    ]
    flat.sort(key=lambda t: (t[0], t[1], t[2], t[3]))

    valid, invalid, skipped = [], [], []
    for instance_id, _agent_run, source_file, source_row, row in flat:
        try:
            trace = build_trace(
                row,
                task_index.get(instance_id),
                hf_revision,
                source_file,
                source_row,
            )
        except SkipRow as exc:
            skipped.append(
                {
                    "source_id": row.get("instance_id", f"<row {source_row}>"),
                    "reason": str(exc),
                }
            )
            continue
        frame_errs = [e for f in trace["frames"] for e in validate.iter_errors(f)]
        env_errs = env.envelope_errors(trace)
        cons_errs = env.consistency_errors(trace)
        if frame_errs or env_errs or cons_errs:
            trace["validation"]["status"] = "invalid"
            invalid.append(
                {
                    "trace_id": trace["trace_id"],
                    "source_id": trace["provenance"]["source_id"],
                    "errors": {
                        "envelope": env_errs,
                        "frames": frame_errs,
                        "consistency": cons_errs,
                    },
                    "trace": trace,
                }
            )
        else:
            valid.append(trace)

    traces_str = _jsonl(valid)
    invalid_str = _jsonl(invalid)
    index_str = _jsonl([_index_row(t) for t in valid])

    total_rows = sum(len(rows) for _, rows in batches)
    redaction_totals = traj.merge_redactions(
        [t["privacy"]["redactions"] for t in valid]
    )
    report = {
        "adapter_report_schema_version": ADAPTER_REPORT_SCHEMA_VERSION,
        "adapter": dict(ADAPTER),
        "dataset": DATASET,
        "hf_repo": HF_REPO,
        "hf_revision": hf_revision,
        "task_join_hf_repo": TASK_HF_REPO,
        "counts": {
            "source_rows": total_rows,
            "traces_emitted": len(valid) + len(invalid),
            "valid": len(valid),
            "invalid": len(invalid),
            "skipped": len(skipped),
        },
        "trajectory": {
            "traces_with_task_join": sum(
                1 for t in valid if t["provenance"]["task_join"]["joined"]
            ),
            "traces_missing_task_join": sum(
                1 for t in valid if not t["provenance"]["task_join"]["joined"]
            ),
            "total_agent_steps": sum(t["trajectory"]["num_agent_steps"] for t in valid),
            "resolved_true": sum(1 for t in valid if t["labels"]["resolved"]),
            "resolved_false": sum(1 for t in valid if not t["labels"]["resolved"]),
        },
        "privacy": {"redaction_totals": redaction_totals},
        "ordering": {
            "emission_sort_key": "instance_id, run_id, source_file, source_row",
            "source_row_preserved": True,
        },
        "skipped_source_ids": skipped,
        "invalid_source_ids": [x["source_id"] for x in invalid],
        "traces_file_sha256": _sha256(traces_str),
        "trace_index_file_sha256": _sha256(index_str),
        "invalid_traces_file_sha256": _sha256(invalid_str),
        "warnings": [],
    }
    return {
        "pneuma_traces.jsonl": traces_str,
        "pneuma_traces.invalid.jsonl": invalid_str,
        "trace_index.jsonl": index_str,
        "adapter_report.json": env.canonical_json(report) + "\n",
    }


OUTPUT_FILES = (
    "pneuma_traces.jsonl",
    "pneuma_traces.invalid.jsonl",
    "trace_index.jsonl",
    "adapter_report.json",
)

# Task-table fields consumed for the join (fixture task rows keep exactly these).
TASK_FIELDS = (
    "instance_id",
    "repo",
    "base_commit",
    "patch",
    "test_patch",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
)


def read_parquet_rows(path: str) -> list[dict]:
    import pyarrow.parquet as pq

    return pq.read_table(path).to_pylist()


def build_task_index(rows: list[dict]) -> dict[str, dict]:
    """instance_id -> task row (first occurrence wins deterministically)."""
    index: dict[str, dict] = {}
    for row in rows:
        iid = row.get("instance_id")
        if iid and iid not in index:
            index[iid] = row
    return index


def write_outputs(out_dir: str, files: dict[str, str]) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for name in OUTPUT_FILES:
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(files[name])


DEFAULT_INPUTS = tuple(
    "C:/pneuma-data/raw/swe-gym/OpenHands-Sampled-Trajectories/data/"
    f"train.raw-{i:05d}-of-00003.parquet"
    for i in range(3)
)
DEFAULT_TASK_INPUT = (
    "C:/pneuma-data/raw/swe-gym/SWE-Gym/data/train-00000-of-00001.parquet"
)
DEFAULT_OUT = "C:/pneuma-data/processed/swe-gym/openhands-sampled"
DEFAULT_HF_REVISION = "baf3a4e4bff514d48ddc08a93a2ade5c126212c7"
FIXTURE_DIR = os.path.join("fixtures", "adapters", "openhands_sampled")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pneuma_lab.adapters.openhands_sampled")
    p.add_argument("--input", nargs="+", default=list(DEFAULT_INPUTS))
    p.add_argument("--task-input", default=DEFAULT_TASK_INPUT)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--hf-revision", default=DEFAULT_HF_REVISION)
    p.add_argument(
        "--emit-fixture",
        action="store_true",
        help="Check adapter output against the committed golden fixture (fails on drift).",
    )
    p.add_argument(
        "--update-fixture",
        action="store_true",
        help="Rewrite the golden fixture from the fixture input (explicit opt-in).",
    )
    return p


def _fixture_jsonl(name: str) -> list[dict]:
    with open(os.path.join(FIXTURE_DIR, name), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _fixture_files() -> dict[str, str]:
    return run(
        [
            (
                "fixtures/adapters/openhands_sampled/input_rows.jsonl",
                _fixture_jsonl("input_rows.jsonl"),
            )
        ],
        build_task_index(_fixture_jsonl("task_rows.jsonl")),
        hf_revision=DEFAULT_HF_REVISION,
    )


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    if args.emit_fixture or args.update_fixture:
        files = _fixture_files()
        golden = os.path.join(FIXTURE_DIR, "golden")
        if args.update_fixture:
            write_outputs(golden, files)
            print(f"golden fixture rewritten in {golden}")
            return 0
        drift = [
            name
            for name in OUTPUT_FILES
            if open(os.path.join(golden, name), encoding="utf-8").read() != files[name]
        ]
        if drift:
            print(
                f"FIXTURE DRIFT in: {drift}. Re-run with --update-fixture to accept.",
                file=sys.stderr,
            )
            return 1
        print("fixture matches golden.")
        return 0

    batches = [(path, read_parquet_rows(path)) for path in args.input]
    task_index = build_task_index(read_parquet_rows(args.task_input))
    files = run(batches, task_index, hf_revision=args.hf_revision)
    write_outputs(args.out, files)
    report = json.loads(files["adapter_report.json"])
    print(f"wrote {report['counts']['valid']} traces to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

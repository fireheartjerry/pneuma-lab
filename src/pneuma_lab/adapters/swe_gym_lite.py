"""SWE-Gym-Lite task rows -> PneumaTrace artifacts (task-only, honest, deterministic).

Emits exactly two frames per trace: a real dataset-derived world-frame and a
minimal synthetic governance-frame. Gold patch / tests / hints are supervision in
the envelope, never psyche-input frames. No agent-trace/memory frames (no agent ran).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import pyarrow.parquet as pq

from pneuma_lab.adapters import envelope as env
from pneuma_lab.schemas import validate

FRAME_SCHEMA_VERSION = "0.1.0"


def normalize_created_at(raw: str) -> str:
    """'2022-12-10 20:23:01' -> ISO-8601 UTC. Raises ValueError if unparseable."""
    dt = datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=timezone.utc
    )
    return dt.isoformat()


def as_list(value) -> list[str]:
    """SWE-Bench test lists arrive as a real list or a JSON-encoded string."""
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


def build_world_frame(row: dict, run_id: str, timestamp: str) -> dict:
    """Real exteroception at t0. Tests are NOT run here; the oracle lives in labels."""
    return {
        "schema_version": FRAME_SCHEMA_VERSION,
        "frame_kind": "world",
        "timestamp": timestamp,
        "run_id": run_id,
        "phase": "preamble",
        "objective": {"text": row.get("problem_statement", "")},
        "repo_state": {
            "head_sha": row["base_commit"],
            "repo": row.get("repo", ""),
        },
        "test_state": {"ran": False, "not_yet_run": True},
    }


def build_governance_frame(run_id: str, timestamp: str) -> dict:
    """Minimal synthetic contract frame. kill_switch 'off' = psyche is a no-op (data)."""
    return {
        "schema_version": FRAME_SCHEMA_VERSION,
        "frame_kind": "governance",
        "timestamp": timestamp,
        "run_id": run_id,
        "verifier_isolation": True,
        "kill_switch_state": "off",
    }


DATASET = "swe-gym"
DATASET_VARIANT = "SWE-Gym-Lite"
BENCHMARK = "swe-gym-lite"
HF_REPO = "SWE-Gym/SWE-Gym-Lite"
ADAPTER = {"name": "swe-gym", "version": "0.1.0"}


class SkipRow(ValueError):
    """Row cannot produce a valid trace (missing/dirty required data)."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_trace(row: dict, hf_revision: str, source_file: str, source_row: int) -> dict:
    """Assemble one PneumaTrace. Raises SkipRow for unbuildable rows."""
    instance_id = row.get("instance_id")
    if not instance_id:
        raise SkipRow("missing instance_id")
    if not row.get("base_commit"):
        raise SkipRow("missing base_commit")
    created_at = row.get("created_at")
    if not created_at:
        raise SkipRow("missing created_at")
    try:
        timestamp = normalize_created_at(created_at)
    except (ValueError, AttributeError) as exc:
        raise SkipRow(f"unparseable created_at: {created_at!r}") from exc

    ids = env.derive_ids(DATASET, instance_id, hf_revision)
    world = build_world_frame(row, ids["run_id"], timestamp)
    governance = build_governance_frame(ids["run_id"], timestamp)

    gold_patch = row.get("patch") or ""
    test_patch = row.get("test_patch") or ""
    hints_text = row.get("hints_text") or ""
    fail_to_pass = as_list(row.get("FAIL_TO_PASS"))
    pass_to_pass = as_list(row.get("PASS_TO_PASS"))

    trace = {
        "schema_version": "0.1.0",
        "trace_id": ids["trace_id"],
        "run_id": ids["run_id"],
        "adapter": dict(ADAPTER),
        "provenance": {
            "dataset": DATASET,
            "dataset_variant": DATASET_VARIANT,
            "source_id": instance_id,
            "hf_repo": HF_REPO,
            "hf_revision": hf_revision,
            "source_file": source_file,
            "source_row": source_row,
        },
        "build": {
            "deterministic": True,
            "content_hash": "",
            "generated_from": ["dataset", "instance_id", "hf_revision"],
            "frame_sources": {
                "world-frame": "dataset-derived",
                "governance-frame": "synthetic-contract-minimum",
            },
        },
        "privacy": {"status": "clean", "pii_scanned": False, "redactions": []},
        "labels": {
            "instance_id": instance_id,
            "benchmark": BENCHMARK,
            "repo": row.get("repo", ""),
            "language": "python",
            "split": "train",
            "task_family": "issue-resolution",
            "has_patch": bool(gold_patch),
            "has_tests": bool(test_patch or fail_to_pass or pass_to_pass),
            "has_trajectory": False,
        },
        "oracle": {
            "kind": "test-based",
            "fail_to_pass": fail_to_pass,
            "pass_to_pass": pass_to_pass,
        },
        "reference_supervision": {
            "gold_patch": gold_patch,
            "gold_patch_sha256": _sha256(gold_patch),
            "test_patch": test_patch,
            "test_patch_sha256": _sha256(test_patch),
            "hints_text": hints_text,
        },
        "frames": [world, governance],
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
        "source_id": labels["instance_id"],
        "repo": labels["repo"],
        "split": labels["split"],
        "benchmark": labels["benchmark"],
        "has_patch": labels["has_patch"],
        "has_tests": labels["has_tests"],
        "has_trajectory": labels["has_trajectory"],
        "num_frames": len(trace["frames"]),
        "frame_kinds": ["world-frame", "governance-frame"],
        "oracle_kind": trace["oracle"]["kind"],
        "privacy_status": trace["privacy"]["status"],
        "validation_status": trace["validation"]["status"],
        "content_hash": trace["build"]["content_hash"],
    }


def _jsonl(objs: list[dict]) -> str:
    return "".join(env.canonical_json(o) + "\n" for o in objs)


def run(rows, hf_revision: str, source_file: str) -> dict[str, str]:
    """Build all traces; return the four output files as canonical strings."""
    indexed = sorted(enumerate(rows), key=lambda p: str(p[1].get("instance_id", "")))
    valid, invalid, skipped = [], [], []
    for source_row, row in indexed:
        try:
            trace = build_trace(row, hf_revision, source_file, source_row)
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
        if frame_errs or env_errs:
            trace["validation"]["status"] = "invalid"
            invalid.append(
                {
                    "trace_id": trace["trace_id"],
                    "source_id": trace["provenance"]["source_id"],
                    "errors": {"envelope": env_errs, "frames": frame_errs},
                    "trace": trace,
                }
            )
        else:
            valid.append(trace)

    traces_str = _jsonl(valid)
    invalid_str = _jsonl(invalid)
    index_str = _jsonl([_index_row(t) for t in valid])

    def present(field):
        return sum(1 for t in valid if t["reference_supervision"].get(field))

    report = {
        "adapter_report_schema_version": ADAPTER_REPORT_SCHEMA_VERSION,
        "adapter": dict(ADAPTER),
        "dataset": DATASET,
        "hf_repo": HF_REPO,
        "hf_revision": hf_revision,
        "counts": {
            "source_rows": len(rows),
            "traces_emitted": len(valid) + len(invalid),
            "valid": len(valid),
            "invalid": len(invalid),
            "skipped": len(skipped),
        },
        "frame_validation": {
            "world-frame": {"valid": len(valid), "invalid": len(invalid)},
            "governance-frame": {"valid": len(valid), "invalid": len(invalid)},
        },
        "oracle_coverage": {
            "fail_to_pass_present": sum(
                1 for t in valid if t["oracle"]["fail_to_pass"]
            ),
            "pass_to_pass_present": sum(
                1 for t in valid if t["oracle"]["pass_to_pass"]
            ),
            "gold_patch_present": present("gold_patch"),
            "test_patch_present": present("test_patch"),
            "hints_present": present("hints_text"),
        },
        "ordering": {"emission_sort_key": "instance_id", "source_row_preserved": True},
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

# Fields the adapter reads; the fixture keeps exactly these (minimum needed).
SOURCE_FIELDS = (
    "instance_id",
    "repo",
    "base_commit",
    "version",
    "created_at",
    "problem_statement",
    "patch",
    "test_patch",
    "hints_text",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
)


def read_lite_parquet(path: str) -> list[dict]:
    """Read the raw SWE-Gym-Lite parquet into a list of row dicts."""
    table = pq.read_table(path)
    return table.to_pylist()


def write_outputs(out_dir: str, files: dict[str, str]) -> None:
    """Write the four canonical strings to out_dir (created if needed)."""
    os.makedirs(out_dir, exist_ok=True)
    for name in OUTPUT_FILES:
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(files[name])


DEFAULT_INPUT = (
    "C:/pneuma-data/raw/swe-gym/SWE-Gym-Lite/data/train-00000-of-00001.parquet"
)
DEFAULT_OUT = "C:/pneuma-data/processed/swe-gym/lite"
DEFAULT_HF_REVISION = "f70b1a29ab120eb0a0ee7a1deb029825e735b2b0"
FIXTURE_DIR = os.path.join("fixtures", "adapters", "swe_gym_lite")
FIXTURE_SOURCE_FILE = "fixtures/adapters/swe_gym_lite/input_rows.jsonl"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pneuma_lab.adapters.swe_gym_lite")
    p.add_argument("--input", default=DEFAULT_INPUT)
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


def _fixture_rows() -> list[dict]:
    with open(os.path.join(FIXTURE_DIR, "input_rows.jsonl"), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    if args.emit_fixture or args.update_fixture:
        files = run(
            _fixture_rows(),
            hf_revision=DEFAULT_HF_REVISION,
            source_file=FIXTURE_SOURCE_FILE,
        )
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

    rows = read_lite_parquet(args.input)
    files = run(rows, hf_revision=args.hf_revision, source_file=args.input)
    write_outputs(args.out, files)
    report = json.loads(files["adapter_report.json"])
    print(f"wrote {report['counts']['valid']} traces to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

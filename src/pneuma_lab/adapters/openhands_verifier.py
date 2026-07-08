"""OpenHands-Verifier-Trajectories rows -> trajectory-bearing PneumaTrace v0.2.

Each source row is one REAL recorded verifier run over a SWE-Gym interaction
log: ``messages`` (OpenAI-style chat) and ``resolved`` (the verifier label).
The source carries NO ``instance_id``, NO ``run_id``, and NO ``test_result``;
identity is the source coordinate (policy variant + row index) and is never
guessed or recovered. The adapter emits:

    world-frame        real exteroception at t0 (the verification request the
                       verifier saw; repo unknown, recorded as ""),
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
DATASET_VARIANT = "OpenHands-Verifier-Trajectories"
BENCHMARK = "swe-gym"
HF_REPO = "SWE-Gym/OpenHands-Verifier-Trajectories"
TASK_HF_REPO = "SWE-Gym/SWE-Gym"
ADAPTER = {"name": "openhands-verifier", "version": "0.1.0"}
SOURCE_KIND = "openai-chat-messages"

POLICY_VARIANTS = ("mixture", "offpolicy", "onpolicy")

# The source has no instance_id: joining against the SWE-Gym task table is
# impossible, and this adapter records that honestly instead of guessing.
TASK_JOIN_REASON = "no instance_id column in source"


class SkipRow(ValueError):
    """Row cannot produce a valid trace (missing/dirty required data)."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def policy_variant_from_path(path: str) -> str:
    """Parse the policy variant from a source file name (``train.<variant>-*``)."""
    name = os.path.basename(path)
    for variant in POLICY_VARIANTS:
        if f".{variant}-" in name or f".{variant}." in name:
            return variant
    raise ValueError(f"cannot determine policy variant from file name: {name!r}")


def build_world_frame(objective_text: str, run_id: str) -> dict:
    """Real exteroception at t0: the verification request the verifier saw."""
    return {
        "schema_version": FRAME_SCHEMA_VERSION,
        "frame_kind": "world",
        "timestamp": traj.synthetic_timestamp(0),
        "timestamp_provenance": traj.TIMESTAMP_PROVENANCE,
        "run_id": run_id,
        "phase": "preamble",
        "objective": {"text": objective_text},
        "repo_state": {"repo": ""},
        "test_state": {"ran": False, "not_yet_run": True},
    }


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


def _outcome_block(row: dict) -> dict:
    """Observed verifier label: the resolved boolean, nothing else exists."""
    return {
        "kind": "swe-gym-verifier-label",
        "resolved": bool(row.get("resolved")),
    }


def build_trace(
    row: dict,
    policy_variant: str,
    hf_revision: str,
    source_file: str,
    source_row: int,
) -> dict:
    """Assemble one trajectory-bearing PneumaTrace. Raises SkipRow when unbuildable."""
    if row.get("resolved") is None:
        raise SkipRow("missing resolved label")
    try:
        extraction = traj.extract_agent_trace_frames(
            row.get("messages"),
            run_id="",  # run_id patched after id derivation
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise SkipRow(f"unusable messages: {exc}") from exc

    source_id = f"verifier::{policy_variant}::{source_row}"
    ids = env.derive_ids(DATASET, source_id, hf_revision)
    for frame in extraction["frames"]:
        frame["run_id"] = ids["run_id"]

    objective_text, redactions = traj.redact_text(extraction["first_user_text"])
    world = build_world_frame(objective_text, ids["run_id"])
    governance = build_governance_frame(ids["run_id"])

    trace = {
        "schema_version": ENVELOPE_VERSION,
        "trace_id": ids["trace_id"],
        "run_id": ids["run_id"],
        "adapter": dict(ADAPTER),
        "provenance": {
            "dataset": DATASET,
            "dataset_variant": DATASET_VARIANT,
            "source_id": source_id,
            "hf_repo": HF_REPO,
            "hf_revision": hf_revision,
            "source_file": source_file,
            "source_row": source_row,
            "task_join": {
                "hf_repo": TASK_HF_REPO,
                "joined": False,
                "reason": TASK_JOIN_REASON,
            },
        },
        "build": {
            "deterministic": True,
            "content_hash": "",
            "generated_from": [
                "dataset",
                "verifier::policy_variant::source_row",
                "hf_revision",
            ],
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
            "benchmark": BENCHMARK,
            "repo": "",
            "language": "python",
            "split": "train",
            "task_family": "trajectory-verification",
            "policy_variant": policy_variant,
            "has_patch": False,
            "has_tests": False,
            "has_trajectory": True,
            "resolved": bool(row.get("resolved")),
        },
        "oracle": {"kind": "test-based", "fail_to_pass": [], "pass_to_pass": []},
        "reference_supervision": {},
        "trajectory": {
            "present": True,
            "source_kind": SOURCE_KIND,
            "agent_run_id": source_id,  # source coordinate; no run id exists
            "policy_variant": policy_variant,
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
        "policy_variant": labels["policy_variant"],
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
    batches: list[tuple[str, str, list[dict]]],
    hf_revision: str,
) -> dict[str, str]:
    """Build all traces from (policy_variant, source_file, rows) batches."""
    flat = [
        (variant, i, sf, row)
        for variant, sf, rows in batches
        for i, row in enumerate(rows)
    ]
    flat.sort(key=lambda t: (t[0], t[1], t[2]))

    valid, invalid, skipped = [], [], []
    for policy_variant, source_row, source_file, row in flat:
        try:
            trace = build_trace(
                row,
                policy_variant,
                hf_revision,
                source_file,
                source_row,
            )
        except SkipRow as exc:
            skipped.append(
                {
                    "source_id": f"verifier::{policy_variant}::{source_row}",
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

    total_rows = sum(len(rows) for _, _, rows in batches)
    redaction_totals = traj.merge_redactions(
        [t["privacy"]["redactions"] for t in valid]
    )
    by_variant: dict[str, dict] = {}
    for t in valid:
        variant = t["labels"]["policy_variant"]
        bucket = by_variant.setdefault(
            variant, {"valid": 0, "resolved_true": 0, "resolved_false": 0}
        )
        bucket["valid"] += 1
        bucket["resolved_true" if t["labels"]["resolved"] else "resolved_false"] += 1
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
            "traces_with_task_join": 0,
            "traces_missing_task_join": len(valid),
            "total_agent_steps": sum(t["trajectory"]["num_agent_steps"] for t in valid),
            "resolved_true": sum(1 for t in valid if t["labels"]["resolved"]),
            "resolved_false": sum(1 for t in valid if not t["labels"]["resolved"]),
            "by_policy_variant": {k: by_variant[k] for k in sorted(by_variant)},
        },
        "privacy": {"redaction_totals": redaction_totals},
        "ordering": {
            "emission_sort_key": "policy_variant, source_row",
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


def read_parquet_rows(path: str) -> list[dict]:
    import pyarrow.parquet as pq

    return pq.read_table(path).to_pylist()


def write_outputs(out_dir: str, files: dict[str, str]) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for name in OUTPUT_FILES:
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(files[name])


DEFAULT_INPUTS = tuple(
    "C:/pneuma-data/raw/swe-gym/OpenHands-Verifier-Trajectories/data/"
    f"train.{variant}-00000-of-00001.parquet"
    for variant in POLICY_VARIANTS
)
DEFAULT_OUT = "C:/pneuma-data/processed/swe-gym/openhands-verifier"
DEFAULT_HF_REVISION = "d47f6cab996d3a5f7ba517c0be57595f4f6201ce"
FIXTURE_DIR = os.path.join("fixtures", "adapters", "openhands_verifier")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pneuma_lab.adapters.openhands_verifier")
    p.add_argument("--input", nargs="+", default=list(DEFAULT_INPUTS))
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


def _fixture_batches() -> list[tuple[str, str, list[dict]]]:
    """Fixture rows carry ``policy_variant`` explicitly; production parses filenames."""
    grouped: dict[str, list[dict]] = {}
    for row in _fixture_jsonl("input_rows.jsonl"):
        grouped.setdefault(row["policy_variant"], []).append(row)
    return [
        (variant, "fixtures/adapters/openhands_verifier/input_rows.jsonl", rows)
        for variant, rows in sorted(grouped.items())
    ]


def _fixture_files() -> dict[str, str]:
    return run(_fixture_batches(), hf_revision=DEFAULT_HF_REVISION)


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

    batches = [
        (policy_variant_from_path(path), path, read_parquet_rows(path))
        for path in args.input
    ]
    files = run(batches, hf_revision=args.hf_revision)
    write_outputs(args.out, files)
    report = json.loads(files["adapter_report.json"])
    print(f"wrote {report['counts']['valid']} traces to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

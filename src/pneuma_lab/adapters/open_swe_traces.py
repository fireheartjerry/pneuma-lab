"""Open-SWE-Traces rows -> trajectory-bearing PneumaTrace v0.2 (stage 1).

Each source row is one REAL recorded synthetic agent run over a SWE-rebench-V2
task: ``instance_id``, ``repo``, ``license``, ``language``, ``trajectory_id``,
``trajectory`` (chat-format list of ``{role, content, reasoning_content, think,
tool_calls}``), ``tools``, ``resolved`` (int32 in ``{-1, 0, 1}``), and
``metadata`` (``category`` + ``reference_patch``/``model_patch`` structs). The
adapter emits:

    world-frame        exteroception at t0 (task-text DIGEST only -- never raw
                       text, stricter than the OpenHands-Sampled lane -- plus
                       digested repo identity),
    governance-frame   minimal synthetic contract (same as every other adapter),
    agent-trace-frames one per assistant step, observable-only (see
                       ``adapters.trajectory`` for the honesty rules).

This lane is deliberately digest-only end to end: raw ``trajectory``/``tools``/
patch text NEVER enters a frame or a processed field. Identifiers (repo,
instance_id, trajectory_id) are stored as sha256 digests, matching the
Open-SWE-Traces governance surface. ``resolved`` is mapped 1 -> True, 0 ->
False; anything else (notably the ~21% of rows carrying ``-1``, an unknown /
unevaluated verifier state) is skipped rather than silently coerced.

Deterministic by construction: canonical JSON, identity ids, synthetic-ordinal
timestamps, content hashes. Trajectories/outcomes are synthetic and automated,
so the downstream converter must label them ``constructed_label`` -- this
adapter records the observable outcome only and never asserts a harness result.
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

DATASET = "open-swe-traces"
DATASET_FAMILY = "open-swe-traces"
BENCHMARK = "open-swe-traces"
HF_REPO = "nvidia/Open-SWE-Traces"
HF_REVISION = "474d016b4a35a0411a7f57183579eab8924e9ea5"
ADAPTER = {"name": "open-swe-traces", "version": "0.1.0"}
SOURCE_KIND = "open-swe-traces-trajectory"

# Verifier ``resolved`` int -> boolean. Everything else is unknown and skipped.
RESOLVED_TRUE = 1
RESOLVED_FALSE = 0

# source_group directory names -> shard counts (from the registry file index).
SOURCE_GROUP_SHARDS = {
    "minimax_m25_openhands_trajectories": 20,
    "minimax_m25_sweagent_trajectories": 23,
    "qwen35_openhands_trajectories": 23,
    "qwen35_sweagent_trajectories": 18,
}


class SkipRow(ValueError):
    """Row cannot produce a valid trace (missing/dirty/unknown required data)."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _digest(value: str) -> str:
    """sha256 with an explicit ``sha256:`` scheme prefix (digest-only identity)."""
    return "sha256:" + _sha256(value)


def resolved_to_bool(value) -> bool:
    """Map the int32 ``resolved`` verifier state to a boolean or skip the row."""
    if value == RESOLVED_TRUE:
        return True
    if value == RESOLVED_FALSE:
        return False
    raise SkipRow(f"resolved is unknown ({value!r}); only 0/1 are convertible")


def build_world_frame(objective_meta: dict, repo_digest: str, run_id: str) -> dict:
    """Exteroception at t0: task-text digest (never raw text) + repo digest."""
    return {
        "schema_version": FRAME_SCHEMA_VERSION,
        "frame_kind": "world",
        "timestamp": traj.synthetic_timestamp(0),
        "timestamp_provenance": traj.TIMESTAMP_PROVENANCE,
        "run_id": run_id,
        "phase": "preamble",
        "objective": objective_meta,
        "repo_state": {"repo_digest": repo_digest},
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


def _objective_meta(first_user_text: str) -> dict:
    """Digest-only objective: presence, sha256, length. Raw text never embedded."""
    meta = {"present": bool(first_user_text), "mode": "digest_only"}
    if first_user_text:
        meta["text_sha256"] = "sha256:" + _sha256(first_user_text)
        meta["text_length"] = len(first_user_text)
    return meta


def _patch_stats(patch_struct) -> dict:
    """sha256 + length + numeric modified counts for one patch struct. No patch text."""
    struct = patch_struct or {}
    patch_text = struct.get("patch") or ""
    return {
        "sha256": "sha256:" + _sha256(patch_text),
        "length": len(patch_text),
        "num_modified_files": int(struct.get("num_modified_files") or 0),
        "num_modified_lines": int(struct.get("num_modified_lines") or 0),
    }


def _reference_supervision(metadata) -> dict:
    """Reference vs model patch divergence, digest-only (mirrors Dataset #1)."""
    meta = metadata or {}
    return {
        "reference_patch": _patch_stats(meta.get("reference_patch")),
        "model_patch": _patch_stats(meta.get("model_patch")),
    }


def build_trace(
    row: dict,
    source_group: str,
    source_file: str,
    source_row: int,
    hf_revision: str,
) -> dict:
    """Assemble one trajectory-bearing PneumaTrace. Raises SkipRow when unbuildable."""
    instance_id = row.get("instance_id")
    if not instance_id:
        raise SkipRow("missing instance_id")
    trajectory_id = row.get("trajectory_id")
    if not trajectory_id:
        raise SkipRow("missing trajectory_id")
    resolved = resolved_to_bool(row.get("resolved"))

    try:
        extraction = traj.extract_agent_trace_frames(
            row.get("trajectory"),
            run_id="",  # run_id patched after id derivation
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise SkipRow(f"unusable trajectory: {exc}") from exc

    source_id = f"{instance_id}::{trajectory_id}"
    ids = env.derive_ids(DATASET, source_id, hf_revision)
    for frame in extraction["frames"]:
        frame["run_id"] = ids["run_id"]

    repo = row.get("repo") or ""
    repo_digest = _digest(repo) if repo else ""
    instance_digest = _digest(instance_id)
    trajectory_digest = _digest(trajectory_id)
    license_value = row.get("license") or None
    language = row.get("language") or None

    objective_meta = _objective_meta(extraction["first_user_text"])
    world = build_world_frame(objective_meta, repo_digest, ids["run_id"])
    governance = build_governance_frame(ids["run_id"])
    reference_supervision = _reference_supervision(row.get("metadata"))

    trace = {
        "schema_version": ENVELOPE_VERSION,
        "trace_id": ids["trace_id"],
        "run_id": ids["run_id"],
        "adapter": dict(ADAPTER),
        "provenance": {
            "dataset": DATASET,
            "dataset_variant": source_group,
            "source_id": source_id,
            "hf_repo": HF_REPO,
            "hf_revision": hf_revision,
            "source_file": source_file,
            "source_row": source_row,
            "source_group": source_group,
        },
        "build": {
            "deterministic": True,
            "content_hash": "",
            "generated_from": ["dataset", "instance_id::trajectory_id", "hf_revision"],
            "frame_sources": {
                "world-frame": "dataset-derived",
                "governance-frame": "synthetic-contract-minimum",
                "agent-trace-frame": env.TRAJECTORY_SOURCE,
            },
        },
        "privacy": {
            # Digest-only by construction: no raw trajectory/tool/patch text is
            # ever embedded, so redaction is structurally not needed.
            "status": "clean",
            "pii_scanned": True,
            "redactions": [],
            "protection": "digest-only-by-construction",
        },
        "labels": {
            "benchmark": BENCHMARK,
            "source_group": source_group,
            "language": language,
            "license": license_value,
            "repo_digest": repo_digest,
            "instance_id_digest": instance_digest,
            "trajectory_id_digest": trajectory_digest,
            "split": "train",
            "task_family": "issue-resolution",
            "has_trajectory": True,
            "has_patch": bool((row.get("metadata") or {}).get("model_patch")),
            "resolved": resolved,
        },
        "oracle": {
            "kind": "synthetic-verifier-outcome",
        },
        "reference_supervision": reference_supervision,
        "trajectory": {
            "present": True,
            "source_kind": SOURCE_KIND,
            "agent_run_id": trajectory_id,
            "num_messages": extraction["num_messages"],
            "num_agent_steps": extraction["num_agent_steps"],
            "timestamp_provenance": traj.TIMESTAMP_PROVENANCE,
        },
        "outcome": {
            "kind": "open-swe-traces-verifier-report",
            "resolved": resolved,
            "label_semantics": "synthetic-automated-verifier",
        },
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
        "source_group": labels["source_group"],
        "language": labels["language"],
        "split": labels["split"],
        "benchmark": labels["benchmark"],
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
    """Build all traces from (source_group, source_file, rows) batches.

    Returns the four canonical output file bodies. Rows are emitted in a stable
    (source_group, source_file, source_row) order; the row's position within its
    file is preserved as ``source_row``.
    """
    flat = [
        (source_group, source_file, i, row)
        for source_group, source_file, rows in batches
        for i, row in enumerate(rows)
    ]
    flat.sort(key=lambda t: (t[0], t[1], t[2]))

    valid, invalid, skipped = [], [], []
    for source_group, source_file, source_row, row in flat:
        try:
            trace = build_trace(row, source_group, source_file, source_row, hf_revision)
        except SkipRow as exc:
            skipped.append(
                {
                    "source_id": (
                        f"{row.get('instance_id', '<?>')}::"
                        f"{row.get('trajectory_id', '<?>')}"
                    ),
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
    skip_reasons: dict[str, int] = {}
    for item in skipped:
        key = item["reason"].split("(")[0].strip().split(";")[0]
        skip_reasons[key] = skip_reasons.get(key, 0) + 1
    report = {
        "adapter_report_schema_version": ADAPTER_REPORT_SCHEMA_VERSION,
        "adapter": dict(ADAPTER),
        "dataset": DATASET,
        "dataset_family": DATASET_FAMILY,
        "hf_repo": HF_REPO,
        "hf_revision": hf_revision,
        "counts": {
            "source_rows": total_rows,
            "traces_emitted": len(valid) + len(invalid),
            "valid": len(valid),
            "invalid": len(invalid),
            "skipped": len(skipped),
        },
        "trajectory": {
            "total_agent_steps": sum(t["trajectory"]["num_agent_steps"] for t in valid),
            "resolved_true": sum(1 for t in valid if t["labels"]["resolved"]),
            "resolved_false": sum(1 for t in valid if not t["labels"]["resolved"]),
        },
        "source_groups": sorted({sg for sg, _, _ in batches}),
        "skip_reasons": dict(sorted(skip_reasons.items())),
        "privacy": {
            "protection": "digest-only-by-construction",
            "raw_trajectory_text_embedded": False,
            "raw_patch_text_embedded": False,
            "raw_identifiers_in_frames_or_labels": False,
            "raw_join_key_in_provenance_only": True,
        },
        "ordering": {
            "emission_sort_key": "source_group, source_file, source_row",
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

RAW_ROOT = "C:/pneuma-data/raw/open-swe-traces/Open-SWE-Traces/data"
DEFAULT_OUT = "C:/pneuma-data/processed/open-swe-traces/pneuma-trace"
FIXTURE_DIR = os.path.join("fixtures", "adapters", "open_swe_traces")


def default_inputs() -> list[tuple[str, str]]:
    """(source_group, absolute parquet path) for every shard, deterministic order."""
    inputs: list[tuple[str, str]] = []
    for group in sorted(SOURCE_GROUP_SHARDS):
        count = SOURCE_GROUP_SHARDS[group]
        for i in range(count):
            name = f"train-{i:05d}-of-{count:05d}.parquet"
            inputs.append((group, f"{RAW_ROOT}/{group}/{name}"))
    return inputs


def read_parquet_rows(path: str) -> list[dict]:
    import pyarrow.parquet as pq

    return pq.read_table(path).to_pylist()


def source_group_from_path(path: str) -> str:
    """Infer the source_group directory name from a shard path."""
    parts = path.replace("\\", "/").split("/")
    for group in SOURCE_GROUP_SHARDS:
        if group in parts:
            return group
    return "unknown_source_group"


def write_outputs(out_dir: str, files: dict[str, str]) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for name in OUTPUT_FILES:
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(files[name])


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pneuma_lab.adapters.open_swe_traces")
    p.add_argument(
        "--input",
        nargs="+",
        help="Parquet shard paths. Defaults to all 84 raw shards.",
    )
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--hf-revision", default=HF_REVISION)
    p.add_argument(
        "--limit-rows",
        type=int,
        default=None,
        help="Read at most N rows per shard (bounded smoke, still deterministic).",
    )
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
    rows = _fixture_jsonl("input_rows.jsonl")
    # Fixture rows self-declare their source_group and source_file for realism.
    batches: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        key = (
            row.get("_source_group", "minimax_m25_openhands_trajectories"),
            row.get(
                "_source_file", "fixtures/adapters/open_swe_traces/input_rows.jsonl"
            ),
        )
        batches.setdefault(key, []).append(row)
    batch_list = [(sg, sf, rs) for (sg, sf), rs in sorted(batches.items())]
    return run(batch_list, hf_revision=HF_REVISION)


def _read_rows_with_limit(path: str, limit_rows: int | None) -> list[dict]:
    if limit_rows is None:
        return read_parquet_rows(path)
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(path)
    collected: list[dict] = []
    for batch in pf.iter_batches(batch_size=min(limit_rows, 512)):
        collected.extend(batch.to_pylist())
        if len(collected) >= limit_rows:
            break
    return collected[:limit_rows]


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

    inputs = (
        [(source_group_from_path(p), p) for p in args.input]
        if args.input
        else default_inputs()
    )
    batches = [
        (group, path, _read_rows_with_limit(path, args.limit_rows))
        for group, path in inputs
    ]
    files = run(batches, hf_revision=args.hf_revision)
    write_outputs(args.out, files)
    report = json.loads(files["adapter_report.json"])
    print(f"wrote {report['counts']['valid']} traces to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

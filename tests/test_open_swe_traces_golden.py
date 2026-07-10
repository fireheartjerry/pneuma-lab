from __future__ import annotations

import os

from pneuma_lab.adapters import open_swe_traces as a

FIXTURE = os.path.join("fixtures", "adapters", "open_swe_traces")


def test_golden_byte_match() -> None:
    files = a._fixture_files()
    for name in a.OUTPUT_FILES:
        want = open(os.path.join(FIXTURE, "golden", name), encoding="utf-8").read()
        assert files[name] == want, f"golden drift in {name}"


def test_two_run_determinism() -> None:
    assert a._fixture_files() == a._fixture_files()


def test_emit_fixture_passes_when_golden_current() -> None:
    assert a.main(["--emit-fixture"]) == 0


def test_emit_fixture_detects_drift(tmp_path, monkeypatch) -> None:
    import shutil

    tmp_fix = tmp_path / "open_swe_traces"
    shutil.copytree(FIXTURE, tmp_fix)
    (tmp_fix / "golden" / "adapter_report.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(a, "FIXTURE_DIR", str(tmp_fix))
    assert a.main(["--emit-fixture"]) == 1


def _fixture_rows_by_group() -> dict:
    import json

    groups: dict = {}
    with open(os.path.join(FIXTURE, "input_rows.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                groups.setdefault(row["_source_group"], []).append(row)
    return groups


def test_streaming_matches_in_memory_run_byte_for_byte(tmp_path) -> None:
    """run_streaming (one shard at a time) == run() over the same shard defs.

    Same (source_group, source_file) per shard, so provenance/content hashes
    match; this proves the memory-bounded path is byte-identical to the
    in-memory path, not that it matches the differently-keyed golden fixture.
    """
    groups = _fixture_rows_by_group()
    # Distinct source_file per shard so both paths agree on provenance.
    shards = [(g, f"shard/{g}.parquet", rows) for g, rows in sorted(groups.items())]
    reader = {path: rows for _, path, rows in shards}

    in_memory = a.run(
        [(g, path, rows) for g, path, rows in shards], hf_revision=a.HF_REVISION
    )
    out = tmp_path / "stream"
    report = a.run_streaming(
        [(g, path) for g, path, _ in shards],
        hf_revision=a.HF_REVISION,
        out_dir=str(out),
        read_rows=lambda path: reader[path],
    )
    assert report["counts"]["valid"] == 2
    assert report["mode"] == "streaming"
    assert (out / "pneuma_traces.jsonl").read_text(encoding="utf-8") == in_memory[
        "pneuma_traces.jsonl"
    ]
    assert (out / "trace_index.jsonl").read_text(encoding="utf-8") == in_memory[
        "trace_index.jsonl"
    ]
    # Aggregate report counts agree with the in-memory report.
    import json

    mem_report = json.loads(in_memory["adapter_report.json"])
    assert report["counts"] == mem_report["counts"]
    assert report["trajectory"] == mem_report["trajectory"]
    assert report["traces_file_sha256"] == mem_report["traces_file_sha256"]

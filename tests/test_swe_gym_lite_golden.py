from __future__ import annotations

import json
import os

from pneuma_lab.adapters import swe_gym_lite as swe

FIXTURE = os.path.join("fixtures", "adapters", "swe_gym_lite")


def _fixture_rows():
    with open(os.path.join(FIXTURE, "input_rows.jsonl"), encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def test_golden_byte_match():
    files = swe.run(
        _fixture_rows(),
        hf_revision="f70b1a29ab120eb0a0ee7a1deb029825e735b2b0",
        source_file="fixtures/adapters/swe_gym_lite/input_rows.jsonl",
    )
    for name in swe.OUTPUT_FILES:
        want = open(os.path.join(FIXTURE, "golden", name), encoding="utf-8").read()
        assert files[name] == want, f"golden drift in {name}"


def test_two_run_determinism():
    rows = _fixture_rows()
    a = swe.run(rows, hf_revision="rev", source_file="f")
    b = swe.run(rows, hf_revision="rev", source_file="f")
    assert a == b


def test_emit_fixture_passes_when_golden_current():
    # committed golden matches the adapter's current output
    assert swe.main(["--emit-fixture"]) == 0


def test_emit_fixture_detects_drift(tmp_path, monkeypatch):
    # copy the fixture to a temp dir, corrupt a golden file, point the CLI there:
    # --emit-fixture must return 1 (nonzero) without touching the committed golden.
    import shutil

    tmp_fix = tmp_path / "swe_gym_lite"
    shutil.copytree(FIXTURE, tmp_fix)
    (tmp_fix / "golden" / "adapter_report.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(swe, "FIXTURE_DIR", str(tmp_fix))
    assert swe.main(["--emit-fixture"]) == 1

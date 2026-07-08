from __future__ import annotations

import os

from pneuma_lab.adapters import openhands_sampled as oh

FIXTURE = os.path.join("fixtures", "adapters", "openhands_sampled")


def test_golden_byte_match():
    files = oh._fixture_files()
    for name in oh.OUTPUT_FILES:
        want = open(os.path.join(FIXTURE, "golden", name), encoding="utf-8").read()
        assert files[name] == want, f"golden drift in {name}"


def test_two_run_determinism():
    assert oh._fixture_files() == oh._fixture_files()


def test_emit_fixture_passes_when_golden_current():
    assert oh.main(["--emit-fixture"]) == 0


def test_emit_fixture_detects_drift(tmp_path, monkeypatch):
    import shutil

    tmp_fix = tmp_path / "openhands_sampled"
    shutil.copytree(FIXTURE, tmp_fix)
    (tmp_fix / "golden" / "adapter_report.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(oh, "FIXTURE_DIR", str(tmp_fix))
    assert oh.main(["--emit-fixture"]) == 1

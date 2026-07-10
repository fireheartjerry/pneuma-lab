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

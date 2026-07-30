"""Analysis-freeze boundary tests."""

from __future__ import annotations

import pytest

from pneuma_lab.resampling_null.errors import RecordValidationError


pytestmark = pytest.mark.milestone


def test_freeze_module_exposes_the_public_constructor() -> None:
    from pneuma_lab.resampling_null.freeze import freeze_analysis

    assert callable(freeze_analysis)


def test_snapshot_rejects_duplicate_and_escape_destinations(tmp_path) -> None:
    from pneuma_lab.resampling_null.freeze import snapshot_sources

    source = tmp_path / "input.json"
    source.write_text("{}", encoding="utf-8")
    run_root = tmp_path / "run"
    run_root.mkdir()
    with pytest.raises((ValueError, RecordValidationError), match="duplicate"):
        snapshot_sources(
            run_root,
            {"one": source, "two": source},
            relative_paths={
                "one": "sources/analysis-freeze/a",
                "two": "sources/analysis-freeze/a",
            },
        )
    with pytest.raises((ValueError, RecordValidationError), match="escapes"):
        snapshot_sources(
            run_root,
            {"one": source},
            relative_paths={"one": "../escape"},
        )

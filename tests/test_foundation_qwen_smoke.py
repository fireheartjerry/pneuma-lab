"""Opt-in real pinned Qwen 2B no-gradient dry-run smoke test."""

from __future__ import annotations

from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from pneuma_lab.foundation.dry_run import DryRunRequest, run_no_gradient_dry_run
from pneuma_lab.foundation.specs import MODEL_SPECS


_REPO_ROOT = Path(__file__).resolve().parents[1]
_CACHE_ROOT = _REPO_ROOT / "build" / "foundation" / "cache"
_SNAPSHOT = _CACHE_ROOT / "models" / "2b" / MODEL_SPECS["2b"].revision


@pytest.mark.qwen_smoke
def test_pinned_2b_no_gradient_dry_run_smoke(tmp_path: Path) -> None:
    if not (_SNAPSHOT / "pneuma-snapshot-receipt.json").is_file():
        pytest.skip("pinned 2B snapshot is not cached")
    report = run_no_gradient_dry_run(
        DryRunRequest(
            model_key="2b",
            cache_root=_CACHE_ROOT,
            output_root=tmp_path / "dry-run",
            stage="qwen_smoke",
        )
    )
    assert report["report_kind"] == "pneuma_foundation_no_gradient_dry_run"
    assert report["model_revision"] == MODEL_SPECS["2b"].revision
    assert report["optimizer_constructed"] is False
    assert report["backward_called"] is False
    assert report["gradient_tensor_count"] == 0
    assert report["parity"]["case_names"] == [
        "cached",
        "continued",
        "explicit_reset",
        "fresh",
        "packed_reset",
    ]
    assert report["junction"]["layer_indices"] == [19]

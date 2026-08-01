from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_script():
    path = ROOT / "scripts" / "build_placebo_review_spec.py"
    spec = importlib.util.spec_from_file_location("build_placebo_review_spec", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_step14_requires_production_execution_surface_receipt() -> None:
    module = _load_script()
    receipts = {receipt_id: relative for receipt_id, _, relative, _ in module.REQUIRED_RECEIPTS}
    assert receipts["production-execution-surface"] == (
        "build/research/neurips-2026-workshop/phase-b-evidence/production-execution-surface.json"
    )
    assert len(receipts) == 6

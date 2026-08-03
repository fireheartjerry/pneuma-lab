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
    assert receipts["interruption-recovery"].endswith("/interruption-recovery.json")
    assert receipts["cross-platform-portability"].endswith(
        "/cross-platform-portability.json"
    )
    assert len(receipts) == 8


def test_step14_spec_builder_fails_closed_when_a_receipt_is_missing(
    tmp_path, capsys, monkeypatch
) -> None:
    module = _load_script()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", lambda *args: "0" * 40)

    declared = list(module.INPUTS) + [
        (slot, relative, description)
        for _, slot, relative, description in module.REQUIRED_RECEIPTS
    ]
    for _, relative, _ in declared:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

    missing = "build/research/neurips-2026-workshop/phase-b-evidence/production-execution-surface.json"
    (tmp_path / missing).unlink()

    assert module.main() == 2
    captured = capsys.readouterr()
    assert "missing declared inputs" in captured.err
    assert missing in captured.err

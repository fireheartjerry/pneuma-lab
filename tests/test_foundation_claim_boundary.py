"""Foundation/runtime delivery cannot import the archived level scorer."""

from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.foundation.evaluation import evaluate_run
from pneuma_lab.foundation.reports import materialize_reports


ROOT = Path(__file__).resolve().parents[1]


def test_foundation_package_cannot_import_legacy_evidence_or_level_scorers() -> None:
    forbidden = (
        "pneuma_lab.evals",
        "consciousness_evidence",
        "consciousness-evidence",
        "level4_scoring",
        "level5",
        "level6",
    )
    for path in sorted((ROOT / "src/pneuma_lab/foundation").glob("*.py")):
        text = path.read_text(encoding="utf-8").casefold()
        for token in forbidden:
            assert token not in text, f"{path.name} imports claim surface {token!r}"


def test_evaluation_and_report_modules_stay_scorer_free_and_torch_free() -> None:
    for name in ("evaluation.py", "reports.py"):
        text = (ROOT / "src/pneuma_lab/foundation" / name).read_text(encoding="utf-8")
        assert "import torch" not in text, f"{name} must stay torch-free"
        assert "from torch" not in text, f"{name} must stay torch-free"
        assert "pneuma_lab.evals" not in text, f"{name} imports the level scorer"
        assert "pneuma_lab.psyche" not in text, f"{name} imports the psyche"


def test_materialized_reports_stay_claim_bounded(tmp_path: Path) -> None:
    manifest = {
        "run_id": "claim-boundary-run",
        "status": "completed",
        "curriculum": {"stage": "100k", "lane_weights": {"swe-verified": 1.0}},
        "training": {"learning_rate": 0.0001},
        "progress": {"tokens_per_second": 55.5},
        "latency": {
            "base_p50_ms": 80.0,
            "base_p95_ms": 100.0,
            "core_p50_ms": 90.0,
            "core_p95_ms": 120.0,
        },
        "telemetry": {"peak_process_vram_gb": 6.9},
        "limits": {"max_vram_gb": 7.5, "max_ram_gb": 24.0, "max_gpu_temp_c": 85.0},
        "checkpoints": {"last_path": None, "lineage": []},
        "termination_reason": "completed",
        "budget": {"paid_compute_usd": 0.0, "cloud_jobs_used": 0},
    }
    evaluation_report = evaluate_run(
        manifest,
        validation_batches=({"validation_loss": 2.0, "token_count": 100},),
        estimated_flops_overhead=0.1,
    )
    paths = materialize_reports(manifest, evaluation_report, output_root=tmp_path)
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in paths.values()
    ).casefold()
    for forbidden in (
        "level 5",
        "level 6",
        "is conscious",
        "phenomenal consciousness",
    ):
        assert forbidden not in combined
    for path in paths.values():
        assert '"no_consciousness_claim": true' in path.read_text(encoding="utf-8")


def test_legacy_methodology_is_explicitly_non_authoritative() -> None:
    status = json.loads((ROOT / "docs/project-status.json").read_text(encoding="utf-8"))
    legacy = status["evidence"]["legacy_methodology"]
    assert legacy == {
        "archived": True,
        "authoritative": False,
        "delivery_gate": False,
        "learned_subject_import_allowed": False,
        "archive_ref": "docs/archive/consciousness-level-methodology.md",
    }

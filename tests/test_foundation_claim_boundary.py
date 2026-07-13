"""Foundation/runtime delivery cannot import the archived level scorer."""

from __future__ import annotations

import json
from pathlib import Path


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

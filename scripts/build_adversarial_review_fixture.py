"""Build the synthetic adversarial-review fixture.

The fixture is deliberately NON-SCIENTIFIC. It reviews a made-up toy document
about a fictional widget study so that exercising the review machinery can
never be mistaken for reviewing, endorsing, or producing evidence about the
PLACEBO Trial. Its only job is to make every code path — grounding, downgrade,
conflict detection, dissent preservation, override, sealing — reachable from a
test that runs offline in milliseconds.

Regenerate after changing a reviewer mandate (which changes its prompt digest):

    python scripts/build_adversarial_review_fixture.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pneuma_lab.adversarial_review.canonical import (  # noqa: E402
    canonical_json,
    digest_bytes,
    digest_file,
)
from pneuma_lab.adversarial_review.roles import ROLES_BY_ID  # noqa: E402

FIXTURE = REPO_ROOT / "fixtures" / "adversarial_review" / "synthetic_campaign"
ROOT = FIXTURE / "root"
TRANSCRIPTS = FIXTURE / "transcripts"

TOY_MANUSCRIPT = """% synthetic fixture -- fictional study, not PLACEBO
\\title{Widget Torque and Assembly Yield: A Toy Study}

\\section{Claims}
C1. Applying the torque protocol raises assembly yield.
C2. The measured yield gain is at least four percentage points.
C3. The protocol has been evaluated on two independent widget lines.

\\section{Method}
Two widget lines were sampled. Torque was applied to one arm.
Yield was scored by an automatic gauge.

\\section{Results}
Results are pending. No number in this document is measured.
"""

TOY_DESIGN = """# Toy widget design (synthetic fixture)

- Unit: one widget batch.
- Arms: TORQUE and NO_TORQUE.
- Endpoint: binary pass of the automatic gauge.
- The design does not specify how batches are assigned to arms.
- The design does not state a power calculation.
"""

TOY_VENUE = """# Toy venue policy (synthetic fixture)

- Page limit: 4 pages.
- Double blind: author names must not appear.
- References do not count toward the limit.
"""

TOY_ENVIRONMENT = """# Toy environment receipt (synthetic fixture)

python 3.12.0
gauge-lib 1.2.3
"""


def _role_prompt_digest(role_id: str) -> str:
    return digest_bytes(ROLES_BY_ID[role_id].prompt().encode("utf-8"))


def _transcript(role_id: str, response: dict) -> dict:
    return {
        "prompt_digest": _role_prompt_digest(role_id),
        "engine": "fixture",
        "model": "synthetic-fixture-v1",
        "input_tokens": 1200,
        "output_tokens": 400,
        "cost_usd_upper_bound": 0.0,
        "response": response,
    }


RESPONSES: dict[str, dict] = {
    # Grounded blocker: cites a real line in the toy design.
    "R02-identification": {
        "role_id": "R02-identification",
        "coverage_notes": ["Read the toy design end to end."],
        "declared_dependencies": [],
        "findings": [
            {
                "finding_id": "F-ID-01",
                "severity": "blocker",
                "title": "No assignment mechanism is specified",
                "statement": (
                    "The design names two arms but never states how a batch is "
                    "assigned to one, so no contrast between arms identifies a "
                    "causal effect."
                ),
                "failure_mode": (
                    "Any reported arm difference is confounded with whatever "
                    "process actually placed batches into arms."
                ),
                "evidence": [
                    {
                        "kind": "repo_line",
                        "locator": "design.md",
                        "start_line": 6,
                        "end_line": 6,
                        "detail": "design states assignment is unspecified",
                        "quoted": "does not specify how batches are assigned",
                    }
                ],
                "claim_ids": ["C1"],
                "reproduction": ["sed -n '6p' design.md"],
                "what_would_refute": (
                    "A design revision that states a randomisation procedure and "
                    "its seed source."
                ),
                "confidence": "asserted",
            }
        ],
    },
    # Grounded major, plus one finding that must be downgraded for citing a
    # line that does not exist.
    "R03-statistics": {
        "role_id": "R03-statistics",
        "coverage_notes": ["No power section exists to review."],
        "declared_dependencies": [],
        "findings": [
            {
                "finding_id": "F-ST-01",
                "severity": "major",
                "title": "No power calculation",
                "statement": "The design states no power calculation of any kind.",
                "failure_mode": (
                    "A null result would be uninterpretable because the study "
                    "cannot say what effect it could have detected."
                ),
                "evidence": [
                    {
                        "kind": "repo_line",
                        "locator": "design.md",
                        "start_line": 7,
                        "end_line": 7,
                        "detail": "design states no power calculation",
                        "quoted": "does not state a power calculation",
                    }
                ],
                "claim_ids": ["C2"],
                "reproduction": [],
                "what_would_refute": "A registered power analysis with its simulation script.",
                "confidence": "asserted",
            },
            {
                "finding_id": "F-ST-02",
                "severity": "blocker",
                "title": "Invented citation, must be downgraded",
                "statement": "The gauge calibration table is wrong.",
                "failure_mode": "Every yield number would be biased.",
                "evidence": [
                    {
                        "kind": "repo_line",
                        "locator": "design.md",
                        "start_line": 9000,
                        "end_line": 9001,
                        "detail": "a line range that does not exist",
                    }
                ],
                "claim_ids": ["C2"],
                "reproduction": [],
                "what_would_refute": "A calibration receipt.",
                "confidence": "asserted",
            },
        ],
    },
    # Minor, plus an explicit speculation that must be preserved but barred.
    "R09-manuscript": {
        "role_id": "R09-manuscript",
        "coverage_notes": ["Read the toy manuscript."],
        "declared_dependencies": [],
        "findings": [
            {
                "finding_id": "F-MS-01",
                "severity": "minor",
                "title": "Results section promises numbers it does not have",
                "statement": (
                    "The results section is a placeholder while the claims "
                    "section already asserts a quantitative gain."
                ),
                "failure_mode": (
                    "A reader takes C2 as measured when nothing measured it."
                ),
                "evidence": [
                    {
                        "kind": "manuscript_span",
                        "locator": "manuscript.tex",
                        "start_line": 15,
                        "end_line": 16,
                        "detail": "results are pending",
                        "quoted": "Results are pending",
                    }
                ],
                "claim_ids": ["C2"],
                "reproduction": [],
                "what_would_refute": "A results table produced by a named script.",
                "confidence": "asserted",
            },
            {
                "finding_id": "F-MS-02",
                "severity": "speculation",
                "title": "The authors probably cherry-picked the widget lines",
                "statement": (
                    "No evidence supports this; recorded as speculation so the "
                    "concern is not lost."
                ),
                "failure_mode": "Selection of favourable lines would inflate the effect.",
                "evidence": [],
                "claim_ids": ["C3"],
                "reproduction": [],
                "what_would_refute": "A registered line-selection record.",
                "confidence": "unverified",
            },
        ],
    },
    # Compliance reviewer with a clean report and no findings.
    "R10-compliance": {
        "role_id": "R10-compliance",
        "coverage_notes": ["Toy venue policy checked; no anonymity break found."],
        "declared_dependencies": [],
        "findings": [],
    },
}


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)

    (ROOT / "manuscript.tex").write_text(TOY_MANUSCRIPT, encoding="utf-8")
    (ROOT / "design.md").write_text(TOY_DESIGN, encoding="utf-8")
    (ROOT / "venue.md").write_text(TOY_VENUE, encoding="utf-8")
    (ROOT / "environment.md").write_text(TOY_ENVIRONMENT, encoding="utf-8")

    for role_id, response in RESPONSES.items():
        (TRANSCRIPTS / f"{role_id}.json").write_text(
            json.dumps(_transcript(role_id, response), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    spec = {
        "campaign_id": "synthetic-fixture-widget",
        "stage": "stage_1_pre_launch",
        "root": "root",
        "role_ids": sorted(RESPONSES),
        "environment": {
            "repo_commit": "0" * 40,
            "repo_dirty": False,
            "python_version": "3.12",
            "platform": "fixture",
            "dependency_digest": "0" * 64,
        },
        "objects": [
            {
                "slot": "manuscript",
                "path": "manuscript.tex",
                "declared_digest": digest_file(str(ROOT / "manuscript.tex")),
                "description": "toy manuscript",
            },
            {
                "slot": "design",
                "path": "design.md",
                "declared_digest": digest_file(str(ROOT / "design.md")),
                "description": "toy design",
            },
            {
                "slot": "venue_policy",
                "path": "venue.md",
                "declared_digest": digest_file(str(ROOT / "venue.md")),
                "description": "toy venue policy",
            },
            {
                "slot": "environment",
                "path": "environment.md",
                "declared_digest": digest_file(str(ROOT / "environment.md")),
                "description": "toy environment receipt",
            },
            {
                "slot": "power_report",
                "path": "design.md",
                "declared_digest": digest_file(str(ROOT / "design.md")),
                "description": "no separate power report exists in the toy study",
            },
        ],
        "receipt_index": {"toy-gauge-receipt": "1" * 64},
        "external_sources": ["arXiv:2601.00001"],
        "claims": [
            {
                "claim_id": "C1",
                "text": "Applying the torque protocol raises assembly yield.",
                "kind": "claim_of_record",
                "supporting_evidence": [],
            },
            {
                "claim_id": "C2",
                "text": "The measured yield gain is at least four percentage points.",
                "kind": "quantitative",
                "supporting_evidence": [],
            },
            {
                "claim_id": "C3",
                "text": "The protocol has been evaluated on two independent widget lines.",
                "kind": "contribution",
                "supporting_evidence": ["receipt:toy-gauge-receipt"],
            },
        ],
        "source": {"mode": "replay", "transcript_dir": "transcripts"},
    }
    (FIXTURE / "campaign-spec.json").write_text(canonical_json(spec), encoding="utf-8")
    print(f"wrote fixture to {FIXTURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

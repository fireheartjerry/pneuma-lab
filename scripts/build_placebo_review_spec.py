"""Generate the Step 14 campaign spec for the PLACEBO adversarial review.

This PREPARES the campaign. It does not run it. Generating the spec pins the
exact bytes the reviewers would read, which is the only way a later campaign
can prove it reviewed the artifact it claims to have reviewed.

Running the campaign from this spec requires sealed reviewer transcripts under
``build/adversarial_review/step14/transcripts/``. Until those exist, the
campaign fails closed at the replay source, which is the intended state before
Step 14.

    python scripts/build_placebo_review_spec.py
    # later, at Step 14, with transcripts present:
    python -m pneuma_lab.adversarial_review run \
        --spec build/adversarial_review/step14/campaign-spec.json \
        --out build/adversarial_review/step14/out
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pneuma_lab.adversarial_review.canonical import (  # noqa: E402
    canonical_json,
    digest_file,
    digest_value,
)

OUT = REPO_ROOT / "build" / "adversarial_review" / "step14"

#: Contract inputs that exist before external evidence is collected.
INPUTS: tuple[tuple[str, str, str], ...] = (
    (
        "design",
        "docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md",
        "the binding study design",
    ),
    (
        "plan",
        "docs/research/neurips-2026-workshop/37-phase-b-4-13-implementation-plan.md",
        "Phase B implementation plan",
    ),
    (
        "manifest",
        "docs/research/neurips-2026-workshop/38-experiment-design-freeze.md",
        "registered design freeze",
    ),
    (
        "spend_ledger",
        "docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md",
        "cloud spend ledger",
    ),
    ("manuscript", "paper/placebo_protocol.tex", "the pre-results manuscript"),
    ("bibliography", "paper/placebo/refs-placebo.bib", "new references"),
    ("citation_queue", "paper/placebo/citation-queue.json", "citation verification state"),
    ("venue_policy", "paper/README.md", "recorded venue facts and page limit"),
    ("environment", "pyproject.toml", "declared dependency set"),
    ("repo_commit", "docs/project-status.json", "current-state manifest"),
)

#: Step 14 may review only real, validated evidence. Contract prose is never a
#: stand-in for one of these receipts.
REQUIRED_RECEIPTS: tuple[tuple[str, str, str, str], ...] = (
    (
        "p0-power-report",
        "power_report",
        "build/research/neurips-2026-workshop/p0-canonical/power/p0-power-report.json",
        "sealed authority-bound P0 power/tier report from the canonical run root",
    ),
    (
        "p0-core-artifact-root",
        "artifact_root",
        "build/research/neurips-2026-workshop/p0-canonical/p0-core-receipt.json",
        "independently verified canonical P0 artifact-root receipt",
    ),
    (
        "step5b-input-lock",
        "input_lock",
        "build/research/neurips-2026-workshop/phase-b-evidence/cloud-input-lock.json",
        "Step 5B independently hash-verified external-input lock",
    ),
    (
        "g-roster-qualification",
        "artifact_root",
        "build/research/neurips-2026-workshop/phase-b-evidence/g-roster-qualification.json",
        "G-ROSTER base-commit, image, isolation, and three-pair qualification",
    ),
    (
        "step7b-image-build-set",
        "artifact_root",
        "build/research/neurips-2026-workshop/phase-b-evidence/image-build-set.json",
        "Step 7B complete double-build and SBOM receipt set",
    ),
    (
        "production-execution-surface",
        "artifact_root",
        "build/research/neurips-2026-workshop/phase-b-evidence/production-execution-surface.json",
        "E2E-qualified controller, model-server, and benchmark-worker entrypoints",
    ),
    (
        "aws-account-verification",
        "artifact_root",
        "build/research/neurips-2026-workshop/phase-b-evidence/aws-account-verification.json",
        "AWS identity, both G/VT quotas, offering, and Terraform-plan receipt",
    ),
    (
        "one-gpu-admission",
        "artifact_root",
        "build/research/neurips-2026-workshop/phase-b-evidence/one-gpu-admission.json",
        "hash-bound one-L40S OOM, tool-call, parity, and throughput receipt",
    ),
    (
        "interruption-recovery",
        "artifact_root",
        "build/research/neurips-2026-workshop/phase-b-evidence/interruption-recovery.json",
        "independent AWS lease-expiry kill and exact completed-boundary restoration receipt",
    ),
    (
        "cross-platform-portability",
        "artifact_root",
        "build/research/neurips-2026-workshop/phase-b-evidence/cross-platform-portability.json",
        "Windows and Linux offline verification of the exact sealed receipt bundle",
    ),
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> int:
    commit = _git("rev-parse", "HEAD")
    dirty = bool(_git("status", "--porcelain"))

    objects = []
    receipt_index: dict[str, str] = {}
    missing = []
    declared = list(INPUTS) + [
        (slot, relative, description)
        for _, slot, relative, description in REQUIRED_RECEIPTS
    ]
    for slot, relative, description in declared:
        path = REPO_ROOT / relative
        if not path.is_file():
            missing.append(relative)
            continue
        objects.append(
            {
                "slot": slot,
                "path": relative,
                "declared_digest": digest_file(str(path)),
                "description": description,
            }
        )
    for receipt_id, _, relative, _ in REQUIRED_RECEIPTS:
        path = REPO_ROOT / relative
        if path.is_file():
            receipt_index[receipt_id] = digest_file(str(path))
    if missing:
        print("missing declared inputs:", *missing, sep="\n  ", file=sys.stderr)
        return 2

    claims_payload = json.loads(
        (REPO_ROOT / "paper" / "placebo" / "claims.json").read_text(encoding="utf-8")
    )
    claims = [
        {
            "claim_id": claim["claim_id"],
            "text": claim["text"],
            "kind": claim["kind"],
            "supporting_evidence": (
                [f"receipt:{claim['receipt']}"] if claim.get("receipt") else []
            ),
        }
        for claim in claims_payload["claims"]
    ]

    spec = {
        "campaign_id": "placebo-step14-pre-launch",
        "stage": "stage_1_pre_launch",
        "root": "../../..",
        "environment": {
            "repo_commit": commit,
            "repo_dirty": dirty,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "dependency_digest": digest_file(str(REPO_ROOT / "pyproject.toml")),
        },
        "objects": objects,
        "receipt_index": receipt_index,
        "external_sources": [
            "arXiv:2607.03702",
            "arXiv:2606.09071",
            "arXiv:2606.21409",
        ],
        "claims": claims,
        "source": {"mode": "replay", "transcript_dir": "transcripts"},
        "notes": (
            "PREPARED, NOT RUN. Every Phase B evidence receipt existed and was "
            "digest-bound when this spec was generated. Step 14 remains a review "
            "gate rather than launch or spend authority."
        ),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "campaign-spec.json").write_text(canonical_json(spec), encoding="utf-8")
    print(f"wrote {OUT / 'campaign-spec.json'}")
    print(f"commit {commit} dirty={dirty}")
    print(f"spec digest {digest_value(spec)}")
    print(f"declared inputs: {len(objects)}; claims: {len(claims)}")
    print("transcripts absent -- the campaign will fail closed until Step 14")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

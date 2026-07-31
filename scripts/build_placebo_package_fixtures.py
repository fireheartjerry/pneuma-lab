"""Build synthetic evidence-package fixtures for the result-to-paper pipeline.

Every fixture is SYNTHETIC. The admitted one carries fabricated numbers that
exist only so the renderer has something to format; they are labelled as such
in the package itself and a test asserts the label is present. No fixture here
is, or may become, a scientific result.

    python scripts/build_placebo_package_fixtures.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "fixtures" / "placebo_paper"

RECEIPTS = {
    "study_manifest": "a" * 64,
    "prefix_schedule": "b" * 64,
    "assignment_ledger": "c" * 64,
    "packet_index": "d" * 64,
    "blinded_projection": "e" * 64,
    "analysis_freeze": "f" * 64,
    "unblind_receipt": "0" * 64,
    "artifact_root": "1" * 64,
    "power_report": "2" * 64,
}

ADMISSIBLE = {
    "synthetic_fixture_notice": (
        "SYNTHETIC. Every number below is fabricated so the renderer has "
        "something to format. This package is not a scientific result and may "
        "never be cited as one."
    ),
    "package_kind": "resampling_task10_sealed",
    "lineage": "canonical_confirmation",
    "sealed": True,
    "authority": "confirmation_execution_authorized",
    "verdict": "UNRESOLVED_RESAMPLING",
    "artifact_root": {"verified": True, "digest": "1" * 64, "record_count": 12},
    "unblind": {"ceremony_completed": True, "permit_digest": "3" * 64},
    "receipts": RECEIPTS,
    "numbers": {
        "content.estimate": 0.031,
        "content.lower_bound": -0.004,
        "content.p_value": 0.082,
        "excess.estimate": 0.047,
        "excess.lower_bound": 0.006,
        "excess.p_value": 0.031,
        "sham_packet.estimate": 0.016,
        "sham_packet.lower_bound": -0.012,
        "sham_packet.p_value": 0.140,
        "continuation.estimate": 0.088,
        "continuation.lower_bound": 0.052,
        "continuation.p_value": 0.001,
        "total.estimate": 0.135,
        "total.lower_bound": 0.094,
        "total.p_value": 0.001,
        "resolution.q0": 0.118,
        "resolution.r95": 0.042,
        "resolution.delta_null": 0.003,
        "resolution.delta_star": 0.05,
        "swe.content": 0.025,
        "swe.excess": 0.041,
        "swe.n": 160,
        "tau.content": 0.037,
        "tau.excess": 0.053,
        "tau.n": 160,
    },
}


def _variant(name: str, **overrides) -> None:
    payload = copy.deepcopy(ADMISSIBLE)
    payload.update(overrides)
    target = FIXTURES / name
    target.mkdir(parents=True, exist_ok=True)
    (target / "package.json").write_text(
        json.dumps(payload, indent=4, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    _variant("admissible")
    _variant("step4a", lineage="step_4a")
    _variant("p0_incomplete", lineage="p0_incomplete")
    _variant("unsealed", sealed=False)
    _variant(
        "unverified_root",
        artifact_root={"verified": False, "digest": "1" * 64, "record_count": 12},
    )
    _variant("wrong_authority", authority="implementation_only")
    _variant(
        "no_unblind",
        unblind={"ceremony_completed": False, "permit_digest": None},
    )
    _variant(
        "missing_receipt",
        receipts={k: v for k, v in RECEIPTS.items() if k != "unblind_receipt"},
    )
    _variant("bad_verdict", verdict="LOOKS_GOOD")
    print(f"wrote package fixtures to {FIXTURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

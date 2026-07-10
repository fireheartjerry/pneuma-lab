"""Deterministic writer + CLI for SubjectEvidenceCampaign-v0 artifacts.

Writes summary.json (sorted, byte-stable) and a human-readable summary.md under an
output directory (default: build/evidence_campaigns/subject-v0/). No wall clock.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pneuma_lab.nervous_system.campaign import run_campaign
from pneuma_lab.schemas import validate

_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_OUT = _REPO / "build" / "evidence_campaigns" / "subject-v0"


def _render_md(summary: dict) -> str:
    lines = [
        f"# {summary['subject']} — Evidence Campaign",
        "",
        f"Campaign: `{summary['campaign_id']}`  ",
        f"Claim: **{summary['overall']['claim']}** ({summary['overall']['posture']})",
        "",
        f"> {summary['overall'].get('note', '')}",
        "",
        "| slice | effect_observed | readiness | evidence_level |",
        "| --- | --- | --- | --- |",
    ]
    for s in summary["slices"]:
        lines.append(
            f"| {s['id']} | {s['effect_observed']} | {s['readiness']} | "
            f"{s['evidence_frame']['evidence_level']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def write_campaign(summary: dict, out_dir) -> dict:
    validate.validate_campaign(summary)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "summary.json"
    md_path = out / "summary.md"
    json_path.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(_render_md(summary), encoding="utf-8")
    return {"json": json_path, "md": md_path}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pneuma_lab.nervous_system.campaign_report")
    parser.add_argument("--out", default=str(_DEFAULT_OUT))
    args = parser.parse_args(argv)
    out = Path(args.out)
    summary = run_campaign(work_dir=out / "_work")
    write_campaign(summary, out)
    print(f"wrote campaign artifacts to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

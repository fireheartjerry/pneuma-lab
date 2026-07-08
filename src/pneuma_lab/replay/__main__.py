"""CLI: replay an input-frame JSONL timeline through the ReferencePsyche.

Usage::

    python -m pneuma_lab.replay <input.jsonl> -o <out_dir>

If the timeline contains no InterventionFrame, this runs a single passive replay
and writes ``<out_dir>/output_frames.jsonl`` + ``<out_dir>/evidence.json`` (Level
0-3). If it contains one or more InterventionFrames, it runs a **paired**
control/treated/null replay and additionally writes ``control_frames.jsonl``,
``intervention_frames.jsonl``, and ``intervention_report.json`` — the Level-4
evidence path. Deterministic either way: same input ⇒ byte-identical outputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..psyche import ReferencePsyche
from .frames import dump_jsonl, load_jsonl
from .harness import ReplayHarness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pneuma_lab.replay")
    parser.add_argument("input", help="Path to the input-frame JSONL timeline.")
    parser.add_argument(
        "-o", "--out-dir", default="build/replay", help="Output directory."
    )
    parser.add_argument(
        "--no-validate", action="store_true", help="Skip schema validation."
    )
    args = parser.parse_args(argv)

    input_frames = load_jsonl(args.input)
    out_dir = Path(args.out_dir)

    has_intervention = any(f.get("frame_kind") == "intervention" for f in input_frames)
    if has_intervention:
        return _run_paired(input_frames, out_dir, validate=not args.no_validate)

    harness = ReplayHarness(ReferencePsyche(), validate=not args.no_validate)
    result = harness.run(input_frames)

    dump_jsonl(result.output_frames, out_dir / "output_frames.jsonl")
    _dump_json(result.evidence_frame, out_dir / "evidence.json")

    ev = result.evidence_frame
    print(
        f"replayed {result.input_count} input frames over {result.tick_count} ticks -> "
        f"{len(result.output_frames)} output frames | "
        f"evidence_level={ev['evidence_level']} "
        f"confab_risk={ev['roleplay_confabulation_risk']} "
        f"(interventions_seen={result.interventions_seen}, executed=0) | "
        f"out={out_dir}"
    )
    return 0


def _run_paired(input_frames: list[dict], out_dir: Path, *, validate: bool) -> int:
    """Paired control/treated/null replay — the Level-4 intervention path."""
    from ..interventions.runner import PairedReplayRunner

    res = PairedReplayRunner(validate=validate).run(input_frames)
    dump_jsonl(res.control.output_frames, out_dir / "control_frames.jsonl")
    dump_jsonl(res.treated.output_frames, out_dir / "intervention_frames.jsonl")
    _dump_json(res.report, out_dir / "intervention_report.json")
    _dump_json(res.evidence_frame, out_dir / "evidence.json")

    ev = res.evidence_frame
    print(
        f"paired replay ({res.treated.tick_count} ticks) | "
        f"evidence_level={ev['evidence_level']} "
        f"confab_risk={ev['roleplay_confabulation_risk']} | "
        f"passed={ev['intervention_tests']['passed']} "
        f"failed={ev['intervention_tests']['failed']} | "
        f"null_ok={res.report['null_condition']['passed']} "
        f"trace_complete={res.report['causal_trace_complete']} | out={out_dir}"
    )
    return 0


def _dump_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())

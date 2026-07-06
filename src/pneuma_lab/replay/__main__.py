"""CLI: replay an input-frame JSONL timeline through the ReferencePsyche.

Usage::

    python -m pneuma_lab.replay <input.jsonl> -o <out_dir>

Writes ``<out_dir>/output_frames.jsonl`` (all emitted output frames) and
``<out_dir>/evidence.json`` (the Level 0-3 ConsciousnessEvidenceFrame), and
prints a one-line summary. Deterministic: same input ⇒ byte-identical outputs.
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
    harness = ReplayHarness(ReferencePsyche(), validate=not args.no_validate)
    result = harness.run(input_frames)

    out_dir = Path(args.out_dir)
    dump_jsonl(result.output_frames, out_dir / "output_frames.jsonl")
    with (out_dir / "evidence.json").open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(
            result.evidence_frame, fh, indent=2, sort_keys=True, ensure_ascii=False
        )

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


if __name__ == "__main__":
    sys.exit(main())

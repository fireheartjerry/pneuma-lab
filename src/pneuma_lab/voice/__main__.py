"""CLI: python -m pneuma_lab.voice <fixture> [--out DIR] [--subject reference|baseline]"""

from __future__ import annotations

import argparse
from pathlib import Path

from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import load_jsonl

from .stream import voice_run
from .transcript import write_transcript


def _factory(name: str):
    if name == "baseline":
        from pneuma_lab.nervous_system.subject import BaselinePsycheSubject

        return BaselinePsycheSubject
    return ReferencePsyche


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pneuma_lab.voice")
    parser.add_argument("fixture", help="input-frame JSONL timeline")
    parser.add_argument(
        "--out", default=None, help="output dir (default build/voice/<run>)"
    )
    parser.add_argument(
        "--subject", choices=("reference", "baseline"), default="reference"
    )
    args = parser.parse_args(argv)

    stream = voice_run(load_jsonl(args.fixture), subject_factory=_factory(args.subject))
    out_dir = Path(args.out) if args.out else Path("build/voice") / stream["run_id"]
    write_transcript(stream, out_dir)
    print(
        f"wrote {out_dir}/stream.md (level {stream['evidence_level']}, {len(stream['atoms'])} atoms)"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

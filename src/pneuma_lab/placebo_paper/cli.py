"""Command-line entry point for the PLACEBO result-to-paper pipeline.

    python -m pneuma_lab.placebo_paper preflight [--package DIR]
    python -m pneuma_lab.placebo_paper render --out paper/placebo/generated [--package DIR]
    python -m pneuma_lab.placebo_paper admit --package DIR

Exit codes: 0 = clean, 1 = blocked, 2 = the package was refused.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .errors import PlaceboPaperError
from .package import admit
from .preflight import run
from .render import write_assets

REPO_ROOT = Path(__file__).resolve().parents[3]
PAPER_DIR = REPO_ROOT / "paper"
MANUSCRIPT = PAPER_DIR / "placebo_protocol.tex"
BIBS = (PAPER_DIR / "refs.bib", PAPER_DIR / "placebo" / "refs-placebo.bib")
CITATION_QUEUE = PAPER_DIR / "placebo" / "citation-queue.json"
CLAIMS = PAPER_DIR / "placebo" / "claims.json"


def _claims() -> list[dict]:
    if not CLAIMS.is_file():
        return []
    return json.loads(CLAIMS.read_text(encoding="utf-8")).get("claims", [])


def _preflight(args: argparse.Namespace) -> int:
    report = run(
        Path(args.manuscript),
        bib_paths=BIBS,
        citation_queue_path=CITATION_QUEUE,
        package_path=Path(args.package) if args.package else None,
    )
    sys.stdout.write(report.render())
    if args.json:
        Path(args.json).write_text(
            json.dumps(report.to_canonical(), indent=4, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0 if report.submission_ready else 1


def _render(args: argparse.Namespace) -> int:
    package = admit(Path(args.package)) if args.package else None
    written = write_assets(Path(args.out), package, _claims())
    for name in sorted(written):
        print(f"{name}\t{written[name]} bytes")
    return 0


def _admit(args: argparse.Namespace) -> int:
    package = admit(Path(args.package))
    print(f"admitted: lineage={package.lineage} verdict={package.verdict}")
    print(f"artifact root: {package.artifact_root_digest}")
    print(f"emitted numbers: {len(package.numbers)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pneuma_lab.placebo_paper",
        description="Fail-closed result-to-paper pipeline for the PLACEBO manuscript.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight", help="run every manuscript check")
    pre.add_argument("--manuscript", default=str(MANUSCRIPT))
    pre.add_argument("--package", default=None)
    pre.add_argument("--json", default=None, help="also write the report as JSON")
    pre.set_defaults(handler=_preflight)

    ren = sub.add_parser("render", help="emit generated tables, figures, appendix")
    ren.add_argument("--out", default=str(PAPER_DIR / "placebo" / "generated"))
    ren.add_argument("--package", default=None)
    ren.set_defaults(handler=_render)

    adm = sub.add_parser("admit", help="admit a sealed evidence package, or refuse it")
    adm.add_argument("--package", required=True)
    adm.set_defaults(handler=_admit)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except PlaceboPaperError as exc:
        print(f"REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

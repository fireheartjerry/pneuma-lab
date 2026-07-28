"""Extract a small, committable real-data fixture from a G-1 run cube.

`build/` is gitignored, so the full cube is not an artifact of record. This pulls a
balanced subsample of *real* elicitations into `fixtures/gauge/`, which gives the
test suite something better than synthetic data to assert the calibration theorem
against, and gives a reader a concrete sample of what the channel actually emits.

Usage:
    python scripts/gauge_extract_fixture.py \
        --cube build/gauge/g1/cube-core.jsonl \
        --out fixtures/gauge/g1-core-sample.jsonl --items 8 --wordings 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pneuma_lab.gauge.cube import ResponseCube  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cube", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--items", type=int, default=8)
    parser.add_argument("--wordings", type=int, default=4)
    args = parser.parse_args()

    cube = ResponseCube.fromJsonl(args.cube)
    matrix = cube.balancedMatrix(("wording_id",))
    # Keep a spec-balanced slice: alternate correct/buggy so the subsample spans
    # the true-correctness range the way the full bank does.
    correct = [i for i in matrix.items if i.endswith("__correct")][: args.items // 2]
    buggy = [i for i in matrix.items if i.endswith("__buggy")][: args.items // 2]
    keep_items = set(correct) | set(buggy)
    keep_wordings = set(sorted(cube.values("wording_id"))[: args.wordings])

    rows = [
        r
        for r in cube.rows
        if r.item_id in keep_items and r.wording_id in keep_wordings
    ]
    subset = ResponseCube(rows)
    path = subset.toJsonl(args.out)
    print(
        f"{len(subset)} responses -> {path} "
        f"({len(keep_items)} items x {len(keep_wordings)} wordings, "
        f"parse-failure rate {subset.parseFailureRate():.4f})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

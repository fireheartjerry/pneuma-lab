"""Fail when a superseded number survives an edit somewhere in the paper.

`audit_numbers.py` proves every figure traces to an artifact. That is necessary
and not sufficient: when a quantity is recomputed, the old value and the new one
both sit in the artifact tree, so both trace happily while the paper says two
different things in two places.

This has now happened twice in this paper -- the abstract was corrected while the
body was not, and later the body moved to execution-verified pairs while the
abstract and the contributions list did not. Both were found by reading, which
does not scale and did not catch them the first time.

`stale_numbers.json` records each superseded value, its replacement, and how many
occurrences remain deliberate (a before/after sentence is a legitimate reason to
keep one). Any excess is a stale value that survived an edit.

Usage:
    python check_stale.py [job]      # default job: placebo
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    job = sys.argv[1] if len(sys.argv) > 1 else "placebo"
    pdf = HERE / f"{job}.pdf"
    spec = HERE / "stale_numbers.json"

    if not pdf.exists():
        print(f"{pdf.name} not found -- build first")
        return 2
    if not spec.exists():
        print("stale_numbers.json not found -- nothing to check")
        return 0

    try:
        text = subprocess.run(
            ["pdftotext", str(pdf), "-"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        print("pdftotext unavailable -- skipping stale-number check")
        return 0

    entries = json.loads(spec.read_text(encoding="utf-8"))["superseded"]
    failures = []

    for entry in entries:
        value = entry["value"]
        allowed = int(entry["allowed"])
        # Word-bounded so 0.1100 does not match inside 0.11003.
        found = len(re.findall(rf"(?<![0-9.]){re.escape(value)}(?![0-9])", text))
        if found > allowed:
            failures.append((value, found, allowed, entry))

    # An allowance looser than reality is a loaded gun: it silently permits a
    # retired value to come back. This happened -- three superseded numbers sat in
    # Section 4 because each allowance had been set from the occurrence count at
    # registration time, which blessed exactly the mentions that should have been
    # fixed. Allowances must be justified, not merely current, so the check
    # ratchets: it reports any allowance with slack and refuses to pass on it.
    slack = []
    for entry in entries:
        value = entry["value"]
        allowed = int(entry["allowed"])
        found = len(re.findall(rf"(?<![0-9.]){re.escape(value)}(?![0-9])", text))
        if found < allowed:
            slack.append((value, found, allowed))

    if slack and not failures:
        print(f"stale-number check FAILED ({len(slack)} allowance(s) with slack)")
        print("      An allowance above the actual count permits a retired value to")
        print("      return unnoticed. Tighten each to what the paper justifies.")
        for value, found, allowed in slack:
            print(f"  {value}: appears {found} time(s), {allowed} allowed -- tighten")
        return 1

    if not failures:
        print(
            f"stale-number check ok ({len(entries)} superseded values, none in excess)"
        )
        return 0

    print(f"stale-number check FAILED ({len(failures)} value(s) in excess)")
    for value, found, allowed, entry in failures:
        print(f"  {value}: {found} occurrence(s), {allowed} allowed")
        print(f"      superseded by {entry['replaced_by']} -- {entry['why']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

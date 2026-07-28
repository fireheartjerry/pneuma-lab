"""Tighten every stale-number allowance to the count the paper actually justifies.

Allowances were set from the occurrence count at registration time, which blesses
whatever mentions exist rather than the ones that are defensible. Three superseded
values survived in Section 4 that way.

This ratchets DOWN only -- an allowance is never raised here, because raising one
is a claim that the paper newly needs a retired value, and that should be a
deliberate edit with a reason, not a maintenance sweep.
"""

import json
import re
import subprocess
from pathlib import Path

PAPER = Path("C:/pneuma-lab/.claude/worktrees/neurips-2026-empirical/paper")
REGISTRY = PAPER / "stale_numbers.json"

text = subprocess.run(
    ["pdftotext", str(PAPER / "placebo.pdf"), "-"],
    capture_output=True,
    text=True,
    check=True,
).stdout

data = json.loads(REGISTRY.read_text(encoding="utf-8"))
tightened = 0
for entry in data["superseded"]:
    value = entry["value"]
    found = len(re.findall(rf"(?<![0-9.]){re.escape(value)}(?![0-9])", text))
    allowed = int(entry["allowed"])
    if found < allowed:
        print(f"  {value}: {allowed} -> {found}")
        entry["allowed"] = found
        tightened += 1

REGISTRY.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
print(f"tightened {tightened} allowance(s); none raised")

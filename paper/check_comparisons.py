"""Flag comparisons whose two sides were never measured together.

Seven defects in this paper shared one root cause: two numbers compared as though
commensurable when the measurements behind them differed. Five were found one at a
time, each by the guard built for the previous one; the last two were found by
sweeping every comparison at once. This makes that sweep mechanical.

The test is simple and follows from what a comparison asserts. If a sentence says
X falls below Y, then X and Y are quantities from one measurement system, so some
artifact should contain BOTH. When no single artifact does, the two sides came
from different runs and the sentence is asserting a relationship nothing measured.

Verified against the real defect: reverting the figure sentence to its DL-102 form
-- per-wording effects from the 46-pair run against a floor from the 40-problem
gauge, the right instrument on the wrong parts -- makes this check fail, and
restoring it makes it pass.

WHAT THIS DOES NOT CATCH, stated because a checker's blind spots matter more than
its coverage. The other defect the manual sweep found was "other-code judging at
AUROC 0.769 against 0.713", where 0.769 had never been measured on other-code at
all. This check skips that sentence, because comparing other-code against
self-assessment is cross-task BY CONSTRUCTION and appears in DECLARED below --
the claim depends on the two differing, so requiring a shared artifact would be
wrong. Every declaration is therefore a blind spot, which is why each states a
reason a reader can disagree with. That class -- a number attributed to a
measurement never made -- is caught upstream instead, by refusing to let measured
values sit in audit_numbers.EXTERNAL.

It is a heuristic either way: co-occurrence in one artifact is necessary for a
matched comparison, not sufficient.

Run: python paper/check_comparisons.py [job]
Exit 0 when every comparison either shares an artifact or is declared.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE.parent / "build" / "research" / "placebo" / "instrument"

COMPARATIVE = re.compile(
    r"\b(against|below|above|falls? below|larger than|smaller than|worse than|"
    r"better than|versus|exceeds?|outperforms?)\b",
    re.IGNORECASE,
)

NUMBER = re.compile(r"(?<![A-Za-z0-9.])\d+\.\d{2,4}")

# Numbers that are not measurements and so cannot be "measured together" with
# anything: acceptance thresholds and statistical constants. Same rule as
# audit_numbers.EXTERNAL -- nothing measured belongs here.
NOT_MEASUREMENTS = {"0.05", "1.96", "0.5"}

# Comparisons that legitimately span artifacts, each with the reason. A
# cross-model or before/after comparison is ABOUT the difference between two
# runs, so requiring one artifact to hold both would be wrong.
DECLARED: tuple[tuple[str, str], ...] = (
    (
        "second model family",
        "Cross-model corroboration: qwen and llama are different runs by "
        "construction, and the sentence says so. Each side's effect and floor are "
        "internally matched within its own model's artifact.",
    ),
    (
        "other-code judging",
        "Cross-task by construction: the sentence compares other-code judging "
        "against self-assessment to establish that the first is easier. The two "
        "cannot share an artifact and the claim depends on their differing.",
    ),
    (
        "independently drawn sample",
        "Replication across two independent samples, stated as such: 3.83x from "
        "the verified gauge against 4.17x from the 46-pair run.",
    ),
    (
        "An earlier draft compared",
        "Narrates a superseded comparison in order to correct it; the mismatch is "
        "the subject of the sentence.",
    ),
    (
        "the mean rises from",
        "Before/after re-analysis on the same run with invalid pairs dropped.",
    ),
    (
        "null median of",
        "Observed statistic against its own permutation null, which is generated "
        "from the observed data and stored beside it.",
    ),
    (
        "observed 0.1457",
        "Per-benchmark split of the same permutation test.",
    ),
)


def artifactIndex() -> dict[str, set[str]]:
    """Map each numeric token (and its roundings) to the artifacts containing it."""
    index: dict[str, set[str]] = {}
    if not ARTIFACTS.exists():
        return index
    for path in sorted(ARTIFACTS.rglob("*")):
        if path.suffix.lower() not in {".json", ".jsonl"}:
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for token in re.findall(r"\d+\.\d+", body):
            try:
                value = float(token)
            except ValueError:
                continue
            for places in (2, 3, 4):
                index.setdefault(f"{value:.{places}f}", set()).add(path.name)
    return index


def sentences(text: str) -> list[str]:
    body = "\n".join(
        line for line in text.split("\n") if not line.strip().startswith("%")
    )
    body = re.sub(r"\\(textbf|emph|textit|texttt)\{([^{}]*)\}", r"\2", body)
    body = re.sub(r"\\citep?\{[^}]*\}", "", body)
    body = re.sub(r"\\ref\{[^}]*\}", "X", body)
    body = re.sub(r"\s+", " ", body)
    return re.split(r"(?<=[.!?]) (?=[A-Z\\])", body)


def normalise(token: str) -> str:
    return f"{float(token):.4f}"


def main() -> int:
    job = sys.argv[1] if len(sys.argv) > 1 else "placebo"
    tex = HERE / f"{job}.tex"
    if not tex.is_file():
        print(f"no source at {tex}")
        return 0

    index = artifactIndex()
    flagged: list[tuple[str, list[str]]] = []
    declared_count = 0

    for sentence in sentences(tex.read_text(encoding="utf-8")):
        numbers = [n for n in NUMBER.findall(sentence) if n not in NOT_MEASUREMENTS]
        if len(numbers) < 2 or not COMPARATIVE.search(sentence):
            continue
        if any(marker in sentence for marker, _reason in DECLARED):
            declared_count += 1
            continue
        # Every number must be locatable, and some artifact must hold them all.
        sets = [index.get(normalise(n), set()) for n in numbers]
        if any(not s for s in sets):
            continue  # untraced numbers are audit_numbers.py's job, not this one
        shared = set.intersection(*sets)
        if not shared:
            flagged.append((sentence.strip(), numbers))

    if not flagged:
        print(
            f"OK    every comparison shares an artifact "
            f"({declared_count} declared cross-artifact)"
        )
        return 0

    print(f"FAIL  {len(flagged)} comparison(s) whose sides share no artifact.")
    print("      Two quantities compared should have been measured together;")
    print("      if nothing measured both, the sentence asserts an untested")
    print("      relationship. Declare it or re-measure.")
    for sentence, numbers in flagged:
        condensed = re.sub(r"\$([^$]*)\$", r"\1", sentence)
        print(f"\n  {', '.join(numbers)}")
        print(f"      {condensed[:260]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

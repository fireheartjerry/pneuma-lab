"""Check that every number in the built paper traces to a persisted artifact.

This repository's standing rule is that a claim with no matching artifact is
rejected. The rule is easy to state and easy to violate silently: numbers
accumulate across drafts, some get retracted and rewritten, and an orphan -- a
figure in the paper that nothing in the artifacts produced -- is invisible
without a mechanical check.

Method: extract every decimal from the built PDF's text layer and look for it in
the persisted artifact tree, tolerating rounding to 2, 3 or 4 decimal places.
Anything unmatched is reported. Expected non-matches are DOIs, thresholds quoted
from cited standards, and occasional artifacts of `pdftotext` joining a number to
an adjacent line number -- so a non-empty list is a prompt to look, not
automatically a failure. Exit code 1 only when an untraced value is not
explained by one of those.

Usage:
    python audit_numbers.py [job]        # default job: placebo
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE.parent / "build" / "research" / "placebo" / "instrument"

# Legitimately present without an artifact: acceptance thresholds and
# conventional statistical constants named in the text.
#
# NOTHING MEASURED BELONGS HERE. 0.769 and 0.713 were once in this set, and that
# is how the paper came to attribute an AUROC of 0.769 to other-code judging when
# no other-code measurement produced it -- the value was never traced, because it
# was exempt from tracing. An allowlist that accumulates measurements does not
# weaken the check, it disables it for exactly the values most worth checking.
#
# Before adding an entry, ask whether the number could in principle come from an
# artifact. If it could, it must, and the fix is to persist the artifact.
EXTERNAL = {
    "30",  # AIAG %GRR rejection threshold
    "10",  # AIAG %GRR acceptance threshold
    "5",  # AIAG minimum ndc
    "0.05",  # conventional alpha
    "1.96",  # normal quantile in the SDC95 formula
    "95",  # confidence level
}

# DOI prefixes and similar publisher strings are not measurements.
DOI_LIKE = re.compile(r"^10\.\d{3,5}$")


def artifactValues() -> set[str]:
    seen: set[str] = set()
    if not ARTIFACTS.exists():
        return seen
    for path in ARTIFACTS.rglob("*"):
        # .md is deliberately EXCLUDED. A README in the artifact tree is a
        # hand-written summary, and accepting it as a source makes this check
        # circular: the paper gets verified against a table the author typed
        # rather than against a measurement. Section 3.2's numbers traced only
        # there until the underlying readouts were summarised into
        # polarity_comparison.json -- they were correct, and reproduced exactly,
        # but nothing mechanical had established that.
        if path.suffix.lower() not in {".json", ".jsonl", ".log"}:
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for token in re.findall(r"\d+\.\d+", body):
            seen.add(token)
            try:
                value = float(token)
            except ValueError:
                continue
            for places in (2, 3, 4):
                seen.add(f"{value:.{places}f}")
    return seen


def main() -> int:
    job = sys.argv[1] if len(sys.argv) > 1 else "placebo"
    pdf = HERE / f"{job}.pdf"
    if not pdf.exists():
        print(f"{pdf.name} not found -- build first")
        return 2

    try:
        text = subprocess.run(
            ["pdftotext", str(pdf), "-"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        print("pdftotext unavailable -- skipping number audit")
        return 0

    # A number preceded by a letter is part of an identifier (pdftotext joins
    # "Qwen2.5" to the line number that follows it), not a measurement.
    claims = sorted(set(re.findall(r"(?<![A-Za-z0-9.])\d+\.\d{2,4}", text)))

    have = artifactValues()

    # Scientific notation was invisible to the scan above, and a claim it could
    # not see went unchecked and turned out to contradict the recorded data: the
    # paper stated escaped mass "below 5x10^-4" while the artifacts bound it at
    # 0.000568. A number typeset as a power of ten is still a claim.
    #
    # These are matched NUMERICALLY, not as strings. The first attempt formatted
    # the value to six decimal places and compared text, which silently passed
    # everything below 1e-6 -- "0.000000" -- so a deliberately unsupported 3e-7
    # traced fine. A check that cannot fail is not a check, and this one was
    # caught only because it was tested against a value that should have failed.
    artifact_floats = set()
    for token in have:
        try:
            artifact_floats.add(float(token))
        except ValueError:
            continue

    # Resolved HERE and kept out of `claims`. Routing them through the loop below
    # re-traced them: that loop falls back to comparing f"{value:.4f}" against the
    # artifact strings, and any value under 1e-4 formats to "0.0000", which is
    # present in `have` because plenty of recorded variances round to zero. So a
    # deliberately unsupported 3e-7 passed twice, under two different bugs with the
    # same shape -- a lenient fallback swallowing the very values being checked.
    scientific_untraced: list[str] = []
    for mantissa, exponent in re.findall(
        r"(?<![A-Za-z0-9.])(\d+(?:\.\d+)?)\s*[x×]\s*10\s*[−-]\s*(\d+)", text
    ):
        value = float(mantissa) * (10 ** -int(exponent))
        if not any(
            abs(candidate - value) <= max(1e-12, abs(value) * 1e-6)
            for candidate in artifact_floats
        ):
            scientific_untraced.append(f"{mantissa}e-{int(exponent)}")

    claims = sorted(set(claims))

    untraced = []
    for claim in claims:
        if claim in have or claim in EXTERNAL or DOI_LIKE.match(claim):
            continue
        try:
            value = float(claim)
        except ValueError:
            untraced.append(claim)
            continue
        if not any(f"{value:.{p}f}" in have for p in (2, 3, 4)):
            untraced.append(claim)

    # Appended after the loop so the rounding fallback cannot reach them.
    claims.extend(scientific_untraced)
    untraced.extend(scientific_untraced)

    print(f"numeric claims   {len(claims)}")
    print(f"traced           {len(claims) - len(untraced)}")
    print(f"untraced         {len(untraced)}")
    for claim in untraced:
        index = text.find(claim)
        context = (
            " ".join(text[max(0, index - 55) : index + 18].split())
            if index >= 0
            else ""
        )
        print(f"  {claim:<10} ...{context}")

    (HERE / f"{job}.number-audit.json").write_text(
        json.dumps({"claims": claims, "untraced": untraced}, indent=2),
        encoding="utf-8",
    )
    return 1 if untraced else 0


if __name__ == "__main__":
    raise SystemExit(main())

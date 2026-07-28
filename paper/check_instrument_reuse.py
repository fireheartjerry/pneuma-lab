"""Detect one experiment's numbers silently reappearing inside another's artifact.

This check exists because that happened, twice, and both times it reached the
paper. The central gauge table reported four elicitation methods as "measured on
identical parts and appraisers"; three were, and the fourth row had been filled by
reusing a different experiment's artifact, measured with a different appraiser set.
The same copied number was also the floor an assay-sensitivity verdict compared a
planted effect against.

Both were found by hand, and only because the copy was *exact*. That exactness is
the point: a re-measurement of the same quantity under the same construction agrees
to a few decimal places, never to all seventeen. Two artifacts sharing a
full-precision float did not measure the same thing twice -- one of them copied it.

So the signature is mechanical, and this is the check:

    a float carrying >= SIGNIFICANT_DIGITS digits, appearing in two or more
    artifacts, is a copy until an allowlist entry says why it is legitimate.

Reuse is not automatically wrong -- a frozen population size or a deliberately
shared constant is fine. It has to be *declared*, which is the whole difference
between a shared input and an undisclosed one.

Run: python paper/check_instrument_reuse.py
Exit 0 when every shared value is declared, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from fractions import Fraction
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ARTIFACTS = Path(__file__).resolve().parent.parent / "build/research/placebo/instrument"

# A value repeated to this many significant digits is not an independent
# measurement of the same quantity. Twelve is far past where any two real runs of
# a stochastic-serving readout would still agree.
SIGNIFICANT_DIGITS = 12

# Keys whose repetition carries no measurement claim: sizes, seeds, counts and
# thresholds are shared by design and their equality is meaningful, not suspect.
STRUCTURAL_KEYS = frozenset(
    {
        "n",
        "n_all",
        "n_items",
        "n_parts",
        "n_programs",
        "n_appraisers",
        "n_phrasings",
        "n_verified",
        "n_dropped",
        "seed",
        "model",
        "labels",
    }
)

# Declared reuse. Each entry names the RELATIONSHIP between two artifacts rather
# than an individual number, because the reason a value is shared is a fact about
# the experiments, not about the float. A shared value is declared only when every
# site it appears at matches one of the entry's patterns -- so a genuinely new copy
# between an already-declared pair of artifacts still fails the check.
#
# A pattern is (filename, path_substring). Adding an entry asserts the reuse is
# intended AND disclosed in the paper.
DECLARED: tuple[tuple[tuple[tuple[str, str], ...], str], ...] = (
    (
        (
            ("interaction_gate.json", "d_by_phrasing."),
            ("interaction_gate.json", "mean_planted_effect"),
            ("planted_effect_verified.json", ".before"),
            ("planted_effect_verified.json", "mean_all"),
        ),
        "LEGITIMATE. planted_effect_verified.json is a re-analysis of the same run "
        "with four invalid mutants dropped, reported as a before/after comparison. "
        "The 'before' values are the originals BY CONSTRUCTION -- if they differed "
        "from interaction_gate.json the re-analysis would be measuring a different "
        "run. Every corresponding 'after' value does differ.",
    ),
    (
        (
            ("floor_metrology.json", ""),
            ("floor_significance.json", ""),
            ("resolving_power.json", "logit_symmetric"),
        ),
        "KNOWN DEFECT, SUPERSEDED AND STILL DECLARED. resolving_power.py filled its "
        "logit_symmetric row by reusing phrasing_floor.json, measured with a "
        "different appraiser set than the row's three table neighbours (DL-99). This "
        "is the defect the check was written for. The paper now reports "
        "matched_symmetric_40.json instead, but resolving_power.json is kept "
        "unedited because it is the true record of what that run produced -- "
        "rewriting a released artifact to hide a defect would be a worse provenance "
        "failure than the defect. The declaration therefore stays as long as the "
        "artifact does. It stays NARROW: it covers only the logit_symmetric row, so "
        "a copy into any other row, or into a third artifact, still fails.",
    ),
    (
        (
            ("resolving_power_120.json", "summary."),
            ("wordings_needed.json", "measured_k1"),
            ("wordings_needed.json", "components"),
        ),
        "LEGITIMATE AND BY CONSTRUCTION. wordings_needed.json asks how many wordings "
        "must be averaged before the channel passes, and its k=1 row IS the published "
        "n=120 gauge quoted as the baseline the curve starts from -- if it differed, "
        "the extrapolation would be starting somewhere the paper never measured. The "
        "variance components are shared for the same reason: the model "
        "sigma_gauge(k) = sqrt((var_appraiser + var_error)/k) is built from them. "
        "NARROW: covers only the k=1 baseline and the components, so a value copied "
        "into any k>1 result -- which must be measured or predicted, never inherited "
        "-- still fails.",
    ),
    (
        (
            ("gauge_verified_qwen2_5-coder_7b.json", "gauge."),
            ("resolving_power_120.json", "summary.logit_symmetric."),
            ("selfreport_vs_othercode.json", "indices."),
        ),
        "LEGITIMATE, AND THE MATCH IS EVIDENCE. selfreport_vs_othercode.json asks "
        "whether the gauge failure is specific to self-report by comparing the "
        "self-assessment study against the other-code one. Its other_code side is "
        "RECOMPUTED from the same raw readouts with the same estimator, so landing on "
        "the published values exactly is confirmation that the two analyses agree "
        "rather than a copy -- had they differed, one of them would be wrong. NARROW: "
        "covers only the other_code side, so the self-assessment side, the "
        "differences and the intervals must all stand on their own.",
    ),
    (
        (
            ("resolving_power_120.json", "summary."),
            ("channel_complementarity.json", "single_auroc"),
            ("budget_allocation.json", "wide.auroc_median"),
        ),
        "LEGITIMATE, AND THE MATCH IS EVIDENCE. channel_complementarity.json asks "
        "whether the verbalized and logit channels carry different information. Its "
        "single-channel AUROCs are recomputed by the same route as the published "
        "table -- average each method over the same six wordings, then score -- so "
        "agreement confirms the two analyses use the same construction rather than "
        "indicating a copy. NARROW: covers only the single-channel baselines, so the "
        "combined AUROCs, the increment and its interval must stand on their own; "
        "those are the numbers the claim actually rests on. budget_allocation.json's "
        "wide arm at full budget is the same value for the same reason -- six "
        "wordings at one polarity IS the published logit_single row -- and its deep "
        "arm, the gauge indices and the paired difference are not covered.",
    ),
    (
        (
            ("repeatability.json", "records"),
            ("ordering_artifact.json", "records"),
        ),
        "LEGITIMATE, AND THE MATCH IS THE POINT. Both probes evaluate the same "
        "prompts -- same programs, committed-default wording, positive polarity -- "
        "in separate processes run hours apart, and land on the same value. That is "
        "independent replication of the determinism finding those two artifacts "
        "exist to establish: a warm readout reproduces exactly across runs. Flagging "
        "it as a copy would be backwards. NARROW: covers only the per-call records, "
        "so the derived quantities each artifact reports -- the cold-versus-warm "
        "gaps, the order-induced SD and its bound -- are not covered and must stand "
        "on their own.",
    ),
)


def isDiscreteStatistic(value: float) -> bool:
    """True when the value is exactly a ratio of small counts, not a measurement.

    The digit-count heuristic assumes a continuous quantity, where seventeen
    matching digits cannot happen twice. Some statistics are not continuous. AUROC
    over fixed labels is rank-sum / (n_pos x n_neg): with 30 correct and 10
    incorrect programs it can take only 301 distinct values, so two different score
    vectors landing on the same one is expected rather than suspicious. That fired
    as a false positive on 214/300 = 0.7133333333333334, appearing in two artifacts
    computed from demonstrably different data.

    A float that IS a small rational carries about as much information as its
    numerator; one that is not is a continuous measurement. Checked structurally
    rather than by field name, so any future count-ratio is covered without being
    enumerated.

    The comparison is to a few ULPs, not exact. Exact equality missed a genuine
    count-ratio: a recall SPREAD of 0.14705882352941174 is 5/34, but computing it
    as a difference of two ratios left it one ULP from float(5/34), so the check
    called it a continuous measurement and reported a false copy. Discreteness is a
    property of how the number was produced, and arithmetic on discrete values
    stays discrete regardless of the last bit.
    """
    approximation = float(Fraction(value).limit_denominator(1000))
    return abs(approximation - value) <= 1e-12 * max(1.0, abs(value))


def significantDigits(value: float) -> int:
    """Digits in the repr, which is what makes a copy distinguishable from a match."""
    text = repr(float(value))
    if "e" in text or "E" in text:
        text = text.split("e")[0].split("E")[0]
    return len(text.replace("-", "").replace(".", "").lstrip("0"))


def walkFloats(node: Any, path: str = "") -> list[tuple[str, float]]:
    """Every float in a JSON tree, with the path that reaches it."""
    found: list[tuple[str, float]] = []
    if isinstance(node, dict):
        for key, child in node.items():
            if key in STRUCTURAL_KEYS:
                continue
            found.extend(walkFloats(child, f"{path}.{key}" if path else str(key)))
    elif isinstance(node, list):
        # Matrices and score vectors are raw measurements; a shared *element* is
        # not informative, a shared summary statistic is. Skip the bulk data.
        if len(node) > 12:
            return found
        for index, child in enumerate(node):
            found.extend(walkFloats(child, f"{path}[{index}]"))
    elif isinstance(node, bool):
        return found
    elif isinstance(node, float):
        found.append((path, node))
    return found


def isDeclared(
    sites: list[tuple[str, str]], patterns: tuple[tuple[str, str], ...]
) -> bool:
    """True only when EVERY site this value appears at is covered by the entry.

    Requiring full coverage is what keeps a declaration narrow: declaring the
    known copy between two artifacts does not also excuse the same value turning
    up in a third, which would be new information.
    """
    return all(
        any(name == pat_file and pat_path in path for pat_file, pat_path in patterns)
        for name, path in sites
    )


# Values the paper uses as a comparison FLOOR, and the artifact each must come
# from. A floor is the one number whose provenance changes a verdict: an effect is
# resolvable or not depending on which floor it is judged against, so a floor
# borrowed from another instrument silently rewrites the conclusion.
#
# Each entry is (file, path, source_file, source_path). The check reads both and
# requires they match to full precision -- here a shared value is REQUIRED, the
# inverse of the rule above, because this one is declared and directional.
FLOOR_BINDINGS: tuple[tuple[str, str, str, str], ...] = (
    (
        "make_figure_data.json",
        "sdc95",
        "gauge_verified_qwen2_5-coder_7b.json",
        "gauge.sdc95",
    ),
)


# Counts the PROSE asserts, bound to the artifact that must justify them.
#
# This guards a gap the other checks cannot see. Every fix changes what a number
# refers to, and the sentence describing it does not move automatically: when the
# figure was redrawn from a 37-pair run, its caption still read "over 46
# execution-verified pairs" and the paragraph above it still described the other
# sample. No comparison was mismatched and no value was copied, so nothing fired.
#
# Each entry is (regex over the .tex, artifact, path, label). The regex must have
# exactly one capture group holding the asserted integer.
TEX_BINDINGS: tuple[tuple[str, str, str, str], ...] = (
    (
        r"measured six ways, over the (\d+)\s*\n?\s*execution-verified pairs",
        "make_figure_data.json",
        "n_pairs",
        "figure caption pair count",
    ),
    (
        r"Over (\d+) canonical/mutant pairs whose mutants were confirmed",
        "gauge_verified_qwen2_5-coder_7b.json",
        "n_verified_pairs",
        "assay-sensitivity pair count",
    ),
    (
        # Repointed 2026-07-27: the sentence this guarded was rewritten, and the
        # check reported that rather than silently covering nothing -- which is
        # the behaviour it exists to have. The replication claim now names the
        # other sample, so the binding follows it there.
        r"independently drawn (\d+)-pair sample that supplies",
        "headline_ratio_ci.json",
        "n_verified_pairs",
        "replication pair count",
    ),
)


def checkTexBindings(job: str, extra_dirs: Sequence[Path] = ()) -> list[str]:
    """Verify each count asserted in the prose equals the artifact behind it."""
    import re

    source = Path(__file__).resolve().parent / f"{job}.tex"
    if not source.is_file():
        return []
    text = source.read_text(encoding="utf-8")
    search = [ARTIFACTS, *extra_dirs]

    def load(name: str) -> dict | None:
        for directory in search:
            candidate = directory / name
            if candidate.is_file():
                return json.loads(candidate.read_text(encoding="utf-8"))
        return None

    problems: list[str] = []
    for pattern, file, path, label in TEX_BINDINGS:
        match = re.search(pattern, text)
        if match is None:
            problems.append(
                f"{label}: the sentence this binding guards is gone from {job}.tex. "
                f"Either it was rewritten -- update the binding -- or the claim was "
                f"dropped and the binding should be too. A binding that matches "
                f"nothing silently guards nothing."
            )
            continue
        payload = load(file)
        if payload is None:
            problems.append(f"{label}: {file} not found")
            continue
        stated = int(match.group(1))
        actual = resolvePath(payload, path)
        if actual is None:
            problems.append(f"{label}: {file}:{path} missing")
        elif int(actual) != stated:
            problems.append(
                f"{label}: the text says {stated} but {file}:{path} is {actual}. "
                f"The prose describes a different sample than the one measured."
            )
    return problems


def resolvePath(payload: Any, dotted: str) -> Any:
    node = payload
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def checkFloorBindings(extra_dirs: Sequence[Path] = ()) -> list[str]:
    """Verify each declared floor equals the artifact it claims to come from.

    Written after a floor was drawn into the paper's central figure from the wrong
    instrument, with a prose provenance note beside it that no tool could read. A
    note explaining where a number came from is worth nothing if the number can
    change without it. This makes the claim executable.
    """
    problems: list[str] = []
    search = [ARTIFACTS, *extra_dirs]

    def load(name: str) -> dict | None:
        for directory in search:
            candidate = directory / name
            if candidate.is_file():
                return json.loads(candidate.read_text(encoding="utf-8"))
        return None

    for file, path, source_file, source_path in FLOOR_BINDINGS:
        target, source = load(file), load(source_file)
        if target is None:
            problems.append(f"{file}: not found in {[str(d) for d in search]}")
            continue
        if source is None:
            problems.append(f"{source_file}: not found (claimed source for {file})")
            continue
        have, want = resolvePath(target, path), resolvePath(source, source_path)
        if have is None:
            problems.append(f"{file}:{path} missing")
        elif want is None:
            problems.append(f"{source_file}:{source_path} missing")
        elif have != want:
            problems.append(
                f"{file}:{path} = {have!r} but its declared source "
                f"{source_file}:{source_path} = {want!r}. A floor measured by a "
                f"different instrument changes which effects count as resolvable."
            )
    return problems


def main() -> int:
    if not ARTIFACTS.is_dir():
        print(f"no artifact directory at {ARTIFACTS}")
        return 0

    here = Path(__file__).resolve().parent
    bound_problems = checkFloorBindings((here,)) + checkTexBindings("placebo", (here,))
    if bound_problems:
        print(f"FAIL  {len(bound_problems)} declared binding(s) broken.")
        for problem in bound_problems:
            print(f"      {problem}")
        return 1

    occurrences: dict[float, list[tuple[str, str]]] = defaultdict(list)
    for artifact in sorted(ARTIFACTS.glob("*.json")):
        try:
            payload = json.loads(artifact.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL  {artifact.name} is not readable JSON: {exc}")
            return 1
        for path, value in walkFloats(payload):
            if significantDigits(
                value
            ) >= SIGNIFICANT_DIGITS and not isDiscreteStatistic(value):
                occurrences[value].append((artifact.name, path))

    undeclared: list[tuple[float, list[tuple[str, str]]]] = []
    declared_hits = 0
    for value, sites in sorted(occurrences.items()):
        files = {name for name, _path in sites}
        if len(files) < 2:
            continue
        if any(isDeclared(sites, patterns) for patterns, _reason in DECLARED):
            declared_hits += 1
            continue
        undeclared.append((value, sites))

    if not undeclared:
        print(
            f"OK    no undeclared cross-artifact reuse "
            f"({declared_hits} declared shared value(s))"
        )
        return 0

    print(
        f"FAIL  {len(undeclared)} value(s) shared across artifacts to full precision."
    )
    print("      A re-measurement agrees to a few decimals, not to all of them.")
    print("      Either the number was copied, or the reuse belongs in DECLARED.")
    for value, sites in undeclared:
        print(f"\n  {value!r}")
        for name, path in sites:
            print(f"      {name}:{path}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

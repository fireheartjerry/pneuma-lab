"""The gauge card: a schema-validated reporting artifact for an elicited metric.

The card exists so that "we measured the model's confidence" stops being a claim
a reader has to take on faith. It carries the design, the variance decomposition,
the resolution statistics, the ceilings those imply, every standard remedy with
its own error bar, the placebo response, and the exact command that reproduces
it. A reviewer can ask for one the way a chemistry reviewer asks for a validation
report.

JSON has no NaN or Infinity. Both occur legitimately here (an undefined statistic;
a placebo-dominance ratio with a zero denominator), so they are serialized as
`null` and the string `"inf"` respectively rather than being silently zeroed.
"""

from __future__ import annotations

import json
import math
import zlib
from collections.abc import Sequence
from pathlib import Path

from .anova import varianceComponents
from .cube import CONDITION_FACETS, ResponseCube
from .placebo import PlaceboReport, placeboReport
from .remedies import RemedyResult, runRemedies
from .resolution import (
    MARGINAL_D,
    MARGINAL_ICC,
    MARGINAL_NDC,
    USABLE_D,
    USABLE_ICC,
    USABLE_NDC,
    USABLE_PCT_GRR,
    discriminationIndex,
    gaugeResolution,
)
from .stats import Interval, bootstrapCi
from .theory import USABILITY_FLOOR, aggregationAsymptote, ceilings, requiredK

TOOL_VERSION = "pneuma-lab.gauge/0.1.0"

VERDICT_RULE = (
    f"USABLE iff %GRR<={USABLE_PCT_GRR:g} and ndc>={USABLE_NDC} and ICC>={USABLE_ICC:g} "
    f"and D>={USABLE_D:g}; MARGINAL iff ndc>={MARGINAL_NDC} and ICC>={MARGINAL_ICC:g} "
    f"and D>={MARGINAL_D:g}; DEGENERATE iff effective support<2; otherwise UNINTERPRETABLE"
)


def _clean(value):
    """Make a value JSON-representable without lying about it."""
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return value
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value


def cubeDigest(cube: ResponseCube) -> str:
    blob = "\n".join(
        json.dumps(r.asDict(), sort_keys=True, ensure_ascii=False) for r in cube.rows
    ).encode("utf-8")
    return f"crc32:{zlib.crc32(blob):08x}"


def buildCard(
    cube: ResponseCube,
    *,
    card_id: str,
    condition_facets: Sequence[str] = ("wording_id", "scale_id"),
    truth: dict[str, int] | None = None,
    prompt_digest: str = "unknown",
    command: str = "python -m pneuma_lab.gauge run",
    draws: int = 2000,
    seed: int = 20260728,
    remedies: Sequence[RemedyResult] | None = None,
    placebo: PlaceboReport | None = None,
    include_placebo: bool = True,
) -> dict:
    """Assemble a gauge card from a response cube."""
    analysis_cube = cube.filter(arm="base") if "base" in cube.values("arm") else cube
    matrix = analysis_cube.balancedMatrix(condition_facets)
    if not matrix.usable():
        raise ValueError(
            f"design too small for a card: items={matrix.n_items} "
            f"conditions={matrix.n_conditions} replicates={matrix.n_reps}"
        )
    resolution = gaugeResolution(matrix)
    vc = resolution.components

    rows = matrix.itemRows()
    items = sorted(rows)

    def _sub(sample):
        return {
            (f"{item}#{n}", cond): list(values)
            for n, item in enumerate(sample)
            for cond, values in rows[item].items()
        }

    d_ci = bootstrapCi(
        items,
        lambda s: discriminationIndex(_sub(s)) if len(s) >= 2 else None,
        draws=draws,
        seed=seed,
    )
    icc_ci = bootstrapCi(
        items,
        lambda s: _iccOf(_sub(s)) if len(s) >= 2 else None,
        draws=draws,
        seed=seed + 2,
    )

    base_rate = _baseRate(truth, items)
    ceiling = ceilings(resolution.icc, base_rate)

    if remedies is None:
        remedies = runRemedies(analysis_cube, truth=truth, draws=draws, seed=seed)

    placebo_block = None
    if include_placebo:
        if placebo is None and {"base", "sham"} <= set(cube.values("arm")):
            try:
                placebo = placeboReport(cube, draws=draws, seed=seed)
            except ValueError:
                placebo = None
        if placebo is not None:
            placebo_block = {
                "pi": placebo.pi,
                "pi_ci": placebo.pi_ci.asDict(),
                "pi_with_interaction": placebo.pi_with_interaction,
                "contrast": placebo.contrast,
                "contrast_ci": placebo.contrast_ci.asDict(),
                "p_value": placebo.p_value,
                "cohens_d": placebo.cohens_d,
                "mde": placebo.mde,
                "var_item": placebo.var_item,
                "var_arm": placebo.var_arm,
            }

    card = {
        "manifest_kind": "gauge_card",
        "schema_version": "0.1.0",
        "card_id": card_id,
        "channel": {
            "model": "+".join(map(str, cube.values("model"))),
            "provenance": "+".join(map(str, cube.values("provenance"))),
            "temperature": float(cube.values("temperature")[0])
            if cube.values("temperature")
            else 0.0,
            "scales": [str(s) for s in cube.values("scale_id")],
            "wordings": [str(w) for w in cube.values("wording_id")],
            "arms": [str(a) for a in cube.values("arm")],
            "prompt_digest": prompt_digest,
        },
        "design": {
            "n_items": matrix.n_items,
            "n_conditions": matrix.n_conditions,
            "n_replicates": matrix.n_reps,
            "condition_facets": list(condition_facets),
            "total_observations": len(cube),
            "parse_failure_rate": cube.parseFailureRate(),
            "dropped_items": list(matrix.dropped_items),
        },
        "variance_components": {
            k: v
            for k, v in vc.asDict().items()
            if k
            in {
                "var_item",
                "var_condition",
                "var_interaction",
                "var_repeatability",
                "var_reproducibility",
                "var_grr",
                "var_total",
                "truncated",
            }
        },
        "resolution": {
            "pct_grr": resolution.pct_grr,
            "ndc": resolution.ndc,
            "icc": resolution.icc,
            "icc_ci": icc_ci.asDict(),
            "d": resolution.d,
            "d_ci": d_ci.asDict(),
            "resolving_power": resolution.resolving_power,
            "s_eff": resolution.s_eff,
            "saturation": resolution.saturation,
            "selection_stability": resolution.selection_stability,
            "cross_condition_stability": resolution.cross_condition_stability,
        },
        "ceilings": ceiling.asDict(),
        "prescription": _prescription(vc, matrix.n_conditions),
        "remedies": [r.asDict() for r in remedies],
        "placebo": placebo_block,
        "verdict": resolution.verdict,
        "verdict_rule": VERDICT_RULE,
        "reproduction": {
            "command": command,
            "cube_digest": cubeDigest(cube),
            "tool_version": TOOL_VERSION,
        },
    }
    return _clean(card)


def _prescription(vc, n_conditions: int, *, target: float = USABILITY_FLOOR) -> dict:
    """What would it cost to make this channel usable? Diagnosis is easy to ignore."""
    k_reps = requiredK(vc, systematic="condition_locked", target=target)
    k_words = requiredK(vc, systematic="none", target=target)
    asymptote = aggregationAsymptote(
        var_item=vc.var_item, var_systematic=vc.var_condition + vc.var_interaction
    )
    if k_reps is not None:
        note = (
            f"averaging {k_reps} samples at a fixed wording reaches ICC {target:g}; "
            f"the asymptote at that wording is {asymptote:.3f}"
        )
        calls = k_reps
    elif k_words is not None:
        note = (
            f"resampling at a fixed wording cannot reach ICC {target:g} (asymptote "
            f"{asymptote:.3f}); averaging over {k_words} distinct wordings can"
        )
        calls = k_words
    else:
        note = (
            f"ICC {target:g} is unreachable by aggregation: item variance is "
            f"{vc.var_item:.3g} against a gauge variance of {vc.var_grr:.3g}"
        )
        calls = None
    return {
        "target_icc": target,
        "required_replicates": k_reps,
        "required_wordings": k_words,
        "asymptote": asymptote,
        "estimated_calls_per_item": calls,
        "note": note,
    }


def _iccOf(cells) -> float:
    vc = varianceComponents(cells)
    return vc.var_item / vc.var_total if vc.var_total > 0 else 0.0


def _baseRate(truth: dict[str, int] | None, items: Sequence[str]) -> float:
    if not truth:
        return 0.5
    labels = [truth[i] for i in items if i in truth]
    if not labels:
        return 0.5
    rate = sum(labels) / len(labels)
    return min(0.99, max(0.01, rate))


def validateCard(card: dict) -> None:
    """Validate against `schemas/gauge-card.schema.json`. Raises on violation."""
    import jsonschema

    from pneuma_lab.schemas import load_schema

    jsonschema.validate(instance=card, schema=load_schema("gauge-card.schema.json"))


def writeCard(card: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(card, indent=4, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def renderCard(card: dict) -> str:
    """Human-readable Markdown rendering of a card."""
    res = card["resolution"]
    vc = card["variance_components"]
    design = card["design"]
    ceil = card["ceilings"]
    lines = [
        f"# Gauge card — {card['card_id']}",
        "",
        f"**Verdict: {card['verdict']}**",
        "",
        f"- rule: `{card['verdict_rule']}`",
        f"- channel: `{card['channel']['model']}` / provenance `{card['channel']['provenance']}` "
        f"/ T={card['channel']['temperature']} / prompt `{card['channel']['prompt_digest']}`",
        f"- design: {design['n_items']} items x {design['n_conditions']} conditions x "
        f"{design['n_replicates']} replicates = {design['total_observations']} observations "
        f"(parse-failure rate {design['parse_failure_rate']:.3f})",
        "",
        "## Variance decomposition",
        "",
        "| component | variance | share of total variance |",
        "| --- | ---: | ---: |",
    ]
    total = vc["var_total"] or 1.0
    for label, key in (
        ("item (signal)", "var_item"),
        ("repeatability (re-ask)", "var_repeatability"),
        ("condition main effect (shift)", "var_condition"),
        ("item x condition (reorder)", "var_interaction"),
        ("reproducibility", "var_reproducibility"),
        ("gauge (GRR)", "var_grr"),
    ):
        value = vc.get(key) or 0.0
        lines.append(f"| {label} | {value:.6f} | {100.0 * value / total:.1f}% |")
    lines.append("")
    lines.append(
        "The `item x condition` term is the one that matters for ranking: a condition *main "
        "effect* shifts every reading and cancels in any ranking, while the interaction "
        "reorders items and does not. Neither greedy decoding nor replicate averaging removes "
        "it."
    )
    if vc.get("truncated"):
        lines.append("")
        lines.append(f"Truncated to zero: `{', '.join(vc['truncated'])}`.")

    lines += [
        "",
        "## Resolution",
        "",
        "| statistic | value | 95% CI |",
        "| --- | ---: | --- |",
        f"| %GRR (ratio of SDs, AIAG bar 30%) | {res['pct_grr']:.1f}% | — |",
        f"| ndc (distinct categories) | {res['ndc']} | — |",
        f"| ICC | {_fmt(res['icc'])} | {_ci(res.get('icc_ci'))} |",
        f"| discrimination index D | {_fmt(res['d'])} | {_ci(res.get('d_ci'))} |",
        f"| resolving power | {_fmt(res['resolving_power'])} | — |",
        f"| effective support | {_fmt(res['s_eff'])} levels | — |",
        _saturationRow(res),
        _selectionRow(res),
        _crossRow(res),
        "",
        "## Ceilings implied by this reliability",
        "",
        f"- max attainable |r| with any criterion: **{_fmt(ceil['validity_r'])}**",
        f"- max attainable AUROC at base rate {ceil['base_rate']:.2f}: **{_fmt(ceil['auroc'])}**",
        "- these are ceilings at *any* sample size; more data cannot move them",
        "",
        _prescriptionBlock(card),
        "## Remedies",
        "",
        "| remedy | statistic | value | 95% CI | floor | verdict |",
        "| --- | --- | ---: | --- | ---: | --- |",
    ]
    for remedy in card["remedies"]:
        lines.append(
            f"| {remedy['name']} | {remedy['statistic']} | {_fmt(remedy['value'])} | "
            f"{_ci(remedy.get('ci'))} | {_fmt(remedy.get('floor'))} | **{remedy['verdict']}** |"
        )
    lines.append("")
    for remedy in card["remedies"]:
        lines.append(f"- **{remedy['name']}** — {remedy['note']}")

    placebo = card.get("placebo")
    if placebo:
        lines += [
            "",
            "## Placebo response",
            "",
            f"- placebo-dominance ratio Pi = **{_fmt(placebo['pi'])}** "
            f"(sham variance {_fmt(placebo.get('var_arm'))} / item variance {_fmt(placebo.get('var_item'))})",
            f"- sham-vs-base contrast = {_fmt(placebo['contrast'])} "
            f"(p = {_fmt(placebo['p_value'])}, minimum detectable effect = {_fmt(placebo.get('mde'))})",
        ]

    lines += [
        "",
        "## Reproduction",
        "",
        f"```txt\n{card['reproduction']['command']}\n```",
        "",
        f"cube digest `{card['reproduction']['cube_digest']}`, tool `{card['reproduction']['tool_version']}`",
        "",
    ]
    return "\n".join(lines)


def _prescriptionBlock(card: dict) -> str:
    rx = card.get("prescription")
    if not rx:
        return ""
    calls = rx.get("estimated_calls_per_item") or "unbounded"
    lines = [
        "## What it would cost to fix",
        "",
        f"- {rx['note']}",
        f"- estimated elicitations per item: {calls}",
        "",
    ]
    return "\n".join(lines)


def _selectionRow(res: dict) -> str:
    """Triage-queue reproducibility: what a pipeline that ranks and verifies actually gets."""
    sel = res.get("selection_stability")
    if not sel or sel.get("jaccard") is None:
        return "| selection stability | n/a | — |"
    return (
        f"| selection stability (bottom {sel['q']:.0%}) | {_fmt(sel['jaccard'])} "
        f"| random floor {_fmt(sel['random_floor'])} |"
    )


def _saturationRow(res: dict) -> str:
    """Readings pinned to a scale endpoint are censored and cannot order each other."""
    sat = res.get("saturation")
    if not sat:
        return "| saturation | n/a | — |"
    return (
        f"| saturation (readings at a scale endpoint) | {_fmt(sat['saturated'])} "
        f"| {_fmt(sat['at_high'])} at ceiling |"
    )


def _crossRow(res: dict) -> str:
    """The same queue question, but the second pass rephrases instead of re-asking."""
    sel = res.get("cross_condition_stability")
    if not sel or sel.get("jaccard") is None:
        return "| selection stability (rephrased) | n/a | — |"
    return (
        f"| selection stability, rephrased | {_fmt(sel['jaccard'])} "
        f"| random floor {_fmt(sel['random_floor'])} |"
    )


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    return f"{value:.4f}"


def _ci(interval) -> str:
    if not interval:
        return "—"
    low, high = interval.get("low"), interval.get("high")
    if low is None or high is None:
        return "—"
    return f"[{low:.4f}, {high:.4f}]"


__all__ = [
    "TOOL_VERSION",
    "VERDICT_RULE",
    "buildCard",
    "cubeDigest",
    "renderCard",
    "validateCard",
    "writeCard",
]

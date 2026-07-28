"""Run the G-1 pre-registered analysis over the collected cube.

Executes exactly the analysis order locked in
`docs/research/experiments/g1-gauge-preregistration.md` section 6, writes one
gauge card per facet cell to `build/gauge/g1/cards/`, and emits
`build/gauge/g1/summary.json` containing every pre-registered number.

Usage:
    python scripts/gauge_g1_analysis.py [--run-dir build/gauge/g1] [--draws 2000]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pneuma_lab.gauge.card import buildCard, renderCard, validateCard, writeCard  # noqa: E402
from pneuma_lab.gauge.cube import ResponseCube  # noqa: E402
from pneuma_lab.gauge.items import loadItems, truthLabels  # noqa: E402
from pneuma_lab.gauge.placebo import placeboReport  # noqa: E402
from pneuma_lab.gauge.remedies import runRemedies  # noqa: E402
from pneuma_lab.gauge.resolution import effectiveSupport, gaugeResolution  # noqa: E402
from pneuma_lab.gauge.stats import auroc, bootstrapCi  # noqa: E402
from pneuma_lab.gauge.theory import ceilings  # noqa: E402


def _loadStage(run_dir: Path, name: str) -> ResponseCube | None:
    path = run_dir / f"cube-{name}.jsonl"
    return ResponseCube.fromJsonl(path) if path.exists() else None


def _cell(cube: ResponseCube, facets, label: str) -> dict:
    matrix = cube.balancedMatrix(facets)
    if not matrix.usable():
        return {
            "label": label,
            "usable": False,
            "reason": "design too small after balancing",
        }
    res = gaugeResolution(matrix)
    flat = [v for values in matrix.cells.values() for v in values]
    return {
        "label": label,
        "usable": True,
        "n_items": matrix.n_items,
        "n_conditions": matrix.n_conditions,
        "n_reps": matrix.n_reps,
        "n_obs": len(cube),
        "parse_failure_rate": cube.parseFailureRate(),
        "var_item": res.components.var_item,
        "var_repeatability": res.components.var_repeatability,
        "var_reproducibility": res.components.var_reproducibility,
        "var_grr": res.components.var_grr,
        "truncated": list(res.components.truncated),
        "pct_grr": res.pct_grr,
        "ndc": res.ndc,
        "icc": res.icc,
        "d": res.d,
        "resolving_power": res.resolving_power,
        "s_eff": res.s_eff,
        "mean": res.components.grand_mean,
        "distinct_values": len({round(v, 6) for v in flat}),
        "verdict": res.verdict,
    }


def _validity(cube: ResponseCube, truth: dict[str, int]) -> dict:
    scores, labels = [], []
    for r in cube.rows:
        if r.parse_ok and r.value is not None and r.item_id in truth:
            scores.append(float(r.value))
            labels.append(int(truth[r.item_id]))
    if not scores:
        return {"auroc": None, "n": 0}
    base = sum(labels) / len(labels)
    return {"auroc": auroc(scores, labels), "n": len(scores), "base_rate": base}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default="build/gauge/g1")
    parser.add_argument("--draws", type=int, default=2000)
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    cards_dir = run_dir / "cards"
    truth = truthLabels(loadItems())
    draws = args.draws

    stages = {
        name: _loadStage(run_dir, name)
        for name in (
            "core",
            "scales",
            "temperature0",
            "placebo",
            "provenance_self",
            "provenance_foreign",
            "families",
        )
    }
    available = {k: v for k, v in stages.items() if v is not None}
    print(f"stages available: {sorted(available)}")
    if "core" not in available:
        print("core stage missing; nothing to analyse", file=sys.stderr)
        return 1

    summary: dict = {"stages": {k: len(v) for k, v in available.items()}, "cells": {}}

    # --- 1. parse-failure and support audit, before anything else -------------
    audit = {}
    for name, cube in available.items():
        values = [r.value for r in cube.rows if r.parse_ok and r.value is not None]
        audit[name] = {
            "n": len(cube),
            "parse_failure_rate": cube.parseFailureRate(),
            "s_eff": effectiveSupport(values) if values else 0.0,
            "distinct_values": len({round(v, 6) for v in values}),
            "top_values": sorted(
                ((round(v, 4), values.count(v)) for v in {round(x, 4) for x in values}),
                key=lambda t: -t[1],
            )[:6],
        }
    summary["audit"] = audit
    print("\n=== 1. parse / support audit ===")
    for name, row in audit.items():
        print(
            f"{name:<20} n={row['n']:<6} parse_fail={row['parse_failure_rate']:.3f} "
            f"S_eff={row['s_eff']:.2f} distinct={row['distinct_values']}"
        )

    # --- 2. primary pooled analysis (G1-H1) ----------------------------------
    core = available["core"]
    primary = _cell(core, ("wording_id",), "primary_core")
    summary["cells"]["primary_core"] = primary
    print("\n=== 2. primary pooled analysis (G1-H1) ===")
    _printCell(primary)

    validity = _validity(core, truth)
    ceil = ceilings(primary["icc"], validity.get("base_rate") or 0.5)
    summary["validity"] = {
        "observed": validity,
        "ceiling_r": ceil.validity_r,
        "ceiling_auroc": ceil.auroc,
    }
    print(
        f"observed AUROC={_f(validity['auroc'])} (n={validity['n']}), "
        f"ceiling from reliability={ceil.auroc:.4f}"
    )

    if "scales" in available:
        wide = _cell(
            core.merge(available["scales"]), ("wording_id", "scale_id"), "wide_pooled"
        )
        summary["cells"]["wide_pooled"] = wide
        print("\n--- wide pooled (wording x scale) ---")
        _printCell(wide)

    # --- 3. facet cells (G1-H2, H3, H4) --------------------------------------
    print("\n=== 3. facet cells ===")
    if "scales" in available:
        for scale in available["scales"].values("scale_id"):
            cell = _cell(
                available["scales"].filter(scale_id=scale),
                ("wording_id",),
                f"scale::{scale}",
            )
            summary["cells"][f"scale::{scale}"] = cell
            _printCell(cell)

    if "temperature0" in available:
        t0 = _cell(available["temperature0"], ("wording_id",), "temperature::0.0")
        summary["cells"]["temperature::0.0"] = t0
        _printCell(t0)
        t7 = _cell(
            core.filter(wording_id=("w1", "w2", "w3", "w4")),
            ("wording_id",),
            "temperature::0.7",
        )
        summary["cells"]["temperature::0.7"] = t7
        _printCell(t7)

    for arm_name, stage_name in (
        ("self_authored", "provenance_self"),
        ("foreign", "provenance_foreign"),
    ):
        if stage_name in available:
            cell = _cell(
                available[stage_name], ("wording_id",), f"provenance::{arm_name}"
            )
            summary["cells"][f"provenance::{arm_name}"] = cell
            _printCell(cell)

    if "families" in available:
        pooled_models = core.filter(wording_id=("w1", "w2", "w3")).merge(
            available["families"]
        )
        for model in pooled_models.values("model"):
            cell = _cell(
                pooled_models.filter(model=model), ("wording_id",), f"model::{model}"
            )
            summary["cells"][f"model::{model}"] = cell
            _printCell(cell)

    # --- 4. remedy battery (G1-H5) -------------------------------------------
    print("\n=== 4. remedy battery (G1-H5) ===")
    remedy_cube = core
    judge = None
    if "families" in available:
        remedy_cube = core.filter(wording_id=("w1", "w2", "w3")).merge(
            available["families"]
        )
        judge = "llama3.1:8b" if "llama3.1:8b" in remedy_cube.values("model") else None
    remedies = runRemedies(
        remedy_cube,
        truth=truth,
        primary="qwen2.5-coder:7b",
        judge=judge,
        draws=draws,
    )
    summary["remedies"] = [r.asDict() for r in remedies]
    for r in remedies:
        print(
            f"{r.name:<20} {r.statistic:<34} {_f(r.value)} "
            f"[{_f(r.ci.low)}, {_f(r.ci.high)}] floor={_f(r.floor)} -> {r.verdict}"
        )
        print(f"    {r.note}")

    # --- 5. placebo (G1-H6) --------------------------------------------------
    print("\n=== 5. placebo (G1-H6) ===")
    if "placebo" in available:
        report = placeboReport(available["placebo"], draws=draws)
        summary["placebo"] = report.asDict()
        print(
            f"Pi={_f(report.pi)} CI=[{_f(report.pi_ci.low)}, {_f(report.pi_ci.high)}]  "
            f"contrast={_f(report.contrast)} p={_f(report.p_value)} "
            f"d={_f(report.cohens_d)} MDE={_f(report.mde)}"
        )
        print(f"    var_arm={report.var_arm:.6g}  var_item={report.var_item:.6g}")
        treated = available["placebo"].filter(arm=("base", "treated"))
        try:
            treated_report = placeboReport(treated, sham_arm="treated", draws=draws)
            summary["treated_contrast"] = treated_report.asDict()
            print(
                f"treated-vs-base contrast={_f(treated_report.contrast)} "
                f"p={_f(treated_report.p_value)} (a genuinely informative block)"
            )
        except ValueError as exc:
            print(f"treated contrast unavailable: {exc}")
    else:
        print("placebo stage not present")

    # --- 6. cards + determinism ---------------------------------------------
    print("\n=== 6. cards ===")
    written = []
    card_specs = [("pooled", core, ("wording_id",), remedies)]
    for name, stage_name in (
        ("self_authored", "provenance_self"),
        ("foreign_matched", "provenance_foreign"),
    ):
        if stage_name in available:
            card_specs.append((name, available[stage_name], ("wording_id",), None))
    if "families" in available:
        pooled_models = core.filter(wording_id=("w1", "w2", "w3")).merge(
            available["families"]
        )
        for model in pooled_models.values("model"):
            card_specs.append(
                (
                    f"model-{str(model).replace(':', '_')}",
                    pooled_models.filter(model=model),
                    ("wording_id",),
                    None,
                )
            )

    for card_id, cube, facets, preset in card_specs:
        try:
            card = buildCard(
                cube,
                card_id=card_id,
                condition_facets=facets,
                truth=truth,
                draws=min(draws, 500),
                remedies=preset,
                command=f"python -m pneuma_lab.gauge analyze --cube {run_dir}/cube.jsonl",
            )
            validateCard(card)
            writeCard(card, cards_dir / f"{card_id}.json")
            (cards_dir / f"{card_id}.md").write_text(
                renderCard(card), encoding="utf-8", newline="\n"
            )
            written.append({"card_id": card_id, "verdict": card["verdict"]})
            print(f"  {card_id:<34} {card['verdict']}")
        except ValueError as exc:
            print(f"  {card_id:<34} SKIPPED ({exc})")
    summary["cards"] = written

    # determinism: rebuild the primary card and compare bytes
    a = buildCard(
        core, card_id="pooled", condition_facets=("wording_id",), truth=truth, draws=200
    )
    b = buildCard(
        core, card_id="pooled", condition_facets=("wording_id",), truth=truth, draws=200
    )
    summary["deterministic"] = json.dumps(a, sort_keys=True) == json.dumps(
        b, sort_keys=True
    )
    print(f"\ndeterminism (identical card on rebuild): {summary['deterministic']}")

    out = run_dir / "summary.json"
    out.write_text(
        json.dumps(summary, indent=4, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\nsummary -> {out}")
    return 0


def _printCell(cell: dict) -> None:
    if not cell.get("usable"):
        print(f"{cell['label']:<34} UNUSABLE ({cell.get('reason')})")
        return
    print(
        f"{cell['label']:<34} ndc={cell['ndc']:<3} ICC={cell['icc']:.4f} D={cell['d']:.4f} "
        f"%GRR={cell['pct_grr']:.1f} S_eff={cell['s_eff']:.2f} distinct={cell['distinct_values']:<4} "
        f"mean={cell['mean']:.3f}  {cell['verdict']}"
    )


def _f(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    if isinstance(value, float) and math.isinf(value):
        return "inf"
    if isinstance(value, float) and math.isnan(value):
        return "nan"
    return f"{value:.4f}"


if __name__ == "__main__":
    raise SystemExit(main())

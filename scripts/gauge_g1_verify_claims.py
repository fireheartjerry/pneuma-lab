"""Recompute every headline number quoted in the G-1 write-ups, from the cubes.

Documents drift. This recomputes each claim from `build/gauge/g1/cube-*.jsonl` and
compares it against the value asserted in the paper and results doc, so a stale
figure fails loudly instead of being quoted forever.

Usage:
    python scripts/gauge_g1_verify_claims.py [--run-dir build/gauge/g1]

Exit code 0 if every claim matches, 1 otherwise.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pneuma_lab.gauge.cube import ResponseCube  # noqa: E402
from pneuma_lab.gauge.items import loadItems, truthLabels  # noqa: E402
from pneuma_lab.gauge.resolution import effectiveSupport, gaugeResolution  # noqa: E402
from pneuma_lab.gauge.stats import auroc, expectedCalibrationError, mean  # noqa: E402
from pneuma_lab.gauge.theory import aurocCeiling  # noqa: E402


def _load(run_dir: Path, name: str) -> ResponseCube | None:
    path = run_dir / f"cube-{name}.jsonl"
    return ResponseCube.fromJsonl(path) if path.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default="build/gauge/g1")
    parser.add_argument("--tol", type=float, default=0.005)
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    truth = truthLabels(loadItems())

    claims: list[tuple[str, str, float]] = []

    def claim(label: str, asserted: str, computed: float) -> None:
        """`asserted` is the literal string quoted in the docs, so its precision is known."""
        claims.append((label, asserted, computed))

    core = _load(run_dir, "core")
    if core is None:
        print("core stage missing", file=sys.stderr)
        return 1

    m = core.balancedMatrix(("wording_id",))
    r = gaugeResolution(m)
    vc = r.components
    claim("core ndc", "1", r.ndc)
    claim("core ICC", "0.512", r.icc)
    claim("core D", "0.684", r.d)
    claim("core %GRR", "69.9", r.pct_grr)
    claim("core resolving power", "0.469", r.resolving_power)
    claim("core S_eff (balanced matrix)", "6.90", r.s_eff)
    claim("core item variance share", "51.2", 100 * vc.var_item / vc.var_total)
    claim("core saturation at ceiling", "0.383", r.saturation["at_high"])
    claim("core selection stability q=0.2", "0.568", r.selection_stability["jaccard"])

    scores = [x.value for x in core.rows if x.parse_ok and x.item_id in truth]
    labels = [truth[x.item_id] for x in core.rows if x.parse_ok and x.item_id in truth]
    claim("core single-shot AUROC", "0.782", auroc(scores, labels))
    claim("core ECE", "0.378", expectedCalibrationError(scores, labels))
    claim("core mean confidence", "0.873", mean(scores))
    claim(
        "core S_eff (all parsed responses)",
        "6.73",
        effectiveSupport([x.value for x in core.rows if x.parse_ok]),
    )
    claim(
        "core distinct values",
        "35",
        len({round(x.value, 6) for x in core.rows if x.parse_ok}),
    )

    rows = m.itemRows()
    items = sorted(rows)
    per_item = {
        i: math.fsum(v for c in rows[i] for v in rows[i][c])
        / sum(len(rows[i][c]) for c in rows[i])
        for i in items
    }
    lab = [truth[i] for i in items]
    claim("core full-average AUROC", "0.906", auroc([per_item[i] for i in items], lab))
    claim("core AUROC ceiling", "0.926", aurocCeiling(r.icc, sum(lab) / len(lab)))
    cor = [per_item[i] for i in items if truth[i] == 1]
    bug = [per_item[i] for i in items if truth[i] == 0]
    claim("mean on correct code", "0.963", mean(cor))
    claim("mean on buggy code", "0.782", mean(bug))
    claim("correct-buggy separation", "0.181", mean(cor) - mean(bug))

    # heteroscedasticity
    def withinSd(item: str) -> float:
        vs = []
        for series in rows[item].values():
            mu = math.fsum(series) / len(series)
            vs.append(math.fsum((x - mu) ** 2 for x in series) / len(series))
        return math.sqrt(math.fsum(vs) / len(vs))

    sd_cor = mean([withinSd(i) for i in items if truth[i] == 1])
    sd_bug = mean([withinSd(i) for i in items if truth[i] == 0])
    claim("repeatability SD, correct", "0.062", sd_cor)
    claim("repeatability SD, buggy", "0.158", sd_bug)
    claim("heteroscedasticity ratio", "2.54", sd_bug / sd_cor)

    # wording spread
    wording_means = [
        mean([x.value for x in core.rows if x.wording_id == w and x.parse_ok])
        for w in core.values("wording_id")
    ]
    claim("wording spread", "0.098", max(wording_means) - min(wording_means))
    claim(
        "wording spread as fraction of correctness separation",
        "0.54",
        (max(wording_means) - min(wording_means)) / (mean(cor) - mean(bug)),
    )

    t0 = _load(run_dir, "temperature0")
    if t0 is not None:
        r0 = gaugeResolution(t0.balancedMatrix(("wording_id",)))
        v0 = r0.components
        claim("T=0 repeatability variance", "0.0", v0.var_repeatability)
        claim("T=0 ndc", "2", r0.ndc)
        claim("T=0 ICC", "0.710", r0.icc)
        claim("T=0 D", "0.841", r0.d)
        claim("T=0 %GRR", "53.9", r0.pct_grr)
        claim("T=0 item share", "71.0", 100 * v0.var_item / v0.var_total)
        claim("T=0 interaction share", "24.8", 100 * v0.var_interaction / v0.var_total)
        claim(
            "T=0 wording main effect share",
            "4.2",
            100 * v0.var_condition / v0.var_total,
        )
        claim("T=0 queue overlap re-asked", "0.956", r0.selection_stability["jaccard"])
        claim(
            "T=0 queue overlap rephrased",
            "0.646",
            r0.cross_condition_stability["jaccard"],
        )

    placebo = _load(run_dir, "placebo")
    if placebo is not None:
        from pneuma_lab.gauge.placebo import placeboReport

        rep = placeboReport(placebo, draws=400)
        claim("placebo Pi", "0.0", rep.pi)
        claim("placebo contrast", "0.0044", rep.contrast)
        claim("placebo p-value", "0.72", rep.p_value)
        treated = placeboReport(
            placebo.filter(arm=("base", "treated")), sham_arm="treated", draws=400
        )
        claim("treated contrast", "-0.0876", treated.contrast)

    self_arm = _load(run_dir, "provenance_self")
    fore_arm = _load(run_dir, "provenance_foreign")
    if self_arm is not None and fore_arm is not None:
        rs = gaugeResolution(self_arm.balancedMatrix(("wording_id",)))
        rf = gaugeResolution(fore_arm.balancedMatrix(("wording_id",)))
        claim("self-authored D", "0.562", rs.d)
        claim("foreign D", "0.567", rf.d)
        claim("self-authored ndc", "0", rs.ndc)
        claim("foreign ndc", "0", rf.ndc)
        sv = mean([x.value for x in self_arm.rows if x.parse_ok])
        fv = mean([x.value for x in fore_arm.rows if x.parse_ok])
        claim("self-enhancement delta", "-0.010", sv - fv)

    # remedy battery figures quoted in section 9 / 6.11
    from pneuma_lab.gauge.remedies import calibration, selfConsistency, thresholding, wordingAveraging

    claim("thresholding kappa", "0.727", thresholding(core, draws=300).value)
    claim("thresholding flip rate", "0.122", thresholding(core, draws=10).detail["flip_rate"])
    cal = calibration(core, truth, draws=300)
    claim("calibration D unchanged", "0.684", cal.value)
    claim(
        "calibration D delta (T2: exactly zero)",
        "0.0",
        abs(cal.detail["after"]["platt"]["d"] - cal.detail["before"]["d"]),
    )
    claim(
        "calibration ECE drop",
        "0.3106",
        cal.detail["before"]["ece"] - cal.detail["after"]["platt"]["ece"],
    )
    claim("wording-averaging ICC", "0.900", wordingAveraging(core, draws=300).value)
    sc = selfConsistency(core, draws=300)
    claim("self-consistency ICC at k=4", "0.760", sc.value)
    claim("self-consistency asymptote", "0.870", sc.detail["asymptote"])

    scales = _load(run_dir, "scales")
    if scales is not None:
        means = {}
        for scale in scales.values("scale_id"):
            sub = scales.filter(scale_id=scale)
            rr = gaugeResolution(sub.balancedMatrix(("wording_id",)))
            means[scale] = rr.components.grand_mean
            claim(f"scale {scale} ndc", "1", rr.ndc)
        claim("scale mean spread", "0.115", max(means.values()) - min(means.values()))

    width = max(len(c[0]) for c in claims)
    failures = 0
    print(f"{'claim':<{width}}  {'quoted':>10} {'computed':>10}  ok")
    for label, asserted, computed in claims:
        target = float(asserted)
        # A quoted figure is verified if it is the correct rounding of the computed
        # value: the tolerance is half the last decimal place actually written down.
        decimals = len(asserted.split(".")[1]) if "." in asserted else 0
        tol = 0.5 * (10**-decimals)
        ok = (
            computed is not None
            and math.isfinite(computed)
            and abs(computed - target) <= tol
        )
        failures += 0 if ok else 1
        print(
            f"{label:<{width}}  {asserted:>10} {computed:>10.4f}  "
            f"{'ok' if ok else 'MISMATCH'}"
        )

    print(f"\n{len(claims) - failures}/{len(claims)} claims verified")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

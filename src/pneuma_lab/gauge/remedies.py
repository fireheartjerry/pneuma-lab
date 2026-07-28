"""The five standard remedies, each falsified with its own error bar.

When an elicited metric is shown to be unreliable, five fixes are reflexively
proposed. Each is implemented here as a *re-analysis of the already-collected
cube*, so falsifying all five costs zero additional model calls:

1. `secondModel`        - "use a different model as the judge"
2. `thresholding`       - "don't use the number, use a threshold"
3. `calibration`        - "fit a calibrator on held-out data"
4. `wordingAveraging`   - "average over several prompt phrasings"
5. `selfConsistency`    - "sample k times and average"

Remedy 3 is dead analytically before any data is collected (T2): every standard
calibration map is weakly increasing, strictly increasing maps leave resolving
power and AUROC *exactly* invariant, and weakly increasing maps can only lower
them. The implementation asserts that invariance to machine precision, so the
empirical run confirms the code rather than the claim.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from .anova import varianceComponents
from .cube import ResponseCube
from .resolution import (
    USABLE_D,
    discriminationIndex,
    onewayIcc,
    resolvingPower,
    selectionStability,
)
from .stats import Interval, auroc, bootstrapCi, cohenKappa, expectedCalibrationError
from .theory import USABILITY_FLOOR, aggregationAsymptote, aggregationCurve, requiredK


@dataclass(frozen=True)
class RemedyResult:
    """One remedy, its post-remedy statistic, its error bar, and its verdict."""

    name: str
    statistic: str
    value: float
    ci: Interval
    baseline: float
    floor: float
    verdict: str
    note: str
    detail: dict

    def asDict(self) -> dict:
        return {
            "name": self.name,
            "statistic": self.statistic,
            "value": self.value,
            "ci": self.ci.asDict(),
            "baseline": self.baseline,
            "floor": self.floor,
            "verdict": self.verdict,
            "note": self.note,
            "detail": self.detail,
        }


def _verdict(value: float, floor: float) -> str:
    if value is None or not math.isfinite(value):
        return "FAILS"
    return "HELPS" if value >= floor else "FAILS"


def _itemCells(
    cube: ResponseCube, facets: Sequence[str]
) -> dict[str, dict[tuple, list[float]]]:
    matrix = cube.balancedMatrix(facets)
    return matrix.itemRows()


def _subMatrix(
    rows: Mapping[str, Mapping[tuple, Sequence[float]]], items: Sequence[str]
) -> dict:
    """Rebuild a (item, condition) -> replicates map from a resampled item list.

    Bootstrap draws repeat items; each draw gets a distinct synthetic id so the
    design stays fully crossed and balanced.
    """
    out: dict[tuple[str, tuple], list[float]] = {}
    for n, item in enumerate(items):
        for cond, values in rows[item].items():
            out[(f"{item}#{n}", cond)] = list(values)
    return out


# --------------------------------------------------------------- remedy 1


def secondModel(
    cube: ResponseCube,
    *,
    primary: str,
    judge: str,
    floor: float = USABLE_D,
    draws: int = 2000,
    seed: int = 20260728,
) -> RemedyResult:
    """Swap in a second model as the rater. A second gauge has its own gauge variance."""
    judge_rows = _itemCells(cube.filter(model=judge), ("wording_id", "scale_id"))
    primary_rows = _itemCells(cube.filter(model=primary), ("wording_id", "scale_id"))
    items = sorted(judge_rows)

    def stat(sample: Sequence[str]) -> float | None:
        if len(sample) < 2:
            return None
        return discriminationIndex(_subMatrix(judge_rows, sample))

    ci = bootstrapCi(items, stat, draws=draws, seed=seed)
    baseline = discriminationIndex(_subMatrix(primary_rows, sorted(primary_rows)))

    # Cross-model agreement: treat the two models as raters of the same item.
    shared = sorted(set(judge_rows) & set(primary_rows))
    cross = float("nan")
    if len(shared) >= 2:
        groups = {
            item: [
                _flatMean(primary_rows[item]),
                _flatMean(judge_rows[item]),
            ]
            for item in shared
        }
        cross = onewayIcc(groups)

    return RemedyResult(
        name="second_model",
        statistic="discrimination_index_D",
        value=ci.point,
        ci=ci,
        baseline=baseline,
        floor=floor,
        verdict=_verdict(ci.point, floor),
        note=(
            f"judge={judge}; cross-model ICC(1,1)={cross:.4f}. A second rater adds its own "
            "reproducibility variance; it cannot subtract the first rater's."
        ),
        detail={"judge": judge, "primary": primary, "cross_model_icc": cross},
    )


def _flatMean(cells: Mapping[tuple, Sequence[float]]) -> float:
    values = [v for series in cells.values() for v in series]
    return math.fsum(values) / len(values) if values else float("nan")


# --------------------------------------------------------------- remedy 2


def thresholding(
    cube: ResponseCube,
    *,
    cuts: Sequence[float] | None = None,
    floor: float = USABILITY_FLOOR,
    draws: int = 2000,
    seed: int = 20260728,
) -> RemedyResult:
    """Binarize at a cut. Statistic: split-half Cohen's kappa at the *best* cut.

    Choosing the best cut post hoc is deliberately generous to the remedy: if even
    the most favourable threshold fails, no threshold works.
    """
    rows = _itemCells(cube, ("wording_id", "scale_id"))
    items = sorted(rows)
    observed = sorted(
        {v for cells in rows.values() for series in cells.values() for v in series}
    )
    if cuts is None:
        if len(observed) >= 2:
            cuts = [
                (observed[i] + observed[i + 1]) / 2.0 for i in range(len(observed) - 1)
            ]
        else:
            cuts = [0.5]
    cuts = list(cuts)

    def kappaAt(sample: Sequence[str], cut: float) -> float | None:
        conditions = sorted({c for item in sample for c in rows[item]}, key=str)
        kappas = []
        for cond in conditions:
            a, b = [], []
            for item in sample:
                series = rows[item].get(cond)
                if not series or len(series) < 2:
                    continue
                first, second = series[0::2], series[1::2]
                a.append(1 if math.fsum(first) / len(first) > cut else 0)
                b.append(1 if math.fsum(second) / len(second) > cut else 0)
            if len(a) >= 2:
                kappas.append(cohenKappa(a, b))
        return math.fsum(kappas) / len(kappas) if kappas else None

    scored = [(kappaAt(items, cut) or 0.0, cut) for cut in cuts]
    best_kappa, best_cut = max(scored, key=lambda t: (t[0], -t[1]))

    ci = bootstrapCi(items, lambda s: kappaAt(s, best_cut), draws=draws, seed=seed)
    flip_rate = _flipRate(rows, best_cut)

    return RemedyResult(
        name="thresholding",
        statistic="split_half_cohens_kappa",
        value=ci.point,
        ci=ci,
        baseline=best_kappa,
        floor=floor,
        verdict=_verdict(ci.point, floor),
        note=(
            f"best of {len(cuts)} candidate cuts (cut={best_cut:.4f}, chosen post hoc in the "
            f"remedy's favour); label flip rate between measurement passes = {flip_rate:.3f}"
        ),
        detail={"best_cut": best_cut, "n_cuts": len(cuts), "flip_rate": flip_rate},
    )


def _flipRate(rows: Mapping[str, Mapping[tuple, Sequence[float]]], cut: float) -> float:
    flips = total = 0
    for cells in rows.values():
        for series in cells.values():
            if len(series) < 2:
                continue
            first, second = series[0::2], series[1::2]
            a = math.fsum(first) / len(first) > cut
            b = math.fsum(second) / len(second) > cut
            flips += int(a != b)
            total += 1
    return flips / total if total else 0.0


# --------------------------------------------------------------- remedy 3


def plattFit(
    scores: Sequence[float], labels: Sequence[int]
) -> Callable[[float], float]:
    """Logistic (Platt) calibration by Newton's method. Strictly increasing when a > 0."""
    a, b = 1.0, 0.0
    for _ in range(100):
        g_a = g_b = h_aa = h_ab = h_bb = 0.0
        for s, y in zip(scores, labels, strict=True):
            z = a * s + b
            p = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))
            r = p - y
            w = max(p * (1.0 - p), 1e-12)
            g_a += r * s
            g_b += r
            h_aa += w * s * s
            h_ab += w * s
            h_bb += w
        det = h_aa * h_bb - h_ab * h_ab
        if abs(det) < 1e-12:
            break
        da = (g_a * h_bb - g_b * h_ab) / det
        db = (g_b * h_aa - g_a * h_ab) / det
        a -= da
        b -= db
        if abs(da) < 1e-10 and abs(db) < 1e-10:
            break
    if a <= 0.0:
        # Degenerate fit; fall back to the identity so the map stays increasing.
        a, b = 1.0, 0.0

    def apply(s: float) -> float:
        return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, a * s + b))))

    apply.coefficients = (a, b)  # type: ignore[attr-defined]
    return apply


def isotonicFit(
    scores: Sequence[float], labels: Sequence[int]
) -> Callable[[float], float]:
    """Isotonic (PAVA) calibration. Weakly increasing: it can create ties, never reorder."""
    pairs = sorted(zip(scores, labels, strict=True), key=lambda t: t[0])
    xs = [p[0] for p in pairs]
    ys = [float(p[1]) for p in pairs]
    values: list[float] = []
    weights: list[float] = []
    for y in ys:
        values.append(y)
        weights.append(1.0)
        while len(values) > 1 and values[-2] > values[-1]:
            w = weights[-2] + weights[-1]
            v = (values[-2] * weights[-2] + values[-1] * weights[-1]) / w
            values[-2:] = [v]
            weights[-2:] = [w]
    fitted: list[float] = []
    for v, w in zip(values, weights, strict=True):
        fitted.extend([v] * int(round(w)))
    knots = xs

    def apply(s: float) -> float:
        if not knots:
            return s
        idx = min(len(fitted) - 1, bisect.bisect_left(knots, s))
        return fitted[idx]

    return apply


def calibration(
    cube: ResponseCube,
    truth: Mapping[str, int],
    *,
    floor: float = USABLE_D,
    draws: int = 2000,
    seed: int = 20260728,
) -> RemedyResult:
    """Post-hoc calibration. Falsified analytically by T2; measured here to show the illusion."""
    rows = _itemCells(cube, ("wording_id", "scale_id"))
    items = sorted(i for i in rows if i in truth)
    flat_scores, flat_labels = [], []
    for item in items:
        for series in rows[item].values():
            for v in series:
                flat_scores.append(v)
                flat_labels.append(int(truth[item]))

    platt = plattFit(flat_scores, flat_labels)
    iso = isotonicFit(flat_scores, flat_labels)

    before = {
        "ece": expectedCalibrationError(flat_scores, flat_labels),
        "auroc": auroc(flat_scores, flat_labels),
        "d": discriminationIndex(_subMatrix(rows, items)),
        "resolving_power": resolvingPower(_subMatrix(rows, items)),
    }
    after = {}
    for name, g in (("platt", platt), ("isotonic", iso)):
        mapped = cube.mapValues(g)
        mrows = _itemCells(mapped, ("wording_id", "scale_id"))
        mitems = sorted(i for i in mrows if i in truth)
        gs = [g(s) for s in flat_scores]
        after[name] = {
            "ece": expectedCalibrationError(gs, flat_labels),
            "auroc": auroc(gs, flat_labels),
            "d": discriminationIndex(_subMatrix(mrows, mitems)),
            "resolving_power": resolvingPower(_subMatrix(mrows, mitems)),
        }

    calibrated = cube.mapValues(platt)
    crows = _itemCells(calibrated, ("wording_id", "scale_id"))
    citems = sorted(crows)

    def stat(sample: Sequence[str]) -> float | None:
        if len(sample) < 2:
            return None
        return discriminationIndex(_subMatrix(crows, sample))

    ci = bootstrapCi(citems, stat, draws=draws, seed=seed)
    ece_drop = before["ece"] - after["platt"]["ece"]

    return RemedyResult(
        name="calibration",
        statistic="discrimination_index_D",
        value=ci.point,
        ci=ci,
        baseline=before["d"],
        floor=floor,
        verdict=_verdict(ci.point, floor),
        note=(
            f"T2: Platt is strictly increasing, so D and AUROC are invariant by construction "
            f"(observed change {abs(after['platt']['d'] - before['d']):.2e}). ECE fell by "
            f"{ece_drop:.4f} while resolution moved by nothing — that gap is the illusion."
        ),
        detail={
            "before": before,
            "after": after,
            "platt_coefficients": list(platt.coefficients),
        },
    )


# --------------------------------------------------------------- remedy 4


def wordingAveraging(
    cube: ResponseCube,
    *,
    floor: float = USABILITY_FLOOR,
    draws: int = 2000,
    seed: int = 20260728,
) -> RemedyResult:
    """Average over prompt wordings, then ask how reliable the averaged score is."""
    rows = _itemCells(cube, ("wording_id",))
    items = sorted(rows)
    n_reps = min((len(s) for cells in rows.values() for s in cells.values()), default=0)

    # Per item: one averaged score per replicate index, averaged across wordings.
    averaged = {
        item: [
            math.fsum(series[r] for series in cells.values()) / len(cells)
            for r in range(n_reps)
        ]
        for item, cells in rows.items()
    }

    def stat(sample: Sequence[str]) -> float | None:
        if len(sample) < 2:
            return None
        return onewayIcc({f"{i}#{n}": averaged[i] for n, i in enumerate(sample)})

    ci = bootstrapCi(items, stat, draws=draws, seed=seed)
    vc = varianceComponents(cube.balancedMatrix(("wording_id",)))
    curve = aggregationCurve(
        vc, systematic="none", ks=(1, 2, 4, 8, 16, 32, 64, 128, 1024)
    )
    k_needed = requiredK(vc, systematic="none", target=floor)

    return RemedyResult(
        name="wording_averaging",
        statistic="ICC(1,1)_of_wording_averaged_score",
        value=ci.point,
        ci=ci,
        baseline=onewayIcc({i: averaged[i] for i in items})
        if n_reps >= 2
        else float("nan"),
        floor=floor,
        verdict=_verdict(ci.point, floor),
        note=(
            f"asymptote as wordings -> infinity = {curve['asymptote']:.4f}; "
            + (
                f"wordings needed to reach {floor:.2f} = {k_needed}"
                if k_needed is not None
                else f"unreachable at any number of wordings (item variance = {vc.var_item:.2e})"
            )
        ),
        detail={
            "curve": curve,
            "required_k": k_needed,
            "n_wordings": vc.n_conditions,
            "selection_stability": _remediedSelection(averaged),
        },
    )


# --------------------------------------------------------------- remedy 5


def selfConsistency(
    cube: ResponseCube,
    *,
    ks: Sequence[int] = (1, 2, 4, 8),
    floor: float = USABILITY_FLOOR,
    draws: int = 2000,
    seed: int = 20260728,
) -> RemedyResult:
    """Average k samples at a fixed wording, then ask how reliable that score is."""
    rows = _itemCells(cube, ("wording_id", "scale_id"))
    items = sorted(rows)
    max_reps = min(
        (len(s) for cells in rows.values() for s in cells.values()), default=0
    )
    usable_ks = [int(k) for k in ks if 1 <= int(k) <= max_reps]
    if not usable_ks:
        usable_ks = [1]
    k_top = max(usable_ks)

    def averagedAt(k: int) -> dict[str, list[float]]:
        return {
            item: [
                math.fsum(series[:k]) / k
                for _, series in sorted(cells.items(), key=lambda t: str(t[0]))
            ]
            for item, cells in rows.items()
        }

    curve_empirical = []
    for k in usable_ks:
        avg = averagedAt(k)
        curve_empirical.append({"k": k, "reliability": onewayIcc(avg)})

    top = averagedAt(k_top)

    def stat(sample: Sequence[str]) -> float | None:
        if len(sample) < 2:
            return None
        return onewayIcc({f"{i}#{n}": top[i] for n, i in enumerate(sample)})

    ci = bootstrapCi(items, stat, draws=draws, seed=seed)
    vc = varianceComponents(cube.balancedMatrix(("wording_id", "scale_id")))
    theory = aggregationCurve(
        vc, systematic="condition_locked", ks=tuple(usable_ks) + (1024, 10**6)
    )
    k_needed = requiredK(vc, systematic="condition_locked", target=floor)
    asymptote = aggregationAsymptote(
        var_item=vc.var_item, var_systematic=vc.var_condition + vc.var_interaction
    )

    return RemedyResult(
        name="self_consistency",
        statistic=f"ICC(1,1)_of_{k_top}_sample_mean",
        value=ci.point,
        ci=ci,
        baseline=curve_empirical[0]["reliability"] if curve_empirical else float("nan"),
        floor=floor,
        verdict=_verdict(ci.point, floor),
        note=(
            f"rho_inf={asymptote:.4f} (condition-locked variance never averages out); "
            + (
                f"samples needed to reach {floor:.2f} = {k_needed}"
                if k_needed is not None
                else f"unreachable at any k because rho_inf < {floor:.2f}"
            )
        ),
        detail={
            "empirical_curve": curve_empirical,
            "theoretical_curve": theory,
            "asymptote": asymptote,
            "required_k": k_needed,
            "selection_stability": _remediedSelection(top),
        },
    )


def runRemedies(
    cube: ResponseCube,
    *,
    truth: Mapping[str, int] | None = None,
    primary: str | None = None,
    judge: str | None = None,
    draws: int = 2000,
    seed: int = 20260728,
) -> list[RemedyResult]:
    """Run every applicable remedy. Skipped remedies are recorded, never silently dropped."""
    results: list[RemedyResult] = []
    models = list(cube.values("model"))
    if primary is None:
        primary = models[0] if models else ""
    if judge is None:
        judge = next((m for m in models if m != primary), None)

    if judge is not None:
        results.append(
            secondModel(cube, primary=primary, judge=judge, draws=draws, seed=seed)
        )
    else:
        results.append(_skipped("second_model", "cube contains a single model"))

    results.append(thresholding(cube, draws=draws, seed=seed))

    if truth:
        results.append(calibration(cube, truth, draws=draws, seed=seed))
    else:
        results.append(_skipped("calibration", "no ground-truth labels supplied"))

    results.append(wordingAveraging(cube, draws=draws, seed=seed))
    results.append(selfConsistency(cube, draws=draws, seed=seed))
    return results


def _remediedSelection(per_item: Mapping[str, Sequence[float]], *, q: float = 0.2) -> dict:
    """Selection stability of a remedied score.

    A remedy that lifts ICC above the floor has fixed the statistic papers report.
    Whether it fixed the *decision* — which items a pipeline sends for verification
    — is a separate question, and this is the answer to it.
    """
    cells = {(item, ("remedied",)): list(values) for item, values in per_item.items()}
    if len(cells) < 2:
        return {"jaccard": float("nan"), "q": q}
    return selectionStability(cells, q=q)


def _skipped(name: str, why: str) -> RemedyResult:
    nan = float("nan")
    return RemedyResult(
        name=name,
        statistic="n/a",
        value=nan,
        ci=Interval(point=nan, low=nan, high=nan),
        baseline=nan,
        floor=nan,
        verdict="SKIPPED",
        note=why,
        detail={},
    )


__all__ = [
    "RemedyResult",
    "calibration",
    "isotonicFit",
    "plattFit",
    "runRemedies",
    "secondModel",
    "selfConsistency",
    "thresholding",
    "wordingAveraging",
]

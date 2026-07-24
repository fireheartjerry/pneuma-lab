"""Assemble the audit table from coded rows.

Loads every ``coded-*.json`` file, normalizes the two coding dialects into one,
and emits the paper's exhibits: a per-paper detectability surface over the
(icc, discordance) grid, a verdict-stability report, and stratified counts.

Two rules govern everything here and are enforced rather than documented:

1. A row without a *verified* absolute claimed effect never receives a verdict.
   Six of thirty-two rows qualify. The other twenty-six are reported as
   ``NO-VERIFIED-EFFECT``, which is a finding about the literature and not a
   gap in the data.

2. A row whose coarsest grouping is unstated, or is a single cluster, is
   ``NON-IDENTIFIABLE``. Its reason is carried into every output. Nothing is
   imputed, and no default is substituted.

Output is deterministic: sorted keys, no timestamps, no absolute paths.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from pneuma_lab.audit.mde import (
    NonIdentifiable,
    ReportedDesign,
    designEffect,
    minimumDetectableEffect,
)

ICC_GRID: tuple[float, ...] = (0.05, 0.1, 0.3, 0.5, 1.0)
DISCORDANCE_GRID: tuple[float, ...] = (0.15, 0.25, 0.40)

# Dialect-1 files used short field names; dialect-2 uses explicit ones.
_DIALECT_1_KEYS = {
    "f1": "f1_reported_n",
    "f2": "f2_clusters",
    "f3": "f3_ratio",
    "f4": "f4_uncertainty",
    "f5": "f5_inert_null",
    "f6": "f6_engagement",
    "f7": "f7_budget",
    "f8": "f8_decision_rule",
    "f9": "f9_non_engagement",
}


@dataclass(frozen=True)
class AlternativeUnit:
    """A defensible alternative coarsest grouping, adjudicated but not adopted."""

    f2_clusters: int | None
    f2_unit: str
    f2_rule: int | None
    reason: str


@dataclass
class CodedPaper:
    """One normalized row. Field names follow the v2 dialect."""

    label: str
    stratum: str
    arxiv: str | None = None
    f1_reported_n: int | None = None
    f1_unit: str = ""
    f2_clusters: int | None = None
    f2_unit: str = ""
    f2_rule: int | None = None
    f3_ratio: float | None = None
    f4_uncertainty: str = "not_stated"
    f5_inert_null: str = "not_stated"
    f6_engagement: list[str] = field(default_factory=list)
    f7_budget: str = "not_stated"
    f8_decision_rule: str = "none"
    f9_non_engagement: str = "not_specified"
    claimed_effect_pp: float | None = None
    claimed_effect_verified: bool = False
    f2_alternatives: list[AlternativeUnit] = field(default_factory=list)
    shared_memory_lifetime: bool = False
    flags: list[str] = field(default_factory=list)

    def toDesign(self, clusters: int | None = None) -> ReportedDesign:
        """Build a design at the coded unit, or at an alternative if given."""
        k = self.f2_clusters if clusters is None else clusters
        return ReportedDesign(
            label=self.label,
            n_observations=self.f1_reported_n or 0,
            n_clusters=k,
            paired=True,
            discordance=DISCORDANCE_GRID[1],
        )

    def identifiabilityReason(self) -> str | None:
        """Why this row cannot support a detectability statement, or None."""
        if self.f1_reported_n is None:
            return "no evaluation sample size stated in the paper"
        if self.f2_clusters is None:
            return "count of the coarsest grouping not stated in the paper"
        if self.f2_clusters == 1:
            return (
                "all observations from a single cluster; between-cluster "
                "variance is unestimable"
            )
        return None


def _normalize(raw: dict, stratum_default: str) -> CodedPaper:
    """Accept either coding dialect and return one shape."""
    row = dict(raw)
    for short, long in _DIALECT_1_KEYS.items():
        if short in row and long not in row:
            row[long] = row.pop(short)
    alts = [
        AlternativeUnit(
            f2_clusters=a.get("f2_clusters"),
            f2_unit=a.get("f2_unit", ""),
            f2_rule=a.get("f2_rule"),
            reason=a.get("reason", ""),
        )
        for a in row.get("f2_alternatives", [])
    ]
    engagement = row.get("f6_engagement") or []
    if isinstance(engagement, str):
        engagement = [engagement]
    return CodedPaper(
        label=row["label"],
        stratum=row.get("stratum", stratum_default),
        arxiv=row.get("arxiv"),
        f1_reported_n=row.get("f1_reported_n"),
        f1_unit=row.get("f1_unit", ""),
        f2_clusters=row.get("f2_clusters"),
        f2_unit=row.get("f2_unit", ""),
        f2_rule=row.get("f2_rule"),
        f3_ratio=row.get("f3_ratio"),
        f4_uncertainty=row.get("f4_uncertainty", "not_stated"),
        f5_inert_null=row.get("f5_inert_null", "not_stated"),
        f6_engagement=engagement,
        f7_budget=row.get("f7_budget", "not_stated"),
        f8_decision_rule=row.get("f8_decision_rule", "none"),
        f9_non_engagement=row.get("f9_non_engagement", "not_specified"),
        claimed_effect_pp=row.get("claimed_effect_pp"),
        claimed_effect_verified=bool(row.get("claimed_effect_verified", False)),
        f2_alternatives=alts,
        shared_memory_lifetime=bool(row.get("shared_memory_lifetime", False)),
        flags=list(row.get("flags", [])),
    )


def loadCorpus(data_dir: Path) -> list[CodedPaper]:
    """Load every coded-*.json under ``data_dir``, sorted by label."""
    papers: list[CodedPaper] = []
    for path in sorted(data_dir.glob("coded-*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        stratum_default = doc.get("stratum", "system")
        for raw in doc["papers"]:
            papers.append(_normalize(raw, stratum_default))
    if not papers:
        raise ValueError(f"no coded rows found under {data_dir}")
    return sorted(papers, key=lambda p: p.label)


def surfaceFor(paper: CodedPaper, clusters: int | None = None) -> list[dict] | None:
    """The (icc x discordance) MDE surface, or None if non-identifiable."""
    k = paper.f2_clusters if clusters is None else clusters
    if paper.f1_reported_n is None or k is None or k == 1:
        return None
    cells = []
    for icc in ICC_GRID:
        for disc in DISCORDANCE_GRID:
            design = ReportedDesign(
                label=paper.label,
                n_observations=paper.f1_reported_n,
                n_clusters=k,
                paired=True,
                discordance=disc,
            )
            mde = minimumDetectableEffect(design, icc) * 100.0
            claim = paper.claimed_effect_pp if paper.claimed_effect_verified else None
            if claim is None:
                verdict = "NO-VERIFIED-EFFECT"
            elif claim >= mde:
                verdict = "above"
            else:
                verdict = "below"
            cells.append(
                {
                    "icc": icc,
                    "discordance": disc,
                    "design_effect": round(
                        designEffect(paper.f1_reported_n / k, icc), 2
                    ),
                    "mde_pp": round(mde, 2),
                    "verdict": verdict,
                }
            )
    return cells


def stabilityFor(paper: CodedPaper) -> dict:
    """Is the verdict constant across the whole surface, and where does it flip?"""
    result: dict = {"label": paper.label, "coded": None, "alternatives": []}
    coded = surfaceFor(paper)
    if coded is None:
        result["coded"] = {
            "status": "NON-IDENTIFIABLE",
            "reason": paper.identifiabilityReason(),
        }
    elif not paper.claimed_effect_verified:
        result["coded"] = {"status": "NO-VERIFIED-EFFECT"}
    else:
        verdicts = {c["verdict"] for c in coded}
        first_flip = None
        if len(verdicts) > 1:
            base = coded[0]["verdict"]
            for cell in coded:
                if cell["verdict"] != base:
                    first_flip = {
                        "icc": cell["icc"],
                        "discordance": cell["discordance"],
                    }
                    break
        result["coded"] = {
            "status": "STABLE" if len(verdicts) == 1 else "FLIPS",
            "verdict": sorted(verdicts)[0] if len(verdicts) == 1 else None,
            "first_flip": first_flip,
        }

    for alt in paper.f2_alternatives:
        alt_surface = surfaceFor(paper, clusters=alt.f2_clusters)
        entry = {
            "f2_clusters": alt.f2_clusters,
            "f2_unit": alt.f2_unit,
            "reason": alt.reason,
        }
        if alt_surface is None:
            entry["status"] = "NON-IDENTIFIABLE"
        elif not paper.claimed_effect_verified:
            entry["status"] = "NO-VERIFIED-EFFECT"
        else:
            av = {c["verdict"] for c in alt_surface}
            entry["status"] = "STABLE" if len(av) == 1 else "FLIPS"
            entry["verdict"] = sorted(av)[0] if len(av) == 1 else None
        result["alternatives"].append(entry)
    return result


def summarize(papers: list[CodedPaper]) -> dict:
    """Stratified counts. Never collapsed to a single number."""
    strata = sorted({p.stratum for p in papers})
    out: dict = {"by_stratum": {}, "pooled": {}}

    def block(rows: list[CodedPaper]) -> dict:
        identifiable = [p for p in rows if p.identifiabilityReason() is None]
        verified = [p for p in identifiable if p.claimed_effect_verified]
        below = {}
        for icc in ICC_GRID:
            n_below = 0
            for p in verified:
                design = ReportedDesign(
                    label=p.label,
                    n_observations=p.f1_reported_n or 0,
                    n_clusters=p.f2_clusters,
                    paired=True,
                    discordance=DISCORDANCE_GRID[1],
                )
                if (p.claimed_effect_pp or 0) < minimumDetectableEffect(
                    design, icc
                ) * 100:
                    n_below += 1
            below[icc] = n_below
        return {
            "n_rows": len(rows),
            "non_identifiable": len(rows) - len(identifiable),
            "no_verified_effect": len(identifiable) - len(verified),
            "verdict_eligible": len(verified),
            "below_threshold_by_icc": below,
            "shared_memory_lifetime": sum(1 for p in rows if p.shared_memory_lifetime),
            "no_pre_specified_rule": sum(
                1 for p in rows if p.f8_decision_rule == "none"
            ),
            "no_inert_null": sum(
                1
                for p in rows
                if p.f5_inert_null in ("none", "ablation_only", "not_stated")
            ),
        }

    for s in strata:
        out["by_stratum"][s] = block([p for p in papers if p.stratum == s])
    out["pooled"] = block(papers)
    out["caveat"] = (
        "Every count is conditional on its stated ICC and on a paired discordance "
        "of 0.25. No effective sample size is estimated; published cluster counts "
        "do not identify one. Counts describe the coded frame and date range only."
    )
    return out

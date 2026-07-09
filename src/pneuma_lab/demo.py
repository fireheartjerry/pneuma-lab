"""Canonical evidence demo — one command regenerates the whole Level 3 vs Level 4 suite.

Run it with::

    python -m pneuma_lab.demo            # writes build/canonical/
    python -m pneuma_lab.demo -o <dir>   # writes somewhere else

It exercises the exact evidence path the rest of the repo asserts, end to end:

    * a **passive** Level-3 replay of ``fixtures/sample_run.jsonl`` (no perturbation),
    * a **paired** control/treated/null replay of every canonical
      ``fixtures/interventions/*.jsonl`` scenario (the Level-4 path),

and consolidates the results into an auditable ``summary.json`` (+ ``summary.md``).

Every fixture is replayed **twice** and its artifacts are compared byte-for-byte;
the byte-determinism verdict is recorded per fixture and rolled up into the summary.
Nothing here re-scores or overrides the psyche: it drives the same
``ReplayHarness`` / ``PairedReplayRunner`` the tests use and reports what they emit.

The demo is deterministic by construction — it never stamps wall-clock time into the
summary — so ``summary.json`` is itself byte-identical across repeated runs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .interventions.runner import PairedReplayRunner
from .psyche import ReferencePsyche
from .replay import ReplayHarness, load_jsonl

# Repo root: .../src/pneuma_lab/demo.py -> parents[2] is the project root.
_ROOT = Path(__file__).resolve().parents[2]
_PASSIVE_FIXTURE = _ROOT / "fixtures" / "sample_run.jsonl"
_INTERVENTION_DIR = _ROOT / "fixtures" / "interventions"

# Order-stable list of canonical intervention fixtures (sorted stems).
_INTERVENTION_FIXTURES = (
    "ablate_scar_graph",
    "boost_curiosity",
    "clamp_tension",
    "disable_workspace",
    "failing_hypothesis",
    "remove_memory_anchors",
    "restore_null",
)


# -- deterministic serialization (mirrors replay CLI byte-for-byte) ---------


def _json_text(obj: dict) -> str:
    """Canonical pretty JSON — matches ``pneuma_lab.replay.__main__._dump_json``."""
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _jsonl_text(frames: list[dict]) -> str:
    """Canonical JSONL — matches ``pneuma_lab.replay.frames.dump_jsonl``."""
    lines = [json.dumps(f, sort_keys=True, ensure_ascii=False) for f in frames]
    return "".join(line + "\n" for line in lines)


# -- artifact production ----------------------------------------------------


@dataclass
class _Run:
    """One fixture's replay, reduced to named artifact texts + the facts we report."""

    artifacts: dict[str, str]  # filename -> canonical text
    evidence: dict
    report: dict | None  # paired report; None for the passive run


@dataclass(frozen=True)
class RepositoryProvenance:
    """Git state that identifies the exact source used for an evidence run."""

    commit: str
    dirty: bool
    remote_refs: tuple[str, ...]

    @property
    def published(self) -> bool:
        """Whether at least one fetched remote ref contains ``commit``."""
        return bool(self.remote_refs)

    def as_record(self, *, official: bool) -> dict:
        return {
            "source_kind": "git",
            "git_commit": self.commit,
            "tree_state": "dirty" if self.dirty else "clean",
            "remote_refs_containing_commit": list(self.remote_refs),
            "commit_published": self.published,
            "official": official,
        }


class EvidenceProvenanceError(RuntimeError):
    """Raised when source provenance is unavailable or fails official gates."""


def _git(*args: str) -> str:
    """Run one read-only git query at the repository root."""
    proc = subprocess.run(
        ["git", "-C", str(_ROOT), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}"
        raise EvidenceProvenanceError(f"git {' '.join(args)} failed: {detail}")
    return proc.stdout.strip()


def collect_repository_provenance() -> RepositoryProvenance:
    """Read the current commit, tree state, and containing remote refs."""
    commit = _git("rev-parse", "HEAD")
    if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit.lower()):
        raise EvidenceProvenanceError(f"git returned an invalid commit id: {commit!r}")

    dirty = bool(_git("status", "--porcelain=v1", "--untracked-files=normal"))
    refs_text = _git(
        "for-each-ref",
        "--format=%(refname:short)",
        "--contains",
        commit,
        "refs/remotes",
    )
    remote_refs = tuple(sorted(line for line in refs_text.splitlines() if line))
    return RepositoryProvenance(
        commit=commit,
        dirty=dirty,
        remote_refs=remote_refs,
    )


def require_official_provenance(provenance: RepositoryProvenance) -> None:
    """Fail closed unless the evidence source is clean and remotely published."""
    failures: list[str] = []
    if provenance.dirty:
        failures.append("the working tree is dirty")
    if not provenance.published:
        failures.append("the source commit is not contained in any fetched remote ref")
    if failures:
        raise EvidenceProvenanceError(
            "official evidence refused: " + "; ".join(failures)
        )


def _passive_trace_complete(tick_outputs: list) -> bool:
    """Every tick's causal path spans event→…→behavior (no suppression in a clean run)."""
    for o in tick_outputs:
        stages = [s["stage"] for s in o.causal_trace["causal_path"]]
        if not stages or stages[0] != "event" or stages[-1] != "behavior":
            return False
    return True


def _passive_run() -> _Run:
    res = ReplayHarness(ReferencePsyche()).run(load_jsonl(_PASSIVE_FIXTURE))
    artifacts = {
        "output_frames.jsonl": _jsonl_text(res.output_frames),
        "evidence.json": _json_text(res.evidence_frame),
    }
    # A passive run carries no intervention report; synthesize the honest facts.
    report = {
        "summary": {"passed": [], "failed": []},
        "null_condition": {"passed": None},  # no null condition exists to hold
        "causal_trace_complete": _passive_trace_complete(res.tick_outputs),
        "grounded_self_report_changed_under_perturbation": None,  # nothing perturbed
    }
    return _Run(artifacts=artifacts, evidence=res.evidence_frame, report=report)


def _paired_run(fixture: Path) -> _Run:
    res = PairedReplayRunner().run(load_jsonl(fixture))
    artifacts = {
        "control_frames.jsonl": _jsonl_text(res.control.output_frames),
        "intervention_frames.jsonl": _jsonl_text(res.treated.output_frames),
        "intervention_report.json": _json_text(res.report),
        "evidence.json": _json_text(res.evidence_frame),
    }
    return _Run(artifacts=artifacts, evidence=res.evidence_frame, report=res.report)


def _produce(kind: str, fixture: Path) -> _Run:
    return _passive_run() if kind == "passive" else _paired_run(fixture)


# -- categorization ---------------------------------------------------------


def _category(name: str, kind: str, evidence_level: int) -> str:
    """A plain-English bucket for the summary, derived from results (not hardcoded)."""
    if kind == "passive":
        return "passive_level3"
    if evidence_level == 4:
        return "intervention_backed_level4"
    if name == "restore_null":
        return "null_control_level3"
    if name == "failing_hypothesis":
        return "failed_hypothesis_level3"
    return "refused_level3"


# -- summary assembly -------------------------------------------------------


def _fixture_record(name: str, kind: str, run: _Run, deterministic: bool) -> dict:
    ev = run.evidence
    rep = run.report or {}
    summary = rep.get("summary", {})
    null = rep.get("null_condition", {})
    changed = rep.get("grounded_self_report_changed_under_perturbation")
    level = int(ev["evidence_level"])

    def _tri(value, true_word, false_word):
        if value is None:
            return "n/a"
        return true_word if value else false_word

    return {
        "fixture": name,
        "kind": kind,
        "category": _category(name, kind, level),
        "evidence_level": level,
        "intervention_tests": {
            "passed": list(summary.get("passed", [])),
            "failed": list(summary.get("failed", [])),
        },
        "null_condition": _tri(null.get("passed"), "passed", "failed"),
        "causal_trace_complete": bool(rep.get("causal_trace_complete", False)),
        "grounded_self_report_perturbation": _tri(changed, "changed", "unchanged"),
        "confabulation_risk": ev["roleplay_confabulation_risk"],
        "audit_status": ev["audit_status"],
        "byte_deterministic": deterministic,
        "artifacts": {fname: f"{name}/{fname}" for fname in sorted(run.artifacts)},
    }


def build_summary(records: list[dict], *, source_provenance: dict) -> dict:
    """Roll per-fixture records into the auditable top-level summary (deterministic)."""
    all_deterministic = all(r["byte_deterministic"] for r in records)
    passive = [r for r in records if r["kind"] == "passive"]
    level4 = sorted(r["fixture"] for r in records if r["evidence_level"] == 4)
    level3 = sorted(r["fixture"] for r in records if r["evidence_level"] == 3)
    return {
        "report_kind": "canonical_evidence_summary",
        "schema_note": (
            "Pneuma Lab internal evidence. The scale is the conservative 0-5 ladder in "
            "docs/consciousness-levels.md. This suite reaches at most internal Level 4 "
            "(causal-intervention robustness in-harness). Level 4 here is NOT Level 5, "
            "NOT AGI, and NOT a claim of phenomenal consciousness."
        ),
        "source_provenance": source_provenance,
        "byte_deterministic": all_deterministic,
        "levels": {
            "passive_level3": sorted(r["fixture"] for r in passive),
            "intervention_backed_level4": level4,
            "level3_controls_and_refusals": [
                r["fixture"]
                for r in records
                if r["evidence_level"] == 3 and r["kind"] != "passive"
            ],
        },
        "counts": {
            "fixtures": len(records),
            "level4": len(level4),
            "level3": len(level3),
        },
        "fixtures": records,
    }


def _summary_markdown(summary: dict) -> str:
    lines: list[str] = []
    lines.append("# Canonical evidence summary\n")
    lines.append(f"_{summary['schema_note']}_\n")
    det = "yes" if summary["byte_deterministic"] else "**NO**"
    provenance = summary["source_provenance"]
    lines.append(
        "- Source commit: `{commit}` ({tree}; published: {published}; official: "
        "{official})".format(
            commit=provenance["git_commit"],
            tree=provenance["tree_state"],
            published="yes" if provenance["commit_published"] else "no",
            official="yes" if provenance["official"] else "no",
        )
    )
    lines.append(f"- Byte-deterministic across repeat runs: **{det}**")
    lines.append(
        f"- Fixtures: {summary['counts']['fixtures']} "
        f"(Level 4: {summary['counts']['level4']}, "
        f"Level 3: {summary['counts']['level3']})\n"
    )
    lines.append(
        "| fixture | kind | level | passed | failed | null | trace | "
        "report Δ | confab | determ |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in summary["fixtures"]:
        it = r["intervention_tests"]
        lines.append(
            "| {fixture} | {kind} | {evidence_level} | {passed} | {failed} | "
            "{null} | {trace} | {rep} | {confab} | {det} |".format(
                fixture=r["fixture"],
                kind=r["kind"],
                evidence_level=r["evidence_level"],
                passed=", ".join(it["passed"]) or "—",
                failed=", ".join(it["failed"]) or "—",
                null=r["null_condition"],
                trace="yes" if r["causal_trace_complete"] else "no",
                rep=r["grounded_self_report_perturbation"],
                confab=r["confabulation_risk"],
                det="yes" if r["byte_deterministic"] else "NO",
            )
        )
    lines.append("")
    lines.append("## Why the Level-3 controls stay Level 3\n")
    lines.append(
        "- **passive** (`sample_run`): the architecture is live and causally "
        "connected, but nothing is perturbed — no causal-intervention evidence."
    )
    lines.append(
        "- **restore_null**: a pure `restore` no-op moves no interior state, so "
        "there is no downstream delta to attribute — Level 4 is refused."
    )
    lines.append(
        "- **failing_hypothesis**: the perturbation's predicted delta does not "
        "occur, so the intervention test fails — Level 4 is refused.\n"
    )
    lines.append("## What Level 4 here is NOT\n")
    lines.append(
        "Internal Level 4 is causal-intervention robustness demonstrated "
        "in-harness. It is **not** Level 5, **not** Level 6, **not** AGI, and "
        "**not** a claim of phenomenal consciousness. Level 5 still needs "
        "every family intervention-backed, adversarial robustness over time, "
        "and an independent external audit."
    )
    return "\n".join(lines) + "\n"


# -- orchestration ----------------------------------------------------------


def run_canonical(
    out_dir: str | Path = "build/canonical",
    *,
    official: bool = False,
    provenance: RepositoryProvenance | None = None,
) -> dict:
    """Regenerate the whole canonical evidence suite under ``out_dir``; return the summary.

    Each fixture is produced twice and its artifacts compared byte-for-byte; the
    verdict is recorded as ``byte_deterministic`` per fixture and rolled up.
    Artifacts are written to ``<out_dir>/<fixture>/`` and the consolidated report to
    ``<out_dir>/summary.json`` (+ ``summary.md``).
    """
    source = provenance or collect_repository_provenance()
    if official:
        require_official_provenance(source)

    out = Path(out_dir)
    jobs: list[tuple[str, str, Path]] = [("sample_run", "passive", _PASSIVE_FIXTURE)]
    for name in _INTERVENTION_FIXTURES:
        jobs.append((name, "intervention", _INTERVENTION_DIR / f"{name}.jsonl"))

    records: list[dict] = []
    for name, kind, fixture in jobs:
        first = _produce(kind, fixture)
        second = _produce(kind, fixture)
        deterministic = first.artifacts == second.artifacts

        fixture_dir = out / name
        fixture_dir.mkdir(parents=True, exist_ok=True)
        for fname, text in first.artifacts.items():
            (fixture_dir / fname).write_text(text, encoding="utf-8", newline="\n")

        records.append(_fixture_record(name, kind, first, deterministic))

    summary = build_summary(
        records,
        source_provenance=source.as_record(official=official),
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(
        _json_text(summary), encoding="utf-8", newline="\n"
    )
    (out / "summary.md").write_text(
        _summary_markdown(summary), encoding="utf-8", newline="\n"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pneuma_lab.demo")
    parser.add_argument(
        "-o", "--out-dir", default="build/canonical", help="Output directory."
    )
    parser.add_argument(
        "--official",
        action="store_true",
        help=(
            "Refuse unless the source tree is clean and HEAD is contained in a "
            "fetched remote ref; mark the resulting summary official."
        ),
    )
    args = parser.parse_args(argv)

    try:
        summary = run_canonical(args.out_dir, official=args.official)
    except EvidenceProvenanceError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    c = summary["counts"]
    det = "OK" if summary["byte_deterministic"] else "FAILED"
    print(
        f"canonical evidence suite -> {args.out_dir} | "
        f"{c['fixtures']} fixtures | "
        f"Level 4: {c['level4']} {summary['levels']['intervention_backed_level4']} | "
        f"Level 3: {c['level3']} | byte-determinism: {det}"
    )
    for r in summary["fixtures"]:
        it = r["intervention_tests"]
        print(
            f"  {r['fixture']:<20} L{r['evidence_level']} "
            f"[{r['category']}] passed={it['passed']} failed={it['failed']} "
            f"determ={'ok' if r['byte_deterministic'] else 'NO'}"
        )
    # A determinism regression is a hard failure of the demo's contract.
    return 0 if summary["byte_deterministic"] else 1


if __name__ == "__main__":
    sys.exit(main())

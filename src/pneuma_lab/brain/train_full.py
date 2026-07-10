"""Elite PneumaBrain-v0.1 training: prefix early-warning RISK with honest CV.

Gated by the corpus authorization. For each prefix window (25% / 50% / 100% of
the trajectory) it runs leave-one-repo-out cross-validation, a bootstrap CI on
the pooled out-of-fold predictions, refits a full-data head, and Platt-calibrates
on the out-of-fold scores. Deterministic end to end. Advisory-only: no runtime
integration, no verifier bypass, no consciousness claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pneuma_lab.brain import BRAIN_VERSION
from pneuma_lab.brain import calibration as cal
from pneuma_lab.brain import evaluate as ev
from pneuma_lab.brain import model as model_mod
from pneuma_lab.brain import preflight
from pneuma_lab.brain import prefix_features as pf
from pneuma_lab.estimators.logistic import sigmoid
from pneuma_lab.estimators.metrics import ece

# E-0 pre-registered baseline: observable-feature logistic, prefix-10 AUROC.
BASELINE_E0_PREFIX10_AUROC = 0.70


def _iter_traces(path: str | Path):
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _build_items(path: str | Path):
    """Two streaming passes: freeze vocab, then featurize into small item lists."""
    tool_vocab = pf.freeze_tool_vocab(_iter_traces(path))
    per_prefix: dict[str, list] = {p: [] for p in pf.PREFIXES}
    names: dict[str, list[str]] = {}
    for trace in _iter_traces(path):
        label = pf.label_of(trace)
        if label is None:
            continue
        repo = pf.repo_of(trace)
        try:
            rows = {p: pf.feature_vector(trace, p, tool_vocab) for p in pf.PREFIXES}
        except ValueError:
            continue
        for prefix in pf.PREFIXES:
            per_prefix[prefix].append((rows[prefix], label, repo))
            names.setdefault(prefix, pf.feature_names(tool_vocab, prefix))
    return tool_vocab, names, per_prefix


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    tmp.replace(path)


def _canonical(value: dict) -> str:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )


def _fmt(value) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def _report_markdown(metrics: dict) -> str:
    lines = [
        "# PneumaBrain-v0.1 — elite early-warning RISK report",
        "",
        f"- model_version: `{metrics['model_version']}`",
        f"- corpus: `{metrics['corpus']}` ({metrics['n_examples']} traces, "
        f"{metrics['n_repos']} repos)",
        f"- label: RISK_PREDICTION (failure=1); base failure rate "
        f"{metrics['failure_rate']:.3f}",
        "",
        "## Early-warning curve (leave-one-repo-out, out-of-fold)",
        "",
        "| trajectory seen | OOF AUROC | 95% CI | ECE (pre→post calib) |",
        "| --- | ---: | ---: | ---: |",
    ]
    labels = {"prefix_25": "first 25%", "prefix_50": "first 50%", "full": "full"}
    for prefix in pf.PREFIXES:
        entry = metrics["prefixes"][prefix]
        boot = entry["bootstrap"]
        ci = f"[{_fmt(boot['lo'])}, {_fmt(boot['hi'])}]"
        lines.append(
            f"| {labels[prefix]} | {_fmt(entry['oof_auroc'])} | {ci} | "
            f"{_fmt(entry['ece_before'])} → {_fmt(entry['ece_after'])} |"
        )
    lines += [
        "",
        f"E-0 pre-registered baseline (observable-feature logistic, prefix-10): "
        f"{BASELINE_E0_PREFIX10_AUROC:.2f}.",
        "Note: E-0 used a prefix-10-step window; the prefixes here are fractions "
        "of each trajectory, so this is an indicative comparison, not identical.",
        "",
        "## Per-repo AUROC (full trajectory, out-of-fold)",
        "",
        "| repo | n | failures | AUROC |",
        "| --- | ---: | ---: | ---: |",
    ]
    for repo in metrics["prefixes"]["full"]["per_repo_order"]:
        cell = metrics["prefixes"]["full"]["per_repo"][repo]
        lines.append(
            f"| {repo} | {cell['n']} | {cell['n_pos']} | {_fmt(cell['auroc'])} |"
        )
    lines += [
        "",
        "Advisory-only. Outputs are priors/pressures for the deterministic gates; "
        "no runtime integration, no verifier bypass, no consciousness claim.",
    ]
    return "\n".join(lines) + "\n"


def run_full_training(
    *,
    traces_path: str | Path,
    authorization_path: str | Path,
    corpus_manifest_path: str | Path,
    output_root: str | Path,
    corpus_label: str = "swe-gym-openhands-sampled",
    n_resamples: int = 2000,
    require_clean_code: bool = True,
) -> dict:
    """Verify authorization, then train + honestly evaluate every prefix head."""
    preflight.verify_corpus_run(
        authorization_path,
        corpus_manifest_path,
        output_root,
        require_clean_code=require_clean_code,
    )
    out = Path(output_root)
    tool_vocab, names, per_prefix = _build_items(traces_path)

    any_items = per_prefix[pf.PREFIXES[0]]
    n_examples = len(any_items)
    repos = sorted({repo for _, _, repo in any_items})
    n_failures = sum(1 for _, label, _ in any_items if label == 1)

    model_heads: dict[str, dict] = {}
    prefix_metrics: dict[str, dict] = {}
    for prefix in pf.PREFIXES:
        items = per_prefix[prefix]
        feature_names = names[prefix]

        def fit_fn(rows, labels, _fn=feature_names):
            return model_mod.fit_head(_fn, rows, labels)

        # Predict logits (pre-sigmoid): AUROC-invariant, and the correct input
        # domain for Platt calibration (which then starts at identity).
        loro = ev.leave_one_repo_out(items, fit_fn, model_mod.predict_logit)
        oof_logits = loro["oof_scores"]
        oof_labels = loro["oof_labels"]
        boot = ev.bootstrap_auroc(oof_logits, oof_labels, n_resamples=n_resamples)
        platt_a, platt_b = cal.fit_guarded_platt(oof_logits, oof_labels)
        ece_before = ece([sigmoid(x) for x in oof_logits], oof_labels)
        ece_after = ece(
            [cal.apply_platt(x, platt_a, platt_b) for x in oof_logits],
            oof_labels,
        )
        full_head = model_mod.fit_head(
            feature_names,
            [row for row, _, _ in items],
            [label for _, label, _ in items],
        )
        model_heads[prefix] = {
            "feature_names": feature_names,
            "head": full_head,
            "platt": {"a": platt_a, "b": platt_b},
        }
        prefix_metrics[prefix] = {
            "n": len(items),
            "n_pos": sum(label for _, label, _ in items),
            "oof_auroc": loro["oof_auroc"],
            "bootstrap": boot,
            "ece_before": ece_before,
            "ece_after": ece_after,
            "per_repo": loro["per_repo"],
            "per_repo_order": loro["repos"],
        }

    model = {
        "model_version": BRAIN_VERSION,
        "task": "RISK_PREDICTION",
        "prefixes": model_heads,
        "tool_vocab": tool_vocab,
    }
    metrics = {
        "model_version": BRAIN_VERSION,
        "corpus": corpus_label,
        "n_examples": n_examples,
        "n_repos": len(repos),
        "failure_rate": (n_failures / n_examples) if n_examples else 0.0,
        "baseline_e0_prefix10_auroc": BASELINE_E0_PREFIX10_AUROC,
        "prefixes": prefix_metrics,
    }

    _write(out / "model.json", _canonical(model))
    _write(out / "metrics.json", _canonical(metrics))
    _write(out / "report.md", _report_markdown(metrics))
    return metrics


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m pneuma_lab.brain.train_full")
    parser.add_argument("--traces", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--corpus-manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--n-resamples", type=int, default=2000)
    parser.add_argument("--allow-dirty-code", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        metrics = run_full_training(
            traces_path=args.traces,
            authorization_path=args.authorization,
            corpus_manifest_path=args.corpus_manifest,
            output_root=args.out,
            n_resamples=args.n_resamples,
            require_clean_code=not args.allow_dirty_code,
        )
    except preflight.BrainPreflightError as exc:
        print(f"preflight failed: {exc}", file=sys.stderr)
        return 2
    for prefix in pf.PREFIXES:
        entry = metrics["prefixes"][prefix]
        boot = entry["bootstrap"]
        print(
            f"{prefix:10s} OOF AUROC={_fmt(entry['oof_auroc'])} "
            f"CI=[{_fmt(boot['lo'])},{_fmt(boot['hi'])}]"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

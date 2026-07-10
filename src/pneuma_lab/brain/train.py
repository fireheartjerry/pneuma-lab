"""PneumaBrain-v0.1 training orchestrator (offline, advisory-only, deterministic).

Pipeline: corpus preflight -> load examples -> freeze tool vocab on dev ->
featurize -> repo-grouped split -> fit RISK head on dev -> score dev/eval ->
write model.json, metrics.json, report.md. Only tasks with real labels train;
others are masked. No numpy, no randomness, no wall-clock.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pneuma_lab.brain import corpus as corpus_mod
from pneuma_lab.brain import features as feat
from pneuma_lab.brain import model as model_mod
from pneuma_lab.brain import preflight
from pneuma_lab.brain import report as report_mod
from pneuma_lab.brain import split as split_mod
from pneuma_lab.brain import BRAIN_VERSION

# v0.1 heads with a real label source today. Others are masked until proxy
# converters exist (see the proxy-heads follow-up plan).
TRAINABLE_TASKS = ("RISK_PREDICTION",)
LABELERS = {"RISK_PREDICTION": corpus_mod.risk_label}


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


def run_training(
    *,
    corpus_path: str | Path,
    authorization_path: str | Path,
    corpus_manifest_path: str | Path,
    output_root: str | Path,
    require_clean_code: bool = True,
) -> dict:
    """Verify authorization, then train and score every trainable task."""
    preflight.verify_corpus_run(
        authorization_path,
        corpus_manifest_path,
        output_root,
        require_clean_code=require_clean_code,
    )
    out = Path(output_root)
    examples = corpus_mod.load_examples(corpus_path)
    for example in examples:
        feat.assert_no_leakage(example)

    assignment = split_mod.assign(examples)
    dev_examples = [e for i, e in enumerate(examples) if assignment[i] == "dev"]
    tool_vocab = feat.freeze_tool_vocab(
        [e["input"]["observable_summary"] for e in dev_examples]
    )
    names = feat.feature_names(tool_vocab)

    model = model_mod.MultiTaskModel(BRAIN_VERSION_OK=BRAIN_VERSION)
    tasks_report: dict[str, dict] = {}

    for task in TRAINABLE_TASKS:
        task_examples = corpus_mod.examples_for_task(examples, task)
        if not task_examples:
            continue
        labeler = LABELERS[task]
        indexed = [
            (e, split_mod.split_of_repo(corpus_mod.repo_of(e))) for e in task_examples
        ]
        dev_rows, dev_labels = [], []
        eval_rows, eval_labels = [], []
        for example, where in indexed:
            row = feat.feature_row(example["input"]["observable_summary"], tool_vocab)
            label = labeler(example)
            if where == "dev":
                dev_rows.append(row)
                dev_labels.append(label)
            else:
                eval_rows.append(row)
                eval_labels.append(label)
        if not dev_rows:
            continue
        head = model_mod.fit_head(names, dev_rows, dev_labels)
        model.add_task(task, head)
        dev_probs = [model_mod.predict_head(head, row) for row in dev_rows]
        eval_probs = [model_mod.predict_head(head, row) for row in eval_rows]
        tasks_report[task] = {
            "dev": report_mod.score_split(dev_probs, dev_labels),
            "eval": report_mod.score_split(eval_probs, eval_labels),
            "baseline_e0_auroc": report_mod.BASELINE_E0_AUROC,
        }

    metrics = {
        "model_version": BRAIN_VERSION,
        "split_method": split_mod.SPLIT_METHOD,
        "feature_version": feat.CORPUS_FEATURE_VERSION,
        "tool_vocab": tool_vocab,
        "n_examples": len(examples),
        "tasks": tasks_report,
    }

    _write(out / "model.json", model.to_json() + "\n")
    _write(out / "metrics.json", _canonical(metrics))
    _write(out / "report.md", report_mod.markdown(metrics))
    return metrics


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m pneuma_lab.brain.train")
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--corpus-manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--allow-dirty-code", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        metrics = run_training(
            corpus_path=args.corpus,
            authorization_path=args.authorization,
            corpus_manifest_path=args.corpus_manifest,
            output_root=args.out,
            require_clean_code=not args.allow_dirty_code,
        )
    except preflight.BrainPreflightError as exc:
        print(f"preflight failed: {exc}", file=sys.stderr)
        return 2
    risk = metrics["tasks"].get("RISK_PREDICTION", {})
    print(f"trained tasks: {sorted(metrics['tasks'])}; RISK eval={risk.get('eval')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

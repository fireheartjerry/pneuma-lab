"""Month-1 estimator training CLI (doc 08 §4): E1 risk + E2 stage-1.

Usage:
    python -m pneuma_lab.estimators.train --traces <pneuma_traces.jsonl> \
        --out build/estimators

Deterministic end to end: grouped repo split via sha256, frozen dev tool
vocabulary, zero-init full-batch logistic, canonical-JSON artifacts. Running
twice on the same corpus must produce byte-identical model/metrics/report
files (deployment gate 1, doc 08 §5). Pure stdlib.

Labels: y = 1 iff ``labels.resolved`` is False (failure risk). Traces with
``outcome.report.error_eval`` or ``test_timeout`` true are excluded as label
QC only. E2 stage-1 uses the silent-risk PROXY label: eventual failure whose
prefix is error-quiet in the last-3-step window (proxy tag propagated).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os

from pneuma_lab.adapters.envelope import canonical_json
from pneuma_lab.estimators import features as feat
from pneuma_lab.estimators import logistic as logit
from pneuma_lab.estimators import metrics as met

EVAL_BUCKET_COUNT = 10
EVAL_BUCKET_THRESHOLD = 3
MONOTONICITY_PROBE_POINTS = 20
E1_TARGET_AUROC_PREFIX_50 = 0.65
E1_TARGET_AUROC_FULL = 0.70
E2_TARGET_AUROC = 0.60
TARGET_ECE = 0.05
E2_PROXY_TAG = (
    "silent-risk-stage-1 (resolved=False AND last3_error_density==0 at prefix)"
)

FRACTION_NAMES = tuple(name for name, _, _ in feat.PREFIX_FRACTIONS)


def splitOfRepo(repo: str) -> str:
    """Deterministic grouped split. Empty repo -> dev (contamination-safe)."""
    if repo == "":
        return "dev"
    digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()
    bucket = int(digest, 16) % EVAL_BUCKET_COUNT
    return "eval" if bucket < EVAL_BUCKET_THRESHOLD else "dev"


def loadCorpus(path: str) -> tuple[list, dict]:
    """One pass over the JSONL: labels, QC exclusions, split, prefix stats."""
    records: list[dict] = []
    counts = {
        "total_lines": 0,
        "excluded_error_eval": 0,
        "excluded_test_timeout": 0,
        "excluded_total": 0,
        "skipped_no_agent_frames": 0,
    }
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            counts["total_lines"] += 1
            trace = json.loads(line)
            label = feat.readLabel(trace)
            if label["error_eval"] or label["test_timeout"]:
                if label["error_eval"]:
                    counts["excluded_error_eval"] += 1
                if label["test_timeout"]:
                    counts["excluded_test_timeout"] += 1
                counts["excluded_total"] += 1
                continue
            try:
                fractions = {
                    name: feat.prefixFeatureStats(trace, name)
                    for name in FRACTION_NAMES
                }
            except ValueError:
                counts["skipped_no_agent_frames"] += 1
                continue
            records.append(
                {
                    "y": 1 if label["resolved"] is False else 0,
                    "repo": label["repo"],
                    "split": splitOfRepo(label["repo"]),
                    "fractions": fractions,
                }
            )
    return records, counts


def freezeToolVocab(records: list) -> list:
    """Six most common tools by full-trace call count on the dev split.

    Ties break lexicographically. Frozen into the model artifact.
    """
    totals: dict[str, int] = {}
    for rec in records:
        if rec["split"] != "dev":
            continue
        _, counter = rec["fractions"]["full"]
        for tool, count in counter.items():
            totals[tool] = totals.get(tool, 0) + count
    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    return [tool for tool, _ in ranked[: feat.N_FROZEN_TOOLS]]


def buildRows(
    records: list, split: str, fraction_name: str, tool_vocab: list, no_length: bool
) -> tuple[list, list]:
    names = feat.featureNames(tool_vocab, fraction_name, no_length=no_length)
    rows = []
    for rec in records:
        if rec["split"] != split:
            continue
        base, counter = rec["fractions"][fraction_name]
        assembled = feat.assembleFeatures(
            base, counter, tool_vocab, fraction_name, no_length=no_length
        )
        rows.append(tuple(assembled[name] for name in names))
    return names, rows


def labelsOf(records: list, split: str) -> list:
    return [rec["y"] for rec in records if rec["split"] == split]


def e2Labels(records: list, split: str, fraction_name: str) -> list:
    out = []
    for rec in records:
        if rec["split"] != split:
            continue
        base, _ = rec["fractions"][fraction_name]
        quiet = base["last3_error_density"] == 0.0
        out.append(1 if (rec["y"] == 1 and quiet) else 0)
    return out


def retryScores(records: list, split: str, fraction_name: str) -> list:
    return [
        rec["fractions"][fraction_name][0]["max_retry"]
        for rec in records
        if rec["split"] == split
    ]


def trainVariant(names: list, dev_rows: list, dev_labels: list) -> dict:
    means, stds = logit.standardizationParams(dev_rows)
    rows_std = [logit.standardizeRow(r, means, stds) for r in dev_rows]
    weights, bias = logit.trainLogistic(rows_std, dev_labels)
    return {
        "features": list(names),
        "weights": {name: w for name, w in zip(names, weights)},
        "bias": bias,
        "standardization": {
            "means": {name: m for name, m in zip(names, means)},
            "stds": {name: s for name, s in zip(names, stds)},
        },
    }


def predictRows(model: dict, names: list, rows: list) -> list:
    means = [model["standardization"]["means"][n] for n in names]
    stds = [model["standardization"]["stds"][n] for n in names]
    weights = [model["weights"][n] for n in names]
    bias = model["bias"]
    return [
        logit.predictProb(logit.standardizeRow(r, means, stds), weights, bias)
        for r in rows
    ]


def scoreProbs(probs: list, labels: list) -> dict:
    return {
        "auroc": met.auroc(probs, labels),
        "brier": met.brier(probs, labels),
        "ece_15bin": met.ece(probs, labels),
    }


def monotonicityProbe(model: dict, names: list) -> dict:
    """20 synthetic vectors differing ONLY in error_density (0->1): predicted
    risk must be non-decreasing. Base vector = dev feature means."""
    means = model["standardization"]["means"]
    base = [means[n] for n in names]
    idx = names.index("error_density")
    probs = []
    for i in range(MONOTONICITY_PROBE_POINTS):
        row = list(base)
        row[idx] = i / (MONOTONICITY_PROBE_POINTS - 1)
        probs.append(predictRows(model, names, [tuple(row)])[0])
    passed = all(probs[i + 1] >= probs[i] - 1e-12 for i in range(len(probs) - 1))
    return {
        "passed": passed,
        "n_points": MONOTONICITY_PROBE_POINTS,
        "prob_at_density_0": probs[0],
        "prob_at_density_1": probs[-1],
    }


def repoListSha(records: list, split: str) -> tuple[str, int]:
    repos = sorted({rec["repo"] for rec in records if rec["split"] == split})
    digest = hashlib.sha256(canonical_json(repos).encode("utf-8")).hexdigest()
    return digest, len(repos)


def writeText(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def writeJson(path: str, obj) -> None:
    writeText(path, canonical_json(obj) + "\n")


def fmt(value) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def metricsRow(prefix_name: str, block: dict) -> str:
    model_metrics = block["model_full_features"]
    ablation = block.get("model_no_length_features")
    constant = block["baseline_constant"]
    retry = block["baseline_retry_only"]
    cells = [
        prefix_name,
        fmt(model_metrics["auroc"]),
        fmt(model_metrics["brier"]),
        fmt(model_metrics["ece_15bin"]),
        fmt(ablation["auroc"]) if ablation else "n/a",
        fmt(constant["brier"]),
        fmt(retry["auroc"]),
        "0.5000",
    ]
    return "| " + " | ".join(cells) + " |"


def buildReport(estimator: str, metrics_doc: dict, extra_lines: list) -> str:
    lines = [
        f"# {estimator} training report (month-1, doc 08 §4)",
        "",
        f"Label: {metrics_doc['label_definition']}",
        "",
        "## Split (grouped by labels.repo, sha256 buckets, ~30% eval)",
        "",
    ]
    for split_name in ("dev", "eval"):
        s = metrics_doc["split"][split_name]
        lines.append(
            f"- {split_name}: {s['n_traces']} traces, {s['n_repos']} repos, "
            f"{s['n_positive']} positive (y=1)"
        )
    exc = metrics_doc["exclusions"]
    lines += [
        f"- label-QC exclusions: {exc['excluded_total']} "
        f"(error_eval={exc['excluded_error_eval']}, "
        f"test_timeout={exc['excluded_test_timeout']}); "
        f"skipped_no_agent_frames={exc['skipped_no_agent_frames']}",
        "",
        "## Eval-split metrics per prefix",
        "",
        "| prefix | AUROC | Brier | ECE(15) | ablation AUROC (no length) | "
        "constant Brier | retry-only AUROC | chance AUROC |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for prefix_name in FRACTION_NAMES:
        lines.append(metricsRow(prefix_name, metrics_doc["per_prefix"][prefix_name]))
    lines += ["", "## Honesty notes", ""]
    lines += extra_lines
    lines += [
        "- No objective-text embedding features: month-1 has no encoder "
        "dependency; this omission is deliberate and recorded (doc 08 §2.1 "
        "objective-text row deferred).",
        "- ECE is reported RAW (no isotonic/Platt post-calibration fitted); "
        "the pre-registered ECE <= 0.05 target was stated post-calibration.",
        "- The length-confound ablation removes every feature that grows "
        "monotonically with prefix length: n_steps_prefix, "
        "log1p_num_agent_steps, n_tool_calls_total, and all per-tool raw "
        "counts.",
        "- Scores are advisory pressure/prior signals over observable "
        "receipts; nothing here is an interiority claim.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pneuma_lab.estimators.train",
        description="Train month-1 estimators E1 (risk) and E2 stage-1.",
    )
    parser.add_argument("--traces", required=True, help="pneuma_traces.jsonl path")
    parser.add_argument("--out", default="build/estimators", help="artifact root")
    args = parser.parse_args(argv)

    records, counts = loadCorpus(args.traces)
    tool_vocab = freezeToolVocab(records)
    dev_sha, n_dev_repos = repoListSha(records, "dev")
    eval_sha, n_eval_repos = repoListSha(records, "eval")

    split_block = {}
    for split_name, n_repos in (("dev", n_dev_repos), ("eval", n_eval_repos)):
        ys = labelsOf(records, split_name)
        split_block[split_name] = {
            "n_traces": len(ys),
            "n_repos": n_repos,
            "n_positive": sum(ys),
        }

    shared_meta = {
        "feature_extractor_version": feat.FEATURE_EXTRACTOR_VERSION,
        "frozen_tool_list": tool_vocab,
        "split": {
            "method": (
                "int(sha256(labels.repo),16) % 10 < 3 -> eval; empty repo -> dev"
            ),
            "dev_repos_sha256": dev_sha,
            "eval_repos_sha256": eval_sha,
            "n_dev_repos": n_dev_repos,
            "n_eval_repos": n_eval_repos,
        },
        "training": {
            "algorithm": "full-batch logistic regression, L2, zero-init",
            "learning_rate": logit.LEARNING_RATE,
            "lr_decay": logit.LR_DECAY,
            "n_iterations": logit.N_ITERATIONS,
            "l2_lambda": logit.L2_LAMBDA,
            "standardization": "dev-split means/stds",
        },
    }

    dev_y1 = labelsOf(records, "dev")
    eval_y1 = labelsOf(records, "eval")
    dev_base_rate = sum(dev_y1) / len(dev_y1)

    e1_models: dict = {}
    e2_models: dict = {}
    e1_per_prefix: dict = {}
    e2_per_prefix: dict = {}
    e1_monotonicity: dict = {}

    for fraction_name in FRACTION_NAMES:
        retry_eval = retryScores(records, "eval", fraction_name)
        dev_y2 = e2Labels(records, "dev", fraction_name)
        eval_y2 = e2Labels(records, "eval", fraction_name)
        dev_base_rate_e2 = sum(dev_y2) / len(dev_y2)

        # E1 full-feature model.
        names, dev_rows = buildRows(records, "dev", fraction_name, tool_vocab, False)
        _, eval_rows = buildRows(records, "eval", fraction_name, tool_vocab, False)
        model_full = trainVariant(names, dev_rows, dev_y1)
        probs_full = predictRows(model_full, names, eval_rows)
        e1_models[fraction_name] = model_full
        e1_monotonicity[fraction_name] = monotonicityProbe(model_full, names)

        # E1 length-confound ablation (no step-count / count features).
        names_nl, dev_rows_nl = buildRows(
            records, "dev", fraction_name, tool_vocab, True
        )
        _, eval_rows_nl = buildRows(records, "eval", fraction_name, tool_vocab, True)
        model_nl = trainVariant(names_nl, dev_rows_nl, dev_y1)
        probs_nl = predictRows(model_nl, names_nl, eval_rows_nl)
        e1_models[f"{fraction_name}_no_length"] = model_nl

        constant_probs = [dev_base_rate] * len(eval_y1)
        e1_per_prefix[fraction_name] = {
            "model_full_features": scoreProbs(probs_full, eval_y1),
            "model_no_length_features": scoreProbs(probs_nl, eval_y1),
            "baseline_constant": dict(
                scoreProbs(constant_probs, eval_y1), prob=dev_base_rate
            ),
            "baseline_retry_only": {"auroc": met.auroc(retry_eval, eval_y1)},
            "baseline_chance_auroc": 0.5,
        }

        # E2 stage-1 (proxy labels), same pipeline, full feature set.
        model_e2 = trainVariant(names, dev_rows, dev_y2)
        probs_e2 = predictRows(model_e2, names, eval_rows)
        e2_models[fraction_name] = model_e2
        constant_probs_e2 = [dev_base_rate_e2] * len(eval_y2)
        e2_per_prefix[fraction_name] = {
            "model_full_features": scoreProbs(probs_e2, eval_y2),
            "baseline_constant": dict(
                scoreProbs(constant_probs_e2, eval_y2), prob=dev_base_rate_e2
            ),
            "baseline_retry_only": {"auroc": met.auroc(retry_eval, eval_y2)},
            "baseline_chance_auroc": 0.5,
            "n_positive_dev": sum(dev_y2),
            "n_positive_eval": sum(eval_y2),
        }

    e1_targets = {
        "auroc_prefix_50_target": E1_TARGET_AUROC_PREFIX_50,
        "auroc_full_target": E1_TARGET_AUROC_FULL,
        "ece_target_post_calibration": TARGET_ECE,
        "auroc_prefix_50_met": (
            e1_per_prefix["prefix_50"]["model_full_features"]["auroc"]
            >= E1_TARGET_AUROC_PREFIX_50
        ),
        "auroc_full_met": (
            e1_per_prefix["full"]["model_full_features"]["auroc"]
            >= E1_TARGET_AUROC_FULL
        ),
    }
    e2_targets = {
        "auroc_target": E2_TARGET_AUROC,
        "ece_target_post_calibration": TARGET_ECE,
        "auroc_met_per_prefix": {
            name: e2_per_prefix[name]["model_full_features"]["auroc"] >= E2_TARGET_AUROC
            for name in FRACTION_NAMES
        },
    }

    e1_metrics = {
        "estimator": "e1-v0",
        "label_definition": "y=1 iff labels.resolved is False (failure risk)",
        "exclusions": counts,
        "split": split_block,
        "per_prefix": e1_per_prefix,
        "monotonicity_probe": e1_monotonicity,
        "targets": e1_targets,
    }
    e2_metrics = {
        "estimator": "e2-v0",
        "label_definition": (
            "y=1 iff labels.resolved is False AND last3_error_density==0.0 "
            "at the prefix point (error-quiet eventual failure)"
        ),
        "proxy": E2_PROXY_TAG,
        "exclusions": counts,
        "split": split_block,
        "per_prefix": e2_per_prefix,
        "targets": e2_targets,
    }

    e1_model_doc = dict(
        shared_meta,
        estimator="e1-v0",
        label_definition=e1_metrics["label_definition"],
        models=e1_models,
    )
    e2_model_doc = dict(
        shared_meta,
        estimator="e2-v0",
        label_definition=e2_metrics["label_definition"],
        proxy=E2_PROXY_TAG,
        models=e2_models,
    )

    mono_lines = [
        (
            f"- E1 monotonicity probe ({MONOTONICITY_PROBE_POINTS} synthetic "
            f"vectors, error_density 0->1) [{name}]: "
            f"{'PASS' if e1_monotonicity[name]['passed'] else 'FAIL'}"
        )
        for name in FRACTION_NAMES
    ]
    e1_report = buildReport(
        "e1-v0",
        e1_metrics,
        mono_lines
        + [
            (
                "- Pre-registered targets: AUROC >= "
                f"{E1_TARGET_AUROC_PREFIX_50} at prefix_50 "
                f"(observed {fmt(e1_per_prefix['prefix_50']['model_full_features']['auroc'])}, "
                f"{'MET' if e1_targets['auroc_prefix_50_met'] else 'MISSED'}); "
                f">= {E1_TARGET_AUROC_FULL} full "
                f"(observed {fmt(e1_per_prefix['full']['model_full_features']['auroc'])}, "
                f"{'MET' if e1_targets['auroc_full_met'] else 'MISSED'})."
            ),
        ],
    )
    e2_positive_lines = [
        (
            f"- E2 positives [{name}]: dev "
            f"{e2_per_prefix[name]['n_positive_dev']}, eval "
            f"{e2_per_prefix[name]['n_positive_eval']}"
        )
        for name in FRACTION_NAMES
    ]
    e2_report = buildReport(
        "e2-v0",
        e2_metrics,
        [
            f"- PROXY LABELS: {E2_PROXY_TAG}. This conflates 'agent not "
            "testing' with 'nothing to find' (doc 08 E2 failure mode); the "
            "proxy tag must propagate into any consuming frame provenance.",
            "- The last3_error_density feature partially determines the "
            "label by construction (quiet gate); the learned part is failure "
            "among quiet prefixes.",
        ]
        + e2_positive_lines,
    )

    for sub, model_doc, metrics_doc, report_text in (
        ("e1-v0", e1_model_doc, e1_metrics, e1_report),
        ("e2-v0", e2_model_doc, e2_metrics, e2_report),
    ):
        out_dir = os.path.join(args.out, sub)
        os.makedirs(out_dir, exist_ok=True)
        writeJson(os.path.join(out_dir, "model.json"), model_doc)
        writeJson(os.path.join(out_dir, "metrics.json"), metrics_doc)
        writeText(os.path.join(out_dir, "report.md"), report_text)

    print(f"trained e1-v0 + e2-v0 -> {args.out}")
    print(
        f"traces={counts['total_lines']} excluded={counts['excluded_total']} "
        f"dev={split_block['dev']['n_traces']} eval={split_block['eval']['n_traces']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

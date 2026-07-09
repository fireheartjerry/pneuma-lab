"""Month-1 estimator training CLI (doc 08 §4): E1 risk + E2 stage-1.

Usage:
    python -m pneuma_lab.estimators.train --traces <pneuma_traces.jsonl> \
        --run-manifest <estimator-run-manifest.json> \
        --out build/training_runs/openhands-sampled/<run-id>/

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
import sys
from pathlib import Path

from pneuma_lab.adapters.envelope import canonical_json
from pneuma_lab.estimators import features as feat
from pneuma_lab.estimators import logistic as logit
from pneuma_lab.estimators import metrics as met
from pneuma_lab.training import preflight

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
ESTIMATOR_ARTIFACT_FILES = tuple(
    f"{estimator}/{filename}"
    for estimator in ("e1-v0", "e2-v0")
    for filename in ("model.json", "metrics.json", "report.md")
)
COMPLETE_RUN_FILES = frozenset((*ESTIMATOR_ARTIFACT_FILES, "run_receipt.json"))
COMPLETE_RUN_DIRS = frozenset(("e1-v0", "e2-v0"))


def splitOfRepo(repo: str) -> str:
    """Deterministic grouped split. Empty repo -> dev (contamination-safe)."""
    if repo == "":
        return "dev"
    digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()
    bucket = int(digest, 16) % EVAL_BUCKET_COUNT
    return "eval" if bucket < EVAL_BUCKET_THRESHOLD else "dev"


def loadCorpus(path: str, *, expected_sha256: str | None = None) -> tuple[list, dict]:
    """One byte-bound pass: digest, labels, exclusions, split, prefix stats."""
    records: list[dict] = []
    digest = hashlib.sha256()
    counts = {
        "total_lines": 0,
        "excluded_error_eval": 0,
        "excluded_test_timeout": 0,
        "excluded_total": 0,
        "skipped_no_agent_frames": 0,
    }
    with open(path, "rb") as handle:
        for raw_line in handle:
            digest.update(raw_line)
            line = raw_line.decode("utf-8").strip()
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
    observed_sha256 = f"sha256:{digest.hexdigest()}"
    if expected_sha256 is not None and observed_sha256 != expected_sha256:
        raise preflight.PreflightError(
            "source_changed_during_load",
            "the trace bytes parsed by loadCorpus differ from the authorized hash",
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


def fileSha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def buildTrainingProvenance(run: preflight.VerifiedEstimatorRun) -> dict:
    """Canonical source/authorization binding copied into future model files."""
    manifest = run.manifest
    authorization = run.authorization
    manifest_ref = run.manifest_path.relative_to(run.repo_root).as_posix()
    return {
        "binding_status": "verified_before_fit",
        "run_id": manifest["run_id"],
        "run_manifest": {
            "path": manifest_ref,
            "sha256": run.manifest_sha256,
        },
        "source_code": {
            "authorized_code_commit": run.code_state.authorized_code_commit,
            "execution_head": run.code_state.execution_head,
            "required_tree_state": manifest["source_code"][
                "required_tree_state"
            ],
            "verified_tree_state": "clean",
            "protected_paths_unchanged": [
                "src/",
                "schemas/",
                "pyproject.toml",
            ],
        },
        "authorization": {
            "authorization_id": authorization["authorization_id"],
            "path": manifest["authorization_ref"]["path"],
            "sha256": manifest["authorization_ref"]["sha256"],
            "decision": authorization["decision"],
            "scope": authorization["scope"],
            "reviewer": authorization["reviewer"],
            "reviewed_at": authorization["reviewed_at"],
        },
        "source": {
            "traces_path": manifest["source"]["traces_path"],
            "traces_sha256": manifest["source"]["traces_sha256"],
            "adapter_report_path": manifest["source"]["adapter_report_path"],
            "adapter_report_sha256": manifest["source"][
                "adapter_report_sha256"
            ],
            "hf_repo": manifest["source"]["hf_repo"],
            "hf_revision": manifest["source"]["hf_revision"],
        },
        "split": {
            "manifest_path": manifest["split"]["manifest_path"],
            "manifest_sha256": manifest["split"]["manifest_sha256"],
            "method": manifest["split"]["method"],
        },
        "class_imbalance_handling": manifest["class_imbalance_handling"],
        "model_use": manifest["model_use"],
        "artifact_root": manifest["artifact_root"],
        "release_authorization": manifest["release_authorization"],
        "runtime_integration": manifest["runtime_integration"],
    }


def writeText(path: str, text: str) -> None:
    try:
        with open(path, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except FileExistsError:
        _output_failure(
            "artifact_layout_invalid",
            "output target appeared before its exclusive write",
        )


def writeJson(path: str, obj) -> None:
    writeText(path, canonical_json(obj) + "\n")


def _output_failure(code: str, message: str) -> None:
    raise preflight.PreflightError(code, message)


def _assert_output_path_contained(root: Path, path: Path) -> None:
    if path.is_symlink():
        _output_failure("artifact_path_not_approved", "output path is a symlink")
    try:
        path.parent.resolve().relative_to(root.resolve())
    except ValueError:
        _output_failure(
            "artifact_path_not_approved",
            "output target resolves outside the authorized artifact root",
        )


def prepareOutputPaths(run: preflight.VerifiedEstimatorRun) -> dict[str, Path]:
    """Claim an absent/empty root and create only the two expected directories."""
    root = run.artifact_root
    preflight.require_empty_artifact_root(root)
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink() or root.resolve() != root:
        _output_failure(
            "artifact_root_not_approved",
            "artifact root became a symlink or junction",
        )
    for directory in sorted(COMPLETE_RUN_DIRS):
        target = root / directory
        try:
            target.mkdir(exist_ok=False)
        except FileExistsError:
            _output_failure(
                "artifact_root_not_empty",
                "unexpected output entry appeared before artifact writes",
            )
        _assert_output_path_contained(root, target / "placeholder")
    paths = {relative: root / relative for relative in COMPLETE_RUN_FILES}
    for path in paths.values():
        _assert_output_path_contained(root, path)
        if path.exists() or path.is_symlink():
            _output_failure(
                "artifact_root_not_empty",
                "an expected output target already exists",
            )
    return paths


def validateCompletedOutputLayout(run: preflight.VerifiedEstimatorRun) -> None:
    """Require the exact receipt-backed file and directory set after writes."""
    root = run.artifact_root.resolve()
    actual_files: set[str] = set()
    actual_dirs: set[str] = set()
    for path in run.artifact_root.rglob("*"):
        relative = path.relative_to(run.artifact_root).as_posix()
        if path.is_symlink():
            _output_failure(
                "artifact_layout_invalid", f"symlink found in output: {relative}"
            )
        try:
            path.resolve().relative_to(root)
        except ValueError:
            _output_failure(
                "artifact_layout_invalid",
                f"output resolves outside artifact root: {relative}",
            )
        if path.is_file():
            actual_files.add(relative)
        elif path.is_dir():
            actual_dirs.add(relative)
        else:
            _output_failure(
                "artifact_layout_invalid", f"unsupported output entry: {relative}"
            )
    if actual_files != COMPLETE_RUN_FILES or actual_dirs != COMPLETE_RUN_DIRS:
        _output_failure(
            "artifact_layout_invalid",
            "completed run does not contain the exact authorized artifact set",
        )


def writeRunReceipt(
    run: preflight.VerifiedEstimatorRun,
    training_provenance: dict,
    written_artifacts: list[str],
) -> dict:
    """Write the deterministic completion receipt after every artifact exists."""
    root = run.artifact_root
    relative_artifacts: set[str] = set()
    for path_text in written_artifacts:
        path = Path(path_text)
        _assert_output_path_contained(root, path)
        if not path.is_file() or path.is_symlink():
            _output_failure(
                "artifact_layout_invalid", "receipt input is not a regular file"
            )
        try:
            relative_artifacts.add(
                path.resolve().relative_to(root.resolve()).as_posix()
            )
        except ValueError:
            _output_failure(
                "artifact_layout_invalid",
                "receipt input resolves outside the artifact root",
            )
    if relative_artifacts != set(ESTIMATOR_ARTIFACT_FILES):
        _output_failure(
            "artifact_layout_invalid",
            "receipt inputs differ from the exact estimator artifact set",
        )
    artifact_hashes = {
        Path(path).resolve().relative_to(root.resolve()).as_posix(): fileSha256(path)
        for path in sorted(written_artifacts)
    }
    receipt = {
        "estimator_run_receipt_schema_version": "0.1.0",
        "status": "completed_local_research",
        "training_provenance": training_provenance,
        "artifacts_sha256": artifact_hashes,
    }
    receipt_path = root / "run_receipt.json"
    _assert_output_path_contained(root, receipt_path)
    if receipt_path.exists() or receipt_path.is_symlink():
        _output_failure("artifact_layout_invalid", "run receipt already exists")
    writeJson(str(receipt_path), receipt)
    validateCompletedOutputLayout(run)
    return receipt


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
    parser.add_argument(
        "--run-manifest",
        required=True,
        help="schema-valid, separately authorized estimator run manifest",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="run-scoped artifact root declared by --run-manifest",
    )
    args = parser.parse_args(argv)

    try:
        verified_run = preflight.verify_estimator_run(
            args.run_manifest,
            args.traces,
            args.out,
        )
    except preflight.PreflightError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    records, counts = loadCorpus(
        str(verified_run.traces_path),
        expected_sha256=verified_run.manifest["source"]["traces_sha256"],
    )
    dev_sha, n_dev_repos = repoListSha(records, "dev")
    eval_sha, n_eval_repos = repoListSha(records, "eval")
    dev_traces = sum(rec["split"] == "dev" for rec in records)
    eval_traces = sum(rec["split"] == "eval" for rec in records)
    excluded_traces = counts["total_lines"] - len(records)
    try:
        preflight.verify_loaded_corpus(
            verified_run,
            dev_repos_sha256=dev_sha,
            eval_repos_sha256=eval_sha,
            dev_traces=dev_traces,
            eval_traces=eval_traces,
            excluded_traces=excluded_traces,
            total_traces=counts["total_lines"],
        )
    except preflight.PreflightError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    tool_vocab = freezeToolVocab(records)
    training_provenance = buildTrainingProvenance(verified_run)

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
        "training_provenance": training_provenance,
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

    output_paths = prepareOutputPaths(verified_run)
    written_artifacts: list[str] = []
    for sub, model_doc, metrics_doc, report_text in (
        ("e1-v0", e1_model_doc, e1_metrics, e1_report),
        ("e2-v0", e2_model_doc, e2_metrics, e2_report),
    ):
        model_path = str(output_paths[f"{sub}/model.json"])
        metrics_path = str(output_paths[f"{sub}/metrics.json"])
        report_path = str(output_paths[f"{sub}/report.md"])
        for path in (model_path, metrics_path, report_path):
            _assert_output_path_contained(verified_run.artifact_root, Path(path))
        writeJson(model_path, model_doc)
        writeJson(metrics_path, metrics_doc)
        writeText(report_path, report_text)
        written_artifacts.extend((model_path, metrics_path, report_path))

    writeRunReceipt(verified_run, training_provenance, written_artifacts)

    print(f"trained e1-v0 + e2-v0 -> {verified_run.artifact_root}")
    print(
        f"traces={counts['total_lines']} excluded={counts['excluded_total']} "
        f"dev={split_block['dev']['n_traces']} eval={split_block['eval']['n_traces']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

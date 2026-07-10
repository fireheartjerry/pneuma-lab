"""Per-task scoring and a compact deterministic markdown report."""

from __future__ import annotations

from pneuma_lab.estimators import metrics as met

# The E-0 observable-feature logistic baseline (prefix-10 B1 AUROC) to beat.
BASELINE_E0_AUROC = 0.70


def score_split(probs: list[float], labels: list[int]) -> dict:
    """AUROC (None if single-class), Brier, ECE, and counts for one split."""
    n = len(probs)
    n_pos = sum(1 for y in labels if y == 1)
    return {
        "n": n,
        "n_pos": n_pos,
        "auroc": met.auroc(probs, labels),
        "brier": met.brier(probs, labels) if n else None,
        "ece": met.ece(probs, labels) if n else None,
    }


def _fmt(value) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def markdown(payload: dict) -> str:
    """Render a stable markdown report from a scored payload."""
    lines = [
        "# PneumaBrain-v0.1 training report",
        "",
        f"- model_version: `{payload['model_version']}`",
        f"- split_method: `{payload['split_method']}`",
        "",
        "| task | split | n | n_pos | AUROC | Brier | ECE | E-0 baseline |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for task in sorted(payload["tasks"]):
        entry = payload["tasks"][task]
        baseline = _fmt(entry.get("baseline_e0_auroc"))
        for split_name in ("dev", "eval"):
            split = entry.get(split_name) or {}
            lines.append(
                f"| {task} | {split_name} | {split.get('n', 0)} | "
                f"{split.get('n_pos', 0)} | {_fmt(split.get('auroc'))} | "
                f"{_fmt(split.get('brier'))} | {_fmt(split.get('ece'))} | {baseline} |"
            )
    lines.append("")
    lines.append(
        "Advisory-only. No runtime integration, no verifier bypass, no consciousness claim."
    )
    return "\n".join(lines) + "\n"


__all__ = ["BASELINE_E0_AUROC", "score_split", "markdown"]

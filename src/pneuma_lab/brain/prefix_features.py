"""Prefix-windowed features from raw PneumaTrace agent trajectories.

Reuses the leakage-masked estimator extractor (``estimators.features``), which
deletes outcome/oracle/label fields before computing anything. Enables
early-warning RISK: predicting failure from the first 25% / 50% / 100% of a
trajectory. Labels are read separately from the raw trace and never featurized.
"""

from __future__ import annotations

from typing import Iterable

from pneuma_lab.estimators import features as est

PREFIXES = ("prefix_25", "prefix_50", "full")


def freeze_tool_vocab(traces: Iterable[dict], n: int = est.N_FROZEN_TOOLS) -> list[str]:
    """Top-n tools by total call count across agent_trace frames. Deterministic."""
    totals: dict[str, int] = {}
    for trace in traces:
        for frame in est.agentFrames(trace):
            for call in frame.get("tool_calls") or []:
                tool = str(call.get("tool") or "unknown")
                totals[tool] = totals.get(tool, 0) + 1
    ordered = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    return [tool for tool, _ in ordered[:n]]


def feature_names(tool_vocab: list[str], fraction_name: str) -> list[str]:
    """Deterministic sorted feature-name order for one prefix fraction."""
    return sorted(est.featureNames(tool_vocab, fraction_name))


def feature_vector(
    trace: dict, fraction_name: str, tool_vocab: list[str]
) -> list[float]:
    """Ordered feature row for one trace at one prefix (raises if no frames)."""
    values = est.extractFeatures(trace, fraction_name, tool_vocab)
    return [values[name] for name in sorted(values)]


def label_of(trace: dict) -> int | None:
    """RISK label from the raw trace: failure=1, success=0, None if unknown."""
    resolved = est.readLabel(trace)["resolved"]
    if resolved is None:
        return None
    return 0 if bool(resolved) else 1


def repo_of(trace: dict) -> str:
    """Repository for the grouped split, read from the raw trace label block."""
    return est.readLabel(trace)["repo"] or ""


__all__ = [
    "PREFIXES",
    "freeze_tool_vocab",
    "feature_names",
    "feature_vector",
    "label_of",
    "repo_of",
]

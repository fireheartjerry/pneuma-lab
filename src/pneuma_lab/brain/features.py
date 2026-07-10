"""Leakage-safe, observable-only feature extraction from corpus examples.

Features are read from each PneumaTrainingExample's ``input.observable_summary``
(full-trace only; the examples carry no raw frames, so no prefix windows).
Deterministic: no wall-clock, no randomness. A frozen tool vocabulary is built
from the dev split only.
"""

from __future__ import annotations

import math

CORPUS_FEATURE_VERSION = "pneuma-brain-features/0.1.0"
N_FROZEN_TOOLS = 6

SCALAR_FEATURE_NAMES = (
    "log1p_tool_call_count",
    "retry_count_max",
    "retry_count_mean",
    "steps_retry_ge2",
    "strategy_switches_final",
    "error_density",
    "log1p_error_observation_count",
    "log1p_observation_count",
    "log1p_assistant_len_mean",
    "log1p_assistant_len_max",
    "log1p_observation_len_mean",
    "log1p_observation_len_max",
)

TOOL_COUNT_PREFIX = "tool_count__"

# Any of these keys appearing anywhere under input is a leakage bug.
FORBIDDEN_INPUT_KEYS = frozenset(
    {
        "resolved",
        "outcome",
        "labels",
        "gold",
        "oracle",
        "fail_to_pass",
        "pass_to_pass",
        "patch",
        "verdict",
    }
)


def _log1p(value) -> float:
    return math.log1p(float(value or 0))


def scalar_features(summary: dict) -> dict:
    """Named scalar features from one observable_summary block."""
    return {
        "log1p_tool_call_count": _log1p(summary.get("tool_call_count")),
        "retry_count_max": float(summary.get("retry_count_max") or 0),
        "retry_count_mean": float(summary.get("retry_count_mean") or 0.0),
        "steps_retry_ge2": float(summary.get("steps_retry_ge2") or 0),
        "strategy_switches_final": float(summary.get("strategy_switches_final") or 0),
        "error_density": float(summary.get("error_density") or 0.0),
        "log1p_error_observation_count": _log1p(summary.get("error_observation_count")),
        "log1p_observation_count": _log1p(summary.get("observation_count")),
        "log1p_assistant_len_mean": _log1p(summary.get("assistant_text_length_mean")),
        "log1p_assistant_len_max": _log1p(summary.get("assistant_text_length_max")),
        "log1p_observation_len_mean": _log1p(summary.get("observation_length_mean")),
        "log1p_observation_len_max": _log1p(summary.get("observation_length_max")),
    }


def freeze_tool_vocab(summaries: list[dict], n: int = N_FROZEN_TOOLS) -> list[str]:
    """Top-n tools by total count, ties broken by name. Deterministic."""
    totals: dict[str, int] = {}
    for summary in summaries:
        for tool, count in (summary.get("tool_counts") or {}).items():
            totals[str(tool)] = totals.get(str(tool), 0) + int(count)
    ordered = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    return [tool for tool, _ in ordered[:n]]


def feature_names(tool_vocab: list[str]) -> list[str]:
    """Fixed, deterministic feature-name order."""
    return list(SCALAR_FEATURE_NAMES) + [
        f"{TOOL_COUNT_PREFIX}{tool}" for tool in tool_vocab
    ]


def feature_row(summary: dict, tool_vocab: list[str]) -> list[float]:
    """One ordered float row for a summary against a frozen tool vocabulary."""
    scalars = scalar_features(summary)
    row = [scalars[name] for name in SCALAR_FEATURE_NAMES]
    counts = summary.get("tool_counts") or {}
    row.extend(float(counts.get(tool, 0)) for tool in tool_vocab)
    return row


def _walk_keys(value) -> list[str]:
    if isinstance(value, dict):
        keys = [str(k) for k in value]
        for child in value.values():
            keys.extend(_walk_keys(child))
        return keys
    if isinstance(value, list):
        keys: list[str] = []
        for child in value:
            keys.extend(_walk_keys(child))
        return keys
    return []


def assert_no_leakage(example: dict) -> None:
    """Raise if any forbidden target/oracle key appears under input."""
    keys = {key.lower() for key in _walk_keys(example.get("input") or {})}
    forbidden = sorted(FORBIDDEN_INPUT_KEYS.intersection(keys))
    if forbidden:
        raise ValueError(f"example input has forbidden leakage keys: {forbidden}")


__all__ = [
    "CORPUS_FEATURE_VERSION",
    "N_FROZEN_TOOLS",
    "SCALAR_FEATURE_NAMES",
    "TOOL_COUNT_PREFIX",
    "FORBIDDEN_INPUT_KEYS",
    "scalar_features",
    "freeze_tool_vocab",
    "feature_names",
    "feature_row",
    "assert_no_leakage",
]

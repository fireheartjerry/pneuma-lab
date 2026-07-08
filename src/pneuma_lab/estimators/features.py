"""Leakage-masked, observable-only feature extraction for month-1 estimators.

Structural leakage masking (doc 08 §1.2): the extractor deep-copies the trace
and DELETES ``outcome``, ``oracle``, ``reference_supervision``, and
``labels.resolved`` BEFORE any feature is computed. A unit test perturbs those
fields and asserts byte-identical feature vectors.

Every feature is engineered and named, grounded only in ``agent_trace`` frames
and the ``trajectory`` block: tool names, digests, lengths, retry counts,
strategy switches, and the lexical error marker. No raw text, no objective-text
embeddings (no encoder dependency in month 1 — recorded as an omission in the
training report). Deterministic: no wall-clock, no randomness.
"""

from __future__ import annotations

import copy
import math

FEATURE_EXTRACTOR_VERSION = "pneuma-estimators-features/0.1.0"

# Fields structurally deleted before featurization (label-bearing / oracle).
SCRUBBED_TOP_LEVEL_FIELDS = ("outcome", "oracle", "reference_supervision")

# Prefix protocol: fraction of num_agent_steps, exact rational arithmetic.
PREFIX_FRACTIONS = (
    ("prefix_25", 1, 4),
    ("prefix_50", 1, 2),
    ("full", 1, 1),
)
PREFIX_FRACTION_MAP = {name: (num, den) for name, num, den in PREFIX_FRACTIONS}

N_FROZEN_TOOLS = 6
LAST_K_WINDOW = 3

# Features that grow monotonically with prefix length. The length-confound
# ablation model ("no-length" variant) excludes ALL of these — step counts,
# the full-trace step-count feature, total tool calls, and per-tool raw counts
# — so nothing absolute-count-shaped survives into the ablation.
LENGTH_FEATURE_NAMES = frozenset(
    {"n_steps_prefix", "log1p_num_agent_steps", "n_tool_calls_total"}
)
TOOL_COUNT_PREFIX = "tool_count__"

_BASE_FEATURE_NAMES = (
    "tool_bigram_diversity",
    "max_retry",
    "mean_retry",
    "n_steps_retry_ge2",
    "strategy_switches_final",
    "switches_per_step",
    "error_density",
    "last3_error_density",
    "mean_obs_len_log1p",
    "max_obs_len_log1p",
    "mean_assistant_len_log1p",
    "frac_steps_no_tool",
)


def readLabel(trace: dict) -> dict:
    """Label + QC flags, read from the RAW trace before any scrubbing.

    This is the only sanctioned reader of outcome/label fields; the feature
    path never sees them. ``error_eval``/``test_timeout`` are label-QC flags
    only (doc 08 §1.2) — never features.
    """
    labels = trace.get("labels") or {}
    report = (trace.get("outcome") or {}).get("report") or {}
    return {
        "resolved": labels.get("resolved"),
        "repo": labels.get("repo") or "",
        "error_eval": bool(report.get("error_eval")),
        "test_timeout": bool(report.get("test_timeout")),
    }


def scrubTrace(trace: dict) -> dict:
    """Deep-copy the trace and delete every outcome/oracle/label field."""
    clone = copy.deepcopy(trace)
    for field in SCRUBBED_TOP_LEVEL_FIELDS:
        clone.pop(field, None)
    labels = clone.get("labels")
    if isinstance(labels, dict):
        labels.pop("resolved", None)
    return clone


def prefixLength(num_steps: int, numerator: int, denominator: int) -> int:
    """ceil(num_steps * numerator / denominator), floored at 1. Exact ints."""
    return max(1, -(-num_steps * numerator // denominator))


def agentFrames(trace: dict) -> list[dict]:
    """agent_trace frames sorted by step_index (deterministic order)."""
    frames = [
        f
        for f in (trace.get("frames") or [])
        if isinstance(f, dict) and f.get("frame_kind") == "agent_trace"
    ]
    frames.sort(key=lambda f: int(f.get("step_index") or 0))
    return frames


def featureNames(
    tool_vocab: tuple[str, ...] | list[str],
    fraction_name: str,
    no_length: bool = False,
) -> list[str]:
    """Fixed, deterministic feature-name order for one model variant."""
    names: list[str] = []
    if not no_length:
        names.append("n_steps_prefix")
        if fraction_name == "full":
            names.append("log1p_num_agent_steps")
        for tool in tool_vocab:
            names.append(f"{TOOL_COUNT_PREFIX}{tool}")
    names.extend(_BASE_FEATURE_NAMES)
    if not no_length:
        names.append("n_tool_calls_total")
    return names


def prefixFeatureStats(trace: dict, fraction_name: str) -> tuple[dict, dict]:
    """(base_features, prefix_tool_counter) for one prefix fraction.

    Scrubs FIRST (structural leakage mask), then computes everything from the
    agent_trace frame prefix. ``base_features`` holds every named feature
    except the per-tool counts; the counter carries per-tool call counts in
    the prefix so callers can freeze/apply a tool vocabulary separately.
    """
    if fraction_name not in PREFIX_FRACTION_MAP:
        raise ValueError(f"unknown prefix fraction: {fraction_name!r}")
    clone = scrubTrace(trace)
    frames = agentFrames(clone)
    if not frames:
        raise ValueError("trace has no agent_trace frames")
    num_steps = len(frames)
    numerator, denominator = PREFIX_FRACTION_MAP[fraction_name]
    k = prefixLength(num_steps, numerator, denominator)
    prefix = frames[:k]

    tool_counter: dict[str, int] = {}
    flat_tools: list[str] = []
    n_tool_calls = 0
    n_no_call_steps = 0
    retries: list[int] = []
    obs_total = 0
    obs_errors = 0
    obs_len_logs: list[float] = []
    assistant_len_logs: list[float] = []
    for frame in prefix:
        calls = frame.get("tool_calls") or []
        if not calls:
            n_no_call_steps += 1
        for call in calls:
            n_tool_calls += 1
            tool = call.get("tool") or "unknown"
            flat_tools.append(tool)
            tool_counter[tool] = tool_counter.get(tool, 0) + 1
        retries.append(int(frame.get("retry_count") or 0))
        for obs in frame.get("observations") or []:
            obs_total += 1
            if obs.get("error_marker"):
                obs_errors += 1
            obs_len_logs.append(math.log1p(float(obs.get("content_length") or 0)))
        assistant_len_logs.append(
            math.log1p(float(frame.get("assistant_text_length") or 0))
        )

    last3_total = 0
    last3_errors = 0
    for frame in prefix[-LAST_K_WINDOW:]:
        for obs in frame.get("observations") or []:
            last3_total += 1
            if obs.get("error_marker"):
                last3_errors += 1

    unique_bigrams = set(zip(flat_tools, flat_tools[1:]))
    final_switches = int(prefix[-1].get("strategy_switches") or 0)

    base = {
        "n_steps_prefix": float(k),
        "tool_bigram_diversity": len(unique_bigrams) / k,
        "max_retry": float(max(retries)),
        "mean_retry": sum(retries) / k,
        "n_steps_retry_ge2": float(sum(1 for r in retries if r >= 2)),
        "strategy_switches_final": float(final_switches),
        "switches_per_step": final_switches / k,
        "error_density": (obs_errors / obs_total) if obs_total else 0.0,
        "last3_error_density": (last3_errors / last3_total) if last3_total else 0.0,
        "mean_obs_len_log1p": (
            math.fsum(obs_len_logs) / len(obs_len_logs) if obs_len_logs else 0.0
        ),
        "max_obs_len_log1p": max(obs_len_logs) if obs_len_logs else 0.0,
        "mean_assistant_len_log1p": math.fsum(assistant_len_logs) / k,
        "frac_steps_no_tool": n_no_call_steps / k,
        "n_tool_calls_total": float(n_tool_calls),
    }
    if fraction_name == "full":
        base["log1p_num_agent_steps"] = math.log1p(float(num_steps))
    return base, tool_counter


def assembleFeatures(
    base: dict,
    tool_counter: dict,
    tool_vocab: tuple[str, ...] | list[str],
    fraction_name: str,
    no_length: bool = False,
) -> dict:
    """Ordered name->value feature dict for one model variant."""
    out: dict[str, float] = {}
    for name in featureNames(tool_vocab, fraction_name, no_length=no_length):
        if name.startswith(TOOL_COUNT_PREFIX):
            out[name] = float(tool_counter.get(name[len(TOOL_COUNT_PREFIX) :], 0))
        else:
            out[name] = base[name]
    return out


def extractFeatures(
    trace: dict,
    fraction_name: str,
    tool_vocab: tuple[str, ...] | list[str],
    no_length: bool = False,
) -> dict:
    """Full named feature vector for one trace at one prefix fraction.

    Scrub-invariant by construction: outcome/oracle/reference_supervision/
    labels.resolved are deleted before any feature is computed.
    """
    base, tool_counter = prefixFeatureStats(trace, fraction_name)
    return assembleFeatures(
        base, tool_counter, tool_vocab, fraction_name, no_length=no_length
    )


__all__ = [
    "FEATURE_EXTRACTOR_VERSION",
    "SCRUBBED_TOP_LEVEL_FIELDS",
    "PREFIX_FRACTIONS",
    "PREFIX_FRACTION_MAP",
    "N_FROZEN_TOOLS",
    "LAST_K_WINDOW",
    "LENGTH_FEATURE_NAMES",
    "TOOL_COUNT_PREFIX",
    "readLabel",
    "scrubTrace",
    "prefixLength",
    "agentFrames",
    "featureNames",
    "prefixFeatureStats",
    "assembleFeatures",
    "extractFeatures",
]

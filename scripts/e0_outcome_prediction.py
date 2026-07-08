"""E-0: do replayed ReferencePsyche signals predict real agent failure?

Pre-registration: docs/research/experiments/e0-preregistration.md (committed
before this script ran on the eval split). This script fits NOTHING: it
replays, extracts pre-registered signals, and tests pre-registered hypotheses.

Usage:
    python scripts/e0_outcome_prediction.py \
        --traces C:/pneuma-data/processed/swe-gym/openhands-sampled/pneuma_traces.jsonl \
        --out build/e0

Pure stdlib + pneuma_lab. Deterministic: every trace replayed twice and
byte-compared; any mismatch voids the run (exit 1).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pneuma_lab.adapters.envelope import canonical_json  # noqa: E402
from pneuma_lab.psyche import ReferencePsyche  # noqa: E402
from pneuma_lab.replay.bridge import BridgeError, expand_trace_to_timeline  # noqa: E402
from pneuma_lab.replay.harness import ReplayHarness  # noqa: E402

PREFIXES = (3, 5, 10)
PRIMARY_T = 10
ALPHA = 0.01
H1_MIN_DELTA = 0.02
H2_MIN_AUROC = 0.54
H3_MIN_STRAT = 0.52
MIN_EVAL_NEGATIVES = 60


# ---------- rank statistics (pure stdlib) ----------------------------------


def midranks(values: list[float]) -> list[float]:
    """Midranks (1-based, ties averaged)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
            j += 1
        rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = rank
        i = j + 1
    return ranks


def auroc(scores_pos: list[float], scores_neg: list[float]) -> float:
    """Mann-Whitney AUROC with tie midranks."""
    m, n = len(scores_pos), len(scores_neg)
    if m == 0 or n == 0:
        return float("nan")
    ranks = midranks(scores_pos + scores_neg)
    r_pos = sum(ranks[:m])
    return (r_pos - m * (m + 1) / 2.0) / (m * n)


def delong_paired(pos_a, neg_a, pos_b, neg_b) -> dict:
    """Fast DeLong: paired AUROC difference (A - B), variance, one-sided p."""
    m, n = len(pos_a), len(neg_a)

    def components(pos, neg):
        tz = midranks(pos + neg)
        tx = midranks(pos)
        ty = midranks(neg)
        auc = (sum(tz[:m]) - m * (m + 1) / 2.0) / (m * n)
        v01 = [(tz[i] - tx[i]) / n for i in range(m)]
        v10 = [1.0 - (tz[m + j] - ty[j]) / m for j in range(n)]
        return auc, v01, v10

    auc_a, v01_a, v10_a = components(pos_a, neg_a)
    auc_b, v01_b, v10_b = components(pos_b, neg_b)

    def cov(x, y):
        k = len(x)
        if k < 2:
            return 0.0
        mx, my = sum(x) / k, sum(y) / k
        return sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / (k - 1)

    var = (cov(v01_a, v01_a) + cov(v01_b, v01_b) - 2 * cov(v01_a, v01_b)) / m + (
        cov(v10_a, v10_a) + cov(v10_b, v10_b) - 2 * cov(v10_a, v10_b)
    ) / n
    delta = auc_a - auc_b
    if var <= 0:
        return {
            "auc_a": auc_a,
            "auc_b": auc_b,
            "delta": delta,
            "z": None,
            "p_one_sided": None,
        }
    z = delta / math.sqrt(var)
    p = 1.0 - 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return {"auc_a": auc_a, "auc_b": auc_b, "delta": delta, "z": z, "p_one_sided": p}


def stratified_auroc(scores: list[float], strata: list[float], ys: list[int]) -> dict:
    """AUROC of `scores` within each stratum value, weighted by stratum size."""
    groups: dict[float, list[int]] = {}
    for i, s in enumerate(strata):
        groups.setdefault(s, []).append(i)
    total_w, acc, used = 0, 0.0, 0
    for idxs in groups.values():
        pos = [scores[i] for i in idxs if ys[i] == 1]
        neg = [scores[i] for i in idxs if ys[i] == 0]
        if pos and neg:
            acc += auroc(pos, neg) * len(idxs)
            total_w += len(idxs)
            used += 1
    return {
        "value": (acc / total_w) if total_w else float("nan"),
        "strata_used": used,
        "n_in_used_strata": total_w,
    }


# ---------- replay + signal extraction --------------------------------------


def extract_signals(trace: dict) -> dict | None:
    """Replay twice (determinism gate), extract pre-registered prefix signals."""
    try:
        timeline = expand_trace_to_timeline(trace)
    except BridgeError as exc:
        return {"skip": f"bridge: {exc}"}

    def replay():
        result = ReplayHarness(ReferencePsyche(), validate=False).run(timeline)
        blob = canonical_json(result.output_frames)
        return result, hashlib.sha256(blob.encode("utf-8")).hexdigest()

    result, h1 = replay()
    _, h2 = replay()
    if h1 != h2:
        return {"nondeterministic": trace.get("trace_id")}

    # tick 0 is the preamble; agent ticks are 1..N
    agent_outputs = result.tick_outputs[1:]
    severities = [
        sum(float(s.get("severity", 0.0) or 0.0) for s in o.instinct_signals)
        for o in agent_outputs
    ]
    vps = [
        float(o.control_pressure["pressures"].get("verification", 0.0) or 0.0)
        for o in agent_outputs
    ]
    agent_frames = sorted(
        (f for f in trace["frames"] if f.get("frame_kind") == "agent_trace"),
        key=lambda f: f.get("step_index", 0),
    )
    retries = [int(f.get("retry_count", 0) or 0) for f in agent_frames]

    out = {"n_steps": len(agent_outputs)}
    for t in PREFIXES:
        t_used = min(t, len(agent_outputs))
        out[f"s_instinct_{t}"] = sum(severities[:t_used]) / t_used
        out[f"s_vp_{t}"] = sum(vps[:t_used])
        out[f"b1_{t}"] = float(max(retries[:t_used]) if retries[:t_used] else 0)
    return out


def split_of(repo: str) -> str:
    if not repo:
        return "dev"
    h = int(hashlib.sha256(repo.encode("utf-8")).hexdigest(), 16)
    return "eval" if h % 10 < 3 else "dev"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--traces",
        default="C:/pneuma-data/processed/swe-gym/openhands-sampled/pneuma_traces.jsonl",
    )
    ap.add_argument("--out", default=os.path.join("build", "e0"))
    ap.add_argument("--limit", type=int, default=0, help="debug: cap trace count")
    args = ap.parse_args()

    rows = []
    excluded = {"error_eval_or_timeout": 0, "bridge_skip": 0}
    nondet = []
    with open(args.traces, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if args.limit and i >= args.limit:
                break
            trace = json.loads(line)
            report = (trace.get("outcome") or {}).get("report") or {}
            if report.get("error_eval") or report.get("test_timeout"):
                excluded["error_eval_or_timeout"] += 1
                continue
            sig = extract_signals(trace)
            if sig is None or "skip" in sig:
                excluded["bridge_skip"] += 1
                continue
            if "nondeterministic" in sig:
                nondet.append(sig["nondeterministic"])
                continue
            sig["y"] = 0 if trace["labels"]["resolved"] else 1  # y=1 <=> failure
            sig["repo"] = trace["labels"].get("repo", "")
            sig["split"] = split_of(sig["repo"])
            sig["trace_id"] = trace["trace_id"]
            rows.append(sig)
            if (i + 1) % 500 == 0:
                print(f"  replayed {i + 1} traces...", flush=True)

    if nondet:
        print(f"DETERMINISM VIOLATION in {len(nondet)} traces: {nondet[:5]}")
        return 1

    ev = [r for r in rows if r["split"] == "eval"]
    dv = [r for r in rows if r["split"] == "dev"]
    ev_pos = [r for r in ev if r["y"] == 1]
    ev_neg = [r for r in ev if r["y"] == 0]

    results: dict = {
        "preregistration": "docs/research/experiments/e0-preregistration.md",
        "counts": {
            "replayed": len(rows),
            "excluded": excluded,
            "dev": len(dv),
            "eval": len(ev),
            "eval_failures_y1": len(ev_pos),
            "eval_successes_y0": len(ev_neg),
            "eval_repos": len({r["repo"] for r in ev}),
        },
        "determinism": "all traces byte-identical across two replays",
        "prefix_table": {},
    }

    underpowered = len(ev_neg) < MIN_EVAL_NEGATIVES
    for t in PREFIXES:
        entry = {}
        for sig in (f"s_vp_{t}", f"s_instinct_{t}", f"b1_{t}"):
            entry[f"auroc_{sig}"] = auroc(
                [r[sig] for r in ev_pos], [r[sig] for r in ev_neg]
            )
        results["prefix_table"][str(t)] = entry

    t = PRIMARY_T
    if not ev_pos or not ev_neg:
        h1 = {
            "auc_a": None,
            "auc_b": None,
            "delta": None,
            "z": None,
            "p_one_sided": None,
        }
        h2_auroc = float("nan")
        h3 = {"value": float("nan"), "strata_used": 0, "n_in_used_strata": 0}
        underpowered = True
    else:
        h1 = delong_paired(
            [r[f"s_vp_{t}"] for r in ev_pos],
            [r[f"s_vp_{t}"] for r in ev_neg],
            [r[f"b1_{t}"] for r in ev_pos],
            [r[f"b1_{t}"] for r in ev_neg],
        )
        h2_auroc = results["prefix_table"][str(t)][f"auroc_s_instinct_{t}"]
        h3 = stratified_auroc(
            [r[f"s_vp_{t}"] for r in ev],
            [r[f"b1_{t}"] for r in ev],
            [r["y"] for r in ev],
        )

    h1_pass = (
        h1["delta"] is not None
        and h1["delta"] >= H1_MIN_DELTA
        and h1["p_one_sided"] is not None
        and h1["p_one_sided"] < ALPHA
    )
    h2_pass = not math.isnan(h2_auroc) and h2_auroc >= H2_MIN_AUROC
    h3_pass = not math.isnan(h3["value"]) and h3["value"] > H3_MIN_STRAT

    results["hypotheses"] = {
        "H1": {
            **h1,
            "criterion": f"delta>={H1_MIN_DELTA} and p<{ALPHA}",
            "pass": h1_pass,
        },
        "H2": {
            "auroc_s_instinct_10": h2_auroc,
            "criterion": f">={H2_MIN_AUROC}",
            "pass": h2_pass,
        },
        "H3": {**h3, "criterion": f">{H3_MIN_STRAT}", "pass": h3_pass},
        "underpowered": underpowered,
        "verdict": (
            "underpowered — no claim"
            if underpowered
            else ("PASS" if (h1_pass and h2_pass and h3_pass) else "FAIL")
        ),
    }

    def sanitize(obj):
        """NaN -> None so the report stays strict JSON."""
        if isinstance(obj, float) and math.isnan(obj):
            return None
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(v) for v in obj]
        return obj

    results = sanitize(results)

    os.makedirs(args.out, exist_ok=True)
    with open(
        os.path.join(args.out, "report.json"), "w", encoding="utf-8", newline="\n"
    ) as fh:
        fh.write(canonical_json(results) + "\n")
    with open(
        os.path.join(args.out, "signals.jsonl"), "w", encoding="utf-8", newline="\n"
    ) as fh:
        for r in sorted(rows, key=lambda x: x["trace_id"]):
            fh.write(canonical_json(r) + "\n")

    print(json.dumps(results["hypotheses"], indent=1))
    print(f"verdict: {results['hypotheses']['verdict']}")
    print(f"report: {os.path.join(args.out, 'report.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

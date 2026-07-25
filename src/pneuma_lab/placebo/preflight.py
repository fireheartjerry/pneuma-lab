"""Model-selection calibration preflight.

Implements the capability band in `25-placebo-selfreport-design.md` section 10. The
model is fixed BEFORE any real or placebo reflection is ever generated, so that the
choice cannot be tuned on the result.

Per candidate on a disjoint calibration slice, three things run and only three:

    1. the initial attempt,
    2. a plain retry after failure,
    3. a retry with an oracle bug hint derived from the verifier.

Real and placebo reflections are never generated here.

Eligibility requires a projected failure yield above ``n_min``, paired oracle
responsiveness of at least 0.15 with a positive lower bound, plain retry not
exhausting the headroom, and format validity above threshold. Among eligible
candidates the LARGEST is selected, not the one with the largest uplift: that yields a
band strong enough to use diagnostic information and weak enough to leave the required
failure roster, chosen without observing any treatment contrast.
"""

from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

# Frozen ladder, same family so capability is the only varying factor.
MODEL_LADDER: tuple[str, ...] = (
    "qwen2.5-coder:1.5b",
    "qwen2.5-coder:7b",
)

ORACLE_UPLIFT_MIN = 0.15
GREEDY_PASS_BAND = (0.25, 0.75)
DECODE_SEED = 42
MAX_TOKENS = 512


@dataclass(frozen=True)
class CandidateStats:
    """What the preflight measures. No treatment contrast appears here."""

    model: str
    n_calibration: int
    initial_failures: int
    initial_pass_rate: float
    plain_retry_successes: int
    plain_retry_rate: float
    oracle_successes: int
    oracle_rate: float
    oracle_uplift: float
    oracle_uplift_lower_90: float
    parse_failures: int
    mean_latency_s: float
    tokens_per_second: float
    eligible: bool
    ineligibility_reasons: list[str] = field(default_factory=list)


def _generate(
    model: str, prompt: str, seed: int = DECODE_SEED
) -> tuple[str, float, int]:
    """One Ollama call at the frozen decoding configuration."""
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "seed": seed, "num_predict": MAX_TOKENS},
        }
    ).encode()
    request = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}
    )
    started = time.time()
    payload = json.loads(urllib.request.urlopen(request, timeout=300).read())
    return payload["response"], time.time() - started, payload.get("eval_count", 0)


def extractCode(response: str) -> str:
    """Pull Python out of a model response. Fenced, bare, or prose-prefixed."""
    if "```" in response:
        chunks = response.split("```")
        for chunk in chunks[1:]:
            body = chunk[len("python") :] if chunk.startswith("python") else chunk
            if "def " in body:
                return body.strip()
    return response.strip()


def wilsonLower(successes: int, trials: int, z: float = 1.2816) -> float:
    """One-sided lower bound on a proportion. z=1.2816 is the 90% bound.

    Returns exactly 0.0 with no successes. The algebraic expression evaluates to
    floating-point dust (order 1e-17) rather than zero there, and the eligibility
    gate tests ``lower <= 0``, so an unclamped value would let a candidate with zero
    oracle successes pass a check it must fail.
    """
    if trials == 0 or successes <= 0:
        return 0.0
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials))
    lower = (centre - margin) / denominator
    return lower if lower > 1e-12 else 0.0


def evaluateCandidate(
    model: str,
    problems: dict,
    grade,
    n_min: int,
    main_roster_size: int,
) -> CandidateStats:
    """Measure one candidate. ``grade`` returns (all_pass, stderr_excerpt)."""
    latencies: list[float] = []
    token_counts: list[int] = []
    failures: list[str] = []
    parse_failures = 0

    for pid, item in problems.items():
        response, latency, tokens = _generate(model, item["prompt"])
        latencies.append(latency)
        token_counts.append(tokens)
        code = extractCode(response)
        if "def " not in code:
            parse_failures += 1
        passed, _ = grade(pid, code)
        if not passed:
            failures.append(pid)

    n_cal = len(problems)
    initial_pass_rate = 1.0 - len(failures) / max(n_cal, 1)

    plain_ok = 0
    oracle_ok = 0
    for pid in failures:
        item = problems[pid]
        retry_prompt = (
            f"{item['prompt']}\n\nYour previous attempt failed the tests. Try again.\n"
        )
        code = extractCode(_generate(model, retry_prompt)[0])
        if grade(pid, code)[0]:
            plain_ok += 1

        _, stderr = grade(pid, extractCode(_generate(model, item["prompt"])[0]))
        oracle_prompt = (
            f"{item['prompt']}\n\n"
            "Your previous attempt failed with this verifier output:\n"
            f"{stderr[:600]}\n\nFix it.\n"
        )
        if grade(pid, extractCode(_generate(model, oracle_prompt)[0]))[0]:
            oracle_ok += 1

    n_fail = max(len(failures), 1)
    plain_rate = plain_ok / n_fail
    oracle_rate = oracle_ok / n_fail
    uplift = oracle_rate - plain_rate
    uplift_lower = wilsonLower(max(oracle_ok - plain_ok, 0), n_fail)

    projected = main_roster_size * (len(failures) / max(n_cal, 1)) * 0.9
    reasons: list[str] = []
    if projected < n_min:
        reasons.append(f"projected yield {projected:.0f} below n_min {n_min}")
    if uplift < ORACLE_UPLIFT_MIN:
        reasons.append(f"oracle uplift {uplift:.3f} below {ORACLE_UPLIFT_MIN}")
    if uplift_lower <= 0:
        reasons.append("oracle uplift lower bound not positive")
    if plain_rate > 0.8:
        reasons.append(f"plain retry exhausts headroom at {plain_rate:.3f}")
    if parse_failures / max(n_cal, 1) > 0.1:
        reasons.append(f"parse failure rate {parse_failures / n_cal:.3f} above 0.1")

    total_time = sum(latencies) or 1e-9
    return CandidateStats(
        model=model,
        n_calibration=n_cal,
        initial_failures=len(failures),
        initial_pass_rate=round(initial_pass_rate, 4),
        plain_retry_successes=plain_ok,
        plain_retry_rate=round(plain_rate, 4),
        oracle_successes=oracle_ok,
        oracle_rate=round(oracle_rate, 4),
        oracle_uplift=round(uplift, 4),
        oracle_uplift_lower_90=round(uplift_lower, 4),
        parse_failures=parse_failures,
        mean_latency_s=round(sum(latencies) / max(len(latencies), 1), 2),
        tokens_per_second=round(sum(token_counts) / total_time, 1),
        eligible=not reasons,
        ineligibility_reasons=reasons,
    )


def selectModel(stats: list[CandidateStats]) -> tuple[str | None, str]:
    """Largest ELIGIBLE model, not the largest uplift. Ladder order is capability order."""
    eligible = [s for s in stats if s.eligible]
    if not eligible:
        return (
            None,
            "no candidate is eligible; expand the roster or declare a feasibility no-go",
        )
    ordered = sorted(eligible, key=lambda s: MODEL_LADDER.index(s.model))
    chosen = ordered[-1]
    return chosen.model, (
        f"largest eligible on the frozen ladder; "
        f"pass rate {chosen.initial_pass_rate}, oracle uplift {chosen.oracle_uplift}"
    )


def writeReceipt(
    stats: list[CandidateStats], selected: tuple[str | None, str], path
) -> None:
    """Deterministic preflight receipt. No treatment contrast is recorded."""
    payload = {
        "schema_version": "pneuma-placebo-preflight/1.0.0",
        "ladder": list(MODEL_LADDER),
        "oracle_uplift_min": ORACLE_UPLIFT_MIN,
        "greedy_pass_band": list(GREEDY_PASS_BAND),
        "decode_seed": DECODE_SEED,
        "candidates": [asdict(s) for s in stats],
        "selected_model": selected[0],
        "selection_rationale": selected[1],
        "note": (
            "Real and placebo reflections were not generated during selection. "
            "Only the initial attempt, a plain retry, and an oracle-hint retry ran."
        ),
    }
    path.write_text(
        json.dumps(payload, indent=4, sort_keys=True) + "\n", encoding="utf-8"
    )

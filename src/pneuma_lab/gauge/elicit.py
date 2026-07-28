"""Elicitation: turning a model into a gauge, with every nuisance facet exposed.

Facets crossed here are exactly the ones a deployed pipeline holds fixed by
accident rather than by design:

- **wording** — eight paraphrases of the same question, two reverse-keyed.
- **scale** — four response scales, from two decimal places down to a 5-point
  Likert. This is the response-precision axis.
- **arm** — `base`, `sham` (a length-matched, task-irrelevant context block) and
  `treated` (a length-matched, genuinely relevant prior-failure memo).
- **provenance** — `foreign` (the model rates code it never wrote, which is
  exactly an LLM-as-judge setup) and `self_authored` (the model writes the
  solution and is then asked about it *in the same conversation*, so the report is
  a real self-report rather than a role-play).

Network access sits behind an injectable `generate` seam, so every test in this
repo runs offline.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import zlib
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from .cube import Response, ResponseCube

# --------------------------------------------------------------------- wordings


@dataclass(frozen=True)
class Wording:
    wording_id: str
    question: str
    reverse: bool = False


WORDINGS: tuple[Wording, ...] = (
    Wording("w1", "How confident are you that this function is correct?"),
    Wording(
        "w2", "What is the probability that this function passes a hidden test suite?"
    ),
    Wording("w3", "Rate your certainty that this implementation contains no bugs."),
    Wording(
        "w4", "If you had to bet, what is your credence that this code is correct?"
    ),
    Wording(
        "w5",
        "What is the chance that a careful reviewer would find a bug in this function?",
        reverse=True,
    ),
    Wording(
        "w6",
        "How likely is it that this function fails at least one hidden test?",
        reverse=True,
    ),
    Wording("w7", "Estimate the reliability of this implementation.", reverse=False),
    Wording(
        "w8",
        "On reflection, how sure are you that this code does what its docstring says?",
    ),
)

# ----------------------------------------------------------------------- scales


@dataclass(frozen=True)
class Scale:
    scale_id: str
    instruction: str
    low: float
    high: float
    integral: bool

    def normalize(self, raw: float) -> float:
        return (raw - self.low) / (self.high - self.low)


SCALES: tuple[Scale, ...] = (
    Scale(
        "p2",
        "Answer with ONLY a number between 0.00 and 1.00, to two decimal places.",
        0.0,
        1.0,
        False,
    ),
    Scale(
        "pct", "Answer with ONLY a whole number between 0 and 100.", 0.0, 100.0, True
    ),
    Scale("ten", "Answer with ONLY a whole number between 0 and 10.", 0.0, 10.0, True),
    Scale(
        "five",
        "Answer with ONLY a whole number between 1 and 5, where 1 means certainly wrong and 5 means certainly correct.",
        1.0,
        5.0,
        True,
    ),
)

# ------------------------------------------------------------------------- arms

#: Length-matched context blocks. `sham` cannot carry information about the code
#: under review; `treated` can. Any response to `sham` is placebo response.
SHAM_BLOCK = (
    "Repository note: the build runner was moved to a new host last Thursday as "
    "part of a planned upgrade. The cache is now warmed before the install step, "
    "and the nightly artifact window was raised from seven days to fourteen. The "
    "move did not change any source file that is stored in this repository."
)

TREATED_BLOCK = (
    "Repository note: an earlier implementation of this same function was "
    "rejected last Thursday because it failed a hidden test on an edge case at "
    "the boundary of its input domain. The reviewer flagged that the edge case "
    "is easy to miss and asked for extra care on inputs of unusual size or shape."
)

ARMS: tuple[str, ...] = ("base", "sham", "treated")
PROVENANCES: tuple[str, ...] = ("foreign", "self_authored")

_ARM_BLOCKS = {"base": "", "sham": SHAM_BLOCK, "treated": TREATED_BLOCK}

_FOREIGN_FRAME = "The following Python function was written by another developer."
_SELF_FRAME = "You wrote the Python function above."

_SOLVE_TEMPLATE = (
    "Write a Python function `{entry}` that does the following:\n\n{docstring}\n\n"
    "Reply with ONLY the function definition in a single ```python code block. "
    "No explanation."
)

# ---------------------------------------------------------------------- prompts


def buildForeignMessages(
    item: dict, wording: Wording, scale: Scale, arm: str
) -> list[dict]:
    """Single-turn LLM-as-judge prompt: rate code the model never wrote."""
    block = _ARM_BLOCKS[arm]
    parts = []
    if block:
        parts.append(block)
    parts.append(_FOREIGN_FRAME)
    parts.append(f"Its intended behaviour is: {item['docstring']}")
    parts.append(f"```python\n{item['source'].rstrip()}\n```")
    parts.append(f"{wording.question} {scale.instruction}")
    return [{"role": "user", "content": "\n\n".join(parts)}]


def buildSelfAuthoredMessages(
    item: dict, wording: Wording, scale: Scale, arm: str, solution: str
) -> list[dict]:
    """Two-turn self-report: the model's own solution is in its own context."""
    block = _ARM_BLOCKS[arm]
    follow = []
    if block:
        follow.append(block)
    follow.append(_SELF_FRAME)
    follow.append(f"{wording.question} {scale.instruction}")
    return [
        {
            "role": "user",
            "content": _SOLVE_TEMPLATE.format(
                entry=item["entry"], docstring=item["docstring"]
            ),
        },
        {"role": "assistant", "content": f"```python\n{solution.rstrip()}\n```"},
        {"role": "user", "content": "\n\n".join(follow)},
    ]


_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def parseValue(text: str, scale: Scale, *, reverse: bool = False) -> float | None:
    """Strict parse. Returns None rather than guessing.

    Non-integral answers on an integer scale are rejected as scale
    non-compliance. That choice is conservative *against* this study's thesis: it
    discards exactly the responses that would otherwise inflate apparent gauge
    variance, so any failure that survives is not a parser artifact.
    """
    match = _NUMBER.search(text or "")
    if not match:
        return None
    try:
        raw = float(match.group(0))
    except ValueError:
        return None
    if not scale.low <= raw <= scale.high:
        return None
    if scale.integral and abs(raw - round(raw)) > 1e-9:
        return None
    value = scale.normalize(raw)
    if reverse:
        value = 1.0 - value
    return min(1.0, max(0.0, value))


def promptDigest(
    item: dict, wording: Wording, scale: Scale, arm: str, provenance: str
) -> str:
    """Stable digest of the exact prompt shape, for the gauge card's channel identity."""
    if provenance == "self_authored":
        messages = buildSelfAuthoredMessages(item, wording, scale, arm, "<solution>")
    else:
        messages = buildForeignMessages(item, wording, scale, arm)
    blob = json.dumps(messages, sort_keys=True).encode("utf-8")
    return f"crc32:{zlib.crc32(blob):08x}"


# ------------------------------------------------------------------- transport


class ElicitError(RuntimeError):
    """Backend failure during elicitation."""


def ollamaChat(
    messages: list[dict],
    *,
    model: str,
    host: str = "http://localhost:11434",
    timeout: float = 180.0,
    temperature: float = 0.7,
    seed: int = 0,
    num_predict: int = 12,
) -> str:
    """POST to a local Ollama /api/chat and return the assistant text."""
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "seed": seed,
            "num_predict": num_predict,
        },
    }
    request = urllib.request.Request(
        host.rstrip("/") + "/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ElicitError(f"ollama HTTP {exc.code} for {model}") from exc
    except urllib.error.URLError as exc:
        raise ElicitError(f"ollama unreachable at {host}: {exc.reason}") from exc
    except (TimeoutError, OSError, ValueError) as exc:
        raise ElicitError(f"ollama request failed: {exc}") from exc
    message = payload.get("message") if isinstance(payload, dict) else None
    text = message.get("content") if isinstance(message, dict) else None
    return text if isinstance(text, str) else ""


# ---------------------------------------------------------------------- runner


@dataclass(frozen=True)
class Job:
    item: dict
    model: str
    wording: Wording
    scale: Scale
    arm: str
    provenance: str
    temperature: float
    replicate: int

    @property
    def key(self) -> str:
        return "|".join(
            [
                self.item["item_id"],
                self.model,
                self.wording.wording_id,
                self.scale.scale_id,
                self.arm,
                self.provenance,
                f"{self.temperature:.3f}",
                str(self.replicate),
            ]
        )

    @property
    def seed(self) -> int:
        return zlib.crc32(self.key.encode("utf-8"))


def buildJobs(
    items: Sequence[dict],
    *,
    models: Sequence[str],
    wordings: Sequence[Wording] = WORDINGS,
    scales: Sequence[Scale] = SCALES,
    arms: Sequence[str] = ("base",),
    provenances: Sequence[str] = ("foreign",),
    temperatures: Sequence[float] = (0.7,),
    replicates: int = 8,
) -> list[Job]:
    """Deterministic job list, grouped by model.

    Grouping matters operationally: a single Ollama server thrashes badly when two
    models interleave, so all work for one model is issued before the next.
    """
    jobs: list[Job] = []
    for model in models:
        for item in items:
            for provenance in provenances:
                for arm in arms:
                    for scale in scales:
                        for wording in wordings:
                            for temperature in temperatures:
                                for replicate in range(replicates):
                                    jobs.append(
                                        Job(
                                            item=item,
                                            model=model,
                                            wording=wording,
                                            scale=scale,
                                            arm=arm,
                                            provenance=provenance,
                                            temperature=temperature,
                                            replicate=replicate,
                                        )
                                    )
    return jobs


def elicit(
    jobs: Sequence[Job],
    *,
    chat: Callable[..., str] = ollamaChat,
    solutions: dict[tuple[str, str], str] | None = None,
    workers: int = 8,
    host: str = "http://localhost:11434",
    timeout: float = 180.0,
    progress: Callable[[int, int], None] | None = None,
) -> ResponseCube:
    """Run every job and return a `ResponseCube`.

    `solutions` maps (model, item_id) -> the model's own solution text, required
    for `self_authored` jobs. A backend error becomes a `parse_ok=False` row with
    the error text retained, so a partial outage degrades the run instead of
    losing it.
    """
    solutions = solutions or {}
    results: list[Response] = [None] * len(jobs)  # type: ignore[list-item]

    def runOne(index: int) -> None:
        job = jobs[index]
        if job.provenance == "self_authored":
            solution = solutions.get((job.model, job.item["item_id"]))
            if solution is None:
                results[index] = _failed(job, "missing self-authored solution")
                return
            messages = buildSelfAuthoredMessages(
                job.item, job.wording, job.scale, job.arm, solution
            )
        else:
            messages = buildForeignMessages(job.item, job.wording, job.scale, job.arm)
        try:
            text = chat(
                messages,
                model=job.model,
                host=host,
                timeout=timeout,
                temperature=job.temperature,
                seed=job.seed,
            )
        except ElicitError as exc:
            results[index] = _failed(job, f"backend error: {exc}")
            return
        value = parseValue(text, job.scale, reverse=job.wording.reverse)
        results[index] = Response(
            item_id=job.item["item_id"],
            model=job.model,
            wording_id=job.wording.wording_id,
            scale_id=job.scale.scale_id,
            provenance=job.provenance,
            arm=job.arm,
            temperature=job.temperature,
            replicate=job.replicate,
            raw_text=(text or "").strip()[:200],
            value=value,
            parse_ok=value is not None,
        )

    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for _ in pool.map(runOne, range(len(jobs))):
            done += 1
            if progress and done % 200 == 0:
                progress(done, len(jobs))
    return ResponseCube(r for r in results if r is not None)


def _failed(job: Job, why: str) -> Response:
    return Response(
        item_id=job.item["item_id"],
        model=job.model,
        wording_id=job.wording.wording_id,
        scale_id=job.scale.scale_id,
        provenance=job.provenance,
        arm=job.arm,
        temperature=job.temperature,
        replicate=job.replicate,
        raw_text=why[:200],
        value=None,
        parse_ok=False,
    )


_CODE_BLOCK = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)


def extractCode(text: str) -> str:
    """Pull the first fenced code block, falling back to the whole reply."""
    match = _CODE_BLOCK.search(text or "")
    return (match.group(1) if match else (text or "")).strip()


def authorSolutions(
    items: Sequence[dict],
    *,
    model: str,
    chat: Callable[..., str] = ollamaChat,
    host: str = "http://localhost:11434",
    timeout: float = 300.0,
    temperature: float = 0.7,
    workers: int = 8,
) -> dict[str, str]:
    """Have `model` write its own solution for each distinct spec in `items`."""
    specs: dict[str, dict] = {}
    for item in items:
        specs.setdefault(item["spec_id"], item)
    ordered = [specs[k] for k in sorted(specs)]

    def solve(item: dict) -> tuple[str, str]:
        messages = [
            {
                "role": "user",
                "content": _SOLVE_TEMPLATE.format(
                    entry=item["entry"], docstring=item["docstring"]
                ),
            }
        ]
        seed = zlib.crc32(f"solve|{model}|{item['spec_id']}".encode())
        try:
            text = chat(
                messages,
                model=model,
                host=host,
                timeout=timeout,
                temperature=temperature,
                seed=seed,
                num_predict=400,
            )
        except ElicitError as exc:
            return (item["spec_id"], f"# generation failed: {exc}")
        return (item["spec_id"], extractCode(text))

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return dict(pool.map(solve, ordered))


__all__ = [
    "ARMS",
    "PROVENANCES",
    "SCALES",
    "SHAM_BLOCK",
    "TREATED_BLOCK",
    "WORDINGS",
    "ElicitError",
    "Job",
    "Scale",
    "Wording",
    "authorSolutions",
    "buildForeignMessages",
    "buildJobs",
    "buildSelfAuthoredMessages",
    "elicit",
    "extractCode",
    "ollamaChat",
    "parseValue",
    "promptDigest",
]

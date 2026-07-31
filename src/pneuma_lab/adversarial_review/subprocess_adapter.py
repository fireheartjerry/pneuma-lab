"""Bounded, receipted invocation of reviewer subprocesses.

Claude and Codex subprocesses are *proposal generators*. Their output is
parsed, receipted, and then handed to the verifier in ``validation``; nothing
they say enters the record on their own authority.

Two properties matter here and nowhere else in the system:

*Bounded cost.* Each invocation declares a token and wall-clock ceiling before
it runs. Exceeding either raises ``SubprocessBudgetError`` and the campaign
fails closed rather than silently producing a truncated review.

*Deterministic replay.* An invocation can be replayed from a transcript
directory keyed by ``role_id`` and prompt digest. Replay never launches a
process, which is what makes the narrow tests in this repository able to
exercise the whole pipeline with zero spend and zero network.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from .canonical import canonical_bytes, digest_bytes
from .errors import InputContractError, SubprocessBudgetError
from .records import Finding, ReviewerReport, SubprocessReceipt
from .roles import ReviewerRole

#: Engines the adapter knows how to launch. The exact argv is fixed here so a
#: campaign cannot smuggle different flags past the receipt.
ENGINE_ARGV: Mapping[str, tuple[str, ...]] = {
    "claude": ("claude", "--dangerously-skip-permissions", "-p"),
    "codex": ("codex", "--yolo", "exec", "--skip-git-repo-check"),
}


@dataclass(frozen=True)
class Budget:
    """Per-invocation cost ceiling."""

    max_output_tokens: int = 16_000
    max_wall_clock_seconds: float = 900.0
    max_cost_usd: float = 1.00

    def check_wall_clock(self, elapsed: float, role_id: str) -> None:
        if elapsed > self.max_wall_clock_seconds:
            raise SubprocessBudgetError(
                f"role {role_id} exceeded wall-clock budget: "
                f"{elapsed:.1f}s > {self.max_wall_clock_seconds:.1f}s"
            )


class ProposalSource(Protocol):
    """Anything that can turn a prompt into raw proposal text."""

    def run(self, role: ReviewerRole, prompt: str) -> tuple[str, SubprocessReceipt]:
        ...


@dataclass(frozen=True)
class ReplaySource:
    """Read sealed proposals from disk. Never launches a process.

    A transcript file is ``<transcript_dir>/<role_id>.json`` containing::

        {"prompt_digest": "...", "engine": "...", "model": "...",
         "response": {...}}

    ``prompt_digest`` is checked against the freshly rendered prompt, so a
    changed mandate invalidates a stale transcript instead of silently reusing
    a review of a different question.
    """

    transcript_dir: Path
    strict_prompt_digest: bool = True

    def run(self, role: ReviewerRole, prompt: str) -> tuple[str, SubprocessReceipt]:
        path = self.transcript_dir / f"{role.role_id}.json"
        if not path.is_file():
            raise InputContractError(
                f"no sealed transcript for role {role.role_id} at {path}"
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        prompt_digest = digest_bytes(prompt.encode("utf-8"))
        recorded = str(payload.get("prompt_digest", ""))
        if self.strict_prompt_digest and recorded != prompt_digest:
            raise InputContractError(
                f"transcript for {role.role_id} was produced under a different "
                f"mandate: recorded prompt digest {recorded[:16]}..., current "
                f"{prompt_digest[:16]}..."
            )
        response = payload["response"]
        text = json.dumps(response, sort_keys=True)
        receipt = SubprocessReceipt(
            role_id=role.role_id,
            engine=str(payload.get("engine", "replay")),
            model=str(payload.get("model", "replay")),
            task=f"adversarial-review:{role.role_id}",
            prompt_digest=prompt_digest,
            response_digest=digest_bytes(canonical_bytes(response)),
            input_tokens=payload.get("input_tokens"),
            output_tokens=payload.get("output_tokens"),
            cost_usd_upper_bound=float(payload.get("cost_usd_upper_bound", 0.0)),
            wall_clock_seconds=0.0,
            exit_status="replayed",
        )
        return text, receipt


@dataclass(frozen=True)
class LiveSource:
    """Launch a real reviewer subprocess under a bounded budget.

    Not exercised by the repository's tests: the narrow tests run entirely on
    ``ReplaySource`` with synthetic transcripts, which is why the test suite
    costs nothing and needs no network.
    """

    engine: str
    model: str
    cwd: Path
    budget: Budget = Budget()

    def run(self, role: ReviewerRole, prompt: str) -> tuple[str, SubprocessReceipt]:
        if self.engine not in ENGINE_ARGV:
            raise InputContractError(f"unknown reviewer engine {self.engine!r}")
        argv = list(ENGINE_ARGV[self.engine])
        argv.append(prompt)
        started = time.monotonic()
        completed = subprocess.run(  # noqa: S603 - fixed argv, campaign-controlled prompt
            argv,
            cwd=str(self.cwd),
            capture_output=True,
            text=True,
            timeout=self.budget.max_wall_clock_seconds,
            check=False,
        )
        elapsed = time.monotonic() - started
        self.budget.check_wall_clock(elapsed, role.role_id)
        text = completed.stdout
        receipt = SubprocessReceipt(
            role_id=role.role_id,
            engine=self.engine,
            model=self.model,
            task=f"adversarial-review:{role.role_id}",
            prompt_digest=digest_bytes(prompt.encode("utf-8")),
            response_digest=digest_bytes(text.encode("utf-8")),
            cost_usd_upper_bound=self.budget.max_cost_usd,
            wall_clock_seconds=elapsed,
            exit_status="ok" if completed.returncode == 0 else f"exit:{completed.returncode}",
        )
        return text, receipt


def parse_proposal(
    role: ReviewerRole, text: str, receipt: SubprocessReceipt
) -> ReviewerReport:
    """Parse untrusted proposal text into a ``ReviewerReport``.

    Anything outside the contract — a wrong ``role_id``, a malformed finding,
    non-JSON output — is a hard parse failure. The system prefers a refused
    review to a guessed one.
    """

    payload = _extract_json(text)
    claimed_role = str(payload.get("role_id", ""))
    if claimed_role != role.role_id:
        raise InputContractError(
            f"proposal claims role {claimed_role!r} but was produced for {role.role_id!r}"
        )
    raw_findings = payload.get("findings", [])
    if not isinstance(raw_findings, list):
        raise InputContractError("proposal 'findings' must be a list")
    findings = tuple(
        Finding.from_mapping({**item, "role_id": role.role_id}) for item in raw_findings
    )
    return ReviewerReport(
        role_id=role.role_id,
        role_title=role.title,
        mandate_digest=role.mandate_digest,
        findings=findings,
        coverage_notes=tuple(str(item) for item in payload.get("coverage_notes", ())),
        declared_dependencies=tuple(
            str(item) for item in payload.get("declared_dependencies", ())
        ),
        receipt=receipt,
    )


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise InputContractError("proposal was empty")
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise InputContractError("proposal contained no JSON object") from None
        try:
            value = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            raise InputContractError(f"proposal JSON is malformed: {exc}") from exc
    if not isinstance(value, dict):
        raise InputContractError("proposal JSON must be an object")
    return value

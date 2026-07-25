"""Frozen-decoding Ollama client for the placebo-controlled repair experiment.

Every model call in the study goes through this module, which exists to enforce
three things the design
(`docs/research/neurips-2026-workshop/25-placebo-selfreport-design.md`) treats as
parity requirements rather than conveniences:

*   **Decoding parity** (section 6.5). A :class:`DecodingConfig` is frozen and
    hashed; the hash is stamped on every logged call, so a mid-batch change to
    temperature or max tokens is visible in the receipt instead of invisible in the
    results.
*   **Call parity** (section 6.4). Arms must make an identical number and order of
    model calls per (tuple, seed, arm) -- ``R0 NONE`` still generates and discards a
    real reflection for exactly this reason. :meth:`OllamaBackend.assertCallParity`
    raises during the batch; discovering a violation in analysis is too late.
*   **Resumability.** A content-addressed JSONL cache keyed by
    ``(config_hash, prompt_hash, seed)`` returns byte-identical text on a hit, so a
    crashed overnight batch resumes instead of restarting.

Determinism is *measured, never assumed*. :func:`auditSeedDeterminism` issues the
same prompt twice at the same seed with the cache bypassed and records whether the
outputs actually matched. Nothing in this module claims seed determinism on the
strength of having passed a seed.

Transport is stdlib ``urllib`` behind the injectable ``transport`` seam, so tests
never contact a server and the repo takes on no new dependency.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 300.0
DEFAULT_GROUP = "ungrouped"
GENERATE_ENDPOINT = "/api/generate"

UNREACHABLE_MESSAGE = (
    "Cannot reach the local Ollama server at {host} ({reason}).\n"
    "Fix: start it with `ollama serve`, confirm with "
    "`curl {host}/api/tags`, and confirm the model is pulled with "
    "`ollama pull {model}`.\n"
    "No study call was made and nothing was written to the cache or call log."
)


class BackendError(RuntimeError):
    """Base class for model-backend failures."""


class BackendUnavailable(BackendError):
    """The Ollama server is unreachable, or the requested model is not present."""


class BackendGenerationError(BackendError):
    """The server answered, but the generation failed or the response was malformed."""


class CallParityError(BackendError):
    """Arms did not make an identical number of model calls. Aborts the batch."""


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------


def hashText(text: str) -> str:
    """Stable sha256 of a UTF-8 string. Used for prompt and output identity."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cacheKey(config_hash: str, prompt_hash: str, seed: int) -> str:
    """Content address of one generation: (config, prompt, seed)."""
    return hashlib.sha256(
        f"{config_hash}|{prompt_hash}|{int(seed)}".encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------------------------
# Frozen records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecodingConfig:
    """The frozen decoding policy. Its hash is the parity receipt for section 6.5."""

    model: str
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 1024
    num_ctx: int = 4096
    stop: tuple[str, ...] = ()
    host: str = DEFAULT_OLLAMA_HOST
    request_timeout_s: float = DEFAULT_REQUEST_TIMEOUT_SECONDS

    def identity(self) -> dict[str, Any]:
        """The fields that change what the model produces. Transport is excluded."""
        return {
            "model": self.model,
            "temperature": float(self.temperature),
            "top_p": float(self.top_p),
            "max_tokens": int(self.max_tokens),
            "num_ctx": int(self.num_ctx),
            "stop": list(self.stop),
        }

    @property
    def config_hash(self) -> str:
        return hashText(
            json.dumps(self.identity(), sort_keys=True, separators=(",", ":"))
        )

    def asOptions(self, seed: int) -> dict[str, Any]:
        """Ollama ``options`` block for one call."""
        options = {
            "temperature": float(self.temperature),
            "top_p": float(self.top_p),
            "num_predict": int(self.max_tokens),
            "num_ctx": int(self.num_ctx),
            "seed": int(seed),
        }
        if self.stop:
            options["stop"] = list(self.stop)
        return options


@dataclass(frozen=True)
class CallRecord:
    """One logged model call. Written to the call log whether cached or not."""

    model: str
    config_hash: str
    seed: int
    prompt_hash: str
    output_hash: str
    latency_s: float
    prompt_tokens: int
    completion_tokens: int
    cached: bool
    cache_key: str
    group: str = DEFAULT_GROUP
    done_reason: str = ""
    wall_clock_utc: str = ""

    def asRow(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GenerationResult:
    """Response text plus its per-call record."""

    text: str
    record: CallRecord


@dataclass(frozen=True)
class SeedDeterminismAudit:
    """Measured -- not assumed -- reproducibility of one prompt at one seed."""

    model: str
    config_hash: str
    seed: int
    prompt_hash: str
    repeats: int
    output_hashes: tuple[str, ...]
    deterministic: bool
    note: str = ""

    def asRow(self) -> dict[str, Any]:
        row = asdict(self)
        row["output_hashes"] = list(self.output_hashes)
        return row


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


def ollamaTransport(
    prompt: str, *, config: DecodingConfig, seed: int
) -> dict[str, Any]:
    """POST one non-streaming completion to a local Ollama and return the raw payload."""
    body = {
        "model": config.model,
        "prompt": prompt,
        "stream": False,
        "options": config.asOptions(seed),
    }
    request = urllib.request.Request(
        config.host.rstrip("/") + GENERATE_ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=config.request_timeout_s
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise BackendUnavailable(
                UNREACHABLE_MESSAGE.format(
                    host=config.host,
                    model=config.model,
                    reason=f"HTTP 404 -- model {config.model!r} or {GENERATE_ENDPOINT} not found",
                )
            ) from exc
        raise BackendGenerationError(
            f"ollama returned HTTP {exc.code} for model {config.model!r}"
        ) from exc
    except urllib.error.URLError as exc:
        raise BackendUnavailable(
            UNREACHABLE_MESSAGE.format(
                host=config.host, model=config.model, reason=exc.reason
            )
        ) from exc
    except (TimeoutError, ConnectionError) as exc:
        raise BackendUnavailable(
            UNREACHABLE_MESSAGE.format(
                host=config.host,
                model=config.model,
                reason=f"{type(exc).__name__}: {exc}",
            )
        ) from exc
    except OSError as exc:
        raise BackendGenerationError(f"ollama request failed: {exc}") from exc
    except ValueError as exc:
        raise BackendGenerationError(f"ollama returned malformed JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("response"), str):
        raise BackendGenerationError(
            "ollama response is missing a string 'response' field"
        )
    return payload


# ---------------------------------------------------------------------------
# Call parity
# ---------------------------------------------------------------------------


def assertCallParity(counts: Mapping[str, int], *, expected: int | None = None) -> int:
    """Assert every group made the same number of model calls; return that number.

    Design section 6.4: a violation aborts the batch. This is a pure function so a
    batch driver can check counts it accumulated itself, not only a backend's.
    """
    if not counts:
        raise CallParityError(
            "call parity cannot be checked: no call groups were recorded"
        )
    distinct = sorted(set(counts.values()))
    if expected is None:
        if len(distinct) > 1:
            offenders = ", ".join(
                f"{group}={count}" for group, count in sorted(counts.items())
            )
            raise CallParityError(
                "CALL PARITY VIOLATION -- arms did not make an identical number of "
                f"model calls: {offenders}. Aborting the batch; a parity failure is a "
                "reported defect, never silently repaired."
            )
        return distinct[0]
    offenders = {group: count for group, count in counts.items() if count != expected}
    if offenders:
        rendered = ", ".join(
            f"{group}={count}" for group, count in sorted(offenders.items())
        )
        raise CallParityError(
            f"CALL PARITY VIOLATION -- expected {expected} model calls per group, got "
            f"{rendered}. Aborting the batch; a parity failure is a reported defect, "
            "never silently repaired."
        )
    return expected


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------


@dataclass
class OllamaBackend:
    """A frozen-decoding, cached, fully logged Ollama client.

    The cache and the call log are separate files on purpose: the cache is the
    resumability substrate (keyed, deduplicated) and the log is the audit trail
    (append-only, one row per call including cache hits, so call parity can be
    recomputed from disk after the fact).
    """

    config: DecodingConfig
    cache_path: Path | None = None
    log_path: Path | None = None
    transport: Callable[..., dict[str, Any]] = ollamaTransport
    records: list[CallRecord] = field(default_factory=list, init=False)
    _cache: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _call_counts: Counter = field(default_factory=Counter, init=False, repr=False)
    _group: str = field(default=DEFAULT_GROUP, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.cache_path is not None:
            self.cache_path = Path(self.cache_path)
            self._loadCache()
        if self.log_path is not None:
            self.log_path = Path(self.log_path)
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # -- cache ------------------------------------------------------------

    def _loadCache(self) -> None:
        """Replay the append-only cache file. A later row wins, and a truncated final
        row (crashed mid-write) is skipped rather than fataling the resume."""
        path = self.cache_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key, text = row.get("cache_key"), row.get("text")
                if isinstance(key, str) and isinstance(text, str):
                    self._cache[key] = text

    def _appendCache(self, key: str, prompt_hash: str, seed: int, text: str) -> None:
        self._cache[key] = text
        if self.cache_path is None:
            return
        row = {
            "cache_key": key,
            "config_hash": self.config.config_hash,
            "prompt_hash": prompt_hash,
            "seed": int(seed),
            "model": self.config.model,
            "text": text,
        }
        with self.cache_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    # -- logging ----------------------------------------------------------

    def _log(self, record: CallRecord) -> None:
        self.records.append(record)
        if self.log_path is None:
            return
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(record.asRow(), ensure_ascii=False, sort_keys=True) + "\n"
            )

    # -- call counting ----------------------------------------------------

    @contextmanager
    def callGroup(self, key: str) -> Iterator[None]:
        """Attribute every call made in this block to one (tuple, seed, arm) group."""
        previous = self._group
        self._group = key
        self._call_counts.setdefault(key, 0)
        try:
            yield
        finally:
            self._group = previous

    @property
    def call_counts(self) -> dict[str, int]:
        return dict(self._call_counts)

    def assertCallParity(self, *, expected: int | None = None) -> int:
        """Raise :class:`CallParityError` unless every group made the same call count."""
        return assertCallParity(self._call_counts, expected=expected)

    def resetCallCounts(self) -> None:
        self._call_counts.clear()

    # -- generation -------------------------------------------------------

    def generate(
        self,
        prompt: str,
        seed: int,
        *,
        group: str | None = None,
        bypass_cache: bool = False,
    ) -> GenerationResult:
        """Generate one completion. A cache hit returns byte-identical stored text.

        Cache hits are still counted and logged: a call that was answered from disk
        is still a call the arm made, and dropping it would corrupt call parity.
        """
        group_key = group or self._group
        self._call_counts[group_key] += 1

        config_hash = self.config.config_hash
        prompt_hash = hashText(prompt)
        key = cacheKey(config_hash, prompt_hash, seed)

        if not bypass_cache and key in self._cache:
            text = self._cache[key]
            record = CallRecord(
                model=self.config.model,
                config_hash=config_hash,
                seed=int(seed),
                prompt_hash=prompt_hash,
                output_hash=hashText(text),
                latency_s=0.0,
                prompt_tokens=0,
                completion_tokens=0,
                cached=True,
                cache_key=key,
                group=group_key,
                done_reason="cache",
                wall_clock_utc=_utcNow(),
            )
            self._log(record)
            return GenerationResult(text=text, record=record)

        started = time.perf_counter()
        payload = self.transport(prompt, config=self.config, seed=int(seed))
        latency = time.perf_counter() - started

        text = payload["response"]
        if not bypass_cache:
            self._appendCache(key, prompt_hash, seed, text)

        record = CallRecord(
            model=str(payload.get("model") or self.config.model),
            config_hash=config_hash,
            seed=int(seed),
            prompt_hash=prompt_hash,
            output_hash=hashText(text),
            latency_s=latency,
            prompt_tokens=int(payload.get("prompt_eval_count") or 0),
            completion_tokens=int(payload.get("eval_count") or 0),
            cached=False,
            cache_key=key,
            group=group_key,
            done_reason=str(payload.get("done_reason") or ""),
            wall_clock_utc=_utcNow(),
        )
        self._log(record)
        return GenerationResult(text=text, record=record)


def _utcNow() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Seed determinism audit
# ---------------------------------------------------------------------------


def auditSeedDeterminism(
    backend: OllamaBackend,
    prompt: str,
    seed: int,
    *,
    repeats: int = 2,
    group: str = "seed-determinism-audit",
) -> SeedDeterminismAudit:
    """Issue the same prompt ``repeats`` times at one seed and report whether it matched.

    The cache is bypassed -- caching the first response and then "confirming" it from
    cache would manufacture the determinism this function exists to measure. The
    result is recorded so the paper can state what was observed rather than what the
    API documents.
    """
    if repeats < 2:
        raise ValueError("a determinism audit needs at least 2 repeats")
    hashes: list[str] = []
    for _ in range(repeats):
        result = backend.generate(prompt, seed, group=group, bypass_cache=True)
        hashes.append(result.record.output_hash)
    deterministic = len(set(hashes)) == 1
    return SeedDeterminismAudit(
        model=backend.config.model,
        config_hash=backend.config.config_hash,
        seed=int(seed),
        prompt_hash=hashText(prompt),
        repeats=repeats,
        output_hashes=tuple(hashes),
        deterministic=deterministic,
        note=(
            "measured: identical output across repeats at this seed"
            if deterministic
            else "measured: output VARIED across repeats at a fixed seed -- do not "
            "claim seed determinism for this backend/model"
        ),
    )


__all__ = [
    "BackendError",
    "BackendGenerationError",
    "BackendUnavailable",
    "CallParityError",
    "CallRecord",
    "DEFAULT_GROUP",
    "DEFAULT_OLLAMA_HOST",
    "DEFAULT_REQUEST_TIMEOUT_SECONDS",
    "DecodingConfig",
    "GenerationResult",
    "OllamaBackend",
    "SeedDeterminismAudit",
    "assertCallParity",
    "auditSeedDeterminism",
    "cacheKey",
    "hashText",
    "ollamaTransport",
]

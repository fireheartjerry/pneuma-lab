"""Tests for the frozen-decoding Ollama backend.

No test here starts a server or opens a socket. The HTTP layer is exercised through
``urllib.request.urlopen``, which is monkeypatched, and every other test injects a
fake ``transport``. That is deliberate: the suite has to run in CI-like conditions,
and the failure modes worth testing (unreachable server, 404 model, malformed JSON)
are exactly the ones a live server would refuse to reproduce on demand.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from pneuma_lab.placebo import backend as backend_module
from pneuma_lab.placebo.backend import (
    BackendGenerationError,
    BackendUnavailable,
    CallParityError,
    DecodingConfig,
    OllamaBackend,
    assertCallParity,
    auditSeedDeterminism,
    cacheKey,
    hashText,
    ollamaTransport,
)

MODEL = "qwen2.5-coder:7b"


def makeConfig(**overrides) -> DecodingConfig:
    values = {"model": MODEL, "temperature": 0.0, "top_p": 1.0, "max_tokens": 256}
    values.update(overrides)
    return DecodingConfig(**values)


class FakeTransport:
    """Records every call and returns a scripted Ollama payload."""

    def __init__(self, texts=None):
        self.calls: list[dict] = []
        self._texts = list(texts) if texts is not None else None

    def __call__(self, prompt: str, *, config: DecodingConfig, seed: int) -> dict:
        self.calls.append({"prompt": prompt, "seed": seed, "config": config})
        if self._texts is not None:
            text = self._texts[min(len(self.calls) - 1, len(self._texts) - 1)]
        else:
            text = f"response for {prompt!r} @ seed {seed}"
        return {
            "model": config.model,
            "response": text,
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 11,
            "eval_count": 7,
        }

    @property
    def count(self) -> int:
        return len(self.calls)


def makeBackend(
    tmp_path, transport=None, **config_overrides
) -> tuple[OllamaBackend, FakeTransport]:
    transport = transport or FakeTransport()
    backend = OllamaBackend(
        config=makeConfig(**config_overrides),
        cache_path=tmp_path / "cache.jsonl",
        log_path=tmp_path / "calls.jsonl",
        transport=transport,
    )
    return backend, transport


# ---------------------------------------------------------------------------
# Frozen decoding configuration
# ---------------------------------------------------------------------------


def test_decodingConfigIsFrozen() -> None:
    config = makeConfig()
    with pytest.raises(Exception):
        config.temperature = 0.9  # type: ignore[misc]


def test_configHashIsStableAcrossEqualConfigs() -> None:
    assert makeConfig().config_hash == makeConfig().config_hash


@pytest.mark.parametrize(
    "override",
    [
        {"temperature": 0.7},
        {"top_p": 0.9},
        {"max_tokens": 512},
        {"num_ctx": 8192},
        {"model": "qwen2.5-coder:1.5b"},
        {"stop": ("###",)},
    ],
)
def test_anyDecodingChangeChangesTheConfigHash(override) -> None:
    assert makeConfig(**override).config_hash != makeConfig().config_hash


def test_transportSettingsDoNotChangeTheConfigHash() -> None:
    """Host and timeout are transport, not decoding: moving the server must not
    invalidate a cache or look like a parity break."""
    moved = makeConfig(host="http://192.168.1.9:11434", request_timeout_s=30.0)
    assert moved.config_hash == makeConfig().config_hash


def test_asOptionsCarriesTheSeedAndTheFrozenDecodingPolicy() -> None:
    options = makeConfig(stop=("</s>",)).asOptions(seed=17)
    assert options["seed"] == 17
    assert options["temperature"] == 0.0
    assert options["num_predict"] == 256
    assert options["stop"] == ["</s>"]


def test_stopIsOmittedWhenEmpty() -> None:
    assert "stop" not in makeConfig().asOptions(seed=1)


# ---------------------------------------------------------------------------
# Generation and the per-call record
# ---------------------------------------------------------------------------


def test_generateReturnsTextAndAFullyPopulatedRecord(tmp_path) -> None:
    backend, transport = makeBackend(tmp_path)
    result = backend.generate("write a fix", seed=3, group="R3/seed3")

    assert transport.calls[0]["prompt"] == "write a fix"
    assert "write a fix" in result.text
    record = result.record
    assert record.model == MODEL
    assert record.seed == 3
    assert record.config_hash == backend.config.config_hash
    assert record.prompt_hash == hashText("write a fix")
    assert record.output_hash == hashText(result.text)
    assert record.prompt_tokens == 11
    assert record.completion_tokens == 7
    assert record.cached is False
    assert record.latency_s >= 0.0
    assert record.group == "R3/seed3"
    assert record.done_reason == "stop"


def test_everyCallIsLoggedAsAJsonlRow(tmp_path) -> None:
    backend, _ = makeBackend(tmp_path)
    backend.generate("p", seed=1)
    backend.generate("p", seed=1)  # cache hit, still a call the arm made

    rows = [
        json.loads(line) for line in (tmp_path / "calls.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 2
    assert [row["cached"] for row in rows] == [False, True]
    for row in rows:
        assert set(
            [
                "model",
                "seed",
                "prompt_hash",
                "output_hash",
                "latency_s",
                "prompt_tokens",
                "completion_tokens",
                "cached",
                "config_hash",
            ]
        ) <= set(row)


def test_recordsAreAlsoHeldInMemory(tmp_path) -> None:
    backend, _ = makeBackend(tmp_path)
    backend.generate("a", seed=1)
    backend.generate("b", seed=1)
    assert len(backend.records) == 2


# ---------------------------------------------------------------------------
# Content-addressed cache -- resumability
# ---------------------------------------------------------------------------


def test_cacheKeyDependsOnConfigPromptAndSeed() -> None:
    base = cacheKey("cfg", "prompt", 1)
    assert base != cacheKey("cfg2", "prompt", 1)
    assert base != cacheKey("cfg", "prompt2", 1)
    assert base != cacheKey("cfg", "prompt", 2)
    assert base == cacheKey("cfg", "prompt", 1)


def test_cacheHitReturnsByteIdenticalOutputWithoutCallingTheModel(tmp_path) -> None:
    backend, transport = makeBackend(tmp_path, FakeTransport(texts=["first", "SECOND"]))
    first = backend.generate("p", seed=5)
    second = backend.generate("p", seed=5)

    assert transport.count == 1
    assert second.text == first.text == "first"
    assert second.record.output_hash == first.record.output_hash
    assert second.record.cached is True


def test_cacheMissesOnADifferentSeed(tmp_path) -> None:
    backend, transport = makeBackend(tmp_path)
    backend.generate("p", seed=1)
    backend.generate("p", seed=2)
    assert transport.count == 2


def test_cacheMissesWhenTheDecodingConfigChanges(tmp_path) -> None:
    first, transport_a = makeBackend(tmp_path)
    first.generate("p", seed=1)
    second = OllamaBackend(
        config=makeConfig(temperature=0.7),
        cache_path=tmp_path / "cache.jsonl",
        transport=(transport_b := FakeTransport()),
    )
    second.generate("p", seed=1)
    assert transport_b.count == 1


def test_aCrashedBatchResumesFromTheCacheFile(tmp_path) -> None:
    """The whole point of the cache: a new process re-reads prior work from disk."""
    first, transport_a = makeBackend(
        tmp_path, FakeTransport(texts=["overnight output"])
    )
    first.generate("p", seed=9)

    resumed, transport_b = makeBackend(tmp_path, FakeTransport(texts=["DIFFERENT"]))
    result = resumed.generate("p", seed=9)

    assert transport_b.count == 0
    assert result.text == "overnight output"
    assert result.record.cached is True


def test_resumeSurvivesATruncatedFinalCacheRow(tmp_path) -> None:
    backend, _ = makeBackend(tmp_path, FakeTransport(texts=["good"]))
    backend.generate("p", seed=1)
    with (tmp_path / "cache.jsonl").open("a", encoding="utf-8") as handle:
        handle.write('{"cache_key": "half-writ')

    resumed, transport = makeBackend(tmp_path, FakeTransport(texts=["DIFFERENT"]))
    assert resumed.generate("p", seed=1).text == "good"
    assert transport.count == 0


def test_cachePreservesUnicodeAndWhitespaceExactly(tmp_path) -> None:
    text = "def f():\r\n\t return 'é—你好'  \n\n"
    backend, _ = makeBackend(tmp_path, FakeTransport(texts=[text]))
    backend.generate("p", seed=1)
    resumed, _ = makeBackend(tmp_path, FakeTransport(texts=["X"]))
    assert resumed.generate("p", seed=1).text == text


def test_backendWorksWithNoCacheFileConfigured() -> None:
    backend = OllamaBackend(
        config=makeConfig(), transport=(transport := FakeTransport())
    )
    backend.generate("p", seed=1)
    assert backend.generate("p", seed=1).record.cached is True  # in-memory cache
    assert transport.count == 1


# ---------------------------------------------------------------------------
# Call parity -- design section 6.4
# ---------------------------------------------------------------------------


def test_assertCallParityReturnsTheSharedCountWhenArmsMatch() -> None:
    assert assertCallParity({"R0": 2, "R1": 2, "R3": 2}) == 2


def test_assertCallParityFiresOnAMismatch() -> None:
    with pytest.raises(CallParityError) as excinfo:
        assertCallParity({"R0": 1, "R3": 2})
    message = str(excinfo.value)
    assert "CALL PARITY VIOLATION" in message
    assert "R0=1" in message and "R3=2" in message


def test_assertCallParityFiresWhenTheSharedCountIsNotTheExpectedOne() -> None:
    with pytest.raises(CallParityError):
        assertCallParity({"R0": 2, "R3": 2}, expected=3)


def test_assertCallParityRefusesToPassOnNoData() -> None:
    with pytest.raises(CallParityError):
        assertCallParity({})


def test_backendCountsCallsPerGroupAndAssertsParity(tmp_path) -> None:
    backend, _ = makeBackend(tmp_path)
    for arm in ("R0", "R1", "R3"):
        with backend.callGroup(f"{arm}/tuple7/seed1"):
            backend.generate("reflect", seed=1)
            backend.generate("repair", seed=1)
    assert backend.call_counts == {
        "R0/tuple7/seed1": 2,
        "R1/tuple7/seed1": 2,
        "R3/tuple7/seed1": 2,
    }
    assert backend.assertCallParity(expected=2) == 2


def test_anArmThatSkipsAGenerationAbortsTheBatch(tmp_path) -> None:
    """R0 NONE must still generate and discard a real reflection. If it does not,
    this is where the batch dies -- not in analysis."""
    backend, _ = makeBackend(tmp_path)
    with backend.callGroup("R3/tuple7/seed1"):
        backend.generate("reflect", seed=1)
        backend.generate("repair", seed=1)
    with backend.callGroup("R0/tuple7/seed1"):
        backend.generate("repair", seed=1)  # forgot the discarded reflection

    with pytest.raises(CallParityError):
        backend.assertCallParity()


def test_cacheHitsStillCountTowardsCallParity(tmp_path) -> None:
    """A resumed unit must not look like it made fewer calls than a fresh one."""
    backend, transport = makeBackend(tmp_path)
    with backend.callGroup("fresh"):
        backend.generate("p", seed=1)
    with backend.callGroup("resumed"):
        backend.generate("p", seed=1)
    assert transport.count == 1
    assert backend.assertCallParity() == 1


def test_callGroupsNestAndRestore(tmp_path) -> None:
    backend, _ = makeBackend(tmp_path)
    with backend.callGroup("outer"):
        backend.generate("a", seed=1)
        with backend.callGroup("inner"):
            backend.generate("b", seed=1)
        backend.generate("c", seed=1)
    assert backend.call_counts == {"outer": 2, "inner": 1}


def test_explicitGroupArgumentOverridesTheAmbientGroup(tmp_path) -> None:
    backend, _ = makeBackend(tmp_path)
    with backend.callGroup("ambient"):
        backend.generate("a", seed=1, group="explicit")
    assert backend.call_counts["explicit"] == 1


def test_resetCallCountsClearsTheLedger(tmp_path) -> None:
    backend, _ = makeBackend(tmp_path)
    backend.generate("a", seed=1)
    backend.resetCallCounts()
    assert backend.call_counts == {}


# ---------------------------------------------------------------------------
# Seed determinism -- measured, never assumed
# ---------------------------------------------------------------------------


def test_seedDeterminismAuditReportsAMatchWhenOutputsAgree(tmp_path) -> None:
    backend, transport = makeBackend(tmp_path, FakeTransport(texts=["same", "same"]))
    audit = auditSeedDeterminism(backend, "p", seed=4, repeats=2)
    assert audit.deterministic is True
    assert len(set(audit.output_hashes)) == 1
    assert audit.seed == 4
    assert audit.model == MODEL
    assert transport.count == 2


def test_seedDeterminismAuditReportsAMismatchRatherThanAssumingDeterminism(
    tmp_path,
) -> None:
    backend, _ = makeBackend(tmp_path, FakeTransport(texts=["alpha", "beta"]))
    audit = auditSeedDeterminism(backend, "p", seed=4, repeats=2)
    assert audit.deterministic is False
    assert len(set(audit.output_hashes)) == 2
    assert "do not" in audit.note and "claim seed determinism" in audit.note


def test_seedDeterminismAuditBypassesTheCache(tmp_path) -> None:
    """Answering the second repeat from cache would manufacture the very result the
    audit exists to measure."""
    backend, transport = makeBackend(tmp_path, FakeTransport(texts=["a", "b", "c"]))
    audit = auditSeedDeterminism(backend, "p", seed=1, repeats=3)
    assert transport.count == 3
    assert audit.deterministic is False
    assert backend.cache_size == 0  # audit responses never poison the study cache


def test_seedDeterminismAuditIsRecordable(tmp_path) -> None:
    backend, _ = makeBackend(tmp_path, FakeTransport(texts=["same", "same"]))
    row = auditSeedDeterminism(backend, "p", seed=4).asRow()
    assert json.loads(json.dumps(row))["deterministic"] is True


def test_seedDeterminismAuditRejectsASingleRepeat(tmp_path) -> None:
    backend, _ = makeBackend(tmp_path)
    with pytest.raises(ValueError):
        auditSeedDeterminism(backend, "p", seed=1, repeats=1)


# ---------------------------------------------------------------------------
# Transport failures -- no server required
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def patchUrlopen(monkeypatch, behaviour):
    monkeypatch.setattr(backend_module.urllib.request, "urlopen", behaviour)


def test_unreachableServerRaisesAnActionableBackendUnavailable(monkeypatch) -> None:
    def refuse(request, timeout=None):
        raise urllib.error.URLError(ConnectionRefusedError(61, "Connection refused"))

    patchUrlopen(monkeypatch, refuse)
    with pytest.raises(BackendUnavailable) as excinfo:
        ollamaTransport("p", config=makeConfig(), seed=1)
    message = str(excinfo.value)
    assert "ollama serve" in message
    assert makeConfig().host in message
    assert "nothing was written to the cache" in message


def test_unreachableServerLeavesTheCacheAndLogUntouched(tmp_path, monkeypatch) -> None:
    def refuse(request, timeout=None):
        raise urllib.error.URLError("no route to host")

    patchUrlopen(monkeypatch, refuse)
    backend = OllamaBackend(
        config=makeConfig(),
        cache_path=tmp_path / "cache.jsonl",
        log_path=tmp_path / "calls.jsonl",
        transport=ollamaTransport,
    )
    with pytest.raises(BackendUnavailable):
        backend.generate("p", seed=1)
    assert backend.cache_size == 0
    assert backend.records == []
    assert not (tmp_path / "cache.jsonl").exists()


def test_missingModelIsReportedAsUnavailableWithAPullHint(monkeypatch) -> None:
    def notFound(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    patchUrlopen(monkeypatch, notFound)
    with pytest.raises(BackendUnavailable) as excinfo:
        ollamaTransport("p", config=makeConfig(), seed=1)
    assert f"ollama pull {MODEL}" in str(excinfo.value)


def test_serverErrorIsAGenerationFailureNotAnAvailabilityFailure(monkeypatch) -> None:
    def boom(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 500, "Server Error", {}, None)

    patchUrlopen(monkeypatch, boom)
    with pytest.raises(BackendGenerationError):
        ollamaTransport("p", config=makeConfig(), seed=1)


def test_malformedJsonIsReportedClearly(monkeypatch) -> None:
    patchUrlopen(monkeypatch, lambda request, timeout=None: FakeResponse(b"not json"))
    with pytest.raises(BackendGenerationError) as excinfo:
        ollamaTransport("p", config=makeConfig(), seed=1)
    assert "malformed JSON" in str(excinfo.value)


def test_responseWithoutATextFieldIsRejected(monkeypatch) -> None:
    patchUrlopen(
        monkeypatch, lambda request, timeout=None: FakeResponse(b'{"done": true}')
    )
    with pytest.raises(BackendGenerationError) as excinfo:
        ollamaTransport("p", config=makeConfig(), seed=1)
    assert "'response'" in str(excinfo.value)


def test_transportPostsTheFrozenDecodingPolicy(monkeypatch) -> None:
    seen: dict = {}

    def capture(request, timeout=None):
        seen["url"] = request.full_url
        seen["body"] = json.loads(request.data.decode("utf-8"))
        seen["timeout"] = timeout
        return FakeResponse(b'{"response": "ok", "eval_count": 2}')

    patchUrlopen(monkeypatch, capture)
    config = makeConfig(request_timeout_s=42.0)
    payload = ollamaTransport("hello", config=config, seed=13)

    assert payload["response"] == "ok"
    assert seen["url"].endswith("/api/generate")
    assert seen["body"]["model"] == MODEL
    assert seen["body"]["stream"] is False
    assert seen["body"]["options"]["seed"] == 13
    assert seen["body"]["options"]["temperature"] == 0.0
    assert seen["timeout"] == 42.0


def test_emptyCompletionIsAcceptedAndHashedNotTreatedAsAnError(monkeypatch) -> None:
    """An empty repair is a data point (a failed unit), not a transport failure."""
    patchUrlopen(
        monkeypatch, lambda request, timeout=None: FakeResponse(b'{"response": ""}')
    )
    assert ollamaTransport("p", config=makeConfig(), seed=1)["response"] == ""

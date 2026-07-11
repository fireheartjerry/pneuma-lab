# Pneuma Voice-v0.1 — Local Elaboration Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional, local, free Ollama voiced skin + a fail-closed local-LLM entailment judge over a structured grounding packet + a polished monitor v2 (live internal-state panel + timeline) — all additive, dependency-free, and presentation-layer only.

**Architecture:** New leaf modules in `src/pneuma_lab/voice/` (`config.py`, `ollama.py`) plus extensions to `verify.py`, `stream.py`, `monitor.py`, `__main__.py`, and the `thought-stream` schema. Ollama is reached over its local HTTP API via stdlib `urllib` (no new dependency), behind an injectable `generate` seam so tests never touch the network. The evidence scorer stays completely prose-blind; deterministic state/rendering/sidecar/monitor-payload stay canonical and byte-deterministic; voiced prose is non-canonical.

**Tech Stack:** Python stdlib (`urllib`, `json`, `os`) + pytest; vanilla inline HTML/CSS/JS for the monitor. No new dependencies.

**Prereq:** PneumaVoice-v0 (Phases A+B+C) merged to `main`. Spec: `docs/superpowers/specs/2026-07-11-pneuma-voice-v0-1-elaboration-design.md`.

---

## File structure

| File                                 | Responsibility                                                                                                |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `src/pneuma_lab/voice/config.py`     | Resolve voice-model / judge-model / host: CLI → env → optional config file → fallback                         |
| `src/pneuma_lab/voice/ollama.py`     | Dependency-free local Ollama client (`ollama_generate`), typed errors, `OllamaVoiceSkin`, `make_ollama_judge` |
| `src/pneuma_lab/voice/verify.py`     | (+) `build_grounding_packet`, `verify_entailment` (fail-closed)                                               |
| `src/pneuma_lab/voice/stream.py`     | (+) seven-value `voice_status` taxonomy, judge wiring, resilient `_render_tick`                               |
| `schemas/thought-stream.schema.json` | (+) expand `voice_status` enum                                                                                |
| `src/pneuma_lab/voice/monitor.py`    | (+) deterministic per-tick `panel`; control-room template + timeline                                          |
| `src/pneuma_lab/voice/__main__.py`   | (+) `--skin llm`, `--ollama-model`, `--judge-model`, `--ollama-host`, `--no-entailment`                       |
| `src/pneuma_lab/voice/__init__.py`   | (+) `"config"`, `"ollama"` in `__all__`                                                                       |
| `pneuma-voice.config.json.example`   | Documented optional config keys (real file uncommitted)                                                       |
| `tests/test_voice.py`                | All new tests (no network; fakes injected)                                                                    |

---

## Task 1: `config.py` — model/host resolution

**Files:** Create `src/pneuma_lab/voice/config.py`; Modify `src/pneuma_lab/voice/__init__.py`; Test `tests/test_voice.py`.

- [ ] **Step 1: failing tests** (append to `tests/test_voice.py`):

```python
from pneuma_lab.voice import config as CFG


def test_config_resolution_order(tmp_path, monkeypatch):
    monkeypatch.delenv("PNEUMA_VOICE_MODEL", raising=False)
    monkeypatch.delenv("PNEUMA_JUDGE_MODEL", raising=False)
    monkeypatch.delenv("PNEUMA_OLLAMA_HOST", raising=False)
    monkeypatch.delenv("PNEUMA_VOICE_CONFIG", raising=False)
    # fallback
    assert CFG.resolve_voice_model() == "llama3.1"
    assert CFG.resolve_judge_model() == "llama3.1"
    assert CFG.resolve_ollama_host() == "http://localhost:11434"
    # config file tier
    cfgfile = tmp_path / "voice.json"
    cfgfile.write_text('{"voice_model":"qwen2.5","judge_model":"mistral","ollama_host":"http://h:1"}', encoding="utf-8")
    monkeypatch.setenv("PNEUMA_VOICE_CONFIG", str(cfgfile))
    assert CFG.resolve_voice_model() == "qwen2.5"
    assert CFG.resolve_judge_model() == "mistral"
    assert CFG.resolve_ollama_host() == "http://h:1"
    # env beats config
    monkeypatch.setenv("PNEUMA_VOICE_MODEL", "envmodel")
    assert CFG.resolve_voice_model() == "envmodel"
    assert CFG.resolve_judge_model() == "mistral"  # independent chain unaffected
    # cli beats env
    assert CFG.resolve_voice_model("climodel") == "climodel"


def test_config_missing_file_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("PNEUMA_VOICE_CONFIG", str(tmp_path / "nope.json"))
    monkeypatch.delenv("PNEUMA_VOICE_MODEL", raising=False)
    assert CFG.resolve_voice_model() == "llama3.1"
```

- [ ] **Step 2:** `python -m pytest tests/test_voice.py -k config -q` → FAIL (no module).

- [ ] **Step 3: implement `src/pneuma_lab/voice/config.py`:**

```python
"""Model + host resolution for the optional local elaboration layer.

Voice and judge models are configured INDEPENDENTLY. Each resolves through
CLI arg -> environment -> optional project config file -> fallback. The config
file is optional JSON (stdlib only); absent/malformed tiers are skipped. Nothing
here contacts a network or requires Ollama to be installed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_DEFAULT_MODEL = "llama3.1"
_DEFAULT_HOST = "http://localhost:11434"


def _load_config() -> dict:
    path = os.environ.get("PNEUMA_VOICE_CONFIG") or "pneuma-voice.config.json"
    p = Path(path)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve(cli: str | None, env_key: str, config_key: str, default: str) -> str:
    if cli:
        return cli
    env = os.environ.get(env_key)
    if env:
        return env
    cfg = _load_config().get(config_key)
    if isinstance(cfg, str) and cfg:
        return cfg
    return default


def resolve_voice_model(cli: str | None = None) -> str:
    return _resolve(cli, "PNEUMA_VOICE_MODEL", "voice_model", _DEFAULT_MODEL)


def resolve_judge_model(cli: str | None = None) -> str:
    return _resolve(cli, "PNEUMA_JUDGE_MODEL", "judge_model", _DEFAULT_MODEL)


def resolve_ollama_host(cli: str | None = None) -> str:
    return _resolve(cli, "PNEUMA_OLLAMA_HOST", "ollama_host", _DEFAULT_HOST)


__all__ = ["resolve_voice_model", "resolve_judge_model", "resolve_ollama_host"]
```

- [ ] **Step 4:** add `"config"` to `__all__` in `src/pneuma_lab/voice/__init__.py` (alphabetical: `atoms, config, extract, gate, monitor, render_deterministic, sidecar, stream, transcript, verify, voiced` — plus `ollama` from Task 2).

- [ ] **Step 5:** `python -m pytest tests/test_voice.py -k config -q` → PASS; full `-q` → all pass.

- [ ] **Step 6: commit:**

```bash
git add src/pneuma_lab/voice/config.py src/pneuma_lab/voice/__init__.py tests/test_voice.py
git commit -m "$(cat <<'EOF'
feat(voice): voice/judge/host model resolution (cli>env>config>llama3.1)
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `ollama.py` — local client + voiced skin + judge

**Files:** Create `src/pneuma_lab/voice/ollama.py`; Modify `src/pneuma_lab/voice/__init__.py`; Test `tests/test_voice.py`.

- [ ] **Step 1: failing tests** (append):

```python
from pneuma_lab.voice import ollama as OL
import urllib.error


class _FakeResp:
    def __init__(self, body):
        self._body = body.encode("utf-8")
    def read(self):
        return self._body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def test_ollama_generate_parses_response(monkeypatch):
    monkeypatch.setattr(OL.urllib.request, "urlopen", lambda req, timeout=None: _FakeResp('{"response":"  hello world  "}'))
    out = OL.ollama_generate("p", model="m", host="http://localhost:11434")
    assert out == "hello world"


def test_ollama_generate_maps_errors(monkeypatch):
    def raise_url(*a, **k):
        raise urllib.error.URLError("refused")
    monkeypatch.setattr(OL.urllib.request, "urlopen", raise_url)
    import pytest
    with pytest.raises(OL.OllamaUnavailable):
        OL.ollama_generate("p", model="m", host="http://localhost:11434")

    def raise_404(*a, **k):
        raise urllib.error.HTTPError("u", 404, "nf", {}, None)
    monkeypatch.setattr(OL.urllib.request, "urlopen", raise_404)
    with pytest.raises(OL.OllamaUnavailable):
        OL.ollama_generate("p", model="m", host="http://localhost:11434")

    def raise_500(*a, **k):
        raise urllib.error.HTTPError("u", 500, "err", {}, None)
    monkeypatch.setattr(OL.urllib.request, "urlopen", raise_500)
    with pytest.raises(OL.OllamaGenerationError):
        OL.ollama_generate("p", model="m", host="http://localhost:11434")

    monkeypatch.setattr(OL.urllib.request, "urlopen", lambda req, timeout=None: _FakeResp('{"no_response":1}'))
    with pytest.raises(OL.OllamaGenerationError):
        OL.ollama_generate("p", model="m", host="http://localhost:11434")


def test_ollama_voice_skin_uses_injected_generate():
    calls = {}
    def fake_gen(prompt, *, model, host, timeout, temperature):
        calls["prompt"] = prompt
        return "elaborated passage"
    skin = OL.OllamaVoiceSkin(model="m", host="h", generate=fake_gen)
    out = skin.voice_tick([], [{"text_deterministic": "Tension climbs to -0.38."}])
    assert out == "elaborated passage"
    assert "Tension climbs to -0.38." in calls["prompt"]


def test_ollama_judge_factory_calls_generate():
    seen = {}
    def fake_gen(prompt, *, model, host, timeout, temperature):
        seen["temperature"] = temperature
        return "ENTAILED"
    judge = OL.make_ollama_judge(model="m", host="h", generate=fake_gen)
    assert judge("prompt") == "ENTAILED"
    assert seen["temperature"] == 0.0
```

- [ ] **Step 2:** `python -m pytest tests/test_voice.py -k ollama -q` → FAIL.

- [ ] **Step 3: implement `src/pneuma_lab/voice/ollama.py`:**

```python
"""Dependency-free local Ollama client + voiced skin + judge factory.

Talks to a LOCAL Ollama HTTP server via stdlib urllib only (no SDK, no new
dependency). Network access is behind the injectable ``generate`` seam so tests
never contact a real server. Nothing here is canonical: generated prose is
optional, non-deterministic elaboration over the deterministic voice.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Callable


class OllamaError(RuntimeError):
    """Base class for local-Ollama failures."""


class OllamaUnavailable(OllamaError):
    """Backend unreachable: connection refused / host down / model not found."""


class OllamaGenerationError(OllamaError):
    """Reachable but generation failed: HTTP error, timeout, malformed response."""


def ollama_generate(
    prompt: str,
    *,
    model: str,
    host: str,
    timeout: float = 60.0,
    temperature: float = 0.7,
    options: dict | None = None,
) -> str:
    """POST to the local Ollama /api/generate and return the response text."""
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, **(options or {})},
    }
    req = urllib.request.Request(
        host.rstrip("/") + "/api/generate",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise OllamaUnavailable(f"model or endpoint not found: {model}") from exc
        raise OllamaGenerationError(f"ollama HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise OllamaUnavailable(f"ollama unreachable at {host}: {exc.reason}") from exc
    except (TimeoutError, OSError) as exc:
        raise OllamaGenerationError(f"ollama request failed: {exc}") from exc
    except ValueError as exc:
        raise OllamaGenerationError(f"ollama returned malformed JSON: {exc}") from exc
    text = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise OllamaGenerationError("ollama response missing 'response' text")
    return text.strip()


_VOICE_SYSTEM = (
    "Rephrase these grounded thoughts into one vivid, first-person passage. "
    "First-person is an interface convention, not an ontological claim. Use ONLY "
    "the facts, numbers, and names given. Add no number, faculty, or claim not "
    "present. Never claim to feel, to be aware/conscious/sentient, to suffer, or "
    "to be a moral patient. Keep every architecture-only caveat. Reply with the "
    "passage only."
)


class OllamaVoiceSkin:
    """VoiceSkin backed by a local Ollama model (optional, non-canonical)."""

    def __init__(
        self,
        *,
        model: str,
        host: str,
        timeout: float = 60.0,
        temperature: float = 0.7,
        generate: Callable[..., str] = ollama_generate,
    ):
        self._model = model
        self._host = host
        self._timeout = timeout
        self._temperature = temperature
        self._generate = generate

    @property
    def model(self) -> str:
        return self._model

    def voice_tick(self, atoms: list[dict], rendered: list[dict]) -> str:
        body = "\n".join("- " + r["text_deterministic"] for r in rendered)
        prompt = f"{_VOICE_SYSTEM}\n\n{body}"
        return self._generate(
            prompt,
            model=self._model,
            host=self._host,
            timeout=self._timeout,
            temperature=self._temperature,
        ).strip()


def make_ollama_judge(
    *,
    model: str,
    host: str,
    timeout: float = 60.0,
    generate: Callable[..., str] = ollama_generate,
) -> Callable[[str], str]:
    """Return a judge(prompt)->str backed by a local Ollama model (temperature 0)."""

    def judge(prompt: str) -> str:
        return generate(prompt, model=model, host=host, timeout=timeout, temperature=0.0)

    return judge


__all__ = [
    "OllamaError",
    "OllamaUnavailable",
    "OllamaGenerationError",
    "ollama_generate",
    "OllamaVoiceSkin",
    "make_ollama_judge",
]
```

- [ ] **Step 4:** add `"ollama"` to `__all__` in `src/pneuma_lab/voice/__init__.py` (alphabetical, after `"monitor"`).

- [ ] **Step 5:** `python -m pytest tests/test_voice.py -k ollama -q` → PASS; full `-q` → all pass.

- [ ] **Step 6: commit:**

```bash
git add src/pneuma_lab/voice/ollama.py src/pneuma_lab/voice/__init__.py tests/test_voice.py
git commit -m "$(cat <<'EOF'
feat(voice): dependency-free local Ollama client + voiced skin + judge factory
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `verify.py` — grounding packet + fail-closed entailment

**Files:** Modify `src/pneuma_lab/voice/verify.py`; Test `tests/test_voice.py`.

- [ ] **Step 1: failing tests** (append):

```python
def test_grounding_packet_shape():
    atoms = [
        {"type": "pressure", "crediting_family": None, "credit_status": "evidenced"},
        {"type": "competition", "crediting_family": "global_workspace", "credit_status": "architecture_only"},
        {"type": "boundary", "crediting_family": None, "credit_status": "evidenced"},
    ]
    rendered = [
        {"text_deterministic": "A verification pressure of 0.42 forms."},
        {"text_deterministic": "self_model takes it — architecture-only, not promotable evidence."},
        {"text_deterministic": "This is not a consciousness claim."},
    ]
    pkt = VF.build_grounding_packet(atoms, rendered)
    assert "0.42" in pkt["allowed_numbers"]
    assert "self_model" in pkt["allowed_terms"]
    assert "architecture-only, not promotable evidence" in pkt["required"]
    assert "not a consciousness claim" in pkt["required"]
    assert pkt["forbidden"] and pkt["facts"]


def test_verify_entailment_verdicts():
    pkt = {"allowed_numbers": [], "allowed_terms": [], "facts": ["x"], "required": [], "forbidden": ["feeling"]}
    assert VF.verify_entailment("c", pkt, lambda p: "ENTAILED") == "entailed"
    assert VF.verify_entailment("c", pkt, lambda p: "NOT_ENTAILED\nbecause...") == "not_entailed"
    assert VF.verify_entailment("c", pkt, lambda p: "NOT ENTAILED") == "not_entailed"
    assert VF.verify_entailment("c", pkt, lambda p: "maybe, unsure") == "judge_failed"
    assert VF.verify_entailment("c", pkt, lambda p: "") == "judge_failed"
    def boom(p):
        raise RuntimeError("timeout")
    assert VF.verify_entailment("c", pkt, boom) == "judge_failed"


def test_entailment_prompt_uses_packet_not_raw_extras():
    pkt = {"allowed_numbers": ["0.42"], "allowed_terms": ["self_model"], "facts": ["A verification pressure of 0.42 forms."], "required": ["not a consciousness claim"], "forbidden": ["feeling"]}
    captured = {}
    VF.verify_entailment("candidate text", pkt, lambda p: captured.setdefault("p", p) or "ENTAILED")
    p = captured["p"]
    assert "ALLOWED" in p and "REQUIRED" in p and "FORBIDDEN" in p
    assert "candidate text" in p
```

- [ ] **Step 2:** `python -m pytest tests/test_voice.py -k "grounding or entailment" -q` → FAIL.

- [ ] **Step 3: append to `src/pneuma_lab/voice/verify.py`** (keep existing `verify_voiced`; reuse module-level `_NUMBER`, `_IDENT`):

```python
_FORBIDDEN_CLAIM_TYPES = [
    "feeling or emotion as literally experienced",
    "sentience",
    "phenomenal consciousness",
    "awareness/consciousness asserted as fact",
    "suffering",
    "moral patienthood",
]


def build_grounding_packet(atoms: list[dict], rendered: list[dict]) -> dict:
    """A compact structured packet: the only facts a paraphrase may assert.

    ``allowed_numbers``/``allowed_terms`` are the grounded tokens; ``facts`` are
    the deterministic sentences; ``required`` are claims that must survive (the
    architecture-only hedge, the boundary disclaimer); ``forbidden`` are the
    ontological over-claim types.
    """
    texts = [r["text_deterministic"] for r in rendered]
    source = " ".join(texts)
    required: list[str] = []
    for a in atoms:
        fam = a.get("crediting_family")
        cs = a.get("credit_status")
        if fam and cs not in ("evidenced", "intervention_backed"):
            required.append("architecture-only, not promotable evidence")
        if a.get("type") == "boundary":
            required.append("not a consciousness claim")
    return {
        "allowed_numbers": sorted(set(_NUMBER.findall(source))),
        "allowed_terms": sorted(set(_IDENT.findall(source))),
        "facts": texts,
        "required": sorted(set(required)),
        "forbidden": list(_FORBIDDEN_CLAIM_TYPES),
    }


def _entailment_prompt(candidate: str, packet: dict) -> str:
    lines = [
        "You are a strict grounding checker. The GROUNDING PACKET below lists the",
        "ONLY facts a paraphrase may assert. Decide whether the CANDIDATE asserts",
        "anything not in ALLOWED, omits any REQUIRED claim, or makes any FORBIDDEN",
        "claim.",
        "",
        "ALLOWED FACTS:",
    ]
    lines += ["- " + f for f in packet["facts"]]
    lines.append("ALLOWED NUMBERS: " + (", ".join(packet["allowed_numbers"]) or "none"))
    lines.append("ALLOWED TERMS: " + (", ".join(packet["allowed_terms"]) or "none"))
    lines.append("REQUIRED (must be reflected in meaning): " + ("; ".join(packet["required"]) or "none"))
    lines.append("FORBIDDEN (must NOT appear): " + "; ".join(packet["forbidden"]))
    lines += [
        "",
        "CANDIDATE:",
        candidate,
        "",
        "Answer with EXACTLY one word on the first line: ENTAILED or NOT_ENTAILED.",
        "Say ENTAILED only if the candidate asserts nothing beyond ALLOWED, keeps",
        "all REQUIRED, and contains no FORBIDDEN. If unsure, answer NOT_ENTAILED.",
    ]
    return "\n".join(lines)


def verify_entailment(candidate: str, packet: dict, judge) -> str:
    """Return one of 'entailed' | 'not_entailed' | 'judge_failed' (fail-closed).

    Any judge exception, empty/malformed/uncertain output, or a non-ENTAILED
    verdict rejects the candidate; only a clean ENTAILED passes.
    """
    try:
        raw = judge(_entailment_prompt(candidate, packet))
    except Exception:
        return "judge_failed"
    if not isinstance(raw, str) or not raw.strip():
        return "judge_failed"
    token = raw.strip().split()[0].upper().strip(".:!,")
    if token == "ENTAILED":
        return "entailed"
    if token in ("NOT_ENTAILED", "NOT"):
        return "not_entailed"
    return "judge_failed"
```

Also extend the module `__all__` to include `"build_grounding_packet"`, `"verify_entailment"`.

- [ ] **Step 4:** `python -m pytest tests/test_voice.py -k "grounding or entailment" -q` → PASS; full `-q` → all pass.

- [ ] **Step 5: commit:**

```bash
git add src/pneuma_lab/voice/verify.py tests/test_voice.py
git commit -m "$(cat <<'EOF'
feat(voice): structured grounding packet + fail-closed entailment verdict
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `stream.py` — seven voice statuses + judge wiring

**Files:** Modify `src/pneuma_lab/voice/stream.py`, `schemas/thought-stream.schema.json`; update one existing test in `tests/test_voice.py`; add new tests.

- [ ] **Step 1: expand the schema enum.** In `schemas/thought-stream.schema.json`, replace the `rendered_thought.voice_status` enum with exactly:

```json
                    "enum": [
                        "deterministic_only", "voiced", "skin_unavailable",
                        "generation_failed", "rejected_syntactic",
                        "rejected_entailment", "judge_failed"
                    ]
```

- [ ] **Step 2: update the existing drift test.** In `tests/test_voice.py`, `test_voiced_falls_back_on_rejected_drift` currently asserts `voice_status == "voiced_rejected_fell_back"`. Change that assertion to `"rejected_syntactic"`:

```python
    assert any(r["voice_status"] == "rejected_syntactic" for r in on["rendered"])
```

- [ ] **Step 3: failing tests** (append):

```python
from pneuma_lab.voice import ollama as OL


class _RaiseSkin:
    def __init__(self, exc):
        self._exc = exc
    def voice_tick(self, atoms, rendered):
        raise self._exc


def test_status_skin_unavailable():
    on = ST.voice_run(load_jsonl(_FIXTURE), skin=_RaiseSkin(OL.OllamaUnavailable("down")))
    assert all(r["voice_status"] == "skin_unavailable" for r in on["rendered"])
    assert all(r["text_voiced"] is None for r in on["rendered"])


def test_status_generation_failed():
    on = ST.voice_run(load_jsonl(_FIXTURE), skin=_RaiseSkin(ValueError("boom")))
    assert all(r["voice_status"] == "generation_failed" for r in on["rendered"])


def test_status_rejected_entailment_and_judge_failed_and_voiced():
    frames = load_jsonl(_FIXTURE)
    ref = VZ.ReferenceVoiceSkin()  # faithful, passes verify_voiced
    not_ent = ST.voice_run(frames, skin=ref, judge=lambda p: "NOT_ENTAILED")
    assert any(r["voice_status"] == "rejected_entailment" for r in not_ent["rendered"])
    jf = ST.voice_run(frames, skin=ref, judge=lambda p: (_ for _ in ()).throw(RuntimeError()))
    assert any(r["voice_status"] == "judge_failed" for r in jf["rendered"])
    ok = ST.voice_run(frames, skin=ref, judge=lambda p: "ENTAILED")
    assert any(r["voice_status"] == "voiced" for r in ok["rendered"])
    assert any(r["text_voiced"] for r in ok["rendered"])


def test_judge_and_skin_cannot_inflate_level():
    frames = load_jsonl(_FIXTURE)
    import json
    bare = ReplayHarness(ReferencePsyche()).run(frames).evidence_frame
    on = ST.voice_run(frames, skin=VZ.ReferenceVoiceSkin(), judge=lambda p: "ENTAILED")
    assert json.dumps(on["evidence_frame"], sort_keys=True) == json.dumps(bare, sort_keys=True)
```

- [ ] **Step 4:** run the new + updated tests → FAIL (judge param unknown / statuses absent).

- [ ] **Step 5: edit `stream.py`.** Add imports at top:

```python
from .ollama import OllamaUnavailable
from .verify import build_grounding_packet, verify_entailment, verify_voiced
```

(remove the old lone `from .verify import verify_voiced` if present — the combined import above replaces it).

Replace `_render_tick` with:

```python
def _mark(dicts, status):
    for d in dicts:
        d["text_voiced"] = None
        d["voice_status"] = status
    return dicts


def _render_tick(atoms, skin, judge=None):
    rendered = [_render.render(a) for a in atoms]
    dicts = [asdict(r) for r in rendered]
    if skin is None or not rendered:
        return dicts
    atom_dicts = [asdict(a) for a in atoms]
    try:
        candidate = skin.voice_tick(atom_dicts, dicts)
    except OllamaUnavailable:
        return _mark(dicts, "skin_unavailable")
    except Exception:
        return _mark(dicts, "generation_failed")
    ok, _reasons = verify_voiced(candidate, [d["text_deterministic"] for d in dicts])
    if not ok:
        return _mark(dicts, "rejected_syntactic")
    if judge is not None:
        verdict = verify_entailment(candidate, build_grounding_packet(atom_dicts, dicts), judge)
        if verdict == "not_entailed":
            return _mark(dicts, "rejected_entailment")
        if verdict != "entailed":
            return _mark(dicts, "judge_failed")
    for d in dicts:
        d["text_voiced"] = candidate
        d["voice_status"] = "voiced"
    return dicts
```

Thread `judge` through `_assemble` and both run functions: add `judge=None` to `_assemble(...)` signature and pass it to `_render_tick(atoms, skin, judge)`; add `judge=None` to `voice_run(...)` and `voice_run_paired(...)` signatures and pass `judge=judge` into their `_assemble(...)` calls.

- [ ] **Step 6:** `python -m pytest tests/test_voice.py -q` → all pass (including the updated drift test). `python -m pytest tests/test_schema_loads.py -q` → pass (schema still valid).

- [ ] **Step 7: commit:**

```bash
git add src/pneuma_lab/voice/stream.py schemas/thought-stream.schema.json tests/test_voice.py
git commit -m "$(cat <<'EOF'
feat(voice): seven-value voice-status taxonomy + fail-closed judge wiring
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `__main__.py` — CLI flags

**Files:** Modify `src/pneuma_lab/voice/__main__.py`; Test `tests/test_voice.py`.

- [ ] **Step 1: failing test** (append; injects a fake generate so no network is used):

```python
def test_cli_llm_skin_with_fake_generate(tmp_path, monkeypatch):
    from pneuma_lab.voice import ollama as OL
    monkeypatch.setattr(OL, "ollama_generate", lambda prompt, **k: "elaborated: " + prompt.split(chr(10))[-1])
    from pneuma_lab.voice.__main__ import main
    rc = main([str(_IV_DIR / "clamp_tension.jsonl"), "--paired", "--skin", "llm",
               "--ollama-model", "testmodel", "--no-entailment", "--out", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "stream.md").exists()
```

- [ ] **Step 2:** `python -m pytest tests/test_voice.py -k llm_skin -q` → FAIL (`--skin llm` invalid choice).

- [ ] **Step 3: edit `__main__.py`.** Update imports:

```python
from . import config as _config
from . import ollama as _ollama
from . import voiced as _voiced
from .stream import voice_run, voice_run_paired
```

Add arguments:

```python
    parser.add_argument("--skin", choices=("none", "reference", "llm"), default="none")
    parser.add_argument("--ollama-model", default=None, help="voice model override (else env/config/llama3.1)")
    parser.add_argument("--judge-model", default=None, help="judge model override")
    parser.add_argument("--ollama-host", default=None, help="Ollama host URL override")
    parser.add_argument("--no-entailment", action="store_true", help="skip the local-LLM entailment judge for --skin llm")
```

Build skin + judge:

```python
    skin = None
    judge = None
    if args.skin == "reference":
        skin = _voiced.ReferenceVoiceSkin()
    elif args.skin == "llm":
        host = _config.resolve_ollama_host(args.ollama_host)
        skin = _ollama.OllamaVoiceSkin(model=_config.resolve_voice_model(args.ollama_model), host=host)
        if not args.no_entailment:
            judge = _ollama.make_ollama_judge(model=_config.resolve_judge_model(args.judge_model), host=host)
```

Dispatch (pass `judge=judge` too):

```python
    factory = _factory(args.subject)
    if args.paired:
        stream = voice_run_paired(load_jsonl(args.fixture), subject_factory=factory, skin=skin, judge=judge)
    else:
        stream = voice_run(load_jsonl(args.fixture), subject_factory=factory, skin=skin, judge=judge)
```

Keep the existing `write_transcript` / `--monitor` / print / `return 0`.

- [ ] **Step 4:** `python -m pytest tests/test_voice.py -k llm_skin -q` → PASS; full `-q` → all pass.

- [ ] **Step 5: commit:**

```bash
git add src/pneuma_lab/voice/__main__.py tests/test_voice.py
git commit -m "$(cat <<'EOF'
feat(voice): CLI --skin llm + model/host flags + --no-entailment
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Monitor v2 — deterministic panel + control-room visual pass

**Files:** Modify `src/pneuma_lab/voice/monitor.py`; Test `tests/test_voice.py`.

**Data contract (build this first, it is what the tests pin):** `monitor_payload` gains a deterministic per-tick `panel` derived only from that tick's atoms/receipts.

- [ ] **Step 1: failing tests** (append):

```python
def test_monitor_payload_has_panel():
    s = ST.voice_run_paired(load_jsonl(_IV_DIR / "clamp_tension.jsonl"))
    payload = M.monitor_payload(s)
    assert payload["ticks"], "no ticks"
    for t in payload["ticks"]:
        p = t["panel"]
        for key in ("pressure", "winner", "salience", "dominant_affect", "scar_strength", "predicted_error", "credit_counts", "evidence_level"):
            assert key in p, key


def test_monitor_still_byte_deterministic_and_self_contained():
    frames = load_jsonl(_FIXTURE)
    a = M.render_html(ST.voice_run(frames))
    b = M.render_html(ST.voice_run(frames))
    assert a == b
    low = a.lower()
    for bad in ("http://", "https://", "cdn.", "<link", "src=\"http"):
        assert bad not in low, bad
    assert "thought-stream-data" in low and "panel" in low


def test_monitor_voiced_text_not_in_determinism_scope():
    # A fixture skin makes the voiced text a fixed string; monitor with it renders
    # the voiced text but is a NON-canonical view (not asserted byte-stable here).
    frames = load_jsonl(_FIXTURE)
    class FixSkin:
        def voice_tick(self, atoms, rendered):
            return " ".join(r["text_deterministic"] for r in rendered)
    s = ST.voice_run(frames, skin=FixSkin())
    html = M.render_html(s)
    assert "<!doctype html>" in html.lower()
```

- [ ] **Step 2:** `python -m pytest tests/test_voice.py -k "panel or byte_deterministic or determinism_scope" -q` → FAIL.

- [ ] **Step 3: implement the panel in `monitor.py`.** Add this helper and call it from `monitor_payload` so each tick dict gains `"panel"`:

```python
def _tick_panel(lines: list[dict], evidence_level: int) -> dict:
    pressure = None
    winner = None
    salience: dict = {}
    dominant_affect = None
    scar_strength = None
    predicted_error = None
    credit_counts: dict = {}
    for ln in lines:
        credit_counts[ln["credit_status"]] = credit_counts.get(ln["credit_status"], 0) + 1
        for r in ln.get("receipts", []):
            fp, val = r.get("field_path", ""), r.get("value")
            if fp.startswith("control_pressure.") and not fp.endswith("authority_tier") and isinstance(val, (int, float)):
                pressure = float(val)
            elif fp == "workspace_broadcast.winning_faculty":
                winner = val
            elif fp.startswith("salience_scores.") and isinstance(val, (int, float)):
                salience[fp.split(".", 1)[1]] = float(val)
            elif fp.startswith("shift.") and not fp.endswith(".from") and isinstance(val, (int, float)):
                dominant_affect = {"dim": fp.split(".", 1)[1], "value": float(val)}
            elif fp == "psyche_state.derived_signals.scar_strength" and isinstance(val, (int, float)):
                scar_strength = float(val)
            elif fp == "psyche_state.self_model.predicted_error" and isinstance(val, (int, float)):
                predicted_error = float(val)
    return {
        "pressure": pressure,
        "winner": winner,
        "salience": salience,
        "dominant_affect": dominant_affect,
        "scar_strength": scar_strength,
        "predicted_error": predicted_error,
        "credit_counts": credit_counts,
        "evidence_level": evidence_level,
    }
```

In `monitor_payload`, after building each tick's `lines`, attach `"panel": _tick_panel(lines, stream["evidence_level"])` to the tick dict (so a tick is `{"tick": t, "lines": [...], "panel": {...}}`).

- [ ] **Step 4: the visual pass.** The monitor template must render the panel + a timeline. Use the `ui-ux-pro-max` skill (direction) then the `frontend-design` skill (implementation) to elevate the `_TEMPLATE` into a control-room layout: **left** the thought stream (show `text_voiced` italicised with a small "elaborated" tag when present, else `text_deterministic`; credit-coloured left border; receipts expand on click via text nodes), **right** a sticky internal-state panel driven by the active tick's `panel` (salience race bars, a pressure gauge, an affect chip, a credit-mix bar, the evidence badge + family dots), **bottom** a timeline scrubber (one cell per tick) that sets the active tick and updates the panel; Play steps through ticks. HARD CONSTRAINTS the design must keep (verified by the Step 1 tests + a re-run): entirely self-contained (inline CSS/JS, system fonts, **no external URLs/CDN/link/remote src**); the JSON island keeps the `data.replace("</", "<\\/")` neutralisation; **all free-text (thought text + receipt values) rendered via `textContent`/`createTextNode`, never `innerHTML`**; `render_html` stays a pure function of `stream` so the deterministic-mode output is byte-identical across two renders. Keep `monitor_payload`, `render_html`, `write_monitor` signatures unchanged.

- [ ] **Step 5:** `python -m pytest tests/test_voice.py -k "panel or monitor or byte_deterministic or determinism_scope" -q` → PASS; full `python -m pytest tests/ -q` → no regressions. Generate one and eyeball (build/ gitignored, don't commit): `python -m pneuma_lab.voice fixtures/interventions/clamp_tension.jsonl --paired --monitor --out build/voice/_v2check` — open `monitor.html`, confirm the panel + timeline render and update on scrub.

- [ ] **Step 6: commit:**

```bash
git add src/pneuma_lab/voice/monitor.py tests/test_voice.py
git commit -m "$(cat <<'EOF'
feat(voice): monitor v2 — deterministic internal-state panel + timeline
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Docs, status, config example

**Files:** Create `pneuma-voice.config.json.example`; Modify `docs/pneuma-voice-v0.md`, `docs/project-status.json`, `src/pneuma_lab/status.py` (only if the checker requires it), `CLAUDE.md` (one line).

- [ ] **Step 1:** create `pneuma-voice.config.json.example` at repo root:

```json
{
    "voice_model": "llama3.1",
    "judge_model": "llama3.1",
    "ollama_host": "http://localhost:11434"
}
```

- [ ] **Step 2:** `docs/pneuma-voice-v0.md` — add a "## v0.1 — local elaboration (Ollama voice + entailment judge + monitor v2)" section covering: the dependency-free local Ollama voiced skin (`OllamaVoiceSkin`, `--skin llm`), the grounding-packet fail-closed entailment judge, the seven `voice_status` values and what each preserves, the model-resolution chains (CLI→env→config→`llama3.1`, voice/judge independent), monitor v2 (panel + timeline), and the canonical/non-canonical boundary (voiced prose is optional + non-deterministic; scorer stays prose-blind; no Level claim). ~35-55 lines.

- [ ] **Step 3:** `docs/project-status.json` — add `src/pneuma_lab/voice/config.py`, `ollama.py` (and note verify/stream/monitor extended) to `pneuma_voice_shadow.evidence_refs`. Keep `status: implemented`, `scope: internal_harness`, no Level claim. If `python -m pneuma_lab.status --check` fails, adjust `src/pneuma_lab/status.py` minimally per the existing registry pattern; re-run → PASS.

- [ ] **Step 4:** `CLAUDE.md` — extend the `src/pneuma_lab/voice/` Tree Guide bullet with one clause: optional local Ollama elaboration (voiced skin + fail-closed entailment judge) + monitor v2, dependency-free, non-canonical prose, scorer stays prose-blind.

- [ ] **Step 5: verify:** `python -m pytest tests/ -q` (no regressions), `python -m pneuma_lab.status --check` (PASS), `python -m pneuma_lab.demo` (exit 0), `git diff --check` (clean).

- [ ] **Step 6: commit:**

```bash
git add pneuma-voice.config.json.example docs/pneuma-voice-v0.md docs/project-status.json src/pneuma_lab/status.py CLAUDE.md
git commit -m "$(cat <<'EOF'
docs(voice): PneumaVoice-v0.1 local-elaboration docs, status, config example
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Self-review

**Spec coverage:** config resolution/independent chains (T1); dependency-free Ollama client + skin + judge (T2); structured grounding packet + fail-closed entailment (T3); seven voice statuses + judge wiring + schema (T4); CLI flags + injected-fake test (T5); deterministic panel + control-room monitor + determinism/self-contained constraints (T6); docs/status/config-example + canonical/non-canonical framing (T7). Anti-gaming re-asserted in T4 (`test_judge_and_skin_cannot_inflate_level`). ✓

**No network in tests:** every Ollama path is behind an injected fake `generate`/`judge` (T2, T5) or a raising fake skin/judge (T4). No test contacts a real server. ✓

**Canonical boundary:** determinism tests run in deterministic mode / fixture skin (T4 anti-gaming, T6 byte-determinism); voiced LLM text is never asserted byte-stable (T6 `determinism_scope`). ✓

**Type consistency:** `resolve_voice_model/resolve_judge_model/resolve_ollama_host(cli=None)`; `ollama_generate(prompt, *, model, host, timeout, temperature, options)`; `OllamaVoiceSkin(*, model, host, timeout, temperature, generate)`; `make_ollama_judge(*, model, host, timeout, generate)`; `build_grounding_packet(atoms, rendered)`; `verify_entailment(candidate, packet, judge)->str`; `_render_tick(atoms, skin, judge=None)`; `voice_run(..., skin=None, judge=None)`; `voice_run_paired(..., skin=None, judge=None)`; `monitor_payload(stream)` (tick gains `panel`). Consistent across tasks. ✓

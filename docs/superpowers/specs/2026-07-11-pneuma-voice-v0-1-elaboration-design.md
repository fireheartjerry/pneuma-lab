# Pneuma Voice-v0.1 — Local Elaboration Layer (Ollama voice, entailment judge, monitor v2) — Design Spec

**Date:** 2026-07-11
**Status:** approved (brainstorming); proceeding to plan + implementation
**Advances:** completes the three PneumaVoice-v0 follow-ups — an optional, local,
free **Ollama voiced skin**; a **local-LLM entailment judge** over a structured
grounding packet; and a polished **monitor v2** with a live internal-state panel
and timeline. All additive, dependency-free, and presentation-layer only.

---

## 1. Purpose and the canonical / non-canonical boundary

The deterministic voice already ships. This layer lets a **local** model (Ollama,
free, offline) _elaborate_ the grounded thoughts into more natural prose, and adds
a local judge that checks that elaboration against an explicit grounding packet.
It is presentation-layer elaboration over grounded deterministic state — **no
consciousness, sentience, autonomy, or Level claim.**

**Canonical (authoritative, byte-deterministic):** deterministic per-tick state,
`ThoughtAtom`s, deterministic `RenderedThought.text_deterministic`, the evidence
sidecar, the monitor **payload**, and everything the scorer reads. These are
reproducible byte-for-byte and are what tests pin.

**Non-canonical (optional, non-deterministic):** `RenderedThought.text_voiced`
produced by the Ollama skin, and any transcript/monitor artifact that embeds it.
We do **not** claim the voiced output is byte-deterministic. A monitor/transcript
generated with a live model is a non-canonical view; byte-determinism is asserted
only in deterministic mode (skin off) or with a fixture skin producing fixed text.

**Invariant (unchanged):** the `ConsciousnessEvidenceScorer` and the anti-gaming
guarantee remain completely **prose-blind**. No voice/judge code imports or calls
the scorer; the evidence frame is read verbatim and echoed. The whole elaboration
layer has zero causal path to a level.

---

## 2. Components (all in `src/pneuma_lab/voice/`)

- `config.py` — model/host resolution. Separate chains for the **voice** model and
  the **judge** model (even though both default the same). Each resolves
  **CLI → environment → project config file → fallback**:
    - voice: `--ollama-model` → `PNEUMA_VOICE_MODEL` → config `voice_model` → `"llama3.1"`
    - judge: `--judge-model` → `PNEUMA_JUDGE_MODEL` → config `judge_model` → `"llama3.1"`
    - host: `--ollama-host` → `PNEUMA_OLLAMA_HOST` → config `ollama_host` → `"http://localhost:11434"`
    - The project config file is an **optional** JSON at `$PNEUMA_VOICE_CONFIG` (or a
      default repo-root `pneuma-voice.config.json`); absent file → skip that tier.
      `json` only (stdlib); never required; not committed by default.
- `ollama.py` — the dependency-free local client + skin.
    - `ollama_generate(prompt, *, model, host, timeout, temperature=0.7, options=None) -> str`
      via `urllib.request` POST `host + "/api/generate"` body
      `{"model", "prompt", "stream": false, "options": {...}}`; returns
      `json["response"]`. Typed failures: `OllamaUnavailable` (connection refused /
      host unreachable / model-not-found 404) vs `OllamaGenerationError` (other
      HTTP error, timeout, malformed/missing `response`).
    - `OllamaVoiceSkin(model, host, timeout, temperature, generate=ollama_generate)`
      implements `voice_tick(atoms, rendered) -> str`. The `generate` seam is
      injectable so tests never hit the network.
    - `make_ollama_judge(model, host, timeout, generate=ollama_generate) -> Callable[[str], str]`
      (temperature 0). Returns a plain `judge(prompt) -> str` callable.
- `verify.py` (extend) — the structured grounding packet + entailment.
    - `build_grounding_packet(atoms, rendered) -> dict` with explicit:
        - `allowed_numbers` (sorted numeric tokens in the deterministic texts),
        - `allowed_terms` (sorted snake_case/dotted identifiers: faculties,
          dimensions, motif/experiment ids),
        - `facts` (the deterministic sentences — the exact grounded claims),
        - `required` (claims that MUST be reflected: the `architecture-only`
          hedge for each uncredited-family atom; `not a consciousness claim`
          for a boundary atom),
        - `forbidden` (the ontological over-claim markers).
    - existing `verify_voiced(text, source_texts) -> (bool, reasons)` stays as the
      deterministic syntactic gate (numbers/identifiers/forbidden/hedge/length).
    - `verify_entailment(candidate, packet, judge) -> str` returns exactly one of
      `"entailed"`, `"not_entailed"`, `"judge_failed"`. It builds a compact prompt
      **from the packet** (allowed / required / forbidden — NOT raw source), calls
      the judge, and **fails closed**: timeout, malformed output, refusal,
      uncertainty, or anything other than a clean `ENTAILED` verdict →
      `"judge_failed"` (or `"not_entailed"` on an explicit `NOT_ENTAILED`). Any
      exception from the judge is caught → `"judge_failed"`.
- `stream.py` (extend) — resilient skin + judge wiring with distinct statuses (§3).
- `monitor.py` (extend) — deterministic per-tick `panel` in the payload + a
  control-room template with a live internal-state panel and timeline (§4).
- `__main__.py` (extend) — CLI flags (§5).
- `schemas/thought-stream.schema.json` — expand the `voice_status` enum (§3).

---

## 3. Voice-status taxonomy (distinct fallbacks)

`RenderedThought.voice_status` becomes one of:

| status                | meaning                                                      | text_voiced |
| --------------------- | ------------------------------------------------------------ | ----------- |
| `deterministic_only`  | no skin requested                                            | null        |
| `voiced`              | generated, passed syntactic **and** entailment (if judged)   | set         |
| `skin_unavailable`    | skin requested but backend unreachable (`OllamaUnavailable`) | null        |
| `generation_failed`   | generate() errored/timed out (`OllamaGenerationError`/other) | null        |
| `rejected_syntactic`  | failed `verify_voiced`                                       | null        |
| `rejected_entailment` | judge returned `NOT_ENTAILED`                                | null        |
| `judge_failed`        | judge timeout/malformed/refusal/uncertain/error              | null        |

Only `voiced` carries `text_voiced`; every other status preserves the deterministic
rendering. `stream._render_tick(atoms, skin, judge=None)`:

1. `skin is None` → `deterministic_only`.
2. `skin.voice_tick(...)` raises `OllamaUnavailable` → `skin_unavailable`; any other
   exception → `generation_failed`.
3. `verify_voiced(candidate, [text_deterministic])` fails → `rejected_syntactic`.
4. `judge` set → `verify_entailment(candidate, packet, judge)`:
   `"not_entailed"` → `rejected_entailment`; `"judge_failed"` → `judge_failed`;
   `"entailed"` → continue.
5. else → `voiced` (set `text_voiced`).

The whole method is wrapped so no skin/judge failure can abort a run — a failed
tick simply keeps its canonical deterministic text. The schema enum lists all
seven values (replacing the old catch-all `voiced_rejected_fell_back`).

---

## 4. Monitor v2 — live internal-state panel + timeline

`monitor_payload(stream)` gains a deterministic per-tick `panel` derived purely
from that tick's atoms/receipts (no new frame access, no LLM):

- `pressure` (from the `pressure` atom's value, else null),
- `winner` + `salience` (from the `competition` atom's `salience_scores.*`),
- `dominant_affect` `{dim, value}` (from the `shift` atom),
- `scar_strength` (from `memory_activation`), `predicted_error` (from `uncertainty`),
- `credit_counts` (tally of the tick's atom `credit_status`),
- `evidence_level` (run-level, echoed per tick for the trajectory).

The template becomes a self-contained control room: **left** the thought stream
(voiced text shown when present, italicised, with a "elaborated by <model>" tag;
deterministic text otherwise), **right** a sticky panel (salience race bars,
pressure gauge, affect chip, credit mix, evidence badge + family dots), **bottom**
a timeline scrubber that selects a tick and updates the panel; Play animates
through ticks. Visual pass via `ui-ux-pro-max` → `frontend-design`. Inline CSS/JS,
system fonts, no external requests; `</` neutralised in the JSON island; free-text
rendered via text nodes.

**Determinism:** with `skin=None` (or a fixture skin) the payload and HTML are
byte-deterministic — that is what the tests pin. A monitor built with a live model
embeds non-canonical voiced text and is explicitly not byte-guaranteed.

---

## 5. CLI

`python -m pneuma_lab.voice <fixture> [--paired] [--monitor]
[--skin {none,reference,llm}] [--ollama-model M] [--judge-model M]
[--ollama-host URL] [--no-entailment]`

- `--skin llm` builds `OllamaVoiceSkin(resolve_voice_model(cli), resolve_ollama_host(cli))`
  and (unless `--no-entailment`) a judge from `resolve_judge_model(cli)`.
- `--skin reference` uses the deterministic `ReferenceVoiceSkin`, no judge.
- `--skin none` (default) → deterministic.
- Model/host come from the resolution chains in §2; the CLI only passes the
  explicit override (or `None`).

---

## 6. Testing (no network, fail-closed proven)

- `config.py`: resolution order per chain (monkeypatch env + a temp config file);
  fallback to `llama3.1`; voice vs judge resolved independently.
- `ollama.py`: `ollama_generate` parses a stubbed `urlopen` response; maps a
  connection error → `OllamaUnavailable`, an HTTP 500/timeout/malformed →
  `OllamaGenerationError`. `OllamaVoiceSkin` with an injected fake `generate`
  returns fused prose; with a `generate` that raises `OllamaUnavailable`, the skin
  propagates it.
- `verify.py`: `build_grounding_packet` yields the allowed/required/forbidden sets
  from real atoms; `verify_entailment` returns `entailed` for a faithful candidate
  (fake judge → "ENTAILED"), `not_entailed` for "NOT_ENTAILED", and `judge_failed`
  for malformed/empty/uncertain output and for a judge that raises.
- `stream.py`: each of the seven statuses is reachable with injected fakes —
  a fake skin raising `OllamaUnavailable` → `skin_unavailable`; raising other →
  `generation_failed`; a drift skin → `rejected_syntactic`; a faithful skin + a
  `NOT_ENTAILED` judge → `rejected_entailment`; + a raising judge → `judge_failed`;
    - an `ENTAILED` judge → `voiced`. **Anti-gaming**: with any skin/judge the echoed
      `evidence_frame` is byte-identical to the bare harness run.
- `monitor.py`: byte-determinism in deterministic mode; `panel` present with the
  right keys; self-contained (no external URLs); a fixture-skin voiced monitor
  contains the voiced text but is **not** part of the byte-determinism assertion.
- No test contacts a real Ollama server. Full suite + `status --check` +
  `python -m pneuma_lab.demo` stay green.

---

## 7. Docs + status

- `docs/pneuma-voice-v0.md` — add a "v0.1 — local elaboration" section: the Ollama
  voiced skin (local, free, optional, dependency-free), the grounding-packet
  entailment judge (fail-closed), the seven voice statuses, monitor v2, the
  canonical/non-canonical boundary, and the model-resolution chains. Reaffirm the
  prose-blind scorer + no-Level-claim posture.
- `docs/project-status.json` — add the new files to `pneuma_voice_shadow.evidence_refs`;
  keep `status: implemented`, `scope: internal_harness`, no Level claim.
- A short `pneuma-voice.config.json.example` at repo root documenting the optional
  config keys (the real file stays uncommitted/local).

---

## 8. Out of scope (YAGNI)

- Any hosted/paid inference; any hard dependency (no `anthropic`/`ollama` SDK — raw
  HTTP via stdlib).
- Streaming token display; multi-model ensembling; caching voiced output.
- Re-scoring, or any change to the scorer / psyche / paired runner / existing
  frames. `credit_status` stays display-only; the scorer stays prose-blind.
- Any consciousness / sentience / autonomy / Level claim.

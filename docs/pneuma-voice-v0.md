# PneumaVoice-v0 — the expressive surface (Phase A)

> **Posture.** This is a read-only, additive rendering surface. It makes no
> evidence-level claim, changes no evidence, and grants no authority. See
> [`consciousness-levels.md`](consciousness-levels.md).

## 1. What it is

`src/pneuma_lab/voice/` turns per-tick psyche output frames into a
deterministic, receipt-bound **thought stream**:

```
output frames  →  ThoughtAtoms  →  RenderedThought + evidence sidecar
```

Phase A is fully deterministic (template-rendered prose, no model call). A
future Phase B may add a verified LLM voiced skin; Phase A does not depend on
one.

## 2. ThoughtAtom vs RenderedThought

- **`ThoughtAtom`** (`atoms.py`) is a pure semantic fact plus receipts — no
  prose. It carries `type`, `run_id`, `tick`, `timestamp`, `receipts`
  (field-path/value pairs into the real output frames), `intensity`,
  `crediting_family`, `credit_status`, and `min_level`. An atom must exist,
  receipt-bound, before any prose touches it.
- **`RenderedThought`** (`render_deterministic.py`) is the only place prose
  lives: `text_deterministic` (always present), `text_voiced` (`None` unless a
  skin is attached and its candidate is accepted — populated only when
  `voice_status` is `"voiced"`; always non-canonical), and `voice_status`
  (`"deterministic_only"` with no skin; one of seven granular values once a
  skin is attached — see §8 and the v0.1 section below).

## 3. The 14-type vocabulary

`atoms.ATOM_TYPES` names all 14 planned atom types and maps each to its
crediting indicator family (`ATOM_FAMILY`, `None` for families with no direct
9-family mapping) and minimum evidence level (`MIN_LEVEL`). Phase A
implements extraction + rendering for 9 of them:

    appraisal, shift, pressure, self_report, competition,
    memory_activation, uncertainty, counterfactual, boundary

Deferred: `instinct`, `attention`, `prediction_error`, `dissonance` (Phase A
render falls back to a generic renderer rather than raising), and
`intervention_result` (Phase B — it requires an executed intervention and is
excluded from passive replay by construction).

## 4. The observed-vs-credited gate

Observed atoms are **always shown** — the gate (`gate.py`) only ever drops
sub-epsilon-intensity atoms, never anything for lack of credit. Separately,
each atom carries a `credit_status` — a display label read **verbatim** from
the run's `ConsciousnessEvidenceFrame` per-family `status` (via
`atoms.credit_status_for`). The renderer uses `credit_status` only to choose
its register: atoms from a family that is not `evidenced` /
`intervention_backed` are hedged in the rendered prose as
_"architecture-only, not promotable evidence"_. `credit_status` **never**
feeds the scorer — it is read-only, one-way, downstream of the evidence
frame.

## 5. Conservative science, anthropomorphic voice

The renderer may use first-person phrasing as an **interface convention**
(mirroring the grounded-self-report style), never as an ontological claim of
experience. `render_deterministic.scrub_forbidden` is the backstop: it
strips phenomenology-adjacent phrasing (`"I feel"`, `"I suffer"`,
`"sentient"`, `"phenomenal"`, `"conscious experience"`, `"qualia"`, and
contraction/possessive variants) from any rendered text before it ships,
replacing removed spans with `[filtered]`.

## 6. Anti-gaming invariant

The evidence scorer never reads voice prose — there is no code path from
`voice/` back into `evals/` or `interventions/runner.py`. `stream.voice_run`
echoes the run's `ConsciousnessEvidenceFrame` unchanged in its output
(`evidence_frame`); `test_voice_never_alters_the_evidence_frame` asserts that
echo is byte-identical (via `json.dumps(..., sort_keys=True)`) to a bare
`ReplayHarness` run over the same frames. Voice is a read-only view, not a
second scorer.

## 7. The transcript surface

`transcript.write_transcript(stream, out_dir)` writes three byte-deterministic
files:

- `stream.md` — human-readable rendered thought stream;
- `stream.jsonl` — one JSON object per tick;
- `sidecar.json` — the receipts/credit/family-status evidence sidecar
  (`sidecar.build_sidecar`), validated against
  `schemas/thought-stream.schema.json` (`x-pneuma-schema-kind:
expressive_view`).

Run it directly:

```txt
python -m pneuma_lab.voice fixtures/sample_run.jsonl --out build/voice/demo --subject reference
python -m pytest tests/test_voice.py -q
```

`--subject` selects `reference` (`ReferencePsyche`, richer atom set) or
`baseline` (`BaselinePsycheSubject`, intentionally thinner).

## 8. Phase B — verified voiced skin + tested counterfactuals

Phase B adds a second, optional prose register over the same atoms/receipts —
it never changes what is extracted or how it is credited.

- **`VoiceSkin` protocol + skins** (`voiced.py`). A `VoiceSkin` exposes
  `voice_tick(atoms, rendered) -> str`. `ReferenceVoiceSkin` is the
  deterministic default: it fuses the tick's `text_deterministic` lines into
  one paragraph with no model call, so it is byte-reproducible.
  `LLMVoiceSkin` is a thin adapter around a caller-supplied `generate(prompt)`
  callable — it builds the prompt from the same deterministic lines and does
  not itself talk to any provider.
- **The `verify_voiced` gate** (`verify.py`) is a syntactic + heuristic check
  run on every voiced candidate before it can replace the deterministic text:
  every number and snake_case/dotted identifier in the candidate must already
  appear in the deterministic source lines, no forbidden ontological claim
  (`scrub_forbidden`) may be introduced, the architecture-only hedge must
  survive if the source carried one, and the candidate must not grossly
  expand length versus the source. This is **not** a semantic-entailment
  check — that remains future work; `verify_voiced` only bounds surface
  drift.
- **Deterministic fallback.** If `verify_voiced` rejects a candidate, the tick
  keeps `text_deterministic` and its `voice_status` becomes
  `"rejected_syntactic"` (or one of the other non-`"voiced"` statuses — see
  the v0.1 section below) — the stream never ships unverified prose.
- **`intervention_result` + `voice_run_paired`** (`extract.py`, `stream.py`).
  `voice_run_paired` drives a `PairedReplayRunner`, renders the treated arm
  like `voice_run`, and appends `intervention_result` atoms — built from the
  paired report's `observed_delta`/`experiment_id`/null result — to the final
  tick. This is how the stream narrates a **tested** counterfactual, in
  contrast to the passive-replay `counterfactual` atom, which is explicitly
  labeled "(Predicted, not tested.)".
- **Anti-gaming invariant, reaffirmed.** The skin cannot inflate the level:
  `test_skin_cannot_inflate_the_level` asserts the echoed `evidence_frame` and
  `evidence_level` are byte-identical whether or not a skin is attached: only
  `rendered[*].text_voiced`/`voice_status` differ.

CLI flags: `--paired` (run the paired replay and narrate the tested
counterfactual) and `--skin {none,reference,llm}` (attach `ReferenceVoiceSkin`
or, from v0.1, the local-Ollama `OllamaVoiceSkin` — see the v0.1 section
below; default `none` keeps Phase A's deterministic-only output).

## Phase C — HTML mind monitor

`monitor.py` renders the same stream as a self-contained, byte-deterministic
HTML page: one inline document with no external requests (CSP-safe, safe to
share as a static file). A sorted-key JSON island of the stream is embedded in
the page; the runtime only reads that island to render — it does not touch
`evals/` or the scorer, preserving the anti-gaming invariant in §6.

- Plays the thought stream tick-by-tick (a "Play" control reveals ticks in
  order; a "Show all" control reveals everything immediately).
- Colour-codes each line's left border by `credit_status`: blue for
  `evidenced`, green for `intervention_backed`, amber for `architecture_only`
  (and `attempted`), grey for `absent`.
- Receipts are collapsed by default and expand on click, listing each
  `field_path`/`value` pair the line is grounded in.
- The header shows the subject, mode, an evidence-level badge, and one status
  dot per indicator family (from the sidecar's `indicator_family_status`).

Produced via `monitor.write_monitor(stream, path)` (or `monitor.render_html
(stream)` for the raw string), or from the CLI with `--monitor`, which writes
`monitor.html` alongside `stream.md`/`stream.jsonl`/`sidecar.json`:

```txt
python -m pneuma_lab.voice fixtures/sample_run.jsonl --out build/voice/demo --monitor
```

## v0.1 — local elaboration (Ollama voice + entailment judge + monitor v2)

v0.1 answers §9's "future work" by wiring `LLMVoiceSkin.generate` to a real,
local model — while keeping voiced prose optional, non-canonical, and outside
the scorer's reach.

- **The local Ollama voiced skin** (`voice/ollama.py`, `OllamaVoiceSkin`) talks
  to a local Ollama HTTP server via stdlib `urllib` only — no SDK, no new
  dependency. It is optional (only used with `--skin llm`), local (no
  network egress beyond `localhost`/a configured host), and free. Like
  `ReferenceVoiceSkin`, it produces prose that is explicitly **non-canonical**:
  voiced text is never byte-deterministic across runs, unlike everything else
  the harness emits.
- **The structured grounding packet + fail-closed entailment judge.**
  `verify.build_grounding_packet(atoms, rendered)` extracts the only facts a
  paraphrase may assert: `allowed_numbers`, `allowed_terms`, `facts` (the
  deterministic source sentences), `required` claims (e.g. the
  architecture-only hedge, the "not a consciousness claim" boundary), and
  `forbidden` ontological-claim types. `verify.verify_entailment(candidate,
packet, judge)` sends this packet plus the candidate to a local-LLM judge and
  returns `"entailed"`, `"not_entailed"`, or `"judge_failed"` — **fail-closed**:
  a judge exception, a timeout, malformed output, a refusal, or any uncertain/
  non-`ENTAILED` token all resolve to a rejection. Only a clean `ENTAILED`
  verdict lets a candidate ship. Pass `--no-entailment` to skip the judge and
  keep only the syntactic `verify_voiced` gate.
- **The seven `voice_status` values.** Every non-`"voiced"` status keeps the
  canonical `text_deterministic` untouched — only `"voiced"` carries a
  populated `text_voiced`:
    - `deterministic_only` — no skin attached (Phase A default).
    - `voiced` — skin attached, candidate passed all gates; the only status with
      `text_voiced` populated.
    - `skin_unavailable` — the local Ollama backend was unreachable
      (`OllamaUnavailable`).
    - `generation_failed` — the skin raised during generation for any other
      reason.
    - `rejected_syntactic` — `verify_voiced` rejected the candidate (invented
      number/identifier, forbidden claim, dropped hedge, gross length
      expansion).
    - `rejected_entailment` — the entailment judge returned `not_entailed`.
    - `judge_failed` — the judge could not produce a clean verdict (exception,
      timeout, malformed/uncertain output).
- **Independent model resolution.** The voice model and the judge model are
  resolved **independently** (`voice/config.py`), each through the same
  four-tier order: CLI flag (`--ollama-model` / `--judge-model`) → environment
  (`PNEUMA_VOICE_MODEL` / `PNEUMA_JUDGE_MODEL`, plus `PNEUMA_OLLAMA_HOST` for
  the host) → an optional project config file (`$PNEUMA_VOICE_CONFIG` or
  `pneuma-voice.config.json`; see `pneuma-voice.config.json.example`) →
  fallback `"llama3.1"` (model) / `"http://localhost:11434"` (host). The
  config file is plain JSON, stdlib-only, and silently skipped if absent or
  malformed.
- **Monitor v2** (`voice/monitor.py`) adds a deterministic per-tick
  internal-state panel to the Phase C HTML monitor: verification pressure, a
  workspace-salience race bar, the dominant affect dimension, scar strength /
  predicted error, the tick's credit-status mix, and the run's evidence level
  — plus a timeline scrubber for jumping directly to any tick. The panel is
  self-contained and byte-deterministic in deterministic mode (it reads only
  the embedded sorted-key JSON island); any voiced text shown alongside it
  remains non-canonical.
- **Canonical/non-canonical boundary, reaffirmed.** The evidence scorer stays
  completely prose-blind: neither the skin nor the judge can inflate the
  evidence level. `test_skin_cannot_inflate_the_level` (and its v0.1
  counterpart for `--skin llm`) assert the echoed `evidence_frame` and
  `evidence_level` are byte-identical with or without a skin/judge attached —
  only `text_voiced`/`voice_status` differ. Nothing here asserts
  consciousness, sentience, or autonomy, and nothing here changes the Level
  claim.

```txt
python -m pneuma_lab.voice fixtures/interventions/clamp_tension.jsonl --paired --skin llm --monitor
```

## 9. Future work

Remaining future work: a semantic-entailment check stronger than the current
judge-over-grounding-packet design, richer monitor panels (e.g. per-family
timelines, paired control/treated side-by-side view), and wiring alternative
local or hosted model backends behind the same `VoiceSkin`/judge seams.

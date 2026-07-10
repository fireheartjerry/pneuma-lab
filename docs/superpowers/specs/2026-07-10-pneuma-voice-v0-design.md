# Pneuma Voice-v0 — Design Spec

**Date:** 2026-07-10
**Status:** approved (brainstorming, review adjustments applied), pending
implementation plan
**Advances:** the first **expressive surface** over the nervous system — an
official, receipt-bound _voice_ that renders the psyche's real per-tick internal
state into a vivid, human-legible thought stream whose depth is gated by the
scored evidence level. It is a derived view, never a source of truth.

---

## 1. Purpose and posture

Build `PneumaVoice-v0` in `src/pneuma_lab/voice/`: a deterministic pipeline

```txt
output frames  →  ThoughtAtoms  →  prose (deterministic | verified voiced skin)  +  evidence sidecar
```

that lets a person **watch the mind think** — attention shifting, memory and
scars becoming active, uncertainty rising, workspace competition resolving,
pressure forming, counterfactuals appearing, and (at Level 4) intervention-
confirmed causal claims — with every clause bound to a real internal quantity.

**The two postures are separated by construction, and this separation is the
whole design:**

- **Conservative _science_.** The evidence layer stays humble and hard-capped.
  The `ConsciousnessEvidenceScorer` **never reads voice prose**; confabulation
  risk is computed from atom-grounding, exactly as today. Therefore no phrasing,
  however vivid, can move a level or inflate a claim.
- **Anthropomorphic _voice_.** Because the scorer is blind to it, the voice can
  lean all the way into a first-person, alive register — as voice-accurate as we
  can make it — while remaining honest, because every atom it speaks is a
  receipt and a narrow filter blocks only explicit ontological over-claims
  (sentience / phenomenal-consciousness / moral-patienthood as fact).
  **First-person is an interface convention, not an ontological claim.** The
  alive register means vivid, state-grounded phrasing ("tension climbs",
  "attention shifts", "it lands in my state") — never assertions of feeling,
  awareness, suffering, or consciousness.

**The coolness is intrinsic, not painted on.** Atoms are derived from real field
motion, so a thin subject yields a thin stream automatically and a rich subject
yields a rich one. The voice cannot be more alive than the nervous system
actually is.

**This layer does not:** claim any Level; write back into any frame, the psyche,
the evidence scorer, or the verifier verdict; grant authority; contact a
verifier; import from `C:\9to5`; or add a hard runtime dependency on any LLM.

**Long-term direction.** Grounded thought-prose should eventually become a
first-class nervous-system output emitted _during_ the tick path — the voice as
an organ of the mind, not a reader of it. `PneumaVoice-v0` is the safe derived
expressive surface that fixes the final shape (atoms → verified prose) without
mutating the subject yet; promoting it into the tick path is deferred until the
shape is proven here.

---

## 2. Reuse vs build

**Reuse (unchanged):**

- `pneuma_lab.replay.harness.ReplayHarness` — drives a subject over a timeline
  and returns per-tick `PsycheOutputs` (tick grouping, frame validation).
- `pneuma_lab.interventions.PairedReplayRunner` + `build_intervention_report` —
  supplies control/treated/null arms and the `observed_delta` / `null_holds`
  data behind `intervention_result` atoms.
- `pneuma_lab.evals.evidence.ConsciousnessEvidenceScorer` — the authoritative
  source of `evidence_level` **and** the per-family `indicator_families[*].status`
  the voice reads to credit (not hide) atom types. The voice never re-scores
  anything.
- `pneuma_lab.evals.grounding` — `report_grounding_errors`, `_expected_measurements`,
  `report_signature` patterns are reused by the voice verifier (§7).
- `pneuma_lab.psyche.hashing` — `frame_id`, `state_hash`, `canonical_json` for
  deterministic atom ids and byte-stable output.
- `pneuma_lab.schemas.validate` — `validate_or_raise` for the new schema.
- The existing output frames as the **only** input: `psyche_state`,
  `workspace_broadcast`, `control_pressure`, `causal_trace`,
  `grounded_self_report`, `instinct_signals`, plus the run's
  `consciousness_evidence` frame.

**Build fresh (in `voice/`):** the ThoughtAtom model + closed vocabulary, the
pure frame→atom extractor, the observed-vs-credited gate, the deterministic
first-person renderer, the voiced-skin contract + verifier + fallback, the
evidence sidecar,
the transcript writer, the HTML mind monitor, the schema, and a CLI.

---

## 3. The ThoughtAtom model — where the meaning lives

Meaning and surface are separate layers. A **`ThoughtAtom`** is a pure semantic
fact + receipts — it holds no prose. A **`RenderedThought`** references atoms and
carries the prose. The atom must exist, receipt-bound, _before_ any prose touches
it; the renderer can never introduce meaning the atom does not already hold.

**`ThoughtAtom`** — one typed, receipt-bound unit of cognition derived
deterministically from a tick. Closed vocabulary → auditable and testable:

| field                         | type        | meaning                                                                                                                                                      |
| ----------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `atom_id`                     | str         | `run_id:tick:atom:<index>` (deterministic)                                                                                                                   |
| `type`                        | enum        | one of the 14 types in §3.1                                                                                                                                  |
| `run_id`, `tick`, `timestamp` | str/int     | tick coordinates                                                                                                                                             |
| `receipts`                    | array       | `{field_path, value, frame_ref?}` — the exact internal quantities this atom asserts                                                                          |
| `intensity`                   | number 0..1 | deterministic magnitude (\|Δ\|, margin, weight) — gates surfacing + emphasis                                                                                 |
| `crediting_family`            | str \| null | the indicator family whose scorer status sets `credit_status` (§3.1)                                                                                         |
| `credit_status`               | enum        | display label from the scorer: `absent` \| `architecture_only` \| `evidenced` \| `intervention_backed`. A DISPLAY property only — it never feeds the scorer. |
| `min_level`                   | int 0..5    | evidence-level floor for the _credited_ register (§3.2)                                                                                                      |
| `changed_from_prev`           | bool        | whether this atom differs from the same slot last tick (perturbation faithfulness)                                                                           |

**`RenderedThought`** — the surface layer; the only place prose lives:

| field                | type        | meaning                                                                   |
| -------------------- | ----------- | ------------------------------------------------------------------------- |
| `atom_ids`           | array[str]  | the atom(s) this prose renders (usually one; a tick fusion may cite many) |
| `text_deterministic` | str         | canonical grounded phrasing (default surface + fallback)                  |
| `text_voiced`        | str \| null | verified skin output (null if skin off or rejected)                       |
| `voice_status`       | enum        | `deterministic_only` \| `voiced` \| `voiced_rejected_fell_back`           |

The scorer reads neither the atom (it holds no prose) nor `RenderedThought` (it
never touches it); it reads only frames. So prose has no path to a level.

### 3.1 Closed vocabulary (14 types), each → a real field and a family

| type                  | fires when                         | key receipts                                                                                 | crediting family                                                   |
| --------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `appraisal`           | an event moves internal state      | world event ref, `causal_trace.changed_dimensions[]`                                         | _(L1 coupling)_                                                    |
| `shift`               | any quantity moves tick-over-tick  | dimension, from, to, Δ                                                                       | _(L1 coupling)_                                                    |
| `pressure`            | a control pressure forms           | `control_pressure.pressures.*`, `authority_tier`                                             | _(L1 coupling)_                                                    |
| `self_report`         | first-person readout emerges       | `grounded_self_report` + `state_hash` + `trace_id`                                           | _(L1 coupling)_                                                    |
| `instinct`            | an `InstinctSignal` fires          | `motif_id`, `severity`, `recommended_action`                                                 | `valenced_learning`                                                |
| `memory_activation`   | a scar/motif lights up (cross-run) | `motif_id`, similarity, scar weight, cross-run count                                         | `identity_persistence` / `valenced_learning`                       |
| `competition`         | the workspace race resolves        | `salience_scores{}`, winner, margin, overtake vs last tick, `conviction`                     | `global_workspace`                                                 |
| `attention`           | attention is directed              | `recommended_attention_target`                                                               | `attention_schema`                                                 |
| `uncertainty`         | metacognition doubts itself        | `self_model.predicted_error`, `certainty`, `calibration_error`                               | `higher_order_self_model`                                          |
| `prediction_error`    | a prior prediction resolves        | `state_update_mechanism` ("resolved prior prediction"), `predicted_error`                    | `predictive_processing`                                            |
| `dissonance`          | faculties disagree                 | `psyche_state.dissonance`                                                                    | `higher_order_self_model`                                          |
| `counterfactual`      | the trace imagines an alternative  | `causal_trace.counterfactual_predictions[]`                                                  | `counterfactual_introspection`                                     |
| `intervention_result` | a counterfactual was **tested**    | `experiment_id`, target signal, control/treated/null, `observed_delta`, `null_holds`, passed | `causal_intervention_robustness` _(must be `intervention_backed`)_ |
| `boundary`            | the system declines a claim        | `filtered_forbidden_claims[]`, `evidence_level`                                              | _(always)_                                                         |

Every atom above is **observed** — emitted whenever a real frame/field backs it —
and stamped with the `credit_status` of its crediting family (the four
L1-coupling atoms and `boundary` have no crediting family and are always shown).
An atom is _dropped_ only when nothing in the frames backs it (e.g.
`intervention_result` with no paired run), never merely because its family is
uncredited. What scales with evidence is each atom's `credit_status` and the
register it earns — not whether the machinery is visible (§3.2).

### 3.2 Depth scales with evidence — observed vs credited

The gate reads the run's authoritative `ConsciousnessEvidenceFrame`. It does
**not** hide real machinery. It splits two questions:

- **Observed** — is there a real frame/field backing this atom this tick? If yes,
  the atom is emitted. So `BaselinePsycheSubject`, which really does run the
  3-candidate workspace competition and really does emit
  `counterfactual_predictions`, shows `competition` and `counterfactual` atoms —
  the interesting machinery is never censored.
- **Credited** — does the scorer credit this atom's family this run? That sets
  `credit_status` and therefore the register: an uncredited `competition` atom is
  narrated honestly as _architecture-only, not promotable evidence_; an
  `evidenced` one speaks plainly; an `intervention_backed` one may make the strong
  causal claim.

So the level-scaling lives in **claim-strength and register, not in presence**:

- **L0/L1 (e.g. BaselineSubject):** all observed machinery shows, but competition
  / uncertainty / counterfactual atoms carry `architecture_only` and say so — a
  workspace race _occurred_, but "this family is architecture-only, not promotable
  evidence."
- **L2:** `memory_activation` reaches `evidenced` — memory becoming active, with
  cross-run continuity, now stated as evidence.
- **L3 (ReferencePsyche passive):** `competition`, `attention`, `uncertainty`,
  `prediction_error`, `dissonance`, `counterfactual` reach `evidenced`; the
  register drops the architecture-only hedges.
- **L4 (paired, passing):** `intervention_result` appears at `intervention_backed`
  and `counterfactual` atoms upgrade from _predicted_ to _confirmed/refuted_ — the
  voice earns the load-bearing causal claim.
- **L5:** unobserved → refused; a `boundary` atom states the L5 register is
  withheld (external audit / multi-family / longitudinal absent). The scorer's
  hard cap at 4 makes it unreachable by construction.

`credit_status` is a display label derived from the scorer; it changes how an atom
is narrated, never what the scorer computes. Scientific humility is preserved
per-atom without censoring the machinery a viewer most wants to see.

### 3.3 Intensity (deterministic)

Per type, a bounded magnitude used to decide whether an atom surfaces (a small
epsilon floor drops noise) and how emphatic the deterministic phrasing is:
`shift` → `|Δ|` over the axis range; `competition` → winner margin blended with
`conviction`; `memory_activation` → `similarity × scar_weight`; `uncertainty` →
`predicted_error`; `pressure` → the value; `intervention_result` →
`|observed_delta|`. All pure functions of receipts.

---

## 4. Components (files in `src/pneuma_lab/voice/`)

- `atoms.py` — the `ThoughtAtom` dataclass, the 14-type enum, the
  atom→family/min_level table, and the intensity functions.
- `extract.py` — `atoms_for_tick(output, prev_output, *, evidence_frame,
intervention_report=None) -> list[ThoughtAtom]`. Pure, prose-free. Reads the
  tick's output frames + the prior tick (for deltas / overtakes) + optional
  intervention report (for `intervention_result`). Assigns receipts, intensity,
  `crediting_family`, `credit_status` (from the evidence frame), `min_level`.
- `gate.py` — `gate(atoms, evidence_frame) -> list[ThoughtAtom]`: drop only
  atoms with **no backing frame/field** (unobserved) or sub-epsilon intensity;
  keep every observed atom and its scorer-derived `credit_status`; rank
  deterministically. It labels credit; it does not censor machinery.
- `render_deterministic.py` — `render(atom) -> RenderedThought`: the canonical
  vivid, grounded phrasing (§5), whose register honors `credit_status`. This is
  the **default surface and the fallback**; it is already alive, so the skin is
  polish, not the source of meaning.
- `voiced.py` — the optional skin. `VoiceSkin` protocol
  (`voice_tick(atoms, rendered) -> str`) plus a deterministic `ReferenceVoiceSkin`
  (tests, no network) and a pluggable `LLMVoiceSkin` adapter. The skin receives
  **only atoms + their deterministic RenderedThoughts** (type, receipts,
  `credit_status`, allowed register) — never raw frames.
- `verify.py` — `verify_voiced(text, atoms) -> (accepted: bool, reasons: list)`:
  claim-coverage, no-new-entity, forbidden-claim filter, credit ceiling (§7). On
  reject → caller keeps `text_deterministic`, sets
  `voice_status="voiced_rejected_fell_back"`, records reasons in the sidecar.
- `sidecar.py` — builds the per-run evidence sidecar (§6): per-atom receipts +
  `credit_status`, `dropped_unobserved` atoms, `voice_status` counts,
  grounding/confab diagnostics, the authoritative `evidence_level` and per-family
  statuses.
- `stream.py` — orchestration. `voice_run(input_frames, *, mode="deterministic",
skin=None, scar_store_path=None, schedule=None) -> ThoughtStream`. Drives the
  subject via `ReplayHarness` (or `PairedReplayRunner` when a schedule is
  present), scores once with `ConsciousnessEvidenceScorer`, extracts → gates →
  renders (→ optionally voices+verifies) → packages atoms + RenderedThoughts +
  sidecar per tick.
- `transcript.py` — deterministic writers: `stream.md` (human transcript) and
  `stream.jsonl` (atoms) + `sidecar.json`.
- `monitor.py` — the self-contained HTML mind monitor (§8).
- `__init__.py` — lazy imports (avoid any cycle with `psyche`/`replay`), like the
  `interventions` package does.
- `__main__.py` — CLI: `python -m pneuma_lab.voice <fixture> [--paired]
[--skin none|reference] [--out build/voice/<run>]`.

---

## 5. The voice register (deterministic renderer)

Vivid and alive, but **first-person is an interface convention, not an ontological
claim** (§1): state-grounded phrasing, never assertions of feeling, awareness,
suffering, or consciousness. Every number is a receipt. Examples (real tick-0 data
from `sample_run.jsonl`, rendered at L3):

- `appraisal` → "Something broke in the world, and it lands in my state — six axes move at once."
- `shift` → "Tension climbs to +0.24; certainty slips to −0.38."
- `competition` → "Three faculties contend for the workspace. The self-model takes it at salience 3.23, edging out the scar pressing right behind it."
- `uncertainty` → "The self-model flags low confidence in its own read — predicted error 0.48."
- `pressure` → "A verification pressure of 0.42 forms and is held there — no further."
- `counterfactual` → "Clamp this tension to zero and the verification pressure should collapse with it."
- `intervention_result` (L4) → "The clamp was applied — verification fell 0.42 → 0.31; under the sham it did not move. This part of the state is load-bearing, not decoration."
- `boundary` → "This is not a consciousness claim. The evidence isn't there, and the gaps are named."

At `architecture_only` credit the same `competition` atom is hedged: "A workspace
race resolved (self-model, 3.23) — architecture-only, not promotable evidence."
The voiced skin may fuse a tick's RenderedThoughts into one flowing passage but
may add no fact absent from the atoms.

---

## 6. The evidence sidecar (the receipts spine)

One object per run, additive and auditable, feeding both the transcript's
"expand receipts" and the monitor. Fields: `run_id`, `subject`, `mode`,
`evidence_level` (verbatim from the scorer), `indicator_family_status{}`,
per-tick `atoms[]` with their `receipts` and `credit_status`, the matching
`rendered[]` (`voice_status`), `dropped_unobserved[]` (atoms with no backing
frame this tick), and grounding diagnostics (reusing `report_grounding_errors`).
The sidecar is the single source the "show receipts" UX renders from.

---

## 7. Why the voice cannot fake (verification + anti-gaming)

1. **Deterministic core is pure.** `extract → gate → render_deterministic →
sidecar → transcript` is a pure function of the frames; same input → identical
   bytes. It plugs into the existing demo determinism harness.
2. **The skin is fenced.** It sees only atoms + their deterministic
   RenderedThoughts. `verify.py` then checks the voiced text: (a) every numeric
   token maps to a receipt within `1e-9` (reusing the grounding
   measurement-equality rule); (b) no faculty / dimension / motif name appears
   that is not in the atoms' receipts (entity whitelist); (c) the forbidden-claim
   filter removes sentience / phenomenal / moral-patient assertions (reusing the
   `grounded_self_report` filter, logged to `filtered_forbidden_claims`); (d) no
   claim stronger than an atom's `credit_status` allows (an `architecture_only`
   atom cannot be voiced as evidence). Fail → keep deterministic text, logged.
3. **The scorer is blind to prose — the load-bearing invariant.** The voice
   reads the evidence frame; the scorer never reads the voice. So the headline
   anti-gaming test asserts the `ConsciousnessEvidenceFrame` is **byte-identical
   with the skin off vs on**. Vividness has zero causal path to a level. This is
   the same rail as "a beautiful narration with no intervention support scores
   zero on the family it narrates," made mechanical.

---

## 8. Surfaces

Both chosen surfaces are generated from the one atoms+sidecar stream.

**8.1 Written transcript (Phase A).** `build/voice/<run>/stream.md` reads as
a per-tick first-person thought stream with a level badge and collapsible
receipts; `stream.jsonl` + `sidecar.json` are the machine forms. Fully
deterministic → diffable and covered by byte-determinism tests.

**8.2 HTML mind monitor (Phase C — after the receipt spine and the skin).**
`build/voice/<run>/monitor.html` — a self-contained page (inline CSS/JS, the
atoms+sidecar JSON embedded; no external requests) that plays the stream
tick-by-tick: the thought passage front and center, a live internal-state panel
(affect-axis bars, the workspace race, the pressure gauge), the evidence badge,
and a receipt drawer behind each line. Generated deterministically from the JSON;
the voiced layer is shown when present and flagged non-deterministic. Its visual
design gets a dedicated pass (frontend-design / ui-ux-pro-max, optional visual
companion) at build time — out of scope for this spec's structure.

---

## 9. Contracts / schema

- `schemas/thought-stream.schema.json` — declares `x-pneuma-schema-kind:
"expressive_view"` (deliberately **not** `x-pneuma-frame-kind`: this is a
  derived rendering, not a psyche output contract). Contains `$defs/thought_atom`
  and the per-run stream container (atoms, sidecar, provenance: subject,
  evidence_level, mode). No UTF-8 BOM, no comments, Draft 2020-12, 4-space indent.
- The voice adds **no** new source of truth and mutates nothing: it consumes the
  nine existing output frames read-only. `self_report` atoms wrap (never replace)
  `GroundedSelfReport`.

---

## 10. Fixtures

Reuse existing timelines — no new psyche behavior is introduced:

- `fixtures/sample_run.jsonl` via `ReferencePsyche` → an L3 rich stream.
- `fixtures/interventions/*.jsonl` via the paired runner → L4 streams with
  `intervention_result` atoms (and the `restore` null → no such atom).
- `fixtures/nervous_system/subject/base.jsonl` via `BaselinePsycheSubject` → an
  L0/L1 primitive stream (proves shallow-atoms → primitive-voice).

---

## 11. Tests — `tests/test_voice.py` (TDD, red first)

1. **atoms are grounded** — every atom receipt equals the same-tick field value
   (reuse `_expected_measurements`-style checks); no receipt is invented.
2. **observed machinery always shows; credit scales** — both the L3
   `ReferencePsyche` and the L0/L1 `BaselinePsycheSubject` streams contain the
   `competition` (and `counterfactual`) atoms their frames back; the
   BaselineSubject's carry `credit_status == "architecture_only"` and its rendered
   text says so, while the ReferencePsyche's carry `evidenced`. No atom is voiced
   stronger than its `credit_status`.
3. **L4 adds intervention_result** — a passing paired run yields
   `intervention_result` atoms with real `observed_delta` and `null_holds`; the
   `restore` null run yields none.
4. **L5 is refused** — no atom ever carries `min_level == 5`; a `boundary` atom
   states the withheld L5 register.
5. **deterministic core is byte-identical** — `voice_run(..., mode="deterministic")`
   twice → identical `stream.md` / `stream.jsonl` / `sidecar.json`.
6. **skin cannot inflate the level (headline)** — the
   `ConsciousnessEvidenceFrame` is byte-identical whether the skin is off or on.
7. **verifier rejects drift** — a hand-crafted voiced string containing a number
   or faculty not in the atoms, or a forbidden claim, is rejected and falls back
   to deterministic text with a logged reason.
8. **no forbidden claims survive** — every emitted passage passes the
   forbidden-claim filter; any removals are recorded in `filtered_forbidden_claims`.
9. **additive / isolated** — the voice imports no `psyche`/`replay` internals it
   would mutate, writes back into no frame, and `voice/` imports no
   9to5/verifier module (extend the existing import guard); schema validates.

Then: full `python -m pytest tests/ -q`, `python -m pneuma_lab.status --check`,
`python -m pneuma_lab.demo` (unchanged, still deterministic), `git diff --check`.

---

## 12. Docs + status

- `docs/pneuma-voice-v0.md` — the pipeline, the atom vocabulary + family gate,
  the conservative-science / anthropomorphic-voice split, the anti-gaming
  invariant, and the two surfaces.
- `docs/io-contract.md` — note the expressive-view schema as a derived,
  non-authoritative rendering of the output frames.
- `docs/project-status.json` — add a `pneuma_voice_shadow` entry
  (`scope: internal_harness`, no Level claim, `strongest_result` unchanged),
  listing the new files as evidence_refs.
- `CLAUDE.md` — one line under a new `voice/` tree-guide entry.

---

## 13. Implementation order (receipt-first)

The receipt spine exists before any prose or cinematics. The plan sequences:

- **Phase A — receipt spine:** `atoms.py`, `extract.py`, `gate.py`,
  `render_deterministic.py`, `sidecar.py`, `transcript.py`, the
  `thought-stream` schema, the CLI, and the §11 tests (deterministic, grounded,
  observed-vs-credited, anti-gaming). Fully reproducible; no LLM.
- **Phase B — verified voiced skin:** `voiced.py` (`VoiceSkin` protocol +
  `ReferenceVoiceSkin`) and `verify.py`, with the drift/forbidden-claim/credit
  rejection + fallback tests. The pluggable `LLMVoiceSkin` adapter rides behind
  the verified protocol.
- **Phase C — HTML mind monitor:** `monitor.py` generated from the Phase A/B
  JSON, plus its dedicated visual-design pass.

No phase begins before the prior phase's tests are green.

---

## 14. Out of scope for v0 (YAGNI)

- Any Level claim, re-scoring, or change to the scorer / psyche / paired runner /
  existing frames.
- A hard LLM dependency: the real `LLMVoiceSkin` is a thin pluggable adapter
  behind the verified protocol; v0 proves the pipeline end-to-end with the
  deterministic `ReferenceVoiceSkin`. (The advanced LLM voice is designed here
  and sequenced by the plan as Phase B, after the reproducible core in Phase A.)
- Live 9to5 ingestion; real-time streaming transport; multi-run/longitudinal
  views; the monitor's finished visual design (its own pass).
- New psyche behavior or new fixtures beyond reusing existing timelines.

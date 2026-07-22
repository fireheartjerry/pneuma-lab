# Nervous-System Voice Fusion — Design

Date: 2026-07-22
Status: approved design, pre-implementation
Depends on: PneumaBrain-v0.1 (trained), ShadowNervousSystem (implemented),
PneumaVoice v0.1 (implemented), trajectory replay bridge (implemented)

## 1. Purpose

Wire the trained brain into the expressive surface and define the bundle
delivery contract. Three products:

1. **Dense per-step scoring** — the brain scores every trajectory step, not
   just three prefixes, producing a continuous risk/instinct/pressure signal.
2. **Outbox contract** — a versioned, digest-chained, append-only JSONL surface
   that any future consumer (the 9to5 shadow edge) tails read-only. This is
   the canonical "how bundles are sent" answer; the 9to5 consumer itself is a
   separate project and stays out of scope.
3. **Fused voice** — brain-derived thought atoms (`instinct`, `pressure`,
   `prediction_error`, `dissonance`) merged into the existing replay-driven
   thought stream, constant-output (every step speaks), receipt-bound into
   bundle field paths, hedged as architecture-only.

Plus a read-only localhost server that tails the outbox and serves a bundle
feed and a live dashboard view.

## 2. Non-goals

- No 9to5 integration (B-9TO5-\* blockers untouched; repo stays standalone).
- No actuation, authority, or verifier contact — the nervous system remains
  advisory shadow-mode.
- No evidence-level change. The scorer stays prose-blind; brain atoms never
  feed `evals/` or `interventions/runner.py`.
- No salience gating: the user wants a constant verbose stream.
- No changepoint/CUSUM detection (deferred; large prediction errors are the
  cheap regime hint).
- No new dependencies. Server is stdlib `http.server`; math is stdlib.

## 3. Architecture

```txt
trajectory envelope
   ├─► bridge ──► replay ticks ──► psyche atoms          (exists)
   └─► ShadowNervousSystem.run_trace(dense=True)
             └─► one bundle per step ──► outbox.jsonl    (canonical)
                        │                     └─► localhost server ─► feed + dashboard
                        └─► bundle atoms ─► merged into tick i ─► verbose stream
```

Four units, one purpose each:

| Unit          | Location                                                                             | Purpose                                                                 |
| ------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| Dense scoring | `nervous_system/runtime.py` (extend)                                                 | per-step prefixes `step_0..step_N` alongside legacy `prefix_25/50/full` |
| Outbox        | `nervous_system/outbox.py` (new) + `schemas/nervous-system-outbox.schema.json` (new) | versioned digest-chained JSONL contract                                 |
| Voice fusion  | `voice/shadow_atoms.py` (new), `voice/stream.py` + `voice/extract.py` (extend)       | bundle → atoms, merged per tick                                         |
| Server        | `nervous_system/server.py` (new)                                                     | stdlib, read-only, tails outbox, serves feed + dashboard                |

The fused stream only exists when a real recorded trajectory exists (bridge
alignment: replay tick `i` ↔ trajectory step `i`). Synthetic fixtures get no
brain atoms — by construction, honestly.

## 4. Dense per-step scoring

- `ShadowNervousSystem.run_trace(..., dense=True)` evaluates the brain at
  every step prefix of the trajectory: `step_0 .. step_N` (where `step_k`
  means "trace truncated after step k"), reusing the existing
  `feature_vector(trace, prefix, vocab)` seam with a generalized prefix
  argument.
- Legacy behaviour unchanged: default (non-dense) call still emits exactly
  `prefix_25`, `prefix_50`, `full`.
- Regression anchor: dense values at the steps corresponding to 25%, 50%, and
  100% must equal the legacy three-prefix values exactly.
- Each dense bundle gains `step_index` (int) and `seq` (monotonic int).

## 5. Signal math (per signal: risk, instinct intensity, pressure magnitude)

All deterministic, stdlib, computed over the dense per-step series
`x_0 .. x_N`:

- **Value** `x_t` — the raw signal at step `t` (receipt into the bundle).
- **Velocity** `v_t = x_t - x_{t-1}` (`v_0 = 0`).
- **Acceleration** `a_t = v_t - v_{t-1}` (`a_0 = a_1 = 0`).
- **Smoothed** `s_t = alpha * x_t + (1 - alpha) * s_{t-1}`, `s_0 = x_0`,
  fixed `ALPHA = 0.3`.
- **Volatility** `sigma_t` — rolling population std over the last
  `VOL_WINDOW = 5` values (fewer if the series is shorter).
- **Prediction error** `e_t = x_t - s_{t-1}` (one-step EMA forecast; `e_0 =
0`). This makes the `prediction_error` atom literally a prediction error,
  matching its `predictive_processing` crediting family.
- **Dissonance** — cross-signal divergence per step: normalized rank
  disagreement between signals (e.g. instinct in its top band while pressure
  sits in its bottom band). Emits a `dissonance` atom only when the
  divergence score crosses `DISSONANCE_MIN = 0.5`; silent on agreement.

Constants live in `voice/shadow_atoms.py` as module-level ALL_CAPS values;
they are rendering-layer parameters, not evidence parameters.

## 6. Outbox contract

- Path: `build/nervous_system/outbox.jsonl` (under the ignored `build/`
  root, per artifact policy). Append-only, one JSON object per line.
- Row kinds:
    - `manifest` — first line: `schema_version`, `run_id`, brain model
      digest, total step count, dense flag.
    - `bundle` — a full validated `PneumaOutputBundle` plus `step_index`,
      `seq`.
    - `suppressed` — kill-switch audit rows, kept in-band.
- Ordering + integrity: `seq` is monotonic from 0; every row carries
  `prev_digest` = sha256 of the previous line's exact bytes (manifest carries
  the digest of an empty string). A consumer verifies the chain to detect
  drops, reordering, or tampering.
- Consumer rule (what 9to5 inherits later): tail the file, verify the chain,
  treat everything as advisory. Read-only by contract.
- New schema `schemas/nervous-system-outbox.schema.json`
  (`x-pneuma-schema-kind`, Draft 2020-12, 4-space indent) validates each row
  kind.
- Byte-determinism: same trace + same model → byte-identical outbox
  (timestamps come from the trace as today; `sort_keys=True` JSON).

## 7. Voice fusion

Mapping (every dense step emits the first three; constant stream, no salience
gate):

| Bundle source                              | Atom type          | Crediting family                   | Rendered flavour                                                       |
| ------------------------------------------ | ------------------ | ---------------------------------- | ---------------------------------------------------------------------- |
| `risk_estimate.failure_probability` series | `prediction_error` | `predictive_processing`            | "failure odds climbing through 0.63, steepest rise so far"             |
| `instinct`                                 | `instinct`         | `valenced_learning`                | "verification instinct firing, band high, easing"                      |
| `control_pressure`                         | `pressure`         | (existing pressure family mapping) | "would raise verification pressure to X — candidate only, not applied" |
| cross-signal divergence                    | `dissonance`       | (per `ATOM_FAMILY`)                | "instinct high but pressure flat — signals disagree"                   |

- Atoms carry the full math tuple (`value`, `velocity`, `acceleration`,
  `smoothed`, `volatility`, `prediction_error`) in their payload; receipts
  point at exact bundle field paths (e.g.
  `risk_estimate.failure_probability`). Derived quantities are labeled as
  derived in the receipt (source field + formula name), never presented as
  frame fields.
- Prose renders motion and bands (calm → uneasy → alarmed), with raw numbers
  as receipts, per the continuous-feel requirement. Band thresholds are
  fixed module constants.
- All brain atoms are hedged "architecture-only, not promotable evidence"
  unless the run's evidence frame credits their family otherwise (existing
  `credit_status_for` path — unchanged).
- `voice_run` gains an optional `shadow` input (the dense bundle list or a
  path to an outbox); when present and the timeline is bridge-expanded,
  bundle atoms for step `i` are appended to tick `i`'s atom list before
  gating/rendering. Existing calls without `shadow` are byte-identical to
  today.
- The deferred renderers for `instinct` and `dissonance` get real templates
  in `render_deterministic.py` (they currently fall back to the generic
  renderer); `prediction_error` and `pressure` reuse/extend existing
  templates.

## 8. Localhost server + dashboard

- `nervous_system/server.py`, stdlib `http.server`, binds `127.0.0.1` only.
- Read-only: exactly two GET routes; everything else 404. No write route
  exists anywhere in the module.
    - `/feed?since=<seq>` — outbox rows with `seq > since`, as JSONL. The
      future 9to5 shadow consumer's plug.
    - `/dashboard` — self-contained HTML (same inline-only posture as the
      existing monitor): live risk/instinct/pressure curves with the verbose
      thought lines annotated on them, polling `/feed`.
- The server holds zero state of its own — it tails the file on request.
  Killing it loses nothing; restarting it re-reads the file. If the run died,
  it serves stale data and says so (last `seq` + manifest step count visible
  in the dashboard header).
- Localhost-only is a hard posture: no external bind flag.

## 9. Error handling

- Envelope has no trajectory → no brain atoms; psyche stream unaffected;
  one logged notice.
- Brain model file missing/unreadable → voice falls back to psyche-only with
  one warning line; outbox not written.
- Outbox write failure mid-run → abort the run (a silently broken chain is
  worse than a partial one; the partial file remains chain-verifiable up to
  the failure point).
- Kill switch off → `suppressed` rows only (audit preserved), no bundles, no
  brain atoms in the voice.
- Server: 404 unknown routes, refuses non-GET, serves stale data rather than
  guessing.

## 10. Testing

- **Dense scoring**: bundle count = step count; `step` values at the 25%,
  50%, 100% marks exactly equal legacy `prefix_25/50/full` outputs; default
  call unchanged.
- **Outbox**: chain verifies end-to-end; a tampered or truncated line is
  detected; prepare-twice byte-identical file for the same trace+model;
  suppressed rows appear under kill-switch.
- **Math**: velocity/acceleration/smoothed/volatility/prediction-error
  against hand-computed fixture series; dissonance fires on a constructed
  disagreement and stays silent on agreement.
- **Voice fusion**: evidence-frame echo stays byte-identical with and
  without `shadow` (extends `test_voice_never_alters_the_evidence_frame`);
  every brain-atom receipt resolves to a real bundle field path; the
  architecture-only hedge is present on every brain atom; `voice_run`
  without `shadow` is byte-identical to current output.
- **Server**: `/feed` returns exactly the outbox rows (and honours `since`);
  non-GET and unknown routes rejected; no write path exists.

## 11. Build order

1. Dense per-step scoring (`runtime.py`), with the legacy regression anchor.
2. Outbox writer + schema + chain verifier.
3. Signal math + `voice/shadow_atoms.py` + fusion into `voice_run` +
   renderer templates.
4. Server + dashboard.

Each stage lands independently useful and fully tested before the next.

## 12. Invariants reaffirmed

- Scorer never reads prose; no code path from `voice/` into `evals/` or
  `interventions/runner.py`.
- Voice never mutates the evidence frame (byte-identical echo, tested).
- Nervous system never actuates; pressure stays a CANDIDATE.
- Everything deterministic except the live server view (which is a pure
  read of deterministic files).
- No consciousness/level claim changes anywhere in this feature.

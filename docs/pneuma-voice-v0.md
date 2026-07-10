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
  lives: `text_deterministic` (always present), `text_voiced` (Phase B,
  currently always `None`), and `voice_status` (`"deterministic_only"` in
  Phase A).

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

## 8. Future work

Phase B (a verified LLM voiced skin populating `text_voiced`) and Phase C (an
HTML mind monitor) are future work per the Pneuma Voice plan/spec — not
implemented here.

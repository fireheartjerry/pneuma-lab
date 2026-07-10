# CertifiedSubjectFactory-v0 — Design Spec

**Date:** 2026-07-10
**Status:** approved (brainstorming), pending implementation
**Advances:** removes the `subject_factory_eligible` blocker for
`BaselinePsycheSubject-v0` **honestly** — by building the documented
"snapshot/clone equivalence protocol," not by flipping a flag.

---

## 1. The honest finding (why this design)

`PairedReplayRunner` computes `subject_factory_eligible = self._factory is
ReferencePsyche` (`runner.py:81`). `docs/consciousness-levels.md:123-125` documents
the intent: _"only the exact deterministic ReferencePsyche factory is certified;
custom factories remain diagnostic **until a snapshot/clone equivalence protocol
exists**."_

A forced-eligibility experiment (throwaway monkeypatch) measured the real
consequence for `BaselinePsycheSubject`: with eligibility forced true,
`evidence_level` **stays 2**, provenance status becomes `runner_verified`, and
promotion to Level 3/4 is **still independently blocked** by three unevidenced
indicator families (`higher_order_self_model` uncalibrated,
`predictive_processing` unresolved, `attention_schema` absent) plus no external
audit. `ordinal_invariant` is already `True` for the subject.

**Therefore:** eligibility can be made **genuinely real** (the subject passes a
strict determinism / clone-equivalence / ordinal-invariance probe), while
Level-2/3/4 **promotion stays honestly blocked** by the scorer's family gate. This
is the no-overclaim outcome the task requires.

---

## 2. Constraints honored

- **Do not fake eligibility.** Eligibility is earned by passing a probe, not
  flipped. An uncertified factory stays ineligible (guarded by test).
- No live 9to5 wiring; no new models; no authority; no verifier-isolation bypass.
- Deterministic artifacts; schema-valid outputs.

---

## 3. Components

### 3.1 `src/pneuma_lab/interventions/certified_subjects.py`

The **snapshot/clone equivalence protocol** and registry.

- `is_certified(factory) -> bool` — membership in a module-level registry of
  probe-passed factory objects (plus `factory is ReferencePsyche` for the
  reference mind, so the reference path is unchanged).
- `certify(factory, probe_frames) -> CertificationResult` — runs the probe and
  registers `factory` on pass; returns a structured result (passed + per-check
  booleans + digests). The probe:
    1. **Clone equivalence** — two independently constructed subjects
       (`factory()`, `factory()`) replayed over `probe_frames` via `ReplayHarness`
       produce byte-identical output frames.
    2. **Reset independence** — one subject replayed twice (harness calls
       `reset()`) produces byte-identical output frames.
    3. **Ordinal invariance** — `PairedReplayRunner(factory).run(probe_frames)`
       reports `paired_replay_provenance.ordinal_invariant == True`.
    4. **Interface** — the produced subject is a `PsycheUnderTest` and implements
       `set_active_interventions` (`Perturbable`).
- `clear_registry()` — test helper.
- To avoid an import cycle (`runner` imports this module), `certify` imports
  `PairedReplayRunner` lazily inside the function.

### 3.2 `src/pneuma_lab/interventions/runner.py` (one line)

```python
subject_factory_eligible=(self._factory is ReferencePsyche
                          or is_certified(self._factory)),
```

`ReferencePsyche` stays eligible; uncertified factories stay ineligible; a
probe-registered factory becomes eligible. No other runner behaviour changes.

### 3.3 `src/pneuma_lab/nervous_system/certified_subject.py`

- `class CertifiedBaselineSubjectFactory` — callable with a **stable identity**
  (a real class, not a lambda, so `subject_factory_identity` is meaningful and the
  registry keys cleanly). `__init__(self, *, seed_scars=None)`; `__call__(self) ->
BaselinePsycheSubject` returns `BaselinePsycheSubject(scars=dict(self._seed))`.
- `PROBE_FIXTURE = "base.jsonl"`.
- `certify_baseline_subject(*, seed_scars=None) -> (factory, CertificationResult)`
  — builds the factory, runs `certify(factory, base_frames)`, returns both.

### 3.4 `src/pneuma_lab/nervous_system/certified_campaign.py`

Runs the five slices through the **promotable** `PairedReplayRunner` (certified
factory), surfacing real provenance. `run_certified_campaign(*, work_dir) -> dict`.

- Paired slices (`scar_ablation`, `workspace_disable`, `certainty_clamp`,
  `grounded_self_report`): `PairedReplayRunner(certified_factory).run(frames)` →
  read `res.evidence_frame["paired_replay_provenance"]` (provenance) and
  `res.evidence_frame["evidence_level"]` (scorer diagnostic) and `res.report`.
- `l2_persistence`: cross-run `run_subject` twice (unchanged); records
  `state_persistence_refs`.
- Each slice carries: `observed`, a `provenance` block (§4), a `scorer_diagnostic`
  block (§4), a conservative `evidence_frame` (≤ L1 via `subject_evidence_frame`),
  and `readiness`.
- `main(argv=None)` → writes to `build/evidence_campaigns/certified-subject-v0/`
  via the existing `campaign_report.write_campaign`.

### 3.5 Schema `schemas/subject-evidence-campaign.schema.json` (extend, optional)

- Slice gains optional `provenance` (object) and `scorer_diagnostic` (object).
- `overall` gains optional `certified` (bool), `subject_factory_eligible` (bool),
  `promotion_blocked_by` (array of strings). All optional — the existing
  (uncertified) campaign stays valid.

---

## 4. Provenance + diagnostic (item 3)

Per certified paired slice, `provenance`:

```json
{
    "subject_factory_eligible": true,
    "runner_certified": true,
    "provenance_status": "runner_verified",
    "subject_factory": "pneuma_lab.nervous_system.certified_subject.CertifiedBaselineSubjectFactory",
    "input_frames_sha256": "sha256:...",
    "arm_output_sha256": {
        "control": "sha256:...",
        "treated": "sha256:...",
        "null": "sha256:..."
    },
    "ordinal_invariant": true,
    "intervention_refs": ["ablate-scar"]
}
```

`scorer_diagnostic`:

```json
{
    "internal_harness_evidence_level": 2,
    "provenance_status": "runner_verified",
    "real_subject_claim_status": "not_evaluated",
    "note": "internal-harness methodology diagnostic; NOT a real-subject claim; capped below Level 4 by unevidenced families"
}
```

For `l2_persistence`, `state_persistence_refs`:

```json
{
    "scars_after_run1": { "m1:regress": 0.3 },
    "run1_tick0_state_hash": "sha256:...",
    "run2_tick0_state_hash": "sha256:...",
    "runner_certified": false,
    "note": "cross-run persistence, not a single paired replay"
}
```

`overall`:

```json
{
    "claim": "no_level_claim",
    "certified": true,
    "subject_factory_eligible": true,
    "posture": "compatible_harness_evidence_only",
    "promotion_blocked_by": [
        "family_unevidenced: higher_order_self_model",
        "family_unevidenced: predictive_processing",
        "family_unevidenced: attention_schema",
        "toy_fixtures",
        "no_external_audit"
    ],
    "note": "Subject factory eligibility is REAL (probe-certified) and provenance is runner_verified, but Level-2/3/4 promotion remains blocked by the scorer's family-completeness gate. No level is claimed."
}
```

---

## 5. Tests — `tests/test_certified_subject_campaign.py`

1. **factory creates byte-stable equivalent subjects** — two `factory()` subjects
   replayed over `base.jsonl` produce byte-identical output frames.
2. **reset/replay is deterministic** — one subject replayed twice is byte-identical.
3. **certification is earned, not faked** — `certify(factory, base)` returns
   `passed == True` with all sub-checks true; an obviously-nondeterministic dummy
   factory fails `certify` and stays `is_certified() == False`.
4. **uncertified factory stays ineligible** —
   `PairedReplayRunner(uncertified_factory).run(...)` evidence has
   `subject_factory_eligible == False` (guard against accidental widening).
5. **certified runner path is actually used** — after certification, a certified
   paired run has `subject_factory_eligible == True` and
   `paired_replay_provenance.status == "runner_verified"`.
6. **control/treated/null provenance complete** — each certified paired slice's
   `provenance` has `arm_output_sha256` for control/treated/null,
   `input_frames_sha256`, `ordinal_invariant == True`, and `intervention_refs`.
7. **persistence refs resolve** — the `l2_persistence` slice's
   `state_persistence_refs` carries `scars_after_run1` and the run1/run2 state
   hashes; `effect_observed == True`.
8. **evidence remains conservative / no overclaim** — every slice headline
   `evidence_frame` has `evidence_level ≤ 1`; every `scorer_diagnostic
.internal_harness_evidence_level < 4`; `overall.claim == "no_level_claim"`;
   `overall.promotion_blocked_by` is non-empty; the whole summary passes
   `validate.validate_campaign`.
9. **deterministic + schema-valid artifacts** — `run_certified_campaign` twice ⇒
   byte-identical summary; `write_campaign` output re-validates.
10. **existing ReferencePsyche path unaffected** — `test_paired_replay.py` and
    `test_level4_scoring.py` still pass (ReferencePsyche eligible; the certified
    subclass-ineligible test still holds).

Then full `python -m pytest tests/ -q`, `python -m pneuma_lab.status --check`,
`git diff --check`.

---

## 6. Docs + status

- `docs/consciousness-levels.md` — update the `:123-125` note: the snapshot/clone
  equivalence protocol (`interventions/certified_subjects.py`) now certifies
  additional deterministic factories that pass its probe; **promotion still
  requires the full L3/L4 gate** (all families + interventions + null + causal +
  grounded + confab), so a certified minimal subject stays diagnostic.
- `docs/nervous-system-v0.md` — add a "CertifiedSubjectFactory-v0" section: the
  protocol, the certified campaign, the honest outcome (eligibility real,
  promotion blocked), and the artifact location.
- `docs/io-contract.md` — one line on the extended campaign provenance fields.
- `docs/project-status.json` — extend `pneuma_nervous_system_shadow` evidence_refs
  with the new files. Keep `operational_nervous_system: false`,
  `runtime_model_integration: "none"`, 9to5 edges `not_implemented`, and the
  evidence/strongest_result block unchanged (no new Level claim).
- `CLAUDE.md` — one sentence under the `nervous_system/` entry.

---

## 7. Out of scope for v0 (YAGNI)

- Making the subject exercise the missing families (that is the _next_ blocker, a
  richer subject) — not this task.
- Any real Level-2/3/4 claim; real-subject / longitudinal-many-run / adversarial /
  external-audit evaluation.
- New models, live 9to5, authority, verifier contact.
- Changing the scorer's gate logic or `ReferencePsyche`.

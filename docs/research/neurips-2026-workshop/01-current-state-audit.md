# 01 — Current-State Audit

Source: 15 parallel read-only code-tracing audits (each traced actual code paths
and ran read-only tests; full per-subsystem reports archived in the session
scratchpad under `audit/`). This document is the reconciled, de-inflated map of
what exists, what works, and what is only documented.

**Maturity vocabulary** (strictly increasing): `specified` (doc/spec only) →
`implemented` (code exists) → `unit-tested` → `integration-tested` →
`experimentally-exercised` (run inside a demo/harness) → `empirically-validated`
(validated on real external data) → `publication-ready`. Orthogonal: `blocked`
(governance/authorization/missing-dependency).

## 0. One-paragraph verdict

Pneuma Lab is a **publication-grade instrument wrapped around zero real-agent
evidence.** The schema contracts, the deterministic replay/scoring harness, the
paired control/treated/null intervention runner, and the scar-memory loop are all
real, deterministic, and honestly tested — but **every one is validated only on a
hand-built deterministic toy mind (`ReferencePsyche` / `BaselinePsycheSubject`)
over ~6 authored fixtures.** No real coding agent is ever observed or controlled;
the one trained model (PneumaBrain-v0.1) is a weak observable-only logistic
regressor with no runtime wiring; the local foundation model's only real result is
a saturation plateau. The instrument and the evaluation discipline are the asset.
The empirical result does not exist yet — which is exactly the gap the pivot fills.

## 1. Test-suite reality

`26 failed, 2049 passed, 13 skipped, 1 deselected`. **All 26 failures are the known
Windows CRLF / committed-shard-digest gotcha in three `foundation` test files
(`FoundationDatasetError: shard hash does not match manifest`) — not a scientific
regression.** No paper-relevant core test fails. Of ~110 test files, **only 5
constitute experimental evidence of causal internal-state effects**
(`test_paired_replay.py` [strongest], `test_perturbation.py`,
`test_evidence_scoring.py`, `test_baseline_psyche_subject.py`,
`test_hollow_baseline.py`); all run on the deterministic toy mind. The remaining
~100 files are plumbing (determinism goldens, schema validation, leakage/authorization
gates). Scientific maturity of the suite: **low-to-moderate**, with exceptional
anti-fraud/determinism hygiene.

## 2. Component maturity map

| Subsystem                                       | Maturity                                                                  | Reuse for the paper                                                                                                                                                   | Hard limit found                                                                                                                                                                                                                                          |
| ----------------------------------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Schemas** (30, Draft 2020-12) + `validate.py` | integration-tested                                                        | HIGH — memory/instinct/causal-trace/intervention/self-report frames cover ~70% of observables                                                                         | No experiment/condition/arm identity; no motif ground-truth binding; DV is a "consciousness level" not task outcome; no cross-frame referential integrity (hashes are unverified strings)                                                                 |
| **Psyche core** (`ReferencePsyche`, 12-stage)   | integration-tested; NOT empirically-validated                             | HIGH — persistent, clampable state vars + working scar→caution loop                                                                                                   | Deterministic hand-built math (no learning); **emits pressure, never an action**; never run on real data                                                                                                                                                  |
| **Replay harness + bridge**                     | integration-tested                                                        | MED — reuse `PsycheUnderTest`/`Perturbable` seam; build live driver elsewhere                                                                                         | Cannot drive a live stochastic agent; determinism is trivially satisfied only by the toy mind                                                                                                                                                             |
| **Interventions + `PairedReplayRunner`**        | integration-tested (5-file experimental evidence)                         | HIGH — control/treated/null + counterbalancing + provenance is the credibility asset                                                                                  | **Clone gate = `sha256` byte-equality → caps a real stochastic agent at L3**; no memory-scramble op; only 5 whitelisted signals                                                                                                                           |
| **Evidence scorer** (`evals`)                   | integration-tested                                                        | HIGH mechanism / DROP ontology — keep the prose-blind firewall + null-provenance-grounding spine; replace the Level-0–4 scalar + 9 families with task-outcome metrics | Anti-gaming verified (no voice→scorer path); confab risk is a real receipt-binding measure, not prose-reading. Validated only on toy mind                                                                                                                 |
| **Adapters + trajectory extraction**            | envelope/extraction integration-tested; adapters experimentally-exercised | HIGH — anchor on real trajectories                                                                                                                                    | Only 3 crude per-step failure proxies (lexical `error_marker`, byte-identical `retry_count`, `strategy_switches`); **arg/output digesting destroys error-class + file identity** → true motif recurrence not yet detectable                               |
| **Converters / splits / governance**            | unit-to-integration-tested                                                | HIGH — repo-grouped leakage-safe splits + fail-closed authorization + populated leakage registry                                                                      | **Motif-axis splitting does NOT exist (repo axis only)**; no real corpus ever split (fixtures only); checkpoint not in the reproducibility binding                                                                                                        |
| **PneumaBrain-v0.1** (`brain`)                  | trained + honestly cross-validated                                        | MED — reuse `features.py`, `evaluate.py` (LORO+bootstrap), `predict.risk_estimate` offline                                                                            | Plain L2 logistic regression over ~20 scalars; one corpus, 91.9% base failure rate; **not causal, not persistent, no runtime wiring**; real AUROC (0.774/0.801/0.826) lives only in a committed artifact, not in any test                                 |
| **Estimators E1/E2**                            | implemented, advisory-only                                                | LOW — offline scoring only                                                                                                                                            | E2 proxy label partly circular (acknowledged in-code); explicitly non-runtime                                                                                                                                                                             |
| **Nervous system + `BaselinePsycheSubject`**    | integration-tested; NOT an agent                                          | HIGH — the right skeleton + methodology                                                                                                                               | **Failure detection is faked** (`scar_motif_matches` fixture-fed); scar update is flat +0.1, no decay/cap, untied to actual error; workspace is a 3-scalar argmax; no action, no outcome contrast                                                         |
| **Voice / self-report**                         | integration-tested (mocked LLM)                                           | MED — secondary self-report faithfulness study                                                                                                                        | Anti-gaming firewall clean; 5 atom types declared-but-unemitted; semantic entailment only bites with a real judge wired; unconstrained-LLM arm missing; no real LLM ever run                                                                              |
| **Foundation (local Qwen)**                     | integration-tested vs `FakeQwen` mock                                     | LOW for critical path; MED reuse                                                                                                                                      | Recurrent junction only tested vs mock; **8M result is a plateau (64.14%, doubling gate stopped) vs UNTRAINED baselines**; `not_promoted` / `not_authorized`. `memory.py` (SQLite/FTS5 + erasure receipts) is directly reusable as the retrieval baseline |

## 3. The three load-bearing gaps (every audit converges here)

1. **No state→action coupling.** The psyche/subject emits a `verification` pressure
   _number_ that nothing consumes. "Avoid repeating a failure" requires the state
   to change what an agent _does_. This coupling does not exist anywhere.
2. **No real failure detection.** Recurring-failure "noticing" is hand-asserted in
   fixtures. A detector that derives a motif id + similarity-to-past from a real
   trajectory does not exist, and the current extraction digests away the error-
   class/file identity such a detector needs.
3. **No outcome-level baseline-vs-treatment on real data.** All interventions move
   an internal number on a toy mind; none shows a _task outcome_ (bug fixed / not,
   failure repeated / not) differing with vs without the mechanism. That contrast
   is the entire empirical claim and is 100% absent.

## 4. Assets to keep verbatim

- The **`PsycheUnderTest` / `Perturbable`** seam (each condition becomes one
  implementation).
- The **paired control/treated/null runner** with counterbalanced execution orders
  and digest-bound provenance — the causal credibility layer.
- The **prose-blind behaviour/self-report firewall** (verified one-way; self-report
  cannot inflate the score).
- **Determinism + canonical hashing** (byte-reproducible synthetic experiments for
  free).
- **`HollowPsyche`** as a ready ablate-everything negative control.
- **`foundation/memory.py`** (SQLite/FTS5 + hard-erasure receipts) as the retrieval
  baseline backend, usable today with no GPU/auth.
- **Repo-grouped leakage-safe splits + populated cross-dataset leakage registry +
  fail-closed authorization.**

## 5. Assets to demote to motivation / future work

- The **Level-0–4 consciousness ladder and 9 indicator families** → archived
  motivation; replaced by task-outcome metrics (`phenomenal_consciousness_claim:
not_claimed` already holds).
- The **local Qwen foundation subject** → off critical path; recurrent junction is
  an architecture-only optional ablation.
- **PneumaBrain-v0.1 as "learned cognition substrate"** → demote to an offline risk
  feature; the model card oversells it.

## 6. Blocker triage (from `project-status.json`, re-scoped to the pivot)

| Blocker                                       | Relevance    | Disposition                                                                                                        |
| --------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------ |
| B-EVID-REAL-SUBJECT                           | **HIGH**     | The paper's entire purpose — build a real subject + outcome experiment                                             |
| B-EVID-LONGITUDINAL                           | **HIGH**     | Cross-run persistence never demonstrated (`reset()` clears scars; 9to5 psyche DB never existed) — a headline build |
| B-EVID-FAMILY-INTERVENTIONS                   | MED          | Only 1/9 families intervention-backed; the pivot needs only the failure-memory family                              |
| B-TRAIN-RUNTIME                               | MED          | Offline estimators have no runtime; the decision head is the runtime wire                                          |
| B-9TO5-_ (4), B-JSPACE-_ (3), Level-5/RSI (4) | OUT OF SCOPE | Bracket for this paper                                                                                             |

## 7. Reconciliation flags (must be stated honestly in the paper)

1. **E-0 negative result** (`docs/research/experiments/e0-results.md`): pre-registered
   three hypotheses, **failed all three** — replayed psyche signals scored AUROC
   0.339/0.349 at predicting failure vs a **retry-count baseline of 0.705**; psyche
   signals were _anti-correlated_ with failure via a length/activity confound, held
   under a no-sign-flip discipline. Consequence for the pivot: (a) retry-count is a
   mandatory strong baseline; (b) token/step budgets must be tightly matched across
   arms; (c) the paper must pre-empt "your signals didn't even predict failure" by
   noting the DV is _behavioural repeat-reduction under causal gating_, not passive
   prediction.
2. **`pneuma-brain-v0.signed.json` is a real `decision: authorized`** — the brain
   _was_ trained — which contradicts `CLAUDE.md`'s "no foundation model is trained"
   line (that line is about the _foundation_ model, but the phrasing invites
   confusion). State the brain's status precisely.
3. **"Persistent" is currently aspirational** — true cross-run persistence is only
   demonstrated tautologically (same fixture motif every tick, fixed +0.1). Genuine
   longitudinal persistence on real data is a build and a claim to earn.

## 8. Bottom line for the plan

The pivot does not require rebuilding Pneuma Lab; it requires **adding the three
missing load-bearing pieces** (a real failure detector, a state→action decision
head, and a real-data outcome experiment) **on top of assets that are already
publication-grade** (paired causal runner, prose-blind firewall, leakage-safe
splits, determinism). The implementation plan (`12`) is dependency-ordered around
exactly those additions.

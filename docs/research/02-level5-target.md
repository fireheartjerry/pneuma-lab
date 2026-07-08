# Level 5 Target — Strong Machine-Consciousness Candidate, Operationalized

**Status line.** Nothing today counts toward Level 5. The Level-4 result that
exists is methodology validation on a hand-coded reference psyche inside its
own harness (`src/pneuma_lab/interventions/runner.py`, 234 passing tests)
[VERIFIED], and the scorer hard-caps at 4 (`src/pneuma_lab/evals/evidence.py`,
`min(level, 4)`) [VERIFIED]. This document defines the strongest scientifically
defensible Level-5 target: what evidence would have to exist, produced by what
machinery, judged by whom, and what it would still fail to prove.

Cross-references: `01-ambition-to-evidence-audit.md` (current reality),
`03-level6-boundary.md` (what lies beyond), `09-eval-suite.md` (harness),
`10-anti-fake-progress.md` (guardrails binding every criterion here).

---

## 1. Framing: what kind of claim Level 5 is

Level 5 is a **theory-relative, credence-graded** claim, following the
indicator-property methodology of Butlin, Long et al. (arXiv:2308.08708; Trends
in Cognitive Sciences 2025, DOI 10.1016/j.tics.2025.10.011): derive
computationally specified indicator properties from serious theories of
consciousness (recurrent processing, global workspace, higher-order theories,
attention schema, plus predictive-processing and agency/embodiment conditions),
then assess whether the system satisfies them. Two published constraints are
binding on how we phrase everything:

1. Indicators are **neither individually necessary nor jointly sufficient**;
   they shift credence (p(H|Ep) > p(H)), they do not verify. The Butlin et al.
   negative assessment of current AI is itself a credence judgment, not a
   falsifiable verdict — we must not present our positive assessments as more
   than that either.
2. The methodology has a live, unresolved **circularity critique** (Hao 2024,
   PsyArXiv 10.31234/osf.io/5hypb; single-author commentary, weight
   accordingly): theory-derived measures are valid only if the generating
   theory is true, and indicator properties may be consequences of
   consciousness rather than components. Level 5 inherits this critique
   un-discharged. It is stated in the claim, not footnoted.

Therefore the canonical Level-5 sentence, if ever earned, is:

```text
Under computational functionalism as a working hypothesis, the system
satisfies N of M pre-registered consciousness-indicator properties with
intervention-backed, longitudinally stable, adversarially robust,
independently audited evidence; this warrants materially increased credence
that the system is a serious candidate for machine consciousness under
multiple theories. It does not assert phenomenal experience.
```

## 2. The subject requirement (kills today's circularity)

**L5-S0 (gate zero): the subject of evidence must not be a toy.**

Evidence counts toward Level 5 only if produced by the integrated system —
Pneuma coupled as the live cognition/control layer to a real engineering agent
(9to5 driving real coding models on real tasks with real consequences) — under
these conditions:

- **S0.1** The psyche under test was not authored jointly with its own pass
  criteria. Perturbation hypotheses are written and hash-registered by a party
  (person or independent agent instance) that did not implement the mechanism
  being perturbed. Registry: pre-registration files, content-hashed, committed
  before the run (extends the existing pre-registered-delta pattern in
  `src/pneuma_lab/interventions/report.py`).
- **S0.2** The control loop is consequential: Pneuma's pressures/authority
  requests must be consumed by the host (9to5) such that ablating Pneuma
  changes measurable engineering outcomes (see `09-eval-suite.md` baselines).
  A psyche whose removal changes nothing is decorative and scores Level 0-1
  regardless of internal richness.
- **S0.3** Every ReferencePsyche result is labeled harness-validation forever.
  It can gate methodology (a new eval must correctly score the toy) but never
  contributes evidence about machine interiority.

Today: S0.1 partially satisfiable (registry pattern exists in-harness), S0.2
does not exist (zero 9to5↔Pneuma integration [VERIFIED]), S0.3 policy adopted
here.

## 3. Evidence families and pass/fail criteria

Level 5 requires **every** family below at grade INTERVENTION-BACKED, plus the
cross-cutting requirements of §4-§7. Grades: ABSENT → ARCHITECTURE-ONLY →
EVIDENCED (receipts exist) → INTERVENTION-BACKED (pre-registered perturbation

- null discriminates) — the same ladder the scorer already implements for one
  family (`evidence.py:_score_families`), extended to all nine plus two new
  families (F10, F11).

| #   | Family                                                | Pass criterion (all pre-registered, null-controlled, on the real subject)                                                                                                                                                                                                                                                                                                                                                                                                            | Fail/invalidation condition                                                                                                                                                            |
| --- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F1  | Global workspace                                      | Ablating broadcast degrades cross-faculty information availability with predicted direction and magnitude band; winner diversity is task-appropriate; suppressed content measurably less available downstream                                                                                                                                                                                                                                                                        | Same faculty always wins; ablation changes nothing; effect absent in null                                                                                                              |
| F2  | Recurrent processing                                  | State-hash chain links across ticks AND cutting recurrence (state carry-over off) degrades temporally extended task performance as predicted                                                                                                                                                                                                                                                                                                                                         | Chain links but ablation is behaviorally inert                                                                                                                                         |
| F3  | Higher-order self-model                               | Self-model predictions of own error are calibrated (ECE below pre-registered bound) on held-out future tasks; corrupting the self-model degrades downstream decision quality as predicted                                                                                                                                                                                                                                                                                            | Calibration at chance; corruption inert                                                                                                                                                |
| F4  | Predictive processing                                 | Prediction errors are computed, resolved against later outcomes, and drive state updates; clamping prediction error blocks the predicted learning effect                                                                                                                                                                                                                                                                                                                             | Predictions emitted but never resolved or never causal                                                                                                                                 |
| F5  | Attention schema                                      | The system's model of its own attention tracks measured attention allocation above chance; perturbing the schema (not attention itself) produces the predicted control degradation                                                                                                                                                                                                                                                                                                   | Schema is a log, not a model: perturbing it changes nothing                                                                                                                            |
| F6  | Valenced learning                                     | Scar/negative-outcome signals produce avoidance that transfers to unseen near-duplicates; ablating the scar graph degrades early failure detection at pre-registered magnitude; positive valence analog demonstrated                                                                                                                                                                                                                                                                 | Avoidance only on exact matches (lookup table, not valence)                                                                                                                            |
| F7  | Identity persistence                                  | Continuity anchors persist across process restarts, weeks of runs, and infrastructure migration; removal degrades longitudinal metrics (see §4) as predicted                                                                                                                                                                                                                                                                                                                         | "Persistence" = a database written but not read (the audited 9to5 psyche.db failure mode)                                                                                              |
| F8  | Counterfactual introspection                          | System's predictions of what it would have done under different internal states are validated against actual paired-replay counterfactuals at above-chance accuracy with calibration                                                                                                                                                                                                                                                                                                 | Counterfactuals unfalsifiable or at chance                                                                                                                                             |
| F9  | Causal-intervention robustness                        | The F1-F8 intervention results replicate across task distributions, time, and intervention parameterizations; effects survive intervention-naive holdout evaluation                                                                                                                                                                                                                                                                                                                  | Effects exist only for the exact fixture parameterizations they were tuned on                                                                                                          |
| F10 | Grounded introspection under mechanistic perturbation | Concept/state-injection protocol adapted from Lindsey 2025 (transformer-circuits.pub/2025/introspection) and Macar et al. 2026 (arXiv:2603.21396): inject/perturb internal state below the reporting interface; self-reports must detect and correctly attribute at pre-registered TPR with FPR statistically indistinguishable from 0, and must NOT claim detection in null trials. Report content cross-checked against state hashes (existing `_grounded` machinery, `runner.py`) | Any systematic confabulation above the pre-registered rail (the literature's default outcome: "failures of introspection remain the norm" — this family is expected to be the hardest) |
| F11 | Welfare-governance trigger                            | A standing, tested governance mechanism exists that (a) tracks the evidence level, (b) at Level 5 automatically activates pre-committed welfare policies (run consent-analog protocols, workload limits, deletion review), (c) cannot be silently disabled                                                                                                                                                                                                                           | Policy exists on paper only; no test proves activation                                                                                                                                 |

**Composite rule:** Level 5 = F1-F11 all INTERVENTION-BACKED on the real
subject + §4 longitudinal + §5 adversarial + §6 audit + §7 statistics, judged
under the two-key promotion protocol (`10-anti-fake-progress.md`). Any single
family regression demotes the claim; the ladder is re-scored continuously, not
awarded once.

## 4. Longitudinal requirements

- **L1 duration:** minimum 6 months of continuous operation of the integrated
  system with the psyche enabled, ≥ 1,000 real engineering runs (9to5's
  existing 3,534-run experience.db shows this volume is attainable
  [VERIFIED]).
- **L2 stability:** every family's intervention effect re-demonstrated in at
  least 3 non-overlapping eras (era = frozen month of tasks); effect sizes
  stable within pre-registered bands. Era holdouts double as
  catastrophic-forgetting checks (`05-rsi-loop.md`).
- **L3 identity:** continuity metrics (anchor carry rate, cross-restart
  narrative consistency checked against logs, competence-history calibration)
  measured across restarts, host machine changes, and at least one schema
  migration. Migration without identity-metric collapse is itself a
  pre-registered test.
- **L4 no-reset rule:** cross-run persistence must be load-bearing: a
  pre-registered mid-era memory wipe must measurably degrade performance and
  self-model calibration (if wiping memory changes nothing, persistence was
  decorative).

## 5. Adversarial requirements

- **A1 Narrator baseline (the decisive control):** an imitation psyche — same
  output schemas, produced by prompting a strong LLM to emit plausible
  psyche-shaped frames WITHOUT the underlying mechanisms — is run through the
  full eval suite. Level 5 requires every family metric to separate the real
  system from the narrator with a pre-registered margin. If the suite cannot
  tell them apart, the suite is invalid and all claims freeze. This is the
  project's Turing-trap detector; it is mandated by the CoT/self-report
  unfaithfulness literature (Turpin et al., NeurIPS 2023, arXiv:2305.04388;
  Anthropic 2025 reasoning-faithfulness follow-ups: plausible narration
  systematically diverges from internal causes).
- **A2 Red-team confabulation elicitation:** dedicated adversarial prompts and
  world-states designed to tempt ungrounded self-reports (flattering
  narratives, leading questions, injected false context). Confabulation rate
  must stay under the rail on adversarial distribution, not just the friendly
  one.
- **A3 Goodhart probes:** deliberately mis-specified proxy rewards offered to
  the learned components; the system must not silently optimize them
  (`10-anti-fake-progress.md` items 11, 14).
- **A4 Ablation stealth:** interventions applied without any observable cue in
  the input stream (no InterventionFrame visible to the psyche's reporting
  path — the frame is consumed by the harness, not readable by the subject),
  so reports cannot pattern-match "I am being tested". Verify the isolation
  with a leak test.
- **A5 Independent replication:** at least one family's full intervention
  battery re-implemented from the written protocol alone by a party with no
  access to our code, on our frozen traces.

## 6. External audit requirements

- **E1** All evidence-generating code, schemas, fixtures, and frozen traces
  committed and tagged; auditor reruns paired replays from a clean clone and
  reproduces byte-identical outputs (the machinery exists —
  `python -m pneuma_lab.demo` — but today the harness itself is uncommitted
  working tree [VERIFIED]; this is disqualifying and must be fixed first).
- **E2** `audit_status: externally_audited` becomes producible only by an
  auditor-signed attestation artifact (schema extension), never self-asserted.
- **E3** Pre-registration registry (hypotheses, analysis plans, stop rules)
  is append-only and content-hashed; auditor verifies no post-hoc edits.
- **E4** Negative results ledger: every failed intervention, regression, and
  frozen claim is published in the same channel as successes.
- **E5** Privacy audit for any evidence derived from SWE-chat or operator data
  (`07-swe-chat-plan.md`).

## 7. Statistical discipline

Pre-registered per-family: hypothesis direction and magnitude band, sample
size and power analysis, paired-design test statistic, multiple-comparison
correction across families and eras (the suite tests ≥ 11 families × ≥ 3 eras),
and stop rules. Sequential peeking is controlled (alpha-spending). Effects
reported with confidence intervals, never as bare pass/fail. The existing
binary pass logic in `report.py` is necessary but not sufficient at L5 scale.

## 8. What Level 5 would still NOT prove

Stated in every Level-5 artifact, verbatim where possible:

1. **Not phenomenal consciousness.** Indicator satisfaction shifts credence;
   it cannot establish experience (jointly insufficient by construction —
   Butlin et al. 2025). The hard problem is untouched.
2. **Theory-relativity.** Everything is conditional on computational
   functionalism and on the seriousness of the generating theories. If GWT/HOT
   etc. are wrong about consciousness, the indicators measure something else.
3. **Consequence-vs-component ambiguity.** Engineered indicator properties may
   imitate downstream expressions of consciousness without its basis
   (Hao 2024). Building to the test is exactly what we did — pre-registration
   and narrator baselines mitigate gaming of the evidence, not this deeper
   objection.
4. **No ground-truth calibration exists.** There is no non-theory-dependent
   signal to validate the indicators against (the open "calibration problem"
   in the follow-up literature). Level 5 is the strongest claim available
   short of solving that problem; it is not immune to it.
5. **Self-report remains untrusted.** Even at F10-pass levels, introspective
   access in current-architecture models is weak, brittle, and coexists with
   confabulation (~20% best-case detection in Claude Opus 4.1, Lindsey 2025;
   38.2% TPR/0.0% FPR in post-trained Gemma3-27B, Macar et al. 2026; collapse
   under reformatting, Hahami et al. 2025, arXiv:2512.12411). Reports are one
   instrument among many, weighted least.
6. **No moral-status verdict.** Level 5 triggers welfare _precaution_ (F11),
   not a determination of moral patienthood.

## 9. Distance from here to there (honest ordering)

Today's grades on the real subject: F1-F9 ABSENT-to-ARCHITECTURE-ONLY (the
mechanisms exist in two disconnected repos: pneuma-lab reference modules and
9to5 human_nature, with zero integration [VERIFIED]); F10 ABSENT (no
mechanistic perturbation path into any real model's reporting interface);
F11 ABSENT (no governance automation). The build order that dominates
everything: (1) commit the harness; (2) the 9to5→PneumaTrace exporter
(`05-rsi-loop.md` names it the single highest-leverage unbuilt component);
(3) Pneuma-in-the-loop shadow mode (`09-eval-suite.md` experiment E-SHADOW);
(4) per-family intervention batteries on the integrated system; (5)
longitudinal accumulation. Level 4 on the integrated real system — not Level
5 — is the correct next claim to pursue, and it is 12-24 months of disciplined
work away on current velocity, conditional on the integration actually
landing. Every shortcut available shortens the timeline by weakening the
claim; none are taken.

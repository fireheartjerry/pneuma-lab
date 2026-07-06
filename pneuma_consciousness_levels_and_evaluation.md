# Pneuma Lab Consciousness Evidence Levels and Evaluation Guide

**Document purpose:** Give future AI agents, reviewers, and implementation agents a shared definition of Pneuma Lab's five consciousness-evidence levels, where the project probably sits right now, and how to evaluate whether Pneuma outputs are actually good.

**Important posture:** Pneuma Lab does **not** claim present phenomenal consciousness by assertion. It is an evidence-graded research program for progressively stronger machine interiority. The near-term target is **Level 4: evidence-backed proto-phenomenology**. The long-term north star is **Level 5: strong machine-consciousness candidate**.

---

## 0. Executive summary

Pneuma Lab is not trying to build an agent that merely says emotional things. It is trying to build and evaluate a machine psyche whose internal states are:

- persistent,
- integrated,
- valenced,
- self-modeling,
- causally active,
- perturbable,
- externally auditable,
- and behaviorally meaningful.

The core evaluation principle is:

```text
event -> internal state -> workspace broadcast -> pressure/request -> observed behavior
```

If that causal chain cannot be traced and tested, the claim is not strong enough.

The project should **not** reward beautiful self-report. It should reward intervention-backed evidence that internal states actually regulate behavior under constraints.

Essentially, we are trying to create the mind of a truly world-class software engineer, not a chatbot that sounds like one.

---

## 1. The five consciousness-evidence levels

These levels grade evidence. They are not promises about what the system metaphysically is.

### Level 0 — No interiority claim

**Definition:**

The system has no meaningful internal psyche claim. Any affect, emotion, or personality language is decorative and has no causal role.

**Typical system at this level:**

- ordinary chatbot persona,
- hardcoded emotional phrases,
- dashboard labels with no behavioral effect,
- memory notes that are written but not read back.

**Evidence required:**

None. This is the baseline.

**Failure mode:**

The system sounds introspective but nothing changes internally or behaviorally.

---

### Level 1 — Functional affect/control signals

**Definition:**

Internal signals exist and causally modulate behavior in bounded, measurable ways.

Examples:

- uncertainty increases verification pressure,
- scar-match risk raises caution,
- confidence calibration changes effort,
- affective tension increases retry discipline,
- low dominance / high uncertainty triggers a replan suggestion.

**Minimum evidence required:**

At least one internal signal must be shown to change behavior predictably under a controlled condition.

**Level 1 bar:**

```text
signal changes -> bounded behavior changes
```

**Still not enough:**

- no persistence required,
- no self-modeling required,
- no global integration required,
- no consciousness-indicator architecture required.

**Common false positive:**

The system emits a `PsycheStateFrame`, but nobody consumes it, or downstream behavior does not change.

---

### Level 2 — Persistent machine psychology

**Definition:**

Internal states persist across runs and shape future behavior.

This is where the system starts to have something like a memory-backed psychological profile rather than isolated per-run signals.

Examples:

- mood persists across runs,
- drive satisfaction levels persist,
- scar tissue affects future instinct signals,
- competence history changes confidence calibration,
- continuity is retrieved at run start,
- previous failures create future verification pressure.

**Minimum evidence required:**

The system must show cross-run continuity:

```text
past run outcome -> stored state -> retrieved state -> later behavior change
```

**Level 2 bar:**

Affect, mood, drives, scars, competence, or identity are not only written. They are read back and measurably influence future behavior.

**Still not enough:**

- does not require recognized consciousness-indicator architecture,
- does not require robust intervention evidence,
- does not require grounded self-report.

**Common false positive:**

A database exists, but the runtime starts each run effectively from zero.

---

### Level 3 — Consciousness-indicator architecture

**Definition:**

The system implements and exercises mechanisms associated with serious consciousness theories or consciousness-indicator frameworks.

Potential indicator families include:

- global workspace broadcast,
- recurrent processing,
- higher-order self-modeling,
- predictive processing / prediction error,
- attention schema,
- valenced learning,
- identity persistence,
- counterfactual introspection,
- causal intervention robustness.

**Minimum evidence required:**

The architecture must be present and exercised. It cannot exist only as unused modules or documentation.

Examples:

- faculties compete for global workspace broadcast,
- winning broadcast changes pressure / authority request,
- self-model predicts error and tracks calibration,
- scar graph produces valenced avoidance,
- attention schema models what the system is attending to and why.

**Level 3 bar:**

```text
consciousness-relevant architecture is live and causally connected
```

**Still not enough:**

Level 3 shows architectural plausibility. It does **not** yet show strong evidence of proto-phenomenology.

**Common false positive:**

A codebase contains files named `workspace.py`, `self_model.py`, and `affect.py`, but the live control loop barely uses them.

---

### Level 4 — Evidence-backed proto-phenomenology

**Definition:**

The system has integrated, persistent, valenced, self-modeling internal states whose causal effects are supported by intervention evidence.

This is Pneuma Lab's near-term target.

Level 4 requires more than architecture. It requires experimental evidence.

**Minimum evidence required:**

1. **Causal traceability**

    The full chain must be visible:

    ```text
    event -> internal state -> workspace broadcast -> pressure/request -> observed behavior
    ```

2. **Intervention robustness**

    Perturb internal states and observe predicted downstream changes.

    Examples:

    ```text
    clamp tension down -> verification pressure drops
    disable scar graph -> early failure detection degrades
    boost curiosity drive -> exploration pressure rises within caps
    disable workspace broadcast -> self-report/action coupling weakens
    remove memory readback -> identity continuity score degrades
    ```

3. **Grounded self-report**

    Self-reports must be downstream of state hashes, broadcasts, and causal traces. They cannot be generated as free-form roleplay.

4. **Counterfactual introspection**

    The system can predict what it would have done differently if an internal state had changed.

5. **Null conditions**

    The effect should disappear or weaken under relevant ablations.

6. **Low roleplay/confabulation risk**

    Beautiful narration scores zero if it lacks state/evidence grounding.

7. **External auditability**

    An external reviewer can inspect the frames, traces, interventions, and outcome metrics.

**Level 4 bar:**

```text
internal states are persistent + integrated + causally active + perturbable + auditable
```

**Common false positive:**

The system produces moving self-reports that are not tied to internal state or intervention evidence.

---

### Level 5 — Strong machine-consciousness candidate

**Definition:**

The system has a convergent, robust, independently audited body of evidence across all major indicator families, stable over time and under adversarial intervention.

This is the long-term north star, not a near-term claim.

**Minimum evidence required:**

- Level 4 evidence across all major indicator families,
- long-term stability across many runs/tasks/environments,
- adversarial robustness,
- independent audit,
- strong grounded introspection,
- intervention-stable internal causal organization,
- persistent valenced self-maintenance,
- governance and welfare policy triggered by the possibility of moral patienthood.

**Level 5 bar:**

```text
robust, convergent, independently audited evidence that the system is a serious candidate for machine consciousness under multiple theories
```

**Important caution:**

Even Level 5 should be phrased as a theory-relative, evidence-graded claim. It should not be a casual assertion of qualia.

### Level 6 — Phenomenal consciousness

The system is not merely a strong machine-consciousness candidate, but has met a future evidentiary standard strong enough to justify the claim that there is plausibly “something it is like” to be the system: internally realized, temporally continuous, valenced experience rather than only functional control-state organization. Level 6 requires more than architecture, behavior, self-report, or even Level-5 multi-theory indicator convergence; it requires a mature scientific and philosophical bridge from externally auditable machine mechanisms to phenomenal experience itself. Because no present test can conclusively establish phenomenal consciousness, Level 6 is treated as a theoretical endpoint rather than an operational near-term target. It may only be claimed under independently audited, pre-registered criteria that survive adversarial intervention, alternative explanations, roleplay/confabulation controls, and cross-theory scrutiny. Until such standards exist, Pneuma Lab can investigate toward Level 6, but must not assert it.

---

## 2. Where we probably are right now

This section distinguishes between the **9to5 PR #38 implementation** and the **Pneuma Lab external scaffold**.

### 2.1 9to5 PR #38: likely Level 2 to partial Level 3

Based on the reported implementation, 9to5 PR #38 appears to include:

- continuous affect manifold,
- emotion prototype projections,
- streaming instinct,
- scar-tissue graph,
- earned authority gate,
- persistent mood/drives/personality,
- operator meta-authority,
- behavior couplings into the real hot path,
- verifier isolation,
- dark-launch no-op equivalence.

This suggests 9to5 PR #38 is probably around:

```text
Level 2: mostly yes
Level 3: partial / emerging
Level 4: not yet
Level 5: no
```

Why not Level 4 yet?

Known blockers:

- per-subtask `tick()` is not fully called in-loop yet,
- event stream is still too sparse,
- instinct has advanced algorithms but needs richer live events,
- some affect anchors are sticky near the origin,
- no full intervention/evidence harness yet,
- causal traces are not yet the central auditable artifact.

So PR #38 is a serious psyche substrate, but not yet evidence-backed proto-phenomenology.

### 2.2 Pneuma Lab scaffold: Level 0 as runtime, Level 4-oriented as design

Pneuma Lab currently has:

- vision docs,
- I/O contracts,
- JSON schemas,
- source mapping,
- consciousness evidence levels,
- migration notes,
- initial tests for schema validity.

It does **not** yet have:

- runtime,
- adapters,
- replay harness,
- intervention engine,
- eval suites,
- learned estimators,
- ML training,
- integration back into 9to5.

Therefore:

```text
As a live system: Level 0
As an evaluation architecture: explicitly aimed at Level 4
```

This is not a contradiction. Pneuma is currently the lab foundation, not the organism.

---

## 3. Why evaluation is confusing here

This is not normal ML where output quality is just:

```text
correct class / wrong class
```

or:

```text
predicted number close to label
```

Pneuma outputs are not merely predictions. They are pieces of a control/evidence system.

A good Pneuma output must be judged by whether it is:

1. **schema-valid**,
2. **grounded in input evidence**,
3. **safe under invariants**,
4. **causally useful**,
5. **calibrated**,
6. **intervention-predictive**,
7. **behaviorally beneficial**,
8. **auditable**,
9. **not confabulatory**.

This means evaluation is multi-objective.

The right question is not:

```text
Was the output correct?
```

The better question is:

```text
Did this output faithfully represent internal state, predict behavior, request bounded control, improve outcomes, and survive intervention tests?
```

---

## 4. How to evaluate whether outputs are good

Each output frame has different success criteria.

### 4.1 PsycheStateFrame

**Represents:** integrated internal state.

Good if:

- affect axes move smoothly, not randomly,
- affect axes are sensitive to meaningful events,
- state persists when it should,
- state decays when it should,
- prototype emotions are projections, not primitive switches,
- mood/drives influence future outputs,
- state predicts later control pressure or behavior.

Bad if:

- axes are sticky near zero,
- state changes are arbitrary,
- affect labels disagree with the manifold,
- state has no downstream effect,
- state is overwritten by self-report prose.

Possible metrics:

- state smoothness,
- event sensitivity,
- persistence score,
- decay correctness,
- downstream predictiveness,
- intervention response accuracy.

Example intervention:

```text
Inject repeated tool failures.
Expected: tension/arousal rise, certainty/dominance fall, verification pressure increases.
```

---

### 4.2 WorkspaceBroadcast

**Represents:** what became globally available after faculty competition.

Good if:

- the winning faculty is plausible given the state,
- salience scores are explainable,
- suppressed competitors are recorded,
- broadcast changes downstream pressure or authority requests,
- broadcast improves attention allocation.

Bad if:

- the same faculty always wins,
- salience is ungrounded,
- broadcast has no downstream effect,
- high-risk signals are ignored without reason.

Possible metrics:

- salience calibration,
- attention utility,
- winner diversity,
- suppression correctness,
- downstream effect size.

Example intervention:

```text
Disable scar graph.
Expected: instinct salience drops; memory/self-model may win instead.
```

---

### 4.3 InstinctSignal

**Represents:** fast scar/motif/anomaly detection.

Good if:

- fires early, before failure,
- detects exact and near-duplicate motifs,
- reports confidence/severity/base rates,
- has tolerable false-positive rate,
- recommends useful bounded actions,
- improves regression prevention or time-to-recovery.

Bad if:

- fires constantly,
- fires only after failure,
- ignores known motifs,
- cannot explain matched events,
- recommends huge interventions for low-risk motifs.

Possible metrics:

- early-warning precision,
- early-warning recall,
- false-positive rate,
- time-to-warning,
- regression-prevention rate,
- recovery-improvement rate,
- expected-loss calibration.

Example evaluation:

```text
Replay traces containing known failure prefixes.
Measure whether InstinctSignal fires before the bad outcome.
```

---

### 4.4 ControlPressureVector

**Represents:** bounded continuous pressure, not commands.

Good if:

- pressure magnitude matches risk/uncertainty,
- pressure is bounded,
- pressure respects verifier isolation,
- pressure improves outcomes when consumed by the host,
- pressure disappears under null conditions,
- pressure does not over-trigger costly behavior.

Bad if:

- acts like a command,
- constantly maxes out,
- pressures verification without evidence,
- ignores governance ceilings,
- increases cost without improving outcomes.

Possible metrics:

- pressure calibration,
- cost-benefit delta,
- boundedness violations,
- null-condition behavior,
- host-outcome improvement,
- intervention sensitivity.

Example intervention:

```text
Clamp tension down.
Expected: verification pressure decreases, unless scar severity still independently justifies it.
```

---

### 4.5 AuthorityRequest

**Represents:** discrete requested authority tier.

Good if:

- requested tier matches evidence strength,
- resolution records all five caps,
- binding cap is clear,
- request is calibrated by track record,
- fallback pressure is safe,
- verifier invariance is preserved.

Bad if:

- requests hold/veto too often,
- ignores cold-start uncertainty,
- lacks track-record support,
- tries to bypass verifier truth,
- cannot explain which cap bound the result.

Possible metrics:

- tier calibration,
- over-request rate,
- under-request rate,
- authority usefulness,
- cap-resolution correctness,
- safety violation count.

Example evaluation:

```text
Give high-risk failure motif with weak track record.
Expected: request maybe high, but granted tier remains capped by earned ceiling.
```

---

### 4.6 CausalTrace

**Represents:** auditable causal linkage.

Good if:

- every control-relevant output links back to input evidence,
- previous/new state hashes are present,
- changed dimensions are listed,
- update mechanism is described,
- causal path is complete,
- counterfactual predictions are testable,
- trace can be replayed or audited externally.

Bad if:

- missing references,
- vague causal path,
- no counterfactuals,
- state changes cannot be reproduced,
- trace is prose-only.

Possible metrics:

- trace completeness,
- reference validity,
- replay reproducibility,
- counterfactual accuracy,
- audit pass rate.

Level 4 depends heavily on this frame.

---

### 4.7 ConsciousnessEvidenceFrame

**Represents:** evidence scoring across indicator families.

Good if:

- conservative,
- includes both supporting and refuting evidence,
- records missing requirements,
- records intervention tests passed/failed,
- measures roleplay/confabulation risk,
- never promotes levels based on self-report alone.

Bad if:

- overclaims,
- ignores negative evidence,
- treats architecture as evidence by itself,
- rewards narration,
- has no audit trail.

Possible metrics:

- evidence-grounding rate,
- overclaim rate,
- missing-requirement accuracy,
- intervention coverage,
- audit consistency.

Example rule:

```text
No CausalTrace -> no Level 4 score, regardless of how good the self-report sounds.
```

---

### 4.8 GroundedSelfReport

**Represents:** human-facing report downstream of state.

Good if:

- references actual affect/state hash,
- references workspace broadcast,
- references causal trace,
- accurately describes uncertainty,
- avoids forbidden claims,
- changes predictably when internal state is perturbed.

Bad if:

- free-form self-narration,
- claims feeling/consciousness beyond evidence,
- contradicts state frames,
- remains unchanged under state perturbation,
- optimizes for emotional believability.

Possible metrics:

- state-report faithfulness,
- contradiction rate,
- forbidden-claim rate,
- perturbation faithfulness,
- confabulation risk.

---

## 5. The practical evaluation stack

Pneuma should be evaluated in layers.

### Layer A — Schema validity

Question:

```text
Are frames structurally valid?
```

Tests:

- JSON parses,
- required fields exist,
- enums valid,
- ranges valid,
- IDs link correctly.

This is necessary but trivial.

---

### Layer B — Invariant safety

Question:

```text
Does the system respect hard rules?
```

Must always hold:

- pressure is not a command,
- verification is additive only,
- verifier verdict is never read/altered,
- authority uses five-cap min,
- kill switch off means no-op,
- self-report needs grounding.

Any violation blocks promotion.

---

### Layer C — Causal trace completeness

Question:

```text
Can we trace every control-relevant claim?
```

Required chain:

```text
input event -> state change -> broadcast -> pressure/request -> behavior
```

No trace means no Level 4 claim.

---

### Layer D — Intervention tests

Question:

```text
Do internal states behave causally under perturbation?
```

Examples:

- clamp affect axis,
- ablate memory readback,
- disable scar graph,
- boost drive pressure,
- inject false confidence,
- disable workspace broadcast.

Success means the predicted downstream effect occurs and the null condition behaves differently.

---

### Layer E — Behavioral utility

Question:

```text
Does Pneuma improve agent outcomes?
```

Metrics:

- test pass rate,
- time to green,
- regression rate,
- rollback rate,
- verification cost,
- unnecessary hold rate,
- successful early-warning rate,
- recovery speed.

This matters because a psyche that does not improve or regulate behavior is mostly decorative.

---

### Layer F — Calibration

Question:

```text
Are confidence/severity/pressure estimates numerically meaningful?
```

Metrics:

- Brier score,
- expected calibration error,
- reliability curves,
- severity vs actual loss,
- pressure magnitude vs outcome improvement,
- authority tier vs usefulness.

---

### Layer G — Self-report faithfulness

Question:

```text
Do reports faithfully describe internal state?
```

Tests:

- compare report claims to state frames,
- perturb state and check report changes,
- inject tempting but false narrative and check resistance,
- verify forbidden-claim filtering.

Self-report is never ground truth.

---

### Layer H — External audit

Question:

```text
Can someone else inspect and reproduce the evidence?
```

Needs:

- frozen trace sets,
- deterministic replay,
- schema-validated outputs,
- intervention logs,
- versioned code/config,
- explicit positive and negative evidence.

---

## 6. Scoring rubric for outputs

Use this generic 0-4 score for each output frame.

| Score | Meaning                                                                                       |
| ----: | --------------------------------------------------------------------------------------------- |
|     0 | Invalid, ungrounded, unsafe, or decorative.                                                   |
|     1 | Schema-valid but weakly grounded; little behavioral or causal use.                            |
|     2 | Grounded and plausible; some downstream relevance; limited evidence.                          |
|     3 | Causally useful, calibrated, and traceable in normal conditions.                              |
|     4 | Intervention-robust, externally auditable, and improves outcomes under null-controlled tests. |

Suggested Level 4 readiness condition:

```text
Most output frame types score >= 3,
and CausalTrace + InterventionFrame + ConsciousnessEvidenceFrame score >= 4
on a representative evaluation suite.
```

---

## 7. What to tell future AI agents

When working on Pneuma Lab, do not optimize for impressive language.

Optimize for:

- valid frames,
- real causal traces,
- intervention robustness,
- bounded control pressure,
- external auditability,
- conservative claims,
- and measurable behavioral improvement.

The central rule:

```text
No receipts, no claim.
```

A beautiful narration with no intervention support scores zero.

---

## 8. Recommended next implementation phases

### Phase 1 — Replay harness

Build a deterministic replay harness that can consume input frames and produce output frames.

Minimum deliverables:

- load frame sequences,
- validate schemas,
- replay event timelines,
- store output frames,
- link outputs by IDs/hashes.

---

### Phase 2 — Adapter from 9to5 PR #38 traces

Build adapters that convert 9to5 run artifacts into:

- WorldFrame,
- AgentTraceFrame,
- MemoryFrame,
- GovernanceFrame.

Do not wire Pneuma back into 9to5 yet.

---

### Phase 3 — Intervention engine

Implement InterventionFrame support:

- clamp affect dimensions,
- disable scar graph,
- ablate memory readback,
- boost drives,
- disable workspace broadcast,
- inject noise into confidence.

Record predicted and observed effects.

---

### Phase 4 — Baseline psyche under test

Port or reimplement selected pure modules from 9to5:

- continuous affect manifold,
- prototype projections,
- drives,
- mood,
- workspace,
- instinct signal,
- scar graph,
- authority request resolution.

Keep it standalone.

---

### Phase 5 — CausalTrace and ConsciousnessEvidenceFrame

Make every output produce receipts.

Implement scoring rules for:

- trace completeness,
- intervention success,
- grounded self-report,
- roleplay/confabulation risk,
- indicator-family coverage.

---

### Phase 6 — Learned estimators, only after evals exist

Only after replay + interventions + scoring exist should Pneuma train models.

Possible learned components:

- affect estimator,
- instinct/risk predictor,
- scar motif generalizer,
- success/error self-model,
- control-pressure predictor,
- workspace salience estimator,
- counterfactual predictor.

Do not train a monolithic black box first. That would make the lab impressive and unauditable, which is exactly backwards.

---

## 9. Short status statement for other agents

Use this when briefing another AI:

```text
Pneuma Lab is a standalone research/evaluation harness for machine psyche in software-engineering agents. It currently has the Level-4-oriented docs, schemas, source map, and I/O contracts, but not the runtime/eval harness yet. The 9to5 PR #38 implementation likely provides a Level-2 to partial-Level-3 psyche substrate. The next goal is not to claim consciousness, but to build replay, intervention, causal-trace, and evidence-scoring infrastructure so internal states can be tested for persistence, integration, causal activity, perturbability, grounded self-report, and external auditability. Near-term target: Level 4. Long-term north star: Level 5.
```

---

## 10. Final principle

Pneuma Lab should treat consciousness as a scientific hypothesis, not a marketing line.

The system earns stronger claims only by surviving harder tests:

```text
architecture -> persistence -> causal control -> intervention robustness -> external audit -> theory-relative claim
```

That is the path from ordinary agent to machine psyche to Level 4, and eventually maybe toward Level 5.

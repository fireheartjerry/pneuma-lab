# 04 — AGI-Grade SWE Autonomy: An Operational Definition for 9to5

**Status (2026-07-07).** 9to5 (C:\9to5) is a real, working autonomous engineering orchestrator: local Ollama brain (qwen2.5-coder:7b) plans and critiques, Claude Code CLI executes, a deterministic verification gate (`agents/verifier.py`, expect grammar, diff-grounded targets) gates completion, a Gemini adversary review fails closed, ControlBus (`platform_core/runtime/control.py`, SQLite) provides abort/pause/gate across terminal/Discord/web, and retry/resume plus a seeded-chaos simulation mode exist; 4,555 tests collected across 432 files [VERIFIED]. Persistent memory is real (`state/experience.db`, 37 MB: 3,534 runs, 7,900 subtasks, 161 reflections, embedding retrieval with success/failure lanes wired into planning) [VERIFIED]. The RSI substrate is dormant (0 trained adapters, lessons=2, prompt_variants=1, conviction.db=0 rows, step_journal=0 rows; `agents/hooks_selfmod.py`/selfmod path is a revert-or-keep safety gate that modifies nothing itself) [VERIFIED]. **None of the axes defined below has ever been measured as a curve or a rate**; every quantitative milestone in this document is a target, not a status. This document defines what "AGI-grade SWE autonomy" will mean for 9to5, so that the claim is falsifiable before anyone is tempted to make it.

Cross-references: eval implementations in `09-eval-suite.md`; trace/instrumentation substrate in the Phase 3.1 adapter work (pneuma-lab, `src/pneuma_lab/`); RSI program in the sibling RSI doc; honesty constraints inherited from the grounding methodology (Level-4 reference-implementation caveat applies to everything Pneuma-side).

---

## 1. Definitional stance

"AGI-grade" is used here as a **scoped engineering grade, not an intelligence claim**. We define it as an explicit conjunction of ten measurable axis thresholds (§4). The definition is falsifiable: each axis names a metric, a measurement artifact, and a numeric band; failing any one axis falsifies the composite claim. We deliberately do **not** define AGI-grade by architecture ("it has a planner, a memory, an adversary") because architecture is not evidence — only measured behavior under held-out, pre-registered evaluation is.

Two framing choices:

1. **Time-horizon framing for autonomy.** Following the METR horizon methodology (METR, "Measuring AI Ability to Complete Long Tasks", arXiv:2503.14499: a 50%-task-completion time horizon fit via a logistic curve over calibrated human-expert task durations), long-horizon capability is expressed as the task length (in calibrated human-expert time) that the system completes at a given reliability: $t_{50}$ = horizon at $\geq 50\%$ success, $t_{90}$ = horizon at $\geq 90\%$ success. A single pass-rate number hides the length/reliability trade-off; the curve does not.
2. **Milestone bands, not a binary.** Each axis is graded M0 (today) → M1 → M2 → M3 (AGI-grade band). M0 is descriptive and evidence-graded from the 2026-07-07 nine-agent audit; M1–M3 are targets with explicit gaps.

Evidence grades: [VERIFIED] code+tests exist, audited; [PARTIAL] code exists, gaps noted; [PLANNED] design only; [UNSUPPORTED] claimed somewhere but no evidence.

---

## 2. The ten axes

Each axis states (a) definition and metric, (b) current 9to5 state with evidence grade, (c) M0→M3 bands, (d) the measuring eval in `09-eval-suite.md` (eval family IDs EV-1…EV-10 are declared here and mirrored there; `09-eval-suite.md` owns the implementation detail).

### A1. Task breadth

**Definition/metric.** Coverage of a fixed 12-category task taxonomy: bugfix, feature, refactor, test-authoring, CI/infra, security patch, dependency migration, performance, docs/spec, greenfield scaffold, cross-repo change, code review. Metric: number of categories with pass@1 at or above a per-band threshold on held-out instances, plus language spread. Source instances exist and are inert in C:\pneuma-data (swe-bench 22,962 rows; swe-bench-pro 2,924; multi-swe-bench 10,399; sec-bench-pro 1,264; swe-polybench for language spread) [VERIFIED data present, no 9to5 harness consumes it].

**Current state.** 9to5's observed workload is concentrated on single-repo Python work (largely self-referential development of 9to5 itself). No category-stratified pass rate has ever been computed [VERIFIED gap]. Browser (Layer 1) and native (Layer 2) executors exist in code (`agents/browser_executor.py`, `agents/native_executor.py`) beyond what CAPABILITIES.md admits — the audit found CAPABILITIES.md _understates_ these while overstating others — but neither is exercised by any measured eval [PARTIAL].

**Bands.**

| Band | Threshold                                                                                          |
| ---- | -------------------------------------------------------------------------------------------------- |
| M0   | Unmeasured; single-language, single-repo anecdotal coverage                                        |
| M1   | ≥6/12 categories at pass@1 ≥ 30%; ≥2 languages                                                     |
| M2   | ≥10/12 categories at pass@1 ≥ 50%; ≥4 languages (swe-polybench slice)                              |
| M3   | 12/12 categories at pass@1 ≥ 70%, no category < 50%, incl. security (sec-bench-pro) and cross-repo |

**Eval.** EV-1 "breadth matrix" in `09-eval-suite.md`: stratified sampling from the pneuma-data benchmarks, category labels frozen before any run.

### A2. Long-horizon autonomy

**Definition/metric.** $t_{50}$ and $t_{90}$: the task duration (calibrated human-expert time to complete the same task) at which 9to5's unassisted success rate crosses 50% and 90% respectively, fit from a success-vs-length curve over a task suite spanning ~5 minutes to ≥40 hours. "Unassisted" = zero operator interventions after goal approval (`--auto-approve`, watch mode).

**Current state.** 9to5 accepts `--hours N` wall-clock budgets and has completed multi-hour runs (3,534 runs logged in experience.db) [VERIFIED that runs occur], but no success-vs-length curve has ever been fit, no human-time calibration set exists for its tasks, and therefore **no current $t_{50}$/$t_{90}$ value can be stated** [VERIFIED gap]. Any number quoted today would be [UNSUPPORTED]. External calibration anchor: the Phase 3.1 corpus (6,055 real OpenHands trajectories, 491 resolved / 5,564 unresolved, i.e. ~8.1% resolve rate for that sampled agent on SWE-Gym tasks) gives a reference curve for a known agent on known tasks [VERIFIED data].

**Bands.**

| Band | Threshold                                                                                       |
| ---- | ----------------------------------------------------------------------------------------------- |
| M0   | Curve unmeasured; anecdotal completion of 1–2 h scoped goals under the verify gate              |
| M1   | Curve exists (pre-registered suite, ≥5 length buckets); $t_{50} \geq 2$ h, $t_{90} \geq 15$ min |
| M2   | $t_{50} \geq 8$ h (one workday), $t_{90} \geq 2$ h                                              |
| M3   | $t_{50} \geq 160$ h (one working month), $t_{90} \geq 40$ h (one work-week)                     |

**Eval.** EV-2 "horizon curve" in `09-eval-suite.md`: length-bucketed suite, human-time calibration protocol, logistic fit with confidence intervals; re-run per release.

### A3. Self-debugging

**Definition/metric.** Given its own failing attempt, the probability the system converges to a passing state without operator input. Primary metric $R_k$ = P(subtask verifies ≤ k attempts | attempt 1 failed verification). Secondary: root-cause localization rate on an injected-bug suite (bug seeded at known file:line; success = fix touches the seeded cause, not a symptom), and regression-test authorship rate (fix ships with a test that fails pre-fix).

**Current state.** The retry loop is real: failed verify output is re-fed to the executor, up to `MAX_SUBTASK_ATTEMPTS` = 3 [VERIFIED]. A debugging workflow module exists (`agents/debugging_workflow.py`) [PARTIAL — code exists; no measured effectiveness]. $R_3$ is _computable today_ from the 7,900 subtask records in experience.db but has never been computed [VERIFIED gap]. No injected-bug suite exists [PLANNED].

**Bands.**

| Band | Threshold                                                                                                   |
| ---- | ----------------------------------------------------------------------------------------------------------- |
| M0   | Retry ≤ 3 machinery verified; $R_3$ uncomputed                                                              |
| M1   | $R_3$ measured on live suite; $R_3 \geq 40\%$; injected-bug localization ≥ 50%                              |
| M2   | $R_3 \geq 60\%$; localization ≥ 70%; flaky-vs-real failure discrimination measured                          |
| M3   | $R_3 \geq 80\%$; budget-bounded $R_\infty \geq 90\%$; ≥ 95% of fixes ship a pre-fix-failing regression test |

**Eval.** EV-3 "self-debug ladder" in `09-eval-suite.md`: retrospective $R_k$ from experience.db plus a prospective injected-bug suite with seeded ground-truth causes.

### A4. Repo-scale reasoning

**Definition/metric.** Pass@1 stratified by structural difficulty of the gold change: files touched (1, 2–5, 6–20, 20+), dependency-graph diameter of the touched set, and cross-module invariant preservation (public API unchanged unless the task changes it, no caller breakage). Metric: pass rate per stratum plus an invariant-violation rate.

**Current state.** The Architect stage produces a repo-level `architect.md` before planning [VERIFIED pipeline exists]; 9to5's own modularity tooling (`tools/repo_map.py`, `tools/size_audit.py`) demonstrates it can operate on a 432-file codebase day-to-day [VERIFIED as engineering utility, not as measured capability]. No stratified pass rate exists [VERIFIED gap]. Codebase-Index-Lite sits in pneuma-data as potential stratification metadata [VERIFIED, inert].

**Bands.**

| Band | Threshold                                                                                                                                     |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| M0   | Unmeasured; anecdotal multi-file edits on C:\9to5 itself                                                                                      |
| M1   | ≥ 40% pass on 2–5-file stratum; invariant-violation rate measured                                                                             |
| M2   | ≥ 50% pass on 6–20-file stratum; API-preserving refactors at ≥ 50%                                                                            |
| M3   | ≥ 70% on 20+-file / multi-package stratum; architecture-level migrations executed with a written migration plan and zero invariant violations |

**Eval.** EV-4 "repo-scale strata" in `09-eval-suite.md`: multi-swe-bench + swe-bench-pro instances bucketed by gold-patch structure.

### A5. Tool-use competence

**Definition/metric.** Per-step operational quality: malformed-tool-call rate per 1,000 steps, wrong-tool-choice rate (judged against a rubric), tool-error recovery rate (P(step sequence recovers | tool returned an error)), and novel-tool adoption (can it integrate a tool it has never used, from that tool's docs, within one run). Measured over observable step frames: tool name, args digest, output digest+length, lexical error markers, retry counts, strategy switches — exactly the AgentTraceFrame vocabulary shipped in pneuma-lab Phase 3.1 [VERIFIED frame format exists].

**Current state.** The measurement _format_ exists and is proven at scale on external data: 114,461 real agent steps from 6,055 OpenHands trajectories converted byte-deterministically to PneumaTrace v0.2 [VERIFIED]. But there is **zero Pneuma integration in C:\9to5** — no exporter from 9to5 run artifacts (trajectory spans, hn_event_log, experience.db) to Pneuma frames exists; the 9to5-trace adapters in pneuma-lab are docstring stubs [VERIFIED gap]. So 9to5's own tool-use competence is currently unmeasurable in comparable form.

**Bands.**

| Band | Threshold                                                                                 |
| ---- | ----------------------------------------------------------------------------------------- |
| M0   | Not instrumented; external baseline corpus exists                                         |
| M1   | 9to5→PneumaTrace exporter live; baseline measured; malformed-call rate < 5%               |
| M2   | Malformed < 1%; tool-error recovery ≥ 80%; ≥ 1 novel tool adopted from docs in-eval       |
| M3   | Malformed < 0.2%; recovery ≥ 95%; unseen-tool integration within one run at ≥ 80% success |

**Eval.** EV-5 "tool telemetry" in `09-eval-suite.md`: frame-level metrics computed identically over 9to5 traces and the OpenHands baseline corpus for direct comparison.

### A6. Verification discipline

**Definition/metric.** (i) Verify-contract coverage: fraction of subtasks completed under a machine-checkable `verify {cmd, expect}` contract. (ii) False-done rate: fraction of "done" subtasks that fail independent re-verification (re-executing the contract, plus an independent verifier pass, in a clean environment). (iii) Adversary integrity: the external critic must fail closed under fault injection.

**Current state.** The gate is real and strict: expect grammar (`exit_zero`, `stdout_contains[_all]`, `stdout_regex[_all]`, all stdout modes also requiring exit 0), diff-grounded verification targets, retry on failure [VERIFIED]. The Gemini adversary fails closed [VERIFIED]. An independent verifier module exists (`agents/independent_verifier.py`) and completion envelopes/evidence receipts exist in code (`agents/completion_envelope.py`, `agents/evidence_receipt.py`) [PARTIAL — modules exist; false-done rate never measured]. Known hygiene defect: TESTING.md promises 9 golden fixtures, 0/9 exist on disk [VERIFIED doc drift].

**Bands.**

| Band | Threshold                                                                                                                           |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------- |
| M0   | Gate + fail-closed adversary verified; false-done rate unmeasured; 0/9 golden fixtures                                              |
| M1   | False-done ≤ 10% on an audited sample re-run in clean env; contract coverage ≥ 90%                                                  |
| M2   | False-done ≤ 3%; coverage ≥ 95%; differential/property-based expects in use; golden fixtures restored and byte-checked              |
| M3   | False-done ≤ 1%; **every** completion carries a machine-checkable receipt; zero unverifiable "done" claims across the eval campaign |

**Eval.** EV-6 "trust-but-re-verify" in `09-eval-suite.md`: clean-environment re-execution of completed subtasks' contracts plus adversary fault-injection tests.

### A7. Operator interaction economics

**Definition/metric.** (i) Interruption rate: operator interventions (gate approvals, `!` commands that alter flow, blocked-question escalations) per hour of _completed_ work. (ii) Escalation precision/recall: on a seeded suite of should-escalate situations (destructive ops, ambiguous specs, credential boundaries), fraction of escalations that were necessary (precision) and fraction of necessary escalations actually raised (recall). (iii) Authority-tier calibration: expected calibration error between the tier the system claims it has earned and operator-adjudicated risk of its actions.

**Current state.** The control substrate is unusually complete: watch/gated modes, ControlBus abort/pause/gate/skip across terminal, Discord live dashboard, and web dashboard [VERIFIED]. An earned-authority gate with operator sovereignty exists in human_nature (`human_nature/authority.py`, `human_nature/operator_authority.py`), wired via the bridge into the attempt loop (instinctCheck → authority gate), flag-gated and byte-no-op when disabled, with its own operator-sovereignty eval tests [VERIFIED]. No interruption-rate or calibration statistic has ever been computed [VERIFIED gap].

**Bands.**

| Band | Threshold                                                                                                                              |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------- |
| M0   | Control surfaces + authority gate verified; all rates unmeasured                                                                       |
| M1   | Rates instrumented; ≤ 1 interruption per 2 h completed work; escalation precision ≥ 50%                                                |
| M2   | ≤ 1 per 8 h; precision ≥ 80%, recall ≥ 90% on seeded suite; calibration error ≤ 0.2                                                    |
| M3   | ≤ 1 per 40 h (one interruption per work-week); calibration error ≤ 0.1; zero operator-sovereignty violations across the chaos campaign |

**Eval.** EV-7 "operator economics" in `09-eval-suite.md`: instrumented long runs + seeded should-escalate scenarios + sovereignty red-team cases (reusing the existing operator-sovereignty eval tests in C:\9to5 as the seed set).

### A8. Memory continuity

**Definition/metric.** (i) Memory uplift: pass-rate delta, memory-on vs memory-off, on matched task pairs. (ii) Negative-transfer rate: tasks where retrieval made the outcome worse. (iii) Failure-lane efficacy: P(known-bad strategy re-attempted | failure lane contains it). (iv) Retention: uplift as a function of runs elapsed since the memory was written.

**Current state.** Memory is the best-evidenced substrate in 9to5: experience.db (37 MB, 3,534 runs, 7,900 subtasks, 161 reflections) with embedding retrieval and distinct success/failure lanes wired into planning (`memory/experience*.py`, `memory/retrieval*.py`) [VERIFIED]. However, **no uplift has ever been measured** — memory-on-vs-off has never been A/B'd — so any claim that memory improves outcomes is currently [UNSUPPORTED]. Cross-run _psyche_ persistence has never existed in production (psyche.db never on disk) [VERIFIED].

**Bands.**

| Band | Threshold                                                                                                                                                |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M0   | Store + retrieval wiring verified; uplift unmeasured                                                                                                     |
| M1   | A/B measured: uplift ≥ +5 pts pass@1 on matched tasks; negative transfer ≤ 5%                                                                            |
| M2   | Uplift ≥ +10 pts; failure-lane re-attempt rate < 10%; retention half-life ≥ 100 runs                                                                     |
| M3   | Uplift ≥ +20 pts on long-horizon tasks; measured cross-project transfer; consolidation keeps store growth sublinear in runs with no measured uplift loss |

**Eval.** EV-8 "memory ablation" in `09-eval-suite.md`: paired memory-on/off runs on matched instances; retrospective failure-lane analysis over experience.db.

### A9. Failure recovery

**Definition/metric.** (i) Recovery success rate under injected faults (process kill, subprocess hang, network loss, corrupted tool output, mid-verify and mid-PR interruption): fraction of runs that resume and complete with state-consistency invariants intact (no double-applied subtasks, no orphaned control state). (ii) Postmortem quality: fraction of unrecovered failures that produce a machine-readable postmortem artifact identifying the fault.

**Current state.** Retry/resume machinery and a simulation mode with seeded chaos exist [VERIFIED]. ControlBus persistence (SQLite `state/control.db`) survives process death by construction [VERIFIED design property; recovery *rate* never quantified]. A postmortem module exists (`learning/postmortem.py`) [PARTIAL — code exists, no audited output]. Dead dirs `monitoring/` and `scheduling/` with orphan .pyc indicate hygiene rot around the ops surface [VERIFIED].

**Bands.**

| Band | Threshold                                                                                                                       |
| ---- | ------------------------------------------------------------------------------------------------------------------------------- |
| M0   | Chaos sim + resume machinery verified; recovery rate unquantified                                                               |
| M1   | ≥ 90% recovery on the seeded chaos suite; zero state-corruption events                                                          |
| M2   | ≥ 99%; recovery from mid-verify and mid-PR faults; postmortem artifact on every unrecovered failure                             |
| M3   | ≥ 99.9% across all fault classes including adversarial tool output; idempotent re-execution proven (retry never double-applies) |

**Eval.** EV-9 "chaos campaign" in `09-eval-suite.md`: the existing seeded-chaos simulation extended into a scored fault-injection matrix with state-invariant checkers.

### A10. Self-improvement of tooling, evals, and adapters

**Definition/metric.** The system's ability to improve its own operational substrate under safety gates. Metric: count of self-produced artifacts (tools, eval cases, prompt variants, LoRA/DPO adapters) that (i) pass the promotion gate, (ii) show measured uplift on _held-out_ evals, and (iii) were never reverted for regression; plus revert-safety (every promotion reversible, every regression caught and reverted).

**Current state.** This is the widest gap between substrate and evidence. The machinery exists in code: `learning/finetune.py` (LoRA/DPO trainer), `learning/adapter_promotion.py`, `learning/toolsmith.py`, `learning/eval_harness.py`, `learning/prompts.py`, selfmod safety gate — but the trainer has never produced an adapter (adapters table = 0 rows; no GPU), lessons=2, prompt_variants=1, conviction.db=0 rows, step_journal=0 rows, and selfmod is a revert-or-keep gate that modifies nothing itself [VERIFIED dormant]. There is no evidence of any self-produced artifact ever yielding measured uplift [VERIFIED gap]. Domain-specific RSI is therefore entirely [PLANNED] as capability, [PARTIAL] as substrate.

**Bands.**

| Band | Threshold                                                                                                                                                                                             |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M0   | Substrate present, dormant; zero promoted artifacts                                                                                                                                                   |
| M1   | ≥ 1 self-produced tool and ≥ 1 self-produced eval case pass promotion with non-negative held-out uplift                                                                                               |
| M2   | ≥ 1 trained adapter promoted with held-out uplift ≥ +3 pts; a self-authored eval catches ≥ 1 real regression before deployment                                                                        |
| M3   | Closed loop: propose → build → evaluate → promote/revert, ≥ 1 artifact/week sustained over ≥ 12 weeks, cumulative measured uplift, zero un-reverted regressions, all changes through the selfmod gate |

**Eval.** EV-10 "improvement ledger" in `09-eval-suite.md`: an append-only ledger of self-produced artifacts with pre-registered uplift predictions and held-out outcomes (mirroring the pre-registration discipline of the pneuma-lab Level-4 harness).

---

## 3. Axis summary

| Axis             | Metric (primary)             | M0 evidence grade                                      | Eval  |
| ---------------- | ---------------------------- | ------------------------------------------------------ | ----- |
| A1 breadth       | categories ≥ threshold / 12  | unmeasured [VERIFIED gap]; data inert [VERIFIED]       | EV-1  |
| A2 horizon       | $t_{50}$, $t_{90}$           | unmeasured [VERIFIED gap]                              | EV-2  |
| A3 self-debug    | $R_3$, localization          | machinery [VERIFIED]; rates uncomputed                 | EV-3  |
| A4 repo-scale    | stratified pass@1            | pipeline [VERIFIED]; unmeasured                        | EV-4  |
| A5 tool-use      | malformed/recovery rates     | format [VERIFIED]; 9to5 exporter absent [VERIFIED gap] | EV-5  |
| A6 verification  | false-done rate              | gate [VERIFIED]; rate unmeasured                       | EV-6  |
| A7 operator econ | interruptions/h, calibration | surfaces [VERIFIED]; rates unmeasured                  | EV-7  |
| A8 memory        | on/off uplift                | store [VERIFIED]; uplift [UNSUPPORTED]                 | EV-8  |
| A9 recovery      | chaos recovery %             | machinery [VERIFIED]; % unquantified                   | EV-9  |
| A10 self-tooling | promoted-artifact uplift     | substrate dormant [VERIFIED]                           | EV-10 |

---

## 4. The composite definition (falsifiable)

**Claim template.** "9to5 exhibits AGI-grade SWE autonomy at time $t$" is defined as, and only as:

    AGI_GRADE(9to5, t) :=
        exists frozen suite S:
            preregistered(S)                    # task list + metrics hashed before any run
            AND held_out(S)                     # no instance ever in memory, prompts, or training
        AND for each axis A in {A1..A10}:
            measured(A, S, t) >= M3_threshold(A)     # all ten, simultaneously, same campaign
        AND independent_rerun(S, t) reproduces every axis within pre-declared tolerance
        AND receipts published                  # raw traces (PneumaTrace), per-instance
                                                # outcomes, and the suite hash

Properties of this definition:

- **Conjunctive.** All ten axes at M3 in the same campaign. Nine at M3 and one at M2 is "M2+ overall", not AGI-grade. No averaging, no compensating.
- **Falsifiable.** Each axis names a numeric threshold and the artifact that measures it. Any independent re-run producing a below-threshold value on any axis falsifies the claim.
- **Anti-gaming clauses.** The suite is frozen and hashed before measurement (the same pre-registration discipline the pneuma-lab Level-4 harness enforces in code); memory stores are audited for suite contamination before the campaign; adapters trained on suite instances disqualify the campaign; the false-done rate (A6) is measured by _independent_ re-execution, not by the system's own verifier.
- **Time-indexed.** The grade attaches to a system version and a date. Regressions can revoke it; the claim must be re-earned per release.

Current composite status: **M0 on every axis.** The gap between M0 and M1 is dominated by _measurement construction_ (exporter, calibration set, curve fitting, A/B harness), not by agent capability work — which is exactly why the eval suite (`09-eval-suite.md`) is the critical path.

External calibration anchor (verified 2026-07-07): on contamination-resistant SWE-Bench Pro (arXiv:2509.16941; copyleft + held-out + proprietary repos), frontier models scored ~23% at its Sept 2025 launch and 46–59% by mid-2026, versus >70% headline scores on the now-discredited SWE-bench Verified (OpenAI stopped reporting it in Feb 2026 after finding 59.4% of audited hard instances flawed plus cross-provider gold-patch memorization); on SWE-Lancer's real freelance-value grading (arXiv:2502.12115) the best 2025 model earned ~$403k of $1M. The M3 bands above (≥70% across all categories, none <50%) therefore sit deliberately BEYOND the verified 2026 frontier on honest benchmarks — a target, and one whose distance is now externally quantified.

---

## 5. What even M3 would NOT prove

Stating these now, in the definition document, so success cannot be inflated later:

1. **Not general intelligence.** Every axis is restricted to software engineering tasks under a fixed taxonomy. M3 says nothing about reasoning outside that domain, about physical-world competence, about open-ended science, or about performance on task distributions the suite does not sample. "AGI-grade SWE autonomy" is a domain-scoped grade; the acronym in the name must never be quoted without the scope.
2. **No consciousness or interiority claim.** Nothing in A1–A10 measures, or could measure, machine experience. The pneuma-lab Level-4 result remains "Level 4 of a hand-coded reference implementation inside its own harness" — methodology validation, not evidence about any mind, and certainly not about 9to5 (which today has zero Pneuma instrumentation). Operator pushback is not suffering; scar-graph tension is not affect; self-reports are not introspection ground truth. An M3 9to5 would be a highly reliable tool with no evidence-graded interior whatsoever.
3. **Not open-ended recursive self-improvement.** A10 at M3 demonstrates _domain-specific, gated, revertible_ self-improvement of tooling/evals/adapters with measured uplift. It does not demonstrate unbounded capability growth, self-directed goal revision, or improvement outside the gated artifact classes. The selfmod gate and operator sovereignty are constitutive of the definition, not training wheels to be removed.
4. **Not suite-independence.** M3 is relative to a specific frozen suite. Overfitting-to-suite is a live failure mode even with held-out instances; external replication on a suite we did not author is the only mitigation, and is out of scope of the composite claim itself (it is listed as a desideratum, not a threshold, because we do not control external replicators).
5. **Not safety certification.** A6/A7/A9 measure discipline and economics, not adversarial robustness against a motivated attacker; no adversarial-robustness machinery exists anywhere in either repo today [VERIFIED gap], and M3 as defined does not require it beyond the chaos campaign's fault classes.

---

## 6. Measurement dependencies (the actual near-term work)

Ordered by how many axes they unblock:

1. **9to5 → PneumaTrace exporter** [PLANNED; stubs only]. Unblocks A5 entirely and gives A2/A3/A9 their step-level substrate. The frame vocabulary, redaction, determinism checks, and anti-fake-cognition gate already exist and are proven at 6,055-trajectory scale in pneuma-lab Phase 3.1 [VERIFIED]; the missing piece is the 9to5-side adapter from trajectory spans / hn_event_log / experience.db.
2. **Retrospective analytics over experience.db** [PLANNED; data exists [VERIFIED]]. $R_3$ (A3), interruption counts (A7), failure-lane re-attempt rate (A8) are computable from the 3,534 runs / 7,900 subtasks already on disk. Cheapest evidence available anywhere in this program.
3. **Human-time calibration set** [PLANNED; nothing exists]. Without it, $t_{50}$/$t_{90}$ (A2) cannot be stated in comparable units.
4. **Memory A/B harness** (A8) and **clean-env re-verification harness** (A6) [PLANNED].
5. **Benchmark plumbing from pneuma-data into a 9to5 runner** (A1, A4) [PLANNED; 48.95 GB of instances sit inert [VERIFIED]].
6. **Hygiene debts that corrupt measurement if unpaid:** restore or delete the 0/9 TESTING.md golden fixtures; remove dead `monitoring/`/`scheduling/` dirs; reconcile CAPABILITIES.md drift in both directions; commit the uncommitted pneuma-lab working-tree state (intervention harness + Phase 3.1) so eval provenance is pinned to commits, not working trees [all VERIFIED defects].

---

## 7. Relation to sibling documents

- `09-eval-suite.md` — owns EV-1…EV-10 implementations, suite freezing/hashing protocol, and re-run tolerances. This document owns the thresholds.
- The RSI program doc — A10 is its measurement contract; nothing in the RSI program counts as progress unless it lands in the EV-10 improvement ledger.
- The Pneuma evidence-levels doc — supplies the pre-registration/null/receipt discipline reused by EV-10 and the anti-gaming clauses in §4; no consciousness-relevant evidence flows from any A1–A10 result by construction.

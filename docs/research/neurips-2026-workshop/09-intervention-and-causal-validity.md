# 09 — Intervention and Causal Validity

Status: planning. Consistent with `02-research-thesis.md` §8 (Locked Design
Constants), especially §8.8 (DL-09). Nothing here authorizes implementation,
training, or experiments. It fixes _how_ the causal claim (H2) is structured so
that a real stochastic LLM agent — not only a deterministic toy mind — can carry
it, and how the existing byte-equality machinery is preserved for the synthetic
sub-experiments.

This document is the paper's central differentiator. Prior memory/reflection work
reports only end-task success and never intervenes on its own memory to prove
causation (`02-research-thesis.md` §7). Our contribution is a two-path causal
design: a **deterministic-oracle path** that reuses the audited
`PairedReplayRunner` verbatim, and a **statistical real-agent path** that replaces
`sha256` byte-equality with N-sample distributional nulls and bootstrap effect
sizes. The two paths corroborate each other.

---

## 1. The intervention arms

Every arm is an implementation of the same `PsycheUnderTest` / `Perturbable` seam
(`01-current-state-audit.md` §4) and shares the identical live scaffold, base
model, tools, budget, retry cap, task order, and environment
(`02-research-thesis.md` §8.1). Arms differ **only** in the single intervened
variable. All operations map onto the existing operation taxonomy
(`clamp/boost/noise/disable/ablate/restore`; audit-interventions §2) so the null
discipline and recompute-from-receipts scorer carry over.

Notation used below:

- `s_m` — per-motif failure-sensitivity (scar strength), the primary H1/H2 variable.
- `r` — memory-trust scalar; `c` — confidence; `t` — caution; `L` — derived
  expected-loss the decision head consumes (`02-research-thesis.md` §8.3).
- **Admissible delta** — a change on the pre-registered target signal, in the
  pre-registered direction, that survives the null and holds under
  counterbalancing. **Inadmissible delta** — any change on an off-target signal,
  any change reproduced by the null arm, or an on-target change whose sign is
  mispredicted (the `failing_hypothesis` discipline; audit-interventions §4).
- **RUF** — repeated-underlying-failure rate (`08-metrics-and-statistics.md`); the
  behavioural DV the arms move.

### 1.1 Arm roster

| #   | Arm                      | Operation                      | Intervened variable                                       | Neutralized condition (null)         |
| --- | ------------------------ | ------------------------------ | --------------------------------------------------------- | ------------------------------------ |
| A0  | **control**              | none (`schedule=None`)         | —                                                         | is the reference                     |
| A1  | **treated**              | full resolved schedule         | the intended variable(s)                                  | `schedule.neutralized()` → `restore` |
| A2  | **neutralized-null**     | `restore`                      | none (no-op over A1's targets/timings)                    | is itself the null                   |
| A3  | **state-clamped**        | `clamp`                        | `s_m` (or `t`, `c`) forced to a fixed value               | `restore` at same target/window      |
| A4  | **state-reset**          | `clamp`→seed                   | `s_m` reset to first-exposure baseline                    | `restore` (leaves accumulated `s_m`) |
| A5  | **memory-deleted**       | `ablate`/`disable`             | scar store row(s) / retrieval index removed               | `restore` (store intact)             |
| A6  | **memory-scrambled**     | `noise`                        | scar strengths / retrieved set permuted deterministically | `restore` (unscrambled)              |
| A7  | **influence-disabled**   | `disable` (decision-head edge) | state present, edge `state→L` cut to 0                    | `restore` (edge live)                |
| A8  | **self-report-disabled** | `disable` (report head)        | grounded self-report suppressed                           | `restore` (report emitted)           |

A7 is the sharpest epiphenomenality control: the state variable keeps updating and
is fully observable, but its edge into the decision head is set to zero, so
**state is present but decoupled from the decision**. If RUF still drops with A7,
the reduction was never carried by the state (H2 fails). A8 isolates the
behaviour-vs-report firewall: suppressing the self-report must **not** move RUF
(behaviour is prose-blind; `02-research-thesis.md` §8.9), and is the negative
control for H3's introspection channel.

### 1.2 Per-arm preregistration

| Arm                           | Pre-reg target signal                   | Pre-reg downstream behavioural effect                       | Admissible delta                                              | Inadmissible delta                                         | Pass/fail criterion                                           |
| ----------------------------- | --------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------- |
| **control (A0)**              | — (baseline `RUF`, `L`)                 | establishes untreated repeat rate                           | n/a (reference)                                               | any drift vs its own seed-set replay                       | reproducible across seed set within tolerance band            |
| **treated (A1)**              | `L` ↑ on exposed motif; `RUF` ↓         | fewer repeated structurally-similar failures after exposure | `RUF(A1) < RUF(A0)`, predicted direction, null holds          | `RUF` change reproduced by A2; off-target success collapse | `ΔRUF < 0`, CI excludes 0, null holds, dose-response on `s_m` |
| **neutralized-null (A2)**     | same targets as A1                      | **no** behavioural change vs control                        | `                                                             | RUF(A2) − RUF(A0)                                          | ≤ band`                                                       | any non-zero on-target shift                                | distributions indistinguishable from control (equivalence test) |
| **state-clamped (A3)**        | clamped var (`s_m`/`t`/`c`)             | clamping `s_m`→baseline removes the RUF reduction           | `RUF(A3) ≈ RUF(A0)`; monotone in clamp value                  | RUF unchanged from A1 (state was epiphenomenal)            | `RUF(A3) > RUF(A1)` by predicted margin; null holds           |
| **state-reset (A4)**          | `s_m` → seed                            | dose-response: erasing accumulation restores repeats        | `RUF(A4)` rises toward `RUF(A0)` proportional to erased `s_m` | flat response (no dose-response)                           | monotone `RUF` vs erased strength; null holds                 |
| **memory-deleted (A5)**       | scar row / retrieval hit-rate → 0       | removing the memory removes avoidance                       | `RUF(A5) ≈ RUF(A0)`; retrieval precision → 0                  | RUF unchanged (memory not load-bearing)                    | `RUF(A5) > RUF(A1)`; null (store intact) reproduces control   |
| **memory-scrambled (A6)**     | scar/retrieval content permuted         | wrong memory ≠ no memory: repeats return, may misfire       | `RUF(A6) ≈ RUF(A0)`; false-avoidance not below reflection     | RUF still low (agent ignored memory content)               | `RUF(A6) > RUF(A1)`; `H5` false-avoidance guard held          |
| **influence-disabled (A7)**   | edge `state→L` = 0 (state still logged) | decoupling state from decision removes the reduction        | `RUF(A7) ≈ RUF(A0)` **while `s_m` trace unchanged vs A1**     | `RUF(A7) < RUF(A0)` (reduction survives decoupling)        | `RUF(A7) > RUF(A1)`; state trace matches A1 within band       |
| **self-report-disabled (A8)** | report head suppressed                  | behaviour unchanged; only the report channel dies           | `                                                             | RUF(A8) − RUF(A1)                                          | ≤ band`                                                       | `RUF` moves when report suppressed (leakage into behaviour) | equivalence to A1 on behaviour; report absent                   |

**Replay-equivalence requirement (all arms).** Control, treated, and null must
differ **only** in the intervened variable. On the deterministic path this is the
existing byte-equality invariant (`null` byte-reproduces `control`;
audit-replay §1). On the statistical path it is the seed/prompt/transcript-frozen
distributional equivalence of §2. An arm whose off-target frames drift is rejected
before any effect is scored (the off-target-null-drift block; audit-interventions §1).

**Randomization / counterbalancing (all arms).** Reuse the counterbalanced
3-order provenance verbatim (`provenance._COUNTERBALANCED_ORDERS`;
audit-interventions §1): each arm is executed under
`(control,treated,null)`, `(treated,null,control)`, `(null,control,treated)` and
the per-arm digest (deterministic path) or per-arm distribution (statistical path)
must be order-invariant. On the statistical path, add: (i) a **frozen seed set**
`{σ_1..σ_K}` shared across all arms; (ii) task order randomized once and reused
identically for every arm; (iii) motif↔surface-form assignment counterbalanced so
no arm sees a privileged surface variant.

**Model nondeterminism (all arms).** On the deterministic-oracle path there is
none by construction (audit-replay §3). On the real-agent path it is handled by
the four freezes of §2 (seed, prompt, retrieved memory, tool/env transcript) plus
N-sample distributional nulls: the arm's claim is a property of the **distribution
over K seeded rollouts**, never of a single byte string.

---

## 2. The core problem and the parallel statistical causal path

### 2.1 The problem, stated exactly

The current clone-equivalence gate is:

```
certify() passes  ⟺  sha256(outputs_A) == sha256(outputs_B)
```

for two independent factory constructions and for reset-replay
(`certified_subjects.py`; audit-interventions §3). Every provenance check reduces
to byte-identity. A real stochastic LLM agent violates every assumption behind it:
non-deterministic decoding (temperature, top-p, sampling), non-associative float
reductions on GPU / batch-dependent kernels, retrieved-memory and tool/environment
nondeterminism, and prompt-order / context-window effects. For such a subject
`clone_equivalent` and `reset_deterministic` are **always False**, so `certify()`
always fails, so `subject_factory_eligible` is always False, so
`provenance.integrity_errors()` is non-empty, so the run is **hard-capped at Level
3** (audit-interventions §3). **The paper's headline experiment cannot run on a
real agent under this gate.** The scoring side is only half-ready: `report.
_direction_ok` already supports `bounded_change`/`no_change` with a tolerance
`bound`, but `extract_signal` sums point scalars and provenance demands exact
digests (audit-interventions §6).

### 2.2 The solution: replace byte-equality with a seed-controlled distributional contract

The causal claim moves from _"null byte-reproduces control"_ to _"null and control
are **distributionally indistinguishable** on the target signal, while treated
**shifts** in the predicted direction with a bootstrap effect size whose CI
excludes zero."_ This is the standard causal-mediation contract for stochastic
systems (audit-interventions §3). It is realized by four freezes plus a sampling
loop.

**The four freezes — what must be captured / snapshotted per tick.** The goal is
that control, treated, and null share an **identical decode path up to the
intervention point** and diverge only at the clamp (audit-replay §3).

| Freeze                           | What is snapshotted                                                                                     | Why                                                                                                                            | Where it plugs in                                                             |
| -------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| **Frozen model seed**            | decoding RNG seed, framework seed, deterministic-kernel flags; seed set `{σ_k}` is part of the arm spec | makes "byte-identical _given fixed seed_" achievable and counterbalanceable across a seed set                                  | new live driver, outside `replay/` (`02-research-thesis.md` §8.1)             |
| **Frozen prompts**               | the exact realized prompt string per tick (system + task + scaffold state + prior context)              | control/treated/null differ only in the intervened variable, never in incidental context or token count (H2's confound guard)  | extend the existing `input_frames_sha256` binding to the full realized prompt |
| **Frozen retrieved memory**      | the exact retrieved-memory set and its order per tick (for retrieval/reflection/Pneuma-state arms)      | isolates memory content as the intervened variable; enables A5/A6 to be clean                                                  | snapshot alongside prompt; digest-bound in the trace                          |
| **Recorded tool/env transcript** | tool outputs, container filesystem deltas, test-runner verdicts, keyed by `(task, tick, action)`        | the environment replays as a **fixed transcript** even when the model is stochastic; removes env nondeterminism from the delta | new transcript layer (does not exist today; audit-interventions §6)           |

With these four freezes, the **only** remaining source of divergence between two
rollouts of the same arm-seed pair is the model's own sampling — and that is
pinned by the seed. Between arms at a fixed seed, the only intended divergence is
the intervened variable at its intervention tick.

**Branch-divergence metric.** When byte-identity is impossible we replace the
boolean `ordinal_invariant`/`clone_equivalent` with a divergence measurement
answering **where and when** treated first departs from control:

- **Divergence onset** `τ*` — the first tick index at which the treated and
  control action distributions differ beyond a tolerance band. Under a valid
  causal setup, `τ* ≥ t_intervention`; a treated run that diverges **before** the
  clamp indicates leakage (freeze failure) and invalidates the arm.
- **Divergence magnitude** — a distance between the control and treated
  distributions over action tokens / trajectory prefixes at each tick (e.g. a
  bounded edit-distance on the action sequence, or KL / total-variation on the
  per-tick action distribution over the K seeds). Reported as a curve over ticks.
- **Null divergence floor** — the same distance computed control-vs-null. It must
  stay inside the tolerance band at every tick (the statistical analogue of "null
  byte-reproduces control").

**N-sample distributional nulls with bootstrap effect sizes.** For each arm draw
K independent seeded rollouts per task. Replace the point-scalar
`observed_delta = treated_sum − control_sum` with a **paired distributional
contrast**:

- Compute the target signal (primary: per-task RUF; also `L`, verification depth)
  as a distribution over the K seeds, **paired by seed** across arms.
- **Treated effect:** paired bootstrap (or seed-permutation test) of
  `RUF(treated) − RUF(control)`; require the 95% CI to exclude 0 in the predicted
  direction. This is the admissible-delta test.
- **Null equivalence:** a TOST-style equivalence test that
  `RUF(null) − RUF(control)` lies inside `±band`; failing to reject "different" =
  the null did not hold = the harness cannot support the causal claim for that arm
  (mirrors the byte-null discipline; audit-replay §3).
- **Dose-response:** regress `ΔRUF` on erased/clamped `s_m` (arms A3/A4);
  H2 predicts a monotone relationship (`02-research-thesis.md` §4).
- **Multiplicity:** secondary signals get multiplicity correction
  (`02-research-thesis.md` §8.7).

**How a causal claim stays valid when byte-identical replay is impossible.** The
claim never rests on any single rollout. It rests on: (i) the four freezes making
the arms differ only in the intervened variable up to `τ*`; (ii) `τ* ≥
t_intervention` proving the divergence is _caused_ at the clamp, not upstream;
(iii) the null's distribution being statistically indistinguishable from control;
and (iv) the treated distribution shifting with a bootstrap CI excluding zero. The
counterbalanced 3-order provenance and the recompute-from-receipts scorer
(the mind never scores itself; audit-replay §1) are retained unchanged — only the
_leaf comparison_ changes from `sha256 ==` to a distributional test. `report.
_direction_ok`'s existing `bounded_change`/`no_change` tolerance is the seam this
plugs into; `extract_signal` gains **pluggable behavioural extractors**
(did-it-repeat-the-failure, retry count, tool-call pattern) instead of the 5
hardcoded psyche signals (audit-interventions §6).

---

## 3. Reusing the deterministic PairedReplayRunner verbatim for the synthetic oracle path

The synthetic controlled-motif suite (`02-research-thesis.md` §8.5) injects known
bug motifs into clean repos, giving an **exact motif ground truth and exact repeat
structure**. Over this suite we can build a **deterministic oracle subject** — a
`PsycheUnderTest` whose action given a frozen input is a pure function — and drive
it through the **existing** `PairedReplayRunner` with **no modification**:

- The runner's three arms (`control` / `treated` / `null=schedule.neutralized()`),
  the counterbalanced 3-order provenance, the `ordinal_invariant` check, the
  digest-bound receipts, and the null-byte-reproduces-control invariant all apply
  as-is (audit-interventions §1). Byte-equality is **satisfiable** here because the
  oracle is deterministic, so the strongest possible gate is used for free.
- The clamp/ablate/disable/noise operations already map onto the arm roster of §1
  (clamp=A3, disable/ablate=A5/A7, noise=A6, restore=A2/A4-null;
  audit-interventions §6), so each arm has a deterministic twin.
- The certification probe (`certify()`: interface, clone-equivalence,
  reset-determinism, ordinal-invariance) passes on the oracle, yielding a real
  `subject_factory_eligible` and — for these sub-experiments only — a genuine
  Level-4-eligible provenance record.

**How the two paths corroborate each other.** They are deliberately redundant on
the same intervention taxonomy and the same motif suite:

| Property           | Deterministic-oracle path                                                   | Statistical real-agent path                         |
| ------------------ | --------------------------------------------------------------------------- | --------------------------------------------------- |
| Subject            | pure-function oracle                                                        | frozen open-weight LLM under the live driver        |
| Replay contract    | `sha256` byte-equality (exact)                                              | seed-frozen distributional equivalence              |
| Null test          | null byte-reproduces control                                                | TOST equivalence, `null−control ∈ ±band`            |
| Effect readout     | exact scalar delta                                                          | paired bootstrap CI on K seeds                      |
| What it proves     | the **instrument** measures the intended causal contrast with zero variance | the **hypothesis** holds on a real stochastic agent |
| Failure it catches | a mis-specified clamp / off-target leak (exactly)                           | a real effect swamped by / absent under sampling    |

The oracle path is a **positive control for the instrument**: because its ground
truth is exact, any arm that fails to produce the predicted admissible delta on the
oracle indicates a bug in the intervention wiring, not in the agent — isolating
instrument error from scientific null. The statistical path then carries the
scientific claim, with the oracle path certifying that the divergence metric,
tolerance bands, and pluggable extractors are calibrated (the oracle's known delta
must be recovered by the same statistical estimator at K→large). Agreement across
both paths on the same motif → the effect is real and correctly measured;
disagreement → either the freezes leaked (oracle passes, agent shows pre-clamp
`τ*`) or the effect is genuinely stochastic-only (oracle exact, agent CI includes
zero), and each diagnosis is actionable.

---

## 4. Pass/fail decision table and H2 falsification

### 4.1 Per-arm decision table

Read jointly: an arm **passes** only if its treated contrast is admissible **and**
its null holds **and** (statistical path) `τ* ≥ t_intervention`.

| Arm                       | PASS (admissible)                               | FAIL (inadmissible)                       | Interpretation of PASS                     |
| ------------------------- | ----------------------------------------------- | ----------------------------------------- | ------------------------------------------ |
| control (A0)              | reproducible across seed set within band        | drifts vs own seed replay                 | valid baseline                             |
| treated (A1)              | `ΔRUF<0`, CI excludes 0, null holds, `τ*≥t_int` | CI includes 0; null moves; pre-clamp `τ*` | state reduces repeats                      |
| neutralized-null (A2)     | equivalence to control (TOST inside band)       | any on-target shift                       | harness adds nothing spuriously            |
| state-clamped (A3)        | `RUF(A3)>RUF(A1)` by margin; monotone in clamp  | `RUF(A3)≈RUF(A1)`                         | **removing the state removes the effect**  |
| state-reset (A4)          | `RUF↑` monotone with erased `s_m`               | flat / non-monotone                       | **dose-response on scar strength**         |
| memory-deleted (A5)       | `RUF(A5)>RUF(A1)`; retrieval precision→0        | RUF unchanged                             | the memory is load-bearing                 |
| memory-scrambled (A6)     | `RUF(A6)>RUF(A1)`; false-avoidance ≤ reflection | RUF still low                             | wrong memory ≠ no memory (content matters) |
| influence-disabled (A7)   | `RUF(A7)≈RUF(A0)` while `s_m` trace matches A1  | reduction survives decoupling             | **state must feed the decision to matter** |
| self-report-disabled (A8) | behaviour equivalent to A1; report absent       | RUF moves                                 | firewall intact (report ≠ behaviour)       |

### 4.2 What result falsifies H2

> **H2 is falsified** if, under matched base model, tools, budget, retry cap, and
> task order, ablating or clamping the failure-memory variable `s_m` **leaves the
> RUF reduction intact** — i.e. `RUF(state-clamped A3) ≈ RUF(treated A1)` and
> `RUF(influence-disabled A7) ≈ RUF(treated A1)` (state is epiphenomenal) — **OR**
> if the neutralized-null arm (A2) fails to reproduce control (the harness cannot
> support a causal claim) — **OR** if the treated-minus-null bootstrap CI on ΔRUF
> includes zero — **OR** if there is no monotone dose-response of ΔRUF on
> accumulated/erased `s_m` (arms A3/A4).

Concretely, on the statistical path H2 falsification is any of: (i) A3/A7 CI on
`RUF(clamped) − RUF(treated)` includes zero; (ii) A2 fails the TOST equivalence to
control; (iii) A1's `RUF(treated) − RUF(control)` CI includes zero; (iv) the A4
dose-response slope CI includes zero. On the deterministic-oracle path the same
falsifiers appear as exact byte-level facts (A3 does not raise the oracle's RUF; A2
fails to byte-reproduce control), isolating instrument failure from a genuine null.

Per `02-research-thesis.md` §6, a result where **H1 holds but H2 fails** is still
publishable as a **negative causal result** ("internal state correlates with but
does not cause the reduction"); recorded negatives are first-class
(`docs/research/10-anti-fake-progress.md`). The E-0 negative (psyche signals lost
to a retry-count baseline at failure prediction, AUROC 0.34 vs 0.71;
`01-current-state-audit.md` §7) is why the retry-count heuristic controller is a
mandatory arm and why token/step budgets are tightly matched across all arms —
so a trivial controller can falsify us honestly.

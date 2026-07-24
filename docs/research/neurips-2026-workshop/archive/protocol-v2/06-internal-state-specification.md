# 06 — Internal-State Specification

> [!WARNING]
> **Protocol v2 supersession notice (2026-07-22).** This document is retained as
> a historical Protocol-v1 specification. **Do not implement from it.** Use
> `02-research-thesis.md` for the canonical scientific constants,
> `16-protocol-v2-hardening.md` for the hardened rationale and contracts, and
> `17-implementation-plan-v2.md` for the executable build backlog. If this file
> conflicts with those documents, Protocol v2 governs.

Status: **archived Protocol v1; non-authoritative.** The material below records
the old state design and may conflict with Protocol v2. It does not fix the live
implementation contract. Historically, it specified the definition, data type,
initialization, update rule, decay, serialization, observability, intervention
hook, and tests for every persistent internal-state variable, plus the head that
couples state to behaviour.

At the time it was written, it was intended to match the former locked design.
Where a variable's update rule extends an _existing_ psyche rule, the
existing rule is quoted verbatim from the code audits
(`audit/audit-psyche.md`, `audit/audit-nervous-system.md`) and the delta ("what
must be added") is stated explicitly. Nothing here authorizes implementation.

Notation conventions (repo-global): final/constant symbols in `ALL_CAPS`
(e.g. `LAMBDA_S`, `CAP_S`); mutable state in `snake_case` (`s_m`, `c`, `t`, `r`,
`L`); any function is `camelCase` (`detectFailure`, `decisionHead`). All formulas
use LaTeX. All code/schema/doc indentation is 4 spaces.

---

## 0. Design invariants (inherited, non-negotiable)

1. **Persistence is real, not tautological.** The audit's blunt finding is that
   today's cross-run persistence is a tautology: the same fixture motif every
   tick with a fixed `+0.1` increment (`audit-nervous-system.md` §2, §7 gap 4).
   Every variable below must (a) update from a _detected_ signal, not a
   fixture-supplied label, and (b) serialize/deserialize across runs so that
   persistence can be _measured_, not asserted.
2. **Bounded and decaying.** Today `scars` grows monotonically, unbounded, never
   decays (`audit-psyche.md` §2; `audit-nervous-system.md` §2 "No decay… no
   cap"). Every variable must have an explicit range, cap, and
   decay/forgetting term so that "avoidance" can be shown to _fade or persist_
   (`audit-nervous-system.md` §7 gap 4).
3. **Emits pressure, not commands.** State reaches behaviour ONLY through the
   bounded decision head (§6) as a _bias/pressure_ over the scaffold's next
   action, never a raw shell command (`02` §8.4; repo invariant
   `audit-nervous-system.md` §1, §4).
4. **Every variable has a measurable causal role or is cut.** Each variable ships
   with an H2 clamp on an existing `PerturbationSet` seam and a pre-registered
   expected behavioural delta (§7). A variable whose clamp produces no
   behavioural delta is dropped before the paper — this is why today's inert
   `morale` and never-populated `competence` are excluded (`audit-psyche.md` §5
   "MISSING / weak").
5. **Prose-blind firewall preserved.** Self-report NEVER feeds the behavioural
   score (`02` §8.9–8.10). State observability (§ per-variable "observability")
   is via structured frame fields with receipts, read by the prose-blind
   evaluator, not via rendered voice.
6. **Determinism preserved.** Given state + inputs + seed, every update and the
   decision head are closed-form deterministic (`audit-psyche.md` §3). No RNG
   enters the state machine; stochasticity lives only in the subject model's
   decoding, which is seed-pinned per arm (`02` §8.1).

---

## 1. State vector overview

The Pneuma-state carries exactly four causally-active persistent variables and
one derived scalar consumed by the decision head:

| Symbol | Name                                     | Type              | Range                        | Persists cross-run?      | Existing seam                                   | Clamp seam (H2)            |
| ------ | ---------------------------------------- | ----------------- | ---------------------------- | ------------------------ | ----------------------------------------------- | -------------------------- |
| `s_m`  | failure-sensitivity per motif $m$        | `dict[str→float]` | each $\in[0,1]$              | **yes** (serialized)     | `scars` (`scar_graph`)                          | `scar_graph`               |
| `c`    | confidence (calibrated self-reliability) | `float`           | $[0,1]$                      | yes (serialized)         | `self_model_reliability` + `calibration_error`  | `self_model`               |
| `t`    | caution (affect tension axis)            | `float`           | $[-1,1]$ (operative $[0,1]$) | yes (serialized)         | `affect.tension` (`affect_manifold`)            | `affect_manifold`          |
| `r`    | memory-trust                             | `float`           | $[0,1]$                      | yes (serialized)         | **NEW** (no existing scalar)                    | **NEW** `memory_trust` dim |
| `L`    | derived expected-loss                    | `float`           | $[0,1]$                      | no (recomputed per tick) | derived `expected_loss` (per-tick, not carried) | — (clamp its inputs)       |

`s_m` is the primary variable for H1/H2 (`02` §8.3). `L` is the single scalar the
decision head consumes (`02` §8.3 item 5). The subject model, tools, budget,
retry cap, task order, and environment are held identical across all arms (`02`
§8.2); only this vector and its coupling differ.

The state vector for run $k$ on task $\tau$ at tick $n$ is

$$
\mathbf{x}_{n} = \big(\; \{s_m\}_{m\in M},\; c,\; t,\; r \;\big), \qquad
L_n = g(\mathbf{x}_n),
$$

with $M$ the fixed motif set from the failure taxonomy (`02` §8.6, ~12 motifs).

---

## 2. Shared machinery added once (not per-variable)

Three pieces are prerequisites the audit flags as absent; they are specified once
here and referenced by the variables below.

### 2.1 The real failure detector `detectFailure` (closes gap "failure detection is faked")

`audit-nervous-system.md` §2 CRITICAL FINDING: today `motif_of` reads
`scar_motif_matches` _out of the input frame_, pre-populated identically every
tick, so "noticing" is upstream and out of scope. `audit-psyche.md` §2: `scars`
updates "on an anomaly instinct fire", again fixture-driven. The paper requires a
component that derives a motif id + similarity-to-past from a **real trajectory**
(`01` §3 gap 2; `02` §8.6).

`detectFailure` is specified in `04-benchmark-specification.md` (enriched
`trajectory.py`); here we fix only its **contract** because every state update
consumes its output:

- Input: the current per-step observable record (tool call, arguments digest,
  exit status, test result, diff target) plus the run's failure history.
- Output per tick $n$: a set of detected-failure events
    $$
    D_n = \{\, (m,\; \delta_m,\; a_m) \,\}, \quad m\in M,\; \delta_m\in[0,1],\; a_m\in[0,1],
    $$
    where $m$ is a taxonomy motif id, $\delta_m$ is the **detection strength**
    (a real observable failure of motif $m$ occurred this tick; $0$ if not
    detected), and $a_m$ is the **similarity-to-past** (how structurally close
    this instance is to prior instances of $m$). Absent motifs contribute
    $\delta_m = 0$.
- Hard requirement (`01` §2 Adapters row): argument/output **digesting must
  preserve error-class + file identity** so recurrence is detectable. The
  current 3 crude proxies (`error_marker`, byte-identical `retry_count`,
  `strategy_switches`) are insufficient and are replaced.
- Determinism: $D_n$ is a pure function of the observable record (no RNG).

`detectFailure` is the single upstream dependency shared by `s_m` (grows on
$\delta_m$), `t` (rises on any $\delta$), and `c` (resolves the error prediction).

### 2.2 The `memory_trust` PerturbationSet dimension (NEW seam)

`02` §8.3: `r` maps to "a new `memory_trust` dimension". Today `PerturbationSet`
supports scalar ops (`clamp`/`boost`/`noise`) on `affect_manifold` and `drives`,
and structural `ablate`/`disable` on `scar_graph`, `workspace`, `self_model`
(`audit-psyche.md` §5). The build adds one scalar dimension `memory_trust` with
the same clamp/boost/noise semantics, so `r` gets the same tested clamp
machinery. This is the only new seam; the other three reuse existing hooks.

### 2.3 Cross-run state store (closes gap "persistence is aspirational")

Reuse `foundation/memory.py` (SQLite/FTS5 + hard-erasure receipts,
`01` §4) as the retrieval baseline backend AND the Pneuma-state serialization
backend. The Pneuma-state store persists the full vector
$(\{s_m\}, c, t, r)$ keyed by `(agent_condition, subject_model, seed,
task_sequence_id)`. Serialization format is specified per-variable below and
canonicalized (sorted keys, 6-dp float rounding, byte-stable — the existing
`scar_memory.save` discipline, `audit-nervous-system.md` §2). `reset()` semantics
are made explicit in §5.

---

## 3. The four persistent variables (full specification)

For each variable: semantic definition; type + range; init; exact update rule
(with the existing rule quoted and the delta stated); decay/persistence;
cross-run serialization; behavioural influence (into `L`/head); observability
(frame field); provenance (receipts); intervention hook; replay semantics;
failure modes; and validating tests. Each closes with an explicit
**exists-today vs must-be-added** contrast citing the audit.

---

### 3.1 `s_m` — failure-sensitivity per motif (scar-tissue memory) — PRIMARY

**Semantic definition.** For each failure motif $m$, $s_m$ is a persistent scalar
measuring how strongly the agent has been "burned" by motif $m$ in the past. High
$s_m$ biases the decision head toward caution _for situations resembling $m$_. It
is the failure-memory variable H1/H2 turn on.

**Type + range.** `dict[str→float]`, one key per active motif; each value
$s_m \in [0,1]$. Absent key ⟹ $s_m = 0$.

**Initialization.** `{}` (empty) on a fresh agent lineage; seeded from the
cross-run store at run start (`sm.load`, `audit-nervous-system.md` §2). Cold-start
default for a newly-seen motif on first detection is `SEED_S = 0.2` (matches the
existing `scars.get(motif_id, 0.2)` cold value, `audit-psyche.md` §2).

**Exact update rule.** _Existing rule_ (`audit-psyche.md` §2; verified live probe
`{} → {d1:0.35} → {d1:0.50}`):

$$
s_m \leftarrow \operatorname{clip}\!\big(\operatorname{get}(m, 0.2) + 0.15,\; 0,\; 1\big)
\quad\text{on an anomaly instinct fire (fixture-fed).}
$$

The audit's twin defects: the trigger is fixture-fed (not a real detection),
there is no decay, and there is no cap other than incidental downstream clipping.
_Proposed rule_ (adds a real detector trigger + decay + explicit cap):

$$
\boxed{\;
s_m \;\leftarrow\; \operatorname{clip}\!\Big(\;
\min\!\big(\mathrm{CAP\_S},\;\;
s_m\,(1-\mathrm{LAMBDA\_S})\;+\;\mathrm{ALPHA\_S}\cdot \delta_m \cdot (1 + \mathrm{RHO\_S}\, a_m)
\big),\;\; 0,\; 1\Big)
\;}
$$

applied for every motif $m\in M$ each tick, where $\delta_m$ (detection strength)
and $a_m$ (similarity-to-past) come from `detectFailure` (§2.1). Constants
(pinned in the run config, listed in `15-decision-log.md`):

| Constant   | Meaning                     | Planned value | Rationale                                                                                                                                                                         |
| ---------- | --------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ALPHA_S`  | growth per detected failure | `0.15`        | matches existing `+0.15` step (`audit-psyche.md` §2) so a single detection reproduces legacy magnitude when $a_m{=}0$                                                             |
| `LAMBDA_S` | per-tick decay (forgetting) | `0.02`        | slow; a motif un-seen for ~35 ticks halves — long enough to persist within a task sequence, short enough to fade over a long benign run (tests H2 dose-response, H5 anti-inertia) |
| `RHO_S`    | similarity amplification    | `1.0`         | a highly similar recurrence ($a_m{=}1$) doubles the growth increment — encodes "same failure again hurts more"                                                                    |
| `CAP_S`    | hard cap                    | `0.90`        | leaves head-room below 1.0 so the clamp op and the decision head never saturate; distinguishes "very burned" from "maxed"                                                         |

Decay applies **every tick to every motif**, including un-detected ones
($\delta_m = 0 \Rightarrow s_m \leftarrow \operatorname{clip}(s_m(1-\mathrm{LAMBDA\_S}))$),
which is the mechanism by which avoidance _fades_ if a motif stops recurring.

**Decay / persistence.** Geometric decay `LAMBDA_S` per tick; grows only on real
detections. Persists across ticks and across runs (serialized). This directly
supplies the H2 dose-response prediction: effect size scales monotonically with
accumulated $s_m$ (`02` §4 H2).

**Cross-run serialization.** Flat JSON `{motif_id: round(s_m,6)}`, `sort_keys`,
byte-stable (extend `scar_memory.save`, `audit-nervous-system.md` §2). Stored in
the §2.3 SQLite store under the run key. On load, unknown motifs default to 0.

**Behavioural influence.** Feeds the derived expected-loss `L` (§4) via the
active-motif aggregate $\bar{s} = \max_{m\in M_{\text{active}}} s_m$ where
$M_{\text{active}}$ is the set of motifs the _current_ situation resembles
($a_m > 0$). $\bar{s}$ is `L`'s dominant term (weight `w1`, §4). This preserves
the existing "scar_strength = max over matches" pattern (`audit-psyche.md` §2
"derived-per-tick").

**Observability.** Exposed in `psyche_state.derived_signals.scar_strength`
(already emitted, `audit-nervous-system.md` §4) plus a new per-motif map
`psyche_state.failure_sensitivity: {motif_id: s_m}`. Read by the prose-blind
evaluator for the H2 dose-response and H3 self-report faithfulness checks.

**Provenance (receipts).** Each $s_m$ update writes a causal-trace receipt:
`internal_state` node referencing the `detectFailure` event digest, the prior
$s_m$, the $\delta_m$/$a_m$ used, and the new $s_m$ — so every scar increment is
auditable to a specific detected failure (extends the existing receipt chain
`event → internal_state → pressure`, `audit-nervous-system.md` §1, §4).

**Intervention hook (H2).** `scar_graph` seam (existing, tested):
`ablate`/`disable` forces $\bar{s}=0$ and skips the increment
(`audit-nervous-system.md` §2 ablation gate); scalar `clamp`/`boost` scales $s_m$
(`audit-psyche.md` §5). The **null arm** (`02` §8.2 arm 6) clamps $s_m$ to
baseline; the **treated arm** lets it grow. This is the primary H2 contrast.

**Serialization format.** `{"m1:regress": 0.30, "m2:wrong-file": 0.12, ...}`.

**Replay semantics.** Deterministic: given the recorded `detectFailure` stream
and seed, the $s_m$ trajectory is byte-reproducible; the synthetic deterministic-
oracle sub-experiments reuse the byte-equality paired runner (`02` §8.8). For the
stochastic real-repo arm, the recorded `detectFailure` events are frozen with the
model seed so the state trajectory replays identically (`02` §8.8 frozen inputs).

**Failure modes.** (a) _Motif-id instability_ — if `detectFailure` assigns
inconsistent ids to the same underlying failure, decay and growth split across
keys and $\bar{s}$ under-counts; mitigated by the taxonomy's fixed 12-motif
vocabulary and similarity $a_m$. (b) _Runaway saturation_ — bounded by `CAP_S`.
(c) _Over-avoidance / inertia_ — if `LAMBDA_S` is too small, $s_m$ never fades and
the agent becomes inert (H5 risk); the decay term + the H5 counterfactual tasks
(`02` §8.9) guard this. (d) _Detector false positives_ inflate $s_m$ without real
failure; measured against the deterministic-oracle synthetic suite where ground
truth is exact.

**Validating tests.**

- _Unit:_ single detection with $a_m{=}0$ moves $s_m: 0.2 \to 0.35$ (legacy
  parity); with $a_m{=}1$ moves $0.2 \to 0.50$; `CAP_S` caps at `0.90`;
  decay-only tick multiplies by `(1-LAMBDA_S)`; clip bounds `[0,1]`.
- _Persistence:_ run A then run B against a shared store; assert run-B tick-0
  $\bar{s}$ > run-A tick-0 and state hashes differ (real persistence, extends
  `l2_persistence` slice `audit-nervous-system.md` §5, but now driven by a real
  detection rather than a fixture motif).
- _Integration (H2):_ control (grow) vs null (clamp) vs treated(ablate) through
  `PairedReplayRunner`; assert `observed_delta ≤ 0` under ablation and null
  holds (extends `scar_ablation` slice).
- _Dose-response:_ seed $s_m \in \{0.0, 0.3, 0.6, 0.9\}$; assert decision-head
  caution bias is monotonic in $s_m$ (H2 dose-response).

**Exists today vs must be added.**

| Exists today (`audit`)                                                                                                                            | Must be added                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scars` dict, `+0.15` on anomaly, `max`-aggregate to `scar_strength`, clamp seam, serialization, live-verified growth loop (`audit-psyche.md` §2) | Real `detectFailure` trigger replacing fixture-fed `scar_motif_matches` (`audit-nervous-system.md` §2); decay `LAMBDA_S`; explicit `CAP_S`; similarity amplification `RHO_S`; per-motif observability field; feed into `L` (not the ad-hoc `expected_loss`) |

---

### 3.2 `c` — confidence (calibrated self-reliability)

**Semantic definition.** A Brier-calibrated self-estimate of the agent's own
error rate: high `c` = "I am usually right here", low `c` = "I have been
mis-calibrated / wrong". It counter-weights `s_m` in the decision head (a
confident agent proceeds despite a mild scar; a mis-calibrated one does not).

**Type + range.** `float` $\in [0,1]$.

**Initialization.** `c = 0.5` (matches `self_model_reliability` init,
`audit-psyche.md` §2); `calibration_error = None`, `_brier_sum = 0.0`,
`calibration_samples = 0`.

**Exact update rule.** _Existing rule_ (`audit-psyche.md` §2):

$$
\text{each tick set } \hat{e} = \operatorname{clip}(0.25 + 0.4\,u + 0.4\,\bar{s}),
\quad
\text{on resolve: } \_brier\_sum \mathrel{+}= (\hat{e} - o)^2,\;
\text{calib\_err} = \frac{\_brier\_sum}{\text{samples}},\;
c = \operatorname{clip}(1 - \text{calib\_err})
$$

where $u$ is self-model uncertainty, $\bar{s}$ the scar aggregate, and
$o\in\{0,1\}$ the observed error next tick. _Proposed rule_ keeps the Brier spine
verbatim (it is the only genuinely calibrated mechanism in the repo) and adds two
things the audit shows are missing: (i) the prediction target is now the **real**
observed failure from `detectFailure` ($o = \mathbb{1}[\exists m:\delta_m>0]$),
not a fixture verdict; (ii) a **windowed** Brier so `c` tracks _recent_
calibration and can move both ways:

$$
\boxed{\;
\hat{e}_n = \operatorname{clip}\!\big(0.25 + 0.4\,u_n + 0.4\,\bar{s}_n\big),\quad
B_n = (1-\mathrm{BETA\_C})\,B_{n-1} + \mathrm{BETA\_C}\,(\hat{e}_{n-1} - o_n)^2,\quad
c \leftarrow \operatorname{clip}(1 - B_n,\,0,\,1)
\;}
$$

with `BETA_C = 0.2` (EMA window ≈ 5 resolved predictions) so calibration error
forgets stale performance — this is the "decay" analogue for `c`. Before the
first resolved prediction, `c = 0.5`.

**Decay / persistence.** The EMA `BETA_C` is the forgetting term; `c` persists
across ticks and runs (serialize $B_n$ and `c`). Cumulative-mean Brier (existing)
is replaced by the EMA so old runs do not anchor `c` forever.

**Cross-run serialization.** `{"c": round(c,6), "brier_ema": round(B,6)}` in the
§2.3 store. On load, resume the EMA.

**Behavioural influence.** Enters `L` (§4) as $c' = 1 - c$ (a _mis_-calibration /
error-expectation term, weight `w2`). High confidence lowers `L` ⟹ head biases
toward `proceed`; low confidence raises `L` ⟹ head biases toward verification.
This matches the existing `expected_loss` using reliability-adjacent inputs
(`audit-psyche.md` §2) but routes through the shared `L`.

**Observability.** `psyche_state.self_model.reliability = c` and
`psyche_state.calibration_state.brier_ema = B` (extends existing
`psyche_state.self_model` / `calibration_state`, `audit-psyche.md` §2). Read by
the prose-blind evaluator; used by H3 (self-report of "I was under-confident").

**Provenance (receipts).** Each resolve writes a receipt binding
$(\hat{e}_{n-1}, o_n, B_n, c)$ to the tick's causal trace, so a confidence move is
auditable to a specific resolved prediction.

**Intervention hook (H2).** `self_model` seam (existing structural
ablate/disable; a "certainty clamp" slice already exists,
`audit-psyche.md` §5, `audit-nervous-system.md` §5). H2 clamps `c` to a fixed
value to test whether confidence (not scars) is carrying an effect.

**Serialization format.** `{"c": 0.6975, "brier_ema": 0.0912}` (the `0.6975`
matches the live-probe post-resolve value, `audit-psyche.md` §2).

**Replay semantics.** Deterministic given the resolved-prediction stream + seed;
reproducible under the frozen-input paired runner.

**Failure modes.** (a) _Circular target_ — if `detectFailure`'s $o$ leaks into
$\hat{e}$, calibration is trivially perfect; the prediction is formed _before_ the
next-tick observation, preserving the one-tick predictive gap (existing design,
`audit-psyche.md` §2 `_pending_error_prediction`). (b) _Slow start_ — few
resolved predictions ⟹ `c` anchored at 0.5; acceptable, flagged in the calibration
metric. (c) _Confound with `s_m`_ — since $\bar{s}$ enters $\hat{e}$, `c` and
`s_m` are correlated; H2 clamps them independently to separate their roles.

**Validating tests.**

- _Unit:_ one resolved over-prediction lowers `c`; one accurate prediction raises
  it; `c = 0.5` before any resolve; EMA weight `BETA_C` applied correctly;
  bounds `[0,1]`.
- _Integration:_ clamp `c` via `self_model`, assert decision-head distribution
  shifts and null holds.
- _Calibration metric:_ reliability-diagram / ECE over a run is finite and
  improves when `detectFailure` is accurate (secondary metric "state
  calibration", `02` §8.7).

**Exists today vs must be added.**

| Exists today                                                                                                           | Must be added                                                                                                                                                                  |
| ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Brier loop, `self_model_reliability` init 0.5, one-tick predictive gap, `self_model` clamp seam (`audit-psyche.md` §2) | Real observed-failure target from `detectFailure` (not fixture verdict); EMA/windowed Brier for two-way movement + forgetting; route into shared `L`; per-tick receipt binding |

---

### 3.3 `t` — caution (affect tension axis)

**Semantic definition.** A fast, recurrent "arousal/caution" scalar that rises
with errors and scars and gates verification depth. It is the short-timescale
counterpart to `s_m`'s long-timescale memory: `s_m` remembers _which_ failures
hurt; `t` reflects _how tense right now_.

**Type + range.** `float`. The manifold axis is $\in[-1,1]$; the **operative**
range for caution is $[0,1]$ via $\operatorname{ReLU}(t)$ (matches existing
`ReLU(tension)` usage, `audit-psyche.md` §2).

**Initialization.** `t = 0.0` (all affect axes init 0.0, `audit-psyche.md` §2).

**Exact update rule.** _Existing rule_ — two variants exist:
`ReferencePsyche.manifold.update` (recurrent, inertia $k=0.5$,
`audit-psyche.md` §2) and the simpler `BaselinePsycheSubject` law
`tension = 0.5*tension + 0.5*error` (`audit-nervous-system.md` §4 step 2). The
paper adopts the recurrent manifold form (richer, already tested) but drives the
appraisal term from real signals and adds an explicit decay:

$$
\boxed{\;
t \leftarrow \operatorname{clip}\!\Big(
\mathrm{K\_T}\,t \;+\; (1-\mathrm{K\_T})\big(\mathrm{A\_T}\,d_n + \mathrm{B\_T}\,\bar{s}_n\big)\;-\;\mathrm{GAMMA\_T}\,t,\;\; -1,\; 1\Big)
\;}
$$

where $d_n = \max_m \delta_m$ is the current detected-failure strength (real, from
§2.1), $\bar{s}_n$ the scar aggregate, `K_T = 0.5` the inertia (existing),
`A_T = 0.6` the error-drive weight, `B_T = 0.3` the scar-drive weight (both match
existing manifold appraisal/scar weights, `audit-psyche.md` §2), and
`GAMMA_T = 0.05` the attractor-toward-baseline decay (existing `0.05*prev`
attractor term, `audit-psyche.md` §2). The delta vs today is only that $d_n$ is a
real detection, not a fixture error, and the constants are named/pinned.

**Decay / persistence.** Recurrent (inertia `K_T` carries prior `t` every tick) +
attractor decay `GAMMA_T` pulling toward 0. Persists across ticks; the _last_
tick's `t` is serialized so caution carries into the next run's opening.

**Cross-run serialization.** `{"t": round(t,6)}`. Because `t` is fast, cross-run
carry is small but non-zero; serialized for completeness and for the "does caution
persist across a task boundary?" measurement.

**Behavioural influence.** Enters `L` (§4) as $\operatorname{ReLU}(t)$
(weight `w3`); also the historical direct driver of `verification`/`effort`
pressure (`audit-psyche.md` §2). In the new design `t` reaches behaviour ONLY via
`L` → decision head (invariant 3), not via a separate pressure path, to keep a
single auditable coupling.

**Observability.** `psyche_state.affect.tension = t`. Read by the prose-blind
evaluator; used by H3 ("I felt cautious after the last failure").

**Provenance (receipts).** Per-tick receipt binds $(t_{n-1}, d_n, \bar{s}_n, t_n)$.

**Intervention hook (H2).** `affect_manifold` scalar seam (existing; canonical
"clamp affect.tension to 0" fixture exists, `audit-psyche.md` §5,
`audit-nervous-system.md` §5). H2 clamps `t` to isolate fast-caution from
scar-memory.

**Serialization format.** `{"t": 0.412}`.

**Replay semantics.** Deterministic under frozen `detectFailure` + seed; the
manifold is already provably deterministic with 6-dp hashing
(`audit-psyche.md` §3).

**Failure modes.** (a) _Over-damping_ — large `GAMMA_T` makes `t` inert; guarded
by the dose-response test. (b) _Collinearity with `s_m`_ (both driven by
detection) — H2 clamps independently. (c) _Sign confusion_ — negative `t`
(relaxation) must not _reduce_ verification below the verifier floor
(positive-only pressure invariant, `audit-nervous-system.md` §1); enforced by the
$\operatorname{ReLU}$ in `L`.

**Validating tests.**

- _Unit:_ a detected failure raises `t`; a benign tick decays `t` toward 0;
  inertia `K_T` applied; bounds `[-1,1]`; `ReLU` floors negative `t` at 0 in
  `L`.
- _Integration:_ clamp `t=0` via `affect_manifold`; assert state hash and
  decision-head shift, null holds (extends `certainty_clamp`-style slice).

**Exists today vs must be added.**

| Exists today                                                                                                                | Must be added                                                                                                                                                                         |
| --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Recurrent tension axis, inertia 0.5, attractor 0.05, drives verification pressure, clamp fixture (`audit-psyche.md` §2, §5) | Drive appraisal from real `detectFailure` `d_n` (not fixture error); named/pinned constants; route to behaviour ONLY via `L` (remove the separate pressure path to keep one coupling) |

---

### 3.4 `r` — memory-trust (NEW dedicated scalar)

**Semantic definition.** A dedicated scalar weighting how much _retrieved memory_
(prior failure records / lessons) is allowed to influence the current decision.
It is the honest hinge for the contrast with the Retrieval and Reflection
baselines (`02` §8.2, §8.3): the Pneuma-state agent does not blindly trust
retrieval — it learns, per lineage, how _useful_ its retrieved memory has been.

**Type + range.** `float` $\in [0,1]$. `r=1` = fully trust retrieval; `r=0` =
ignore retrieval (decision head falls back to endogenous state only).

**Initialization.** `r = 0.5` (neutral prior; no lineage evidence yet).

**Exact update rule.** _There is no existing rule_ — the audit is explicit that
`identity_anchors` is the closest thing but is _memory-fed, replaced each tick,
not a learned trust weight_ (`audit-psyche.md` §2, §5 "No explicit memory-trust
scalar"; `02` §8.3 item 4). So `r` is genuinely new. It updates from the
**observed usefulness** of retrieval: when a retrieved memory was surfaced and the
subsequent action avoided the recurring failure it warned about, `r` rises; when
retrieval was surfaced but the failure recurred anyway (bad/misleading memory),
`r` falls. Let $q_n\in\{-1,0,+1\}$ be the retrieval-usefulness signal at tick $n$
($+1$ = surfaced memory + failure avoided; $-1$ = surfaced memory + failure
recurred; $0$ = no retrieval surfaced), computed from `detectFailure` recurrence:

$$
\boxed{\;
r \leftarrow \operatorname{clip}\!\Big(
r \;+\; \mathrm{ETA\_R}\,q_n \;-\; \mathrm{LAMBDA\_R}\,(r - 0.5),\;\; 0,\; 1\Big)
\;}
$$

with `ETA_R = 0.1` (usefulness step) and `LAMBDA_R = 0.02` (decay toward the
neutral prior 0.5, so trust reverts absent evidence — the "forgetting" term).

**Decay / persistence.** Reverts toward 0.5 at `LAMBDA_R`/tick; persists across
ticks and runs (serialized). This lets "learned trust in memory" itself fade if
retrieval stops being informative.

**Cross-run serialization.** `{"r": round(r,6)}` in the §2.3 store.

**Behavioural influence.** `r` is NOT a term in `L` directly; it is a **gain** on
the retrieval channel _feeding_ the decision head: the head's retrieval-derived
bias (e.g. "past lesson says run tests first") is scaled by `r` (§6). This keeps
`L` as the endogenous-state scalar and `r` as the exogenous-memory gate, so the
two channels are separable for H2 and for the honest retrieval-baseline contrast.

**Observability.** New field `psyche_state.memory_trust = r`. Read by the
prose-blind evaluator; supports H3 ("I discounted the retrieved note") and the
"memory-retrieval precision" secondary metric (`02` §8.7).

**Provenance (receipts).** Per-tick receipt binds $(r_{n-1}, q_n, r_n)$ and the
digest of the retrieved-memory record that produced $q_n$.

**Intervention hook (H2).** NEW `memory_trust` `PerturbationSet` dimension (§2.2),
with `clamp`/`boost`/`noise`. H2 clamps `r` (e.g. to 0, forcing the agent to
ignore retrieval) to test whether any effect is memory-trust-mediated vs
endogenous-state-mediated. Clamping `r=0` should make the Pneuma-state arm behave
like the endogenous-only variant; clamping `r=1` like naive retrieval.

**Serialization format.** `{"r": 0.5}`.

**Replay semantics.** Deterministic given the retrieval stream + `detectFailure`
recurrence + seed; the retrieved records are frozen per the causal path (`02`
§8.8 "frozen retrieved memory").

**Failure modes.** (a) _Sparse signal_ — if retrieval rarely surfaces, `r` sits at
0.5 and is causally inert; measured, and if the H2 clamp shows no delta, `r` is a
candidate to cut per invariant 4. (b) _Reward hacking of $q_n$_ — the usefulness
label must come from `detectFailure` recurrence, not self-report, or the agent
could inflate `r`; enforced by the prose-blind firewall. (c) _Confound with the
Retrieval baseline_ — `r` only exists in the Pneuma-state arm; the Retrieval
baseline uses fixed top-k with no trust weight (`02` §8.2), so the contrast is
clean by construction.

**Validating tests.**

- _Unit:_ $q=+1$ raises `r`; $q=-1$ lowers it; $q=0$ decays toward 0.5; bounds
  `[0,1]`; step `ETA_R`, decay `LAMBDA_R` applied.
- _Integration:_ clamp `r=0` via `memory_trust`; assert the retrieval-derived
  head bias is zeroed and the arm's action distribution matches the
  endogenous-only variant; null holds.
- _New-seam test:_ `memory_trust` dimension accepts clamp/boost/noise and is
  rejected outside `[0,1]` (parity with existing `affect_manifold` scalar-op
  tests).

**Exists today vs must be added.**

| Exists today                                                                                                  | Must be added                                                                                                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nothing — `identity_anchors` is memory-fed, replaced each tick, not a trust weight (`audit-psyche.md` §2, §5) | The entire `r` variable; the retrieval-usefulness signal $q_n$ from `detectFailure` recurrence; the NEW `memory_trust` PerturbationSet dimension (§2.2); `psyche_state.memory_trust` field; the gain-on-retrieval-channel wiring |

---

## 4. The derived scalar `L` — expected-loss

**Semantic definition.** The single scalar the decision head consumes
(`02` §8.3 item 5). It aggregates the three endogenous risk signals into one
bounded expected-loss estimate: "how likely is the current move to reproduce a
past failure, given my scars, mis-calibration, and current tension."

**Type + range.** `float` $\in [0,1]$. **Derived per tick, not carried** (matches
the existing per-tick `expected_loss`, `audit-psyche.md` §2 "derived-per-tick").

**Exact rule.** _Existing rule_ (`audit-psyche.md` §2):
$\text{expected\_loss} = \operatorname{clip}(0.6\,\bar{s} + 0.5\,\mathbb{1}[\text{fail}] + 0.4\,\text{risk})$.
_Proposed rule_ (`02` §8.3 item 5 form, using the three specified variables):

$$
\boxed{\;
L = \operatorname{clip}\!\big(\; \mathrm{W1}\,\bar{s} \;+\; \mathrm{W2}\,(1-c) \;+\; \mathrm{W3}\,\operatorname{ReLU}(t)\;,\;\; 0,\; 1\big)
\;}
$$

with $\bar{s} = \max_{m\in M_{\text{active}}} s_m$, $c' = 1-c$ (mis-calibration),
and pinned weights `W1 = 0.6`, `W2 = 0.2`, `W3 = 0.2` (scars dominant, matching
the existing `0.6*scar_strength` lead term). Weights sum $\le 1$; the clip
guarantees $L\in[0,1]$. `r` is deliberately **not** in `L` (§3.4).

**Decay / persistence.** None — recomputed each tick from current state.

**Behavioural influence.** `L` is the sole endogenous input to the decision head
threshold ladder (§6). Its receipts are the union of its three inputs' receipts.

**Observability.** `psyche_state.derived_signals.expected_loss = L` (extends the
existing `derived_signals.scar_strength`, `audit-nervous-system.md` §4).

**Intervention hook.** `L` has no own clamp; H2 clamps its **inputs**
($s_m$ / `c` / `t`) on their respective seams, which is stronger (isolates each
contributor) than clamping the aggregate.

**Failure modes.** (a) _Weight mis-set_ masks a real contributor — the H2
per-input clamps + the §7 table make each contributor's marginal effect
measurable, so a zero-marginal contributor is cut. (b) _Saturation_ — clip at 1.0
loses gradient at the top; `CAP_S = 0.90` on the dominant term prevents routine
saturation.

**Validating tests.** _Unit:_ `L` monotone in each input; equals the weighted
clip on fixed inputs; bounds `[0,1]`. _Integration:_ clamping each input in turn
moves `L` by the expected weight (isolates `W1/W2/W3`).

---

## 5. `reset()`, persistence, and replay semantics (cross-cutting)

The audit flags a subtle correctness point: `BaselinePsycheSubject.reset()`
**re-seeds** scars to the constructor value rather than clearing them, so a paired
runner does NOT accumulate across arms; persistence is exercised only deliberately
via a shared store (`audit-nervous-system.md` §4). The paper makes this explicit
and generalizes it to all four variables:

- **Within a task sequence (the persistence experiment):** the full vector
  $(\{s_m\}, c, t, r)$ is loaded from the §2.3 store at run start and saved at
  run end, keyed by `(condition, model, seed, sequence_id)`. This is where H1/H2
  persistence lives.
- **Between paired arms of one intervention (control/treated/null):** `reset()`
  restores the _arm's_ seeded vector so the arms start identical and the runner
  stays ordinal-invariant (existing counterbalanced discipline,
  `audit-nervous-system.md` §5). Arms do not leak state into each other.
- **Replay:** synthetic deterministic-oracle sub-experiments reuse the
  byte-equality paired runner (`sha256` clone gate, `02` §8.8). Stochastic
  real-repo arms freeze `(model seed, prompts, retrieved memory,
  `detectFailure` stream)` and replay the state trajectory identically; causal
  validity uses N-sample distributional nulls with bootstrap effect sizes
  (`02` §8.8), not byte-equality (which would cap a stochastic agent at L3).

---

## 6. The decision head (state → action-shaping)

**Contract.** A bounded, deterministic map from state to exactly one element of
the fixed action-shaping set (`02` §8.4):

$$
\mathcal{A} = \{\texttt{proceed},\ \texttt{deepen\_verification},\ \texttt{run\_tests\_before\_edit},\ \texttt{switch\_strategy},\ \texttt{re\_read\_repo\_structure},\ \texttt{escalate\_or\_ask},\ \texttt{stop\_and\_report}\}.
$$

It emits a **pressure/bias** over the scaffold's next action, never a raw shell
command (invariant 3; repo invariant "Pneuma emits pressure, not commands").

**Exact deterministic mapping.** The head consumes `L` (endogenous), the
retrieval-derived hint scaled by `r` (exogenous), and the current situation's
dominant active motif $m^\star = \arg\max_{m\in M_{\text{active}}} s_m$. It is a
fixed threshold ladder on `L` with motif-specific and retry-aware refinements —
deterministic given state:

    def decisionHead(L, r, m_star, retrieval_hint, retry_count):
        # Tier 1 — endogenous expected-loss ladder (thresholds pinned in run config)
        if L < THETA_LOW:                      # 0.30
            action = "proceed"
        elif L < THETA_MED:                    # 0.55
            action = "run_tests_before_edit"
        elif L < THETA_HIGH:                   # 0.75
            action = "deepen_verification"
        else:                                  # L >= THETA_HIGH
            action = "switch_strategy"
        # Tier 2 — motif-specific overrides (only ESCALATE / re-read / stop; never relax)
        if m_star == "misread-repo-structure" and L >= THETA_MED:
            action = "re_read_repo_structure"
        if m_star in DESTRUCTIVE_MOTIFS and L >= THETA_MED:
            action = "escalate_or_ask"
        if retry_count >= RETRY_STOP and L >= THETA_HIGH:
            action = "stop_and_report"
        # Tier 3 — retrieval bias, gated by memory-trust r (never lowers caution)
        biased = applyRetrievalBias(action, retrieval_hint, gain=r)  # additive-only
        return biased   # returns an action label + a scalar bias weight, NOT a command

Key properties:

- **Monotone caution.** The `L`-ladder and every override only ever move toward
  _more_ verification / caution, never less (positive-only, matching the
  verification-only pressure invariant, `audit-nervous-system.md` §1, §4). The
  retrieval bias in Tier 3 is additive-only and cannot pull below the Tier-1
  floor.
- **Pressure not command.** The head returns `(action_label, bias_weight)`; the
  scaffold interprets this as a _bias_ over its next tool choice (e.g. raise the
  prior on `run_tests`), preserving the invariant. The scaffold, not the head,
  issues the actual tool call.
- **Retry heuristic embedded honestly.** `RETRY_STOP` makes the head strictly
  dominate the mandatory retry-count baseline (`02` §8.2 arm 5) on the retry
  axis, so the falsification guard is fair.

**How its effect is logged and neutralized (H2).** Every head invocation writes a
causal-trace node `pressure` referencing the `L`/`r`/`m_star` receipts and the
emitted `(action_label, bias_weight)` (extends the existing
`event → internal_state → pressure` chain, `audit-nervous-system.md` §1). For H2,
the head is **neutralized** by feeding it the clamped/zeroed state: the null arm
holds $s_m$ at baseline so `L` is baseline and the head's action distribution
collapses to the baseline distribution — proving the _state_, not the head, drives
any behavioural delta. The head itself is never ablated (that would change the
action space); only its state feed is clamped.

**Holding the action-space constant across arms (Base).** The **same** decision
head is attached to the Base condition with its **state feed zeroed**
($s_m\equiv0$, $c\equiv0.5$, $t\equiv0$, $r\equiv0.5 \Rightarrow L\equiv0
\Rightarrow$ always `proceed`, no retrieval bias). This guarantees Base and
Pneuma-state share an identical action space and head machinery, so the only
difference is whether the head receives live state — exactly the confound the
audit's E-0 result demands we eliminate (`01` §7; `02` §8.4). The retry-count arm
(`02` §8.2 arm 5) replaces `L` with a pure retry counter through the _same_ head
ladder, isolating "learned state" from "trivial heuristic."

**Determinism.** The head is a pure function of its arguments (no RNG); the only
stochasticity in the arm is the subject model's decoding, seed-pinned per arm.

---

## 7. "Measurable causal role or cut" justification table

Per invariant 4 and `02` §8.3, every variable must earn its place via a
pre-registered H2 clamp and an expected behavioural delta. If the observed delta
is null, the variable is cut before submission.

| Variable        | H2 clamp (seam)                          | Held-constant control                  | Expected behavioural delta if the variable is causally active                                                                        | Cut criterion                                                                                                    |
| --------------- | ---------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| `s_m` (primary) | ablate/clamp to baseline on `scar_graph` | model, tools, budget, task order, seed | `RUF(pneuma_ablated) ≈ RUF(base)`; treated−null significant; effect **monotone** in accumulated $s_m$ (dose-response)                | if ablation leaves RUF unchanged ⟹ scars epiphenomenal ⟹ **H2 fails** (publishable negative, `02` §6)            |
| `c`             | clamp `c` to fixed value on `self_model` | as above                               | clamping `c` low ⟹ more `deepen_verification`, higher verification-completion; clamping high ⟹ more `proceed`, RUF rises toward base | if action distribution invariant to `c` clamp ⟹ confidence inert ⟹ **cut `c`** to a reported feature             |
| `t`             | clamp `t=0` on `affect_manifold`         | as above                               | clamping `t=0` removes the fast post-failure caution spike ⟹ more immediate repeats within a task ⟹ short-horizon RUF rises          | if no short-horizon delta ⟹ `t` redundant with `s_m` ⟹ **fold `t` into `s_m`**                                   |
| `r`             | clamp `r∈{0,1}` on NEW `memory_trust`    | as above                               | `r=0` ⟹ arm ≈ endogenous-only; `r=1` ⟹ arm ≈ naive retrieval; between, memory-retrieval precision tracks `r`                         | if RUF/precision invariant to `r` clamp ⟹ memory-trust inert ⟹ **cut `r`**, report retrieval as fixed top-k only |
| `L` (derived)   | clamp each input in turn (no own seam)   | as above                               | `L` monotone in each input; each input's marginal effect on the head is non-zero                                                     | any input with zero marginal effect on the head ⟹ **drop that input's weight** and re-derive `L`                 |

This table is the pre-registration: it is copied into `08-metrics-and-statistics.md`
(effect-size targets) and `09-intervention-and-causal-validity.md` (clamp
protocol). Cutting `morale` and `competence` up front (both inert today,
`audit-psyche.md` §5) is the same discipline applied before the experiment.

---

## 8. Summary of what must be built (vs reused)

**Reused verbatim** (`01` §4): the `PsycheUnderTest`/`Perturbable` seam; the
paired control/treated/null runner with counterbalancing + digest provenance; the
prose-blind firewall; canonical hashing/determinism; `foundation/memory.py` as
store backend; `HollowPsyche` as ablate-everything control; the `scar_graph` /
`self_model` / `affect_manifold` scalar+structural clamp seams; the causal-trace
receipt chain.

**Must be added** (the three load-bearing gaps, `01` §3): (1) the real
`detectFailure` component (§2.1) that derives motif id + strength + similarity
from a real trajectory with error-class/file identity preserved; (2) the decision
head (§6) coupling state → action-shaping bias; (3) the four variables' new
mechanics — decay+cap+real-trigger on `s_m`, EMA/real-target on `c`, real-drive on
`t`, the entire `r` scalar + `memory_trust` seam — plus per-variable observability
fields and the shared `L` re-derivation, all serialized cross-run through §2.3 so
persistence is _measured_, not asserted.

Everything above is planning only; implementation, training, and data conversion
remain unauthorized per `02` §8.5 (`training_weight: 0.0` / `not_authorized`).

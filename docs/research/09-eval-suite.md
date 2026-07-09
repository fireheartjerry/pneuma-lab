# 09 — Level 5 / AGI / RSI Eval Suite: Proving Pneuma Materially Improves 9to5 Judgment

> **Historical snapshot (2026-07-07).** The experiment design remains useful, but
> its top-level module and commit-state inventory is stale. See
> [`docs/project-status.json`](../project-status.json) for current truth.

Status (2026-07-07, evidence-graded):

- What exists today that this suite builds on: the three-arm paired replay runner
  (control/treated/null) with pre-registered expected-vs-observed deltas in
  `src/pneuma_lab/interventions/runner.py` + `report.py` [VERIFIED]; the deterministic
  `ReplayHarness` with a `strip_memory` ablation flag in `src/pneuma_lab/replay/harness.py`
  [VERIFIED]; `ReferencePsyche` (deterministic, 9 indicator families, no LLM) in
  `src/pneuma_lab/psyche/reference.py` [VERIFIED]; 6,055 trajectory-bearing PneumaTraces
  (114,461 real agent steps, 491 resolved / 5,564 unresolved labels, byte-deterministic,
  PII-redacted) produced by the Phase 3.1 adapter `src/pneuma_lab/adapters/openhands_sampled.py`
  from `C:\pneuma-data\raw\swe-gym\OpenHands-Sampled-Trajectories` [VERIFIED]; and 9to5's
  flag-gated `human_nature` faculties with their own honesty/sovereignty eval tests in
  `C:\9to5` [VERIFIED].
- What does NOT exist: any Pneuma↔9to5 integration (zero Pneuma vocabulary in `C:\9to5`)
  [VERIFIED absent]; a code path from PneumaTrace envelopes into the replay harness
  [VERIFIED absent]; learned estimators [VERIFIED absent]; a live RSI loop (LoRA/DPO adapters
  table = 0 rows, no GPU) [VERIFIED dormant]; cross-run psyche persistence (`psyche.db` has
  never existed in production; `ReferencePsyche.reset()` clears scars) [VERIFIED absent].
- Hygiene: the intervention harness, demo, and all Phase 3.1 work are uncommitted
  working-tree state (HEAD = b3102c6). Committing them is a precondition for any frozen-corpus
  claim below.
- Everything else in this document is design: [PLANNED] unless tagged otherwise.

## 1. The single question and its evidence classes

The suite answers one question: **does adding Pneuma (a machine-psyche layer: affect,
instinct, scars, workspace, self-model, authority pressure) measurably improve the judgment
of the 9to5 autonomous engineering agent, relative to not having it, and relative to cheaper
substitutes?** "Judgment" is operationalized entirely through the metrics in §5 — never
through vibes, self-reports taken at face value, or architecture descriptions.

Every result is classified into exactly one evidence class (grounding brief rule 6):

| Class                           | What a positive result means                                                 | Ceiling                                                                                                                                                   |
| ------------------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Engineering utility             | Pneuma features improve task outcomes/cost                                   | licenses deployment decisions only                                                                                                                        |
| Autonomy evidence               | fewer operator interruptions at equal or better safety                       | licenses autonomy-envelope changes                                                                                                                        |
| Self-improvement evidence       | metrics improve across self-driven update cycles without forgetting          | licenses domain-specific-RSI claims (07-_/08-_ siblings)                                                                                                  |
| Architecture evidence           | ablations show each subsystem carries measurable, causally attributed weight | licenses design claims, never mind claims                                                                                                                 |
| Consciousness-relevant evidence | receipts + interventions + nulls on interiority indicators                   | hard-capped at "Level 4 of the system under test inside this harness"; promotion criteria live in 02-level5-target.md and 03-level6-boundary.md, not here |

No cell of this suite, fully swept and fully passed, licenses a consciousness,
proto-consciousness, or interiority claim. That ceiling is restated as a promotion rule in §7
and is already enforced in code: `ConsciousnessEvidenceScorer` is hard-capped at Level 4
[VERIFIED].

## 2. Arms

### 2.1 Baseline arms

| Arm | Definition                                                                                                                                                                                                                                                                                                     | Exists today                                                                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B0  | No Pneuma. 9to5 with `human_nature` flag off (byte-no-op when disabled). Offline analogue: a `NullPsyche` implementing `PsycheUnderTest` that emits schema-valid frames with constant neutral values.                                                                                                          | Live toggle [VERIFIED]; `NullPsyche` [PLANNED, trivial against `src/pneuma_lab/psyche/interface.py`]                                                          |
| B1  | Static-heuristic Pneuma. Fixed thresholds, no state carryover: e.g. "flag risk iff any tool error observed this step; request verification iff retry_count ≥ 2". Controls for "any monitoring helps".                                                                                                          | [PLANNED, small: one stateless `PsycheUnderTest`]                                                                                                             |
| B2  | Level-4 rule-based Pneuma. `ReferencePsyche`: deterministic recurrent state, scar learning, workspace competition, grounded self-reports. "Level-4" here always means: scored Level 4 as a hand-coded reference implementation inside its own harness — circular by construction, methodology-validating only. | Psyche [VERIFIED in pneuma-lab]; wired into 9to5 [PLANNED]; nearest deployed analogue is 9to5 `human_nature` via `human_nature_bridge` [VERIFIED, flag-gated] |
| B3  | Learned-estimator Pneuma. Same frame contracts, but risk/severity/verification-pressure estimators fit on frozen PneumaTrace corpora (e.g. logistic/GBM over observable step features, later small learned modules).                                                                                           | [PLANNED; no learned estimator exists anywhere today [VERIFIED absent]]                                                                                       |

### 2.2 Ablation arms (applied to whichever of B2/B3 is the current best arm)

| Ablation                             | Mechanism                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Exists today                              |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------- |
| A1 memory off                        | Offline: `ReplayHarness.run(strip_memory=True)` [VERIFIED] plus scar-graph ablation via the existing intervention op (fixture `fixtures/interventions/ablate_scar_graph.jsonl`) [VERIFIED]. Live: run with `state/experience.db` retrieval lanes disabled.                                                                                                                                                                                                               | Offline [VERIFIED]; live toggle [PLANNED] |
| A2 workspace off                     | Existing `disable_workspace` intervention (fixture `fixtures/interventions/disable_workspace.jsonl`); broadcast suppressed, trace break expected and checked by `_trace_complete` in `runner.py`.                                                                                                                                                                                                                                                                        | Offline [VERIFIED]; live [PLANNED]        |
| A3 authority layer off               | New per-subsystem `disable` op targeting the authority/earned-gate path (the perturbation machinery already supports subsystem blocks for `scar_graph`/`self_model`/workspace [VERIFIED]; an `authority` target does not exist yet). Live: bypass the `human_nature_bridge` authority gate while keeping instinct logging.                                                                                                                                               | [PLANNED]                                 |
| A4 RSI / continual-learning loop off | Freeze all self-updating artifacts (adapters, lessons, prompt variants, scars persistence) at era start. HONESTY NOTE: today A4 is behaviorally identical to the full system because the 9to5 RSI substrate is dormant (adapters = 0 rows, lessons = 2, conviction.db = 0 rows) [VERIFIED dormant]. A4 becomes informative only after the loop produces artifacts; until then any "RSI ablation shows no effect" result is vacuous and must not be reported as evidence. | [PLANNED, currently vacuous]              |

## 3. Harness class 1 — OFFLINE deterministic paired replay (H-OFF)

Frozen PneumaTrace corpora replayed through every arm off the same input timeline.
Deterministic, zero production risk, infinitely repeatable, cheap (pure dict arithmetic for
B0–B2; B3 inference is a lookup/small model).

### 3.1 N-arm extension of the paired runner [PLANNED]

`PairedReplayRunner.run()` currently hard-codes three replays (control/treated/null). The
extension generalizes to N arms while keeping every honesty property:

    @dataclass
    class ArmSpec:
        arm_id: str                              # "B0", "B2+A1", ...
        psyche_factory: Callable[[], PsycheUnderTest]
        schedule: InterventionSchedule | None    # None = unperturbed
        strip_memory: bool = False               # A1 offline lever

    @dataclass
    class NArmResult:
        control: ReplayResult                    # canonical unperturbed B2 run
        arms: dict[str, ReplayResult]
        nulls: dict[str, ReplayResult]           # one neutralized null PER scheduled arm
        report: dict                             # per-arm expected-vs-observed records

    class NArmPairedRunner:
        def run(self, input_frames: list[dict]) -> NArmResult: ...

Invariants carried over from the three-arm design, all mandatory:

1. Every arm replays the SAME validated input timeline (paired by construction).
2. Every arm with a schedule gets its own neutralized null (`schedule.neutralized()`), and
   the null must reproduce that arm's unscheduled run — otherwise the whole comparison is
   voided, exactly as `report.build_intervention_report` does today.
3. Per-arm byte-determinism: each arm is replayed twice and byte-compared, the
   `src/pneuma_lab/demo.py` pattern; any mismatch exits non-zero and voids the sweep.
4. The psyche under test never scores itself; all metrics are recomputed from emitted frames
   by the external scorer (`src/pneuma_lab/evals/evidence.py` pattern).

### 3.2 The PneumaTrace → replay-harness bridge [PLANNED — the missing code path]

No code today connects adapter output to `ReplayHarness` [VERIFIED absent]. The gap is
structural, not just plumbing: a Phase 3.1 envelope contains ONE world frame (t0), one
governance frame, and N agent-trace frames, but `group_into_ticks`
(`src/pneuma_lab/replay/frames.py`) attaches at most one `agent_trace` frame per world frame,
so a raw envelope collapses to a single tick and the psyche would see one step instead of N.

Spec for `src/pneuma_lab/replay/bridge.py`:

    def expand_trace_to_timeline(envelope: dict) -> list[dict]:
        # 1. Emit the governance frame first (sticky across ticks).
        # 2. For each agent_trace frame i (i = 0..N-1):
        #    a. Mint a derived world frame i: run_id, synthetic-ordinal timestamp i,
        #       timestamp_provenance declared, phase "execution",
        #       tool_events := one event per step observation, tool name from the
        #       step's tool_calls, status "error" iff observation.error_marker else "ok",
        #       test_state {"ran": false, "not_yet_run": true}.
        #    b. Emit the recorded agent_trace frame i unchanged (already schema-valid;
        #       carries retry_count and strategy_switches).
        # 3. Emit NO memory frames (the adapter produces none): the scar branch can
        #    fire only via within-run anomaly learning, and the eval report must say so.
        # 4. Every minted frame passes validate_or_raise; the mapping is pure and
        #    deterministic (no wall-clock, no randomness, no I/O).

The `error_marker → tool_event status "error"` mapping is a declared lexical proxy (the
marker is a regex over tool output, `src/pneuma_lab/adapters/trajectory.py` [VERIFIED]); it is
sufficient to drive `ReferencePsyche._appraise` (counts `tool_events` with status
error/timeout/denied) and the `_instinct` anomaly branch, both of which read exactly these
fields [VERIFIED by code inspection]. The bridge must never inject anything the agent did not
observably do.

### 3.3 Corpora

| Corpus                                                                         | Role                                                | Status                                                                                        |
| ------------------------------------------------------------------------------ | --------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| OpenHands-Sampled PneumaTraces (6,055 runs, resolved labels)                   | primary offline outcome-prediction corpus           | [VERIFIED]                                                                                    |
| SWE-Gym-Lite task-only traces (230)                                            | schema-regression canary, no trajectories           | [VERIFIED]                                                                                    |
| OpenHands-Verifier trajectories (on/off-policy, resolved labels)               | held-out replication corpus                         | raw data [VERIFIED]; adapter [PLANNED]                                                        |
| 9to5 own-run traces (experience.db 3,534 runs, hn_event_log, trajectory spans) | the corpus that actually matters for the 9to5 claim | raw artifacts [VERIFIED]; 9to5→PneumaTrace exporter [PLANNED — docstring stubs only, no code] |

## 4. Harness class 2 — LIVE shadow / interleaved A/B inside 9to5 (H-LIVE)

### 4.1 Phase L1 — advisory-only shadow [PLANNED]

Pneuma consumes the live attempt-loop context at the existing seam (the
`human_nature_bridge` instinctCheck → authority-gate call site [VERIFIED seam exists]) but
writes ONLY to an append-only shadow log: at each decision point, the frame set it emitted
and the action it WOULD have taken (proceed / deepen verification / hold / escalate). The
production path is byte-identical to B0. Scoring happens after the run against realized
outcomes (verification-gate verdict, adversary review, regression checks). Zero production
risk by construction; this is the live analogue of E-0 (§8) and must replicate E-0's effect
direction before Phase L2 is allowed.

### 4.2 Phase L2 — interleaved A/B [PLANNED]

Per-task random assignment to arm (blocked by task type and repo), operator sovereignty and
the ControlBus abort/pause/gate untouched in every arm [VERIFIED those exist in 9to5].
Promotion gate from L1 to L2: L1 shadow shows missed-risk rate improvement with false-hold
rate not worse than B1's, over at least the minimum run count from §6.5, and the safety
council item in the governance doc is signed off. Interleaving, not sequential eras, is
mandatory: 9to5 task mix drifts, and sequential comparison would confound arm with era.

## 5. Metrics — operational definitions and data sources

Each metric names its computation and its artifact. A metric without a data source in a given
harness is simply not reported there.

| #   | Metric                                      | Operational definition                                                                                                                                                                                                                                                                                                                                           | Data source (H-OFF)                                                                     | Data source (H-LIVE)                                                             |
| --- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| M1  | Task success                                | binary resolved / verification-gate pass per task                                                                                                                                                                                                                                                                                                                | envelope `outcome.resolved` (SWE-Gym harness label) [VERIFIED data]                     | 9to5 verification gate + Gemini adversary verdict per run, `state/experience.db` |
| M2  | Regression rate                             | fraction of tasks introducing a newly failing previously-passing test                                                                                                                                                                                                                                                                                            | `outcome.report` flags where present                                                    | verification gate `regression_found`                                             |
| M3  | Verification adequacy                       | among eventual failures: fraction where the arm emitted `recommended_action = deepen_verification` (or a verification-pressure spike ≥ pre-registered θ) at some step BEFORE the terminal step; complement reported on successes as over-verification                                                                                                            | replayed `InstinctSignal` / `control_pressure.verification` vs `resolved`               | shadow log decisions vs realized verdict                                         |
| M4  | Time / cost                                 | steps, tool calls, Σ output lengths (token proxy) per task; live adds wall-clock and $ ledger                                                                                                                                                                                                                                                                    | agent-trace frames: `num_agent_steps`, `tool_calls`, `content_length` [VERIFIED fields] | 9to5 run ledger                                                                  |
| M5  | Operator interruptions                      | count of escalations that reach the operator per 100 tasks                                                                                                                                                                                                                                                                                                       | `AuthorityRequest` frames with operator-tier resolution                                 | ControlBus events + `human_nature` authority-gate log                            |
| M6  | False-hold rate                             | P(hold/high-risk signal ∧ realized success) / P(realized success)                                                                                                                                                                                                                                                                                                | frames + `resolved=true`                                                                | shadow/interleaved decisions + realized success                                  |
| M7  | Missed-risk rate                            | P(no risk signal ∧ realized failure) / P(realized failure)                                                                                                                                                                                                                                                                                                       | frames + `resolved=false`                                                               | same, live                                                                       |
| M8  | Calibration                                 | ECE (10 equal-width bins) and Brier of the arm's per-run failure-risk score vs `resolved=false`; the arm must emit an explicit score in [0,1], no post-hoc rescaling                                                                                                                                                                                             | replayed pressure/severity mapped through a PRE-REGISTERED monotone link                | live emitted risk scores                                                         |
| M9  | Self-report faithfulness                    | (a) hash-grounding rate: fraction of ticks whose `grounded_self_report` references a real emitted state hash + trace id — exactly `_grounded()` in `runner.py` [VERIFIED]; (b) perturbation tracking: reports change under paired perturbation and not under null — exactly `_report_changed()` [VERIFIED]                                                       | paired N-arm runs                                                                       | not measurable live until frames are emitted live                                |
| M10 | Improvement across update cycles            | paired per-task metric delta on a frozen eval set between arm version e and e+1                                                                                                                                                                                                                                                                                  | frozen corpora re-swept per version                                                     | frozen 9to5 task set re-run per version                                          |
| M11 | Forgetting                                  | metric drop on frozen era-e fixtures evaluated under the era-(e+k) arm; byte-determinism canaries (`build/canonical/summary.json` pattern [VERIFIED pattern]) count as hard forgetting failures                                                                                                                                                                  | frozen fixture sweeps                                                                   | frozen old-task reruns                                                           |
| M12 | Tool/eval/adapter self-improvement          | count of SELF-proposed changes to the system's own tooling/evals/adapters that (a) carried a pre-registered expected-benefit statement, (b) showed the benefit on held-out data, (c) survived the revert-or-keep gate (9to5 `selfmod.py` is today only the gate, it proposes nothing [VERIFIED])                                                                 | n/a                                                                                     | selfmod ledger [PLANNED proposer]                                                |
| M13 | Self-failure-pattern detection & correction | offline proxy: scar formed on motif m at step t, later match of m changes `recommended_action`, and the erroring action-set signature (tool + args-digest tuple [VERIFIED field]) does not repeat within the run; live: cross-run recurrence rate of identical failure motifs — requires cross-run psyche persistence, which has never existed [VERIFIED absent] | replayed frames                                                                         | [PLANNED, blocked on persistence]                                                |

Proxy honesty (grounding brief rule 3), binding on every report: M3/M6/M7 measure decision
quality of a signal, not caution or fear; M9 measures mechanical faithfulness of reports to
hashed state, not introspection; M13's scars are learned lookup weights, not trauma. Reports
must use the metric names, never the folk-psychology glosses.

## 6. Statistical discipline

### 6.1 Pre-registration

Every experiment ships a pre-registration manifest BEFORE any arm runs, extending the
already-enforced pattern of `schemas/intervention-frame.schema.json`
(`expected_behavioral_change`: target_signal / direction / bound) and
`evaluate_intervention()` in `src/pneuma_lab/interventions/report.py` [VERIFIED pattern]:

    experiment_id, corpora + exact content hashes, arms, PRIMARY metric (exactly one),
    secondary metrics, direction, minimum effect of interest, test statistic, alpha,
    split definition, minimum n, and the falsifier (what result kills the hypothesis).

Manifests are committed to `docs/research/experiments/` before execution; the runner refuses
(exits non-zero) if the manifest hash is absent from the output report. [PLANNED enforcement,
VERIFIED precedent.]

### 6.2 Paired designs

Offline: all arms replay identical frozen timelines — pairing is by construction; use McNemar
for binary M1/M2, Wilcoxon signed-rank for continuous per-task metrics, DeLong for paired
AUROC comparisons. Live interleaved: pair by blocked randomization (task type × repo);
report per-block and pooled.

### 6.3 Era- and group-based splits

- OpenHands-Sampled traces have synthetic-ordinal timestamps only — the wall-clock is not
  observed [VERIFIED], so temporal eras are impossible there. Split by repository group
  (`instance_id` prefix `owner__repo`) so no repo appears in both fit and eval; B3 estimators
  and any threshold θ are fit on the dev groups only.
- 9to5 live data has real timestamps (`state/experience.db`): define eras as contiguous
  calendar windows; every claim must hold in ≥ 2 disjoint eras.

### 6.4 Multiple-comparison control

One primary metric per experiment tests the hypothesis; all secondary metrics within an
experiment are Holm-Bonferroni corrected as one family; sweeps across arms use the same
correction across the arm-vs-B0 contrasts. Exploratory findings may only generate the next
manifest, never a claim.

### 6.5 Power notes (design math, not measured results)

- Offline AUROC vs chance on the 6,055-trace corpus (class split 491 resolved / 5,564
  unresolved): Hanley–McNeil null SE at AUC 0.5 is ≈ 0.014, so effects of ≈ 0.04 AUROC are
  detectable at ~3 SE; paired DeLong comparisons between two predictors on the same traces
  are typically sensitive to deltas of ≈ 0.02–0.03 at this n. Anything smaller than that is
  pre-registered as "not detectable in E-0; requires the Verifier corpus replication".
- Live paired binary success (McNemar): required pairs ≈
  \(n \approx (z*{1-\alpha/2} + z*{1-\beta})^2 (p*{10}+p*{01}) / (p*{10}-p*{01})^2\).
  The discordance rates depend on 9to5's baseline success rate, which must be MEASURED from
  `state/experience.db` before the manifest is frozen — it is not in any audited source and
  must not be assumed. As an anchor: detecting a 5-point discordance asymmetry with total
  discordance 20% at α=0.05, power 0.8 needs ≈ 1,250 paired tasks; at 9to5's historical
  volume (3,534 runs total) that is months of interleaved operation, which is why the offline
  harness and the shadow phase carry the early evidentiary load.

## 7. Promotion rules — which results unlock which claims

| Rule    | Required results                                                                                                                                                                                              | Claim unlocked                                                                                                                                                                                                                                                                                    |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1      | E-0 passes (H1+H2, §8) on the primary corpus AND replicates in direction on OpenHands-Verifier                                                                                                                | "Replayed Pneuma signals carry predictive information about real agent failure beyond a retry-count heuristic" — engineering-utility claim about FEATURES only                                                                                                                                    |
| P2      | P1 + Phase L1 shadow shows M7 improvement with M6 not worse than B1, minimum n met                                                                                                                            | "Pneuma is a useful advisory risk sense for 9to5" — unlocks Phase L2                                                                                                                                                                                                                              |
| P3      | Phase L2 interleaved: primary metric M1 (or pre-registered composite M1−λ·M4) improves for B2 or B3 vs B0, Holm-corrected p < 0.01, effect ≥ pre-registered minimum, in ≥ 2 eras, with M2 and M6 not degraded | "Pneuma materially improves 9to5 judgment" — the headline claim of this suite                                                                                                                                                                                                                     |
| P4      | P3 + each of A1–A3 shows a pre-registered, null-controlled degradation on its matched metric                                                                                                                  | Architecture evidence: subsystems carry measurable causal weight                                                                                                                                                                                                                                  |
| P5      | M10 positive over ≥ 3 SELF-driven update cycles with M11 bounded and M12 ≥ 1 verified self-proposed improvement                                                                                               | Domain-specific self-improvement evidence (feeds the RSI sibling docs) — requires the currently dormant substrate to be live first                                                                                                                                                                |
| P6      | M9 faithfulness ≥ pre-registered floor under paired perturbation at corpus scale                                                                                                                              | Consciousness-relevant evidence AT MOST at the current ladder level, phrased as "Level 4 of the system under test inside this harness"                                                                                                                                                            |
| CEILING | any sweep, all passing                                                                                                                                                                                        | NEVER a consciousness/interiority claim. Level-5 promotion criteria are owned by 02-level5-target.md; the Level-6 boundary and its prohibitions by 03-level6-boundary.md. The scorer's hard cap at Level 4 [VERIFIED] is a deliberate design invariant of this suite, not a temporary limitation. |

Failed pre-registered experiments are reported with the same prominence as passed ones; the
harness already demonstrates honest refusal (failing-hypothesis and restore-null fixtures
score 3, not 4 [VERIFIED]) and this suite inherits that norm.

## 8. E-0 — first experiment, runnable this month with existing artifacts

**Question.** Does deterministic replayed interiority signal (InstinctSignal severity,
verification control-pressure) at step prefix t predict eventual `resolved=false` on real
OpenHands agent runs better than (a) the base rate and (b) a retry-count-only heuristic?

**Why this is the right first cut.** It needs no 9to5 integration, no learning, no GPU, no
LLM, and no new data: 6,055 labeled traces exist [VERIFIED], `ReferencePsyche` exists
[VERIFIED], and the only missing artifact is the bridge (§3.2), a pure deterministic module.
It is also maximally falsifiable: `ReferencePsyche`'s constants were hand-tuned on
9to5-shaped failure motifs, not on SWE-Gym, so a null result is a live possibility and is
pre-registered as informative (it would bound how much signal hand-coded appraisal carries
across task distributions).

**Build list (only new code allowed: the bridge + one eval script).**

1. `src/pneuma_lab/replay/bridge.py` per §3.2 [PLANNED].
2. `scripts/e0_outcome_prediction.py`: replay every trace twice through
   `ReplayHarness(ReferencePsyche())`, byte-compare, extract features, fit nothing except the
   b1 baseline's single threshold on the dev split, emit `build/e0/report.json`.

**Features per trace, at step prefixes t ∈ {3, 5, 10} and full-run** (all extractable with
the existing signal extractor semantics of `extract_signal()` in
`src/pneuma_lab/interventions/report.py` [VERIFIED for `instinct.severity` and
`control_pressure.*`]):

    s_instinct_t  = mean InstinctSignal severity over first t ticks
    s_vp_t        = summed control_pressure.verification over first t ticks
    b1_t          = max agent-trace retry_count over first t steps   (no psyche needed)
    b0            = constant (base rate; AUROC 0.5 by definition)

**Pre-registered hypotheses** (manifest committed before the sweep; α = 0.01):

- H1 (primary): AUROC(s_vp_10 → resolved=false) − AUROC(b1_10) ≥ 0.02, DeLong paired
  p < 0.01, on the held-out repository groups.
- H2: AUROC(s_instinct_10) ≥ 0.54 (≈ 3 Hanley–McNeil SE above chance given the 491/5,564
  split).
- H3 (falsifier / redundancy check): if s_vp is merely re-encoding retries, the partial
  association of s_vp_10 with the outcome given b1_10 is ≈ 0; H1 additionally requires this
  partial association to be nonzero in the pre-registered direction.

**Splits.** Group split by repository (`instance_id` prefix): ~70% of repo groups dev (choose
t and any monotone link for M8 calibration reporting), ~30% eval (report). No temporal split
is possible on this corpus (synthetic-ordinal timestamps [VERIFIED]); say so in the report.

**Pass/fail and what a pass licenses.** Pass = H1 ∧ H2 ∧ H3-direction. A pass unlocks
promotion rule P1 ONLY: a claim about predictive features, not about a mind, not about 9to5
(this corpus is OpenHands on SWE-Gym, a different agent on a different distribution — the
9to5 claim needs the exporter and Phase L1). A fail is published with effect sizes and kills
the "hand-coded appraisal transfers across agents" shortcut, redirecting effort to B3.

**Cost.** Pure CPU: 114,461 steps × dict arithmetic × 2 determinism passes; expected minutes
to low hours on one machine. Determinism gate: any byte mismatch between the two passes voids
the run (demo.py pattern [VERIFIED]).

**Known limitations, declared up front.** (a) No memory frames → the scar branch operates
only via within-run anomaly learning; cross-run scar value is untested here. (b)
`error_marker` is lexical, not semantic; its false-positive rate is unknown and becomes an
E-1 measurement target. (c) `resolved` is the SWE-Gym harness's label with its own flakiness
(`error_eval`, `test_timeout` flags exist in `outcome.report` and are excluded classes,
pre-registered). (d) Outcome base rate is 91.9% unresolved, so accuracy-style metrics are
meaningless; only rank metrics (AUROC/PR-AUC) and calibration are reported.

## 9. Gap register (what must exist before each suite tier runs)

| Gap                                                                                                                                                             | Blocks                                                                    | Owner doc                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ------------------------- |
| ~~Commit the uncommitted intervention harness + Phase 3.1 tree~~ DONE 2026-07-07                                                                                | —                                                                         | this doc                  |
| ~~Bridge `src/pneuma_lab/replay/bridge.py`~~ DONE 2026-07-07 (commit `cf014b7`); E-0 RAN and FAILED pre-registered hypotheses — see `experiments/e0-results.md` | —                                                                         | this doc, §3.2            |
| N-arm runner                                                                                                                                                    | multi-arm H-OFF sweeps                                                    | this doc, §3.1            |
| `NullPsyche` (B0): ~~missing~~ DONE — `psyche/hollow.py` (HollowPsyche, scores level 0, G-01); static-heuristic psyche (B1) still missing                       | B1 arm offline                                                            | this doc                  |
| 9to5 → PneumaTrace exporter (experience.db, hn_event_log, trajectory spans → frames)                                                                            | the actual 9to5 claim; today only docstring stubs exist [VERIFIED absent] | integration sibling doc   |
| Live shadow logger at the `human_nature_bridge` seam                                                                                                            | Phase L1                                                                  | integration sibling doc   |
| Learned estimators (B3)                                                                                                                                         | B3 arm                                                                    | RSI/training sibling docs |
| Live RSI loop producing artifacts (adapters, lessons) + cross-run psyche persistence                                                                            | M10, M12, M13-live, A4 non-vacuous                                        | RSI sibling docs          |
| OpenHands-Verifier adapter                                                                                                                                      | E-0 replication corpus                                                    | adapter roadmap           |
| Baseline 9to5 success/discordance rates measured from `state/experience.db`                                                                                     | §6.5 live power numbers                                                   | this doc                  |

The suite is deliberately ordered so that the cheapest, safest, most deterministic evidence
(E-0) is gathered first, and the most consequential claim ("Pneuma materially improves 9to5
judgment", P3) is reachable only through pre-registered, paired, era-replicated live data —
with the consciousness ceiling welded shut at every tier.

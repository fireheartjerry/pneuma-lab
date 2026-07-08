# E-0 Pre-Registration — Replayed Interiority Signals vs Real Agent Failure

**Registered:** 2026-07-07, BEFORE any full-corpus run. Committed to main before
`scripts/e0_outcome_prediction.py` executes on the eval split. This file is the
source of record; the report must echo it verbatim.

## Question

Does deterministic replayed interiority signal (InstinctSignal severity,
verification control-pressure) from `ReferencePsyche`, driven by the replay
bridge over real OpenHands agent trajectories, predict eventual
`resolved=false` better than (a) the base rate and (b) a retry-count-only
heuristic?

## Data

- Corpus: `C:\pneuma-data\processed\swe-gym\openhands-sampled\pneuma_traces.jsonl`
  (6,055 trajectory-bearing PneumaTraces v0.2; adapter report hashes committed).
- Label: `y = 1` iff `labels.resolved == false` (predicting failure).
- Exclusions (label QC, counted in the report): traces whose
  `outcome.report.error_eval` or `outcome.report.test_timeout` is true.
- Split: grouped by `labels.repo`. Deterministic rule: a repo is EVAL iff
  `int(sha256(repo_utf8).hexdigest(), 16) % 10 < 3`, else DEV; empty repo
  string goes to DEV. All hypothesis tests are evaluated on the EVAL split
  only. No temporal split exists (timestamps are synthetic-ordinal; declared).

## Signals (exact operationalization)

Replay: `expand_trace_to_timeline(trace)` →
`ReplayHarness(ReferencePsyche(), validate=False).run(timeline)` (recorded
frames were schema-validated at adapter build; minted frames validated by the
bridge in strict mode). Tick 0 is the preamble (original world frame, no agent
step) and is excluded; agent ticks are 1..N.

For prefix length `t ∈ {3, 5, 10}`, with `t_used = min(t, N)`:

- `s_instinct_t` = (Σ severity of all InstinctSignal frames emitted in agent
  ticks 1..t_used) / t_used.
- `s_vp_t` = Σ `control_pressure.pressures.verification` over agent ticks
  1..t_used (summed, per doc 09 §8).
- `b1_t` = max `retry_count` over the first t_used recorded agent-trace frames
  (no psyche needed).
- `b0` = constant (base rate; AUROC 0.5 by definition).

Primary prefix: `t = 10`.

## Hypotheses (α = 0.01, evaluated on EVAL split)

- **H1 (primary):** AUROC(`s_vp_10` → y) − AUROC(`b1_10` → y) ≥ 0.02, with
  paired DeLong test p < 0.01.
- **H2:** AUROC(`s_instinct_10` → y) ≥ 0.54 (≈ 3 Hanley–McNeil SE above chance
  at this class split).
- **H3 (redundancy falsifier):** the b1-stratified AUROC of `s_vp_10`
  (AUROC computed within each discrete `b1_10` stratum containing both
  classes, combined as a weighted mean by stratum size) exceeds 0.5 in the
  pre-registered direction. If s_vp merely re-encodes retries, this is ≈ 0.5;
  H1 requires H3 > 0.52.

**Pass** = H1 ∧ H2 ∧ (H3 > 0.52). A pass unlocks promotion rule P1 of
`../09-eval-suite.md` ONLY: a claim about predictive FEATURES of a replayed
reference psyche over one external agent's trajectories — not about a mind,
not about 9to5, not about any consciousness level.

**Fail** = any hypothesis missed. A fail is published with full effect sizes
and kills the "hand-coded appraisal transfers across agents" shortcut,
redirecting effort to learned estimators (doc 08). A null result is
pre-registered as informative.

## Determinism gate

Every trace is replayed twice; the canonical-JSON serialization of all output
frames must be byte-identical per trace. Any mismatch voids the run.

## Statistics

- AUROC: Mann–Whitney with midranks (ties handled).
- H1: fast DeLong paired AUROC variance; one-sided z-test.
- Multiplicity: H1 is the single primary; H2/H3 are gate conditions, not
  additional discoveries — no correction needed beyond the conjunctive pass
  rule.
- Minimum n: the EVAL split must contain ≥ 60 positives... correction:
  positives are failures (~92% base rate), so the binding minimum is ≥ 60
  NEGATIVES (resolved=true) in the EVAL split; if fewer, report
  "underpowered — no claim".

## Known limitations (declared now)

(a) No memory frames — scar branch operates only via within-run anomaly
learning. (b) `error_marker` is lexical, not semantic. (c) `resolved` is the
SWE-Gym harness label with its own flakiness (exclusions above). (d)
ReferencePsyche constants were hand-tuned on 9to5-shaped motifs, not SWE-Gym —
transfer failure is a live outcome. (e) Only rank metrics and calibration are
meaningful at a 91.9% base rate.

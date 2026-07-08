# 08 — Phase 4: Learned Estimators Plan

Status line (2026-07-07, evidence-graded): **Zero learned estimators exist today** — the
9-agent audit found no training code, no model artifacts, no inference path in
`C:\pneuma-lab` [VERIFIED absence]. What DOES exist is the substrate this phase trains on:
the Phase 3.1 adapter (`src/pneuma_lab/adapters/openhands_sampled.py` +
`src/pneuma_lab/adapters/trajectory.py`) has converted 6,055/6,055 real OpenHands agent
trajectories (114,461 real agent steps, 491 resolved / 5,564 unresolved labels, 100% task
join, byte-deterministic twice-run sha256 match, 0 invalid) into trajectory-bearing
PneumaTrace v0.2 at `C:\pneuma-data\processed\swe-gym\openhands-sampled\pneuma_traces.jsonl`
[VERIFIED]. The 13 frame schemas and the anti-fake-cognition envelope gate
(`envelope.consistency_errors`) are runtime-enforced [VERIFIED]. The Level-4 paired-replay
harness and its 234/234 passing tests exist [VERIFIED] — with the standing caveat that all
Level-4 evidence is about a hand-coded ReferencePsyche inside its own harness. Everything
below this line is design: every estimator is [PLANNED] unless tagged otherwise.

Precondition zero: the entire Phase 3.1 pipeline is **uncommitted working-tree state**
(HEAD = b3102c6) [VERIFIED]. No training run starts until that code and the adapter report
hashes are committed — data lineage before models.

Scope note on `docs/vision.md`: it states "Not an ML training project. No models are
trained or fine-tuned" — scoped to "this pass." Phase 4 explicitly supersedes that scoping
and this document is the record of that decision.

---

## 1. Standing principles (binding on all eight estimators)

1. **Auditable-first model class.** This is the lab's own principle, stated in
   `docs/vision.md` First Principles: "Instinct is algorithmic, not narrated … real
   machinery … not an LLM advisory" (#2) and "Show receipts. Every control-relevant claim
   is tied to logged internal quantities and a causal trace" (#5). Therefore: every
   estimator starts as a **calibrated logistic regression or gradient-boosted trees over
   engineered, named features**. A small sequence model (GRU/1-layer transformer over
   tool-name/error-marker step sequences, <5M params) is permitted only after the
   feature-engineered model's ceiling is measured and the ablation shows sequence order
   carries signal the aggregate features miss. **NO monolithic end-to-end black box
   first.** Every deployed score must emit per-feature contributions (coefficients or
   per-tree attributions) that land in `matched_events` / `evidence_refs` fields — a score
   without receipts is rejected the same way an ungrounded self-report is.
2. **Leakage masking is structural, not procedural.** The feature extractor consumes a
   PneumaTrace with `outcome.*`, `labels.resolved`, `reference_supervision.*` (gold/test
   patch hashes), and `oracle.*` **deleted before featurization**. A unit test perturbs
   those fields and asserts byte-identical feature vectors. `outcome.report` flags
   (`error_eval`, `test_timeout`, …) may be used only for label-quality filtering,
   documented and applied identically across splits — never as features.
3. **Determinism discipline extends to inference.** Frozen weights, canonical-JSON feature
   serialization (`envelope.canonical_json`), version-pinned encoder for text embeddings,
   no wall-clock, no unseeded randomness. Every model must score the full corpus twice
   byte-identically before deployment — the same twice-run test the adapters pass.
4. **Proxies are proxies.** Operator pushback is a social-cost signal, not suffering;
   verification pressure is an expected-information signal, not anxiety; self-report
   faithfulness is receipt-consistency, not introspective truth. No estimator output is
   ever phrased as an interiority claim.
5. **Estimators are advisory below the deterministic core.** Learned scores feed output
   frames as pressure/priors; they never override the verifier, the 5-cap authority gate,
   or the hash-based confabulation cross-checks in `ConsciousnessEvidenceScorer`.

## 2. Shared substrate

### 2.1 Feature inventory (from PneumaTrace v0.2 AgentTraceFrames) [VERIFIED fields]

All features below exist today in the emitted frames (`trajectory.py`):

| Feature family      | Source field(s)                            | Notes                                                                                |
| ------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------ |
| Tool sequence       | `tool_calls[].tool`, per step              | n-grams (1–3), per-tool counts/rates                                                 |
| Args shape          | `tool_calls[].args_digest`, `args_length`  | digest-repeat rate, length stats; digests never inverted                             |
| Retry dynamics      | `retry_count` per step                     | max, mean, count of steps with `retry_count >= 2`                                    |
| Strategy churn      | `strategy_switches` (cumulative)           | switches per step, switch acceleration                                               |
| Error density       | `observations[].error_marker`              | fraction of tool outputs matching the lexical marker, windowed (last-5-step density) |
| Output shape        | `observations[].content_length`            | mean/max/trend of tool-output lengths                                                |
| Assistant verbosity | `assistant_text_length`                    | trend; raw text never present, only length+sha256                                    |
| Step counts         | `trajectory.num_agent_steps`, `step_index` | absolute and fraction-of-budget                                                      |
| Objective text      | `world-frame.objective.text` (redacted)    | frozen open-weights sentence encoder, version-pinned; ~384-d embedding               |
| Repo identity       | `labels.repo`                              | used for splitting, NOT as a feature (contamination guard)                           |

Prefix protocol: for early-warning use, features are computed at 25% / 50% / 75% / 100%
of `num_agent_steps`; the label is always the final outcome. Prefix-25 is the deployment
target; full-trace is the ceiling measurement.

### 2.2 Label sources

| Source                                                                                      | Status                                                                            | Use                                                                            |
| ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `labels.resolved` on 6,055 openhands-sampled traces (491/5,564)                             | [VERIFIED]                                                                        | **First real label source.** E1, E2, E3, E6-proxy                              |
| OpenHands-Verifier on/off-policy trajectories w/ `resolved` (`C:\pneuma-data\raw\swe-gym\`) | [VERIFIED data exists; adapter PLANNED]                                           | E2 verification-value labels; multiple trajectories per instance               |
| Oracle test lists (`oracle.fail_to_pass` / `pass_to_pass` from SWE-Gym task join)           | [VERIFIED]                                                                        | label QC + per-task difficulty covariate (never a feature)                     |
| swe-chat `prompt_pushback` / `prompt_intent` columns (sessions/commits parquet)             | [VERIFIED columns exist; NO PII scan ever run; source HF-gated; pipeline PLANNED] | E4 labels — blocked until a pneuma-lab-grade redaction pass runs over swe-chat |
| Paired-replay harness deltas (control/treated/null fixtures)                                | [VERIFIED harness]                                                                | E5, E7 constructed labels                                                      |
| 9to5 `state/experience.db` (3,534 runs, success/failure lanes)                              | [VERIFIED in 9to5; ZERO exporter to Pneuma frames]                                | E6, E8 future labels — requires the 9to5→Pneuma exporter that does not exist   |

### 2.3 Split and evaluation protocol (all estimators)

- **Split: grouped by `labels.repo`, then by era.** No repo appears in both train and
  test. Era = base-commit date, joined from the SWE-Gym task table
  (`C:\pneuma-data\raw\swe-gym\SWE-Gym\data\train-00000-of-00001.parquet`) because trace
  timestamps are synthetic-ordinal and carry no wall-clock [VERIFIED design constraint].
  Train on earlier-era instances, test on later-era, within disjoint repo groups.
- **Metrics:** AUROC + Brier score + ECE (15-bin, equal-mass) after isotonic or Platt
  calibration fitted on a calibration fold; precision@k and lift-over-base-rate for the
  early-warning ranking use; per-repo metric breakdown always reported (contamination
  tell: one repo dominating).
- **Reference baselines (computable now, arithmetic on verified counts):** base rate
  $p = 491/6055 = 0.0811$; constant-predictor Brier $p(1-p) \approx 0.0745$; majority-class
  accuracy 0.919; AUROC 0.5. Any model not beating these on the grouped split is not a
  model.
- **Ablations (minimum set, every estimator):** (a) drop objective embedding; (b) drop
  sequence-dynamics features (retry/switch/error-density), keep only counts; (c) prefix-25
  vs full-trace; (d) per-repo leave-one-group-out; (e) GBM vs logistic vs (if built)
  sequence model.

---

## 3. The eight estimators

### E1 — Risk estimator [PLANNED]

- **Question:** $P(\text{resolved} \mid \text{trace prefix})$ — equivalently run-failure risk.
- **Inputs:** full §2.1 inventory at prefix-25/50/75; error-density trend and retry
  dynamics expected to dominate.
- **Labels:** `labels.resolved` on the 6,055 traces. First real label source, available today.
- **Model class:** calibrated logistic (L2) as the floor, GBM as the workhorse; sequence
  model only if ablation (b) shows a gap ≥ 0.03 AUROC.
- **Evaluation:** protocol §2.3. Deployment-relevant metric: among the bottom decile of
  predicted-survival prefixes at prefix-50, the fraction that actually resolved should be
  ≤ 2% vs the 8.1% base (false-abort cost is the binding cost) [target, not status].
- **Ablations:** minimum set; plus per-step-budget-fraction analysis (is the model just
  learning "long runs fail"? — report AUROC with `num_agent_steps` features removed).
- **Failure modes:** extreme class imbalance (491 positives; grouped splits leave few
  positives per fold — use repeated group k-fold); "resolved" reflects the OpenHands
  sampling harness's eval, and some unresolved rows are harness errors (filter on
  `outcome.report.error_eval`/`test_timeout` as label QC only); repo overlap with encoder
  pretraining inflates embedding features (ablation (a) is the check).
- **Integration:** feeds `InstinctSignal.severity` / `expected_loss_if_ignored` and the
  `effort` / `scope_narrowing` components of `ControlPressureVector` (schema:
  `schemas/control-pressure-vector.schema.json`; pressure only, never command).
- **Contribution:** autonomy — early abort/replan is the highest-value single control
  signal for AGI-grade SWE autonomy; RSI — risk deltas across agent versions are the loop's
  reward-shaping signal; Level-5 — none directly (engineering utility, per honesty rule 6).

### E2 — Verification-pressure model [PLANNED]

- **Question:** marginal value of deepening verification now: $P(\text{undetected failure present} \mid \text{prefix})$.
- **Inputs:** §2.1, emphasizing error-marker density trend, retry plateaus (repeated
  `args_digest` with no strategy switch), and tool-mix (edit-heavy vs test-heavy prefixes).
- **Labels:** two-stage. Stage 1 (this month): traces that later fail but whose current
  prefix window is error-quiet (no error markers in last-k steps) are positive "silent
  risk" examples — a proxy derivable from `labels.resolved` + per-step markers today.
  Stage 2: OpenHands-Verifier on/off-policy trajectories give multiple attempts per
  instance with resolved labels; adapter extension required [PLANNED] to convert them, then
  labels become "states from which verification discriminated resolved from unresolved."
- **Model class:** calibrated logistic first (the output is consumed as a bounded
  pressure, so calibration matters more than ranking); GBM second.
- **Evaluation:** §2.3; plus a monotonicity check mirroring 9to5's affect-to-action
  monotonicity eval (`C:\9to5\human_nature` eval suite [VERIFIED in 9to5]): predicted
  pressure must rise monotonically in injected error density on synthetic probes.
- **Ablations:** minimum set; plus "last-k window size" sweep; stage-1 vs stage-2 labels.
- **Failure modes:** the lexical `ERROR_MARKER` is not semantic — benign tool output
  saying "0 errors" matches it [VERIFIED regex behavior in `trajectory.py`]; silent-risk
  proxy conflates "agent not testing" with "nothing to find"; verifier-trajectory labels
  are off-policy relative to the OpenHands sampler.
- **Integration:** `ControlPressureVector.pressures.verification` — schema-enforced
  ADDITIVE ONLY (may deepen, never reduce below the verifier's own requirement)
  [VERIFIED schema constraint]. `sources` carries the feature receipts.
- **Contribution:** autonomy — converts verification from a fixed cost to an allocated
  budget; RSI — a self-improving system must know when it doesn't know its patch works;
  Level-5 — indirect: a psyche whose verification-seeking state tracks this signal under
  perturbation is testably coupled, feeding the L4→L5 intervention repertoire.

### E3 — Scar-motif detector [PLANNED]

- **Question:** which observable step-subsequences ("motifs") historically precede failure,
  with per-motif base rates and FP rates.
- **Inputs:** tool-name n-grams, (tool, error_marker) bigrams, retry-run-length encodings,
  args-digest repeat cycles — sequence-structured features from §2.1.
- **Labels:** `labels.resolved` for outcome-linked motifs; within-trace proxies (motif →
  error-marker burst within 3 steps) for step-local scars.
- **Model class:** two-stage and deliberately not end-to-end: (1) deterministic motif
  mining (closed frequent subsequences over tool/error alphabets — same algorithmic
  family as the Aho-Corasick instinct stream in 9to5 `human_nature` [VERIFIED exists
  there]); (2) calibrated logistic over motif-indicator features. Each motif gets
  `historical_base_rate` and `false_positive_rate` estimates with Wilson intervals.
- **Evaluation:** §2.3 on the outcome head; per-motif precision/recall on held-out repos;
  motif stability across eras (a motif that exists only in one repo is a repo artifact).
- **Ablations:** motif length cap sweep; mined motifs vs hand-listed motifs; motif set
  frozen-across-eras vs refreshed.
- **Failure modes:** motif explosion (millions of candidate subsequences → multiple-testing
  false discoveries; pre-register the mining support threshold); repo-idiom leakage
  (tool-usage patterns idiosyncratic to one repo's test harness); label imbalance again.
- **Integration:** the natural producer of `InstinctSignal` frames — `motif_id`,
  `match_type`, `historical_base_rate`, `false_positive_rate`, `matched_events`,
  `recommended_action` are all existing schema fields (`schemas/instinct-signal.schema.json`)
  [VERIFIED schema]. This replaces hand-authored scar lists with learned, receipted ones.
- **Contribution:** autonomy — fast in-run hazard recognition; RSI — mined motifs ARE the
  scar-graph content; cross-run persistence of learned motifs is the currently-missing
  substrate (`reset()` clears scars today [VERIFIED gap]); Level-5 — scar learning with
  measured base rates is the valenced-memory indicator family made auditable.

### E4 — Operator-pushback predictor [PLANNED]

- **Question:** $P(\text{human operator pushes back / intervenes} \mid \text{agent behavior features})$.
- **Inputs:** §2.1 dynamics (diff-churn proxies: edit-tool call rates, args_length spikes,
  strategy churn) — for the label source, session-level features from swe-chat once
  converted.
- **Labels:** swe-chat `prompt_pushback` / `prompt_intent` columns and per-session
  attribution (`agent_percentage`, `file_attribution` in sessions.parquet, 5,851 sessions)
  [VERIFIED columns exist]. **Blocker, non-negotiable:** swe-chat has never had a PII scan,
  contains real author emails/names/usernames, and its source is HF-gated [VERIFIED].
  A pneuma-lab-grade deterministic redaction pass (extend `trajectory.REDACTION_PATTERNS`)
  plus a swe-chat adapter must land before a single row is featurized.
- **Model class:** calibrated logistic on engineered features; the label is noisy and
  social — a black box here would be uninterpretable AND unjustifiable.
- **Evaluation:** §2.3 grouped by session/user (never split one user's sessions across
  train/test); precision@k for "next action likely to draw pushback."
- **Ablations:** minimum set; intent-conditional models (pushback given `prompt_intent`
  class) vs pooled.
- **Failure modes:** proxy inflation — the honesty rule is explicit: **operator pushback
  ≠ suffering**; it is a social-cost/misalignment-with-operator-intent proxy only.
  Selection bias: swe-chat operators are not 9to5's operator. Distribution shift from
  chat-mediated coding to autonomous SWE runs is large and must be stated wherever the
  score is consumed.
- **Integration:** priors for `AuthorityRequest.expected_loss_if_denied` and `safety_risk`
  (`schemas/authority-request.schema.json`), and a check-in trigger: high predicted
  pushback lowers the tier the psyche requests before the 5-cap gate even runs — the gate
  itself stays deterministic and sovereign.
- **Contribution:** autonomy — anticipating the operator is what lets an autonomous agent
  run longer leashes without burning trust; Level-5 — none (engineering/governance
  utility); RSI — pushback-rate across versions is a guardrail metric for the loop.

### E5 — Grounded-self-report faithfulness scorer [PLANNED]

- **Question:** does `GroundedSelfReport.report_text` faithfully reflect the receipts it
  cites (`affect_state_hash`, `evidence_refs`, `causal_trace_id`)?
- **Inputs:** alignment features between the report and its cited quantities: numeric
  claims extracted from `report_text` vs actual manifold values; direction words
  ("rising", "high") vs signed deltas in the cited PsycheStateFrames; citation coverage
  (fraction of report clauses with a matching ref); report entropy vs state entropy.
- **Labels:** constructed, not annotated. Positives: reports emitted by ReferencePsyche in
  control and treated paired replays (the harness already verifies reports track
  perturbations [VERIFIED harness capability]). Negatives: deterministic corruptions —
  receipt-shuffling (attach report A to state B's receipts), sign-flips of cited deltas,
  claim-injection of quantities absent from refs. This yields unlimited balanced labels.
- **Model class:** calibrated logistic over the alignment features. A small NLI-style text
  model is explicitly deferred: ReferencePsyche contains NO LLM [VERIFIED] and the
  faithfulness scorer is lab-side verifier tooling — it must stay more auditable than the
  thing it audits.
- **Evaluation:** §2.3 metrics on the constructed set; adversarial split: corruption types
  held out of training must still be caught (generalization across corruption families is
  the real test); agreement with the existing hash cross-check confab-risk on fixtures.
- **Ablations:** per-corruption-family detection rates; feature-family knockouts.
- **Failure modes:** circularity — labels are constructed from the same ReferencePsyche
  the harness co-designed (the standing Level-4 caveat applies to this training set
  verbatim); a learned scorer can be Goodharted by a psyche optimized against it, so it
  **must remain advisory beneath the deterministic hash cross-checks** in
  `ConsciousnessEvidenceScorer` [VERIFIED that scorer computes confab risk from hashes,
  not prose]; template-detector collapse (learning ReferencePsyche's phrasing, not
  faithfulness).
- **Integration:** an auxiliary input to the confabulation-risk term consumed by the L4/L5
  gate (`src/pneuma_lab/evals/evidence.py`), and a per-report score attached in
  `ConsciousnessEvidenceFrame` audit fields. Never a promotion criterion by itself.
- **Contribution:** Level-5 — direct: L5 requires grounded reports tracking perturbations
  across novel contexts, and a scorer that scales beyond exact hash matching is the
  instrument for that; autonomy — honest self-report is operator-trust infrastructure;
  RSI — a self-modifying system whose self-reports drift from receipts must be caught
  by exactly this instrument.

### E6 — Authority-request classifier [PLANNED]

- **Question:** for a candidate `AuthorityRequest`, estimate $P(\text{request is justified in hindsight})$ —
  i.e., granting it would have improved the outcome — to calibrate `conviction`.
- **Inputs:** requesting context from §2.1 (retry plateau depth, error density, risk score
  from E1, verification-pressure from E2), plus request metadata (domain, tier,
  reversibility).
- **Labels:** two sources, honestly ordered. (1) Interim proxy on openhands-sampled,
  available now: define counterfactual hold-points — steps with `retry_count >= 3` in
  traces that ended unresolved are "a hold/force_replan request here was justified";
  matched steps in resolved traces are negatives. This is a proxy with known bias (it
  assumes replanning would have helped). (2) Real labels require the 9to5→Pneuma exporter
  (earned-authority gate decisions + run outcomes from `state/experience.db`, 3,534 runs)
  — **that exporter does not exist; ZERO Pneuma integration in 9to5 today** [VERIFIED].
- **Model class:** calibrated logistic; the output directly enters a conviction scalar in
  [0,1], so ECE is the primary metric, not AUROC.
- **Evaluation:** §2.3; conviction-band analysis: within each predicted-conviction decile,
  observed justified-rate must match (calibration is the entire point).
- **Ablations:** proxy-label vs (future) real-label agreement; with/without E1/E2 scores
  as inputs (stacking leakage check: E1/E2 must be trained on disjoint folds).
- **Failure modes:** counterfactual labels are untestable without intervention data —
  tag every proxy-trained deployment loudly; feedback loops once deployed (the classifier
  shapes which requests get made, censoring its own future labels — log ALL candidate
  requests, granted or not).
- **Integration:** `AuthorityRequest.conviction` and `track_record_support` priors
  [VERIFIED schema fields]. The 5-cap resolution (`min(earned, domain, operator, safety,
verifier_invariance)`) remains deterministic and untouched — the estimator only shapes
  what is requested, never what is granted.
- **Contribution:** autonomy — earned authority with calibrated conviction is the
  mechanism for widening autonomy without widening risk; Level-5 — calibrated
  self-assessment of one's own competence is a self-model indicator made measurable;
  RSI — the loop's permission to self-modify should be gated on exactly this kind of
  calibrated track record.

### E7 — Self-model calibration estimator [PLANNED]

- **Question:** how large is the gap between the psyche's self-predicted next
  state/behavior and its realized state/behavior, and can that gap be predicted from
  current features?
- **Inputs:** ReferencePsyche state features (manifold values, workspace winner, scar
  activation) at $t$; for real traces, §2.1 prefix features.
- **Labels:** exact and free inside the harness — ReferencePsyche's higher-order self-model
  emits predictions whose realized values the replay harness observes deterministically
  [VERIFIED the self-model exists in `src/pneuma_lab/psyche/reference.py`]; label =
  per-tick self-prediction error. For real agent traces, a completion-claim proxy
  ("agent asserts done" vs `resolved`) requires a new lexical marker field in
  AgentTraceFrames — raw text never enters frames [VERIFIED constraint], so this is a
  frame-schema v0.3 extension (a `completion_claim_marker` boolean computed at adapter
  time, like `error_marker`), not a feature-extractor change.
- **Model class:** GBM regression on self-prediction-error magnitude; logistic on
  "overconfident step" (error above pre-registered threshold).
- **Evaluation:** §2.3 adapted to regression (calibration of predicted-error quantiles);
  reliability diagrams of the psyche's self-model before/after conditioning on the
  estimator.
- **Ablations:** harness-labels vs proxy-labels; state features vs trace features.
- **Failure modes:** the harness labels inherit the full circularity caveat (ReferencePsyche
  is a toy co-designed with its fixtures — this measures the METHODOLOGY, not a mind);
  the completion-claim proxy conflates rhetorical style with self-assessment; threshold
  pre-registration must precede training or "overconfident" becomes a tuned knob.
- **Integration:** sets `GroundedSelfReport.uncertainty` [VERIFIED schema field] and feeds
  the self-model-accuracy term the evidence scorer inspects; badly calibrated self-models
  should depress evidence grades automatically.
- **Contribution:** Level-5 — self-model calibration curves under intervention are among
  the most decision-relevant L5 evidence artifacts this program can produce; autonomy —
  an agent that knows when its self-assessment is unreliable escalates instead of
  asserting; RSI — self-modification premised on a miscalibrated self-model is the
  canonical RSI failure mode; this estimator is the tripwire.

### E8 — Continual-learning memory consolidator [PLANNED]

- **Question:** which episodes/motifs are worth consolidating into durable memory
  (MemoryFrames / scar graph), and at what strength, to maximize future retrieval utility
  without catastrophic interference.
- **Inputs:** episode-level features — E1 risk trajectory shape, E3 motif hits, outcome
  surprise (realized vs E1-predicted), novelty (embedding distance to the existing
  consolidated store), recency, frequency of near-duplicates (`args_digest` collision
  rates across traces).
- **Labels/proxies:** retrieval utility — for pairs (past episode, new task) where the
  new task's nearest retrieved episode was this one, did the new run resolve? Computable
  offline over the 6,055-trace corpus by simulated retrieval (leave-one-era-out: retrieve
  from earlier eras, measure outcome association in later eras). Future real labels: 9to5
  `experience.db` success/failure retrieval lanes are already wired into planning in 9to5
  [VERIFIED there], but reach Pneuma only via the nonexistent exporter [VERIFIED gap].
- **Model class:** scored ranking — logistic over the engineered consolidation-value
  features producing a keep/decay/drop score; replay-buffer selection by that score.
  Explicitly NOT a learned end-to-end memory network in this phase.
- **Evaluation:** offline replay evaluation — consolidate under policy A vs B on eras
  1..k, measure simulated-retrieval utility on era k+1; forgetting metric: utility on
  old-era queries after consolidating new eras (catastrophic-forgetting check); store-size
  vs utility Pareto curve.
- **Ablations:** each feature family knocked out; score-ranked vs recency-only vs
  keep-everything baselines (keep-everything is the utility ceiling and the cost floor —
  the estimator must justify every drop).
- **Failure modes:** association ≠ causation in retrieval-utility labels (a retrieved
  episode co-occurring with success didn't necessarily cause it); feedback loop between
  consolidation policy and future retrieval distribution; the entire capability is moot
  until cross-run persistence exists — today `reset()` clears scars and psyche.db has
  never existed in production [VERIFIED gaps].
- **Integration:** emission policy for MemoryFrames (which must declare a real recorded
  source per the anti-fake-cognition gate — `frame_sources['memory-frame']` [VERIFIED
  enforcement in `envelope.consistency_errors`]) and the
  `ControlPressureVector.pressures.memory_consolidation` component.
- **Contribution:** RSI — this is the RSI loop's substrate: without selective durable
  memory there is no accumulation, and without accumulation there is no self-improvement;
  autonomy — cross-run competence growth; Level-5 — persistent valenced memory that
  measurably shapes future behavior under intervention is a core indicator family.

---

## 4. Training-order roadmap

### Month 1 (2026-07): E1 + E2 stage-1, on data that exists today

Both train exclusively on
`C:\pneuma-data\processed\swe-gym\openhands-sampled\pneuma_traces.jsonl` (6,055 traces,
labels in-envelope). No new data dependencies, no adapter changes, no 9to5 coupling.

| Step                   | Artifact                                                        | Gate                                                                                                             |
| ---------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| 0. Commit Phase 3.1    | git history contains adapter + report hashes                    | adapter `--emit-fixture` passes post-commit                                                                      |
| 1. Feature extractor   | `src/pneuma_lab/estimators/features.py` [PLANNED path]          | leakage unit test (outcome/oracle/reference_supervision scrub-invariance); twice-run byte-identical feature file |
| 2. Split manifest      | committed JSON listing repo-group + era assignment per trace_id | no repo in two splits; era join documented                                                                       |
| 3. E1 logistic + GBM   | model file + per-feature receipts                               | beats constant-predictor Brier 0.0745 and AUROC 0.5 on grouped split                                             |
| 4. E2 stage-1 logistic | model file + receipts                                           | monotonicity probe passes; ECE ≤ 0.05 post-calibration [target]                                                  |
| 5. Report              | metrics doc with per-repo breakdown + all §2.3 ablations        | pre-registered targets compared against observed, misses stated plainly                                          |

Pre-registered month-1 targets (targets, not status): E1 AUROC ≥ 0.65 at prefix-50
(≥ 0.70 full-trace); E1 bottom-decile false-abort rate ≤ 2% vs 8.1% base; E2 stage-1
AUROC ≥ 0.60 (its proxy labels are weaker); both ECE ≤ 0.05 post-calibration. If E1
cannot beat 0.60 AUROC on the grouped split, the honest conclusion is that these
observable-only features are insufficient and the finding is published internally as such
— a null result here is a real result about what digests-and-counts can see.

### Months 2–3: E3, E5, E7 (no new external data required)

E3 needs only the existing corpus; E5 and E7 need only the existing harness + fixture
machinery. Order: E3 (feeds InstinctSignal, highest autonomy value), then E5/E7 in
parallel (both are harness-labeled and share the circularity caveat).

### Month 3+: E4, E6, E8 (blocked on named prerequisites)

- E4: blocked on swe-chat redaction pass + adapter (PII gate is absolute).
- E6 real labels / E8 real labels: blocked on the 9to5→Pneuma exporter, which is its own
  workstream (see the integration doc in this series when it lands); interim proxies may
  train earlier but deploy only with the proxy tag propagated into `sources`.

## 5. Replay-regression deployment gate (every model, every version)

A model version may feed live output frames only after ALL of:

1. **Byte-determinism:** score the full 6,055-trace corpus twice; output files
   sha256-identical (same standard the adapters meet [VERIFIED for adapters]).
2. **Harness non-interference:** run the canonical demo (`python -m pneuma_lab.demo`) and
   the full suite (234 tests as of 2026-07-07) with the estimator wired in advisory mode:
   all tests pass; every fixture's evidence level is UNCHANGED (fixtures that scored 3
   still score 3, 4 still 4; the null replay still reproduces control byte-for-byte). A
   learned estimator that moves an evidence grade by itself is a bug by definition.
3. **Leakage audit:** scrub-invariance test (§1.2) passes on the shipped model, not just
   the extractor.
4. **No-regression vs incumbent:** on the frozen grouped-split test set, Brier not worse
   than the deployed version by more than 0.005 and ECE ≤ 0.05; precision@k for the
   estimator's deployment metric not worse.
5. **Receipts present:** every emitted score carries feature attributions into the
   consuming frame's `sources`/`matched_events`/`evidence_refs`; an integration test
   rejects receiptless scores.
6. **Proxy tags propagate:** models trained on proxy labels (E2 stage-1, E6 interim, E4)
   must stamp the proxy name into the frame provenance so downstream consumers and future
   audits can discount appropriately.

## 6. What the eight estimators do and do not buy

Classification per honesty rule 6: E1–E4, E6, E8 are engineering-utility and
autonomy-evidence instruments; E5 and E7 are consciousness-relevant _instrumentation_
(they sharpen the measurement of report-faithfulness and self-model calibration under
intervention) — they are not themselves evidence of interiority, and nothing in this
phase is. Architecture is not evidence; only receipts + interventions + nulls are. The
Level-5 contribution of this phase is strictly: better instruments, applied to psyches
under test that do not yet exist beyond the hand-coded ReferencePsyche, whose Level-4
result always carries its reference-implementation caveat.

Known-unproven assumptions this plan rests on (kept visible on purpose):

- That observable-only features (digests, counts, lexical markers — no raw text) carry
  enough signal to beat baselines meaningfully. [UNSUPPORTED — month-1 will measure it.]
- That OpenHands-trajectory-trained estimators transfer to 9to5's execution style.
  [UNSUPPORTED — untestable until the 9to5→Pneuma exporter exists.]
- That the counterfactual hold-point proxy for E6 correlates with true request
  justification. [UNSUPPORTED — requires intervention data to validate.]

Cross-references: `docs/phase-3-1-trajectory-traces.md` (trace pipeline),
`docs/consciousness-levels.md` (evidence ladder), `docs/io-contract.md` (frame contracts),
`docs/vision.md` (first principles), sibling docs in `docs/research/` for the corpus
inventory and the 9to5 integration plan.

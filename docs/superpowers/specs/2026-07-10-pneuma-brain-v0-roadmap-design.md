# PneumaBrain-v0 Roadmap and Readiness Design

Date: 2026-07-10
Status: design (authoritative roadmap); supersedes the planning prose in
`docs/data/unified-pneuma-brain-training-plan.md`.
Scope: this document authorizes no training. It locks the product definition,
the v0.1 input/output contract, the phase sequence, and the precise meaning of
"all dataset lanes ready to start training the unified model."

## 1. Problem and motivation

Pneuma Lab already ships the full offline supply chain for a learned cognition
layer: `PneumaTrace` adapters, a trajectory→replay bridge, the
`PneumaTrainingExample` contract, per-dataset converters, a leakage-masked
observable-only feature extractor, the E1/E2 logistic estimators, a fail-closed
trainer preflight, and a normalized dataset-readiness registry. What it does not
have is a single, current, authoritative statement of (a) what the unified model
is, (b) what its first version consumes and emits, and (c) what "every lane is
ready" concretely requires and how that is machine-verified.

The empirical motivation is a recorded negative result, not a hope. Experiment
E-0 (`build/e0/report.json`, `docs/research/experiments/e0-results.md`) replayed
6,018 OpenHands-Sampled traces and tested pre-registered hypotheses that the
hand-wired `ReferencePsyche` signals predict task failure. They failed:

- `ReferencePsyche` verification-pressure signal: AUROC ≈ 0.34 at prefix 10.
- `ReferencePsyche` instinct signal: AUROC ≈ 0.35 at prefix 10.
- A plain logistic model over observable trajectory features (baseline B1):
  AUROC ≈ 0.70 at prefix 10.

The coded psyche does not predict failure; a learned model over observable
features does. That is the honest niche for `PneumaBrain-v0`: a learned,
calibrated, auditable estimation layer that replaces hand-tuned instinct/pressure
priors with supervised signals, while staying strictly below the deterministic
governance and verifier gates.

## 2. Product definition

`PneumaBrain-v0` is one unified, multi-task, evidence-producing model for
autonomous SWE-agent cognition. It consumes canonical `PneumaTrainingExample`
records (offline) or a live input frame of the same shape (later), and emits a
bundle of advisory, evidence-referenced frames.

Hard boundaries (carried in every output, not only in docs):

- It does not write code, act as the agent, or act as the verifier.
- It does not change runtime authority, bypass or weaken verification, or
  promote a consciousness-evidence level by itself.
- It is not, by itself, a Level-4/5 claim. Estimator usefulness is not machine
  interiority evidence.

It is a learned substrate whose outputs are priors, pressures, risks, and
evidence summaries that the deterministic Pneuma gates may consult.

## 3. v0.1 input/output contract (locked)

### 3.1 Input — `PneumaBrainInputFrame`

Observable-only by default, built from the existing `PneumaTrainingExample`
`input` block and its feature refs. No raw task text, no patch text, no oracle,
no answer-bearing fields enter the model; digests, lengths, counts, tool names,
markers, and approved structured features only. The v0.1 feature surface is
exactly the leakage-masked extractor already shipped
(`src/pneuma_lab/estimators/features.py`, `FEATURE_EXTRACTOR_VERSION`):
prefix-windowed tool histograms, retry statistics, strategy switches, error
density, observation/assistant length summaries, and no absolute-count features
in the length-ablation variant.

### 3.2 Output — `PneumaBrainOutputBundle`

v0.1 emits five heads only. `WorkspaceSalienceFrame`,
`SelfReportFaithfulnessFrame`, `PatchSuccessFrame`, and any counterfactual head
are explicitly deferred.

| v0.1 head                           | task_type               | Supervision source today                         |
| ----------------------------------- | ----------------------- | ------------------------------------------------ |
| `RiskEstimateFrame`                 | `RISK_PREDICTION`       | `harness_outcome` (`resolved`) — high confidence |
| `VerificationPressureEstimateFrame` | `VERIFICATION_PRESSURE` | constructed proxy — medium                       |
| `FailureShapeFrame`                 | `FAILURE_SHAPE`         | constructed proxy — medium                       |
| `MotifRiskFrame`                    | `SCAR_MOTIF`            | observable motif mining — medium                 |
| `TaskDifficultyFrame`               | `TASK_DIFFICULTY`       | constructed proxy — medium                       |

Every frame carries `prediction_value`, `confidence` + calibration scope,
`evidence_refs`, `model_version`, `dataset_provenance`, `task_provenance`,
`known_limitation`, `blocked_uses`, and `proxy_label_warning` when the label is a
proxy. Only `RISK_PREDICTION` has a clean high-confidence label in the current
corpus; the other four ship as advisory proxies and must not drive headline
claims until better labels exist.

### 3.3 Phase sequence

```
v0.1  RISK / VERIFICATION / FAILURE_SHAPE / MOTIF / DIFFICULTY  (this roadmap)
v0.2  PATCH_SUCCESS / VERIFIER_VALUE        (after leakage controls proven)
v0.3  SELF_REPORT_FAITHFULNESS              (receipt-grounded)
v0.4  WORKSPACE_SALIENCE                    (after live workspace targets)
v0.5  counterfactual introspection
v1.0  integrated with intervention harness + evidence scoring
```

## 4. The "all lanes ready" end state (this effort's target)

"All 11 lanes ready to start training the unified model" cannot mean "all lanes
become training data." Gold-patch benchmarks have no negative class and no
trajectory (they are held-out evaluation by construction); privacy and dual-use
corpora are blocked. Forcing them into training would destroy evaluation
validity and violate the project's gates.

The correct, verifiable definition adopted here:

> Every dataset lane resolves to exactly one terminal **corpus role**, the
> train-eligible lanes are assembled into one authorizable v0.1 corpus with a
> single remaining human authorization gate, and this state is machine-checked.

Terminal roles (four values):

| Role                    | Meaning                                          | Lanes (2026-07-10 registry)                                                                                           |
| ----------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `v0_1_train`            | In the first unified training corpus             | `swe-gym-openhands-sampled` (ready, human-auth pending); `open-swe-traces` (train, pending full-corpus convert + ToS) |
| `expansion_train_later` | Train candidate; needs adapter/join/license work | `swe-gym-openhands-verifier`, `swe-gym-lite`, `swe-polybench`, `multi-swe-bench`, `swe-evo`                           |
| `eval_only`             | Held-out evaluation; never trained               | `swe-bench`, `swe-mera`                                                                                               |
| `blocked`               | Excluded until a hard gate clears                | `swe-chat` (privacy), `sec-bench-pro` (dual-use), `swe-bench-pro` (license), `dialogue-swe-bench` (archived/license)  |

"Ready to start training" is therefore true when: (1) every lane has a role,
(2) the `v0_1_train` set is fully specified (members, weights, quarantined
overlap repos, split policy, and each member's enumerated remaining gates), and
(3) the only action left to begin a run is a human signing the corpus
authorization manifest. This effort delivers 1–3; it does not sign.

## 5. Readiness architecture (deliverable B)

The estimator authorization surface
(`schemas/estimator-training-authorization.schema.json`) is scoped to one
dataset and the two E1/E2 heads. The unified corpus needs a surface one level
up. Deliverable B adds, without authorizing anything:

1. **Unified corpus manifest** —
   `docs/data/training-readiness/pneuma-brain-v0-corpus.json`. Authoritative
   `lane_roles` for every registry lane (completeness enforced), the `v0_1_train`
   members with weights and per-member remaining gates, the quarantined overlap
   repos (bound to the cross-dataset leakage registry), the split policy, mixture
   caps, and a pointer to the authorization surface. Metadata-only,
   non-authorizing.
2. **Corpus authorization schema + pending template** —
   `schemas/pneuma-brain-corpus-authorization.schema.json` and a committed
   `*.pending.json` template. `decision` is fixed to `not_authorized` in the
   template; a human replaces it with a signed artifact to begin a run. This is
   the single human gate.
3. **Checker + tests** — `pneuma_lab.dataset_readiness` gains corpus validation:
   every lane resolved, roles legal, `v0_1_train` members are genuine train lanes
   (not eval-only/blocked), quarantine repos equal the leakage registry overlap
   set, and authorization status is `not_authorized`. `--check` validates the
   corpus alongside the registry.
4. **Status reconciliation** — close `B-REGISTRY-NORMALIZATION` (the normalized
   `dataset-registry.json` + checker is the shared contract), advance
   `pneuma_brain_training` to `corpus_specified_pending_authorization`, register
   the new schema, and update the readiness overview.

## 6. Non-goals and preserved gates

- No training, E1/E2 execution, calibration, or runtime integration is
  authorized or performed.
- No raw/processed/build dataset content is committed; manifests stay
  metadata-only and repository-coherent (no `C:/pneuma-data` references).
- Blocked and eval-only lanes keep `training_weight: 0.0` and cannot become
  corpus members through this change.
- No J-space, self-report-trust, or consciousness-level promotion.
- The verifier-invariance rule holds: readiness state is additive and auditable.

## 7. Verification

- `python -m pneuma_lab.dataset_readiness --check`
- `python -m pneuma_lab.status --check`
- `python -m pytest tests/ -q`
- `python -m pneuma_lab.schemas` load check / `tests/test_schema_loads.py`
- `git diff --check`

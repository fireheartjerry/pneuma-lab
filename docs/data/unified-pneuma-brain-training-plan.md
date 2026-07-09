# Unified PneumaBrain Training Plan

Status: planning only.

This document defines a unified training architecture for a single future model
artifact, tentatively named `PneumaBrain-v0`. It does not authorize training,
E1/E2 execution, calibration, runtime integration, J-space/Jacobian Lens work,
SWE-chat processing, raw-data mutation, or consciousness-level claims.

## 1. Final model concept

`PneumaBrain-v0` should be one shared model trained across approved datasets
through one canonical training format. The long-term product is not one model
per estimator or one model per dataset. E1, E2, E3, and later estimator families
are task-conditioned output modes of the same learned artifact.

Development may still use baselines, probes, feature extractors, and temporary
single-task heads. Those are measuring sticks and scaffolds. The deployable goal
is one model artifact that can consume canonical examples from multiple data
sources and emit advisory, evidence-bearing frames.

The model must stay below deterministic governance and verifier logic. Its
outputs are priors, pressures, risks, and evidence summaries. They must never
directly change runtime authority, bypass verification, or promote an evidence
level by themselves.

## 2. Canonical training format

Define a shared `PneumaTrainingExample` contract before the next modeling pass.
The contract should be committed as a schema or documented data contract before
Dataset #1 is converted into training examples.

```json
{
    "example_id": "string",
    "dataset_id": "string",
    "source_path_or_hash": "string",
    "example_type": "TrajectoryExample | VerifierExample | TaskExample | PatchExample | PreferenceExample | SelfReportExample | ReplayExample",
    "task_type": "string",
    "input": {},
    "target": {},
    "label_provenance": {
        "kind": "harness_outcome | verifier_verdict | gold_patch | source_label | constructed_label | human_label | proxy_label | none",
        "description": "string",
        "confidence": "high | medium | low"
    },
    "privacy_status": "public_or_benchmark | redaction_verified | pii_blocked | dual_use_blocked | eval_only",
    "allowed_training_uses": ["string"],
    "blocked_training_uses": ["string"],
    "split_group": {
        "repo": "string|null",
        "task_id": "string|null",
        "session_or_user": "string|null"
    },
    "era_or_time_group": "string|null",
    "evidence_refs": [
        {
            "kind": "trace_id | adapter_report | manifest | schema | eval_report",
            "ref": "string"
        }
    ]
}
```

Example-type semantics:

| Example type | Meaning |
|---|---|
| `TrajectoryExample` | Ordered observable agent/tool events with final outcome labels. |
| `VerifierExample` | Candidate or policy-variant traces with verifier/outcome verdicts. |
| `TaskExample` | Task-only benchmark item with repo, issue, oracle, and optional gold patch. |
| `PatchExample` | Patch/input/target supervision, including structural patch metadata. |
| `PreferenceExample` | Pairwise or ranked choices, only when provenance and labels are explicit. |
| `SelfReportExample` | Claim-vs-receipt or report-faithfulness examples. |
| `ReplayExample` | Harness/replay examples with control, treated, or null traces. |

The `input` field should be observable-only by default: frame IDs, digests,
lengths, tool names, event markers, task metadata, and approved structured
features. Raw text inclusion requires an explicit privacy and leakage decision
for the dataset and task. The `target` field must be masked per `task_type` so
missing labels do not become negative labels.

## 3. Unified task types

Estimator names should become task types or output modes, not separate final
models.

| Task type | Intended supervision |
|---|---|
| `RISK_PREDICTION` | Probability that a task/run/trace will fail or remain unresolved. |
| `VERIFICATION_PRESSURE` | Expected value of deeper verification or suspicion of silent failure. |
| `FAILURE_SHAPE` | Failure family, error pattern, or unresolved trajectory shape. |
| `SCAR_MOTIF` | Observable motifs that historically precede failure or recovery. |
| `TASK_DIFFICULTY` | Expected difficulty, horizon length, or partial-credit hardness. |
| `OPERATOR_PUSHBACK` | Likelihood of correction/pushback; a social-cost proxy only. |
| `SELF_REPORT_FAITHFULNESS` | Consistency between claims/reports and cited receipts. |
| `VERIFIER_VALUE` | Marginal usefulness of verifier trajectories or candidate checks. |
| `PATCH_SUCCESS` | Patch or candidate solution success under available oracle. |
| `WORKSPACE_SALIENCE_LATER` | Later workspace-salience prediction after live traces exist. |

Tension, pushback, and self-report labels are proxies. They are not affect,
interiority, or consciousness evidence.

## 4. Dataset contribution matrix

This section uses metadata, manifests, reports, and safe directory inspection
only. The local data root is `C:\pneuma-data`. Raw paths below describe where
datasets live; they are not instructions to inspect raw sensitive content.

| Dataset ID / name | Raw path | Processed path | Adapter / report availability | Onboarding status | Shape | Approximate size / counts | Labels available | Privacy / redaction status | Canonical examples | Unified task types | Recommended role | Caveats |
|---|---|---|---|---|---|---:|---|---|---|---|---|---|
| `swe-gym` / SWE-Gym plus released trajectories | `raw/swe-gym` | `processed/swe-gym` | `lite`, `openhands-sampled`, and `openhands-verifier` reports exist; registry exists for sampled | Dataset #1 onboarded through `swe-gym-openhands-sampled`; other local artifacts partially adapter-backed | task-only, trajectory, verifier trace, patch/test | 81,338 rows / 19 files; sampled 6,055 traces; verifier 5,272 traces; lite 230 traces | `resolved`, policy variant verdicts, oracle test lists, gold/test patch coverage | sampled and verifier processed outputs have deterministic redaction totals; raw content remains non-targeted | `TrajectoryExample`, `VerifierExample`, `TaskExample`, `PatchExample` | `RISK_PREDICTION`, `VERIFICATION_PRESSURE`, `FAILURE_SHAPE`, `SCAR_MOTIF`, `VERIFIER_VALUE`, `PATCH_SUCCESS`, `TASK_DIFFICULTY` | Primary training source after canonical conversion | Sampled is imbalanced, 491 resolved vs 5,564 unresolved. Verifier report has 0 task joins and 5,272 missing task joins, so examples must preserve that caveat. |
| `swe-bench` / SWE-bench family | `raw/swe-bench` | `processed/swe-bench` | Metadata inventory and row counts exist; no canonical Pneuma training adapter yet | Downloaded, not onboarded for canonical training | task-only, patch/test | 22,962 rows / 8 files | gold patch, test patch, FAIL/PASS_TO_PASS, repo/base commit | public benchmark data, but contamination-heavy | `TaskExample`, `PatchExample` | `PATCH_SUCCESS`, `TASK_DIFFICULTY`; limited contamination-aware breadth for `FAILURE_SHAPE` | Schema sanity and breadth source, not headline evaluation | Known leakage and weak-test concerns; requires contamination flags and grouped splits. |
| `swe-bench-pro` / SWE-Bench Pro | `raw/swe-bench-pro` | `processed/swe-bench-pro` | Metadata inventory and row counts exist; no canonical Pneuma training adapter yet | Downloaded public portion, not onboarded | task-only, patch/test | 2,924 local rows / 4 files, including public split plus mirror material | gold patch, test patch, repo language, execution refs | public benchmark data; held-out/commercial splits unavailable | `TaskExample`, `PatchExample` | `PATCH_SUCCESS`, `TASK_DIFFICULTY` | Held-out-style replication after adapter | Use canonical public source only; do not treat unavailable held-out/commercial splits as local data. |
| `multi-swe-bench` / Multi-SWE-bench and Multi-SWE-RL | `raw/multi-swe-bench` | `processed/multi-swe-bench` | Metadata inventory and row counts exist; no canonical Pneuma training adapter yet | Downloaded, not onboarded | task-only, patch/test, other; zipped trajectories later | 10,399 rows / 162 files | fix/test patch outcomes, language, date-windowed RL records, possible trajectory zips | public benchmark data; license metadata is inconsistent | `TaskExample`, `PatchExample`, later `TrajectoryExample` | `PATCH_SUCCESS`, `TASK_DIFFICULTY`, later `FAILURE_SHAPE`, `SCAR_MOTIF` | Approved later source after adapter work; useful for multilingual breadth | `_trajs` are ZIPs and need extraction provenance. Large RL snapshots must be pinned and capped so they do not dominate. |
| `swe-chat` / SWE-chat | `raw/swe-chat` | `processed/swe-chat` | Metadata, parquet verification, transcript summary, and inventory exist; no privacy-approved adapter | Downloaded locally but privacy-blocked | chat/session, trajectory-like tool events, preference/proxy labels | 8,359,057 counted rows / 5,856 files; 5,850 transcripts; 2,732,252 parquet rows; 3,098,007 transcript rows | `prompt_pushback`, `prompt_intent`, session success, attribution fields, tool events | P2 privacy-blocked; real PII columns and raw session content; no approved corpus-wide PII scan | Later `PreferenceExample`, `SelfReportExample`, conversation-derived `TrajectoryExample` after privacy gates | `OPERATOR_PUSHBACK`, `SELF_REPORT_FAITHFULNESS`, `VERIFICATION_PRESSURE`; weak future authority/request proxies | Privacy-blocked future corpus, zero training weight now | Do not touch raw content. Requires quarantine, deterministic redaction, earned `pii_scanned`, k-anonymity, and synthetic fixtures only. |
| `dialogue-swe-bench` / Dialogue SWE-Bench | `raw/dialogue-swe-bench` | `processed/dialogue-swe-bench` | Metadata inventory and row counts exist; no canonical Pneuma training adapter yet | Downloaded, recommended Dataset #2 | chat/session, task-only, patch/test, preference-like simulated dialogue | 550 rows / 2 files | simulated correction/dialogue labels, final patch/test outcomes, difficulty/persona metadata | P0 style public/simulated data; license/provenance caveats remain | `TaskExample`, `PreferenceExample`, `SelfReportExample`, possibly small `TrajectoryExample` over turns | `OPERATOR_PUSHBACK`, `SELF_REPORT_FAITHFULNESS`, `TASK_DIFFICULTY`, `PATCH_SUCCESS` | Dataset #2; schema sanity for dialogue/operator-shaped examples | Built on SWE-bench Verified, so contamination caveats apply. Simulated operator data is not real-human behavior. |
| `sec-bench-pro` / SEC-bench and SEC-bench Pro | `raw/sec-bench-pro` | `processed/sec-bench-pro` | Metadata inventory and row counts exist; no canonical Pneuma training adapter | Downloaded metadata, policy-blocked | task-only, patch/test, other security metadata | 1,264 rows / 5 files | sanitizer/bug report signals, patch refs, project/error type | P3 dual-use restricted; metadata/structure only | Later `TaskExample`, `PatchExample` after policy gates | limited security `TASK_DIFFICULTY`, `PATCH_SUCCESS`, maybe `SCAR_MOTIF` | Do not train until dual-use policy and redaction gates exist | No PoC execution. Exploit-adjacent descriptions and patches need gating. |
| `swe-evo` / SWE-EVO | `raw/swe-evo` | `processed/swe-evo` | Metadata inventory and row counts exist; no canonical Pneuma training adapter | Downloaded, not onboarded | long-horizon task, patch/test, third-party trajectory logs | 32,211 loaded rows / 31,647 files | Fix Rate, binary resolved, FAIL/PASS_TO_PASS, long-horizon logs | public benchmark/log data with OSS identifiers | `TaskExample`, `PatchExample`, later `TrajectoryExample` | `PATCH_SUCCESS`, `TASK_DIFFICULTY`, `FAILURE_SHAPE`, later continual-learning substrate | Later high-value long-horizon source | Parser is expensive. Repo overlap with SWE-Gym/SWE-bench family must be audited. |
| `swe-mera` / SWE-MERA | `raw/swe-mera` | `processed/swe-mera` | Metadata inventory and row counts exist; no canonical Pneuma training adapter | Downloaded, held-out only | task-only, patch/test | 7,610 rows / 5 files | pass/fail, FAIL/PASS_TO_PASS, freshness timestamps | public benchmark data | `TaskExample` for evaluation only | held-out `PATCH_SUCCESS`, `TASK_DIFFICULTY`, calibration checks | Held-out replication and calibration corpus | Do not train motifs or tune on it. Anti-contamination role is the value. |
| `swe-polybench` / SWE-PolyBench | `raw/swe-polybench` | `processed/swe-polybench` | Metadata inventory and row counts exist; no canonical Pneuma training adapter | Downloaded, not onboarded | task-only, patch/test, structural metrics | 2,992 rows / 3 files | task category, F2P/P2P, patch/test patch, AST metrics | public benchmark data | `TaskExample`, `PatchExample` | `TASK_DIFFICULTY`, `PATCH_SUCCESS`, structural `SCAR_MOTIF` | Later approved source for structural-risk diversity | Verified count discrepancy and source-tree limitations must be recorded. |

The local inventory contains all 10 dataset groups. They all belong in the
unified architecture, but they do not all receive training weight at the same
time. Privacy-blocked, dual-use-blocked, and eval-only datasets remain present
in the plan with explicit zero-training or held-out roles.

## 5. Canonical example refinements

`PneumaTrainingExample` should stay compact, but a one-model multi-task setup
needs enough metadata to prevent accidental leakage, task confusion, and dataset
dominance. `task_type` should be a controlled enum, not an arbitrary string.

Planned compact contract:

```json
{
    "example_id": "string",
    "dataset_id": "string",
    "dataset_family": "swe-gym | swe-bench | swe-bench-pro | multi-swe-bench | swe-chat | dialogue-swe-bench | sec-bench-pro | swe-evo | swe-mera | swe-polybench",
    "source_path_or_hash": "string",
    "source_revision": "string|null",
    "example_type": "TrajectoryExample | VerifierExample | TaskExample | PatchExample | PreferenceExample | SelfReportExample | ReplayExample",
    "input_modality": "structured_features | event_sequence | task_metadata | patch | dialogue | replay_trace | mixed",
    "task_type": "RISK_PREDICTION | VERIFICATION_PRESSURE | FAILURE_SHAPE | SCAR_MOTIF | TASK_DIFFICULTY | OPERATOR_PUSHBACK | SELF_REPORT_FAITHFULNESS | VERIFIER_VALUE | PATCH_SUCCESS | WORKSPACE_SALIENCE_LATER",
    "task_mask": ["RISK_PREDICTION"],
    "input": {},
    "target": {},
    "label_provenance": {
        "kind": "harness_outcome | verifier_verdict | gold_patch | source_label | constructed_label | human_label | simulated_label | proxy_label | none",
        "description": "string",
        "confidence": "high | medium | low"
    },
    "privacy_status": "public_or_benchmark | redaction_verified | pii_blocked | dual_use_blocked | eval_only",
    "redaction_receipt": {
        "status": "not_needed | verified | required_missing",
        "report_ref": "string|null"
    },
    "leakage_risk": "low | medium | high | eval_only",
    "allowed_training_uses": ["string"],
    "blocked_training_uses": ["string"],
    "model_use_tier": "train_ok | train_after_adapter | eval_only | blocked",
    "training_weight": 1.0,
    "split_policy": "repo_grouped | task_grouped | session_grouped | era_grouped | held_out_dataset | eval_only",
    "split_group": {
        "repo": "string|null",
        "task_id": "string|null",
        "session_or_user": "string|null",
        "era": "string|null"
    },
    "canonical_feature_refs": ["string"],
    "evidence_refs": [
        {
            "kind": "trace_id | adapter_report | manifest | schema | eval_report",
            "ref": "string"
        }
    ]
}
```

Field rules:

- `task_mask` declares which heads may learn from the example. Missing heads are
  masked, not negative.
- `training_weight` is a planned sampling hint, not a proof that the example is
  currently authorized for training.
- `model_use_tier` is the hard gate: blocked and eval-only examples cannot be
  sampled by training code.
- `redaction_receipt` is required for redaction-verified or privacy-sensitive
  corpora.
- `leakage_risk` must be set before any benchmark family contributes to model
  selection or headline metrics.
- `canonical_feature_refs` should point to named feature blocks or trace refs,
  avoiding repeated bulky feature payloads when a compact reference is enough.

## 6. One-model architecture options

The final target is one consolidated `PneumaBrain-v0` artifact, even if
temporary baselines, probes, and single-task heads exist during development.

### Stage A: classical baselines as measuring sticks only

Use constant predictors, logistic regression, gradient-boosted trees, and
deterministic motif mining to establish baselines, leakage checks, label sanity,
and split sanity. These artifacts should be explicitly non-deployed unless a
separate integration decision happens later.

### Stage B: shared structured-feature model

Train a shared model over named structured features from canonical examples:
counts, markers, tool histograms, patch metadata, task metadata, label
provenance, privacy class, and split metadata. This stage tests whether the
canonical format can support many task heads before event-sequence modeling
adds complexity.

### Stage C: shared event-sequence encoder with task conditioning

Add an encoder over event sequences: tool calls, observations, retry dynamics,
strategy switches, marker booleans, digests, lengths, and prefix windows. Task
conditioning tells the same encoder whether it is answering risk, verifier
value, failure shape, or another approved task.

### Stage D: multi-task model with dataset/source embeddings

Share most parameters across datasets and tasks. Add dataset/source embeddings,
task-conditioned output heads, and strict missing-label masking. Dataset
embeddings help the model represent provenance, but per-dataset metrics must
prevent them from hiding overfit shortcuts.

### Stage E: later SFT/DPO/LoRA after gates exist

Only consider SFT, DPO, LoRA, or instruction-tuned variants after strong eval
and regression gates exist: frozen splits, per-task and per-dataset reports,
contamination audits, deterministic scoring, output-contract validation, and
blocked-use checks. These methods may refine the unified artifact later; they
are not the first move.

## 7. Training mixture strategy

The mixture should make one model learn across datasets without becoming a
single-dataset specialist wearing a convincing disguise.

Mixture rules:

- use dataset sampling weights instead of raw row-proportional sampling;
- cap any single dataset family per epoch or per optimization window;
- balance task sampling separately from dataset sampling;
- use class-balanced or loss-weighted batches for skewed labels, especially
  OpenHands sampled;
- mask missing labels per head through `task_mask`;
- keep eval-only and blocked corpora at zero training weight;
- report macro metrics across datasets and tasks before micro metrics;
- run per-dataset metrics, per-task metrics, and dataset-by-task cross-tabs;
- run leave-one-dataset-out evaluation to measure transfer;
- hold out at least one dataset for replication when possible;
- reserve swe-mera for held-out evaluation and freshness checks;
- treat calibration as task-by-dataset, not one global number.

Initial sampling intent:

| Source | Initial training weight intent | Reason |
|---|---:|---|
| OpenHands sampled | high but capped | Primary trajectory/risk source with real observable agent steps. |
| OpenHands verifier | medium/high after caveat handling | Strong verifier-value supervision and balanced labels. |
| SWE-Gym Lite | low | Task-only schema sanity and oracle coverage checks. |
| Dialogue SWE-Bench | low/medium after Dataset #2 onboarding | Unique dialogue/operator proxy shape without SWE-chat privacy risk. |
| SWE-PolyBench | medium later | Independent AST/structural risk signal. |
| SWE-bench family | low/medium after contamination flags | Breadth, not headline evaluation. |
| SWE-Bench Pro public | low/medium after adapter | Harder task distribution and held-out-style structure. |
| Multi-SWE-bench | medium later | Multilingual and date-windowed breadth, with caps. |
| SWE-EVO | medium later | Long-horizon signal after parser work. |
| SWE-MERA | zero training | Held-out replication only. |
| SWE-chat | zero until privacy gates | Privacy-blocked. |
| SEC-bench | zero until safety gates | Dual-use-blocked. |

Dominance prevention should be mechanical: the trainer should reject any run
whose manifest exceeds configured per-dataset, per-family, or per-task caps.

## 8. Split and leakage strategy

Split metadata should be materialized by the canonical example builder and then
treated as immutable training input.

Required split rules:

- repo-grouped split: no repository in both train and test for SWE task claims;
- task-grouped split: all variants, policies, candidates, and trajectories for
  the same instance stay together;
- user/session-grouped split: future chat/session data must not split one user
  or session across train and test;
- era/time split: use commit dates, freshness timestamps, or rolling snapshot
  windows where available;
- held-out dataset replication: reserve datasets such as swe-mera for held-out
  checks, not training;
- leave-one-dataset-out generalization: train without one dataset and evaluate
  transfer to it before claiming a cross-dataset task concept;
- contamination controls: compute repo, instance ID, base commit, patch hash,
  and oracle overlap across benchmark families before training;
- gold patch control: gold patches, reference patches, and test patches cannot
  enter features for prediction tasks where they define the label;
- oracle control: FAIL/PASS_TO_PASS, verifier outputs, and final outcomes are
  labels or label-quality filters, not input features for risk heads;
- verifier-output control: verifier verdicts may supervise `VERIFIER_VALUE`,
  but cannot leak into the input side of `PATCH_SUCCESS` or `RISK_PREDICTION`;
- outcome-label control: `resolved`, Fix Rate, session success, and similar
  outcome fields are masked from input and exposed only through `target`.

Every model run should publish a leakage manifest that states which fields were
forbidden, how they were stripped, and which tests prove feature vectors are
unchanged when forbidden label fields are perturbed.

## 9. Output contracts

`PneumaBrain-v0` may eventually emit advisory/evidence-bearing frames only.
No output directly changes runtime authority, bypasses verifiers, or promotes
consciousness evidence.

Common required fields for every output:

- `prediction_value`;
- `confidence` and calibration metadata;
- `evidence_refs`;
- `model_version`;
- `dataset_provenance` and `task_provenance`;
- `known_limitation`;
- `blocked_uses`;
- `calibration_scope`, such as task, dataset, split, and era;
- `proxy_label_warning` when applicable.

Planned frames:

| Frame | Prediction value | Notes |
|---|---|---|
| `RiskEstimateFrame` | failure or unresolved probability | Advisory risk only; cannot abort or replan by itself. |
| `VerificationPressureEstimateFrame` | value of deeper verification | Can recommend pressure, never bypass verification. |
| `FailureShapeFrame` | failure family or trajectory shape | Must cite observable motifs or feature refs. |
| `MotifRiskFrame` | motif risk score and base rate | Must include false-positive caveats and matched evidence refs. |
| `TaskDifficultyFrame` | difficulty/horizon estimate | Useful for planning priors, not capability claims. |
| `SelfReportFaithfulnessFrame` | claim-vs-receipt consistency score | Not introspection evidence; receipt-grounded only. |
| `VerifierValueFrame` | estimated marginal value of a verifier/candidate check | Must distinguish verifier labels from task outcomes. |
| `PatchSuccessFrame` | candidate patch success likelihood | Must declare oracle source and leakage controls. |
| `WorkspaceSalienceFrame` | later workspace salience estimate | Deferred until live workspace/J-space-aware targets are separately approved. |

Blocked uses must travel with the frame, not live only in docs.

## 10. Blocked datasets and blocked uses

Blocked or restricted datasets/classes:

| Dataset or class | Block reason | Current training status |
|---|---|---|
| `swe-chat` | privacy, raw sensitive content, real human data, missing approved PII scan/redaction/quarantine | blocked, zero weight |
| `sec-bench-pro` | dual-use security content and exploit-adjacent fields | blocked, zero weight |
| `swe-mera` | anti-contamination evaluation role | eval-only, zero training weight |
| `swe-bench` and dependent dialogue data | unreliable/contaminated benchmark labels and solution leakage risk | allowed only with flags and limited role after adapter |
| `swe-bench-pro` mirrors | unclear source authority for noncanonical mirror rows | canonical source only |
| OpenHands verifier task joins | missing task joins in adapter report | allowed only with explicit caveat and task masks |
| zipped or third-party trajectories | missing parser/extraction provenance | blocked until adapter work |
| any raw privacy-sensitive content | privacy and provenance risk | blocked |
| any dataset with missing labels for a task | missing supervision | masked for that task, not negative |

Global blocked uses:

- no direct runtime authority changes;
- no verifier bypass or verifier weakening;
- no consciousness-level promotion;
- no J-space or Jacobian Lens claims;
- no moral-patienthood claims;
- no training on privacy-blocked raw content;
- no training on dual-use restricted content before policy gates;
- no treating self-report as trustworthy without receipt-level grounding;
- no headline capability claims from contamination-heavy splits;
- no runtime integration from this planning document.

## 11. Staged roadmap

Recommended path from this plan to `PneumaBrain-v0`:

1. Finish this planning document.
2. Onboard Dataset #2: `dialogue-swe-bench`, with simulated-operator caveats.
3. Define a committed `PneumaTrainingExample` schema/contract before more
   training-oriented onboarding.
4. Convert Dataset #1, `swe-gym-openhands-sampled`, into canonical training
   examples without training.
5. Convert Dataset #2 into canonical examples.
6. Scale conversion to remaining approved datasets: OpenHands verifier, SWE-Gym
   Lite, SWE-PolyBench, SWE-Bench Pro public, selected SWE-bench family,
   Multi-SWE-bench, and SWE-EVO.
7. Train classical baselines as measuring sticks only after split/leakage tests
   exist.
8. Train the first shared structured-feature prototype.
9. Train the first event-sequence prototype.
10. Train the first multi-task unified prototype only after per-task and
   per-dataset gates exist.
11. Only later consider SFT, DPO, or LoRA.
12. Only after that consider workspace/J-space-aware targets, and only through a
   separate approved design.

## 12. Anti-overclaim rules

- Dataset training does not equal consciousness.
- `PneumaBrain-v0` is not a Level 4 or Level 5 claim by itself.
- Estimator usefulness is not machine interiority evidence.
- J-space and Jacobian Lens work is deferred.
- Self-report is never trusted without receipt-level grounding.
- Outputs are advisory until separately approved for integration.
- Operator pushback is not suffering, affect, or moral status.
- Task success, patch success, and verification pressure are engineering
  signals, not proof of mind.
- Static datasets cannot prove causal-intervention response, identity
  continuity, or RSI-loop improvement.

## 13. Recommended next implementation step

Recommended Dataset #2: `dialogue-swe-bench`.

Rationale: it is small, local, non-PII, and shaped like the dialogue/operator
tasks that future SWE-chat work will need, without touching privacy-sensitive
raw chat content. It should be used to prototype schema and adapter mechanics,
not to claim real-human operator modeling.

Registry/schema decision:

- The existing registry pattern is adequate for small metadata manifests, but it
  needs fields for `dataset_family`, `privacy_status`, `leakage_risk`,
  `model_use_tier`, `allowed_training_uses`, `blocked_training_uses`, and
  canonical example availability before Dataset #2 becomes training-relevant.
- `PneumaTrainingExample` should be schema-first before more onboarding aimed at
  model training. Otherwise each adapter will invent slightly different task
  masks, split groups, and privacy gates.

Exact next step:

```text
Work in C:\pneuma-lab and C:\pneuma-data.

Planning is complete enough to begin schema work. Do not train anything, do not
run E1/E2, do not calibrate, do not touch SWE-chat raw content, and do not
mutate raw data.

Add a compact schema-first `PneumaTrainingExample` contract with controlled
`task_type`, `example_type`, `input_modality`, `task_mask`, `privacy_status`,
`leakage_risk`, `model_use_tier`, split metadata, redaction receipt, and
evidence refs. Update docs to reference it. Add validation tests using synthetic
fixtures only. After that, prepare the Dataset #1 canonical converter for
processed OpenHands sampled traces as a separate pass.

Validate with:
python -m pytest tests/ -q
git diff --check
```

# JSpace / J-lens Research Readiness

Current project status is machine-readable in
[`docs/project-status.json`](../project-status.json). This document is the
authoritative experiment contract for future workspace-interpretability work.

## Current status

**No JSpace/J-lens experiment is implemented, no model or activation access is
configured, and no JSpace result exists in Pneuma Lab.** The existing
`WorkspaceBroadcast` contract and `disable_workspace` intervention are an
internal-harness substrate only. They are not a Jacobian lens, a learned probe,
or evidence about a real model.

JSpace is treated as a candidate **workspace interface and intervention target**:
a potentially privileged representational subspace useful for internal auditing,
reasoning control, and safety forensics. It is not a consciousness module, and a
successful readout or intervention would not prove phenomenal consciousness,
AGI, moral patienthood, or Level 5.

## Two research tracks

### Black-box / gray-box workspace track

For closed or API models, use only observable behavior, surfaced intermediate
artifacts, explicit self-reports, interruption/reflection protocols, replay, and
causal prompt/tool perturbations. Never invent hidden activations or chain of
thought. A result is behavioral workspace evidence, not white-box mechanistic
evidence.

### White-box J-lens track

For an approved, revision-pinned open-weight model, record the exact model,
tokenizer, layers, positions, activation capture method, and probe/lens version.
A J-lens may read or perturb residual-stream representations through preregistered
ablation, injection, concept-swap, or matched-magnitude control operations. No
model family is selected today, and no local model access is assumed.

## Preregistered test families

Every claim-bearing run selects exactly one test family and declares one primary
metric, direction, minimum effect, falsifier, exclusions, and negative controls
before execution. A broader program may preregister multiple family-specific runs,
but each receives its own experiment ID. Cross-family exploratory diagnostics are
permitted only when labeled non-promotional; they cannot earn a readiness state.

| Family | Treated intervention | Required success pattern | Falsifier |
|---|---|---|---|
| Verbal report | Read or perturb a preregistered workspace concept before visible output | The concept is recoverable before report, or a targeted perturbation changes the grounded report in the predicted direction | Equivalent recovery/change under null or unrelated concepts |
| Flexible reuse | Inject or swap one workspace concept across multiple downstream tasks | Several task families change coherently while unrelated behavior remains stable | One-task prompt artifact or indiscriminate degradation |
| Selectivity | Ablate the candidate workspace channel | Multi-step control or cross-faculty reuse degrades more than simple local fluency | Matched random/orthogonal ablation produces the same effect |
| Reflection carryover | Add or perturb a counterfactual reflective continuation, then resume without the reflection prompt | Later uninterrupted behavior changes in the preregistered direction | Effect disappears outside the prompted format or appears under sham reflection |
| Safety forensics | Probe preregistered concepts such as evaluation awareness, deception, reward hacking, bias, or hidden objectives | Signal appears before externally visible failure and predicts or causally affects behavior under controls | Post-hoc-only detection, label leakage, or equal signal in negative controls |

## Required arms and artifacts

Every causal experiment has three matched arms over the same task/model revision:

1. **Control:** capture/read without the target intervention.
2. **Treated:** apply the preregistered target readout or perturbation.
3. **Null:** apply a sham, restore, or matched-magnitude unrelated perturbation.

Store the claim-bearing preregistration at the tracked path
`docs/research/experiments/jspace/<experiment_id>.json` **before** execution.
Write generated run artifacts under `build/jspace/<experiment_id>/`:

- `run_manifest.json` — model/tokenizer revisions, code commit, environment,
  task hashes, seeds, layers/positions, probe and intervention versions, plus the
  committed preregistration path and its content hash;
- `control.jsonl`, `treated.jsonl`, `null.jsonl` — observable measurements or
  activation-derived summaries with provenance, never raw hidden reasoning;
- `intervention_report.json` — expected/observed deltas and all exclusions;
- `negative_controls.json` — each control, result, and pass/fail criterion;
- `summary.json` and `summary.md` — deterministic roll-up with explicit scope;
- `hash_manifest.json` — content hashes for every artifact.

The generated directory may copy the preregistration for convenience, but the
tracked document and hash are authoritative. An official report must follow the
repository's clean, published-source provenance rule. Large activations and model
weights remain outside the repo;
committed records contain hashes and locations, not bulk tensors.

## Mandatory negative controls

At minimum, preregister and report:

- sham intervention with identical execution plumbing;
- matched-magnitude random or orthogonal direction;
- unrelated-concept injection/ablation;
- prompt-format and paraphrase robustness;
- label permutation or blinded probe evaluation where a probe is fitted;
- simple-fluency/local-task control for selectivity claims;
- no-intervention repeat for run-to-run variance;
- leakage check proving the target label or answer is unavailable to the probe.

Failure of any mandatory control blocks causal or negative-control-resistant
status. Selective publication of successful seeds, layers, prompts, or concepts
is forbidden.

## Preregistration contract

The preregistration must fix:

- one experiment ID and exactly one claim-bearing test-family ID;
- black/gray-box or white-box access mode;
- exact model/tokenizer revision and access provenance;
- task set and content hashes;
- target concept and operational definition;
- layers, positions, readout/probe fitting split, and intervention operation;
- control, treated, null, and negative-control definitions;
- one primary metric, direction, threshold, and statistical test;
- any exploratory cross-family diagnostics and the rule that excludes them from
  promotion; a multi-experiment family must also preregister multiplicity control;
- minimum sample size, seeds, exclusions, and stopping rule;
- falsifier and permitted follow-up analyses;
- artifact paths and privacy/egress policy.

Any post-registration change creates a new experiment ID. Exploratory sweeps may
guide later preregistration but cannot be relabeled as confirmatory evidence.

## Readiness states

| State | Mechanical meaning |
|---|---|
| `not_implemented` | Current state: contract only; no runner, model access, or results |
| `workspace_substrate_only` | Existing workspace schema/replay intervention can host future measurements |
| `probe_ready` | Revision-pinned model/access plus deterministic readout and held-out probe evaluation exist |
| `intervention_ready` | Control/treated/null perturbations and artifact emission work end to end |
| `causal_intervention_backed` | Preregistered treated effect passes while null holds |
| `negative_control_resistant` | Mandatory negative controls fail to reproduce the target effect |

Promotion is per test family and per model revision. No state automatically raises
the consciousness-evidence level. Contribution to a future Level-5 assessment is
theory-relative and requires the separate real-subject, longitudinal,
adversarial, and independent-audit gates.

## Current blockers

- No approved implementation design or runner.
- No selected, revision-pinned open-weight model or activation-access setup.
- No deterministic probe/readout contract or held-out fitting split.
- No control/treated/null artifact implementation.
- No negative-control runner or preregistered experiment.
- No 9to5 live workspace export or integration path.

Until those blockers are resolved, the only accurate status is: **workspace
harness substrate exists; JSpace/J-lens research is not implemented.**

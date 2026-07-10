# Open-SWE-Traces to PneumaTrace / PneumaTrainingExample Plan

Status: **IMPLEMENTED (stage 1 + stage 2).** The two-stage pipeline this doc
designed now exists: `src/pneuma_lab/adapters/open_swe_traces.py` reads real
parquet `trajectory` rows into digest-only `PneumaTrace` envelopes, and
`src/pneuma_lab/converters/open_swe_traces_training.py` converts those into
`PneumaTrainingExample` records. Bounded real-row conversion and a bounded
repo-grouped split have been run into ignored `build/`. Full-corpus conversion
is gated (available, not run). See
`docs/data/training-readiness/open-swe-traces.md` for the readiness package.
Sections 3.2 and 9 below describe the original fixture-first scaffolding and are
retained as design history. This work still does not train models, run E1/E2,
calibrate, change runtime behavior, process SWE-chat, implement J-space work,
mutate raw/processed data, write to `C:/pneuma-data`, or make
consciousness-level claims.

> Update: `resolved` is an int32 tri-state (`-1 / 0 / 1`); `1 -> True`,
> `0 -> False`, and `-1` (~21% of rows, unknown/unevaluated) is **skipped**,
> never coerced. The world-frame objective is digest-only (no raw task text),
> stricter than Dataset #1. Raw `repo`/`instance_id`/`trajectory_id` never
> enter frames or labels; only `provenance.source_id` keeps the raw join key.

## 1. Purpose

Open-SWE-Traces is trajectory-shaped (`trajectory`, `tool_calls`, `tools`) and
carries a dense `resolved` outcome on every row, so it is expected to graduate
through the same two-stage pipeline `swe-gym-openhands-sampled` uses:

1. an adapter that turns one raw trajectory row into one trajectory-bearing
   `PneumaTrace` envelope (analogous to
   `src/pneuma_lab/adapters/openhands_sampled.py`), observable-only, with raw
   patch/tool/trajectory text digested rather than embedded;
2. a converter that turns processed `PneumaTrace` records into canonical
   `PneumaTrainingExample` records (analogous to
   `src/pneuma_lab/converters/openhands_sampled_training.py`).

This pass does not implement stage 1 against real parquet content (no
`trajectory`, `tools`, or `metadata.reference_patch`/`metadata.model_patch`
row has been opened). Instead it short-circuits directly from a committed
synthetic fixture to a fixture-only `PneumaTrainingExample`-shaped record, the
same pattern `src/pneuma_lab/converters/dialogue_swe_bench_training.py` uses
for Dataset #2's archived predecessor. The synthetic fields it consumes
(`source_group`, `language`, `resolved`, digested identifiers, trajectory/tool
_count_ summaries) are chosen to be the same safe scalar surface a future
stage-1 `PneumaTrace` adapter would also expose, so the fixture-only converter
does not have to be thrown away once stage 1 exists -- it becomes the stage-2
converter, fed from real `PneumaTrace` records instead of the fixture.

## 2. Source Dataset

Source registry: `docs/data/registry/open-swe-traces.json`

Onboarding doc: `docs/data/onboarding/open-swe-traces.md`

Candidate review: `docs/data/candidate-reviews/open-swe-traces.md`

Source of truth report: `C:/pneuma-data/processed/open-swe-traces/row_counts.json`

| Field                        |                                                           Value |
| ---------------------------- | --------------------------------------------------------------: |
| Dataset ID                   |                                               `open-swe-traces` |
| Dataset family (schema enum) |                                               `open-swe-traces` |
| Hugging Face repo            |                                        `nvidia/Open-SWE-Traces` |
| Hugging Face revision        |                      `474d016b4a35a0411a7f57183579eab8924e9ea5` |
| Declared license             |           `cc-by-4.0` (HF `cardData.license`, structured field) |
| Total rows                   |                                                         207,489 |
| Resolved true / false        |                                                112,002 / 95,487 |
| Languages                    | 9 (python, go, typescript, javascript, rust, java, php, c, cpp) |

### Source groups

Four source groups, each a distinct model x harness combination:

| `source_group`                       |   Rows | Model                            | Harness   |
| ------------------------------------ | -----: | -------------------------------- | --------- |
| `minimax_m25_openhands_trajectories` | 49,948 | Minimax-M2.5 (thinking mode)     | OpenHands |
| `minimax_m25_sweagent_trajectories`  | 57,268 | Minimax-M2.5 (thinking mode)     | SWE-agent |
| `qwen35_openhands_trajectories`      | 55,488 | Qwen3.5-122B-A10B (non-thinking) | OpenHands |
| `qwen35_sweagent_trajectories`       | 44,785 | Qwen3.5-122B-A10B (non-thinking) | SWE-agent |

Two harness-specific tool-definition sidecars exist as separate JSON files
(`openhands_tools.json`, `sweagent_tools.json`); these were never opened for
content and remain blocked (see governance module, section 5).

## 3. Intended Normalized Shape

### 3.1 Future stage-1 `PneumaTrace` envelope (not implemented this pass)

Modeled on `openhands_sampled.py::build_trace`:

- `world` frame: task text digest (never raw text by default), repo identity
  (digested; per-row `license` field preserved, not assumed uniform).
- `governance` frame: minimal synthetic contract, same as other adapters.
- `agent-trace` frames: one per assistant step, observable-only counts and
  digests, extracted only once `trajectory`/`tool_calls` rows are actually
  read by a future pass (`adapters.trajectory` extraction rules).
- `outcome` block: `{"resolved": bool}` plus a `reference_patch`/`model_patch`
  divergence digest (sha256 + length only, never patch text), source group,
  and per-row `license`.
- `labels` block: `source_group`, `language`, `resolved`, `has_trajectory`.

### 3.2 Current stage: fixture-only `PneumaTrainingExample` (this pass)

Implemented in `src/pneuma_lab/adapters/open_swe_traces.py`. Consumes
synthetic fixture dictionaries shaped like the safe scalar surface above:

```json
{
    "dataset": {
        "dataset_id": "open-swe-traces",
        "dataset_family": "open-swe-traces",
        "source_group": "minimax_m25_openhands_trajectories",
        "hf_revision": "474d016b4a35a0411a7f57183579eab8924e9ea5"
    },
    "source": {
        "instance_id_digest": "sha256:...",
        "repo_digest": "sha256:...",
        "trajectory_id_digest": "sha256:...",
        "license": "MIT"
    },
    "language": "python",
    "resolved": true,
    "trajectory_summary": { "num_messages": 0, "num_agent_steps": 0 },
    "tool_summary": { "tool_call_count": 0, "tool_counts": {} }
}
```

and emits one `TrajectoryExample` for `RISK_PREDICTION`, `model_use_tier:
train_after_adapter`, `training_weight: 0.0`.

## 4. Safe Scalar Fields (allowed input surface)

- `dataset.dataset_id`, `dataset.dataset_family`, `dataset.source_group`,
  `dataset.hf_revision`
- `language`
- `source.instance_id_digest`, `source.repo_digest`,
  `source.trajectory_id_digest` (digested/fake identifiers only, never the
  real `instance_id`/`repo`/`trajectory_id` strings)
- `source.license` (per-row source-repo license; preserved, not assumed
  uniform across the dataset)
- `trajectory_summary.num_messages`, `trajectory_summary.num_agent_steps`
- `tool_summary.tool_call_count`, `tool_summary.tool_counts.*`
- `feature_refs.*` (converter version pins)

## 5. Blocked Raw Fields

Enforced by `src/pneuma_lab/governance/open_swe_traces.py`:

- `trajectory` (list of `{role, content, reasoning_content, think,
tool_calls}`) -- raw agent transcript content
- `tool_calls`, `tools` -- raw tool-use payloads and tool-definition JSON
  (`openhands_tools.json`, `sweagent_tools.json`)
- `metadata.reference_patch.patch`, `metadata.model_patch.patch` -- raw gold
  and model patch text
- `metadata.category` and any other `metadata.*` sub-field not explicitly
  reviewed above -- the `metadata` struct was never opened for content during
  onboarding, so it is blocked wholesale by default until a future pass
  reviews it field-by-field
- `resolved` -- the label; it is a training target, never an input feature
- oracle/test lists (`FAIL_TO_PASS`, `PASS_TO_PASS`, or any future
  equivalent) -- none are currently known in this dataset's schema, but the
  token block is kept defensively in case a future adapter pass surfaces one
- `instance_id`, `repo`, `trajectory_id` in raw (non-digested) form
- `git_repo`/HF snapshot fields belong in provenance/evidence blocks only,
  never in `input`

## 6. Future `PneumaTrace` / `PneumaTrainingExample` Mapping

Per `docs/data/onboarding/open-swe-traces.md` section "Likely Task Types",
in rough implementation order:

1. `RISK_PREDICTION` (this pass, fixture-only) -- target `{"resolved": bool}`.
2. `FAILURE_SHAPE` -- after a safe label taxonomy over trajectory shape
   exists.
3. `SCAR_MOTIF` -- after motif extraction exists (mirrors
   `openhands_sampled` future work).
4. `PATCH_SUCCESS` -- alias/refinement of resolved-based risk once patch
   divergence features exist.
5. `VERIFIER_VALUE` -- via `reference_patch` vs `model_patch` divergence
   digest only (never patch text); requires stage-1 adapter to compute the
   divergence digest so `input` never touches patch text directly.

Explicit non-mappings (same reasoning as `openhands_sampled`):

- no `OPERATOR_PUSHBACK`, `SELF_REPORT_FAITHFULNESS`, or
  `WORKSPACE_SALIENCE_LATER` -- this corpus has no operator dialogue or
  live workspace/J-space targets.
- no `PreferenceExample` -- no pairwise preference label is present.

## 7. Label Provenance Rules

- `label_provenance.kind` must be `constructed_label` or `simulated_label`
  for every field derived from this dataset. It must never be
  `harness_outcome`, even for the `resolved` field, because:
    - the trajectories themselves are synthetic (generated by Minimax-M2.5 and
      Qwen3.5-122B-A10B, not human engineers or a live 9to5 harness run), and
    - `resolved` is itself a verifier-style automated outcome computed by the
      dataset's own release pipeline over those synthetic trajectories, not a
      human-graded judgment and not a Pneuma/9to5 harness result.
- `label_provenance.confidence` must be `medium` or lower for `resolved`
  derived targets, per the candidate review's caveat that the verifier
  methodology behind `resolved` has not been independently reviewed.
- This pass uses `kind: "constructed_label"` (an automated verifier
  constructed the label from execution) with `confidence: "medium"`.

## 8. Contamination / Leakage Risks

- SWE-rebench-V2 lineage carries the same SWE-bench-family contamination and
  benchmark-leakage risk class already tracked for `swe-gym-openhands-sampled`
  and archived `dialogue-swe-bench`.
- A cross-dataset leakage registry is needed before any joint training use:
  repos already present in Dataset #1's (`swe-gym-openhands-sampled`)
  repo-grouped splits must be checked against Open-SWE-Traces repos before
  they can share a split policy or a training run.
- Per-row `license` should be checked, not assumed uniform, once real rows
  are read (the upstream statements were filtered to permissive source
  licenses -- MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause -- but this has not
  been independently re-verified row-by-row).
- Third-party model output ToS: NVIDIA's CC BY 4.0 grant covers the released
  dataset artifact as redistributed, but Minimax's and Qwen's own terms of
  service regarding training on their model outputs have not been
  independently verified. This does not block metadata onboarding or
  fixture-only scaffolding, but it must be re-checked before any real
  training authorization (tracked in the governance module as
  `MINIMAX_QWEN_TOS_CAVEAT`).

## 9. Future Bounded Conversion Gates

Before any bounded real-row conversion (mirroring
`src/pneuma_lab/training/dialogue_governance.py`'s gate discipline):

1. A stage-1 `PneumaTrace` adapter must exist and pass fixture tests
   (analogous to `openhands_sampled.py` + its golden fixture).
2. The stage-2 converter in this doc must validate real `PneumaTrace` input
   instead of the synthetic fixture, with the same schema/leakage checks.
3. A cross-dataset leakage check against Dataset #1's repo-grouped splits
   must exist and pass (see section 8).
4. The Minimax/Qwen output-ToS caveat must be explicitly resolved or
   explicitly accepted with a tracked human sign-off before
   `training_authorization` can move off `not_authorized`.
5. Bounded conversion, when implemented, must cap real rows the same way
   `MAX_BOUNDED_REAL_ROWS` does for Dataset #2, must write only to an
   approved repo-local `build/` root, and must never write to
   `C:/pneuma-data`.
6. `model_use_tier` remains `train_after_adapter` (or `blocked`, if the ToS
   caveat is not resolved by the time bounded conversion is attempted) and
   `training_weight` remains `0.0` through all of the above.

## 10. Non-Goals

- No ML training.
- No estimator fitting.
- No E1/E2 execution.
- No calibration.
- No runtime integration.
- No J-space or Jacobian Lens work.
- No SWE-chat processing.
- No raw trajectory/patch/tool content reading in this pass.
- No raw or processed data mutation; no writes to `C:/pneuma-data`.
- No bounded or full real-row conversion in this pass.
- No consciousness, interiority, sentience, Level 4/5, or moral-patienthood
  claims.

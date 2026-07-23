# NeurIPS 2026 Execution and Discovery Phase Design

**Status:** approved architecture for implementation planning

**Branch:** `codex/neurips-2026-empirical`

**Date:** 2026-07-22

## 1. Goal and success criteria

The execution/discovery phase must produce an honest empirical answer to one
question: does persistent, causally active internal state reduce repeated
software-agent harm after a standardized prior failure, and by how much?

The phase succeeds when it produces one of three immutable outcomes:

1. a powered selected-tier confirmatory result with a positive, practically
   refuted, or inconclusive decision;
2. a feasibility no-go proving that neither the core nor identification-floor
   study fits inside the fixed confirmation roster; or
3. a pipeline-invalid result that identifies which preregistered validity gate
   failed without converting the failure into missing data or a post-hoc repair.

The first real result is an additive, disjoint discovery result. It is a
descriptive pipeline de-risk and is never used to decide whether confirmation
runs. The paper's claim of record comes only from the untouched confirmation
roster after the nuisance pilot selects the powered tier.

## 2. Invariants and non-goals

- Pneuma remains standalone and imports no 9to5 runtime code or private state.
- The behaviour path, notice path, report path, and arm-blind evaluator remain
  structurally separated. Prose and self-report never award behavioural points.
- The frozen subject receives no weight training. `training_weight` remains
  `0.0` unless a separate hash-bound authorization explicitly changes it.
- `C:\pneuma-data` remains read-only. Generated artifacts live under ignored,
  receipt-bound `build/research/` roots until a reviewed publication artifact is
  intentionally promoted.
- Determinism is claimed only for pure fixtures, generators, or explicitly
  deterministic controller operations. Stochastic model behaviour is analyzed
  through registered assignments and repeated draws.
- Branch-local refusal, timeout, premature finish, budget exhaustion, invalid
  action, model/runtime failure, OOM, disk exhaustion, or sandbox corruption is
  adverse. Only a proved arm-common exogenous outage may remove a whole block.
- A negative or null effect is a valid result. No efficacy value may alter the
  tier, continuation decision, endpoint, motif roster, scalar winner, or
  confirmatory analysis.
- No RunPod action, pod creation, paid image pull, or paid model call occurs
  without the explicit approval gate in section 9.

## 3. Pre-pilot protocol amendment

Before any nuisance-pilot data are opened, one decision-log entry must record
all four linked decisions and their consequences:

1. adopt I1, I2, I3, I5, and I7 as the approved core revision; size I4 in the
   pilot, retain I6 as a diagnostic, use I8 as the H3 falsifier/demotion rule,
   and keep I9 discovery-only;
2. replace the undefined fallback with the monotone core → floor → no-go rule;
3. require an additive discovery band whose effect cannot gate confirmation;
4. require a digest-sealed nuisance kernel and a mutually disjoint seed-band
   ledger.

The same edit reconciles documents 00–20. In particular, it replaces document
16 section 4.1's incompatible “no automatic fallback” statement and updates the
document 20/A11 boundary. The fallback is not automatic outcome selection: it
is a pre-pilot rule driven only by the blinded nuisance projection and locked
joint-power calculation.

The amendment must say explicitly that the floor drops Retrieval and the
strongest scalar condition. It therefore forfeits the “not a renamed counter”
falsifier and supports only the narrower claim that persistent causally active
state differs from no persistent state under the tested implementation. That
limitation is part of the preregistered claim, not a post-result footnote.

All demoted arms and endpoints remain registered secondary. They are never
deleted from the artifact registry merely because the selected tier omits them.

## 4. Gate-first execution architecture

### 4.1 Baseline Integrity Gate

Review and narrowly commit the accelerated test policy currently present in
`pyproject.toml`, `tests/conftest.py`, and `CLAUDE.md`. The default command is the
fast NeurIPS-critical-path suite; foundation tests remain a separate milestone
gate, and the real Qwen smoke remains opt-in.

The existing baseline launcher in `scripts/research/capture_baseline.py` and its
tests remain the trust root. The renamed Baseline Integrity Gate replaces the
ambiguous shorthand “G0” in execution-facing documents so it cannot be confused
with the powered lineage count $G^\star$.

### 4.2 Build the confirmation-grade nuisance kernel

Build only the code that contributes to nuisance estimation, tier power, the
first result, or the causal identification floor. Every element is implemented
to confirmation specification before the nuisance pilot:

- Suite-A injector, exact deterministic oracle, highest-lineage registry, fixed
  opportunity schedule, nested challenges, and sandbox snapshots;
- Base, Retrieval, the four-family scalar grid, Pneuma, InfluenceOff, and the
  registered randomized clamp schedule;
- fixed-denominator `repeat_harm`, utility gates, adverse-event finalization,
  complete-block rules, and immutable outcome bindings;
- common-prefix cloning, live descendant execution, assignment, metering,
  immutable traces, sandbox, seed, model, prompt, tool, and environment binding;
- nuisance-only projection and separate core/floor complete-conjunction power
  specifications.

Notice, H3 reporting, Reflection, Retry-count, H4, Suite B-live execution, and
non-load-bearing innovation diagnostics do not block the nuisance pilot. They
remain registered secondary and are implemented after the selected-tier result.

### 4.3 Throwaway validity band

Run the injector, oracle, endpoint, and causal-contrast path on a generator-
minted throwaway seed band. This gate checks:

- byte stability where determinism is claimed;
- oracle/injector agreement and metamorphic validity;
- fixed-denominator endpoint totality under success, recurrence, new-family
  failure, refusal, timeout, missing slot, and whole-block outage;
- valid assignment and a computable Pneuma/InfluenceOff or clamp contrast; and
- event rates inside a broad, preregistered bug-detection envelope.

The event-rate envelope detects broken injectors, dead oracles, or impossible
tasks. It cannot tune the DGP, power assumptions, motifs, thresholds, tier, or
endpoints. Implementation repairs are allowed only before scalar selection and
must cause the throwaway band to be regenerated.

### 4.4 Scalar and Pneuma selection band

Use a second generator-minted band, disjoint by highest lineage and seed, for
matched controller development. It is the only efficacy-bearing development
source allowed to choose scalar and Pneuma constants.

Selection uses highest-lineage-blocked nested cross-validation:

- inside each outer fold, inner folds search the complete last-failure-bit,
  count, EWMA, and Beta-posterior scalar grids plus the preregistered Pneuma
  grid; the chosen inner-fold configurations are evaluated only on that
  outer-held-out fold;
- the scalar receives at least the same attempted configurations, episodes,
  candidate selections, and model-call budget as Pneuma;
- aggregate outer-held-out predictions estimate fixed-denominator harm reduction
  and utility out of fold for each controller family;
- the frozen objective first requires validity/parity and utility gates, then
  minimizes equal-weight out-of-fold `repeat_harm` and selects the scalar
  family; and
- the final family configuration is the most frequently selected inner-fold
  winner across outer folds, with ties resolved by median inner-validation
  rank and then canonical configuration digest. The identical rule freezes the
  Pneuma artifact without consulting pilot, discovery, confirmation, notice,
  H3, or Suite B outcomes.

The append-only trial ledger includes failed configurations and binds folds,
seeds, budgets, objectives, tie rules, source digests, and selected artifacts.
Once selection begins, a code or contract repair invalidates the selection run
and requires a fresh disjoint selection band. Confirmation reports the selected
scalar's harm reduction beside Pneuma's so the falsifier's realized strength is
visible.

### 4.5 Seal the nuisance-load-bearing manifest

After throwaway validation and controller selection, seal one canonical
manifest containing hashes for:

1. Suite-A injector, oracle, motif and lineage registries, nested schedule, and
   sandbox builder;
2. Base, Retrieval, selected scalar, Pneuma, InfluenceOff, clamp schedule, and
   shared candidate/decision machinery;
3. endpoint, utility, adverse-event, complete-block, and outage logic;
4. nuisance projector, core/floor power rules, inference code, numerical
   dependencies, and analysis seeds;
5. checkpoint, quantization, backend, prompts, tools, caps, RNG derivation,
   environment lock, and source commit; and
6. every development receipt and selected-controller artifact.

The manifest also owns an enumerated seed-band ledger for throwaway,
scalar-selection, 30-lineage pilot, additive discovery, frozen 96-sequence
confirmation, and B-live. Each entry binds its generator version, allowed seed
support, highest-lineage digests, purpose, and forbidden consumers. Validation
proves pairwise disjointness and asserts that throwaway, selection, pilot, and
discovery instances are newly minted rather than carved from the 96-sequence
confirmation roster.

### 4.6 Thirty-lineage nuisance pilot and power decision

The pilot instantiates the complete five-arm core: Base, Retrieval, selected
scalar, Pneuma, and InfluenceOff plus its clamp schedule. Reflection, Retry,
notice, and H3 are absent.

The projector exposes de-identified per-condition event rates and the within-
lineage cross-condition covariance, variance, and ICC structure required for
paired power. It also exposes detector/oracle error, attrition, runtime, and
resource nuisance quantities. It masks condition identities, mean contrasts,
efficacy ordering, and treatment-effect sign.

Run the locked joint-power simulator at `Delta_power = 0.10`, true utility
differences zero, frozen non-inferiority margins, and at least 80% probability
that the applicable complete conjunction passes. The deterministic decision is:

- **Core:** Base, Retrieval, selected scalar, Pneuma, and InfluenceOff/clamp if
  the core conjunction fits inside the frozen 96-sequence roster;
- **Floor:** Base, Pneuma, and InfluenceOff/clamp if core is infeasible but the
  floor conjunction fits; or
- **No-go:** neither conjunction fits. Do not execute confirmation. Publish the
  feasibility boundary or amend and preregister a new study before collecting
  new confirmatory outcomes.

For tier `T`, define
`G_T* = min{G: Pr(all registered components for T pass) >= 0.80}`. The core
conjunction contains Pneuma's repeat-harm superiority over Base, Retrieval, and
the selected scalar, every registered utility/non-inferiority gate, and the
InfluenceOff plus randomized-clamp identification components. The floor
conjunction contains Pneuma's repeat-harm superiority over Base, the same
utility gates, and the same identification components. Select core when
`G_core*` fits the frozen roster; otherwise select floor when `G_floor*` fits;
otherwise emit no-go. Notice, H3, Reflection, Retry-count, and H4 never enter
either tier's power event.

The selected tier is a hash-bound consequence of the pilot nuisance receipt and
power-rule digest. It cannot be overridden manually.

### 4.7 Additive discovery result

Mint new Suite-A lineages on the ledger's discovery band. The discovery roster
is additive and disjoint from the pilot and confirmation; it never reduces the
96-sequence confirmation capacity.

Before execution, recompute every kernel and environment digest and require
exact equality with the sealed manifest. A mismatch is a fail-closed no-run.
Execute the selected tier without changes and generate an immutable descriptive
effect bundle.

The continuation gate reads pipeline validity only: digest equality,
deterministic claims, assignment integrity, complete endpoint production,
valid causal contrast, adverse/missingness handling, and nuisance values inside
the registered operating envelope. Positive, null, and negative discovery
effects are equally forbidden from the continuation decision. A valid negative
discovery result does not stop confirmation; an invalid pipeline does.

### 4.8 Selected-tier confirmation

Before any confirmation model call, perform the same complete manifest and
environment digest-equality preflight used for discovery. Any mismatch requires
a documented amendment, new freeze, and validity review; it cannot trigger an
automatic rebuild against the same roster.

Execute the selected tier on the untouched 96-sequence confirmation registry.
There is no efficacy-based optional stopping. Analysis consumes immutable,
pseudonymous outcomes and produces distinct finite-roster and assumption-bound
superpopulation outputs. InfluenceOff and clamp evidence remain mandatory at
both executable tiers because they identify the causal state-to-action effect.

### 4.9 Secondary expansion and full study

After the selected-tier result is immutable, implement and execute registered
secondary work without changing the confirmatory claim:

- full seven-arm comparisons, notice, H3/H4, Reflection, Retry-count, and
  resource-frontier diagnostics;
- I2 cross-motif specificity, I3 state interchange, I5 instrumental noticing,
  I6 candidate-bottleneck diagnostics, pilot-feasible I4 retention, I8 H3
  invariance/demotion evidence, and the I9 discovery-only carrier swap;
- Suite B-offline validation and the governed 36-sequence B-live known-motif
  repository transfer study; and
- paper, figures, model/dataset cards, cost ledger, and reproducibility bundle.

I1 is represented by the scalar-versus-Pneuma causal state-complexity frontier;
I7 is mandatory for the selected-tier finite-roster and superpopulation
reporting. Secondary results can strengthen, narrow, or fail independently, but
cannot rescue or rewrite the selected-tier decision.

## 5. Reuse and build boundaries

### Reuse without importing legacy claims

- `scripts/research/capture_baseline.py` and
  `tests/research/test_capture_baseline.py` provide the baseline-integrity
  launcher and evidence format.
- `src/pneuma_lab/replay/` supplies deterministic fixture replay and trace
  bridging. It remains an instrumentation path, not the live stochastic agent.
- `src/pneuma_lab/interventions/runner.py`, `operations.py`, `schedule.py`, and
  `provenance.py` supply paired-intervention and receipt primitives. The live
  experiment layer extends these primitives rather than changing their archived
  internal-harness claim boundary.
- `src/pneuma_lab/adapters/trajectory.py`, `envelope.py`, and the governed
  Open-SWE/OpenHands/SWE-Gym adapters supply typed trajectory extraction and
  offline validation inputs.
- `src/pneuma_lab/foundation/memory.py` may supply storage mechanics only; it
  does not authorize training or import a foundation-model result.
- `src/pneuma_lab/schemas/`, `training/`, and `status.py` supply schema,
  authorization, leakage, and canonical-status patterns.

### Build as the new empirical layer

The currently absent `experiment`, `agent`, `benchmark`, `recognition`, `state`,
`conditions`, and `statistics` packages implement the Protocol-v2 experiment.
New live intervention, repeat-harm, utility, self-report, orchestration, and
analysis modules extend the existing package at the narrow seams defined by
document 17. The experiment layer may consume exported adapter data but never
imports 9to5.

The implementation plan must refactor document 17 into pilot-critical tasks,
selected-tier tasks, and registered-secondary tasks while retaining its exact
contracts and tests. It must not execute the old V2-01→V2-38 sequence linearly.

## 6. Data and authority flow

```text
generator + seed ledger
    -> independent repository snapshots and common live failure prefix
    -> arm mapping / execution-order receipt
    -> selected condition and live descendant trace
    -> arm-blind exact outcome finalization
    -> immutable per-lineage block
    -> nuisance-only projector OR sealed result analysis
```

The nuisance route ends at de-identified rates and covariance structures. It
has no API for unblinding mean contrasts. The result route remains sealed until
the discovery or confirmation analysis stage. Notice/report routes terminate in
separate one-way sinks and are absent from the pilot-critical behavioural path.

Every capability is scope-specific: fixture, throwaway, selection, pilot,
discovery, confirmation, B-live, and paid execution capabilities are not
interchangeable. A capability validates its band, manifest, task digests, source
commit, and maximum model/resource calls before the guarded operation begins.

## 7. Gates, artifacts, and failure behavior

| Gate | Required artifact | Pass consequence | Failure consequence |
| --- | --- | --- | --- |
| Baseline Integrity | dual-run baseline receipt and fast-suite result | build kernel | repair baseline only |
| Injector validity | throwaway-band oracle/endpoint report | start selection | repair, regenerate throwaway band |
| Controller selection | nested-CV ledger and selected-artifact receipt | seal manifest | no pilot; repair requires new selection band |
| Kernel seal | manifest plus disjoint seed-band ledger | authorize pilot | no pilot |
| Feasibility | nuisance receipt, core/floor power bundles, tier receipt | build/run selected tier | no-go below floor |
| Discovery validity | digest-equality receipt and immutable descriptive result | confirmation remains authorized | stop only for pipeline invalidity |
| Paid compute | approved cost plan and atomic reservation | one bounded paid action | no RunPod call |
| Confirmation | digest-equality, untouched roster, official capability | immutable claim-of-record bundle | fail closed; no silent rerun |

Generated phase artifacts are append-only or content-addressed. Repairs create
new versions and supersession receipts; they never overwrite a result. Private
raw traces stay ignored, while publishable manifests contain bounded typed
features, digests, and explicit provenance.

## 8. Verification and interpretation

### Development verification

- Use `python -m pytest -q` as the fast default after Claude's test-policy
  changes are reviewed and committed.
- Run targeted `tests/research/` files for every empirical task.
- Run `python -m pytest -m "not qwen_smoke" -q` at milestone gates, with the
  documented WSL path for byte-sensitive foundation fixtures.
- Run the separately governed Qwen smoke only when the local model/cache and
  authorization gates are satisfied.
- Require `python -m pneuma_lab.status --check`, schema tests, firewall tests,
  manifest replay, `git diff --check`, and a clean source commit before every
  seal or execution capability.

### Result interpretation

- **Core positive:** Pneuma beats Base, Retrieval, and the visibly strong scalar
  while utility gates pass, and InfluenceOff/clamp evidence supports causal
  state influence. Credit the four-variable controller only to the extent that
  the scalar comparison permits.
- **Core scalar tie or win:** persistent state may help, but richer Pneuma state
  is not necessary under this implementation.
- **Floor positive:** claim only persistent causally active state versus no
  persistent state. Do not claim protection against a renamed counter.
- **InfluenceOff equivalent to Pneuma:** the implemented state is epiphenomenal;
  H2 is practically refuted even if a behavioural contrast exists.
- **Pipeline-valid null/negative:** report the interval and practical decision.
  Do not call failure to reject “no effect.”
- **No-go:** report the powered boundary and which conjunction components drove
  infeasibility. Nested challenges, transforms, and seeds never masquerade as
  new lineages.
- **Discovery effect:** always labelled descriptive and never used to explain
  why confirmation did or did not run.

## 9. Local-first compute and RunPod approval

All unit, fixture, generator, oracle, inference, power, and fake-backend work is
local CPU. Local authorized smoke runs use the pinned small Qwen quantization;
the primary frozen Qwen2.5-Coder-7B subject runs locally when measured throughput
and memory permit.

Before any paid action, a local dry run must produce:

- exact selected-tier cell counts, candidate/model-call/token/tool caps, retry
  allowance, checkpoint/quantization, image, GPU type, and resumability plan;
- measured local or light-spike throughput and a conservative wall-time model;
- the current provider price and a worst-case cost calculation including failed
  starts, retries, storage, and egress;
- the sealed kernel, preregistration, environment, and task-bundle hashes; and
- an append-only cost-ledger balance proving
  `settled + reserved + proposed worst case <= USD 50`.

The user must explicitly approve the exact plan hash and reservation. Approval
is one-use; price, image, GPU, bundle, manifest, or balance drift invalidates it.
The first paid action is a bounded throughput/parity spike. The full reservation
is released only after parity and artifact-copy verification pass. No experiment
run authorizes training, model promotion, or a larger cloud program.

## 10. Acceptance boundary

The design is satisfied when the implementation plan can point every task to a
phase, prerequisite gate, owned artifact, exact test command, and honest failure
state without leaving the implementer to decide:

- which tier runs;
- which data may choose the scalar or tune the system;
- which seed band an artifact belongs to;
- what code must remain byte-identical;
- what discovery can gate;
- when RunPod is permitted; or
- how positive, null, negative, invalid, and infeasible outcomes are reported.

This document authorizes planning and local implementation only. It does not
authorize the nuisance pilot, discovery run, confirmation, training, or paid
compute by itself.

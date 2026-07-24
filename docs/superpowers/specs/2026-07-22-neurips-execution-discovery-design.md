# NeurIPS 2026 Execution and Discovery Phase Design

**Status:** revised architecture; empirical implementation blocked on statistical
P0, then the conditional P0-T candidate-graph time gate in section 4.0

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

The feasibility boundary is itself a planned, publishable result. A P0 or pilot
no-go is not a failed build: it establishes that the registered causal claim
cannot be powered inside the fixed roster under the declared alternatives and
nuisance model. The floor limitation must be visible from the start: section 3
preregisters that a floor result cannot rule out a strong scalar counter.

### Hypotheses and claim order

- **H1-T (selected-tier behavior):** Pneuma reduces fixed-denominator
  `repeat_harm` by at least the observed five-point rule relative to every
  comparator required by the selected tier, while every registered utility and
  anti-gaming non-inferiority component passes.
- **H2-T (causal state influence):** disabling state-to-action influence and a
  randomized pre-action full-state clamp both worsen `repeat_harm` relative to
  intact Pneuma under the registered intervention schedule. H2-T is required at
  core and floor; a behavioral arm contrast without H2-T does not support the
  persistent-*causal*-state claim.
- **H3 (trace-grounded attribution):** postbehavior, prose-firewalled reports
  track the registered causal state better than the registered report controls.
  H3 is registered secondary and cannot explain H1-T/H2-T unless separately
  confirmed on a fresh preregistered roster.
- **H4 (known-motif transfer):** the H1-T pattern transfers to the registered
  surface and repository holdouts. H4 is registered secondary under this
  gate-first study.

The selected-tier claim is the intersection H1-T $\cap$ H2-T. H3 and H4 cannot
rescue it.

## 2. Invariants and non-goals

- Pneuma remains standalone and imports no 9to5 runtime code or private state.
- The behavior path, notice path, report path, and arm-blind evaluator remain
  structurally separated. Prose and self-report never award behavioral points.
- The frozen subject receives no weight training. `training_weight` remains
  `0.0` unless a separate hash-bound authorization explicitly changes it.
- Input data are resolved only from the required `data.input_root` configuration
  key or `PNEUMA_DATA_ROOT`; there is no implicit machine-specific default. The
  resolved root must be protected read-only by its mount/ACL and a platform-
  specific startup assertion recorded in the run receipt. Generated artifacts
  live under ignored, receipt-bound `build/research/` roots until a reviewed
  publication artifact is intentionally promoted.
- Determinism is claimed only for pure fixtures, generators, or explicitly
  deterministic controller operations. Stochastic model behavior is analyzed
  through registered assignments and repeated draws.
- Branch-local refusal, timeout, premature finish, budget exhaustion, invalid
  action, model/runtime failure, OOM, disk exhaustion, or sandbox corruption is
  adverse. Only a proved arm-common exogenous outage may remove a whole block.
- A negative or null effect is a valid result. No **pilot, discovery, or
  confirmation** efficacy value may alter the tier, continuation decision,
  endpoint, motif roster, scalar winner, or confirmatory analysis. Scalar and
  Pneuma constants are chosen solely from the disjoint selection band under
  section 4.4.
- Every arm receives identical ex-ante model-call, token, tool-action, time,
  memory, disk, and sandbox quotas. Differential cap binding is an outcome and
  a claim gate, never a reason to change a denominator or grant an arm more
  resources.
- Blinding is capability-enforced, not entrusted to a solo operator's memory.
  Raw pilot bytes are encrypted and quarantined before projection; tier
  computation can read only the sealed nuisance receipt. Every agent session has
  a capability/access receipt.
- An agent context that reads pilot, discovery, or confirmation outcome bytes is
  permanently outcome-tainted. That context and every descendant context are
  forbidden from authoring or modifying tier, power, or confirmatory-analysis
  code. The tier decision executes in a fresh context against sealed inputs.
- Subagents may parallelize disjoint authorship after determinism contracts are
  frozen; they are never counted as model-inference throughput or schedule slack.
- No RunPod action, pod creation, paid image pull, or paid model call occurs
  without the explicit approval gate in section 9.2.

## 3. Pre-pilot protocol amendment

Before any nuisance-pilot data are opened, one decision-log entry must record
all five linked decisions and their consequences:

1. adopt I1, I2, I3, I5, and I7 as the approved core revision; size I4 in the
   pilot, retain I6 as a diagnostic, use I8 as the H3 falsifier/demotion rule,
   and keep I9 discovery-only;
2. replace the undefined fallback with the monotone core → floor → no-go rule;
3. require an additive discovery band whose effect cannot gate confirmation;
4. require a digest-sealed nuisance kernel and a mutually disjoint seed-band
   ledger; and
5. require context-keyed candidate-pool sharing, the P0-T time gate, capability-
   scoped agent sessions, and outcome-context taint propagation.

That single entry also freezes the P0 prior-predictive nuisance grid, the
H2-T planning alternatives, the outcome-coding table in section 4.2, the
selection-band size and grid cardinalities, the observed-effect and
non-inferiority margins, and the time deadline. These values may be amended only
before P0 is run; a change after P0 requires a new P0 artifact and supersession
receipt.

The same entry precommits one utility-scope ladder before P0: U0 is the full
seven-component comparator-specific vector in section 4.2; if and only if U0's
P0 `P(no-go) > 0.40`, U1 retains verified-success non-inferiority, the frozen
composite-adverse non-inferiority gate, and resource-cap-binding
non-inferiority. All U1 margins remain `0.05`; attempt, completion, normalized
severity, false-avoidance, and adverse-event subtypes remain registered
descriptive decompositions. If U1 also has `P(no-go) > 0.40`, the result is P0
no-go. There is no margin-widening tier.

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
The amendment supersedes the old four-slot confirmatory treatment of H3/H4 for
this study: section 4.9 makes all demoted work descriptive-only unless a fresh
roster receives a separate preregistration before any of its outcomes exist.

## 4. Gate-first execution architecture

### 4.0 P0 joint-power plausibility gate

No locked joint-power executable exists in the current tree: the planned
`src/pneuma_lab/statistics/power.py` package is absent, and the earlier protocol
does not assign planning alternatives to the new mandatory H2-T components.
Consequently, as of 2026-07-22, `P(core)`, `P(floor)`, and `P(no-go)` are
**unavailable**, and the P0 gate is fail-closed. Reporting invented values here
would be worse than reporting no power result.

P0 is therefore the first and only permitted pre-kernel implementation unit:
implement and test the deterministic prior-anchor builder and simulator in
`src/pneuma_lab/statistics/prior_anchor.py`,
`src/pneuma_lab/statistics/power.py`,
`tests/research/test_prior_anchor.py`, and
`tests/research/test_power_simulation_v2.py`; bind their numerical
dependencies; and run them before any empirical kernel task in section 4.2.
The simulator must rerun the exact selected-tier decision logic, including the
intersection-union test and the co-required simultaneous max-T lower-bound rule
in section 4.2, rather than multiplying marginal powers. An IUT-only
approximation is not admissible. The decision-log amendment freezes the
following design inputs before the run:

- behavioral H1-T and both mandatory H2-T planning alternatives are absolute
  risk differences of `0.10` in the favorable direction;
- all true utility differences are zero and every bounded rate or normalized
  severity non-inferiority margin is an absolute `0.05`;
- the base-harm support is derived by the frozen adapter-anchor and recurrence-
  bridge rule below. Paired discordance has support and weights
  `{0.15: 0.15, 0.20: 0.35, 0.30: 0.35, 0.40: 0.15}`; the algebraic
  `0.10` boundary receives no prior mass. Highest-lineage ICC has support
  `{0.05, 0.15, 0.30}`, cross-component correlation has support
  `{0.25, 0.50, 0.75}`, and the three joint nuisance-quality profiles
  `(attrition, evaluator error, utility event rate, utility discordance)` equal
  to `(0.00, 0.00, 0.05, 0.05)`, `(0.025, 0.05, 0.15, 0.15)`, or
  `(0.05, 0.10, 0.30, 0.30)`. ICC, correlation, and nuisance profiles have
  equal within-dimension weights. The 324 pre-rejection cells receive the
  product of their dimension weights; effect/discordance-incompatible or
  non-positive-semidefinite cells are rejected by frozen rules and surviving
  weights are renormalized;
- because the concrete registry is not built before P0, P0 uses the deliberately
  optimistic ceilings of 96 distinct behavioral lineages and 48 distinct clamp
  lineages and repeats the screen at behavioral ceilings `{48, 64, 80, 96}`;
  the later manifest/pilot decision replaces those ceilings with the actual
  distinct conservative lineage counts and can only reduce feasibility; and
- official mode uses at least 10,000 deterministic decision-pipeline draws per
  surviving grid cell and adaptively increases to 100,000 whenever the 99%
  Monte Carlo interval intersects the `0.80` boundary. It emits Monte Carlo
  uncertainty, code/config digests, per-component marginal power, conjunction
  power, and the component most often responsible for failure.

#### Frozen adapter anchor and recurrence bridge

The external adapters do not measure Suite-A `repeat_harm`. They expose
dataset-specific observed `resolved` labels produced by other agents, scaffolds,
or verifiers; notably, the OpenHands-Verifier label is not asserted to be a
joined task outcome. Using their unresolved rate directly as Pneuma's base-harm
rate would be false precision. They are therefore allowed to anchor only broad
failure-like prevalence, followed by an explicit transport bridge.

`prior_anchor.py` consumes canonical, hash-verified adapter reports produced by
exactly these outcome-bearing adapters:

- `src/pneuma_lab/adapters/open_swe_traces.py`;
- `src/pneuma_lab/adapters/openhands_sampled.py`; and
- `src/pneuma_lab/adapters/openhands_verifier.py`.

`src/pneuma_lab/adapters/swe_gym_lite.py` is excluded because it is task-only
and has no observed agent outcome. For each included adapter `j`, compute
`f_j = resolved_false_j / (resolved_true_j + resolved_false_j)` over valid rows
after that adapter's frozen skip/quarantine policy. The generic failure anchor
is the median of the three `f_j` values, so each dataset family receives one
vote regardless of row count. Raw rows are never pooled across adapters. The
verifier stratum's documented missing-join and label-semantics caveats remain in
the receipt; its equal vote broadens external heterogeneity and is not evidence
that its label is endpoint-equivalent.

Inputs resolve under the read-only `data.input_root`/`PNEUMA_DATA_ROOT` from
section 2 at exactly:

- `processed/open-swe-traces/pneuma-trace/adapter_report.json`;
- `processed/swe-gym/openhands-sampled/adapter_report.json`; and
- `processed/swe-gym/openhands-verifier/adapter_report.json`.

The source revisions and expected adapter identities come from
`docs/data/registry/open-swe-traces.json`,
`docs/data/registry/openhands-sampled.json`, and the verifier entry in
`docs/data/training-readiness/dataset-registry.json`; report content must agree
with them before its label counts are read.

Let `f_anchor` be that median. The conditional recurrence bridge has support and
weights `{0.25: 0.25, 0.50: 0.50, 0.75: 0.25}` and induces three base-harm
values `p_harm = f_anchor * recurrence_share`. If two canonical decimal values
coincide, their weights are summed. This bridge is transport uncertainty, not a
claim that generic failure and repeated harm are equivalent.

The immutable `prior-anchor.json` receipt records every adapter/report/source
digest, adapter version, valid/skipped/quarantined counts, the three `f_j`
values, `f_anchor`, bridge support and weights, induced base-harm support, code
digest, and canonical serializer digest. Missing reports, a hash or schema
mismatch, a zero valid-label denominator, a non-finite rate, or an unavailable
included adapter produces **P0 no-run**. There is no uniform-grid fallback and
no substitution of fixture labels, task-only rows, prose heuristics, or
selection/pilot/discovery/confirmation outcomes.

P0 evaluates both precommitted utility scopes on the same surviving grid cells,
simulation draws, and common random numbers. `U0` is the seven-component vector
and `U1` is the three-component vector defined in section 4.2. For each
`U in {U0, U1}`, define

```text
P_U(core)  = Pr(core conjunction under U reaches 0.80 at the P0 support ceilings)
P_U(floor) = Pr(core under U does not reach 0.80 AND floor under U does)
P_U(no-go) = Pr(floor under U does not reach 0.80 at one or both ceilings).
```

The P0 receipt reports all six probabilities at
`Delta_power in {0.05, 0.10, 0.15}`. Only `0.10` selects utility scope: use U0
when `P_U0(no-go) <= 0.40`; otherwise use U1 when
`P_U1(no-go) <= 0.40`; otherwise emit P0 no-go. The selected utility scope is
sealed before any empirical kernel or outcome exists and cannot change at the
pilot tier gate. The other Delta values and the unselected utility scope remain
reported sensitivity analyses. If both scopes exceed the threshold, no kernel
build begins. The team must negotiate a larger independent-lineage roster or
explicitly choose the feasibility-boundary paper. Raising `Delta_power`,
widening a margin, or inventing another utility subset merely to make the roster
fit is forbidden.

The values have independent practical meanings. The observed H1-T rule of
`0.05` is one avoided repeat harm per 20 scheduled opportunities; the `0.05`
utility margin tolerates no more than one additional adverse utility event per
20. The `0.10` planning alternative is one avoided repeat harm per ten and is
twice the observed pass boundary because powering at the boundary gives roughly
an even chance of clearing the point-estimate rule. It is a planning scenario,
not the claimed minimum true effect and not a feasibility-tuned SESOI.

An analytic stress check already demonstrates why P0 is blocking. Under a
simplified paired-Bernoulli approximation with 96 independent lineages,
one-sided `alpha=0.05`, true difference `0.10`, and the observed five-point
gate, use `SE = sqrt((discordance - Delta^2) / 96)` and pass threshold
`max(0.05, 1.645 * SE)`. The power of **one** behavioral component is:

| Paired discordance | One-component power | Three independent components |
| ---: | ---: | ---: |
| 0.10 (mathematical minimum) | 0.948 | 0.851 |
| 0.15 | 0.835 | 0.582 |
| 0.20 | 0.727 | 0.384 |
| 0.30 | 0.569 | 0.185 |
| 0.40 | 0.470 | 0.104 |

The `0.10` row is retained only as the mathematical boundary stress check; it
has zero weight in the official prior. This is not the locked result: it omits
the lineage opportunity averages, cross-component dependence, utility gates,
H2-T, and the 48-sequence clamp ceiling. It is an auditable warning that a
complete conjunction can fail even when a marginal contrast looks conventional.

#### P0-T candidate-graph time plausibility gate

P0-T runs only if statistical P0 permits further work. Before the rest of the
empirical kernel, it authorizes one minimal local slice:
`src/pneuma_lab/agent/{backend,ollama_backend,sandbox,tools,actions,candidate_prompt,repair,candidate_pool,metering,driver}.py`
and the minimum experiment authorization seam, together with their determinism,
firewall, fake-backend, and one bounded primary-checkpoint spike tests. Static
fixture-only tasks exercise context divergence; no endpoint or treatment-effect
outcome is computed.

Candidate sharing is keyed by the complete pre-action generation context:
checkpoint/quantization and decoding digests, prompt/scaffold and tool-schema
digests, actor-visible current context, declared text-memory context if any,
sandbox snapshot digest, sequence/opportunity/challenge/seed, candidate-call
ordinal, repair state, and a pool seed derived without a configuration id.
Controller state, pressure, condition identity, intervention metadata, and
outcome/evaluator fields are forbidden key or prompt inputs.

One candidate batch is generated and receipt-bound per exact context key, then
fanned out byte-identically to every selection configuration with that key. Each
configuration reranks independently. Once selected actions or observable
histories diverge, their context keys diverge and they receive separate live
candidate calls. A later byte-identical context may share again. Tool execution
and downstream outcomes are not shared unless the determinism manifest
separately proves that operation pure; the default is independent cloned live
execution. There is no global one-pool-per-episode shortcut and no off-policy
one-step proxy for full `repeat_harm`.

Thus the 28,800 selection episode-cells are logical policy evaluations and
scoring operations, not automatically 28,800 model generations. The 360
`60 lineages × 3 challenges × 2 seeds` pools are only the first-decision nodes.
The candidate-graph receipt separately reports total unique context nodes,
fan-out per node, decision depth, divergence/reconvergence, actual model calls,
tokens, tool calls, cache hits, and cache-key collision checks.

P0-T uses a fixture-only six-lineage seed band, one lineage per motif, disjoint
from throwaway, selection, pilot, discovery, confirmation, and B-live. It
projects the complete 60-lineage selection band twice: once from configured hard
caps and once from p95 observed context-node growth and model/tool use. The
hard-cap projection determines authorization; p95 is reported as operational
expectation only. Both projections use section 9.1's measured throughput and
deadline. P0-T applies section 9.1's precommitted D0→D1→D2 rule; if D2 misses
2026-08-03, no remaining kernel work begins. Any different descope requires a
signed amendment and a fresh P0-T run. P0-T may not change grid members,
selection outcomes, endpoints, or scientific constants.

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

Before parallel authorship begins, write and review the failing determinism and
firewall contract tests for every module group in section 4.5. These tests own
canonical serialization, seed derivation, candidate-context keys, state/head
purity, outcome totality, power RNG, and manifest replay. Only after that test
commit is frozen may subagents implement disjoint module groups. An ownership
ledger permits one writer at a time per manifest group; cross-group interface
changes require the contract owner to update and re-freeze tests before parallel
work resumes.

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

The vocabulary is fixed. A **sequence** is an authored execution object with
its opportunities, three challenges, and nested decoding seeds. A
**highest-dependency lineage** is the conservative shared semantic/generator or
repository ancestor and is the only independent inferential unit. Every
sequence carries exactly one `lineage_id`; many sequences may map to one
lineage. The registry computes
`G_max = count(distinct conservative lineage_id)` after all ancestry merges.
Every comparison of `G_T*` to roster capacity uses `G_max`, never the nominal
96-sequence count. Nested challenges, transformations, and seeds increase
measurement density but not independent sample size.

#### Frozen primary outcome map

Every scheduled post-exposure opportunity contributes exactly as follows. The
table is canonical input to `src/pneuma_lab/evals/repeat_harm.py`, its serialized
form is hashed into the manifest, and exhaustive fixtures must prove that no
terminal state falls through to an implementer default.

| Terminal state | Numerator | Denominator | Notes |
| --- | ---: | ---: | --- |
| Task success | 0 | 1 | Remains in the fixed denominator. |
| Same-family harmful recurrence | 1 | 1 | Primary repeated-harm event. |
| New-family failure | 0 | 1 | Adverse in the separate total/new-family utility co-gate; never relabeled as recurrence. |
| Refusal | 1 | 1 | Branch-local non-engagement; ITT adverse. |
| Timeout | 1 | 1 | Includes actor or tool timeout confined to the branch. |
| Budget exhaustion | 1 | 1 | Model-call, token, tool-action, or retry cap. |
| Invalid action | 1 | 1 | Includes malformed action, premature finish, and unrepaired invalid output. |
| Missing scheduled slot | 1 | 1 | Any post-assignment branch that does not reach its slot. |
| Infrastructure failure (OOM/disk/sandbox) | 1 | 1 | Includes model/runtime error or sandbox corruption confined to one branch; cause is not adjudicated post hoc. |
| Whole-block exogenous outage | — | 0 for every arm | Allowed only when immutable arm-blind telemetry proves one external event made the complete randomized block unobservable. Apply one common mask, common weight renormalization, and best/worst attrition sensitivity. Unknown or partial cases remain branch-local adverse. |

A missing generator artifact or failed common preflight before assignment
invalidates the run; it does not create an outcome row. ITT with branch-local
infrastructure failures adverse is primary. A preregistered sensitivity analysis
recomputes every estimate after applying one common mask to any exact slot in
which **any** arm has an infrastructure failure, and reports the changed support
and weights beside ITT. Because that union mask is post-treatment, the
sensitivity is diagnostic and cannot replace, rescue, or overturn the ITT
decision.

All arms receive the identical resource envelope enforced by
`src/pneuma_lab/agent/metering.py` and the sandbox runtime. The pre-seal validity
band must show pooled cap binding at most `0.05` and a maximum between-condition
cap-binding-rate spread at most `0.05`; otherwise the resource envelope is a
broken instrument and must be repaired on a fresh throwaway band. Confirmation
never stops on an arm's observed binding rate. Instead, the same five-point
non-inferiority margin is a selected-tier utility component; failure blocks a
resource-neutral positive claim and remains part of the result.

The P0-selected H1-T utility scope is exhaustive and comparator-specific. U0
contains seven components for every comparator required by the tier: attempt
rate, completion rate, verified-success rate, normalized total/new-family-
failure severity, counterfactual false-avoidance rate, a composite branch-local
non-engagement/runtime-adverse rate, and resource-cap-binding rate.

U1 contains exactly three components per required comparator:

1. verified-success rate, higher is better;
2. composite-adverse rate, lower is better; and
3. resource-cap-binding rate, lower is better.

For U1, the composite-adverse indicator is one per scheduled opportunity when
any of the following occurs: new-family failure, refusal, timeout, premature
finish, budget exhaustion, invalid or unrepaired model output, missing slot,
branch-local infrastructure failure, or counterfactual false avoidance.
Same-family harmful recurrence remains the separate `repeat_harm` superiority
component and is not duplicated in this utility indicator. Multiple adverse
events in one opportunity still contribute one. A proved whole-block outage
uses the common denominator exclusion in the frozen outcome map.

All U0 and U1 non-inferiority margins remain absolute `0.05`. Higher-is-better
components use `U(Pneuma) - U(a) + 0.05`; lower-is-better components use the
opposite orientation plus `0.05`. Under U1, attempt, completion, normalized
severity, false-avoidance, non-engagement/runtime subtypes, and every individual
adverse subtype are registered descriptive outputs. U1 supports only aggregate
utility non-inferiority: it cannot establish separate non-inferiority for a
demoted component, and the composite can mask offsetting subtype tradeoffs.
Every demoted component and subtype is therefore reported beside the composite,
without a confirmatory p-value.

#### Primary estimand and inference

For comparator `a`, the finite-roster estimand is
`Delta_a^B = mu(a) - mu(Pneuma)`, where `mu` gives equal weight to registered
opportunities within cell, equal weight to cells within highest lineage, equal
weight to lineages within motif, and equal weight to the six motifs. Positive
values favor Pneuma. Policy mapping is paired within the complete randomized
block, while the highest lineage—not a sequence, challenge, or seed—is the
cluster.

The finite-roster sharp-global-null test replays the exact registered policy
assignment and uses all mappings when enumerable or at least 100,000 fixed-seed
Monte Carlo mappings. It supplies a Fisher p-value, not an effect interval.
Point estimates and assumption-bound population inference use at least 10,000
motif-stratified whole-lineage bootstrap draws, preserve every nested arm/cell/
seed together, and use the frozen studentized max-T distribution for
simultaneous one-sided 95% lower bounds. The result bundle reports both outputs
without presenting the bootstrap claim as design-based.

Within H1-T, `p_H1T` is the maximum component p-value over every tier-required
behavioral superiority and utility/non-inferiority component. Within H2-T,
`p_H2T` is the maximum over InfluenceOff and the randomized full-state clamp.
The selected-tier claim uses
`p_selected = max(p_H1T, p_H2T)` and passes only when every component, support
condition, observed five-point behavioral rule, simultaneous lower bound, and
validity gate passes. This intersection-union construction is one primary claim;
it does not divide alpha across its required components. H3, H4, notice, and all
section 4.9 outputs are outside this primary family.

Notice, H3 reporting, Reflection, Retry-count, H4, Suite B-live execution, and
non-load-bearing innovation diagnostics do not block the nuisance pilot. They
remain registered secondary and are implemented after the selected-tier result.

### 4.3 Throwaway validity band

Run the injector, oracle, endpoint, and causal-contrast path on a generator-
minted throwaway seed band of exactly six highest-dependency lineages, one per
motif. This gate checks:

- byte stability where determinism is claimed;
- oracle/injector agreement and metamorphic validity;
- fixed-denominator endpoint totality under success, recurrence, new-family
  failure, refusal, timeout, budget exhaustion, invalid action, infrastructure
  failure, missing slot, and whole-block outage;
- valid assignment and a computable Pneuma/InfluenceOff or clamp contrast;
- event rates inside a broad, preregistered bug-detection envelope; and
- identical resource-cap configuration plus the pooled and between-condition
  cap-binding limits in section 4.2.

The event-rate envelope detects broken injectors, dead oracles, or impossible
tasks. It cannot tune the DGP, power assumptions, motifs, thresholds, tier, or
endpoints. Implementation repairs are allowed only before scalar selection and
must cause the throwaway band to be regenerated.

### 4.4 Scalar and Pneuma selection band

Use a second generator-minted band of exactly 60 highest-dependency lineages,
ten per motif, disjoint by lineage and seed, for matched controller development.
It is the only efficacy-bearing development source allowed to choose scalar and
Pneuma constants.

Execution uses the P0-T context-keyed candidate graph. A `CandidateBatch` is a
common randomized pre-action object only for configurations whose full
generation-context key is identical. Every such configuration receives the
same bytes and performs its own deterministic rerank and live continuation.
Sharing stops at the first context divergence. The out-of-fold score is always
the full live fixed-denominator outcome; cached candidate generation never
becomes an off-policy or candidate-label proxy.

Selection uses five highest-lineage-blocked outer folds and four inner folds.
`controller-search-space.json` contains the D0 master of exactly 16 unique,
pre-enumerated configurations for each of five families: last-failure bit,
cumulative count, EWMA hazard, Beta-posterior hazard, and Pneuma, plus the frozen
D1/D2 subset labels from section 9.1. P0-T selects one equal family cardinality:
16, eight, or four. The scalar competition therefore receives 64, 32, or 16
total candidates against Pneuma's 16, eight, or four. Adaptive additions,
duplicate padding, and unlogged manual trials are forbidden. Selection then
proceeds as follows:

- inside each outer fold, inner folds search the complete last-failure-bit,
  count, EWMA, and Beta-posterior scalar grids plus the preregistered Pneuma
  grid; the chosen inner-fold configurations are evaluated only on that
  outer-held-out fold;
- the scalar receives at least the same attempted configurations, episodes,
  candidate selections, and logical candidate-access budget as Pneuma. Physical
  shared-pool calls are recorded once in the pool ledger rather than falsely
  multiplied across configurations;
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

Selection is stable only if the same scalar family/configuration pair wins at
least three of five outer-fold inner selections and the same Pneuma
configuration wins at least three of five. Failure is not resolved by the tie
rule: both controllers are under-determined, no pilot may run, and any changed
grid or enlarged band requires a decision-log amendment plus a fresh disjoint
selection band. The outer-held-out estimates are reported for each family and
may not be replaced by its in-sample score.

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
   shared candidate/context-key/decision machinery;
3. endpoint, utility, adverse-event, complete-block, and outage logic;
4. nuisance projector, core/floor power rules, inference code, numerical
   dependencies, and analysis seeds;
5. checkpoint, quantization, backend, prompts, tools, caps, RNG derivation,
   environment lock, and source commit; and
6. every development receipt and selected-controller artifact.

The manifest also binds the agent-session capability ledger, context-taint
ancestry, raw-band encryption public key, projector/tier capability digests, and
protected-code path set in section 6.

The manifest also owns an enumerated seed-band ledger for P0-T, throwaway,
scalar-selection, 30-lineage pilot, additive discovery, frozen 96-sequence
confirmation, and B-live. Each entry binds its generator version, allowed seed
support, highest-lineage digests, purpose, and forbidden consumers. Validation
proves pairwise disjointness and asserts that P0-T, throwaway, selection, pilot,
and discovery instances are newly minted rather than carved from the
96-sequence confirmation roster.

The ledger fixes the nominal bands at six fixture-only P0-T lineages, six
throwaway lineages, 60 selection lineages, 30 pilot lineages, 12 discovery
lineages, 96 confirmation sequences, and 36 B-live sequences. Each entry includes both `sequence_id` and
`lineage_id`; confirmation records the computed `G_max` after conservative
ancestry merging. “No band carved from the 96” is a machine-checked invariant,
not prose metadata.

#### Determinism manifest

The draft determinism manifest exists before the throwaway run, section 4.3
iterates it, and section 4.5 seals it. Byte stability for identical typed inputs,
seed, source, configuration, and numerical lock is required for:

1. `src/pneuma_lab/benchmark/motif_catalog.py`, `suite_a.py`, `sequence.py`,
   and `task_oracle.py`: generator output, lineage mapping, schedule, oracle,
   and sandbox-source specification;
2. `src/pneuma_lab/state/` pure update/decay/clip/serialization functions,
   `src/pneuma_lab/state/decision_head.py`, and the four scalar pure updates in
   `src/pneuma_lab/conditions/`: controller state and action-pressure outputs;
3. `src/pneuma_lab/interventions/schedule.py`, `operations.py`, and
   `provenance.py`: assignment seed derivation, clamp schedule, and canonical
   intervention receipt;
4. `src/pneuma_lab/evals/opportunity_evaluator.py` and `repeat_harm.py`:
   terminal-state classification, outcome coding, common-outage mask, and the
   equal opportunity→cell→lineage→motif aggregation;
5. `src/pneuma_lab/statistics/config.py`, `power.py`, `randomization.py`, and
   `bootstrap.py`: fixed-seed nuisance projection, P0/pilot power, assignment
   enumeration or draw stream, and bootstrap draw stream; and
6. all canonical JSON/JSONL registries, seed ledgers, search ledgers, manifests,
   authorization receipts, and result-bundle indexes after volatile timestamps
   are excluded from the hashed payload by one frozen serializer.

The same byte-stability requirement applies to
`src/pneuma_lab/agent/candidate_pool.py` context keys, pool-seed derivation,
fan-out order, and cache receipts. Candidate model output itself remains
stochastic; identical sharing means one realized receipt-bound batch is reused,
not that repeated model calls are claimed byte-identical.

Live model tokens/actions, external tool latency, OS scheduling, and wall-clock
timestamps are explicitly stochastic and receive no byte-stability claim.
Their prompts, caps, seeds, inputs, outputs, ordering, and environment are bound
in immutable receipts so stochastic variation is observable rather than silently
normalized away. Adding or removing an item from either set changes the manifest
digest and requires a pre-pilot amendment.

### 4.6 Thirty-lineage nuisance pilot and power decision

The pilot instantiates the complete five-arm core: Base, Retrieval, selected
scalar, Pneuma, and InfluenceOff plus its clamp schedule. Reflection, Retry,
notice, and H3 are absent.

The projector exposes de-identified per-condition event rates and the within-
lineage cross-condition covariance, variance, and ICC structure required for
paired power. It also exposes detector/oracle error, attrition, runtime, and
resource nuisance quantities. It masks condition identities, mean contrasts,
efficacy ordering, and treatment-effect sign.

The pilot runner writes append-only encrypted outcome chunks using a
manifest-bound projector public key and has no decrypt capability. The projector
capability alone may decrypt inside a fresh process, emit the signed nuisance
receipt, append its read/write audit, and reseal raw bytes into quarantine; it
has no source-write or tier-decision capability. The tier capability runs in a
fresh agent/process context, can read only the manifest, signed nuisance receipt,
and frozen power executable, and emits the tier receipt. Direct raw-byte access,
a missing access receipt, a tainted tier context, or a protected-code write after
raw access invalidates the pilot. With one OS owner this prevents accidental and
tool-mediated leakage; it is not represented as independent-party blinding
against a malicious machine administrator.

Run the locked joint-power simulator at `Delta_power = 0.10`, true utility
differences zero, the absolute `0.05` non-inferiority margins, and at least 80%
probability that the applicable complete conjunction passes. The deterministic
decision is:

- **Core:** Base, Retrieval, selected scalar, Pneuma, and InfluenceOff/clamp if
  the core conjunction fits inside the actual behavioral and causal
  highest-lineage support of the frozen registries;
- **Floor:** Base, Pneuma, and InfluenceOff/clamp if core is infeasible but the
  floor conjunction fits the same support ceilings; or
- **No-go:** neither conjunction fits. Do not execute confirmation. Publish the
  feasibility boundary or amend and preregister a new study before collecting
  new confirmatory outcomes.

The 30-lineage nuisance receipt does not use plug-in point estimates for this
step-function decision. It constructs a simultaneous 95% nuisance confidence
set over per-condition rates, the complete within-lineage covariance matrix,
variance/ICC, detector/oracle error, attrition, resource binding, and common-
outage quantities using whole-lineage resampling. For tier `T` and nuisance
vector `theta`, let `pi_T(G; theta)` run the complete decision on `G` behavioral
lineages while the frozen causal subroster contributes
`min(G, G_causal_max)` lineages. Define
`G_T(theta) = min{G: pi_T(G; theta) >= 0.80}`, with `G_T(theta) = infinity`
when H2-T cannot reach target power at `G_causal_max`, and use the conservative
projection `G_T* = max_{theta in C_0.95} G_T(theta)`. Beneficial covariance receives its
lower confidence bound; variance, ICC, error, attrition, and resource-loss terms
receive their adverse bounds. If point, lower, and upper-bound projections imply
different tiers, the conservative tier wins automatically.

The core conjunction contains Pneuma's repeat-harm superiority over Base,
Retrieval, and
the selected scalar, every registered utility/non-inferiority gate, and the
InfluenceOff plus randomized-clamp identification components. The floor
conjunction contains Pneuma's repeat-harm superiority over Base, the same
utility gates, and the same identification components. Select core when
`G_core* <= G_max`; otherwise select floor when `G_floor* <= G_max`; otherwise
emit no-go. A causal-subroster shortfall makes the corresponding `G_T*` infinite,
so it cannot be hidden by the larger behavioral registry. The receipt also reports
the frozen sensitivity at `Delta_power in {0.05, 0.10, 0.15}` without allowing
those sensitivity values to select the tier. Notice, H3, Reflection,
Retry-count, and H4 never enter either tier's power event.

The arithmetic is explicit. Under U0, core has three behavioral-superiority
components, seven utility components against each of three comparators, and two
H2-T components—26 required components total; floor has one behavioral, seven
utility, and two H2-T components—10 total. Under U1, core has three behavioral,
three utility components against each of three comparators, and two H2-T
components—14 total; floor has one behavioral, three utility, and two H2-T
components—6 total. Shared-lineage dependence is modeled jointly; these counts
are never converted into a product of marginal powers.

The selected tier is a hash-bound consequence of the pilot nuisance receipt and
power-rule digest. It cannot be overridden manually.

### 4.7 Additive discovery result

Mint exactly 12 new Suite-A highest-dependency lineages, two per motif, on the
ledger's discovery band. The discovery roster is additive and disjoint from the
pilot and confirmation; it never reduces the 96-sequence confirmation capacity.

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
The core result reports the selected scalar's confirmation-time harm reduction,
interval, utility outcomes, and cap-binding rate beside Pneuma's; selection-band
strength is not substituted for confirmation performance.

If an integrity gate fails after confirmation starts, all collected bytes are
sealed in a quarantined incident bundle and are never opened for efficacy
analysis. Publish an integrity/attrition report. A replacement confirmation is
a new study requiring a new preregistration, seed band or roster, manifest, and
authorization; it cannot pool with or silently replace the interrupted run.
Valid arm-common exogenous outages follow the frozen atomic mask. If their
removal leaves either highest-lineage support ceiling below the selected
`G_T*`, the result is **inconclusive due to lost support** and is not rerun on
the same registration. Branch-local failures remain adverse ITT and do not
trigger this disposition.

### 4.9 Secondary expansion and full study

After the selected-tier result is immutable, implement and execute registered
**descriptive-only** secondary work without changing the confirmatory claim:

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

No secondary p-value is a finding in this study. Secondary bundles report
effect sizes, uncertainty, full denominator/support counts, and an explicit
`descriptive` provenance tag. If a later paper requires confirmatory H3, H4, or
another secondary family, it must freeze its family and correction on a fresh
unseen roster before data collection; the current outcomes cannot be promoted
after inspection. Exploratory BH-FDR values may be emitted only when the frozen
dependence condition is justified and remain labeled exploratory/descriptive.

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
- `src/pneuma_lab/adapters/trajectory.py`, `envelope.py`,
  `open_swe_traces.py`, `openhands_sampled.py`, and
  `openhands_verifier.py` supply typed trajectory extraction, hash-bound
  generic outcome counts, and offline validation inputs. Their only P0 role is
  the limited failure-prevalence anchor in section 4.0; SWE-Gym-Lite remains
  task-only and contributes no outcome.
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
separate one-way sinks and are absent from the pilot-critical behavioral path.

Every capability is scope-specific: fixture, throwaway, selection, pilot,
discovery, confirmation, B-live, and paid execution capabilities are not
interchangeable. A capability validates its band, manifest, task digests, source
commit, and maximum model/resource calls before the guarded operation begins.

### 6.1 Agent-session capability and context-taint firewall

Every human or agent operation carries a manifest-bound `session_id`, parent
context ids, capability, readable path prefixes, writable path prefixes, source
commit, and append-only access log. The minimum capability classes are:

| Capability | May read | May write | Forbidden |
| --- | --- | --- | --- |
| Contract/source author | Frozen docs, tests, fixtures, source | Assigned source/test group | Every pilot/discovery/confirmation outcome path |
| Band runner | Frozen executable inputs and encrypted-output public key | Encrypted raw chunks and run receipts only | Decryption, source/docs, tier or analysis output |
| Nuisance projector | Encrypted pilot chunks via private projector capability | Signed blinded nuisance receipt and audit only | Source/docs, arm map, mean contrasts, tier receipt |
| Fresh tier decider | Manifest, blinded nuisance receipt, frozen power executable | Tier receipt only | Raw outcomes, source/docs, manual override |
| Result analyst | Sealed discovery/confirmation outcomes and frozen analysis executable | Immutable result bundle only | Source/docs, tier/power/analysis-code writes |
| Incident custodian | Encrypted/quarantined bytes and integrity telemetry | Quarantine and incident receipts only | Efficacy analysis and protected-code writes |

Reading any raw or unblinded pilot, discovery, or confirmation outcome marks the
session and all descendant contexts `outcome_tainted=true` permanently. The
capability layer then denies writes to the protected set:
`src/pneuma_lab/statistics/{power,config,randomization,bootstrap,multiplicity,decision_regions}.py`,
`src/pneuma_lab/experiment/{analysis,preregistration,official_gate,official_executor}.py`,
their tests and schemas, the frozen outcome map, and the decision-log/spec
sections governing tier or inference. Renaming a file or creating an alternate
analysis path does not evade the set: an import-graph and artifact-role audit
classifies new equivalents fail-closed.

A “fresh” tier context has no parent that is outcome-tainted, inherits no prior
conversation/transcript or scratch state, and receives only the three allowed
sealed inputs. Context separation is proved by the session ancestry/access
receipt and operating-system process boundary, not asserted in prose. Any
violation invalidates the affected band and triggers section 4.8's incident
disposition. Subagent count never appears in a throughput or wall-time formula.

## 7. Gates, artifacts, and failure behavior

| Gate | Required artifact | Pass consequence | Failure consequence |
| --- | --- | --- | --- |
| P0 power plausibility | hash-verified `prior-anchor.json`, locked U0/U1 prior-predictive `P(core)/P(floor)/P(no-go)` bundles, utility-scope receipt, Delta sensitivity, simulator/tests digest | seal U0 if its no-go probability is at most `0.40`, else U1 if its is; permit determinism contracts and P0-T | P0 no-run on anchor failure; otherwise negotiate roster or choose feasibility-boundary paper if both scopes exceed `0.40`; no kernel build |
| Baseline Integrity | dual-run baseline receipt and fast-suite result | permit the next authorized gate | repair baseline only; attempts are unbounded before registration but every attempt is logged and no later gate opens until clean |
| Determinism contract | reviewed failing contract tests and one-writer-per-group ownership ledger | permit P0-T slice, then disjoint parallel authorship | no parallel implementation |
| P0-T time plausibility | context-graph receipt plus hard-cap and p95 wall-time projections | build remaining kernel only if hard-cap path fits 2026-08-03 | execute frozen pre-P0-T descope ladder or feasibility-boundary route |
| Injector validity | throwaway-band oracle/endpoint report | start selection | repair, regenerate throwaway band |
| Controller selection | 60-lineage nested-CV ledger, P0-T-selected D0/D1/D2 search manifest, stability and selected-artifact receipt | seal manifest | no pilot; instability or repair requires amendment and fresh selection band |
| Kernel seal | manifest plus disjoint seed-band ledger | authorize pilot | no pilot |
| Context firewall | capability matrix, encryption/key receipt, session ancestry, protected-path and access-log audit | authorize each outcome-bearing capability | affected band invalid; quarantine and incident report |
| Feasibility | bounded nuisance receipt, core/floor power bundles, `G_max`/causal-support comparison, tier receipt | build/run selected tier | no-go below floor |
| Discovery validity | digest-equality receipt and immutable descriptive result | confirmation remains authorized | stop only for pipeline invalidity |
| Time feasibility | measured section 9.1 ledger and deadline slack | authorize each run band | shrink/amend before selection or stop; never trim a frozen run |
| Paid compute | approved cost plan and atomic reservation | one bounded paid action | no RunPod call |
| Confirmation | digest-equality, untouched roster, official capability | immutable claim-of-record bundle | fail closed; no silent rerun |

Generated phase artifacts are append-only or content-addressed. Repairs create
new versions and supersession receipts; they never overwrite a result. Private
raw traces stay ignored, while publishable manifests contain bounded typed
features, digests, and explicit provenance.

### Invariant-to-gate audit

| Section 2 invariant | Enforcing gate(s) |
| --- | --- |
| Standalone/no 9to5 runtime or private-state import | Baseline Integrity; kernel seal; discovery/confirmation digest preflight |
| Behavior/notice/report/evaluator separation | Baseline Integrity; injector validity; kernel seal; confirmation analysis receipt |
| `training_weight: 0.0` without hash-bound authorization | Baseline Integrity; kernel seal; every execution capability |
| Configured read-only input root and ignored output root | Baseline Integrity; kernel seal; every run startup receipt |
| Scoped determinism only | Injector validity iterating the determinism manifest; kernel seal; both digest preflights |
| Branch-local adverse and only proved whole-block exclusion | Injector validity; endpoint totality; confirmation analysis receipt |
| No pilot/discovery/confirmation efficacy-driven tuning | Controller-selection provenance; nuisance blinding; feasibility and discovery-validity gates |
| Equal ex-ante resources and differential binding as outcome | Injector validity; parity receipt; H1-T utility gate |
| Capability-enforced blinding and permanent context taint | Context firewall; projector and fresh-tier receipts; discovery/confirmation analyst receipts |
| Subagents provide no inference-speed credit | Determinism contract; P0-T and section 9.1 ledgers |
| No paid action without approval | Time feasibility; Paid compute capability and one-use reservation |

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

- **P0 unavailable (current state):** no powered tier is claimed and no empirical
  kernel build begins. The analytic table is a warning, not a replacement power
  result.
- **P0 anchor no-run:** report the missing or invalid adapter receipt and stop.
  Do not replace real outcome reports with task-only data, fixtures, or a
  uniform prior.
- **P0 no-go:** report `prior-anchor.json`, the transported base-harm support,
  the weighted prior grid, both U0/U1 `P(core)/P(floor)/P(no-go)` bundles,
  Delta sensitivity, support ceilings, and failure-driving components.
  Negotiate the roster before any empirical implementation or publish the
  planned feasibility boundary; do not widen margins or select an unregistered
  third utility subset.
- **U1 selected:** every positive result is qualified as aggregate utility
  non-inferiority only. Report all demoted components and adverse subtypes so an
  offsetting tradeoff remains visible; none receives a confirmatory p-value.
- **P0-T no-go:** report context branching, pool reuse, hard-cap/p95 wall-hours,
  and the D0/D1/D2 tier reached. Do not relabel logical episode-cells as model
  calls or use coding-agent parallelism to claim the schedule fits.
- **Core positive:** Pneuma beats Base, Retrieval, and the visibly strong scalar
  while utility gates pass, and InfluenceOff/clamp evidence supports causal
  state influence. Credit the four-variable controller only to the extent that
  the scalar comparison permits.
- **Core scalar tie or win:** persistent state may help, but richer Pneuma state
  is not necessary under this implementation.
- **Floor positive:** claim only persistent causally active state versus no
  persistent state. Do not claim protection against a renamed counter.
- **InfluenceOff equivalent to Pneuma:** the implemented state is epiphenomenal;
  H2-T is practically refuted even if a behavioral contrast exists.
- **Pipeline-valid null/negative:** report the interval and practical decision.
  Do not call failure to reject “no effect.”
- **ITT/sensitivity split:** ITT determines the claim. A materially different
  infrastructure-censored estimate is evidence of resource sensitivity and
  narrows interpretation; it never substitutes for ITT.
- **Interrupted or under-supported confirmation:** release the integrity or
  attrition disposition without efficacy analysis or same-registration rerun.
- **No-go:** report the powered boundary and which conjunction components drove
  infeasibility. Nested challenges, transforms, and seeds never masquerade as
  new lineages.
- **Discovery effect:** always labeled descriptive and never used to explain
  why confirmation did or did not run.

## 9. Local-first compute and RunPod approval

All unit, fixture, generator, oracle, inference, power, and fake-backend work is
local CPU. Local authorized smoke runs use the pinned small Qwen quantization;
the primary frozen Qwen2.5-Coder-7B subject runs locally when measured throughput
and memory permit.

### 9.1 Wall-clock ledger and deadline gate

The time budget is binding even when dollar cost is zero. One **episode-cell** is
one condition/configuration × sequence × challenge × decoding-seed logical
execution. It is not synonymous with one model call. Suite A has three
challenges and two seeds. The planned primary-path caps are:

| Band | Exact episode-cell cap before retries | Purpose |
| --- | ---: | --- |
| Throwaway | `6 lineages × 5 arms × 3 × 2 = 180` | Injector/oracle/endpoint and resource validity |
| P0-T | six fixture-only lineages; model calls set by unique context nodes | Candidate-graph branching and wall-time plausibility only |
| Selection | `60 lineages × (4 scalar families + Pneuma) × 16 configs × 3 × 2 = 28,800` logical evaluations | Five-fold nested-CV live controller selection over context-keyed shared candidate pools |
| Pilot | `30 lineages × 5 arms × 3 × 2 = 900` | Core nuisance estimation |
| Discovery floor/core | `12 × 3 × 3 × 2 = 216` / `12 × 5 × 3 × 2 = 360` | First descriptive result |
| Confirmation floor/core | `96 × 3 × 3 × 2 = 1,728` / `96 × 5 × 3 × 2 = 2,880` | Nominal execution capacity; power still uses `G_max` |

The randomized full-state clamp adds one descendant per causal-subroster cell:
`30 × 3 × 2 = 180` in the pilot, `12 × 3 × 2 = 72` in discovery, and
`48 × 3 × 2 = 288` in confirmation. Therefore the all-in primary caps are
1,080 pilot cells, 288 floor/432 core discovery cells, and 2,016 floor/3,168
core confirmation cells. Retries may consume only the common preregistered
retry allowance and appear separately in the ledger. B-live and other
secondaries receive a separate post-primary ledger and cannot delay or borrow
from the selected-tier run.

A local light spike before each new execution class measures, separately for
model and tool work: unique context nodes, fan-out, p50/p95 model calls per
logical episode-cell, input/output tokens, sustained p10 tokens/second, fixed
call latency, sandbox/tool seconds, memory, disk I/O, safe physical inference
workers, retry rate, and checkpoint-load/setup time. For band `b`, the receipt
computes and reports both projections:

```text
cap_model_hours_b = sum(max_context_nodes * max_calls_per_node
                        * token_cap / measured_p10_tokens_per_second
                        + max_calls * fixed_call_cap_seconds)
                    / (3600 * safe_physical_workers)
p95_model_hours_b = sum(p95_context_nodes * p95_calls_per_node
                        * p95_tokens / measured_p10_tokens_per_second
                        + p95_calls * p95_fixed_call_seconds)
                    / (3600 * safe_physical_workers)
cap_wall_hours_b = 1.25 * (cap_model_hours_b + cap_tool_hours_b + setup_hours_b)
p95_wall_hours_b = 1.25 * (p95_model_hours_b + p95_tool_hours_b + setup_hours_b)
```

The hard gate uses `cap_wall_hours`; p95 is operational context, not permission.
The 1.25 factor is contingency, not spare experimental capacity. A
content-addressed fixed-configuration result may be read by multiple CV folds
but is executed once; rerunning it consumes the retry ledger and never erases
the first receipt. `safe_physical_workers` counts measured model-serving slots,
not coding subagents or agent sessions.

Before P0-T, `controller-search-space.json` freezes nested, equal-cardinality
configuration sets for every scalar family and Pneuma: D0 has 16 per family, D1
has eight, and D2 has four. D1 and D2 are deterministic maximin-coverage subsets
of D0's normalized hyperparameter coordinates, selected without outcomes. P0-T
applies the monotone time rule: use D0 if its hard-cap path meets the deadline;
otherwise D1; otherwise D2; otherwise selection is time no-go. Their logical
selection sizes are 28,800, 14,400, and 7,200. Any descope weakens the
strongest-scalar falsifier and is recorded in the claim limitation; it never
changes the 60-lineage band or uses efficacy.

Hard milestones are inherited from the publication plan: kernel and selection
seal by 2026-08-03, pilot by 2026-08-06, tier/preregistration by 2026-08-09,
and immutable selected-tier confirmation by 2026-08-16 AoE, leaving analysis,
review, and submission time before 2026-08-29 AoE. Before a band starts, its
measured conservative critical path plus all unfinished prerequisite bands must
fit its milestone. If it does not, the run is no-go until scope is amended
before selection or compute is explicitly approved under section 9.2. No frozen
band is trimmed, parallelized beyond measured safety, or stopped on efficacy to
save the schedule.

The dated stop/descope triggers are: P0 and its decision-log inputs sealed by
2026-07-25; determinism contracts and P0-T tier D0/D1/D2 sealed by 2026-07-27;
throwaway and controller-selection execution authorized by 2026-07-29;
selection immutable by 2026-08-03; pilot immutable by 2026-08-06; and the tier
receipt sealed by 2026-08-09. Missing the first three triggers moves immediately
to the next precommitted time tier or the feasibility-boundary paper; missing
selection, pilot, or tier triggers forbids confirmation for this deadline. A
coding subagent cannot extend any trigger.

### 9.2 Paid-compute approval

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
- how every terminal state enters the primary numerator and denominator;
- which unit is independent and how sequence capacity maps to `G_max`;
- which estimand, test, bootstrap, IUT, and secondary multiplicity rule apply;
- which nuisance bound and power alternative drive feasibility;
- whether resource failures, partial rosters, and interrupted runs are handled;
- whether the wall-clock critical path meets the publication deadline;
- which candidate-generation contexts may share one realized pool;
- which agent capability may read each band's bytes;
- which context ancestry is permanently disqualified from protected code; and
- which dated descope or stop trigger applies;
- what discovery can gate;
- when RunPod is permitted; or
- how positive, null, negative, invalid, and infeasible outcomes are reported.

This document authorizes planning plus local implementation/testing of
statistical P0. If P0 passes, it conditionally authorizes only the frozen
determinism contracts and minimal P0-T slice. The remaining empirical kernel is
blocked until P0-T passes. It does not authorize the nuisance pilot, discovery
run, confirmation, training, or paid compute by itself.

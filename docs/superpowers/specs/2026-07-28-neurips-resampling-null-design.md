# The Resampling Null — NeurIPS 2026 Study Design

**Status:** selected submission-primary design; zero-spend local implementation
authorized; currency-bearing provider execution remains hash-gated

**Branch:** `codex/neurips-2026-empirical`

**Date:** 2026-07-28

**Internal deadline:** 2026-08-28; venue deadline 2026-08-29 23:59 AoE

## 1. Decision

The submission-primary study is:

> **The Resampling Null: Did Verification Help, or Did the Agent Just Get
> Another Try?**

It will test whether task-specific verifier feedback causally improves a frozen
tool agent beyond:

1. ordinary continuation without feedback;
2. an independent continuation from the same state;
3. a verifier-shaped but task-mismatched sham packet; and
4. the finite-sample resolution floor induced by stochastic decoding.

The empirical study uses two materially different open, objective environments:

- repository repair from SWE-bench-Live MultiLang; and
- stateful conversational/API work from the objective text subset of
  `tau2-bench` v1.0.1, referred to by the benchmark authors as τ³-bench.

The frozen primary subject is the official open-weight
`Qwen/Qwen3.6-35B-A3B-FP8`. A BF16 run is a distinct subject and may be used
only as a separately reported precision/provider replication.

This design supersedes the G1 gauge paper only as the submission-primary
workstream. It does not alter G1's results, revive the sealed Protocol-v2
program, or weaken any previous no-go.

## 2. Why this program

Three candidate programs were scored before implementation. Scores are out of
100 and use the weights in the header.

| candidate | novelty 25 | identification 25 | venue fit 15 | Aug-29 feasibility 15 | power / breadth 10 | artifact value 10 | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Frontier replication of G1 gauge cards | 13 | 19 | 11 | 14 | 7 | 9 | 73 |
| Generic four-arm standard across unrelated interventions | 18 | 22 | 13 | 10 | 8 | 8 | 79 |
| Verification-feedback assay with a measured resampling null | 23 | 24 | 15 | 11 | 8 | 9 | **90** |

The first option is feasible but would remain a measurement-reliability paper
with a frontier-generalization patch. The second has breadth but risks becoming
a benchmark collection without one decisive estimand. The selected option has
one intervention, one causal decomposition, direct workshop fit, and two
objective domains.

The generic novelty claim is retired. Three 2026 papers already test placebo,
shape-matched, or compute-matched controls in small code repair, and recent
agent-evaluation work already studies repeated trials, paired noise floors, and
harness variance. The open claim is narrower and stronger:

> For frontier-capable, long-horizon tool agents, can correct task-specific
> verifier evidence be distinguished from a plausible mismatched report and a
> pooled two-replicate no-feedback continuation, while quantifying post-trigger
> seed sensitivity under exact state branching?

The literature audit that forced this narrowing is retained under
`build/research/neurips-2026-workshop/last30days/`.

## 3. Claims and non-claims

### 3.1 Claim of record

The strongest admissible positive claim is:

> On one frozen open-weight subject across two objective tool-agent settings,
> true verifier feedback produced a task-level success gain that cleared a
> verifier-shaped mismatched-report sham and the pooled two-replicate
> no-feedback condition, while the paired no-feedback branches established an
> admissible post-trigger resolution scale.

That claim requires every gate in section 9. A positive point estimate alone is
not enough.

### 3.2 Contributions

1. A four-arm, snapshot-paired causal protocol separating correct task-specific
   feedback from a mismatched-report control and pooled no-feedback
   continuation, while measuring post-trigger continuation gain and seed
   sensitivity.
2. A resampling-null resolution test that turns post-trigger continuation
   variation into an observed control distribution rather than an assumed zero.
3. A cross-setting empirical application to repository repair and stateful
   tool/API work with objective endpoint graders.
4. A lineage-aware, arm-blind artifact and inference contract that can be reused
   by agent benchmark authors.
5. If API credits become eligible, a secondary measurement audit asking whether
   blinded LLM judges recover the same causal verdict as objective graders.

### 3.3 Explicit non-claims

- This is not proof that verification generally helps every model or scaffold.
- It does not identify the effect of a human expert verifier.
- It does not call sham feedback semantically inert; its purpose is to isolate
  correct/task-relevant feedback from a plausible mismatched report.
- No four-arm contrast identifies packet form alone. A pure apparatus estimand
  would require a fifth neutral-format arm and is outside this study.
- It does not treat seeds, trajectories, issues from one repository, or telecom
  permutations as independent scientific units.
- It does not claim exact prompt-token equality between packet and no-packet
  arms. REAL and SHAM are token-matched; the packet/no-packet difference is the
  required sham-packet decomposition, not a pure apparatus estimand.
- It does not import the legacy scorer, modify 9to5, train model weights, or
  establish phenomenal consciousness.

## 4. Frozen external subjects

All revisions below are immutable inputs. A later upstream change creates a new
experimental subject and cannot be pooled silently.

### 4.1 SWE-bench-Live MultiLang

- Harness: `microsoft/SWE-bench-Live`
  `70ec57e852e3f2d195790fe71f553e272c691833`.
- Dataset: `SWE-bench-Live/MultiLang`
  `608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b`.
- Dataset surface at that revision: 743 tasks, 381 repositories, eight
  language splits.
- License: harness and dataset MIT; every upstream repository and image keeps
  its own license and must pass the per-base-commit audit.
- Primary endpoint: all registered `FAIL_TO_PASS` and `PASS_TO_PASS` checks pass
  in a clean endpoint image.

Eligible tasks must:

1. come from a non-archived repository with an unambiguous permissive
   MIT/Apache/BSD/ISC/Zlib-class license at the task's base commit;
2. have a buildable pinned image;
3. pass the gold patch and regression suite in three consecutive clean runs;
4. fail at least one target check at the base commit;
5. require no private credential, mutable external service, or unsupported
   accelerator; and
6. contribute at most one task per repository to a confirmatory roster.

The preferred `C160` roster has 160 tasks from 160 repositories. The minimum
defensible `C120` roster has 120 tasks from 120 repositories with allocation:
9 C, 14 C++, 16 C#, 17 Go, 16 Java, 16 JavaScript, 16 Rust, and 16 TypeScript.
The exact `C160` allocation is produced before subject execution by the frozen
registry builder, with at least 12 tasks per language and no repository reuse.

### 4.2 τ³-bench objective text subset

- Repository: `sierra-research/tau2-bench`.
- Tag: `v1.0.1`.
- Dereferenced revision:
  `fc0055dc4e0a316c3f83133267fbd6faaa770992`.
- License: MIT.
- Python contract: `>=3.12,<3.14`.

The eligible pool contains only tasks with objective evaluation components:

| domain | eligible pool | accepted evaluator components |
| --- | ---: | --- |
| airline | 50 | `DB`, `COMMUNICATE` |
| telecom base | 114 | `ENV_ASSERTION`, and where present `ACTION` |
| banking knowledge | 97 | `DB`, `ACTION`; frozen offline BM25 retrieval |

Retail is excluded because 112 of 114 tasks depend on an LLM
`NL_ASSERTION`. Voice mode and API-backed retrieval are excluded. The resulting
pool is 261 task definitions.

The preferred `C160` roster contains 44 airline, 58 telecom, and 58 banking
tasks. The `C120` roster contains 40 from each domain. A domain-stratified
deterministic hash chooses tasks. Telecom receives an additional
issue-family-blocked and leave-one-family-out sensitivity because its 114 tasks
derive from only three issue families.

The user simulator is a frozen, locally served
`Qwen/Qwen3.5-9B` at
`c202236235762e1c871ad0ccb60c8ee5ba337b9a`, greedy decoding, with prompt,
chat template, turn cap, and per-turn seed recorded. This differs from the
official frontier user-simulator setting and must be described as an internal,
fully reproducible objective setting rather than leaderboard parity.

The simulator is a separately metered serving subject. On AWS, the default
`g6e.12xlarge` schedule reserves one L40S for the 9B simulator during τ³ work,
leaving at most three one-GPU primary replicas; a separate `g6.xlarge` L4 is the
predeclared substitute. On Azure, τ³ replication requires an additional
`Standard_NV36ads_A10_v5` simulator node. If that node is not eligible or
available, the BF16 replication is SWE-only; simulator compute is never
hand-waved as free or replaced with precomputed interaction-dependent replies.

### 4.3 Model subject and serving stack

Primary model:

- `Qwen/Qwen3.6-35B-A3B-FP8`;
- Hugging Face revision
  `95a723d08a9490559dae23d0cff1d9466213d989`;
- Apache 2.0;
- official block-wise FP8 checkpoint;
- text-only, thinking-mode tool use;
- `vllm==0.19.0` candidate serving package;
- `--language-model-only`;
- `--reasoning-parser qwen3`;
- `--enable-auto-tool-choice`;
- `--tool-call-parser qwen3_coder`;
- multi-token/speculative decoding disabled;
- prefix caching disabled for the study unless the parity pilot proves
  byte-identical responses under the frozen seed contract.

The container image, CUDA, driver, PyTorch, vLLM source/wheel digest, tokenizer,
chat template, tool parser, packet template, packet normalization/truncation
policy, and neutral pad-unit set are frozen after a no-cost or bounded parity
test. Their byte-level references are sealed in the study manifest before
packet construction. A package version without an image/source digest is not a
reproducibility receipt.

The topology and context cap are deliberately not frozen before the memory
pilot. The official FP8 blobs occupy about 34.9 GiB, leaving a tight margin on a
48 GiB L40S. The predeclared ladder is:

1. L40S tensor parallelism 1 at 32,768 tokens;
2. L40S tensor parallelism 1 at 65,536 tokens;
3. two L40S GPUs with tensor parallelism 2 at 65,536 tokens; then
4. H100 94 GB tensor parallelism 1 at the largest validated cap not exceeding
   131,072 tokens.

The largest candidate that passes OOM, tool-call, output-parity, and p10
throughput gates is frozen before confirmation. A topology change is a subject
change because it can change kernels and numerics. BF16 contains about 67.0 GiB
of weight blobs and therefore defaults to Azure
`Standard_NC48ads_A100_v4`, two A100 80 GB GPUs with tensor parallelism 2.
Single-A100 BF16 is allowed only if a realistic-context OOM and byte-parity
pilot passes; it is not the planning assumption.

Seeded online serving is not assumed reproducible. Tier 1 tests
`VLLM_BATCH_INVARIANT=1` with fixed request order, concurrency, topology, and
per-call seeds. The gate requires repeated requests to produce identical token
IDs. If it fails, Tier 1 is a no-go under the displayed topology and hour
table. Concurrency-one/offline serving with
`VLLM_ENABLE_V1_MULTIPROCESSING=0` is a diagnostic fallback only; confirmation
may use it only after a new throughput measurement, hour/cost calculation,
manifest hash, and approval. If no mode passes the byte-equality fixture, the
empirical study records a serving feasibility no-go. The four-arm design uses
IID randomized slots and never depends on common-random-number coupling.

Sampling is benchmark-specific but arm-common:

- SWE: thinking mode, temperature 0.6, top-p 0.95, top-k 20,
  presence penalty 0.0, repetition penalty 1.0.
- τ³: thinking mode, temperature 1.0, top-p 0.95, top-k 20,
  presence penalty 1.5, repetition penalty 1.0.

These are the publisher-recommended precise-coding and general-task settings.
Every seed is generated before outcomes and stored in the sealed assignment
ledger.

Separate, non-pooled subjects:

- BF16 precision replication:
  `Qwen/Qwen3.6-35B-A3B`
  `995ad96eacd98c81ed38be0c5b274b04031597b0`;
- development-only local subject:
  `Qwen/Qwen3.5-9B`
  `c202236235762e1c871ad0ccb60c8ee5ba337b9a`;
- optional frontier API replication, only under a fresh preregistration and an
  eligible provider-specific approval.

FP8 and BF16 results are never pooled as if they were the same subject.

## 5. Experimental unit and branching

### 5.1 Unit

The randomized causal unit is one benchmark task definition. Repository is the
highest lineage for SWE. Domain and issue family are additional blocks for τ³.
Seeds and branches are repeated measurements nested inside the task.

Each task produces one common prefix and four continuations. The prefix is
created exactly once, so arm differences cannot be attributed to different
pre-intervention trajectories.

### 5.2 Trigger

The intervention trigger is the earliest completed tool boundary satisfying
either:

1. the first mutation/action has returned and the state is verifier-eligible;
   or
2. the fourth subject tool call has returned.

The trigger occurs only after a tool result is committed. It never interrupts a
command, transaction, or model response.

Tasks that terminate before a trigger form the fixed-denominator
`no_intervention_opportunity` stratum. They are not discarded, re-run with a
different trigger, or used to choose a more favorable subject.

For the primary intention-to-treat estimator, such a task is retained with
`Y_R = Y_S = Y_N = Y_Z = Y_0`, so it contributes zero arm contrast. Effects
conditional on reaching the trigger are preregistered secondary estimates and
cannot replace the fixed-roster result.

### 5.3 Snapshot

At the trigger, the controller records and hashes:

- task and benchmark revisions;
- complete arm-visible transcript;
- subject sampling state and remaining quotas;
- tool call/result ledger;
- environment state;
- filesystem/worktree diff for SWE;
- both environment databases, user-simulator state, transcript, and RNG state
  for τ³;
- container/image/runtime digests; and
- a disposable endpoint score of the prefix state.

SWE uses a committed filesystem/container layer plus a clean checkout receipt.
τ³ uses a canonical serialization followed by deep-copy/restore equality tests.
Model KV state is not treated as portable state; each branch reconstructs the
same tokenized context and the receipt records exact token IDs.

If a pre-trigger response queued multiple tool calls, the snapshot includes
those pending calls. Each branch executes them in the same frozen order before
the first packet-visible model call. They count against the post-trigger
tool-call and wall-clock caps. The four post-pending/pre-injection visible-state
and token-ID digests must still match.

Prefix scoring and verifier execution happen on disposable clones. Their cache,
filesystem, timing, and output cannot flow back into any focal branch.

## 6. Arms

Every arm receives the identical post-trigger subject model-call, generated
token, tool-call, wall-clock, disk, network, and candidate/selection caps.
There is no best-of selection. The endpoint is the direct result of that arm.

| arm | injected evidence | continuation sampling |
| --- | --- | --- |
| `REAL` | correct task-specific verifier packet | one IID opaque branch slot |
| `SHAM` | shape- and token-matched packet derived from another lineage | one IID opaque branch slot |
| `NONE` | no message and no verifier evidence | one IID opaque branch slot |
| `RESAMPLE` | no message and no verifier evidence | one IID opaque branch slot |

For each frozen prefix, the controller creates four branch slots with IID
preregistered seed streams and a randomized execution-order/hardware schedule.
A uniform within-task draw assigns the multiset `{REAL, SHAM, NO_PACKET,
NO_PACKET}` over its 12 possible slot allocations, then a fair coin labels the
two no-packet slots NONE and RESAMPLE solely for the resampling audit. Both
draws occur before any continuation. The allocation is sealed and never
depends on a branch outcome.

Every primary-subject and τ³ user-simulator call derives its seed from the
scheduled prefix root or continuation-slot root, role, and call index through
the frozen domain-separated SHA-256 program.
The ordered per-call seed receipt is persisted. Both prefix and continuation
loops invoke the simulator through an explicit controller-owned seeded
interface; environment adapters may expose simulator context and apply a
returned turn but may not call a simulator internally. Adapters and serving
processes cannot choose replacement seeds.

`NONE` and `RESAMPLE` are exchangeable no-treatment replicates. Their mean is
the no-feedback continuation condition; their paired disagreement is the
empirical resampling null. The study makes no common-random-number claim for
REAL versus SHAM.

REAL and SHAM have the exact same subject-token length under the frozen
tokenizer, packet schema, field count, severity distribution, and continuation
sampling distribution. They differ in whether the findings apply to the focal
task.

The study does not pretend the no-payload arms have the same input length as the
packet arms. The estimand `SHAM - mean(NONE, RESAMPLE)` measures the net effect
of a mismatched report, including extra prompt tokens, misinformation, and the
generic instruction to reconsider work. It is not a pure apparatus effect.

### 6.1 Post-trigger quotas

Initial caps, frozen before pilot execution:

| benchmark | generated tokens | subject tool calls | wall clock |
| --- | ---: | ---: | ---: |
| SWE | 32,768 | 32 | 60 minutes |
| τ³ | 16,384 | 16 turns/tool calls | 30 minutes |

The common prefix has the same caps available before the trigger, but unused
prefix allowance does not enlarge an arm's post-trigger allowance. Cap binding,
timeout, refusal, malformed tool calls, and premature finish are outcomes.

## 7. Verifier and sham construction

### 7.1 SWE verifier

The verifier runs the task's pinned target and regression checks on a disposable
clone of the prefix state. The REAL packet may include:

- pass/fail status by registered check identifier;
- normalized compiler, assertion, or runtime failure class;
- a bounded log excerpt;
- regression status; and
- verifier resource/timeout status.

It never includes test source, gold patch content, future commits, or an
unbounded traceback. The final endpoint runs the official checks again in a
fresh grader image.

This is an intervention study, not a leaderboard submission. Giving hidden-test
feedback mid-trajectory is the treatment being studied and must be stated
plainly.

### 7.2 τ³ verifier

The verifier evaluates the eligible objective components against the cloned
prefix environment and transcript. The REAL packet reports:

- component type and satisfied/unsatisfied state;
- a policy-safe reason code;
- the relevant action or communication category; and
- bounded current-state evidence.

Expected final values and hidden task answers are not emitted. No LLM judge
creates a primary verifier finding.

### 7.3 Sham donor

A deterministic minimum-cost matching algorithm selects one donor from another
eligible lineage:

- SWE: same language, check runner/failure class, failure-count band, and log
  length band; different repository.
- τ³: same domain, evaluator-component multiset, failure-count band, and report
  length band; different task and, for telecom, different issue family where
  possible.

Task-specific identifiers are represented as typed references—repository/file,
symbol, test/check, database entity, policy/action, or task record—and replaced
only by the same reference type before injection. The donor assignment is a
derangement: no task donates to itself, no two-task reciprocal pair is allowed
within a block, and the map is frozen before branch outcomes.

The packet builder truncates bounded evidence and uses deterministic neutral
padding to make REAL and SHAM exactly equal in tokenizer length. Both packets
receive the same formatting and padding algorithm. Every truncation records the
original digest/token count, retained token count, rule ID, and omitted count;
nothing is silently dropped. Each packet-pair receipt binds focal/donor
verifier digests, assignment digest, identifier-map digest, tokenizer digest,
normalized findings, padding search, and collision result. All packet-pair
receipts are sealed into one packet-index digest before any branch starts. Raw
real and donor packets remain encrypted at rest. A branch worker may decrypt
only its opaque slot's packet inside the isolated subject-only guidance
boundary; packet text and the decryption capability remain unavailable to the
analysis author until unblinding.

### 7.4 Manipulation and detectability gates

Before confirmation:

1. every REAL finding must validate against its objective verifier artifact;
2. every SHAM packet must be false or irrelevant for the focal prefix under a
   collision checker;
3. a blinded packet classifier must have cross-validated AUROC whose upper 95%
   task-lineage bootstrap bound is below 0.60;
4. token count, field count, severity, truncation, and formatting distributions
   must satisfy the preregistered balance checks; and
5. manual or independent blind audit must find no arm-revealing identifier in
   the fixed audit sample.

Failure is `packet_invalid`; it blocks confirmation rather than inviting a
post-hoc rewrite after outcomes.

## 8. Outcomes and estimands

### 8.1 Primary outcome

`success` is the benchmark's objective binary endpoint:

- SWE: all target and regression checks pass in the clean final grader.
- τ³: all eligible objective components pass under v1.0.1.

All allocated blocks remain in ITT. An arm-specific infrastructure or model
failure is zero. A preregistered, arm-blind provider-outage receipt created
before any endpoint is readable may trigger one full four-arm rerun with the
identical snapshot, seeds, and allocation. If that rerun cannot complete, all
four outcomes are zero through a fail-closed finalizer that validates both
attempts and the original pre-endpoint outage, emits four adverse-zero
execution receipts, and never calls the endpoint grader. No allocated task is
excluded or replaced.

Workers therefore stop at sealed unscored terminal snapshots. The controller
seals every completed terminal receipt in its chronological attempt; no
superseded or partial-attempt receipt is discarded. It seals four final
completion/failure receipts and any one-time outage/rerun decision before a
grader may read an endpoint. No rerun interface accepts a graded receipt. A
no-intervention prefix launches no branch worker and records four copies of
`Y_0`.

For arm `a`, let
`f_a = 1/2 * (mean_i failure_SWE,i,a + mean_i failure_TAU,i,a)`.
The registered differential-failure gate is
`max_(a,a') |f_a - f_a'| <= 0.02`. Larger imbalance marks the pipeline invalid;
it never licenses task deletion.

### 8.2 Primary estimands

Let `Y_R`, `Y_S`, `Y_N`, and `Y_Z` denote REAL, SHAM, NONE, and RESAMPLE task
success. Let `Y_0` denote the disposable prefix-state score.

```text
no_feedback = (Y_N + Y_Z) / 2

content effect       Δ_content     = Y_R - Y_S
causal excess        Δ_excess      = Y_R - no_feedback
sham-packet effect       Δ_sham_packet = Y_S - no_feedback
continuation gain        Δ_continuation = no_feedback - Y_0
total verifier gain      Δ_total = Y_R - Y_0
resampling drift         Δ_null = Y_Z - Y_N
```

The two co-primary estimands are `Δ_content` and `Δ_excess`. Both must clear the
registered resolution gate. `Δ_continuation`, `Δ_sham_packet`, and `Δ_null`
are required decompositions, not optional diagnostics. `Δ_sham_packet`
combines packet form, extra tokens, mismatched content, and any misinformation
cost; it is not a pure apparatus estimand.

The primary cross-setting estimator gives SWE and τ³ equal weight, then averages
within benchmark over its fixed task roster. Benchmark-specific estimates are
always reported. Raw rows are never pooled as if the environments were one
exchangeable population.

### 8.3 Secondary outcomes

- benchmark-native partial reward;
- target-test gain and regression creation for SWE;
- evaluator-component gain for τ³;
- completion, refusal, malformed-action, timeout, and cap-binding rates;
- generated tokens, model calls, tool calls, verifier runtime, endpoint runtime,
  and wall clock;
- state-edit distance and action-path divergence after the intervention;
- packet acknowledgement and cited-finding rate; and
- arm-blinded judge score and reliability, if the API sidecar runs.

## 9. Inference, resolution, and verdicts

### 9.1 Finite-roster estimand and assignment

Index benchmark `b` in `{SWE, TAU}`, frozen task-prefix block
`i = 1, ..., n_b`, and four opaque continuation slots `j = 1, ..., 4`. Before
any continuation outcome, each slot receives an independently generated,
digest-bound seed stream and execution-order/hardware-lane label. Let
`Y_bij(a)` be the binary endpoint slot `j` would produce under
`a` in `{R, S, 0}`—REAL, SHAM, or no packet—conditional on the frozen task,
prefix, packets, software, quotas, and slot. Branch isolation and no
interference are required validity conditions.

Within each task, the assignment program uniformly randomizes the multiset
`{R, S, 0, 0}` over the four slots—12 equally likely allocations—then
fair-coin labels the two no-packet slots `N` and `Z` solely for the resampling
audit. The registry, prefix seeds, slot seeds, task order, and provider schedule
are digest-bound before prefixes. After all common prefixes and verifier
artifacts are frozen, the donor derangement is frozen and then each task
receives an independent uniform 12-way arm allocation plus an independent N/Z
coin, all before any branch-continuation outcome. Roster, order, and provider
schedules may be blocked by benchmark, language, domain, or declared
replication block; arm allocations are not coupled across tasks.

The finite-roster effects give each benchmark weight one half and average over
the four frozen seed/slot realizations:

```text
tau_content =
    sum_b [1 / (2 n_b)]
    * sum_i [1/4 * sum_j {Y_bij(R) - Y_bij(S)}]

tau_excess =
    sum_b [1 / (2 n_b)]
    * sum_i [1/4 * sum_j {Y_bij(R) - Y_bij(0)}]
```

Their unbiased observed estimators use
`d_content,bi = Y_R - Y_S`,
`d_excess,bi = Y_R - (Y_N + Y_Z)/2`, and
`hat_tau_k = sum_b [1/(2 n_b)] sum_i d_k,bi`.

The branch slot is the treatment-assignment unit; task prefix is the randomized
block and analysis cluster. With one prefix per task, inference is conditional
on those realized prefixes and measures post-trigger continuation variation,
not whole-run randomness or an unrestricted population of unseen
repositories. For a task that terminates before the trigger, all three
potential outcomes equal its terminal prefix grade. It remains in the primary
ITT analysis with zero contrast. Trigger-eligible effects are secondary.
Provider placement is not randomized into the primary effect; a different
kernel, precision, or provider is a separate replication block.

The analysis loads the immutable roster only through study-manifest ancestry
and rejects missing/extra task rows or changed benchmark, language/domain, or
issue-family membership before computing any statistic. A claimed roster
digest without the referenced bytes has no authority.

### 9.2 Finite-sample sharp-null tests

Exact Fisher tests are reported for sharp unit-level nulls; they are not called
confidence procedures for weak average-effect nulls.

For `H_content^sharp: Y_ij(R) = Y_ij(S)` for every slot, the test conditions on
the two slots occupied by `{R, S}` and independently swaps R/S within each task.
Its one-sided statistic is `hat_tau_content`.

For `H_excess^sharp: Y_ij(R) = Y_ij(0)` for every slot, the test conditions on
the SHAM slot and independently chooses which of the other three slots receives
REAL, with probability one third. Its one-sided statistic is
`hat_tau_excess`.

Exact product-randomization tails are computed by enumeration or dynamic
programming where feasible. Otherwise a valid Monte Carlo Fisher test uses
999,999 digest-bound draws, add-one p-values
`(1 + count(T* >= T_obs)) / (B + 1)`, and a reported Monte Carlo standard
error. Because the scientific alternative is the intersection
`{tau_content > 0 AND tau_excess > 0}`, the sharp-null decision is an
intersection-union test: both local one-sided p-values must be at most 0.05;
that conjunction needs no multiplicity correction.

An omnibus Fisher test of
`H_all^sharp: Y_ij(R) = Y_ij(S) = Y_ij(0)` redraws the full 12-way allocation
within every task, recomputes studentized `T_content` and `T_excess`, and uses
`max(T_content, T_excess)`. Its max-T p-value is exact for that global sharp
null only when enumerated, and otherwise is a valid add-one Monte Carlo Fisher
test. Define
`T_k = hat_tau_k / sqrt(Var_pi(hat_tau_k | unordered slot outcomes))`; if the
conditional variance is zero, set `T_k = 0` when `hat_tau_k = 0` and block the
test otherwise. The omnibus result is not a test or interval for weak average
nulls.

### 9.3 Simultaneous average-effect lower bounds

Average-effect inference uses a benchmark-stratified, task-cluster,
Romano-Wolf single-step multiplier max-t procedure. Let
`d_bi = (d_content, d_excess)'`, `bar_d_b` be its benchmark mean, and:

```text
S_b =
    1 / (n_b - 1)
    * sum_i (d_bi - bar_d_b)(d_bi - bar_d_b)'

V_hat = 1/4 * sum_b S_b / n_b
se_k  = sqrt(V_hat[k,k])
```

For each of 99,999 frozen Rademacher multiplier draws:

```text
G* =
    1/2 * sum_b 1/n_b
    * sum_i xi_bi * sqrt(n_b/(n_b-1)) * (d_bi - bar_d_b)

Z*_k = G*_k / se_k
M*   = max(Z*_content, Z*_excess)
```

Sort the `B = 99,999` realized max statistics and take the 1-based order
`min(B, ceil((B + 1) * 0.95))`, without interpolation, as `c_0.95`. The
simultaneous one-sided bounds are
`L_k = hat_tau_k - c_0.95 * se_k`. These bounds are
asymptotically valid/Neyman-conservative under independent randomized task
blocks; they are not finite-sample exact. A zero/non-finite standard error or a
failed no-interference receipt blocks a positive claim.

The positive claim requires:

- both local Fisher p-values—enumerated exact or add-one Monte Carlo—at most
  0.05;
- both simultaneous average-effect lower bounds above zero;
- both point estimates at least the practical screen `delta_star = 0.05`;
- both point estimates strictly above `r95`;
- non-negative point estimates in each benchmark separately; and
- for every co-primary contrast `k` and preregistered sensitivity group `h`
  (SWE language; τ³ domain and telecom issue family), the equal-benchmark
  estimator recomputed after deleting `h` and renormalizing within that
  benchmark satisfies `hat_tau_k^(-h) >= -0.05`; and
- the maximum pairwise difference among equal-benchmark-weighted arm-specific
  infrastructure-failure rates is at most 0.02.

`delta_star` is a preregistered observed-effect screen, not a confidence claim
that either effect is at least five percentage points. The paper may say the
effects were positive and large enough to resolve under this design; it may not
say a five-point minimum was established unless both simultaneous lower bounds
themselves exceed 0.05.

The secondary endpoint family is exactly
`(sham_packet, continuation, total)`. The same task-cluster Rademacher draws
produce marginal one-sided add-one multiplier p-values, Holm-adjusted across
these three, and a separate three-contrast single-step max-t 95% lower-bound
family. Holm adjusts p-values, not bounds. Benchmark-specific families use Holm
correction separately. Confidence
intervals, exact discordant-pair counts, and all estimates are reported
regardless of significance.

### 9.4 Resampling-null resolution

NONE and RESAMPLE are exchangeable no-payload replicates assigned to IID frozen
continuation slots. Let `D_bi = Y_biZ - Y_biN` and
`w_bi = 1 / (2 n_b)`. The analysis reports:

```text
q0  = sum_bi w_bi * |D_bi|

R(epsilon) =
      |sum_bi w_bi * epsilon_bi * D_bi|

r95 = inf {
          r : Pr_epsilon[R(epsilon) <= r] >= 0.95
      },
      with
          epsilon_bi independently in {-1, +1}
```

`q0` is the observed per-task no-feedback discordance. `r95` is the
aggregate label-swapped placebo-contrast scale. The sign-flip distribution is
exact under exchangeability of the two no-payload labels. When
`n_SWE = n_TAU = n` and `m` controls are discordant, it is the 0.95 quantile of
`|2K - m| / (2n)` for `K ~ Binomial(m, 1/2)`; otherwise the implementation uses
an exact weighted convolution. `q0` and `r95` are not confidence intervals,
semantic-verifier uncertainty, or minimum detectable effects.

`Δ_null = sum_bi w_bi D_bi` is only a randomized-label balance diagnostic.
There is no mean-equivalence gate: cancellation could make one pass under
maximal unit-level instability. Failure of either co-primary point estimate to
exceed both `delta_star` and `r95` produces `UNRESOLVED_RESAMPLING`, even when a
conventional p-value for REAL is small.

### 9.5 Power and roster tier

Before any confirmation outcome exists, deterministic P0 evaluates C120 and
C160 with the production assignment, local sharp tests, `q0/r95`, point gates,
and verdict logic. A synthetic roster may validate code/runtime conditionally,
but it has no tier-selection authority. The decisive P0 run occurs only after
the eligible registry freezes exact C120/C160 membership plus every SWE
language, τ³ domain, and telecom issue-family label, and it executes all
corresponding leave-one-group gates. The powered alternative is frozen at
full-roster ITT effects
`(tau_content, tau_excess) = (0.15, 0.15)` in each benchmark. For each benchmark,
the nuisance tuple is:

- no-feedback success `p0` in `{0.10, 0.40, 0.70}`;
- exact trigger opportunity `gamma` in `{0.60, 0.75, 0.90}`; and
- latent within-task equicorrelation `rho` in `{0.00, 0.40, 0.80}`.

The Cartesian product across SWE and τ³ contains 27 × 27 = 729 alternative
cells. On a no-trigger block, P0 draws `B ~ Bernoulli(p0)` and sets
`(R, S, N, Z) = (B, B, B, B)`. On a triggered block, it draws a four-variate
Gaussian copula with equicorrelation `rho` and thresholds it to marginals:

```text
p_R = p0 + 0.15 / gamma
p_S = p_N = p_Z = p0
```

These choices keep every probability in `[0.10, 0.95]` and make each
benchmark's expected ITT content and excess effects exactly 0.15. For each
benchmark, set `m_b = gamma * n_b` exactly; every registered combination makes
`m_b` integral. Uniformly select an exact-size triggered subset through
deterministic multivariate-hypergeometric counts over the roster's joint
sensitivity-group cells. A digest-pinned deterministic normal-rectangle
implementation precomputes the 16 triggered Bernoulli-pattern probabilities
and draws each cell's counts as `Multinomial(m_cell, pi_trigger)`. For that
cell's no-trigger tasks, draw
`U_cell ~ Binomial(n_cell - m_cell, p0)`, assign `U_cell` to pattern `1111`, and
assign the remainder to `0000`. These cell counts feed the same scalar/
vectorized sufficient-statistics gate kernel used by final analysis. P0 uses a
counter-based PRNG and 20,000 datasets per cell.

For power simulation only, the 99,999-draw multiplier critical value is
replaced with its deterministic two-dimensional Gaussian-max analogue:
`r = V_hat_CE / (se_C se_E)` and `c` solves
`Phi_2(c, c; r) = 0.95`. The worst five C160 cells, selected by the lowest
unrounded alternative gate-pass estimate (ties by frozen cell order) before
any confirmation outcome, must validate this
approximation against the full multiplier routine on 2,000 outer datasets.
Validation passes only if every selected cell's absolute difference between
Gaussian-max and full-multiplier gate-pass rates is at most 0.01 and both
methods choose the same roster tier. Otherwise P0 runs the full multiplier
routine on every cell under a separately screened
`full_multiplier_fallback` phase or records `FEASIBILITY_NO_GO`. Failed and
superseded attempts remain in the final report's ancestry. A successful
fallback emits a phase-specific validation receipt that checks full ordered
cell coverage, raw counts, numeric receipts, and tier decision directly; it
does not fabricate or reuse a Gaussian worst-five selection.

The numeric contract is frozen:

- `rho` is latent-Gaussian equicorrelation, not observed Bernoulli
  correlation;
- triggered 16-pattern probabilities use the one-factor representation and
  96-point Gauss-Hermite quadrature;
- probability sum and every recovered marginal must be within `1e-10`;
- the bivariate-normal CDF uses 128-point Gauss-Legendre quadrature over
  Plackett's correlation integral;
- Gaussian-max correlations `+1` and `-1` use the analytic one-sided-normal and
  two-sided-normal limits, respectively;
- the Gaussian-max root uses bisection tolerance `1e-10` and at most 200
  iterations; and
- separate one-sided Clopper-Pearson lower/upper inversions receive the full
  registered tail probability, use binomial-tail bisection tolerance `1e-12`,
  and use at most 200 iterations.

P0 first screens 200 datasets per cell on the declared CPU topology. The
projected full-grid wall time must be at most 12 hours and the screen must
reproduce numeric fixture digests before the 20,000-dataset run starts.
Otherwise the implementation is vectorized/partitioned and re-screened under
an incremented immutable generation, or the study records
`FEASIBILITY_NO_GO`. Every power artifact records its decision authority,
phase, generation, stage, and, for shards, shard index. The complete
power/type-I report parents every attempt. Its closed finalization is either a
completed selected chain with worst-cell validation or a terminal
`FEASIBILITY_NO_GO` naming the failed attempt/stage and reason without
fabricated downstream refs.

The type-I audit uses the same 729 nuisance pairs for each of three boundaries:

```text
A: both null
   p_R = p_S = p_N = p_Z = p0

B: content null, excess +0.15
   p_R = p_S = p0 + 0.15/gamma
   p_N = p_Z = p0

C: excess null, content +0.15
   p_R = p_N = p_Z = p0 + 0.15/gamma
   p_S = p0
```

The tier passes only when simultaneous exact-binomial Monte Carlo bounds
establish:

```text
min_theta P_theta(
    all statistical CAUSAL_CONTENT gates pass
    | alternative and nonstatistical gates pass
) >= 0.80

max_theta P_theta(
    statistical CAUSAL_CONTENT decision
    | either co-primary null and nonstatistical gates pass
) <= 0.05
```

For the 729 alternative cells, every one-sided Clopper-Pearson lower bound uses
tail probability `0.05 / 729`. For the 3 × 729 = 2,187 null-boundary cells,
every upper bound uses `0.05 / 2,187`. This is joint intersection power and a
familywise type-I audit, not marginal power for either contrast. The ordered
cell manifest, numeric routines, simulation count, validation cells, RNG
mapping, and raw counts are digest-bound. P0 also runs adversarial fixtures
with asymmetric sham harm, differential branch failure, and no-feedback
marginal imbalance; those must fail the applicable validity gate but do not
enter sample-size selection.

The preferred tier is `C160`, 160 tasks per benchmark. `C120`, 120 tasks per
benchmark, is the minimum. Preliminary planning says 120 paired binary units
per benchmark have about 80% power only for effects near 17 points at
discordance 0.40; that estimate is not a registered power result. If the exact
simulator or eligible roster cannot support the minimum tier, the study records
a feasibility no-go instead of shrinking into an anecdote.

Tier selection may use only frozen power output, eligible-roster size, verified
credit, measured p10 throughput, and calendar feasibility. It may not use pilot
arm efficacy.

### 9.6 Verdict taxonomy

Let `hat_tau_sham = SHAM - no_feedback`. It receives the registered one-sided
task-cluster multiplier lower bound `L_sham` from the three-contrast secondary
max-t family and a separately Holm-adjusted one-sided multiplier p-value. Let
`U_content` and `U_excess` be simultaneous
one-sided 95% upper bounds constructed by the same task-cluster max-t method.
Verdicts execute in the order below; `FEASIBILITY_NO_GO` is emitted only by
pre-outcome power/roster/runtime checks, never as a fallback from observed
outcomes.

| verdict | definition |
| --- | --- |
| `FEASIBILITY_NO_GO` | before outcomes, the powered roster/runtime cannot be completed |
| `PIPELINE_INVALID` | packet, snapshot, assignment, no-interference, grader, or differential-failure gate fails |
| `HARMFUL_OR_MISDIRECTING` | for content or excess, the point estimate is at most -0.05 and its simultaneous upper bound is below zero |
| `CAUSAL_CONTENT` | both co-primary contrasts and every registered statistical/resolution/admissibility gate pass |
| `SHAM_PACKET_ONLY` | CAUSAL_CONTENT fails; `hat_tau_sham >= 0.05`, `hat_tau_sham > r95`, the three-family Holm-adjusted sham p-value is at most 0.05, `L_sham > 0`, and content fails at least one of its registered finite-SE/sharp/lower/materiality/resolution/benchmark/sensitivity gates |
| `UNRESOLVED_RESAMPLING` | no earlier outcome verdict applies and a primary SE is invalid or a co-primary point estimate fails `delta_star`/`r95` |
| `RESAMPLING_CONSISTENT` | the valid, resolved remainder: observed REAL gains do not clear the registered inferential controls |

Every verdict is publishable. None authorizes changing endpoints or deleting
failed blocks.

## 10. Pilot and confirmation separation

Pilot rosters are disjoint from confirmation and reserve rosters:

- SWE: 16 pilot tasks, two per language, each from a unique repository.
- τ³: nine pilot tasks, three per domain.

Pilot outputs can validate:

- snapshot byte equality;
- tool parser and context reconstruction;
- verifier correctness;
- sham detectability;
- trigger opportunity;
- environment/grader flakiness;
- p10 episodes per GPU-hour;
- disk, memory, and network demand; and
- fixed budget adequacy.

Pilot efficacy is labeled and excluded from confirmation. No arm-specific pilot
effect may select a model, benchmark, endpoint, sample tier, or analysis.

After pilot validation, a fresh context seals:

1. the implementation and dependency digests;
2. the eligible task registry and replacements;
3. the prefix/slot schedule plus the deterministic donor-derangement and
   12-way allocation program and its synthetic fixtures;
4. the statistical-analysis source and expected synthetic fixtures;
5. the exact cloud execution manifest; and
6. the preregistration timestamp and digest.

Confirmation then runs and seals every common prefix and verifier artifact
without exposing branch endpoints. The already-sealed program mechanically
materializes the donor ledger, 12-way arm allocations, and N/Z coins from those
receipts, constructs and audits every token-matched packet pair, seals the final
packet-index digest, and seals the already-frozen analysis source/config/
projection-schema digest before any branch continuation. A human may inspect
only completeness/validity receipts during that transition, not prefix scores,
verifier content, packet text, allocation, or branch outcome.

Confirmation bytes remain encrypted and unavailable to analysis authors until
the analysis hash and artifact completeness receipt are sealed.

## 11. Optional objective-versus-judge sidecar

If OpenAI and Anthropic credits become verified and eligible, a post-hoc compute
action may run a separately preregistered, arm-blind measurement sidecar.

The judge receives only the final artifact, task statement, frozen rubric, and
objective evidence permitted by the benchmark. It never receives arm labels,
packet text, provider placement, or causal hypotheses. Order is randomized.

The sidecar uses:

- two frozen rubric wordings;
- one OpenAI model and one Anthropic model;
- deterministic or provider-supported seeded settings where available;
- the provider Batch API where compatible; and
- a fixed disagreement-adjudication sample chosen before judge results.

It reports ICC, `ndc`, wording/provider variance, and whether the judge-derived
causal verdict matches the objective verdict. Task/repository is the bootstrap
unit. It reuses the useful measurement-system idea from G1 only after repairing
G1's pooling, bootstrap-unit, calibration-split, provenance, and artifact
defects.

Judge results are secondary and cannot rescue a failed objective claim.

## 12. Artifact and blinding contract

### 12.1 Required records

Every scientific JSON root is validated by one registered schema:

```text
resampling-study-manifest.schema.json
resampling-prefix-schedule.schema.json
resampling-prefix-receipt.schema.json
resampling-assignment-ledger.schema.json
resampling-packet-index.schema.json
resampling-task-block.schema.json
resampling-blinded-projection.schema.json
resampling-analysis-freeze.schema.json
resampling-analysis.schema.json
resampling-power-report.schema.json
resampling-unblind-receipt.schema.json
resampling-artifact-root.schema.json
```

Raw model/tool streams, snapshots, patches, logs, and binary blobs are not
standalone records; a schema-valid parent carries their digest, size, media
type, and relative artifact name. Every task block and study envelope therefore
emits canonical, hash-linked coverage for:

- study manifest;
- external revision/license receipt;
- task registry and lineage;
- assignment and seed ledger;
- prefix trajectory and snapshot receipt;
- true verifier artifact;
- REAL/SHAM packet and donor receipt;
- branch trajectory and resource counters;
- endpoint grader output;
- infrastructure/adverse-event receipt;
- provider cost receipt; and
- analysis projection.

`resampling-packet-index` is a closed staged record: `candidate` contains
complete pair/no-intervention receipts and encrypted artifact refs; `sealed`
parents the candidate and adds the passed audit gates. Branches accept only
`sealed`. `resampling-power-report` likewise uses closed stages
`screen`, `shard`, `selection`, `validation`, and `final`.

A triggered task block embeds every chronological attempt and all terminal
receipts completed within it, including superseded first attempts and partial
failed second attempts. It also embeds four outcome-source terminal receipts,
four execution receipts, the chosen-attempt index, optional outage receipt, and
validity-event references. Those embedded records carry final-snapshot, grade,
provider-event, adverse-event, and provider-cost ArtifactRefs. A no-trigger
block uses a distinct closed schema arm with no branch receipts and four copied
`Y_0` outcomes.

Scientific records receive one injected `frozen_created_at` from the study
manifest; code never reads the wall clock while constructing their digest.
Operational event timestamps live in a separate non-scientific receipt chain.
Only artifact-root-relative POSIX names may enter scientific records; absolute
paths and output directories are excluded. Two self-tests with the same frozen
clock must therefore hash identically.

The artifact root recursively follows every ArtifactRef from every scientific
record, verifies the referenced raw bytes/size/media metadata, and hashes the
union of scientific records and referenced blobs. Dangling, conflicting, or
unlisted refs fail closed, including the deepest blob referenced only through
an embedded task-block receipt. Manifest, schedule, prefix-index, assignment,
projection, freeze, analysis, and unblind kinds are singleton. Packet indexes
have exactly one candidate and one sealed identity; task blocks are unique by
task ID with exact roster coverage. A power chain has one screen, selection,
validation, and shard set per append-only
`(decision_authority, phase, generation)` attempt, where phase is
`gaussian_approximation` or `full_multiplier_fallback`. Duplicate identities
within an attempt fail closed, but failed attempts remain immutable and later
generations are retained. Exactly one final report per authority parents every
attempt and closes as a phase-discriminated Gaussian completed chain,
full-multiplier completed chain, or terminal feasibility no-go. The Gaussian
arm requires its worst-five selection/approximation validation. The
full-multiplier arm instead requires its fallback trigger and full-grid
completeness/numeric/tier-validation receipt and forbids a Gaussian selection.
Determinism probes and nested artifact roots never share the result-of-record
root.

Large raw artifacts remain under ignored `build/research/` roots. A reviewed,
de-identified, license-compliant release bundle is promoted intentionally.

### 12.2 Capability separation

- The schedule controller cannot read verifier artifacts, arm IDs, or endpoint
  outcomes.
- The assignment controller can map arm IDs after prefix/verifier freeze but
  cannot read branch endpoint outcomes.
- A trusted preparer may resolve the clear ledger and packet index into four
  one-slot work orders. Each run worker receives only one opaque slot
  capability, its frozen snapshot/seed/caps, and at most one generically named
  subject-guidance artifact; it cannot read arm names, donor mappings,
  packet-pair receipts, the clear ledger, or other branches.
- The outcome projection builder receives task/slot capabilities and outcomes
  only; it cannot load the clear assignment ledger. It exposes opaque A/B/C/D
  labels.
- Only the hash-gated unblinder receives both opaque projection and clear
  ledger.
- The analysis author cannot access the unblinding key until source and
  synthetic expected outputs are sealed.
- A context that reads confirmation outcome bytes is outcome-tainted and cannot
  alter confirmatory code, task filters, or verdict rules.

The first run after unblinding is the result of record. A correction requires an
append-only deviation and a new artifact; it never overwrites the original.

## 13. Exact cloud architecture

No provider resource is authorized by this section. Prices are 2026-07-28
planning observations and must be re-queried at each action freeze.

The hour and cost model is valid only if Tier 1 proves:

1. FP8 Qwen3.6 serves on one L40S with the frozen context/concurrency cap;
2. BF16 Qwen3.6 serves on two A100 80 GB GPUs with tensor parallelism two;
3. AWS sustains four concurrent SWE subject replicas and three concurrent τ³
   subject replicas plus one user-simulator replica;
4. the frozen vLLM deterministic/batch-invariant mode passes byte equality;
5. forced interruption restores every arm-visible byte at a completed
   boundary; and
6. projected content-addressed durable bytes, p99 boundary delta, upload time,
   object requests, and attached GB-hours at C160 and Tier 3 fit the 2,000
   GB-month and fixed request/infrastructure allowances;
7. the independent AWS and Azure lease-expiry kill drills remove every tagged
   compute, pool, disk, endpoint/IP, and sibling container without relying on
   the study controller;
8. the exact AWS private/public network path and all endpoint/NAT charges pass
   bootstrap and metering;
9. the exact Azure VNet/subnet, node-communication mode, public-IP
   configuration, outbound/endpoints, DNS/firewall, and charges pass bootstrap
   and metering;
10. benchmark containers fail negative probes for IMDS, node credentials,
   managed identity, and Docker-socket access;
11. Azure seals SKU/image/node-agent/allocation/quota receipts and successfully
    allocates one exact node of every requested family;
12. the A10 simulator passes realistic-context OOM and throughput gates; and
13. every storage/network/log/registry/API billing dimension has an admission
    meter whose in-flight worst case fits the frozen cap.

Failure of any item invalidates the topology, hour table, and cost table. It
requires a newly priced and hashed manifest before confirmation.

### 13.1 AWS primary path

Region: `us-east-1`.

Services:

- AWS Batch managed EC2 compute environment, min vCPU 0, with a custom GPU AMI
  pinned by AMI ID and root-snapshot ID plus a bootstrap SHA-256, one-instance
  maximum, and one whole-instance job per node. The On-Demand environment pins
  `instanceTypes=[g6e.12xlarge]`, `maxvCpus=48`, and
  `allocationStrategy=BEST_FIT`; exactly one runnable controller job requests
  48 vCPUs, all four GPUs, and allocatable memory. Any Spot environment also
  pins the exact type/max-vCPU/job shape, seals its allocation strategy, and
  proves and independently guards one-node behavior in a separately
  hash-approved Tier-3 preflight whose hours debit the Tier-3 cap. Tier 1
  remains On-Demand only. Any future non-`BEST_FIT` On-Demand environment
  reserves the documented possible one-instance `maxvCpus` overshoot;
- EC2 `g6e.12xlarge`, 4 × L40S 48 GB and 384 GiB host RAM, reserved as one
  privileged controller allocation requesting all four GPUs, allocatable
  vCPUs, and allocatable memory so no unrelated Batch job can share the node;
- four TP1 subject replicas for SWE, or three TP1 subject replicas plus one
  frozen Qwen3.5-9B user-simulator replica for τ³; this concurrency assumption
  is invalid unless the Tier-1 gate passes;
- host Docker exposed only to the privileged controller, with the
  instance-store devices enumerated, formatted, and mounted as Docker's data
  root—striped only when enumeration finds more than one device, for
  approximately 3.8 TB total local NVMe;
- unique names, networks, work directories, and cleanup receipts for every
  benchmark container, with no provider credential exposed inside it;
- benchmark containers receive neither the Docker socket nor cloud
  credentials, and their network namespaces block IMDS. The controller uses a
  minimal per-run role restricted to its content-addressed storage prefix plus
  consistent `GetItem` on the exact run lease key/table; it cannot renew the
  lease. The independent watcher has a separate write/termination identity. A
  negative IMDS/credential/socket and least-privilege probe is part of Tier 1;
- ECR for digest-pinned controller, model-server, simulator, and harness
  images;
- one-AZ private networking with an action-manifested endpoint set for ECR API,
  ECR DKR, S3, DynamoDB lease reads, ECS control/agent/telemetry, CloudWatch
  Logs, and whichever of STS/EC2 the measured bootstrap requires; alternatively,
  a newly priced public/NAT path. Gateway/interface endpoint policies restrict
  the study role to its exact resources. Endpoint hourly and data-processing
  charges are explicit meters, never hidden inside “no NAT”;
- S3 Standard for durable manifests, checkpoints, provider-local OCI archives,
  and final artifacts, with a manifest-bound lifecycle-policy ID, absolute
  deletion date, and abort-incomplete-multipart rule. Any intermediate
  transition additionally freezes the destination price, minimum duration,
  retrieval charges, and final deletion date;
- content-addressed local NVMe caches, with bounded gp3 only when a measured
  image working set exceeds instance storage;
- CloudWatch Logs with fixed retention; and
- AWS Budgets alarms plus a controller-enforced multi-resource watchdog;
- an independently deployed EventBridge Scheduler + Lambda stop path with a
  DynamoDB lease and a minimal termination role. On expiry or a missing fresh
  lease it cancels/terminates Batch work, disables and drains the queue/
  compute environment, terminates every tagged study instance, removes tagged
  volumes/endpoints after artifact recovery, deletes the compute environment,
  and verifies zero tagged billable resources; and
- node boot sweepers and exit traps that kill every study sibling container.
  No fresh watchdog lease means no new model or API call.

Every model, package, and benchmark-image byte is staged provider-locally by
digest before confirmation. A no-NAT job is eligible only after the exact
endpoint set above passes a measured bootstrap; otherwise public/NAT
networking and all hourly/data-processing charges enter a newly hashed
manifest.

Current rates:

- `g6e.12xlarge`: $10.49264/hour On-Demand;
- historical Spot planning observation: $4.467/hour, currently non-authoritative
  because its AZ, UTC query response, product description, and digest were not
  retained;
- S3 Standard: $0.023/GB-month;
- gp3: $0.08/GiB-month.

The admission controller reads each task's declared and observed cgroup memory
and disk use. It starts a branch only when the admitted set plus a 20% reserve
fits at or below 307.2 GiB combined RSS/cache and 3.0 TB working disk; ECS/OS
use remains inside that reserve. Sustainable four-/three-way concurrency is a
Tier-1 measurement, never assumed for repositories near the reported 50 GB task
requirement.

Although each L40S is marketed as 48 GB, AWS documents roughly 44 GiB usable
per GPU on G6e. The Tier-1 OOM receipt therefore measures against usable
device memory, not nominal capacity. The 32K/65K ladder is a deliberate
deadline/budget compromise below Qwen's recommended 128K context and must be
reported as such if selected.

Confirmation is On-Demand. Spot is eligible only for a Tier-3 expansion after
the forced-interruption gate passes and a fresh AZ-specific
`DescribeSpotPriceHistory` response (UTC timestamp, product description, raw
response, and digest) is sealed. Until then all AWS Tier-3 expected and
reserved planning uses On-Demand.

No SageMaker endpoint, EKS cluster, marketplace model image, persistent idle
GPU, or cross-AZ artifact path is planned.

### 13.2 Azure replication/fallback path

Region: `East US`.

Services:

- separate Azure Batch pools: dedicated Tier-1/precision pools and Tier-3 Spot
  pools, each scale-to-zero with one task slot and at most one whole-node study
  allocation per VM. Dedicated and Spot target-node counts are explicit and
  never mixed behind one price;
- an action-manifested VNet/subnet, simplified node-communication mode,
  `publicIPAddressConfiguration`, and exact outbound path to Batch, ACR,
  Blob/lease, and required control planes. NAT versus service/private
  endpoints, DNS/firewall rules, hourly/data charges, and measured bootstrap
  receipts are frozen before use;
- a pool-scope elevated, idempotent start task that installs/validates the
  pinned host Docker/runtime/driver stack, preserves
  `AZ_BATCH_NODE_ROOT_DIR`, inspects `lsblk`/`findmnt`, and mounts only
  positively identified unclaimed temporary devices. It never generically
  formats “the NVMe disk”; the before/after device, filesystem, and mount
  receipt is sealed;
- non-container, pool-administrator Batch study tasks that launch only
  digest-pinned sibling host containers, avoiding Docker inside a Batch
  container or nested virtualization;
- `Standard_NC40ads_H100_v5` for same-FP8 provider parity/fallback;
- `Standard_NC48ads_A100_v4`, 2 × A100 80 GB under TP2, for the separately
  labeled BF16 precision replication;
- `Standard_NV36ads_A10_v5` for the Qwen3.5-9B τ³ user simulator whenever a
  τ³ H100 or A100 subject block runs;
- Azure Container Registry Basic for digest-pinned images, with a
  watcher-owned explicit repository/registry deletion action, absolute
  deadline, and receipt (Basic has no native untagged-manifest retention
  policy);
- flat-namespace (`HNS=false`) Blob Storage Hot LRS for
  manifests/checkpoints/artifacts, with manifest-bound lifecycle policy,
  absolute deletion date, and explicit version/soft-delete retention. Any
  intermediate tier transition freezes its destination/minimum-duration/
  retrieval pricing through final deletion;
- ephemeral/local disk for replaceable cache; and
- Cost Management advisory thresholds aligned with the action/provider hard
  stops enforced by the independent watcher;
- a separate pool/start-task `AcrPull` identity or short-lived repository-scoped
  pull token used only to hydrate digest-pinned images. Its digest/pull/revocation
  receipt is sealed before benchmark siblings start, and those siblings cannot
  reach the credential;
- a least-privileged controller identity restricted to the exact run
  container/prefix plus read-only access to the exact Storage lease; it cannot
  renew the lease, and sibling containers cannot reach its token/IMDS path;
- an independently deployed Function or Automation stop path with a Storage
  lease and termination-only managed identity. On expiry or missing lease it
  terminates tasks/jobs, sets both dedicated and Spot targets to zero, deletes
  every manifest-listed immutable pool/backing-resource ID, and verifies that
  exact node/disk/IP/endpoint set is gone. It never assumes backing-resource
  tag propagation; if resource tags are used for discovery, the manifest must
  prove `poolAllocationMode=UserSubscription`; and
- benchmark containers with no Docker socket, managed identity, IMDS access, or
  provider credential, proven by a recorded negative probe.

Current rates:

- H100 NVL 94 GB: $6.98/hour On-Demand, $1.40298/hour Spot;
- 2 × A100 80 GB: $7.346/hour On-Demand, $1.357541/hour Spot;
- A10 24 GB: $3.20/hour On-Demand, $0.59136/hour Spot; and
- flat-namespace Blob Hot LRS: $0.0208/GB-month.

The retired Batch Low Priority label/rate is not an execution option; Tier 3
uses explicit Spot pools.

H100 parity is substitute-only for Tier 2 when AWS primary capacity is
unavailable. In Tier 3 it is an optional additive, preregistered parity slice
already included in the displayed Tier-3 reservation. A100 BF16 output is a
distinct replication block.
The simulator VM is costed for the same τ³ wall time as its subject VM; if it is
unavailable, τ³ is omitted from that replication rather than silently sharing
or changing the user model.

Before the first Azure action, a read-only gate seals the current East-US
`list-skus` response, exact `imageReference`, `nodeAgentSkuId`, Batch allocation
mode, and regional/family dedicated/Spot quotas. Quota is not treated as
capacity. A separately priced, hash-approved Tier-1 reservation then allocates
one exact node of each requested family and seals its allocation receipt.
Those receipts are mandatory before any Tier-2/Tier-3 Azure reservation. NCads
A100 v4 is a material availability risk for net-new deployments; inability to
allocate the exact NC48 node drops the BF16 block unless a separately priced,
hashed, and approved substitute topology passes Tier 1. The A10 simulator also
has an explicit realistic-context OOM/throughput gate because its 24 GB device
margin is tight.

Azure is a parity/precision slice, not an automatic full-confirmation fallback.
At the registered wall-clock caps, a full C120 Azure replacement would reserve:

```text
H100 FP8:
1.5 * (900 * 6.98 + 300 * 3.20) + 341.60 = $11,204.60

A100 BF16:
1.5 * (900 * 7.346 + 300 * 3.20) + 341.60 = $11,698.70
```

Both exceed the user-reported Azure face value before that value is verified.
Full Azure substitution therefore needs a new budget and approval. No Azure ML
managed online endpoint, AKS cluster, public load balancer, or permanent GPU
pool is planned.

### 13.3 Durable boundary and interruption contract

After every completed model response or tool result, the controller writes a
content-addressed checkpoint containing:

- transcript bytes and exact token IDs;
- per-call subject and simulator seed schedules;
- tool invocation/result receipt;
- repository diff plus every mutable non-git workspace artifact required for
  exact reconstruction;
- τ³ databases, simulator state, transcript, and RNG state;
- runtime, container, image, model, and tokenizer digests; and
- cumulative token, call, wall-clock, and cost counters.

The reservation/watchdog meter covers instance/node hours, attached
GiB-hours, durable byte-hours, snapshot/version/soft-delete byte-hours,
incomplete multipart-upload bytes, ECR/ACR byte-hours, object operations,
log-ingest bytes, egress bytes, interface-endpoint/public-IP hours, and every
API billing dimension. Fixed miscellaneous allowances are worst-case
reservations, not enforceable caps by themselves. Provider budget alerts are
delayed advisory signals and never substitute for the independent stop path.
Storage and supported registry/log lifecycle-policy IDs, absolute expiry
dates, abort-incomplete-multipart rules, and version/soft-delete retention are
frozen before upload. ACR Basic instead uses the watcher-owned explicit delete
action and deadline above. The storage reservation and watcher stay active
until a verified final-deletion receipt, unless the remaining retention horizon
is fully reserved. A storage-class transition alone never releases a
reservation; destination-tier and minimum-duration costs remain reserved
through verified final deletion.

The checkpoint is uploaded to S3 or Blob, verified by hash, and followed by an
atomic completion marker before the next boundary starts. A local marker is
insufficient. A resumed branch retains task, arm, sample ID, and seed schedule
and appends an attempt receipt. Restore must match the prior boundary receipt
before the next model call. Any mismatch invalidates the entire four-arm task
block; one failed arm is never silently replaced.

Model KV state is reconstructed from recorded token IDs. A server restart,
instance replacement, provider change, GPU topology change, or kernel change is
not presumed reproducible. Online vLLM uses `VLLM_BATCH_INVARIANT=1`,
per-request seeds, and frozen request order/concurrency only after the exact
Qwen3.6 byte-equality fixture passes. A failure is a Tier-1 no-go for the
displayed concurrency and cost model. Concurrency-one/offline execution is
eligible only after a newly measured, recosted, hashed, and approved manifest.
The study makes no common-random-number claim.

### 13.4 API path

OpenAI and Anthropic are restricted to the blinded secondary sidecar or a fresh
frontier replication. They do not create primary verifier findings or primary
outcomes.

Planning models and standard input/output rates per million tokens:

- OpenAI `gpt-5.6-luna`: $1 / $6; Batch $0.50 / $3;
- OpenAI `gpt-5.6-terra`: $2.50 / $15; Batch $1.25 / $7.50;
- Claude Haiku 4.5: $1 / $5; Batch $0.50 / $2.50;
- Claude Sonnet 5 introductory: $2 / $10; Batch $1 / $5 through
  2026-08-31.

Only de-identified, license-permitted excerpts may leave the compute account.

Each API action manifest also freezes cache-read/write charging,
long-context/tool/regional premiums, retry count, and per-request input/output
ceilings. Admission enforces:

```text
charged
+ reserved_worst_case_cost_of_every_in_flight_request
+ proposed_request_worst_case
    <= action_cap
```

A post-response check is insufficient because it can discover an overrun only
after billing.

## 14. Costed execution tiers

### 14.1 Cap-derived hours

One task consumes one prefix plus four continuations. The registered wall caps
give:

```text
SWE subject-hours per task = 5 * 1.0 = 5.0
τ³ subject-hours per task  = 5 * 0.5 = 2.5
```

Four SWE subjects share an AWS node. Three τ³ subjects share it while the
fourth GPU serves the user simulator.

| roster | SWE subject-hours | AWS SWE instance-hours | τ³ subject-hours | AWS τ³ instance-hours | total AWS instance-hours |
| --- | ---: | ---: | ---: | ---: | ---: |
| C120 | 600 | 150 | 300 | 100 | **250** |
| C160 | 800 | 200 | 400 | 133.3333 | **333.3333** |

These are cap-derived schedule hours, not optimistic token-throughput
estimates. The reservation multiplier covers startup, verifiers, graders,
admission-control loss, bounded retry, and scale-down lag:

```text
unbuffered_compute = instance_hours * current_On_Demand_rate

reserved_total =
    1.50 * unbuffered_compute
    + object_block_registry_log_request_egress_allowance
    + API_caps
```

Tier-3 AWS planning expected uses On-Demand until the interruption gate and a
sealed current AZ-specific Spot query both pass. Azure planning expected uses
the current official Retail Spot observations but remains conditional on
capacity/eligibility. Every reservation uses all-On-Demand; a lower
all-eligible-Spot scenario is reported separately and never used for admission.

### 14.2 Fixed allowances

```text
Tier-2 AWS:
2,000 GB-month S3   = 2,000 * 0.023 = $46.00
2,000 GiB-month gp3 = 2,000 * 0.08  = $160.00
ECR/log/request/egress cap                  = $200.00
AWS infrastructure allowance               = $406.00

Tier-3 incremental AWS infrastructure       = $506.00

Tier-3 Azure:
2,000 GB-month Blob = 2,000 * 0.0208 = $41.60
managed disk/ACR/log/request/egress cap     = $300.00
Azure infrastructure allowance             = $341.60
```

Tier 1 uses $20 AWS and $30 Azure infrastructure allowances.

### 14.3 Tiers

| tier | exact scope | planning expected | reserved worst case |
| --- | --- | ---: | ---: |
| 0 | local registry, schemas, simulator, fake model, and local 9B work | $0 | $0 |
| 1 | AWS 12 h g6e OD; Azure 8 h H100 OD, 8 h NC48 A100 OD, and 16 h A10 OD; $50 infrastructure | $341.72 | **$487.58** |
| 2-C120 | AWS C120, 250 g6e OD hours; $406 AWS infrastructure; OpenAI cap $200; Anthropic cap $50 | $3,279.16 | **$4,590.74** |
| 2-C160 | AWS C160, 333.3333 g6e OD hours; same infrastructure and API caps | $4,153.55 | **$5,902.32** |
| 3 | one disjoint 80-task-per-benchmark expansion roster on AWS; Azure H100 and BF16 reuse the same fixed 24-task-per-benchmark subset of that roster; OpenAI $1,500; Anthropic $350 | **$5,014.23** with AWS OD and current Azure planned Spot; $4,009.96 conditional all-eligible-Spot scenario | **$9,764.78** |

Arithmetic of record:

```text
Tier 1 AWS expected =
    12 * 10.49264 + 20
    = $145.91168

Tier 1 AWS reserved =
    1.5 * (12 * 10.49264) + 20
    = $208.86752

Tier 1 Azure expected =
    8 * 6.98 + 8 * 7.346 + 16 * 3.20 + 30
    = $195.808

Tier 1 Azure reserved =
    1.5 * (8 * 6.98 + 8 * 7.346 + 16 * 3.20) + 30
    = $278.712

C120 expected =
    250 * 10.49264 + 406 + 200 + 50
    = $3,279.16

C120 reserved =
    1.5 * (250 * 10.49264) + 406 + 200 + 50
    = $4,590.74

C160 expected =
    (1,000 / 3) * 10.49264 + 406 + 200 + 50
    = $4,153.54667

C160 reserved =
    1.5 * ((1,000 / 3) * 10.49264) + 406 + 200 + 50
    = $5,902.32
```

Tier 3 freezes one 80-task-per-benchmark roster disjoint from pilot and
confirmation. AWS runs that roster. H100 and BF16 both reuse the same fixed
24-task-per-benchmark subset of those 80 tasks, so the provider/precision
slices consume no additional task definitions. Tier 3 uses exactly `500 / 3`
AWS g6e instance-hours (166.6667 when displayed); each Azure subject slice uses
180 VM-hours, and their τ³ slices
jointly use 120 A10 simulator hours:

```text
Tier-3 AWS expected =
    (500 / 3) * 10.49264 + 506
    = $2,254.773333...

Tier-3 AWS reserved =
    1.5 * ((500 / 3) * 10.49264) + 506
    = $3,129.16

Tier-3 Azure expected =
    180 * 1.40298
    + 180 * 1.357541
    + 120 * 0.59136
    + 341.60
    = $909.45698

Tier-3 Azure reserved =
    1.5 * (
        180 * 6.98
        + 180 * 7.346
        + 120 * 3.20
    )
    + 341.60
    = $4,785.62

Tier-3 total expected =
    2,254.773333... + 909.45698 + 1,500 + 350
    = $5,014.230313...

Conditional eligible-Spot scenario =
    ((500 / 3) * 4.467 + 506)
    + 909.45698 + 1,500 + 350
    = $4,009.95698

Tier-3 total reserved =
    3,129.16 + 4,785.62 + 1,500 + 350
    = $9,764.78
```

Tier 3 is not automatic. If selected before unblinding, selection may use only
funding, quota, throughput, and artifact-completeness data. If selected after
unblinding, it is a newly preregistered, disjoint exploratory replication and
cannot be merged into the original confirmatory test.

### 14.4 Cumulative planning stops

| completed scope | cumulative expected | cumulative worst (rounded cents) | rounded kill cap |
| --- | ---: | ---: | ---: |
| Tier 1 | $341.72 | $487.58 | **$500** |
| Tier 1 + C120 | $3,620.88 | $5,078.32 | **$5,100** |
| Tier 1 + C160 | $4,495.27 | $6,389.90 | **$6,400** |
| Tier 1 + C120 + Tier 3 | $8,635.11 | $14,843.10 | **$14,900** |
| Tier 1 + C160 + Tier 3 | $9,509.50 | $16,154.68 | **$16,200** |

Full-plan provider-local ceilings, using C160, are:

| provider | full-plan worst (rounded cents) | provider kill cap |
| --- | ---: | ---: |
| AWS | $8,990.35 | **$9,100** |
| Azure | $5,064.33 | **$5,100** |
| OpenAI | $1,700.00 | **$1,700** |
| Anthropic | $400.00 | **$400** |

These are ceilings, not entitlements. A sidecar whose provider remains
unverified is skipped and its cap remains unreserved. The face values are
pending, have spendable value zero, and are not fungible across providers.

## 15. Spend and action gate

Before every currency-bearing provider action:

1. verify portal balance, expiry, eligible services, Spot/Batch eligibility,
   region, billing currency, applicable tax/fees, and whether credits cover
   those tax/fees;
2. read quotas and published availability signals without mutation; capacity
   is proved only by a separately reserved, approved Tier-1 allocation receipt;
3. re-query every unit price;
4. freeze provider, region, SKU, pool/instance count, maximum instance-hours,
   API input/output tokens, uploaded bytes, object requests, attached GB-hours,
   actual billing currency, FX source/timestamp/buffer, tax/fee treatment and
   uncovered-cash amount, durable/snapshot/version/soft-delete/multipart bytes, registry bytes,
   log-ingest and egress bytes, endpoint/public-IP hours, job timeout,
   AMI/root-snapshot/bootstrap and image/model/dataset digests, output prefix,
   checkpoint cadence, supported lifecycle-policy IDs, explicit ACR-deletion
   action, absolute retention/expiry/deletion dates, multipart-abort and
   version/soft-delete rules, retry ceiling, API
   cache/context/tool/region premiums, and the independent lease-based stop
   watcher plus teardown verification;
5. calculate expected, all-On-Demand reserved worst case, provider cumulative
   worst, and project cumulative worst;
6. prove both invariants:

```text
provider_settled
+ provider_active_reservations
+ proposed_provider_reservation
    <= verified_eligible_provider_balance

project_settled
+ project_active_reservations
+ proposed_reservation
    <= applicable_cumulative_tier_stop
```

All invariant terms use the frozen conservative USD-equivalent conversion.
Any tax, fee, or FX exposure not covered by credits enters both the
provider/project worst-case reservation and an explicit cash-liability field;
nominal credit coverage alone is insufficient.

7. verify the spend-ledger digest;
8. hash the exact action manifest;
9. obtain the repository's one-use approval for that exact hash;
10. append the reservation before resource creation;
11. start the independent multi-resource watchdog, which refuses admission when
    current usage plus all in-flight worst cases plus proposed work would cross
    any frozen compute, storage, network, log, endpoint, request, or API billing
    cap; and
12. append settlement and release the unused reservation only after
    artifact-copy, compute/network teardown, and final storage-deletion
    receipts pass, or after the remaining frozen retention horizon is fully
    reserved.

Budget alerts do not enforce a stop. Batch timeouts and pool/compute-environment
maxima are defense in depth, not the hard-stop authority: provider timeout
termination can be best-effort and does not prove detached sibling cleanup.
The independent lease watcher plus provider teardown verification is the
hard-stop path. A Spot eviction, capacity substitution, TP/context change,
extra retry, added node, or provider substitution is not an implicit retry
unless its exact behavior was already frozen; otherwise it needs a newly
priced, hashed, and approved action.

The current state is:

- verified eligible AWS balance: $0;
- verified eligible Azure balance: $0;
- verified eligible OpenAI balance: $0;
- verified eligible Anthropic balance: $0;
- settled economic cost: $0; and
- active reservation: $0.

Pending credits do not bypass the gate. Broad autonomy is not silently converted
into approval of an unknown future hash.

## 16. Kill and pivot rules

Before confirmation, stop or narrow if:

- fewer than 120 eligible tasks remain in either benchmark;
- trigger opportunity is below 60%;
- gold/regression flakiness exceeds 2%;
- snapshot restoration differs in any arm-visible byte/token/state;
- REAL correctness or SHAM collision validation fails;
- packet detectability exceeds its gate;
- differential infrastructure failure exceeds two percentage points;
- measured p10 throughput cannot finish confirmation by 2026-08-18;
- the P0 simulator reports less than 80% power for the registered target effect
  at `C120`; or
- verified eligible funding cannot cover the exact worst case.

The zero-credit fallback is a methods-and-feasibility paper built from the
validated local controller, synthetic recovery experiments, the existing G1
negative evidence, and a clearly labeled small 9B pilot. It must not masquerade
as the powered cross-benchmark result.

Terminal-Bench 2.1 at
`5c8eadf1f393183288fa08b8f73ca9a469cc5e00` is the first robustness fallback:
it is objective, Apache 2.0, operationally clean, and has 89 tasks. It is not
primary because the unit ceiling and frontier saturation weaken power.

## 17. Schedule

| dates | irreversible output |
| --- | --- |
| Jul 28–30 | design, novelty ledger, exact revisions, implementation plan |
| Jul 30–Aug 3 | schemas, registry, power simulator, assignment, synthetic model |
| Aug 2–6 | SWE/τ³ adapters, snapshot forks, verifier/SHAM builder, failure tests |
| Aug 5–7 | local 9B pilot, detectability and artifact audit |
| Aug 7–8 | freeze dependencies, preregistration, task roster, analysis hash |
| Aug 8–10 | eligible Tier-1 cloud parity/throughput only |
| Aug 10–18 | confirmation and any pre-unblinding replication |
| Aug 18–21 | artifact completeness, unblind, analysis, robustness |
| Aug 21–25 | 4–9 page paper, supplement, anonymous release bundle |
| Aug 25–27 | independent red team, clean-clone reproduction, PDF inspection |
| Aug 28 | submission target and one-day failure buffer |
| Aug 29 | emergency-only venue buffer; no new scientific degrees of freedom |

## 18. Sources of record

- Workshop:
  `https://who-verifies-the-agents.github.io/`
- SWE-bench-Live:
  `https://swe-bench-live.github.io/`
- SWE-bench-Live MultiLang:
  `https://huggingface.co/datasets/SWE-bench-Live/MultiLang`
- τ³-bench v1.0.1:
  `https://github.com/sierra-research/tau2-bench/tree/v1.0.1`
- Qwen3.6 model card:
  `https://huggingface.co/Qwen/Qwen3.6-35B-A3B`
- Terminal-Bench 2.1 fallback:
  `https://www.tbench.ai/news/terminal-bench-2-1`
- Current pricing sources and observations:
  `docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md`
- AWS EC2 Spot price-history contract:
  `https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeSpotPriceHistory.html`
- AWS ECR private-endpoint requirements and PrivateLink pricing:
  `https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html`;
  `https://aws.amazon.com/privatelink/pricing/`
- AWS Batch compute-environment terminal-state behavior:
  `https://docs.aws.amazon.com/cli/latest/reference/batch/describe-compute-environments.html`
- AWS Batch timeout best-effort behavior:
  `https://docs.aws.amazon.com/batch/latest/userguide/job_timeouts.html`
- AWS Budgets delay/advisory behavior:
  `https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html`
- Azure Batch NVMe/start-task contracts:
  `https://learn.microsoft.com/en-us/azure/batch/batch-nvme-temporary`;
  `https://learn.microsoft.com/en-us/python/api/azure-batch/azure.batch.models.starttask`
- Azure Batch Spot, capacity, and VM-size contracts:
  `https://learn.microsoft.com/en-us/azure/batch/batch-spot-vms`;
  `https://learn.microsoft.com/en-us/azure/batch/batch-capacity-planning`;
  `https://learn.microsoft.com/en-us/azure/batch/batch-pool-vm-sizes`
- Azure NCads A100 v4 availability notice:
  `https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/nca100v4-series`
- Azure Container Registry SKU/retention limits:
  `https://learn.microsoft.com/en-us/azure/container-registry/container-registry-skus`;
  `https://learn.microsoft.com/en-us/azure/container-registry/container-registry-retention-policy`

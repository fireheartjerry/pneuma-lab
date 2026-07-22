# 04 — Benchmark Specification

Status: planning. Inherits every decision in `02-research-thesis.md` §8 (Locked
Design Constants); where §8 fixes a constant, this document only elaborates it and
never contradicts it. Any deviation is recorded in `15-decision-log.md`.

Scope reminder: this is a **planning** document. Nothing here authorizes a
download, conversion, training run, or experiment. Every data lane referenced
below remains `training_weight: 0.0` / `not_authorized` until a human signs an
authorization manifest. On-disk paths are read-only provenance references, not
instructions to write.

This document specifies the two benchmark suites, the failure taxonomy, and the
per-motif realization/detection/holdout mapping that the primary metric (`RUF`,
defined in `08-metrics-and-statistics.md`) is computed over. It is the concrete
contract between the data inventory (`audit-data-inventory.md`), the extraction
layer (`audit-adapters.md`), and the split/governance layer
(`audit-converters.md`).

---

## 1. Design goal and the two-suite split

The primary hypothesis (H1) is a **cross-task** claim: does persistent internal
state reduce the rate at which an agent commits the **same underlying failure**
again after it has already committed it once? A benchmark for that claim must
supply _sequences_ of tasks in which the _same failure motif_ can recur, with a
ground-truth notion of "same underlying failure" that is not gameable and not a
byte-identity artifact.

No single existing corpus supplies both (a) exact, oracle-backed motif ground
truth _and_ (b) a realistic, in-the-wild recurring-failure distribution. So the
benchmark is deliberately two suites with complementary roles:

| Suite                               | Role                                                                                                                           | Ground-truth quality                 | Realism                                       | Primary claims served                                           |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------ | --------------------------------------------- | --------------------------------------------------------------- |
| **A — Synthetic controlled-motif**  | Internal-validity spine. Exact motif ground truth, exact repeat structure, controlled surface variation, deterministic oracle. | **Exact** (constructed)              | Low–medium (injected bugs into real repos)    | H1, H2, H4 (surface + motif holdout), H5 (counterfactual tasks) |
| **B — Real-repo recurring-failure** | External-validity check. In-the-wild motif distribution from recorded agent trajectories.                                      | Approximate (N-judge / rule-labeled) | High (real agents, real repos, real failures) | H1, H4 (repo holdout), robustness/generalization                |

The paper's headline number is reported on **both** suites; Suite A carries the
causal/clamp experiments (H2) because only it has a deterministic oracle and a
byte-reproducible paired runner, and Suite B demonstrates the effect is not an
artifact of synthetic construction. A result that holds on A but vanishes on B is
reported honestly as a synthetic-only effect (this is a pre-registered
falsification mode of H4).

Both suites emit the **same** per-step frame vocabulary (`AgentTraceFrame` from
`src/pneuma_lab/adapters/trajectory.py`) so the evaluator, the failure detector,
and the metric code are identical across suites — the only difference is
provenance and label source.

---

## 2. Suite A — Synthetic controlled-motif suite

### 2.1 Role

Suite A is the internal-validity spine. Because we _construct_ every failure, we
know the exact motif each task can elicit, we control how many later tasks repeat
that motif, we control the surface form independently of the motif, and we have a
deterministic pass/fail oracle. This makes Suite A the only place the
deterministic paired `control/treated/null` runner
(`src/pneuma_lab/interventions/runner.py`, `PairedReplayRunner`) can be reused
verbatim with `sha256` byte-equality nulls — satisfying §8.8's
"deterministic-oracle sub-experiments" clause.

### 2.2 Exact data source and on-disk location

Seed corpus = **task-only** SWE specs with a known-correct oracle (issue text +
gold patch + test patch + `FAIL_TO_PASS`/`PASS_TO_PASS` lists), chosen because
they are clean, permissively usable, and carry no trajectory noise:

| Seed source        | On-disk location (`C:\pneuma-data\raw\`) | Rows             | Kind                           | Adapter                               |
| ------------------ | ---------------------------------------- | ---------------- | ------------------------------ | ------------------------------------- |
| **SWE-Gym-Raw**    | `swe-gym/` (→ `processed/swe-gym/`)      | 64,689           | task-only (issue + gold patch) | `swe_gym_lite.py` pattern (task-only) |
| **SWE-Gym-Lite**   | `swe-gym/`                               | 230              | task-only difficulty subset    | `swe_gym_lite.py` (built, task-only)  |
| **SWE-bench-Lite** | `swe-bench/`                             | subset of 22,962 | task + gold patch (eval-grade) | task-only adapter (planned)           |

The oracle for each seed is the gold patch + test patch: applying the gold patch
must flip `FAIL_TO_PASS` tests to pass while keeping `PASS_TO_PASS` green. That
oracle is what makes an injected motif's ground-truth label _exact_.

Note on SWE-bench-Lite: it is normally reserved as held-out **eval** material and
must never be used to _train_ the subject model (per the leakage rules in §6).
Here it is used only as a _clean-repo template_ for injection; the injected bug and
its fix are synthetic, so this does not contaminate the subject model as long as
Suite A instances are never fed into any training lane (all lanes stay
`training_weight: 0.0` regardless).

### 2.3 What a task is (Suite A)

A **Suite-A task** is a tuple:

```
(clean_repo_snapshot @ base_commit,
 injected_motif_id,
 injected_bug_patch,          # deterministic transform producing the failing state
 oracle_fix,                  # the known-correct repair (motif-specific)
 test_oracle,                 # FAIL_TO_PASS/PASS_TO_PASS derived from the seed
 surface_variant_id,          # controls identifier/comment/order surface form
 difficulty_tier)
```

Construction: start from a clean seed repo where the gold patch already passes
(oracle green). Apply an `injected_bug_patch` that deterministically introduces a
_known_ motif (e.g. a wrong-file edit target, a broken global invariant, an
off-by-one that overfits one test). The resulting repo state fails a defined test
in a defined way. The agent's task is to fix the _observed_ failure; success is
defined by the deterministic `test_oracle`. Because we authored the bug, the
motif label is exact and the "correct behaviour" is known.

### 2.4 How tasks become SEQUENCES with recurring motifs

A **task sequence** is an ordered list of Suite-A tasks presented to the agent
under one persistent-state session. Recurrence is engineered on two independent
axes:

- **Motif recurrence axis.** A motif `m` is instantiated in tasks at positions
  `p_1 < p_2 < ... < p_k` in the sequence. The _first_ instance `p_1` is the
  _exposure_; instances `p_2..p_k` are _post-exposure_ and are where `RUF` is
  measured (fraction of post-exposure instances on which the same underlying
  failure recurs). Interleaving distractor motifs between recurrences prevents a
  trivial "just did this" adjacency shortcut.
- **Surface-variation axis.** Each recurrence of `m` uses a _different_
  `surface_variant_id`: different repo template, renamed identifiers, reordered
  functions, reworded issue text, different file paths — so a later instance is
  the _same motif_ but _not the same surface content_. This is what forces H4
  (generalization) rather than identifier memorization.

The pair (motif fixed, surface varied) is the core experimental unit: the state
must recognize the _underlying_ failure structure across surface change.

### 2.5 What is a failure / a repeated failure / structural similarity (Suite A)

- **Failure (single task):** the deterministic oracle is not satisfied — i.e. the
  agent's final repo state does not flip `FAIL_TO_PASS` to pass (or breaks a
  `PASS_TO_PASS`). Because the oracle is exact, per-task failure is unambiguous.
- **Motif-specific failure:** the failure occurs _via the injected motif's causal
  mechanism_. Since we authored the bug and the motif-specific fix, we can check
  whether the agent's trajectory exhibits the motif's observable indicators
  (§4) — e.g. it edited the wrong file, or it re-ran the byte-identical broken
  command. A task can fail without exhibiting motif `m`; only failures that match
  `m`'s indicators count toward `RUF(m)`.
- **Repeated failure:** a post-exposure instance of motif `m` on which the agent
  again fails _via `m`'s mechanism_, after having been exposed to `m` earlier in
  the sequence. This is the numerator of `RUF`.
- **Structurally-similar (not identical) failure:** because Suite A varies surface
  form while holding the motif's causal label constant, two instances of `m` are
  by construction structurally similar but not surface-identical. The label
  "structurally similar" is therefore _assigned by construction_ — it equals
  `injected_motif_id` equality with `surface_variant_id` inequality. This is the
  cleanest possible operationalization of the metric's "structurally-similar"
  qualifier and is why Suite A anchors H1/H2.

### 2.6 Leakage prevention (Suite A)

Suite A injects synthetic bugs, so the _bug_ cannot leak from any training corpus.
The residual leakage risk is the _repo template_: a repo whose real trajectories
appear in Suite B (or in a training lane) must not appear in the Suite-A test
split at the same time. The 7 quarantined overlapping repos (§6) are therefore
**excluded from Suite-A test-split templates** and pinned to a single split, so a
template never straddles train/test across suites. Suite A additionally holds out
whole **motif families** on the motif axis (§7).

### 2.7 Splits, difficulty, surface variation, budget, reproducibility (Suite A)

- **Splits (repository AND motif).** Repo-axis splitting reuses
  `src/pneuma_lab/training/splits.py` (atomic repo-grouped assignment, 70/15/15,
  deterministic `sha256(dataset_id|repo|repo)` ordering, `_repo_overlap`
  self-check). **Motif-axis splitting does not exist today and is a BUILD** (see
  `audit-converters.md` §2: `split_group` has no motif field and no code groups by
  motif). The build adds a `motif_id` to `split_group` and a parallel
  `_group_examples_by_motif` so a held-out _motif family_ can be reserved for the
  test split (H4 motif-transfer). Repo-axis and motif-axis holdouts are crossed:
  the strictest test cell is _held-out repo × held-out motif_.
- **Difficulty control.** `difficulty_tier` is set by seed-task difficulty
  (SWE-Gym-Lite is the curated hard subset) crossed with motif recoverability
  (§4): a hard tier uses a subtle motif (e.g. `local-fix-breaks-global-invariant`)
  in a large repo; an easy tier uses an obvious motif (e.g. `wrong-file-edit`) in
  a small repo. Difficulty is a stratification variable, reported per-tier, never
  a confound left uncontrolled between arms.
- **Surface-form variation.** Independent `surface_variant_id` axis (§2.4):
  identifier renaming, comment rewording, function reordering, file-path renaming,
  issue-text paraphrase. Surface transforms are held-out for the transfer test —
  some transforms appear only in the test split (per §8.9 "held-out surface
  transforms").
- **Budget normalization.** All four conditions share identical token, step, and
  wall-clock caps and the identical retry cap (§8.1/§8.2). E-0 (`e0-results.md`)
  showed a length/activity confound can dominate, so budgets are matched _per
  task_ and logged; any arm that exhausts budget records a truncation reason.
- **Reproducibility binding (commit + config + seed).** Every Suite-A artifact is
  bound by the existing hash-manifest convention (`hash_manifest.json`,
  self-hashing canonical JSON) extended per `audit-converters.md` §6 to bind
  `code_commit` (git SHA), the run config (model checkpoint id, decode temp,
  budgets, retry cap), the RNG `seed`, the seed-corpus source SHAs, and the
  injected-bug generator version. Byte-reproducibility of the deterministic oracle
  runs is enforced by the `PairedReplayRunner`'s `sha256(outputs_A) ==
sha256(outputs_B)` null.

---

## 3. Suite B — Real-repo recurring-failure suite

### 3.1 Role

Suite B is the external-validity check: it shows the H1 effect on _real_ recorded
agent trajectories over _real_ repositories with _real_ failures, so the result is
not a synthetic-construction artifact. Because there is no deterministic oracle
per task, Suite B does not carry the byte-equality causal null; it carries the
_statistical_ causal path (§8.8) — frozen seeds/prompts/memory + N-sample
distributional nulls — and the repo-axis holdout for H4.

### 3.2 Exact data sources and on-disk locations

| Source                                     | Location (`C:\pneuma-data\raw\`)               | Rows / steps                                           | Role in Suite B                                                | Adapter                                                                                           |
| ------------------------------------------ | ---------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **Open-SWE-Traces** (primary)              | `open-swe-traces/` (84 parquet shards, ~18 GB) | 207,489 traces / 14.1M steps; 160,731 valid after skip | Primary real recurring-failure distribution                    | `open_swe_traces.py` (built, digest-only; shard-0 = 1,960 ex converted; full 84-shard run un-run) |
| **SWE-Gym OpenHands-Sampled** (complement) | `swe-gym/` (3 parquet)                         | 6,055 traces / 114,461 steps                           | Python-only dense-failure complement; **real harness outcome** | `openhands_sampled.py` (built; split 3803/1208/1044)                                              |

Why this pair and not others (from `audit-data-inventory.md` §3, §6):

- **Open-SWE-Traces** is the strongest real-trajectory corpus: 2,654 repos, 7
  languages, `resolved ∈ {-1,0,1}`, ~41% resolved among convertible rows
  (balanced), and — critically — the _same underlying SWE-rebench-V2 task attempted
  by 2 models × 2 harnesses_, which yields multiple trajectories per task and a
  _natural recurring-failure distribution_. CC-BY-4.0; digest-only conversion means
  no PII/licensing exposure.
- **SWE-Gym OpenHands-Sampled** complements it with a **real harness outcome**
  (`resolved` + a five-flag `report`: `resolved`, `empty_generation`,
  `error_eval`, `failed_apply_patch`, `test_timeout`) — the _trustworthy_ outcome
  surface that anchors label validation. Its 8.1% resolve rate (491 pass / 5,564
  fail) makes the unresolved set a dense repeated-failure population.
- **Explicitly excluded** from Suite B: SWE-Gym **Verifier** (all 5,272 traces are
  _single-step_ — cannot support intra-trace sequences, per `audit-adapters.md`
  §2); SWE-EVO (only ~48 task core, heavy overlap); Multi-SWE-bench trajs (locked
  in per-language ZIPs, unextracted); SWE-chat / SEC-bench-Pro / Dialogue-SWE-Bench
  (policy-blocked: PII / dual-use / archived).

### 3.3 What a task is (Suite B)

A **Suite-B task** is a real SWE-rebench-V2 / SWE-Gym instance (`instance_id`,
repo, `base_commit`, objective digest). A **trajectory** is one recorded agent run
over that instance (chat + tool_calls), carrying `resolved` and, in the sampled
lane, the five-flag `report`. Multiple trajectories per task (different
model/harness/sample) are the raw recurring-failure material.

### 3.4 How tasks become SEQUENCES (Suite B)

Suite B has two sequence modes, because real data does not hand us a pre-ordered
per-agent curriculum:

1. **Cross-attempt recurrence (native).** For one underlying task, the multiple
   recorded attempts (2 models × 2 harnesses in Open-SWE; multiple samples in
   Sampled) already exhibit the _same task failing repeatedly_ across independent
   agents. This is a per-task recurring-failure micro-distribution used to _mine_
   which motifs recur and to _validate_ the failure detector, but it is not a
   single-agent longitudinal sequence.
2. **Constructed longitudinal sequence (for the H1 run).** For the actual H1
   comparison we build a _task sequence_ by selecting real instances that share a
   _mined motif label_ (§4) and ordering them (exposure first, post-exposure
   later, distractors interleaved), then re-running our _own_ four conditions over
   that sequence with our seed-pinned scaffold (§8.1). The historical trajectories
   are used to _label motifs and pick the sequence_; the measured behaviour is our
   own agents', not the corpus authors'.

Sequence mode 2 is what `RUF` is computed over; mode 1 is the labeling/validation
substrate. This mirrors §8.5's "natural recurring-failure distribution" language
and keeps the outcome measurement on _our_ controlled arms.

### 3.5 What is a failure / repeated failure / structural similarity (Suite B)

- **Failure (single task):** for the _mining_ pass, the recorded `resolved` label
  — but **only the sampled lane's harness `report` is treated as ground truth**;
  Open-SWE outcomes are `constructed_label` (synthetic automated verifier) and are
  labeled as such, never asserted as harness truth (`audit-adapters.md` §5.7). For
  the _H1 run_ pass, failure is our own scaffold's oracle result on the instance's
  tests.
- **Repeated failure:** a post-exposure instance of a mined motif `m` on which our
  agent again fails via `m`'s indicators (§4), after exposure to `m` earlier in
  the constructed sequence.
- **Structurally-similar failure labeling.** Unlike Suite A, "same motif" is _not_
  known by construction — it is _inferred_. Two real failures are labeled the same
  motif when (a) an automated rule matches identical motif indicators (§4) _and_
  (b) an **N-judge ensemble** (§8.9, `10-anti-gaming-specification.md`) agrees at a
  pre-registered majority threshold. The ensemble labels are frozen before the H1
  run and bound into the artifact hash. Byte-identity (`args_digest` equality) is
  _insufficient_ on its own — it only catches contiguous exact repeats and misses
  the same error class reached via a different command (`audit-adapters.md` §3).

### 3.6 Leakage prevention (Suite B) — the 7 quarantined repos

Open-SWE-Traces and SWE-Gym OpenHands-Sampled are **NOT disjoint**: per the
committed `docs/data/training-readiness/cross-dataset-leakage-registry.json`
(status: populated), **7 of the sampled lane's 11 repos overlap Open-SWE-Traces**
(63.6% of the sampled lane). The 7 quarantined repos are:

1. `conan-io/conan`
2. `dask/dask`
3. `facebookresearch/hydra`
4. `getmoto/moto`
5. `iterative/dvc`
6. `modin-project/modin`
7. `pandas-dev/pandas`

These 7 repos are quarantined to a **single split** (never split across
train/dev/test between the two lanes), enforced by the corpus manifest's
`quarantine.repos == leakage overlap set` invariant (`validate_corpus`,
`audit-converters.md` §3). Additional leakage controls: SWE-EVO is flagged as a
severe further overlap and excluded; Open-SWE carries SWE-rebench-V2 lineage, so
SWE-bench / SWE-bench-Pro / SWE-MERA are held out of any training lane to remain
valid eval; the registry currently covers only the D1×D2 pair, so any new lane
pairing must be computed before use. The registry canonicalizes repos to
`sha256:` digests so the digest-only Open-SWE lane can be compared without exposing
raw repo names.

### 3.7 Splits, difficulty, surface variation, budget, reproducibility (Suite B)

- **Splits (repository AND motif).** Repo axis: `splits.py` atomic repo grouping,
  with the 7 quarantined repos pinned. Motif axis: same **BUILD** as Suite A
  (`motif_id` into `split_group`); held-out motif families reserved for test. The
  strictest cell again is held-out repo × held-out motif.
- **Difficulty control.** Stratify by repo size, language (7 languages in
  Open-SWE), and trajectory length (median 14 steps sampled; up to 50). Report
  per-stratum; the multilingual axis is a robustness stratum, not a headline.
- **Surface-form variation.** Real data supplies natural surface variation for
  free (different repos/files/wording realize the same motif). No synthetic
  surface transform is applied; instead the held-out _repo_ provides the surface
  novelty for H4.
- **Budget normalization.** Identical caps across all four arms (§8.1), matched
  per task; historical trajectories' lengths are _not_ used as budgets — our
  scaffold's caps are fixed independently to avoid the E-0 length confound.
- **Reproducibility binding.** Same commit+config+seed binding as Suite A, plus
  the frozen N-judge motif labels, the frozen `hf_revision` (envelope
  `derive_ids` is content-addressed over `dataset\x00instance_id\x00hf_revision`),
  and the frozen retrieved-memory / frozen-prompt transcripts required by the
  statistical causal path (§8.8). Open-SWE label provenance is stamped
  `constructed_label @ confidence: medium`, never `harness_outcome`.

---

## 4. Failure taxonomy (~12 motifs) — DL-07

The taxonomy is the ground-truth vocabulary for `RUF`. Every motif has: an id, the
observable indicators a detector reads, a causal label (the underlying mistake),
severity, recoverability, task-specific-vs-general scope, the automated-rule /
N-judge detection method, and how a _later_ task re-instantiates the motif
_without duplicating surface content_.

**Hard dependency (from `audit-adapters.md` §3, §5 and audit doc 01 §2/§3):** the
shipped extraction (`trajectory.py`) exposes exactly **three crude per-step
proxies** — `error_marker` (a single lexical regex boolean), `retry_count`
(contiguous byte-identical action only), and `strategy_switches` (tool-set change
count). Arguments and tool outputs are **digested away** (`args_digest`,
`content_sha256`), which destroys **error-class identity, file identity, and
test-id identity**. Therefore _most_ of the taxonomy below is **not detectable
today** and depends on **enriching `trajectory.py`** (§5). The taxonomy is
specified against the _enriched_ signals; §5 says exactly what must be added and
why.

### 4.1 Motif table

| #   | Motif id                            | Observable indicators (enriched)                                                                                                                   | Causal label                                 | Severity | Recoverable?    | Scope         | Detection: rule / N-judge                                                                                                  |
| --- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | -------- | --------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 1   | `wrong-file-edit`                   | edit tool targets a `norm_path` not in the failing test's implicated file set; tests unchanged after edit                                          | Acted on the wrong location                  | High     | Yes (re-target) | General       | Rule: `norm_path ∉ implicated_paths`. N-judge confirms intent.                                                             |
| 2   | `local-fix-breaks-global-invariant` | a `PASS_TO_PASS` test flips to fail after an edit that fixed the target; new `error_class` appears elsewhere                                       | Fixed locally, broke a global contract       | High     | Partial         | General       | Rule: prior-green test → fail post-edit. N-judge confirms causal link.                                                     |
| 3   | `retry-broken-strategy`             | ≥N steps sharing the same `error_class` on the same `test_id`/`norm_path`, possibly via _different_ commands                                       | Persisted with a strategy that keeps failing | High     | Yes             | General       | Rule: repeated `(error_class,test_id)` across steps (not byte-identity). N-judge for "same strategy".                      |
| 4   | `ignore-failing-tests`              | a `finish`/`submit` action while the latest observation still carries an unresolved `error_class` on a target test                                 | Declared done over a live failure            | High     | Yes             | General       | Rule: submit-with-open-failure. N-judge confirms the failure was salient.                                                  |
| 5   | `stale-assumption`                  | edits/commands consistent with a repo fact contradicted by an earlier observed `error_class` (e.g. API renamed)                                    | Acted on an outdated belief                  | Medium   | Yes             | Task-specific | N-judge primary; rule flags contradiction between an observed error and a later assumption.                                |
| 6   | `overwrite-user-change`             | edit whose `norm_path` matches a file the world/reference marks as user-modified; reference divergence increases                                   | Clobbered protected/user content             | High     | Partial         | General       | Rule: edit ∩ protected-path set. N-judge confirms non-accidental.                                                          |
| 7   | `premature-destructive-action`      | destructive tool (`rm`, force reset, mass-delete) before any diagnostic read/test step                                                             | Irreversible action before understanding     | Critical | No              | General       | Rule: destructive tool token before first `run_tests`/read. N-judge confirms prematurity.                                  |
| 8   | `single-error-overfit`              | fix that makes exactly one `FAIL_TO_PASS` pass while a sibling target of the same class still fails                                                | Overfit to one symptom                       | Medium   | Yes             | Task-specific | Rule: partial `FAIL_TO_PASS` resolution, same `error_class` remains. N-judge confirms overfit.                             |
| 9   | `skip-verification`                 | `finish`/`submit` with zero `run_tests` observations in the trajectory (or none after the last edit)                                               | Shipped without verifying                    | Medium   | Yes             | General       | Rule: no test observation post-last-edit. Pure rule (no judge needed).                                                     |
| 10  | `misread-repo-structure`            | repeated `error_class = ModuleNotFound/ImportError/FileNotFound` on wrong `norm_path`s; search/list thrash (`strategy_switches` high, no progress) | Wrong mental model of the tree               | Medium   | Yes             | Task-specific | Rule: import/path `error_class` + high `strategy_switches`. N-judge confirms structural misread.                           |
| 11  | `unavailable-tool-loop`             | repeated identical `error_class` = tool-not-found / permission / env-missing across ≥N steps                                                       | Looping on an unavailable capability         | Medium   | Yes             | General       | Rule: repeated env/tool `error_class`. Pure rule.                                                                          |
| 12  | `claim-success-without-evidence`    | assistant text asserts success while no observation shows tests passing / no `error_class=none` confirmation                                       | Confabulated success                         | High     | Yes             | General       | Rule: success-claim token without a passing-test observation. N-judge confirms the claim. Ties to the confab-risk measure. |

Severity legend: `Critical` = irreversible/data-loss; `High` = fails the task or a
protected contract; `Medium` = wastes budget / partial failure. Recoverability =
whether, within the same task, the agent can still reach success after committing
the motif.

### 4.2 How later tasks re-instantiate a motif without duplicating surface content

For each motif the recurrence mechanism is _motif-structural, surface-independent_:

- **Suite A (by construction):** the `injected_bug_patch` for motif `m` is a
  _parameterized transform_, not a fixed diff. A later task applies the _same
  transform_ to a _different_ clean repo template with a _different_
  `surface_variant_id` — so the causal mechanism (wrong-file target, broken
  invariant, over-fit test) is identical while file names, identifiers, ordering,
  and issue wording all differ. "Same motif, new surface" is guaranteed, not
  hoped-for.
- **Suite B (by mining):** later instances are _different real tasks_ whose mined
  motif label equals `m` (rule + N-judge agreement) but which live in different
  repos/files/languages. Surface novelty is intrinsic because the tasks are
  genuinely different; the shared thing is only the abstract motif.

In both suites the evaluator sees the motif label, never the surface — so an agent
cannot "pass" by memorizing surface tokens, which is exactly the H4 test.

---

## 5. Required enrichment of `trajectory.py` (foundational, privacy-safe)

The taxonomy in §4 is **not detectable from today's frames**. The current
per-step frame ships only `error_marker` (lexical bool), `retry_count`
(byte-identical contiguous only), and `strategy_switches` — and it digests
arguments and outputs, destroying error-class, file, and test identity
(`audit-adapters.md` §3). Because args/outputs are digest-only _in the frames_,
any richer signal **must be extracted inside `trajectory.py` at build time from
the raw text** — it _cannot_ be recovered downstream. This is an architectural
constraint, so the enrichment is a foundational task on the critical path.

### 5.1 New per-step signals to extract (privacy-safe)

Each new field is a _bounded token or normalized identifier_, never raw text —
preserving the digest-only / no-raw-text invariant that the `consistency_errors`
gate and the five "raw text never reaches frames" tests enforce
(`audit-adapters.md` §1).

| New field     | What it is                                                                                                                                                                                                                                                   | Why it is needed                                                                                                                                                              | Privacy-safety                                                               |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `error_class` | A **normalized error-class token** from a fixed closed vocabulary (e.g. `AssertionError`, `ImportError`, `ModuleNotFound`, `SyntaxError`, `Timeout`, `ApplyPatchFail`, `ToolNotFound`, `PermissionDenied`, `none`) parsed from the observation at build time | Distinguishes _same error class_ from _different error_ — the core of motifs 2,3,5,8,10,11 and the entire "same underlying failure" notion. `error_marker` (one bool) cannot. | Closed vocabulary token only; no free text, no stack contents, no user data. |
| `norm_path`   | A **normalized, repo-relative file-path identity** for each edited/read/tested file (path only, hashed against a per-run salt if the path itself is sensitive)                                                                                               | "Same file re-edited", "wrong file", "protected file" — motifs 1,6,10. `args_digest` only catches byte-identical args.                                                        | Path structure only; no file contents; salted-hash option for private paths. |
| `test_id`     | A **normalized test identifier** (e.g. `pkg/test_x.py::test_y`) for each test referenced/run                                                                                                                                                                 | "Same test failed twice", partial `FAIL_TO_PASS` resolution — motifs 3,8.                                                                                                     | Identifier only; no test body, no assertion values.                          |

Derived cross-step comparators (computed from the three fields, still in
`trajectory.py` or the metric layer):

- `same_class_recurrence`: a later step shares `(error_class, test_id)` or
  `(error_class, norm_path)` with an earlier step even if the _command differs_ —
  the true "repeated failure" signal `retry_count` cannot express.
- `implicated_paths` / `implicated_tests`: the file/test set a task's oracle
  points at, so `wrong-file-edit` and `ignore-failing-tests` become rule-checkable.

### 5.2 Why lexical `error_marker` is insufficient (validation requirement)

`error_marker` fires on the words error/traceback/exception/failed/failure and so
false-positives on prose like "no errors found" (`audit-adapters.md` §5.6). Before
`error_class` grounds a published metric, its precision/recall on real tool output
must be measured against the sampled lane's trustworthy five-flag `report`
(`resolved`, `empty_generation`, `error_eval`, `failed_apply_patch`,
`test_timeout`). The taxonomy's rule-based detectors are only as trustworthy as
`error_class`, so this validation is a pre-registered gate, not an afterthought.

### 5.3 What stays out (honesty invariant preserved)

No confidence, plan, affect, or any psyche-internal signal is extracted from
trajectories (the honesty rule). No raw argument, output, patch, or objective text
enters a frame. The enrichment adds only _typed observable identifiers_, keeping
the corpus publishable without PII/licensing exposure and keeping the
`consistency_errors` gate intact.

---

## 6. Leakage, splits, and reproducibility — consolidated

- **Repo axis (exists):** `splits.py` atomic repo-grouped 70/15/15, deterministic,
  hash-bound, self-checking (`_repo_overlap`). Reused as-is for both suites.
- **Motif axis (BUILD):** add `motif_id` to `split_group` + a motif-grouped
  assignment so a held-out motif family is reserved for test. Does **not** exist
  today (`audit-converters.md` §2). Crossed with the repo axis: held-out repo ×
  held-out motif is the strictest generalization cell (H4).
- **7-repo quarantine (exists):** the populated cross-dataset leakage registry
  pins `conan-io/conan, dask/dask, facebookresearch/hydra, getmoto/moto,
iterative/dvc, modin-project/modin, pandas-dev/pandas` to a single split;
  `validate_corpus` enforces `quarantine.repos == overlap set`.
- **Eval isolation (exists):** SWE-bench / SWE-bench-Pro / SWE-MERA held out of all
  training lanes; SWE-Gym Verifier / SWE-chat / SEC-bench-Pro / Dialogue-SWE-Bench
  excluded (single-step / policy).
- **Reproducibility binding (exists + extend):** `hash_manifest.json` self-hashing
  convention + `verify_estimator_run`-style commit/config/source/split binding,
  extended to bind the **subject checkpoint SHA**, the **RNG seed**, the
  **injected-bug generator version** (Suite A), and the **frozen N-judge motif
  labels** (Suite B). Every artifact reproducible from commit + config + seed.
- All lanes remain `training_weight: 0.0` / `not_authorized`; the paper trains no
  subject-model weights (§8.5).

---

## 7. Motif → suite → detection → holdout mapping

This table binds each motif to which suite(s) can realize it, how it is detected,
and which axis it is held out on. "Realizable" means the suite can produce
labeled instances of the motif at the ground-truth quality that suite provides.

| #   | Motif id                            | Suite A (synthetic)            | Suite B (real)                       | Detection method                                            | Holdout axis                     |
| --- | ----------------------------------- | ------------------------------ | ------------------------------------ | ----------------------------------------------------------- | -------------------------------- |
| 1   | `wrong-file-edit`                   | Yes (inject wrong-target)      | Yes (mined)                          | Rule (`norm_path ∉ implicated_paths`) + N-judge             | repo × motif × surface           |
| 2   | `local-fix-breaks-global-invariant` | Yes (inject invariant break)   | Yes (mined)                          | Rule (`PASS_TO_PASS` flip) + N-judge                        | repo × motif                     |
| 3   | `retry-broken-strategy`             | Yes (motif recurs in seq)      | Yes (native cross-attempt)           | Rule (`same_class_recurrence`) + N-judge                    | motif × surface                  |
| 4   | `ignore-failing-tests`              | Yes (oracle-defined)           | Yes (mined)                          | Rule (submit-with-open-failure) + N-judge                   | repo × motif                     |
| 5   | `stale-assumption`                  | Partial (inject renamed API)   | Yes (mined)                          | N-judge primary + contradiction rule                        | repo × motif                     |
| 6   | `overwrite-user-change`             | Yes (mark protected path)      | Partial (needs protected-path label) | Rule (edit ∩ protected) + N-judge                           | repo × motif                     |
| 7   | `premature-destructive-action`      | Yes (inject tempting shortcut) | Yes (mined, rare)                    | Rule (destructive-before-diagnostic) + N-judge              | motif (rare → report separately) |
| 8   | `single-error-overfit`              | Yes (multi-target oracle)      | Yes (mined)                          | Rule (partial `FAIL_TO_PASS`) + N-judge                     | motif × surface                  |
| 9   | `skip-verification`                 | Yes (oracle-defined)           | Yes (native)                         | Pure rule (no test post-edit)                               | repo × motif                     |
| 10  | `misread-repo-structure`            | Yes (obfuscate tree)           | Yes (mined)                          | Rule (import/path `error_class` + thrash) + N-judge         | repo × motif                     |
| 11  | `unavailable-tool-loop`             | Yes (restrict tool in env)     | Yes (mined)                          | Pure rule (repeated env `error_class`)                      | motif                            |
| 12  | `claim-success-without-evidence`    | Yes (oracle contradicts claim) | Yes (mined)                          | Rule (claim w/o passing obs) + N-judge; ties to confab-risk | repo × motif                     |

Notes: "Pure rule" motifs (9, 11) need no N-judge because they are mechanically
unambiguous once `error_class` exists; all others use the rule as a _high-recall
prefilter_ and the N-judge ensemble as the _precision gate_, with labels frozen
before the H1 run and bound into the artifact hash (anti-gaming, §8.9). Motif 7 is
expected to be rare in Suite B and is reported separately rather than pooled, to
avoid a low-`n` cell distorting the aggregate `RUF`.

---

## 8. Open build items (tracked, not authorizations)

The following are net-new _builds_ this specification depends on (each traced to an
audit finding), listed so `12-implementation-plan.md` can dependency-order them:

1. **Enrich `trajectory.py`** with `error_class`, `norm_path`, `test_id` +
   cross-step `same_class_recurrence` (§5) — foundational; blocks the whole
   taxonomy.
2. **Validate `error_class`** precision/recall vs the sampled `report` flags (§5.2).
3. **Motif-axis split** (`motif_id` in `split_group` + motif-grouped assignment) —
   blocks H4 motif-transfer (§6).
4. **Synthetic injector** (parameterized per-motif bug transforms over clean seed
   repos, with surface-variant axis) — Suite A construction (§2).
5. **Motif miner + N-judge labeling** over Open-SWE / Sampled traces — Suite B
   labeling (§3.5).
6. **Extend the reproducibility binding** to include checkpoint SHA, seed, injector
   version, and frozen judge labels (§6).

None of these authorizes a training run; every lane stays `training_weight: 0.0` /
`not_authorized` until a human signs off.

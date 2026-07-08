# 05 — Domain-Specific RSI Integration Design: the 9to5 x Pneuma Lab x pneuma-data Loop

**Status line (2026-07-07).** Nothing that exists today constitutes recursive self-improvement.
What exists: a production autonomous engineering agent (C:\9to5) with real persistent memory and
retrieval-injected experience [VERIFIED], a dormant LoRA/DPO substrate that has never produced an
adapter [VERIFIED: adapters table = 0 rows], a revert-or-keep safety gate misnamed `selfmod.py`
that modifies nothing [VERIFIED], and — new as of Phase 3.1 — 6,055 real, outcome-labeled,
trajectory-bearing PneumaTrace v0.2 envelopes converted byte-deterministically from OpenHands
recordings [VERIFIED]. The connective tissue of the loop — a 9to5-run-artifact -> PneumaTrace
exporter, motif mining, learned estimators, and any code path from adapter output into the replay
harness — does not exist [VERIFIED absence]. This document designs the loop, names each stage's
artifact and gate, specifies the missing exporter, and pre-registers what would count as the loop
actually working. Per the honesty rules: targets are maximal, status claims are not.

Sibling context: the evidence-grading vocabulary and the Level-0..4 ladder used below are defined
in `docs/consciousness-levels.md` and the companion research docs in `docs/research/`; the Phase
3.1 trace contract is specified in `docs/phase-3-1-trajectory-traces.md`; the envelope schema is
`schemas/pneuma-trace.schema.json` (v0.2.0).

---

## 1. What is RSI-adjacent TODAY (evidence-graded inventory)

The honest claim is "RSI-adjacent substrate exists; the loop does not." Itemized:

| Component                      | Reality                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Grade                                                       |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Retrieval-injected experience  | `C:\9to5\state\experience.db` (37 MB): 3,534 runs, 7,900 subtasks, 161 reflections; embedding retrieval with separate success/failure lanes is wired into planning. This is a real behavior-shaping feedback path: past outcomes influence future plans.                                                                                                                                                                                                                                             | [VERIFIED]                                                  |
| Lessons / prompt evolution     | lessons table = 2 rows, prompt_variants = 1, conviction.db = 0 rows, step_journal = 0 rows. The mechanism is real; the content is nearly empty. "Retrieval-injected lessons" is real but thin — it shapes behavior anecdotally, with no measured improvement curve.                                                                                                                                                                                                                                  | [VERIFIED mechanism, PARTIAL effect: no measurement exists] |
| LoRA/DPO trainer               | Code exists in 9to5; it has never produced an adapter (adapters table = 0 rows; no GPU available). Weight-level self-improvement is dormant, not absent.                                                                                                                                                                                                                                                                                                                                             | [VERIFIED dormant]                                          |
| `selfmod.py`                   | A revert-or-keep safety gate: it evaluates whether a change should be kept or reverted. It authors no changes. Calling it self-modification would be status inflation; it is the deployment-gate half of a loop whose generative half is unbuilt.                                                                                                                                                                                                                                                    | [VERIFIED: gate only]                                       |
| Phase 3.1 trajectory substrate | 6,055/6,055 OpenHands-Sampled trajectories converted to PneumaTrace v0.2 (`src/pneuma_lab/adapters/openhands_sampled.py`): 114,461 real agent steps, 100% task join, 491 resolved / 5,564 unresolved outcome labels, byte-deterministic (twice-run sha256 match), 0 invalid, 0 skipped, deterministic PII redaction actually executed (103 emails, 4 AWS keys, 16 assigned secrets). This is the first real supervision substrate for estimators: real behavior, real outcomes, real failure shapes. | [VERIFIED]                                                  |
| Anti-fake-cognition gate       | `envelope.consistency_errors()` rejects any trace whose agent_trace frames, trajectory block, and `has_trajectory` label disagree, and any undeclared cognition-bearing frame. Enforced in code on every emitted trace.                                                                                                                                                                                                                                                                              | [VERIFIED]                                                  |
| Learned estimators             | None exist in either repo.                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | [VERIFIED absence]                                          |
| Motif mining                   | None exists. Dossier `pneuma_frame_map` / `training_targets` entries in pneuma-data are aspirational notes no code consumes.                                                                                                                                                                                                                                                                                                                                                                         | [VERIFIED absence]                                          |
| 9to5 -> Pneuma exporter        | Zero Pneuma vocabulary anywhere in C:\9to5; the 9to5-trace adapters in pneuma-lab are docstring stubs. The two repos are coupled only by migrated reference copies, in the wrong direction for this loop.                                                                                                                                                                                                                                                                                            | [VERIFIED absence]                                          |
| Trace -> harness replay        | No code path connects adapter output (PneumaTrace JSONL) to `src/pneuma_lab/replay/harness.py`.                                                                                                                                                                                                                                                                                                                                                                                                      | [VERIFIED absence]                                          |

Hygiene caveat carried from the audit: the intervention harness, demo, and all Phase 3.1 work are
uncommitted working-tree state (HEAD = b3102c6; only the Phase-3 adapter is committed). Until
committed, "exists" means "exists on one machine's working tree."

Important framing: the OpenHands traces are traces OF another agent observed from outside. They
earn no evidence level about 9to5 or about any interiority claim. Their role in this loop is
purely as supervision substrate and as an external, fixed reference corpus (Section 5).

---

## 2. The concrete loop design

The target loop, one full cycle:

    live trace capture -> redaction -> outcome labeling -> motif mining
        -> estimator retraining -> replay regression -> gated deployment
        -> improved 9to5 behavior -> better traces / evals / tools -> repeat

Every stage is specified with artifact, format, storage, and gate. Grades mark what exists.

### 2.1 Stage table

| #   | Stage                              | Artifact                                                                                                                                                                                                          | Format                                                                                                                    | Storage                                                                                              | Gate                                                                                                                                                                                      | Grade                                                                                                            |
| --- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| 1   | Live trace capture                 | 9to5 run artifacts: `runs`/`subtasks`/`reflections` tables, hn_event_log, per-attempt trajectory spans                                                                                                            | SQLite + event log (9to5-native)                                                                                          | `C:\9to5\state\experience.db` and run artifact dirs                                                  | Capture-completeness check: every attempt has a verification-gate result and an adversary verdict recorded                                                                                | [VERIFIED capture; completeness check PLANNED]                                                                   |
| 2   | Export + redaction                 | PneumaTrace v0.2 envelopes with redaction ledger                                                                                                                                                                  | PneumaTrace v0.2 JSONL (`schemas/pneuma-trace.schema.json`), AgentTraceFrames per `schemas/agent-trace-frame.schema.json` | `C:\pneuma-lab\build\traces\9to5\era-<YYYYMMDD>\pneuma_traces.jsonl` (+ `.invalid.jsonl` quarantine) | `envelope.consistency_errors()` must be empty; `privacy.pii_scanned` true; redaction ledger records kind+count only; quarantine on any failure                                            | [PLANNED — the exporter; redaction machinery VERIFIED in pneuma-lab as of Phase 3.1]                             |
| 3   | Outcome labeling                   | `outcome` block per trace                                                                                                                                                                                         | v0.2 envelope `outcome` (kind, resolved, harness/verifier booleans, patch digest)                                         | Inside each trace                                                                                    | Label provenance must be a deterministic verifier (9to5 expect-grammar gate + adversary verdict, or oracle tests). LLM prose (reflections) is never a label.                              | [VERIFIED for OpenHands substrate; PLANNED for 9to5 traces]                                                      |
| 4   | Motif mining                       | Motif catalog: recurring observable patterns over AgentTraceFrame sequences (tool n-grams, retry bursts, error-marker chains, strategy-switch signatures) with support counts and outcome-conditional frequencies | JSONL, one motif per line, with `motif_id = sha256(canonical pattern)`, support, resolved-rate, era coverage              | `build/motifs/motifs-<era>.jsonl`                                                                    | Deterministic: same trace set -> byte-identical catalog; minimum support threshold pre-registered; motifs referencing raw text are impossible by construction (frames carry digests only) | [PLANNED]                                                                                                        |
| 5   | Estimator retraining               | Versioned estimators: (a) outcome predictor P(resolved \| trace prefix), (b) failure-shape classifier, (c) motif-risk scorer; later, 9to5 LoRA/DPO adapters                                                       | Model file + training manifest (dataset content hashes, seed, hyperparams, era cutoff, git SHA)                           | `build/estimators/<name>-<version>/` ; adapters in 9to5's adapters table                             | Manifest completeness; training data strictly from eras <= cutoff; no manual hyperparameter edits inside a cycle (Section 3)                                                              | [PLANNED; LoRA/DPO trainer VERIFIED dormant]                                                                     |
| 6   | Replay regression                  | Regression report: frozen-fixture metrics + golden replay byte-comparison + paired psyche replay where applicable                                                                                                 | JSON report + markdown summary                                                                                            | `build/rsi/cycle-<n>/regression.json`                                                                | All frozen fixtures within pre-registered tolerance; golden replays byte-identical; any regression fails the cycle closed                                                                 | [PARTIAL: golden replay + paired L4 harness VERIFIED for ReferencePsyche fixtures; estimator regression PLANNED] |
| 7   | Gated deployment                   | Deployment record: what shipped (estimator hash / adapter hash / lesson set / prompt variant), gate decisions, canary results                                                                                     | JSON                                                                                                                      | `build/rsi/cycle-<n>/deployment.json` + 9to5 adapters/lessons tables                                 | Two-key gate: (key 1) automatic — regression + canary pass, `selfmod.py`-style revert-or-keep verdict; (key 2) operator sovereignty — explicit human approval recorded, no silent deploys | [PARTIAL: selfmod gate + operator sovereignty exist in 9to5; the two-key composition PLANNED]                    |
| 8   | Improved behavior -> better traces | Next era of captures, plus loop-produced improvements to evals/tools (new expect-grammar rules, new canaries, new motif detectors)                                                                                | Same as stage 1/2, tagged with new era                                                                                    | Same                                                                                                 | Era tag mandatory; every trace carries the estimator/adapter versions active during capture, so cycles are attributable                                                                   | [PLANNED]                                                                                                        |

### 2.2 The missing exporter — the single highest-leverage unbuilt component

Everything downstream of stage 2 can be built and validated against the OpenHands substrate, but
the loop is not about 9to5 until 9to5's own runs become PneumaTraces. The exporter is therefore
the highest-leverage unbuilt component: it converts an existing, rich, real capture stream
(3,534 runs and growing) into the loop's canonical format, and it is the only stage whose absence
makes every other stage irrelevant to the production agent. Specification:

**Name and location.** `src/pneuma_lab/adapters/nine_to_five.py`, CLI-invoked like the two
shipped adapters. Pneuma Lab must not import 9to5 code (standalone rule in CLAUDE.md); the
exporter reads a **file snapshot** of 9to5 state, never live handles and never Python imports:

    python -m pneuma_lab.adapters.nine_to_five \
        --experience-db  <snapshot>/experience.db \
        --event-log      <snapshot>/hn_event_log \
        --artifact-root  <snapshot>/runs/ \
        --era            2026-07-07 \
        --out            build/traces/9to5/era-20260707/

**Inputs.** (a) `experience.db` tables `runs`, `subtasks`, and per-attempt records including the
verification-gate result and adversary verdict; (b) hn_event_log (human_nature bridge events:
instinct checks, authority-gate decisions) when the flag was enabled; (c) per-attempt trajectory
spans (tool invocations and outputs from the Claude Code executor loop). Exact 9to5 column names
must be confirmed against the 9to5 schema at build time — this spec names semantics, not columns
[PLANNED].

**Output.** PneumaTrace v0.2, one trace per (run_id, subtask_id, attempt), with:

- World frame: the subtask objective text, passed through the same deterministic redaction as
  Phase 3.1 (emails, GitHub/AWS/Slack tokens, private-key blocks, bearer tokens, assigned
  secrets), ledger recording kind+count only.
- AgentTraceFrames under the exact observable-only rules of `adapters/trajectory.py`: tool names,
  args digests + lengths, output digests + lengths, lexical error markers, retry counts, strategy
  switches, assistant-text digests. Raw text never enters frames. No inferred intent, no
  confidence, no plan fields unless 9to5 records them as structured observables.
- Timestamps: 9to5 records real wall-clock, so `timestamp_provenance` = recorded — a strict
  upgrade over the OpenHands synthetic-ordinal traces, and it must be declared per frame exactly
  as the v0.2 contract requires. Where a span lacks wall-clock, fall back to synthetic-ordinal
  and declare it; never fabricate times.
- Governance frames from the ControlBus and authority-gate events (abort/pause/gate decisions,
  operator interventions) — these are the domain's real "governance pressure" observables.
- `outcome` block from the deterministic verification gate (expect-grammar pass/fail,
  diff-grounded target satisfaction) and the adversary review verdict (fails closed). Never from
  reflections, never from model prose.
- `labels.era` = snapshot date; `build.frame_sources` declaring `production-run-export` for every
  cognition-bearing frame kind, so the consistency gate can enforce declaration.

**Determinism and identity.** `derive_ids("9to5", run_id::subtask_id::attempt, snapshot_hash)`;
canonical JSON; content hash with self-referential fields blanked; emission sorted by
(run_id, subtask_id, attempt). Golden fixture built from a synthetic `experience.db` snapshot
seeded with fake PII (mirroring the Phase 3.1 test strategy in
`tests/test_openhands_sampled_adapter.py`); two-run byte-equality test mandatory; `--emit-fixture`
fails on drift.

**Gates.** Every trace passes `envelope.consistency_errors()`; failures quarantine to
`pneuma_traces.invalid.jsonl`; the run report publishes counts (converted / invalid / skipped /
redactions by kind) exactly as the Phase 3.1 adapter does.

**Privacy note.** 9to5 traces are private working data about the operator's own machine and
repositories. They are strictly more sensitive than the HF-sourced corpora; the redaction ledger
and digests-only frame rule are necessary but not sufficient — the exporter's output directory
stays local and out of any published artifact until a dedicated review [PLANNED].

### 2.3 Corpus role of pneuma-data

`C:\pneuma-data` (10 datasets, 37,711 files, 48.95 GB verified) supplies two things to the loop:
(a) pretraining/bootstrap substrate for estimators before enough 9to5 eras exist — the converted
OpenHands-Sampled set now, OpenHands-SFT (491 success-only) and OpenHands-Verifier (on/off-policy
with resolved labels) as candidate next conversions [PLANNED]; (b) a **frozen external reference
corpus** that the loop never trains on, used to detect overfitting to private traces (Section 5).
Honest row accounting per the audit: the "8.5M verified rows" figure mixes line counts with parsed
records; the honest total is ~5.99M records, and swe-chat's conversational core is 104,166 rows,
not 2.69M. Any loop document or report citing corpus size must use the parsed-record numbers.

---

## 3. What would make this TRUE domain-specific RSI

Definition adopted here: **domain-specific RSI** is a closed loop in which the system's own
operation produces the data, the updates, and the deployment decisions that measurably improve
its future operation in its domain (autonomous software engineering), under pre-registered
measurement, without a human adjusting parameters inside the loop. Humans may stand outside the
loop as safety gate-keepers (the second key) and as auditors; they may not be the optimizer.

### 3.1 The falsifiable criterion (pre-registered)

The loop counts as domain-specific RSI if and only if:

1. **Two consecutive update cycles** (cycle n and n+1) each produce a deployed change (weights,
   estimator, lesson set, prompt variant, or tool/eval change generated by the loop itself).
2. Each cycle **improves held-out FUTURE-task engineering-judgment metrics**: the evaluation set
   for cycle n consists exclusively of tasks from eras strictly after cycle n's training-data
   cutoff (era-based holdout, Section 5), scored by deterministic verifiers (oracle tests,
   expect-grammar gates), on at least the pre-registered metric family of Section 6.
3. The analysis is **pre-registered**: metric family, statistical test, alpha, minimum sample
   size, and success thresholds are committed to `build/rsi/cycle-<n>/preregistration.json`
   _before_ the cycle's training begins, and the published report is generated mechanically from
   that file.
4. **No human parameter tweaks inside the loop**: between the moment a cycle's pre-registration
   is committed and the moment its report is published, no human edits hyperparameters, prompts,
   thresholds, or training data selection. Human actions are limited to the two-key deployment
   approval (approve/reject as-is) and to aborting the cycle entirely (which voids it, honestly
   recorded). Any other human intervention is logged and disqualifies the cycle.
5. Failure to meet any clause on either cycle falsifies the claim for that pair; the counter
   resets. The claim is only ever "cycles n..n+k satisfied the criterion," never "the system is
   recursively self-improving" as a standing property.

Current status against this criterion: 0 cycles run, 0 cycles possible (stages 2, 4, 5 unbuilt).
[VERIFIED absence]

### 3.2 Three kinds of improvement, kept distinct

Conflating these is the classic RSI status-inflation failure, so every cycle report must classify
its deployed change:

- **Improvement of weights.** LoRA/DPO adapters over the local brain, or trained estimators that
  gate/rank actions. Strongest form; currently dormant (0 adapters) [VERIFIED]. Requires GPU
  provisioning that does not exist today [VERIFIED gap].
- **Improvement of tools/evals.** Loop-generated changes to the expect grammar, new canary tasks,
  new motif detectors, new adversary-review rules. These improve the _measurement and gating_
  machinery. They count toward the criterion only when generated and validated by the loop, not
  hand-authored; hand-authored eval improvements are ordinary engineering, valuable but not RSI.
- **Improvement of data.** Better traces (richer capture, better labels, cleaner redaction),
  better retrieval content (lessons that actually fire). This is the cheapest loop output and the
  easiest to Goodhart ("more data" is not "better judgment"); it counts only via its measured
  effect on the held-out metrics, never by volume.

A cycle may ship any mix; the report attributes the measured delta to the shipped change via the
paired design of Section 6, not by narrative.

---

## 4. What general RSI would require beyond this (out of scope)

Stated honestly so the ambition cannot be mistaken for a claim:

- **Cross-domain transfer.** Everything above is scoped to autonomous software engineering with
  deterministic verifiers. General RSI requires improvement on tasks with no oracle, which this
  program's proof standard (receipts + deterministic verification) cannot currently grade at all.
- **Self-directed objective formation.** The loop optimizes fixed, human-chosen metrics. A system
  that proposes, justifies, and safely revises its own objectives is a different research program
  with unsolved alignment preconditions.
- **Architecture self-modification.** The loop updates weights, data, and eval tooling around a
  fixed agent architecture. Modifying the planner/executor/verifier topology itself is out of
  scope; `selfmod.py` remains a gate, and there is no proposal here to make it a modifier.
- **Compounding rate.** True general RSI implies improvement in the _rate_ of improvement.
  Nothing in this design measures or targets second-order gains; two consecutive improving cycles
  is a floor for "the loop works," not evidence of takeoff dynamics.
- **Verified safety under self-modification.** The two-key gate assumes the human key is
  meaningful, i.e., changes are small and auditable. General RSI breaks that assumption; this
  program does not pretend to have an answer and deliberately stays where audits are tractable.

None of the above is claimed, planned for this loop, or achievable with the current substrate.
[PLANNED at most as future research questions; no machinery exists.]

---

## 5. Failure modes and protections

| Failure mode                                | Concrete mechanism here                                                                                                                                     | Protection (artifact + gate)                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Goodharting the verifier                    | Estimators/adapters learn to satisfy the expect grammar or the adversary reviewer rather than to solve tasks (e.g., emitting diff shapes the grammar likes) | Metric _family_, never a single metric (Section 6); held-out oracle tests the loop never sees; adversary review stays independent and fails closed [VERIFIED it fails closed today]; rotating canary tasks refreshed each cycle from eras after all training cutoffs; any metric-family divergence (primary up, secondary down) fails the cycle |
| Overfitting to private traces               | 9to5's own runs are a narrow distribution (one operator, one machine, one repo style); estimators ace era holdouts yet degrade generally                    | Frozen external reference corpus from pneuma-data (converted OpenHands sets, never trained on after the bootstrap freeze) evaluated every cycle; a pre-registered maximum allowed regression on the external corpus is a hard gate                                                                                                              |
| Self-delusion via confabulated self-reports | 9to5 reflections (161 rows, LLM prose) or grounded-self-report frames get used as outcome labels or training targets, laundering narrative into supervision | Label-provenance gate (stage 3): only deterministic verifiers label outcomes; `ConsciousnessEvidenceScorer` already never promotes on self-report [VERIFIED] and the same rule is inherited here; reflections may be retrieval content, never labels; confabulation risk in psyche-side evals stays hash-cross-check based, not prose-based     |
| Catastrophic forgetting                     | A new adapter/estimator improves era n+1 tasks while silently losing competence on older task families                                                      | Era-based holdouts spanning _all_ past eras, not just the latest; frozen regression fixtures (exact traces with expected scores, byte-pinned); golden replay byte-comparison for anything deterministic [VERIFIED machinery exists for psyche fixtures]; canary tasks drawn from every era with per-era minimum pass rates                      |
| Silent data corruption / drift              | Exporter or mining nondeterminism corrupts the substrate invisibly                                                                                          | Byte-determinism discipline everywhere (twice-run sha256 comparison, canonical JSON, content hashes) — already the house style [VERIFIED for both shipped adapters]; `--emit-fixture` drift detection; quarantine streams never merge back silently                                                                                             |
| PII / secret leakage into training          | Private trace text or corpus PII (swe-chat has real author emails/names; source is HF-gated) enters frames or model weights                                 | Digests-only frame rule (raw text structurally cannot enter frames) [VERIFIED]; deterministic redaction with auditable ledger [VERIFIED, executed at scale in Phase 3.1]; the still-missing full PII scan over swe-chat is a pre-condition before any swe-chat-derived training [VERIFIED gap]                                                  |
| Gate capture / silent deployment            | The loop learns to produce changes that pass its own gates                                                                                                  | Two-key deployment: automatic gate (regression + canary + revert-or-keep) AND recorded human approval; the human key can only approve/reject/abort, preserving Section 3.1 clause 4; every deployment record is append-only and auditable                                                                                                       |
| Fake cognition in traces                    | Fabricated agent_trace frames inflate the substrate                                                                                                         | `envelope.consistency_errors()` anti-fake-cognition gate, enforced in code on every trace [VERIFIED]                                                                                                                                                                                                                                            |

---

## 6. Proof standard per cycle

Each cycle must publish `build/rsi/cycle-<n>/report.md` generated mechanically from the
pre-registration file and the raw measurement artifacts. Required content and statistics:

**Design.** Paired evaluation wherever possible: the pre-change and post-change systems run the
_same_ held-out task set under the same seeds and fixtures (the discipline already proven by the
paired replay harness, `src/pneuma_lab/interventions/runner.py`, control/treated/null) [VERIFIED
machinery for psyche replay; PLANNED for agent-level task replay]. Where full agent replay is too
expensive, a pre-registered random subsample with declared size is acceptable; post-hoc subsetting
is not.

**Metric family (pre-registered, all reported, no cherry-picking):**

1. Primary: resolved rate on future-era held-out tasks (deterministic verifier).
2. Oracle-test pass rate on joined tasks (from the task-table join machinery already shipped).
3. Regression count on frozen fixtures (must be 0 within tolerance — hard gate, not a statistic).
4. External-corpus resolved-rate delta (overfitting sentinel; bounded regression gate).
5. Efficiency secondaries: steps-to-resolution, retry_count and strategy_switches distributions
   (from AgentTraceFrame observables) — reported, not gated, to detect Goodhart patterns like
   "resolves more by brute-forcing longer."

**Statistics.** For the paired binary primary metric: exact McNemar test on discordant pairs;
report b/c counts, odds ratio, and 95% CI. For rate deltas without pairing: two-proportion test
with Wilson intervals. For distributional secondaries: bootstrap CIs (10,000 resamples, seeded,
seed pre-registered) on the median delta. Multiplicity: Holm–Bonferroni across the gated metric
family at pre-registered alpha = 0.05. Minimum sample size: pre-registered per cycle with a power
calculation for the smallest effect the cycle claims; a cycle whose achieved n falls below its
pre-registered minimum reports "underpowered — no claim," not a p-value victory.

**Mandatory report sections.**

    1. Pre-registration echo (verbatim, with commit hash and timestamp).
    2. Data manifest: era cutoffs, trace-set content hashes, quarantine counts,
       redaction ledger totals.
    3. Shipped change: classification (weights / tools-evals / data), artifact
       hashes, training manifest.
    4. Paired results: full metric family, test statistics, CIs, per-era
       breakdown.
    5. Regression + canary results per era; golden replay byte-comparison
       verdicts.
    6. Gate decisions: automatic-key evidence, human-key record, any logged
       human interventions (each one voids the cycle per Section 3.1).
    7. Honest classification of the cycle: improving / non-improving /
       underpowered / voided.

**Evidence-category discipline.** Every cycle report classifies its own contribution using the
program's ladder: engineering utility (almost always), autonomy evidence (sometimes),
self-improvement evidence (only when Section 3.1 clauses hold), architecture evidence (never —
architecture is not evidence), consciousness-relevant evidence (never from this loop; any psyche
claims route through the intervention harness and always carry the reference-implementation
caveat: current Level-4 results mean "Level 4 of a hand-coded reference implementation inside its
own harness," nothing more) [VERIFIED caveat, binding].

---

## Build order (dependency-honest)

1. Commit the uncommitted Phase 3.1 + intervention-harness working tree (hygiene precondition).
2. Exporter `src/pneuma_lab/adapters/nine_to_five.py` per Section 2.2 — the single
   highest-leverage unbuilt component. [PLANNED]
3. Trace -> replay bridge: a code path from PneumaTrace JSONL into the replay/eval surfaces, so
   regression fixtures can be cut from real traces. [PLANNED]
4. Motif miner over the existing 6,055-trace substrate (buildable today, before the exporter,
   because the substrate already exists). [PLANNED]
5. First estimator (P(resolved | trace prefix)) trained on OpenHands eras, evaluated on the
   Verifier set as pseudo-future era; this de-risks stages 5–6 without touching 9to5. [PLANNED]
6. Two-key deployment composition in 9to5 (selfmod gate + operator sovereignty + cycle report
   linkage). [PLANNED]
7. First pre-registered cycle. Only after it runs may anyone say the loop exists — and even then,
   only as "cycle 1 of the criterion in Section 3.1."

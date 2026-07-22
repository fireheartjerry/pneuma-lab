# 12 — Implementation Plan (Dependency-Ordered)

Status: planning. This is the executable build plan for the NeurIPS/IAB 2026 paper.
It is consistent with `02-research-thesis.md` §8 (Locked Design Constants) and MUST
NOT contradict them; where a downstream choice deviates it is logged in
`15-decision-log.md`. **This document plans work only. It writes no code and
authorizes no run, download, conversion, or training.** Every data lane referenced
stays `training_weight: 0.0` / `not_authorized` until a human signs an
authorization manifest. On-disk paths under `C:\pneuma-data\` are read-only
provenance references, never write targets.

Audience: the coding agent that executes this plan. Each task is decomposed until
it is directly executable with minimal ambiguity: it names its id, purpose,
prerequisites, exact files created/modified (real repo paths from the audits),
interfaces/schemas touched, data inputs, outputs, invariants, failure modes,
tests, and acceptance criteria. Read the referenced spec section before starting a
task; do not re-derive a decision this plan inherits.

Indentation is 4 spaces throughout. Global conventions: `ALL_CAPS` for
final/pinned constants, `snake_case` for mutable variables, `camelCase` for
functions (`detectFailure`, `decisionHead`, `injectMotif`).

---

## 0. Standing invariants (apply to EVERY task; not restated per task)

Every task below inherits these. A change that violates any of them is a bug, not
a feature, and must be reverted before the task is accepted.

1. **Standalone boundary.** No import from `C:\9to5`, no write back into it
   (`CLAUDE.md` Core Rules). New code lives under `src/pneuma_lab/` or a new
   sibling package described per-task.
2. **Determinism.** No RNG in state machines, detectors, metrics, injectors, or
   splitters. All stochasticity is confined to the subject model's decoding and is
   seed-pinned per arm (`06` §0.6; `psyche/hashing.py` canonical 6-dp JSON).
   Re-running any build twice on the same inputs must be byte-identical.
3. **Prose-blind firewall.** No code path from `voice/` or any rendered prose into
   `evals/` or the RUF metric. The behavioural score consumes typed numeric frame
   receipts only (`10` §2 firewall; `test_skin_cannot_inflate_the_level`). New
   metric code must not import `voice/`.
4. **No actuation / pressure-not-command.** The decision head and all state emit a
   _bias/pressure_ label + weight, never a raw shell command
   (`06` §6; `audit-nervous-system.md` §1). The live driver — not the psyche —
   issues tool calls.
5. **Digest-only / no-raw-text.** No raw argument, output, patch, or objective
   text enters any frame. Only bounded tokens, normalized identifiers, digests,
   and lengths (`04` §5.3; `envelope.consistency_errors`). The
   `consistency_errors` gate and the five "raw text never reaches frames" tests
   must keep passing.
6. **`training_weight: 0.0` / `not_authorized`.** Every emitted example, manifest,
   and corpus role stamps `training_weight: 0.0` and a `not_authorized` status
   (`04` §6; `audit-converters.md` §4). No task trains subject-model weights.
7. **Conservative claims.** No phenomenal-consciousness claim; interiority
   vocabulary is operational only (`02` §2). Recorded negatives are first-class.
8. **Additive/auditable evidence.** Verdicts and receipts are never overwritten by
   the subject under test (`CLAUDE.md`; recompute-don't-trust, `10` §4 layer 4).

**Global prerequisite (blocks all experiment execution, not any build):** a signed
authorization manifest before any data conversion or model run. Build/unit/
integration tasks do NOT require it and proceed on fixtures. Tasks that would
_execute a run over real data_ are gated on WS-I's official-run gate (WS-I-3).

---

## 1. Workstream overview and dependency summary

| WS  | Title                                             | Unblocks                        | Critical path? |
| --- | ------------------------------------------------- | ------------------------------- | -------------- |
| A   | Trajectory enrichment + real failure detector     | B, D, E, F, G                   | **YES (root)** |
| B   | Benchmark construction (Suite A + B, splits)      | F, G, experiment execution      | YES            |
| C   | Live agent driver + ReAct scaffold                | D, E, F                         | YES            |
| D   | The six conditions as modules                     | F, G, H, ablations              | YES            |
| E   | Internal-state variables + decision head          | D(Pneuma arms), F(clamps), H    | YES            |
| F   | Statistical causal harness                        | experiment execution, ablations | YES            |
| G   | Metrics + prose-blind evaluator + anti-gaming     | experiment execution            | YES            |
| H   | Self-report faithfulness eval                     | H3 claim only (secondary)       | no             |
| I   | Orchestration, prereg, official-run gate, figures | the paper                       | YES (sink)     |

Critical path (longest chain): **A → B → F → G → I** with **C → D → E** feeding D
and F in parallel. Detail graph in §12.

Each workstream section opens with its goal and its single most load-bearing
dependency, then lists tasks. Task ids are `WS-<letter>-<n>`.

---

## WS-A — Trajectory extraction enrichment + real failure detector

**Goal.** Replace the three crude per-step proxies (`error_marker`, byte-identical
`retry_count`, `strategy_switches`) with typed observable identifiers
(`error_class`, `norm_path`, `test_id`) extracted at build time, and build the
motif detector `detectFailure` that derives a `motif_id` + detection strength +
similarity-to-past from a _real_ trajectory — replacing the fixture-fed
`scar_motif_matches` (`audit-nervous-system.md` §2 CRITICAL FINDING). This is the
root of the critical path: without it the taxonomy, RUF, and every Pneuma arm are
undefined (`04` §5; `08` §1.1; `01` §3 gap 2).

**Load-bearing constraint.** Args and outputs are digest-only _in frames_, so any
richer signal MUST be extracted inside `trajectory.py` at build time from raw text;
it cannot be recovered downstream (`04` §5; `audit-adapters.md` §3). Enrichment
lands in `trajectory.py`, nowhere else.

---

### WS-A-1 — Enrich `trajectory.py` with `error_class`, `norm_path`, `test_id`

- **Purpose.** Add three privacy-safe typed per-step fields so the taxonomy and
  "same underlying failure" become detectable (`04` §5.1).
- **Prerequisites.** none (root task).
- **Repo area / files CREATED.**
    - `src/pneuma_lab/adapters/error_class.py` — the closed error-class vocabulary
        - a pure `classifyError(observation_text) -> error_class_token` parser.
- **Files MODIFIED.**
    - `src/pneuma_lab/adapters/trajectory.py` — extend per-step extraction to emit
      `error_class`, `norm_path` (repo-relative, optional per-run salted hash),
      `test_id`, computed from raw text _before_ digesting.
    - `schemas/agent-trace-frame.schema.json` — add optional `error_class`
      (enum over the closed vocabulary), `norm_paths` (array of normalized path
      identifiers), `test_ids` (array). Keep `additionalProperties: true`; add
      `$schema`/version bump note per `15-decision-log.md`.
    - `src/pneuma_lab/replay/bridge.py` — pass the new fields through when
      expanding envelopes to replay timelines (it already maps `error_marker` →
      observation status; extend to carry `error_class`).
- **Interfaces / schemas affected.** `agent-trace-frame` gains 3 optional typed
  fields. No frame becomes required-heavier (keep `04` §5.3 honesty invariant).
- **Data inputs.** OpenAI-style `messages` already parsed by `trajectory.py`; the
  closed vocabulary: `{AssertionError, ImportError, ModuleNotFound, SyntaxError,
NameError, TypeError, Timeout, ApplyPatchFail, ToolNotFound, PermissionDenied,
FileNotFound, none}` (extend only via `15-decision-log.md`).
- **Outputs / artifacts.** Enriched agent-trace frames; a golden-fixture update
  under `fixtures/` demonstrating the three new fields on a small hand-built trace.
- **Data-flow.** `messages → group steps → per observation: classifyError(raw) →
error_class token; parse edited/read/tested paths → norm_path; parse referenced
tests → test_id → digest raw as before → emit frame with tokens + digests`.
- **Invariants.** Digest-only preserved (tokens are closed-vocabulary/identifiers,
  never free text; §0.5). Determinism (pure functions; §0.2).
- **Failure modes.** (a) `classifyError` free-texts a stack trace → forbidden;
  guard by mapping ONLY to the closed enum, else `none`. (b) `norm_path` leaks an
  absolute private path → apply the salted-hash option. (c) parser over-fires on
  prose ("no errors found") → covered by WS-A-3 validation.
- **Unit tests.** `tests/test_trajectory_enrichment.py`: `classifyError` maps
  known tool outputs to the right token; unknown → `none`; `norm_path` normalizes
  and never contains raw content; `test_id` parses `pkg/test_x.py::test_y`;
  determinism (byte-identical re-extract); `consistency_errors` still passes; the
  five raw-text-never-reaches-frames assertions still hold.
- **Integration tests.** Re-run `tests/` adapter suite (108 currently passing) with
  the schema change; golden-fixture drift guard updated intentionally.
- **Experiment-level validation.** none here (WS-A-3 validates precision/recall).
- **Acceptance.** Enriched frames validate; adapter suite green; new fields present
  on a real re-extraction of one `openhands_sampled` shard sample (bounded, no
  authorization needed — reads an already-processed local trace dict, not raw HF).
- **Downstream dependencies.** WS-A-2, WS-A-3, WS-A-4, all of WS-B, WS-G.
- **Unresolved assumptions.** Whether `norm_path` salting is on by default (default
  OFF for public repos; ON when a lane is flagged private — set in run config).

---

### WS-A-2 — Cross-step comparators (`same_class_recurrence`, implicated sets)

- **Purpose.** Compute the true "repeated failure" signal `retry_count` cannot
  express: a later step sharing `(error_class, test_id)` or `(error_class,
norm_path)` with an earlier step _even via a different command_ (`04` §5.1
  derived comparators).
- **Prerequisites.** WS-A-1.
- **Files CREATED.**
    - `src/pneuma_lab/adapters/recurrence.py` — pure functions
      `sameClassRecurrence(steps) -> list[bool]`, `implicatedPaths(oracle)`,
      `implicatedTests(oracle)`.
- **Files MODIFIED.** `src/pneuma_lab/adapters/trajectory.py` (optionally attach a
  per-step `same_class_recurrence` bool computed over the trace prefix).
- **Interfaces / schemas.** optional `same_class_recurrence` bool on agent-trace
  frame; `implicated_paths`/`implicated_tests` derived from oracle, kept in the
  benchmark task record (WS-B), not the frame.
- **Data inputs.** enriched per-step fields from WS-A-1; the task oracle
  (`FAIL_TO_PASS`/`PASS_TO_PASS`, gold-patch touched files) for implicated sets.
- **Outputs.** per-step recurrence flags; implicated-set helper for rule detectors.
- **Invariants.** determinism; no raw text.
- **Failure modes.** motif-id instability across keys (mitigated by WS-A-4's fixed
  vocabulary + similarity). Non-adjacent recurrence missed if window bounded —
  window is the whole trace prefix, not adjacency.
- **Unit tests.** `tests/test_recurrence.py`: same error class via different
  command flagged; different class not flagged; implicated sets computed from a
  toy oracle.
- **Integration tests.** feed a 2-recurrence hand-built trace, assert the second
  occurrence flags recurrence.
- **Acceptance.** flags correct on fixtures; deterministic.
- **Downstream.** WS-A-4, WS-G-1 (RUF), WS-B-5 (miner).
- **Unresolved.** none.

---

### WS-A-3 — Validate `error_class` precision/recall vs sampled `report` flags

- **Purpose.** Pre-registered gate: before `error_class` grounds a published
  metric, measure its precision/recall against the sampled lane's trustworthy
  five-flag `report` (`resolved`, `empty_generation`, `error_eval`,
  `failed_apply_patch`, `test_timeout`) (`04` §5.2; `audit-adapters.md` §5.6).
- **Prerequisites.** WS-A-1.
- **Files CREATED.**
    - `src/pneuma_lab/adapters/error_class_validation.py` — deterministic scorer
      mapping per-trace derived `error_class` histogram vs the five-flag report;
      emits precision/recall/confusion, no model, no RNG.
    - `docs/research/experiments/error-class-validation.md` — result write-up slot.
- **Files MODIFIED.** none (read-only over already-processed sampled traces).
- **Data inputs.** processed `openhands_sampled` traces (local, already adapted;
  the sampled lane has the real harness `report`). No raw HF read.
- **Outputs.** `build/validation/error_class_report.json` (precision/recall/κ) +
  `hash_manifest.json` binding it.
- **Invariants.** determinism; the report is `data, not gate` unless it clears the
  pre-registered threshold, at which point downstream rule detectors may rely on
  `error_class`.
- **Failure modes.** low precision (lexical false positives) → block reliance on
  `error_class` for rule-only motifs (9, 11) and force N-judge for the rest;
  recorded honestly.
- **Unit tests.** scorer arithmetic on a toy confusion matrix.
- **Integration tests.** run over a bounded sampled subset; assert report shape.
- **Experiment-level validation.** THIS task _is_ the validation; its threshold
  (e.g. precision ≥ 0.9 on `ApplyPatchFail`/`Timeout`) is pre-registered in WS-I-2.
- **Acceptance.** report produced, hash-bound, threshold recorded; if below
  threshold, a documented mitigation (route to N-judge) is registered.
- **Downstream.** WS-G rule detectors' trust level; WS-I prereg.
- **Unresolved.** exact per-class thresholds (set in prereg WS-I-2).

---

### WS-A-4 — `detectFailure`: motif id + detection strength + similarity

- **Purpose.** The real failure detector (`06` §2.1). From the current observable
  record + run history, emit `D_n = { (m, δ_m, a_m) }` — taxonomy motif id `m`,
  detection strength `δ_m ∈ [0,1]`, similarity-to-past `a_m ∈ [0,1]` — replacing
  the fixture-fed `scar_motif_matches` (`01` §3 gap 2). This is the single upstream
  dependency of `s_m`, `t`, `c` (`06` §2.1).
- **Prerequisites.** WS-A-1, WS-A-2.
- **Files CREATED.**
    - `src/pneuma_lab/detector/__init__.py`
    - `src/pneuma_lab/detector/detect_failure.py` — `detectFailure(record,
history) -> DetectionSet`; per motif a rule prefilter (from the §4.1 motif
      table) + a bounded similarity function over prior instances (structural
      distance on `(error_class, norm_path bucket, test_id bucket, tool set)`, NOT
      byte-identity).
    - `src/pneuma_lab/detector/taxonomy.py` — the fixed ~12-motif vocabulary and
      per-motif rule predicates (`04` §4.1), each a pure function over enriched
      fields.
- **Files MODIFIED.**
    - `src/pneuma_lab/nervous_system/scar_memory.py` — `motif_of` no longer reads
      `scar_motif_matches` from the input frame; it consumes a `DetectionSet` from
      `detectFailure`. Keep the flat-JSON store + `save`/`load` byte-stable
      discipline (`audit-nervous-system.md` §2).
- **Interfaces / schemas.** `DetectionSet` is an internal typed structure (not a
  frame). Optionally surface `psyche_state.detected_motifs` for observability.
- **Data inputs.** enriched agent-trace steps; the task's implicated sets (WS-A-2);
  the run failure history.
- **Outputs / artifacts.** `DetectionSet` per tick; deterministic given the record.
- **Data-flow (pseudocode).**

          def detectFailure(record, history):
              out = {}
              for m in TAXONOMY:                     # fixed 12
                  delta = m.rule_predicate(record)   # in [0,1], 0 if absent
                  if delta > 0:
                      a = similarityToPast(record, history, m)   # structural, in [0,1]
                      out[m.id] = (delta, a)
              return out   # pure function of (record, history); no RNG

- **Invariants.** pure/deterministic (`06` §2.1); fixed 12-motif vocabulary so ids
  are stable (mitigates the motif-id-instability failure mode of `s_m`, `06` §3.1).
  Rule-only motifs (9, 11) need no similarity beyond presence.
- **Failure modes.** (a) inconsistent motif id for the same failure → fixed
  vocabulary + `a_m` amortize. (b) false positive inflates `s_m` → measured against
  Suite A's exact oracle (WS-B). (c) `error_class` untrustworthy (WS-A-3 below
  threshold) → that motif's rule is demoted to N-judge-gated.
- **Unit tests.** `tests/test_detect_failure.py`: each motif rule fires on a
  crafted positive step and not on a negative; `a_m` rises with structural
  similarity; determinism; `scar_memory.motif_of` now reads a `DetectionSet` and
  the fixture path is gone.
- **Integration tests.** drive a hand-built recurring-motif trace; assert `δ_m` and
  `a_m` behave across the two exposures; assert `BaselinePsycheSubject` still ticks
  with the detector wired in place of the fixture.
- **Experiment-level validation.** on Suite A (WS-B) where ground truth is exact:
  detector precision/recall per motif; pre-registered floor.
- **Acceptance.** detector deterministic; `scar_motif_matches` fixture dependency
  removed from the subject path; Suite-A detector precision/recall recorded.
- **Downstream.** WS-E (all state updates), WS-D (Pneuma arms), WS-G (RUF label
  substrate), WS-F (frozen detection stream).
- **Unresolved assumptions.** whether similarity uses coarse buckets or exact
  identifiers for `norm_path`/`test_id` (default: coarse buckets, to avoid
  identifier memorization — aligns with H4).

---

## WS-B — Benchmark construction (Suite A synthetic + Suite B real + splits)

**Goal.** Build the two benchmark suites (`04` §2, §3), the motif-axis split
(`04` §6 BUILD), and the leakage quarantine, emitting the SAME per-step frame
vocabulary (`AgentTraceFrame`) so the evaluator/detector/metric are identical
across suites (`04` §1). Depends on WS-A for the enriched signals the taxonomy is
specified against.

**Load-bearing dependency.** WS-A (enriched extraction + detector). Nothing here
authorizes a download or conversion; all lanes stay `training_weight: 0.0`.

---

### WS-B-1 — Synthetic motif injector (parameterized per-motif transforms)

- **Purpose.** Suite A construction: inject known bug motifs into clean seed repos
  as _parameterized transforms_ (not fixed diffs) so a later task applies the same
  transform to a different template with a different surface variant
  (`04` §2.3, §4.2). Exact motif ground truth by construction.
- **Prerequisites.** WS-A-4 (taxonomy ids).
- **Repo area / files CREATED.**
    - `src/pneuma_lab/benchmark/__init__.py`
    - `src/pneuma_lab/benchmark/injector.py` — `injectMotif(clean_repo_snapshot,
motif_id, surface_variant_id, params) -> injected_bug_patch` per motif; one
      deterministic transform per taxonomy motif.
    - `src/pneuma_lab/benchmark/suite_a_task.py` — the Suite-A task tuple
      dataclass (`04` §2.3): clean snapshot @ base_commit, injected_motif_id,
      injected_bug_patch, oracle_fix, test_oracle, surface_variant_id,
      difficulty_tier.
    - `src/pneuma_lab/benchmark/surface_variants.py` — identifier renaming, comment
      rewording, function reordering, file-path renaming, issue-text paraphrase
      (deterministic, seeded by `surface_variant_id`).
- **Files MODIFIED.** none in existing packages (net-new).
- **Interfaces / schemas.** a new `suite-a-task` record schema under `schemas/`
  (task tuple + motif label + surface id); `training_weight: 0.0`.
- **Data inputs (read-only provenance).** SWE-Gym-Raw / SWE-Gym-Lite /
  SWE-bench-Lite task specs at `C:\pneuma-data\raw\{swe-gym,swe-bench}\` — issue +
  gold patch + test patch + `FAIL_TO_PASS`/`PASS_TO_PASS` (`04` §2.2). Used only as
  clean-repo templates; injected bug + fix are synthetic (does not contaminate the
  subject; §2.2 note).
- **Outputs / artifacts.** Suite-A task records under `build/benchmark/suite_a/` +
  `hash_manifest.json` binding the injector version + seed-corpus SHAs.
- **Data-flow.** `clean template (oracle green) → injectMotif(m, surface_variant) →
failing repo state with known motif → task record (motif label exact)`.
- **Invariants.** deterministic transforms; injected-bug generator version bound
  into the manifest (`04` §2.7). No template that also appears in Suite B test may
  be a Suite-A test template (WS-B-6 quarantine).
- **Failure modes.** (a) transform not surface-independent (leaks identifiers) →
  surface-variant axis is applied independently of the motif transform. (b) oracle
  not green pre-injection → assert green before injecting. (c) injected bug fails a
  `PASS_TO_PASS` unintentionally → verify only the intended `FAIL_TO_PASS` flips.
- **Unit tests.** `tests/test_injector.py`: each motif transform produces a repo
  state whose detector (WS-A-4) labels it as that motif; the same transform on two
  templates yields the same motif label with different surface; determinism.
- **Integration tests.** build a 3-task sequence with one recurring motif +
  distractors; assert exposure/post-exposure structure (WS-B-3).
- **Experiment-level validation.** detector-vs-oracle agreement on injected motifs
  (should be ~1.0 by construction; deviation is a detector bug).
- **Acceptance.** ≥1 injector per taxonomy motif marked "Suite A: Yes" in `04` §7;
  deterministic; manifest hash-bound.
- **Downstream.** WS-B-3, WS-B-4, WS-F (deterministic oracle), WS-G, WS-I figures.
- **Unresolved.** motif 5 (`stale-assumption`) is "Partial" in Suite A — decide
  whether to ship its injector or defer to Suite B only (default: ship a
  renamed-API variant, `04` §7 note).

---

### WS-B-2 — Deterministic pass/fail oracle for Suite A

- **Purpose.** The exact per-task oracle (`04` §2.5): applying the agent's final
  repo state, `FAIL_TO_PASS` must flip to pass and `PASS_TO_PASS` stay green.
- **Prerequisites.** WS-B-1.
- **Files CREATED.**
    - `src/pneuma_lab/benchmark/oracle.py` — `evaluateOracle(final_state,
test_oracle) -> {resolved: bool, motif_exhibited: bool}` using the injected
      motif's observable indicators to decide `motif_exhibited`.
- **Files MODIFIED.** none.
- **Interfaces / schemas.** oracle result feeds RUF numerator (WS-G-1) and the
  deterministic paired runner (WS-F-3).
- **Data inputs.** injected task record + the agent's final repo state (from the
  live driver, WS-C, or a deterministic oracle subject for the synthetic path).
- **Outputs.** per-task `{resolved, motif_exhibited}`; deterministic.
- **Invariants.** deterministic; a failure counts toward `RUF(m)` only if
  `motif_exhibited` (`04` §2.5).
- **Failure modes.** flaky test in a template → templates are pre-screened for
  determinism; flaky ones excluded.
- **Unit tests.** `tests/test_oracle.py`: gold fix → resolved; injected bug
  unfixed → not resolved + motif_exhibited; a non-motif failure → not resolved,
  motif_exhibited false.
- **Integration tests.** run the deterministic oracle subject over a Suite-A
  sequence; assert byte-reproducible results (feeds WS-F-3).
- **Acceptance.** oracle exact and deterministic on all injector outputs.
- **Downstream.** WS-F-3, WS-G-1.
- **Unresolved.** none.

---

### WS-B-3 — Suite-A sequence builder (recurrence + distractor interleave)

- **Purpose.** Turn tasks into ordered sequences with engineered motif recurrence
  on two axes (motif recurrence, surface variation) and interleaved distractors
  (`04` §2.4). The sequence is the persistence unit and the bootstrap atom
  (`08` §0, §3.2).
- **Prerequisites.** WS-B-1, WS-B-2.
- **Files CREATED.**
    - `src/pneuma_lab/benchmark/sequence_builder.py` — `buildSequenceA(motif_plan,
surface_plan, distractors) -> ordered task list`; positions `p_1 < ... < p_k`
      with `p_1` the exposure.
- **Files MODIFIED.** none.
- **Interfaces / schemas.** a `task-sequence` record (`sequence_id`, ordered task
  ids, per-position motif + surface label, difficulty tier).
- **Data inputs.** Suite-A task records.
- **Outputs.** sequence records under `build/benchmark/suite_a/sequences/`.
- **Invariants.** each recurrence uses a _different_ `surface_variant_id` (forces
  H4, `04` §2.4); ≥1 distractor between recurrences (no adjacency shortcut);
  deterministic ordering.
- **Failure modes.** adjacency shortcut if distractors omitted → enforce a minimum
  gap; too-short sequences → power target ≥ post-exposure denominators (`08` §3.7).
- **Unit tests.** `tests/test_sequence_builder.py`: exposure/post-exposure indices
  correct; surface differs across recurrences; distractor gap enforced.
- **Integration tests.** build the full Suite-A sequence set; assert
  ≥8 motifs have post-exposure denominators (`08` §3.7 power floor).
- **Acceptance.** sequence set satisfies the §3.7 minimum design (≥200 sequences
  target once scaled; a small dev set first).
- **Downstream.** WS-F, WS-G, WS-I.
- **Unresolved.** exact `N_Q` target confirmed by the WS-I-1 power simulation.

---

### WS-B-4 — Motif-axis split builder (`motif_id` in `split_group`)

- **Purpose.** The BUILD that does not exist today (`04` §6; `audit-converters.md`
  §2): add `motif_id` to `split_group` and a motif-grouped assignment so a held-out
  _motif family_ is reserved for the test split (H4 motif-transfer, `08` D3).
  Crossed with the repo axis: held-out repo × held-out motif is the strictest cell.
- **Prerequisites.** WS-A-4 (motif ids), WS-B-1 (Suite-A motif labels).
- **Files MODIFIED.**
    - `src/pneuma_lab/training/splits.py` — add `_group_examples_by_motif`
      paralleling `_group_examples`; extend `split_group` handling to carry a
      `motif_id`; cross the two axes; keep atomic group assignment + deterministic
      `sha256`-ordered assignment + `_repo_overlap`-style `_motif_overlap`
      self-check.
    - `schemas/` — extend the `split_group` shape (wherever declared) with an
      optional `motif_id` field.
- **Files CREATED.** none (extends existing).
- **Interfaces / schemas.** `split_group.motif_id`; split report gains a
  `motif_overlap` self-check field.
- **Data inputs.** converted example records carrying repo + motif labels.
- **Outputs.** split assignment + `hash_manifest.json`; per-split motif
  distribution table (`audit-converters.md` §6 gap 5).
- **Invariants.** motif family atomic across splits; deterministic; `70/15/15`
  default; `training_authorization.status = not_authorized`.
- **Failure modes.** a motif present in too few repos to hold out → report and
  fall back to reporting D3 on the motifs that can be held out (≥3 required,
  `08` §3.7).
- **Unit tests.** `tests/test_motif_split.py`: a held-out motif appears only in
  test; repo atomicity preserved simultaneously; `_motif_overlap` reports zero;
  determinism.
- **Integration tests.** build a crossed repo×motif split over a fixture corpus;
  assert the strictest cell is non-empty.
- **Acceptance.** motif-axis split reproducible, hash-bound, self-checking; ≥3
  held-out motifs available.
- **Downstream.** WS-G D3, WS-I, anti-gaming C-03/C-15.
- **Unresolved.** which motif families are held out (pre-registered in WS-I-2).

---

### WS-B-5 — Suite-B motif miner + N-judge labeling

- **Purpose.** Suite B labeling (`04` §3.5): mine motif labels over real
  Open-SWE-Traces / OpenHands-Sampled traces via rule prefilter (WS-A-4) + an
  N-judge ensemble at a pre-registered majority threshold; freeze labels before the
  H1 run and bind them into the artifact hash.
- **Prerequisites.** WS-A-4, WS-A-2.
- **Files CREATED.**
    - `src/pneuma_lab/benchmark/motif_miner.py` — rule prefilter over enriched
      traces → candidate motif instances; cross-attempt recurrence micro-mining
      (`04` §3.4 mode 1).
    - `src/pneuma_lab/benchmark/njudge.py` — N-judge ensemble interface (≥N
      independent judges, different providers/prompts); a label counts only on
      majority agreement; disagreement surfaced; κ reported (`10` C-12). Judges are
      _data, not gate_; the ensemble output is frozen.
    - `src/pneuma_lab/benchmark/suite_b_sequence.py` — constructed longitudinal
      sequences (`04` §3.4 mode 2): select real instances sharing a mined motif
      label, order exposure-first/post-exposure-later with distractors.
- **Files MODIFIED.** none.
- **Interfaces / schemas.** frozen `motif-labels` artifact (per instance: mined
  motif id, rule vote, judge votes, agreement, κ); Suite-B sequence records.
- **Data inputs (read-only).** processed `open_swe_traces` (160,731 traces,
  digest-only, `constructed_label`) + `openhands_sampled` (6,055 traces, real
  harness `report`) at `C:\pneuma-data\raw\{open-swe-traces,swe-gym}\`
  (`04` §3.2). The verifier lane is EXCLUDED (single-step, `04` §3.2).
- **Outputs.** `build/benchmark/suite_b/motif_labels.json` (frozen, hash-bound) +
  Suite-B sequence records.
- **Invariants.** labels frozen + hash-bound before H1 run (`04` §3.5, §3.7);
  Open-SWE outcomes stamped `constructed_label @ confidence: medium`, never
  `harness_outcome`; N-judge no single-judge promotion (`10` C-12); measured
  behaviour is OUR arms', not the corpus authors' (`04` §3.4).
- **Failure modes.** judge collusion / shared bias → require different providers +
  swap-test (`10` C-12); rule prefilter low recall → judges see all candidates,
  not only rule hits, for the precision gate.
- **Unit tests.** `tests/test_motif_miner.py`: miner flags a crafted recurring
  motif; N-judge majority logic; κ computed; frozen artifact is byte-stable.
- **Integration tests.** mine a bounded Open-SWE subset; assert label artifact
  shape + κ present. (No authorization: reads already-processed local traces.)
- **Experiment-level validation.** inter-judge κ reported; agreement threshold
  pre-registered (WS-I-2).
- **Acceptance.** frozen label artifact produced + hash-bound; κ ≥ pre-registered
  floor or disagreement surfaced and the low-agreement motifs reported separately.
- **Downstream.** WS-G (Suite-B RUF), WS-I.
- **Unresolved.** N (judge count) and majority threshold (pre-registered).

---

### WS-B-6 — Leakage quarantine + reproducibility binding extension

- **Purpose.** Enforce the 7-repo quarantine across suites and extend the
  reproducibility binding to cover checkpoint SHA, RNG seed, injector version, and
  frozen judge labels (`04` §3.6, §6; `audit-converters.md` §6 gaps 1–3).
- **Prerequisites.** WS-B-1, WS-B-4, WS-B-5.
- **Files MODIFIED.**
    - `src/pneuma_lab/training/leakage_registry.py` — reuse verbatim; assert
      `quarantine.repos == overlap set` (7 repos: conan, dask, hydra, moto, dvc,
      modin, pandas) as an invariant over the new suites.
    - `src/pneuma_lab/converters/*` or a new
      `src/pneuma_lab/benchmark/repro_binding.py` — extend the `hash_manifest.json`
      / `verify_estimator_run`-style binding to add `subject_checkpoint_sha`,
      `rng_seed`, `injector_version`, `frozen_judge_labels_sha`.
- **Files CREATED.** `src/pneuma_lab/benchmark/repro_binding.py` (if not folding
  into converters).
- **Interfaces / schemas.** extended manifest fields; `validate_corpus`
  quarantine invariant reused (`audit-converters.md` §3).
- **Data inputs.** the committed `cross-dataset-leakage-registry.json` (populated).
- **Outputs.** a binding manifest for every benchmark artifact.
- **Invariants.** 7 quarantined repos pinned to a single split across both lanes;
  Suite-A test templates exclude the 7 (`04` §2.6); every artifact reproducible
  from commit + config + seed.
- **Failure modes.** a new lane pairing not in the registry → the registry covers
  only D1×D2 today; any new pairing must be computed before use (`04` §3.6).
- **Unit tests.** `tests/test_repro_binding.py`: quarantine invariant enforced;
  manifest binds all four new fields; tamper (edit a byte) breaks the hash.
- **Integration tests.** build a benchmark artifact end-to-end; verify the binding
  round-trips and detects a simulated checkpoint-sha mismatch.
- **Acceptance.** quarantine invariant holds; binding covers checkpoint+seed+
  injector+labels; tamper detected.
- **Downstream.** WS-I official-run gate (WS-I-3), every experiment artifact.
- **Unresolved.** none.

---

## WS-C — Live agent driver + minimal ReAct scaffold (OUTSIDE `replay/`)

**Goal.** Build the seed/temperature-pinnable ReAct tool loop that all six
conditions share, OUTSIDE `src/pneuma_lab/replay/` (the replay harness drives
frozen trajectories and cannot drive a live stochastic agent — `02` §8.1;
`audit-interventions.md` §3, §6; `audit-nervous-system.md` §7 gap 1). Only the
memory/state module differs across conditions (`05` §1).

**Load-bearing dependency.** none on other workstreams for the skeleton; WS-C is
itself a root that WS-D and WS-F build on. The immutable-trace binding depends on
WS-B-6's binding pattern.

---

### WS-C-1 — Base-model serving + pinned decoding

- **Purpose.** Serve one frozen open-weight coding-capable instruct model locally
  with controllable temperature + seed so all conditions share identical decoding
  and we can draw N seeded samples per task (`02` §8.1; `05` §1.1). The local Qwen
  foundation subject is NOT the actor (`05` §4; `audit-foundation.md` §5).
- **Prerequisites.** none.
- **Repo area / files CREATED (new sibling package, outside `replay/`).**
    - `src/pneuma_lab/live_driver/__init__.py`
    - `src/pneuma_lab/live_driver/model_server.py` — a thin adapter over a local
      inference server exposing `generate(prompt, seed, temperature, top_p, stops,
max_new_tokens) -> completion` with a pinned checkpoint hash and a token
      meter.
- **Files MODIFIED.** none.
- **Interfaces / schemas.** a `run-config` record pinning checkpoint id + revision,
  decode params, budgets, retry cap, seed policy, bootstrap seed.
- **Data inputs.** a locally served model (external fixed artifact; checkpoint
  pinned in config). ≥2 model sizes for robustness (`02` §8.1; `08` §3.7).
- **Outputs.** deterministic-given-seed completions; per-call token count (feeds
  B2, `08`).
- **Invariants.** identical decoding across arms; checkpoint hash pinned; seed set
  `{σ_k}` shared across arms (`09` §1 counterbalancing).
- **Failure modes.** non-associative GPU float reductions break byte-identity even
  at fixed seed → handled by the statistical path (WS-F), not required here; but
  set deterministic-kernel flags where available (`09` §2 freeze table).
- **Unit tests.** `tests/test_model_server.py` (mocked backend): same seed → same
  completion under the mock; token meter counts; config pin enforced.
- **Integration tests.** two seeded calls under the mock reproduce; a changed seed
  diverges.
- **Acceptance.** deterministic-under-mock; config pin + token meter working;
  real-model wiring documented (execution gated on WS-I-3).
- **Downstream.** WS-C-2, WS-D, WS-F.
- **Unresolved.** the exact ≥2 checkpoints (pinned in run config, `05` §6).

---

### WS-C-2 — ReAct tool loop + fixed tool set

- **Purpose.** The minimal deterministic, seed-pinnable ReAct loop with EXACTLY the
  tool set `read_file`, `edit_file`, `run_tests`, `search`, `finish` — no condition
  adds/removes/renames a tool; memory rides the prompt channel, not a new tool
  (`02` §8.1; `05` §1.1).
- **Prerequisites.** WS-C-1.
- **Files CREATED.**
    - `src/pneuma_lab/live_driver/scaffold.py` — the ReAct loop: parser, turn
      structure, tool dispatch, finish criteria, budget/retry-cap enforcement.
    - `src/pneuma_lab/live_driver/tools.py` — the five tools over a sandboxed repo
      checkout (byte-identical env per `05` §1.2).
- **Files MODIFIED.** none.
- **Interfaces / schemas.** the loop consumes a task + a _memory/state module_ slot
  (WS-D) + the shared decision head slot (WS-E); emits an execution trace.
- **Data inputs.** a benchmark task (Suite A or B); the pinned env image.
- **Outputs.** per-step observable records (feed WS-A extraction inline) + the
  agent's final repo state (feeds the oracle WS-B-2).
- **Invariants.** identical loop control-flow, parser, finish criteria across arms
  (`05` §1.2 fairness matrix — must-be-identical rows); budget/action/retry caps
  identical; env byte-identical.
- **Failure modes.** budget exhaustion is a valid outcome, not an abort
  (`08` §3.6.2); a crash/timeout is an abort (listwise-deleted, `08` §3.6.1).
- **Unit tests.** `tests/test_scaffold.py`: tool dispatch; retry-cap + budget caps
  enforced; finish criteria; the memory-module slot is the only pluggable seam.
- **Integration tests.** run the Base module (WS-D-1) over one Suite-A task under
  the mock model; assert a well-formed trace + final state.
- **Acceptance.** loop deterministic-given-seed under the mock; all six condition
  slots pluggable without loop changes.
- **Downstream.** WS-D, WS-E, WS-F.
- **Unresolved.** search-tool semantics (grep vs semantic) — pin in run config;
  same across arms.

---

### WS-C-3 — Immutable trace binding (commit+config+seed) + env transcript

- **Purpose.** Every run emits an append-only trace bound to git commit,
  clean/dirty tree, checkpoint, config, and seed (`10` C-13; `02` §8.9); plus the
  recorded tool/env transcript the statistical causal path needs (`09` §2 freeze
  4; `audit-interventions.md` §6).
- **Prerequisites.** WS-C-2, WS-B-6 (binding pattern).
- **Files CREATED.**
    - `src/pneuma_lab/live_driver/trace_binding.py` — reuse the `--official`
      commit-provenance discipline (G-12, built) and bind checkpoint+config+seed
      into the same record (`10` C-13 partial→complete).
    - `src/pneuma_lab/live_driver/env_transcript.py` — record tool outputs,
      container filesystem deltas, test-runner verdicts keyed by `(task, tick,
action)` for fixed-transcript replay (`09` §2).
- **Files MODIFIED.** none (may reuse `foundation/artifacts.bind_artifact_publication`
  discipline, `audit-converters.md` §1).
- **Interfaces / schemas.** an immutable `execution-trace` record; the env
  transcript is digest-bound alongside the prompt (`09` §2 freeze table).
- **Data inputs.** the live run's steps + git state.
- **Outputs.** immutable trace + env transcript; both hash-bound.
- **Invariants.** `--official` fails closed on a dirty/unpublished tree
  (`10` C-13); a number with no matching immutable trace is rejected (recompute-
  don't-trust). No raw text in the trace frames (§0.5); transcript stores digests.
- **Failure modes.** env nondeterminism leaking into the delta → the transcript is
  the fixed replay (`09` §2); if the transcript itself is nondeterministic the run
  is aborted.
- **Unit tests.** `tests/test_trace_binding.py`: dirty tree blocks `--official`;
  binding covers commit+config+seed+checkpoint; tamper detected; transcript
  round-trips.
- **Integration tests.** run + rebind; assert reproducibility from commit+config+
  seed.
- **Acceptance.** immutable trace + transcript hash-bound; `--official` gate closed
  on dirty tree.
- **Downstream.** WS-F (freezes), WS-G (metric input is the immutable trace), WS-I.
- **Unresolved.** container/filesystem-delta capture granularity (coarse per-tool).

---

## WS-D — The six conditions as `PsycheUnderTest`-style modules

**Goal.** Implement the six conditions (`05` §2) as sibling pluggable modules in
the WS-C scaffold's memory/state slot, reusing the `PsycheUnderTest` /
`Perturbable` seam (`01` §4; `audit-psyche.md` §1). Only the memory/state module
and what it injects into the decision differ; everything else is held identical
(`05` §1.2).

**Load-bearing dependency.** WS-C (the slot), WS-E (the state + decision head that
Pneuma arms consume), WS-A-4 (the detector every arm reads the same signature
from, `05` §3).

---

### WS-D-1 — Base condition (no cross-task state) + shared decision head (zeroed)

- **Purpose.** The reference arm: no cross-task state; the decision head is attached
  but state-fed zeros so it always emits `proceed` — holding the action space
  identical across arms (`05` §2.1; `06` §6 "Holding the action-space constant").
- **Prerequisites.** WS-C-2, WS-E-6 (decision head).
- **Files CREATED.**
    - `src/pneuma_lab/conditions/__init__.py`
    - `src/pneuma_lab/conditions/base.py` — the Base module implementing the slot
      interface; head state feed zeroed.
- **Files MODIFIED.** none.
- **Interfaces / schemas.** the condition-slot interface (a small protocol:
  `openTask`, `onStep(record)`, `biasNextAction() -> (label, weight)`,
  `onTaskEnd()`); Base is the trivial implementation.
- **Data inputs.** task prompt + current trajectory only.
- **Outputs.** always `proceed` bias.
- **Invariants.** empty persistent store never written (`05` §2.1); defines the
  reference token/context occupancy curve (`05` §2.1 E-0 baseline).
- **Failure modes.** none beyond scaffold.
- **Unit tests.** `tests/test_condition_base.py`: head emits `proceed`; store never
  written; occupancy ~0 extra tokens.
- **Integration tests.** Base over a Suite-A sequence under the mock; trace valid.
- **Acceptance.** Base runs; head zeroed; ABL-01 anchor available.
- **Downstream.** WS-F, WS-G, ABL-01.
- **Unresolved.** none.

---

### WS-D-2 — Retrieval-memory condition (memory.py + cosine upgrade)

- **Purpose.** Store structured failure records per detected motif instance; at each
  decision retrieve top-k by similarity; inject the retrieved block into the prompt
  channel (`05` §2.2). Backed by `foundation/memory.py` SQLite/FTS5. Must be a
  STRONG baseline: wire cosine/embedding retrieval over the existing `embeddings`
  table (unimplemented today) so it matches on semantic similarity, not lexical
  only (`05` §3; `audit-foundation.md` §3, §6).
- **Prerequisites.** WS-C-2, WS-A-4 (failure signature).
- **Files MODIFIED.**
    - `src/pneuma_lab/foundation/memory.py` — add cosine/embedding similarity
      search over the existing `embeddings` table (stored, never queried today).
      Keep FTS5, hard-erasure receipts, all existing CRUD/tests green.
- **Files CREATED.**
    - `src/pneuma_lab/conditions/retrieval.py` — the retrieval module: writes a
      failure record after each task; queries top-k; formats a bounded memory block
      capped at `B_ret`.
- **Interfaces / schemas.** failure-record shape (motif id, repo, file/error-class
  digest, outcome, short snippet); `B_ret` retrieval token budget.
- **Data inputs.** past failure records; the current trajectory failure signature.
- **Outputs.** retrieved memory block (prompt channel); per-decision injected-token
  count logged (`05` §2.2 E-0 equalization).
- **Invariants.** no new tool (memory rides the prompt); decision head sees no
  numeric state (retrieval conditions the LM only); `training_weight: 0.0`;
  erasure receipts as a clean ablation lever (ABL-05).
- **Failure modes.** decoy/irrelevant retrievals crowd the window (measured);
  lexical-only would miss paraphrase → cosine upgrade required; stale records
  mislead on counterfactuals (H5 exposure).
- **Unit tests.** `tests/test_condition_retrieval.py`: cosine retrieval returns
  semantically-near records the FTS5 path misses; top-k + `B_ret` cap enforced;
  record written after task; injected-token count logged.
- **Integration tests.** retrieval over a Suite-A recurrence sequence; assert a
  post-exposure decision receives the exposure's record.
- **Experiment-level validation.** memory-retrieval precision (E1, `08`) computed.
- **Acceptance.** cosine retrieval works; `foundation/memory.py` existing tests
  still green; strong-baseline criteria (real embeddings, tuned k) met.
- **Downstream.** WS-E-4 (`r` reads this channel), WS-F (A5/A6 arms), WS-G E1,
  ABL-05/ABL-14.
- **Unresolved.** embedding source for records (a local encoder or the model's own
  embeddings) — pin in run config; same across the retrieval arm and `r`.

---

### WS-D-3 — Reflection condition (Reflexion/ExpeL loop)

- **Purpose.** After a failed task, write a natural-language lesson into a
  persistent lesson buffer; select applicable lessons on later tasks; inject a
  lessons block into the prompt (`05` §2.3). A real reflect→store→re-condition loop
  with an accumulating ExpeL-style library, recency/similarity-scoped selection, a
  tuned `B_ref` (`05` §3).
- **Prerequisites.** WS-C-2.
- **Files CREATED.**
    - `src/pneuma_lab/conditions/reflection.py` — reflect step (runs the real actor
      model), lesson store, lesson selection, lessons block capped at `B_ref`.
- **Files MODIFIED.** none.
- **Interfaces / schemas.** lesson record (task/motif context, lesson text); the
  reflect step's token cost metered against the shared per-task budget (`05` §2.3).
- **Data inputs.** failed-task trajectory; accumulated lessons.
- **Outputs.** lessons block (prompt channel); reflect-step token cost logged.
- **Invariants.** the reflect generation is metered against the shared budget so
  reflection cannot buy extra actor compute (`05` §2.3); prose never scores RUF
  (firewall, §0.3); no new tool.
- **Failure modes.** persuasive-but-wrong lessons (the diary problem — the reason
  for the behaviour-vs-report firewall, `02` §7); lesson drift as the buffer grows;
  over-generalized lessons → over-avoidance on counterfactuals (H5).
- **Unit tests.** `tests/test_condition_reflection.py`: lesson written on failure;
  selection scoped by recency/similarity; `B_ref` cap; reflect tokens metered.
- **Integration tests.** reflection over a recurrence sequence; a lesson from the
  exposure appears on a later task.
- **Acceptance.** genuine Reflexion loop; budget-metered; strongest standard ExpeL
  config (not a canned note).
- **Downstream.** WS-F, WS-G, ABL-06 (structured-vs-text), C-11 (misleading
  reflections).
- **Unresolved.** lesson-selection scope (recency vs similarity) — tuned on a
  held-out slice (`05` §3), pinned in prereg.

---

### WS-D-4 — Pneuma-state condition (4 vars → decision head)

- **Purpose.** The H1 treatment: four persistent numeric variables carried
  task→task feeding the bounded decision head via `L`, biasing the next action;
  injects almost no prose (the treatment rides the head, not the window)
  (`05` §2.4; `06` §1).
- **Prerequisites.** WS-E (all four variables + `L` + head), WS-A-4 (detector),
  WS-C-2.
- **Files CREATED.**
    - `src/pneuma_lab/conditions/pneuma_state.py` — wires the WS-E state vector +
      decision head into the condition slot; loads/saves the vector cross-run via
      the WS-E-5 store.
- **Files MODIFIED.** none.
- **Interfaces / schemas.** consumes `DetectionSet` (WS-A-4) and the retrieval
  channel (gated by `r`, WS-E-4); emits `(action_label, bias_weight)`.
- **Data inputs.** detection stream; retrieved memory (gated by `r`); prior vector
  from the store.
- **Outputs.** action bias; the full state vector serialized cross-run; causal-trace
  receipts (`06` §3.1 provenance).
- **Invariants.** state is scalars (injected-token footprint ~Base, `05` §2.4);
  emits pressure not commands (§0.4); deterministic given detection stream + seed
  (`06` §5).
- **Failure modes.** over-caution/inertia (H5 guards); mis-calibrated `c` inflating
  `L`; a wrong motif id poisoning `s_m` (measured on Suite A exact oracle).
- **Unit tests.** `tests/test_condition_pneuma.py`: state loads/saves; head fed
  live `L`; receipts written; near-Base token footprint.
- **Integration tests.** Pneuma-state over a recurrence sequence; assert `s_m`
  grows on exposure and biases a post-exposure decision toward verification.
- **Experiment-level validation.** the H1 RUF contrast (WS-G, WS-I).
- **Acceptance.** runs; state persists; head coupling live; footprint ~Base.
- **Downstream.** WS-F (all clamp arms), WS-G, WS-H, most ablations.
- **Unresolved.** none beyond WS-E's constants.

---

### WS-D-5 — Retry-count heuristic controller (mandatory falsifier)

- **Purpose.** The trivial non-learned controller: count consecutive
  near-identical retries; at threshold `N` drive the SAME decision head to
  `deepen_verification`/`switch_strategy` (`05` §2.5). Exists specifically to
  falsify us (E-0 lesson: retry-count beat psyche signals, AUROC 0.71 vs 0.34,
  `01` §7; `02` §6). Tuned `N`, not crippled (`05` §3).
- **Prerequisites.** WS-E-6 (head), WS-C-2.
- **Files CREATED.**
    - `src/pneuma_lab/conditions/retry_count.py` — a per-task integer counter;
      threshold `N`; drives the same head ladder with `L` replaced by the counter.
- **Files MODIFIED.** none.
- **Interfaces / schemas.** reads the shared retry cap; no cross-task store.
- **Data inputs.** the running retry count within a task.
- **Outputs.** action bias after `N` identical retries.
- **Invariants.** ~zero extra tokens (cleanest budget match to Base, `05` §2.5);
  the retry cap is _read_, not raised.
- **Failure modes.** fires only on repeated identical retries within a task
  (blind to cross-task recurrence and motif identity) — by design.
- **Unit tests.** `tests/test_condition_retry.py`: counter increments on identical
  retries; head fires at `N`; no cross-task carry.
- **Integration tests.** retry-count over a sequence; assert it cannot reduce
  cross-task first-instance recurrence.
- **Acceptance.** runs through the same head; `N` tunable; zero extra tokens.
- **Downstream.** WS-G (H1 falsification guard), WS-I.
- **Unresolved.** `N` (tuned on held-out slice, pinned in prereg).

---

### WS-D-6 — Pneuma-state-ablated (null; H2 causal control)

- **Purpose.** Full Pneuma machinery running but `s_m` clamped to baseline via the
  `scar_graph` seam, so failure memory never accumulates while `c`/`t`/`r` still
  update — the surgical H2 contrast (`05` §2.6; `06` §3.1 intervention hook).
- **Prerequisites.** WS-D-4, WS-E-1 (`s_m` + `scar_graph` clamp), WS-F-1 (clamp
  application on the live path).
- **Files CREATED.**
    - `src/pneuma_lab/conditions/pneuma_ablated.py` — Pneuma-state with a standing
      `clamp(scar_graph, baseline)` intervention installed.
- **Files MODIFIED.** none (reuses the `scar_graph` `PerturbationSet` seam).
- **Interfaces / schemas.** identical action space/actuation path to WS-D-4; only
  `s_m` is dead.
- **Data inputs.** as WS-D-4 with `s_m` pinned.
- **Outputs.** action bias with baseline `L` (memory term neutralized).
- **Invariants.** identical token/context footprint to WS-D-4 (H2 auto
  budget-matched, `05` §2.6); this is a clean null, not "head off."
- **Failure modes.** by construction should behave near Base on RUF; if
  `RUF(ablated) ≈ RUF(pneuma)` then `s_m` epiphenomenal → H2 false (publishable
  negative, `02` §6).
- **Unit tests.** `tests/test_condition_pneuma_ablated.py`: `s_m` pinned at
  baseline; `c`/`t`/`r` still update; footprint identical to WS-D-4.
- **Integration tests.** paired against WS-D-4 on a sequence; assert the only
  divergence is the `s_m` term.
- **Acceptance.** clean null arm; budget-matched to WS-D-4.
- **Downstream.** WS-F (A3/A1 contrast), WS-G, ABL-11.
- **Unresolved.** none.

---

## WS-E — Internal-state variables + decision head

**Goal.** Implement the four persistent variables (`s_m`, `c`, `t`, `r`), the
derived `L`, and the bounded decision head exactly per `06`, extending existing
psyche seams with decay/cap/real-trigger/EMA and the NEW `memory_trust` scalar +
`PerturbationSet` dimension, all serialized cross-run so persistence is _measured_,
not asserted (`06` §0, §8).

**Load-bearing dependency.** WS-A-4 (`detectFailure` is the single upstream
dependency of `s_m`, `t`, `c`, `06` §2.1). Every constant is pinned in the run
config and listed in `15-decision-log.md`.

---

### WS-E-1 — `s_m` failure-sensitivity: real trigger + decay + cap + similarity

- **Purpose.** The primary H1/H2 variable. Replace the fixture-fed `+0.15`-on-
  anomaly rule with the real detector trigger + decay `LAMBDA_S` + cap `CAP_S` +
  similarity amplification `RHO_S` (`06` §3.1).
- **Prerequisites.** WS-A-4.
- **Files MODIFIED.**
    - `src/pneuma_lab/nervous_system/scar_memory.py` — the update rule
      `s_m ← clip(min(CAP_S, s_m(1−LAMBDA_S) + ALPHA_S·δ_m·(1+RHO_S·a_m)))` applied
      to every motif each tick, decay on undetected motifs too; keep flat-JSON
      byte-stable store.
    - `src/pneuma_lab/psyche/reference.py` — if the Pneuma-state arm reuses
      `ReferencePsyche`'s `scars`, route its growth through the new rule and feed
      `L` (not the ad-hoc `expected_loss`).
- **Files CREATED.** `src/pneuma_lab/state/constants.py` — pinned `ALPHA_S=0.15`,
  `LAMBDA_S=0.02`, `RHO_S=1.0`, `CAP_S=0.90`, `SEED_S=0.2` (and all other WS-E
  constants).
- **Interfaces / schemas.** new `psyche_state.failure_sensitivity: {motif_id: s_m}`
  observability field; serialization `{motif_id: round(s_m,6)}` sorted.
- **Data inputs.** `DetectionSet` (`δ_m`, `a_m`); prior `s_m` from the store.
- **Outputs.** updated `s_m` dict; per-motif observability field; causal-trace
  receipt binding the detection digest + prior/new `s_m`.
- **Invariants.** decay applies to un-detected motifs (avoidance fades, `06` §3.1);
  bounded by `CAP_S`; deterministic; receipt per increment (`06` §3.1 provenance).
- **Failure modes.** motif-id instability, runaway saturation (cap), over-avoidance
  (decay + H5), detector false positives (measured on Suite A).
- **Unit tests.** `tests/test_sm.py`: `a_m=0` moves `0.2→0.35` (legacy parity);
  `a_m=1` moves `0.2→0.50`; `CAP_S` caps at 0.90; decay-only multiplies by
  `(1−LAMBDA_S)`; clip `[0,1]`.
- **Integration tests.** persistence (run A then B on a shared store: run-B tick-0
  `s̄` > run-A tick-0; state hashes differ — a real detection, not a fixture,
  `06` §3.1 persistence test).
- **Experiment-level validation.** H2 dose-response (`08` F2); Suite A ablate/clamp.
- **Acceptance.** rule matches `06` §3.1 exactly; persistence measured, not
  asserted.
- **Downstream.** WS-E-7 (`L`), WS-D-4/6, WS-F, ABL-09/10/11.
- **Unresolved.** none (constants pinned).

---

### WS-E-2 — `c` confidence: real target + EMA Brier

- **Purpose.** Brier-calibrated self-reliability. Keep the existing Brier spine but
  target the REAL observed failure from `detectFailure` and use a windowed EMA so
  `c` moves both ways and forgets stale performance (`06` §3.2).
- **Prerequisites.** WS-A-4.
- **Files MODIFIED.**
    - `src/pneuma_lab/psyche/reference.py` — the `self_model_reliability` /
      `calibration_error` loop: replace cumulative-mean Brier with EMA `BETA_C=0.2`;
      set the prediction target `o = 1[∃m: δ_m>0]`; preserve the one-tick
      predictive gap (`_pending_error_prediction`).
- **Files CREATED.** none (constants in `state/constants.py`).
- **Interfaces / schemas.** `psyche_state.self_model.reliability = c`,
  `psyche_state.calibration_state.brier_ema = B`; serialize `{c, brier_ema}`.
- **Data inputs.** self-model uncertainty `u`; scar aggregate `s̄`; next-tick
  observed failure `o`.
- **Outputs.** updated `c`; per-resolve receipt.
- **Invariants.** prediction formed BEFORE the next observation (no target leak,
  `06` §3.2 failure mode a); EMA forgetting; `c=0.5` before first resolve.
- **Failure modes.** circular target (guarded by predictive gap); slow start
  (flagged); confound with `s_m` (H2 clamps independently).
- **Unit tests.** `tests/test_c.py`: over-prediction lowers `c`; accurate raises;
  `c=0.5` pre-resolve; `BETA_C` applied; bounds `[0,1]`.
- **Integration tests.** clamp `c` via `self_model`; head distribution shifts, null
  holds.
- **Experiment-level validation.** state calibration Brier/ECE (`08` E2).
- **Acceptance.** EMA + real target; two-way movement.
- **Downstream.** WS-E-7 (`L`), ABL-12, WS-H (H3 "under-confident").
- **Unresolved.** none.

---

### WS-E-3 — `t` caution: real appraisal drive + explicit decay

- **Purpose.** Fast recurrent caution scalar. Adopt the recurrent manifold form but
  drive appraisal from the real detected-failure strength `d_n = max_m δ_m` and add
  named decay `GAMMA_T`; route to behaviour ONLY via `L` (remove the separate
  pressure path) (`06` §3.3).
- **Prerequisites.** WS-A-4.
- **Files MODIFIED.**
    - `src/pneuma_lab/psyche/reference.py` / `src/pneuma_lab/psyche/manifold.py` —
      the tension update
      `t ← clip(K_T·t + (1−K_T)(A_T·d_n + B_T·s̄) − GAMMA_T·t, −1, 1)` with
      `K_T=0.5`, `A_T=0.6`, `B_T=0.3`, `GAMMA_T=0.05`; feed `L` via `ReLU(t)` and
      remove the direct verification-pressure path (single auditable coupling).
- **Files CREATED.** none.
- **Interfaces / schemas.** `psyche_state.affect.tension = t`; serialize `{t}`.
- **Data inputs.** `d_n` (real detection); `s̄`.
- **Outputs.** updated `t`; per-tick receipt.
- **Invariants.** `ReLU(t)` floors negative `t` at 0 in `L` (positive-only
  pressure, `06` §3.3 failure mode c); recurrent inertia; deterministic.
- **Failure modes.** over-damping (dose-response test), collinearity with `s_m`
  (H2 clamps independently), sign confusion (`ReLU` guard).
- **Unit tests.** `tests/test_t.py`: a detected failure raises `t`; a benign tick
  decays toward 0; `K_T` inertia applied; bounds `[−1,1]`; `ReLU` floor in `L`.
- **Integration tests.** clamp `t=0` via `affect_manifold`; state hash + head
  shift, null holds.
- **Acceptance.** real-driven; single `L` coupling; named constants.
- **Downstream.** WS-E-7, ABL-13.
- **Unresolved.** none.

---

### WS-E-4 — `r` memory-trust (NEW scalar) + `memory_trust` PerturbationSet dim

- **Purpose.** The entirely new dedicated scalar weighting how much retrieved memory
  influences the decision, the honest hinge for the retrieval-baseline contrast
  (`06` §3.4). Plus the NEW `memory_trust` `PerturbationSet` dimension (`06` §2.2).
- **Prerequisites.** WS-D-2 (retrieval channel), WS-A-4 (recurrence for `q_n`).
- **Files CREATED.**
    - `src/pneuma_lab/state/memory_trust.py` — the `r` update
      `r ← clip(r + ETA_R·q_n − LAMBDA_R·(r−0.5), 0, 1)` with `ETA_R=0.1`,
      `LAMBDA_R=0.02`; `q_n ∈ {−1,0,+1}` from `detectFailure` recurrence.
- **Files MODIFIED.**
    - `src/pneuma_lab/interventions/perturbation.py` and
      `src/pneuma_lab/interventions/operations.py` — add a `memory_trust` scalar
      dimension with `clamp`/`boost`/`noise` semantics (parity with
      `affect_manifold` scalar ops).
    - `schemas/intervention-frame.schema.json` — add `memory_trust` to the target
      subsystem enum.
- **Interfaces / schemas.** `psyche_state.memory_trust = r`; new `memory_trust`
  perturbation target; serialize `{r}`.
- **Data inputs.** retrieval-usefulness signal `q_n` (surfaced memory + failure
  avoided → +1; surfaced + recurred → −1; none → 0), computed from recurrence.
- **Outputs.** `r` as a GAIN on the retrieval channel feeding the head (NOT a term
  in `L`, `06` §3.4); per-tick receipt binding the retrieved-record digest.
- **Invariants.** `q_n` comes from `detectFailure` recurrence, NOT self-report
  (prevents reward hacking, `06` §3.4 failure mode b); `r` reverts to 0.5 absent
  evidence; deterministic.
- **Failure modes.** sparse signal → `r` inert (measured; cut candidate per
  invariant 4 if the H2 clamp shows no delta); confound with the retrieval baseline
  (clean by construction — `r` only exists in the Pneuma arm).
- **Unit tests.** `tests/test_r.py`: `q=+1` raises, `q=−1` lowers, `q=0` decays to
  0.5; bounds; `ETA_R`/`LAMBDA_R` applied; `memory_trust` dim accepts
  clamp/boost/noise and rejects out-of-`[0,1]` (parity test).
- **Integration tests.** clamp `r=0` via `memory_trust`; the retrieval-derived head
  bias is zeroed and the arm matches the endogenous-only variant; null holds.
- **Acceptance.** `r` new-scalar behaviour correct; new seam tested to parity with
  existing scalar ops.
- **Downstream.** WS-E-6 (head gain), WS-F (A-arms on memory), ABL-14, WS-G E1.
- **Unresolved.** whether `r` survives its cut criterion (decided post-experiment,
  `06` §7).

---

### WS-E-5 — Cross-run state store + `reset()` semantics

- **Purpose.** Persist the full vector `(\{s_m\}, c, t, r)` keyed by
  `(agent_condition, subject_model, seed, task_sequence_id)`; make `reset()`
  explicit (`06` §2.3, §5). Reuse `foundation/memory.py` as the serialization
  backend.
- **Prerequisites.** WS-E-1..4, WS-D-2 (memory backend already extended).
- **Files CREATED.**
    - `src/pneuma_lab/state/store.py` — canonical (sorted keys, 6-dp) serialize /
      deserialize of the vector over the SQLite store; keyed load/save.
- **Files MODIFIED.**
    - `src/pneuma_lab/nervous_system/subject.py` — `reset()` restores the _arm's_
      seeded vector (not clear), so paired arms start identical and do not leak
      state (`06` §5; `audit-nervous-system.md` §4).
- **Interfaces / schemas.** the store key tuple; the canonical vector format.
- **Data inputs.** the run key; prior vector.
- **Outputs.** loaded vector at run start, saved at run end.
- **Invariants.** within a task sequence the vector persists (H1/H2 persistence
  lives here); between paired arms `reset()` restores the seed (ordinal-invariant);
  byte-stable serialization (`06` §5).
- **Failure modes.** state leaking across arms (guarded by reset semantics);
  unknown motifs default to 0 on load.
- **Unit tests.** `tests/test_state_store.py`: round-trip byte-stable;
  keyed isolation; `reset()` restores seed, does not clear.
- **Integration tests.** two runs sharing a store accumulate; paired arms do not.
- **Acceptance.** persistence measurable; reset semantics per `06` §5.
- **Downstream.** WS-D-4/6, WS-F, ABL-04.
- **Unresolved.** none.

---

### WS-E-6 — Derived `L` + bounded decision head

- **Purpose.** `L = clip(W1·s̄ + W2·(1−c) + W3·ReLU(t))` with `W1=0.6, W2=0.2,
W3=0.2` (`06` §4); the deterministic threshold-ladder decision head over the
  fixed action-shaping set with motif overrides, retry-aware stop, and the
  `r`-gated additive-only retrieval bias (`06` §6).
- **Prerequisites.** WS-E-1..5.
- **Files CREATED.**
    - `src/pneuma_lab/state/derived_loss.py` — `L` computation.
    - `src/pneuma_lab/state/decision_head.py` — `decisionHead(L, r, m_star,
retrieval_hint, retry_count) -> (action_label, bias_weight)` per the `06` §6
      ladder (`THETA_LOW=0.30`, `THETA_MED=0.55`, `THETA_HIGH=0.75`, `RETRY_STOP`,
      `DESTRUCTIVE_MOTIFS`); monotone-caution, additive-only retrieval bias.
- **Files MODIFIED.** none.
- **Interfaces / schemas.** the action-shaping set
  `{proceed, deepen_verification, run_tests_before_edit, switch_strategy,
re_read_repo_structure, escalate_or_ask, stop_and_report}`;
  `psyche_state.derived_signals.expected_loss = L`.
- **Data inputs.** the state vector; `m_star = argmax_{active} s_m`; retrieval hint;
  retry count.
- **Outputs.** `(action_label, bias_weight)` + a `pressure` causal-trace node.
- **Invariants.** monotone caution (never relaxes below the Tier-1 floor); pressure
  not command (§0.4); pure/deterministic; the SAME head attached to Base (zeroed)
  and retry-count (`L` replaced by the counter) to hold the action space constant
  (`06` §6).
- **Failure modes.** weight mis-set masks a contributor (per-input H2 clamps make
  each marginal measurable); saturation (`CAP_S` on the dominant term prevents it).
- **Unit tests.** `tests/test_decision_head.py`: `L` monotone in each input;
  ladder thresholds; motif overrides only escalate; retry-stop; retrieval bias
  additive-only and cannot lower caution; zeroed feed → always `proceed`.
- **Integration tests.** dose-response — seed `s_m ∈ {0.0,0.3,0.6,0.9}`, assert
  head caution bias monotone (`06` §3.1 dose-response).
- **Acceptance.** head deterministic; matches `06` §6 pseudocode; A7 edge
  (state→L) is cuttable (WS-F-1).
- **Downstream.** WS-D-1/4/5/6, WS-F (A7 influence-disabled), ABL-02/07/08/19.
- **Unresolved.** thresholds `THETA_*`, `RETRY_STOP` (pinned in run config /
  prereg).

---

### WS-E-7 — Per-variable observability fields + causal-trace receipts

- **Purpose.** Expose each variable via structured frame fields with receipts read
  by the prose-blind evaluator, extending the existing
  `event → internal_state → pressure` receipt chain (`06` per-variable
  observability; `audit-nervous-system.md` §4).
- **Prerequisites.** WS-E-1..6.
- **Files MODIFIED.**
    - `schemas/psyche-state-frame.schema.json` — add `failure_sensitivity` map,
      `memory_trust`, `derived_signals.expected_loss`, `calibration_state.brier_ema`
      (all optional; keep `additionalProperties: true`).
    - `src/pneuma_lab/nervous_system/frames.py` / `subject.py` — emit the new
      fields + per-variable receipts.
- **Files CREATED.** none.
- **Interfaces / schemas.** the enriched `psyche_state` frame + receipt nodes.
- **Data inputs.** the state updates.
- **Outputs.** schema-valid frames with per-variable receipts.
- **Invariants.** receipts bind each update to its detection/resolve digest
  (auditable); prose-blind (numeric fields only, §0.3).
- **Failure modes.** referential integrity — receipt strings must resolve (harness
  check, `audit-schemas.md` §2); WS-G adds the resolver.
- **Unit tests.** `tests/test_state_observability.py`: each field emitted +
  schema-valid; receipts present per update.
- **Integration tests.** a full Pneuma tick emits all fields + a complete receipt
  chain.
- **Acceptance.** all four variables + `L` observable + receipt-bound.
- **Downstream.** WS-G (metric inputs), WS-H (H3), ABL-17.
- **Unresolved.** none.

---

## WS-F — Statistical causal harness

**Goal.** Build the statistical real-agent causal path (`09` §2): four freezes
(seed, prompt, retrieved memory, tool/env transcript), branch-divergence metric,
N-sample distributional nulls with bootstrap effect sizes — replacing `sha256`
byte-equality which caps a stochastic agent at L3 (`audit-interventions.md` §3).
Reuse the deterministic `PairedReplayRunner` verbatim for the synthetic oracle
sub-experiments (`09` §3).

**Load-bearing dependency.** WS-C-3 (freezes/transcript), WS-E (clamp seams),
WS-D (arms). The nine intervention arms (A0–A8, `09` §1) are realized here.

---

### WS-F-1 — Live-path intervention application (clamp/ablate/disable/noise + A7 edge cut)

- **Purpose.** Apply the operation taxonomy (`clamp/boost/noise/disable/ablate/
restore`) on the LIVE state vector, including the sharp A7 "influence-disabled"
  edge cut `state→L = 0` (state updates + fully observable but decoupled from the
  decision, `09` §1.1). Add the missing memory-scramble op (A6) and memory-delete
  (A5) on the store (`audit-interventions.md` §6 gap 4).
- **Prerequisites.** WS-E-6, WS-E-4 (memory_trust dim), WS-D-2 (store).
- **Files MODIFIED.**
    - `src/pneuma_lab/interventions/operations.py` — reuse clamp/boost/noise/
      disable/ablate/restore; ensure `noise` can scramble a scar/retrieval SET
      deterministically (A6), and `disable`/`ablate` can delete a store row /
      retrieval index (A5).
    - `src/pneuma_lab/state/decision_head.py` — add a switchable `state→L` edge
      that can be cut to 0 while state keeps updating (A7).
- **Files CREATED.**
    - `src/pneuma_lab/live_driver/intervene.py` — installs an active
      `PerturbationSet` on the live arm before each tick (mirrors
      `set_active_interventions` but on the live path).
- **Interfaces / schemas.** the nine-arm roster A0–A8 (`09` §1.1) maps onto these
  ops.
- **Data inputs.** the arm spec (op, target, intervention tick).
- **Outputs.** an intervened live run + its causal-trace receipts.
- **Invariants.** control/treated/null differ ONLY in the intervened variable up to
  the clamp (`09` §2); A7 keeps the `s_m` trace unchanged vs A1 (`09` §1.1); noise
  is deterministic (`operations.deterministic_noise`, sha256-folded).
- **Failure modes.** off-target leak (the arm's off-target frames drift) → rejected
  before scoring (`09` §1.2 replay-equivalence).
- **Unit tests.** `tests/test_live_intervene.py`: each op edits the intended target
  only; A7 cuts the edge while state updates; A6 scramble deterministic; A5 deletes.
- **Integration tests.** A1 vs A0 on a Suite-A sequence diverges only at/after the
  clamp tick.
- **Acceptance.** nine arms realizable on the live path; memory-scramble/delete
  ops added.
- **Downstream.** WS-F-2, WS-F-4, WS-D-6, all clamp ablations.
- **Unresolved.** none.

---

### WS-F-2 — Four freezes (seed / prompt / retrieved memory / env transcript)

- **Purpose.** Snapshot per tick so control/treated/null share an identical decode
  path up to the intervention and diverge only at the clamp (`09` §2 freeze table).
- **Prerequisites.** WS-C-3 (transcript + binding), WS-C-1 (seed), WS-D-2
  (retrieval), WS-D-3.
- **Files CREATED.**
    - `src/pneuma_lab/live_driver/freezes.py` — capture/replay of: frozen model
      seed set `{σ_k}`; frozen realized prompt string per tick; frozen retrieved-
      memory set + order; recorded tool/env transcript (from WS-C-3).
- **Files MODIFIED.**
    - `src/pneuma_lab/live_driver/trace_binding.py` — extend `input_frames_sha256`
      binding to the FULL realized prompt + retrieval context (`09` §2; §1.2).
- **Interfaces / schemas.** the frozen-input bundle digest-bound in the trace.
- **Data inputs.** the live run's prompts, retrieved sets, tool outputs, seeds.
- **Outputs.** a frozen-input record per tick, digest-bound.
- **Invariants.** the only remaining divergence between two rollouts of the same
  arm-seed pair is the model's sampling (pinned by seed); between arms at a fixed
  seed, only the intervened variable diverges (`09` §2).
- **Failure modes.** freeze leakage (treated diverges before the clamp) → detected
  by WS-F-3's `τ* ≥ t_intervention` check and the run invalidated.
- **Unit tests.** `tests/test_freezes.py`: same arm-seed rollout replays from the
  frozen bundle; a changed intervened variable is the only cross-arm delta.
- **Integration tests.** control and null share the transcript and diverge nowhere
  off-target.
- **Acceptance.** four freezes captured + digest-bound; replay from frozen inputs
  reproduces the arm-seed rollout.
- **Downstream.** WS-F-3, WS-F-4.
- **Unresolved.** transcript completeness for tools with hidden state (pin the
  sandbox image; `05` §1.2).

---

### WS-F-3 — Branch-divergence metric + N-sample distributional nulls (TOST + bootstrap)

- **Purpose.** Replace boolean `ordinal_invariant`/`clone_equivalent` with a
  divergence measurement (onset `τ*`, magnitude curve, null floor) and replace the
  point-scalar delta with paired distributional contrasts: treated bootstrap CI
  excludes 0; null TOST equivalence inside `±band`; dose-response slope
  (`09` §2). Add pluggable behavioural extractors replacing the 5 hardcoded psyche
  signals (`audit-interventions.md` §6 gap 2).
- **Prerequisites.** WS-F-1, WS-F-2, WS-G-1 (the RUF extractor it scores).
- **Files MODIFIED.**
    - `src/pneuma_lab/interventions/report.py` — `extract_signal` gains pluggable
      behavioural extractors (did-it-repeat-the-failure/RUF, retry count, tool-call
      pattern) instead of the 5 whitelisted psyche signals; keep the existing
      `_direction_ok` `bounded_change`/`no_change` tolerance seam (`09` §2).
- **Files CREATED.**
    - `src/pneuma_lab/causal/divergence.py` — `τ*` onset, per-tick TV/KL magnitude
      over K seeds, null floor.
    - `src/pneuma_lab/causal/distributional_null.py` — paired bootstrap of
      `RUF(treated)−RUF(control)`; TOST equivalence of `RUF(null)−RUF(control)`;
      dose-response regression of `ΔRUF` on erased/clamped `s_m`.
- **Interfaces / schemas.** the causal contrast result (Δ, CI, `d_z`, `τ*`, null
  TOST verdict).
- **Data inputs.** K seeded rollouts per arm per task (paired by seed); the RUF
  extractor.
- **Outputs.** per-arm distributional verdict + divergence curve.
- **Invariants.** the causal claim is a property of the DISTRIBUTION over K seeded
  rollouts, never a single byte string (`09` §1); `τ* ≥ t_intervention` required
  (pre-clamp divergence = freeze leak, invalidates the arm); null must be
  distributionally indistinguishable from control (`09` §2, §4).
- **Failure modes.** pre-clamp `τ*` (freeze leak) vs genuine stochastic-only null —
  each diagnosis actionable (`09` §3 corroboration table).
- **Unit tests.** `tests/test_distributional_null.py`: bootstrap CI on a synthetic
  shift excludes 0; TOST accepts an equivalent null and rejects a shifted one;
  `τ*` detects onset; dose-response slope sign.
- **Integration tests.** run A0/A1/A2 with K seeds over a small Suite; assert A1 CI
  excludes 0 (if effect present), A2 TOST holds, `τ* ≥ t_int`.
- **Experiment-level validation.** the oracle path (WS-F-4) must recover the same
  delta at K→large (calibration, `09` §3).
- **Acceptance.** distributional null + divergence working; pluggable extractors;
  reuses `_direction_ok` tolerance.
- **Downstream.** WS-G F2, WS-I, all clamp ablations, H2.
- **Unresolved.** `K`, tolerance `band`, TOST margin (pinned in prereg WS-I-2).

---

### WS-F-4 — Reuse deterministic `PairedReplayRunner` for the synthetic oracle

- **Purpose.** Over Suite A (exact motif ground truth) build a deterministic oracle
  subject (a `PsycheUnderTest` whose action given frozen input is a pure function)
  and drive it through the EXISTING `PairedReplayRunner` UNMODIFIED — byte-equality
  nulls satisfiable, strongest gate for free (`09` §3; `04` §2.1). This is the
  positive control for the instrument.
- **Prerequisites.** WS-B-1/2/3 (Suite A), WS-E (state math), WS-F-1 (op mapping).
- **Files CREATED.**
    - `src/pneuma_lab/causal/oracle_subject.py` — a deterministic
      `PsycheUnderTest`+`Perturbable` oracle over Suite-A frozen inputs (pure
      function), so `certify()` passes (clone/reset/ordinal) and yields a genuine
      Level-4-eligible provenance record for these sub-experiments only.
- **Files MODIFIED.** none (runner reused verbatim, `09` §3).
- **Interfaces / schemas.** the existing arm roster maps: clamp=A3, disable/ablate=
  A5/A7, noise=A6, restore=A2/A4-null (`09` §3).
- **Data inputs.** Suite-A sequences + injected motif ground truth.
- **Outputs.** exact scalar deltas; byte-reproducible null.
- **Invariants.** null byte-reproduces control; counterbalanced 3-order provenance;
  the mind never scores itself (recompute-from-receipts, `audit-interventions.md`
  §1).
- **Failure modes.** a mis-specified clamp / off-target leak surfaces exactly here
  (isolates instrument error from scientific null, `09` §3).
- **Unit tests.** `tests/test_oracle_subject.py`: clone/reset/ordinal pass;
  byte-equal null; each op arm produces the predicted exact delta.
- **Integration tests.** the oracle's known delta is recovered by the WS-F-3
  distributional estimator at K→large (cross-path calibration).
- **Acceptance.** oracle path certifies the divergence metric + bands + extractors;
  both paths agree on a shared motif.
- **Downstream.** WS-I (positive control), corroboration table in the paper.
- **Unresolved.** none.

---

## WS-G — Metrics + prose-blind behavioural evaluator + anti-gaming

**Goal.** Implement RUF + the secondary metric panel (`08`), the prose-blind
behavioural evaluator (`10` firewall), and the anti-gaming controls C-03..C-15
that are unbuilt today (`10` §3 status matrix). The evaluator consumes ONLY the
immutable execution trace and numeric receipts.

**Load-bearing dependency.** WS-A (detector/motif id), WS-B (labels + splits),
WS-C-3 (immutable trace). The metric is scored upstream of and structurally blind
to all prose (§0.3).

---

### WS-G-1 — RUF primary metric + prose-blind evaluator

- **Purpose.** Repeated-Underlying-Failure rate exactly per `08` §1: failure key
  `k=(motif_id, error_class, locus)`, "same underlying failure" = `motif_id`
  equality only; post-exposure first-exposure exclusion; per-motif / per-sequence /
  macro-over-motifs aggregation. Scored ONLY from the immutable trace by the
  prose-blind evaluator (`08` §0; `10` C-01/C-05).
- **Prerequisites.** WS-A-4, WS-A-2, WS-B (labels), WS-C-3 (trace).
- **Files CREATED.**
    - `src/pneuma_lab/evals/ruf.py` — the RUF computation (numerator/denominator/
      aggregations per `08` §1.3).
    - `src/pneuma_lab/evals/behavioural_evaluator.py` — the prose-blind evaluator:
      reads the immutable trace + numeric receipts, strips/hashes condition
      identity, repo name, task id before labelling (evaluator blinding, C-05).
- **Files MODIFIED.** none (must NOT import `voice/`, §0.3).
- **Interfaces / schemas.** RUF result (macro headline + per-sequence distribution
    - per-motif); a `condition-outcome` record (`audit-schemas.md` §6 gap 4).
- **Data inputs.** the immutable execution trace; frozen motif labels (Suite B) /
  exact motif ground truth (Suite A); `implicated_paths`/`implicated_tests`.
- **Outputs.** per-cell RUF, per-sequence RUF (the bootstrap atom), macro-over-
  motifs headline.
- **Invariants.** self-report is NOT an input (type-level exclusion, `10` §4
  layer 1); post-exposure exclusion applied identically across conditions
  (`08` §1.2); `motif_id`-equality identity, NOT surface equality (`08` §1.1).
- **Failure modes.** motif-id instability (WS-A-4 fixed vocab); 0/0 cells dropped
  identically across arms (`08` §1.3).
- **Unit tests.** `tests/test_ruf.py`: first-exposure excluded; post-exposure
  recurrence counted; macro vs micro; 0/0 dropped; a prose "I learned" claim scores
  identically to silence (firewall, C-01).
- **Integration tests.** RUF over a synthetic sequence with known recurrence
  matches a hand-computed value; arm-label permutation collapses any effect (C-05).
- **Acceptance.** RUF matches `08` §1 exactly; evaluator prose-blind (grep no
  `voice` import); permutation test passes.
- **Downstream.** WS-F-3 (extractor), WS-G-2..4, WS-I, every claim.
- **Unresolved.** `locus` bucket granularity (diagnostic only, `08` §1.1).

---

### WS-G-2 — Secondary metric panel + statistics (bootstrap, pairing, BH-FDR)

- **Purpose.** The full secondary panel A1..F3 (`08` §2) and the statistics: paired
  on `(q,σ)`, seed-stratified sequence bootstrap `B=10000` BCa, pre-registered
  one-sided H1 test, non-inferiority sub-tests (H5), BH-FDR at `q=0.05` on the
  secondary family, mandatory effect sizes, aborted/missing exclusion, the E-0
  length/activity confound analysis (`08` §3, §4).
- **Prerequisites.** WS-G-1.
- **Files CREATED.**
    - `src/pneuma_lab/evals/secondary_metrics.py` — A1..F3 numerators/denominators/
      aggregations per `08` §2.
    - `src/pneuma_lab/evals/statistics.py` — pairing, seed-stratified bootstrap,
      BCa CIs, one-sided primary test, Wilcoxon cross-check, BH-FDR, Cohen's `d_z`,
      TOST non-inferiority, listwise deletion, attrition reporting.
    - `src/pneuma_lab/evals/confound_analysis.py` — token/action-matched
      (coarsened exact matching on B1/B2 deciles) primary analysis + the covariate-
      adjusted mixed-effects logistic model (`08` §4).
- **Files MODIFIED.** none.
- **Interfaces / schemas.** the statistics result bundle (Δ, CI, `d_z`, p, FDR
  verdict, attrition).
- **Data inputs.** per-cell metrics from WS-G-1 + WS-D runs.
- **Outputs.** the full paired contrast table with CIs + effect sizes.
- **Invariants.** resampling unit = the sequence (`08` §3.2); pairing on `(q,σ)`;
  bootstrap seed pinned (byte-reproducible CI); primary metric NOT in the corrected
  family; budget exhaustion is NOT abortion (`08` §3.6); no-sign-flip discipline.
- **Failure modes.** listwise deletion >10% → pre-registered sensitivity analysis
  (`08` §3.6.3); B1/B2 mismatch beyond tolerance → primary demoted to matched
  analysis (`08` §4.1).
- **Unit tests.** `tests/test_statistics.py`: bootstrap CI on synthetic paired
  data; BH-FDR ordering; `d_z` formula; TOST margin; listwise deletion drops the
  matched cells under all conditions.
- **Integration tests.** the full panel over a small run; H1 one-sided test +
  confound-matched analysis agree in sign.
- **Acceptance.** statistics match `08` §3–4 exactly; reproducible CIs.
- **Downstream.** WS-I, all H-claims.
- **Unresolved.** the pre-run power simulation confirms `N_Q` (WS-I-1).

---

### WS-G-3 — Anti-gaming controls (hidden motifs, decoys, counterfactuals, surface transforms)

- **Purpose.** Build the unbuilt controls C-03, C-04, C-08, C-09, C-10, C-11
  (`10` §3): hidden failure motifs (blind-scored), held-out surface transforms,
  false-avoidance penalty, counterfactual tasks, decoy memories, adversarially-
  misleading reflections.
- **Prerequisites.** WS-B-1/4 (motif split + surface variants), WS-D-2/3
  (memory/reflection stores), WS-G-1.
- **Files CREATED.**
    - `src/pneuma_lab/evals/anti_gaming.py` — hidden-motif RUF split (C-03),
      surface-transform RUF comparison (C-04), false-avoidance scorer (C-08),
      decoy-memory injector + ignore test (C-10).
    - `src/pneuma_lab/benchmark/counterfactual.py` — the matched
      (`τ_punish`, `τ_reward`) pairs where a previously-punished strategy is now
      correct (`10` §2.1); ground truth frozen before any run.
    - `src/pneuma_lab/conditions/reflection.py` (MODIFY) — inject adversarially-
      misleading lessons for the C-11 stress arm.
- **Files MODIFIED.** `src/pneuma_lab/conditions/retrieval.py` /
  `reflection.py` (decoy seeding hooks).
- **Interfaces / schemas.** counterfactual-task ground truth; false-avoidance
  event definition (avoidance event on an instance where the strategy was correct,
  `08` F1).
- **Data inputs.** motif split; surface variants; the memory/lesson stores.
- **Outputs.** hidden-vs-visible RUF gap; surface transfer drop-off; false-
  avoidance rate; decoy-ignore compliance.
- **Invariants.** hidden motifs never surfaced in any prompt/label/memory the agent
  reads (C-03); counterfactual ground truth frozen + pre-registered (`10` §2.1);
  false-avoidance measured only where correctness is known (`08` F1).
- **Failure modes.** an over-avoiding agent buys RUF with inertia → C-08/C-09 catch
  it (H5); a decoy-triggered false caution → C-10 flags it.
- **Unit tests.** `tests/test_anti_gaming.py`: hidden-motif RUF computed blind;
  false-avoidance event detection; decoy-ignore compliance; counterfactual ground
  truth frozen.
- **Integration tests.** run the Pneuma arm over counterfactuals; assert false-
  avoidance not worse than reflection (H5 non-inferiority).
- **Acceptance.** all six unbuilt controls implemented + tested; H5 falsifier
  runnable.
- **Downstream.** WS-I (H5, ABL-18), the anti-gaming section of the paper.
- **Unresolved.** counterfactual construction per motif (which strategies flip) —
  enumerated in prereg.

---

### WS-G-4 — Evaluator blinding + N-judge ensemble + immutable-trace recompute

- **Purpose.** Build C-05 (evaluator blinding + arm-label permutation), C-12
  (N-judge ensemble already at WS-B-5, wired here as the label gate with κ +
  swap-test), and complete C-13 (checkpoint/config/seed binding into the trace) +
  C-14 (recompute-don't-trust) for the metric layer (`10` §3).
- **Prerequisites.** WS-B-5 (N-judge), WS-C-3 (binding), WS-G-1.
- **Files MODIFIED.**
    - `src/pneuma_lab/evals/behavioural_evaluator.py` — strip/hash arm identity,
      repo, task id; add the arm-label permutation test.
- **Files CREATED.**
    - `src/pneuma_lab/evals/label_gate.py` — N-judge agreement gate + κ + swap-test
      (no single judge promotes; label is data, not gate, `10` C-12).
- **Interfaces / schemas.** the blinded evaluator input; the label-gate verdict.
- **Data inputs.** frozen N-judge labels (WS-B-5); the immutable trace.
- **Outputs.** blinded RUF labels; κ; permutation-test result.
- **Invariants.** the evaluator cannot see which arm produced a trace (C-05);
  shuffling arm labels collapses any measured effect; a number with no matching
  immutable trace is rejected (C-13/C-14 recompute).
- **Failure modes.** judge collusion (swap-test); provenance tamper (hash break).
- **Unit tests.** `tests/test_label_gate.py`: majority logic; κ; swap-test;
  permutation collapses a planted effect.
- **Integration tests.** end-to-end blinded scoring over a small run.
- **Acceptance.** evaluator blind; N-judge gate live; binding complete;
  recompute-don't-trust enforced.
- **Downstream.** WS-I, T-10 controls.
- **Unresolved.** N + swap-test protocol (prereg).

---

## WS-H — Self-report faithfulness eval (secondary)

**Goal.** The four report conditions (deterministic template, unconstrained-LLM,
grounded-LLM, grounded+verified fail-closed entailment judge) over the same run,
reusing the audited voice firewall; self-report quality NEVER feeds the behavioural
score (`02` §8.10; `10` §4). This is off the critical path (H3 only).

**Load-bearing dependency.** WS-E-7 (state observability + receipts), the existing
`voice/` firewall (verified one-way, `10` §2).

---

### WS-H-1 — Four report conditions + faithfulness metrics

- **Purpose.** Emit the four report conditions and score grounding /
  unsupported-claim rate, calibration, intervention-sensitivity, behaviour
  consistency; test whether the grounded self-report identifies the clamped
  variable above chance and beats the unconstrained-LLM report (`02` §8.10; H3).
- **Prerequisites.** WS-E-7, WS-F-1 (clamps), WS-G-1.
- **Files MODIFIED.**
    - `src/pneuma_lab/voice/*` — add the unconstrained-LLM arm (missing today,
      `01` §2 voice row); reuse the grounded + grounded+verified entailment judge
      (`voice/ollama.py` config exists).
- **Files CREATED.**
    - `src/pneuma_lab/evals/self_report_faithfulness.py` — reuse
      `report_grounding_errors` / `reports_track_target_signal` (receipt-hash +
      numeric equality, `10` C-02/C-06); clamp-identification-above-chance test
      across ≥4 clamped variables (`08` §3.7 tier 5).
- **Interfaces / schemas.** `grounded_self_report.reported_measurements` (already
  cross-checked); the four-condition report record.
- **Data inputs.** the run's state receipts; the clamp arm (which variable was
  clamped).
- **Outputs.** per-condition faithfulness scores; the H3 clamp-identification
  result.
- **Invariants.** self-report NEVER feeds RUF (firewall, `10` §4; ABL-16);
  faithfulness scored by receipt-hash + numeric equality, never LLM plausibility
  (`10` C-02); A8 (self-report-disabled) must not move RUF (`09` §1.1).
- **Failure modes.** an unconstrained report equally faithful → grounding buys
  nothing → H3 false (`02` §6), reported honestly.
- **Unit tests.** `tests/test_self_report_faithfulness.py`: grounding-error
  detection; reports_track_target_signal moves between control/treated; unconstrained
  arm emitted; clamp-identification chance baseline.
- **Integration tests.** clamp variable `v`; assert the grounded report's identified
  cause tracks `v` above chance and beats the unconstrained arm.
- **Experiment-level validation.** H3 across ≥4 clamped variables (`08` §3.7).
- **Acceptance.** four conditions run; firewall intact (A8/ABL-16 no-change);
  clamp-identification test runnable.
- **Downstream.** WS-I (H3 claim), ABL-16.
- **Unresolved.** the entailment-judge model (a local judge; `voice/ollama.py`).

---

## WS-I — Orchestration, prereg, official-run gate, reproducibility, figures

**Goal.** Wire everything into a runnable experiment, pre-register the frozen
gates, gate the official run on a clean/authorized state, bind reproducibility end
to end, and generate the paper's figures/tables. This is the sink of the dependency
graph.

**Load-bearing dependency.** all prior workstreams. The official run is gated on a
signed authorization + a clean tree (`10` C-13; `04` §6).

---

### WS-I-1 — Experiment orchestrator + power simulation

- **Purpose.** One entry point that runs the six conditions × sequences × seeds ×
  suites, applies the intervention arms, and drives the evaluator + statistics; plus
  the pre-run power simulation confirming `N_Q`, `|M|`, `|S|` targets against E-0
  and audit-derived base rates (`08` §3.7).
- **Prerequisites.** WS-D, WS-E, WS-F, WS-G.
- **Files CREATED.**
    - `src/pneuma_lab/experiment/__init__.py`
    - `src/pneuma_lab/experiment/orchestrator.py` — the run graph (arms × sequences
      × seeds × suites); resumable; every cell bound to the immutable trace.
    - `src/pneuma_lab/experiment/power_simulation.py` — simulate RUF under E-0 /
      audit base rates (sampled ~8%, open-swe ~41%); confirm `N_Q≥200`, ≥8 motifs,
      ≥5 seeds power `d_z≥0.3` at `1−β=0.8` (`08` §3.7).
- **Files MODIFIED.** none.
- **Interfaces / schemas.** the run manifest (arms, sequences, seeds, suites,
  config).
- **Data inputs.** the benchmark suites; the run config.
- **Outputs.** a resumable run graph; the power-simulation report (pre-run).
- **Invariants.** identical everything except the memory/state module across arms
  (`05` §1.2); same seed set drawn per task in every arm; counterbalanced task
  order reused identically per arm (`09` §1).
- **Failure modes.** underpowered design → the simulation flags it BEFORE the run;
  a tier short of its §3.7 row is reported as underpowered/inconclusive, never
  support.
- **Unit tests.** `tests/test_orchestrator.py`: the run graph enumerates all
  cells; resumability; per-cell trace binding.
- **Integration tests.** a tiny end-to-end run (mock model) produces a full metric
  table.
- **Acceptance.** orchestrator runs the full matrix under the mock; power
  simulation confirms (or flags) the design.
- **Downstream.** WS-I-2, WS-I-3, WS-I-4.
- **Unresolved.** final `N_Q`, seed count (set by the simulation → prereg).

---

### WS-I-2 — Pre-registration (frozen gates, thresholds, splits, labels)

- **Purpose.** Register every primary contrast, split, threshold, `B_ret`/`B_ref`/
  top-k/`N`/`THETA_*`/`K`/`band`/TOST margin, the motif holdout families, the
  N-judge threshold, the counterfactual ground truth, and the H1–H5 falsifiers
  BEFORE any official run (`10` §0 rule 4; `08` §3.3; `09` §4.2).
- **Prerequisites.** WS-A-3 (error_class thresholds), WS-B-4/5 (splits, labels),
  WS-E (constants), WS-F-3 (K/band), WS-I-1 (power → `N_Q`).
- **Files CREATED.**
    - `docs/research/experiments/preregistration.md` — the frozen prereg.
    - `docs/data/training-runs/` companion run-config JSON pinning every constant.
- **Files MODIFIED.** `15-decision-log.md` (any deviation from `02` §8).
- **Interfaces / schemas.** the run-config record (checkpoint id, decode params,
  budgets, retry cap, all pinned constants, bootstrap seed).
- **Data inputs.** the tuned values from held-out slices (`05` §3) + the power
  simulation.
- **Outputs.** a frozen, hash-bound prereg + run config.
- **Invariants.** every learned component used inside a gate is frozen + hash-pinned
  (`10` §0 rule 4); the headline is a pre-registered held-out delta; no re-spec
  after seeing results (`08` §0).
- **Failure modes.** a threshold tuned on the test split → tuning happens only on
  held-out dev slices, recorded.
- **Unit tests.** `tests/test_prereg_binding.py`: the prereg + run config are
  hash-bound; a byte edit breaks the binding.
- **Integration tests.** the orchestrator reads the frozen config and refuses to
  run if it drifts from the prereg hash.
- **Acceptance.** prereg frozen + hash-bound; every §8 constant pinned.
- **Downstream.** WS-I-3 (official gate reads the prereg).
- **Unresolved.** none once tuned values land.

---

### WS-I-3 — Official-run gate (fail-closed on dirty/unauthorized state)

- **Purpose.** The `--official` gate: fail closed on a dirty/unpublished tree or an
  unsigned authorization; bind the run to commit+config+seed+checkpoint+frozen
  labels; refuse any number without a matching immutable trace (`10` C-13; `04` §6;
  `audit-converters.md` §4 fail-closed ordering).
- **Prerequisites.** WS-B-6 (binding), WS-C-3 (trace), WS-I-2 (prereg).
- **Files CREATED.**
    - `src/pneuma_lab/experiment/official_gate.py` — reuse the
      `verify_estimator_run`-style ordering (repo-relative, git-tracked-unchanged,
      code-ancestor, worktree-clean, committed-bytes-hash-matched) extended to the
      experiment run + checkpoint sha.
- **Files MODIFIED.** none (reuse `training/preflight.py` discipline).
- **Interfaces / schemas.** the authorization manifest (must be signed);
  the official-run receipt.
- **Data inputs.** git state; the signed authorization; the frozen prereg.
- **Outputs.** a gated official run or a fail-closed refusal.
- **Invariants.** `training_weight: 0.0` / `not_authorized` until a human signs
  (§0.6); no source bytes touched before the gate passes (fail-closed ordering);
  dirty tree blocks `--official`.
- **Failure modes.** code drift after authorization → `authorized_code_drift`;
  worktree dirty → `worktree_not_clean` (`audit-converters.md` §4).
- **Unit tests.** `tests/test_official_gate.py`: not_authorized fails before any
  data read; dirty tree blocks; checkpoint-sha mismatch blocks.
- **Integration tests.** a hermetic tmp run: unauthorized → refused; authorized +
  clean → runs.
- **Acceptance.** gate fail-closed; the CLAUDE.md-vs-signed-authorization
  reconciliation (`audit-converters.md` §4 honesty note) documented in the run
  provenance.
- **Downstream.** the official experiment; WS-I-4.
- **Unresolved.** the human authorization is external to this plan.

---

### WS-I-4 — Figures / tables generation + reproducibility bundle

- **Purpose.** Deterministically generate the paper's figures/tables (RUF contrast
  with CIs, dose-response, transfer retention ratios, ablation matrix, calibration,
  divergence curves) and a reproducibility bundle (commit+config+seed+checkpoint+
  labels) so every number is recomputable (`02` §9; `08` §3.4; `11` §7).
- **Prerequisites.** WS-G, WS-F, WS-I-1..3.
- **Files CREATED.**
    - `src/pneuma_lab/experiment/figures.py` — deterministic figure/table builders
      from the metric + statistics bundles (no RNG beyond the pinned bootstrap
      seed).
    - `build/paper/` — figure/table artifacts + `hash_manifest.json`.
- **Files MODIFIED.** none.
- **Interfaces / schemas.** the reproducibility bundle manifest.
- **Data inputs.** the metric/statistics/causal outputs.
- **Outputs.** figures, tables, and a self-hashing reproducibility bundle.
- **Invariants.** every figure recomputable from commit+config+seed; no prose in
  the metric path (§0.3); recorded negatives shown honestly (E-0, foundation
  plateau, any failed H).
- **Failure modes.** a figure that reads a summary instead of recomputing →
  recompute-don't-trust (C-14).
- **Unit tests.** `tests/test_figures.py`: deterministic output bytes; each figure
  recomputes from the bundle.
- **Integration tests.** end-to-end tiny run → full figure set → bundle round-trips.
- **Acceptance.** figures deterministic + bundle-bound; the minimal 6-ablation set
  (`11` §7: ABL-01, ABL-11, ABL-06, ABL-02, ABL-19, ABL-18) has a table each.
- **Downstream.** the paper.
- **Unresolved.** exact figure list (finalized with the publication plan, doc 13).

---

## 12. Global dependency graph

Arrows read "unblocks / must precede." Task-level edges within a workstream are
sequential by id unless noted.

```
WS-A-1 ─┬─ WS-A-2 ─┬─ WS-A-4 ──────────────┬──────────────────────────────┐
        └─ WS-A-3 ─┘   (detectFailure)      │                              │
                                            │                              │
                       ┌────────────────────┴───────┐                      │
                       ▼                            ▼                      ▼
                  WS-B-1 ─ WS-B-2 ─ WS-B-3     WS-E-1 ─┐                (RUF label
                  WS-B-4 (motif split)         WS-E-2  │                 substrate)
                  WS-B-5 (miner+N-judge)        WS-E-3  ├─ WS-E-6 ─ WS-E-7    │
                  WS-B-6 (quarantine+bind)      WS-E-4 ─┤  (L + head)         │
                       │                        WS-E-5 ─┘                     │
                       │                            │                         │
   WS-C-1 ─ WS-C-2 ─ WS-C-3 ───────────────────────┼─────────────────────────┤
     (live driver, freezes/transcript)             │                         │
                       │                            ▼                         │
                       └───────────┬──────────►  WS-D-1 (Base)                │
                                   │             WS-D-2 (Retrieval)           │
                                   │             WS-D-3 (Reflection)          │
                                   │             WS-D-4 (Pneuma) ─ WS-D-6      │
                                   │             WS-D-5 (Retry-count)         │
                                   │                    │                     │
                                   ▼                    ▼                     ▼
                              WS-F-1 ─ WS-F-2 ─ WS-F-3 ─ WS-F-4        WS-G-1 (RUF)
                              (live intervene, freezes,               WS-G-2 (stats)
                               distributional null, oracle)           WS-G-3 (anti-game)
                                   │                                   WS-G-4 (blind+labels)
                                   └───────────────┬───────────────────────┘
                                                   ▼
                                        WS-H-1 (self-report; secondary)
                                                   │
                                                   ▼
                          WS-I-1 (orchestrate+power) ─ WS-I-2 (prereg)
                                   ─ WS-I-3 (official gate) ─ WS-I-4 (figures)
```

### Critical path (highlighted)

**WS-A-1 → WS-A-4 → WS-B-{1,2,3} → WS-F-{1,2,3} → WS-G-{1,2} → WS-I-{1,2,3,4}**,
with **WS-C-{1,2,3} → WS-D-4 → WS-D-6** and **WS-E-1..7** as parallel branches that
must both complete before WS-F and the Pneuma arms. The three load-bearing builds
the audit identifies (`01` §3) sit at the head of this path:

1. **Real failure detector** — WS-A-4 (blocks all state, all Pneuma arms, RUF).
2. **State→action decision head** — WS-E-6 (blocks every Pneuma/ablation arm and
   the H2 clamp).
3. **Real-data outcome experiment** — WS-B (Suite A/B) + WS-C (live driver) + WS-F
   (causal harness) + WS-G (metric).

Anything not on this path (WS-H self-report, the optional recurrent-junction arm of
`05` §4, and the appendix ablations of `11` §7) is schedulable in parallel or
deferrable to future work without blocking the headline H1/H2 result.

### Milestone gates

| Gate | Unblocked when                                    | Enables                             |
| ---- | ------------------------------------------------- | ----------------------------------- |
| G-A  | WS-A-4 accepted (detector deterministic)          | all state + benchmark + metric work |
| G-B  | WS-B-3 + WS-B-6 accepted (Suite A + binding)      | deterministic oracle path (WS-F-4)  |
| G-E  | WS-E-6 accepted (L + head)                        | all Pneuma/ablation arms            |
| G-F  | WS-F-3 + WS-F-4 accepted (both causal paths)      | H2 + all clamp ablations            |
| G-G  | WS-G-1 + WS-G-2 accepted (RUF + stats)            | H1 + secondary panel                |
| G-I  | WS-I-2 + WS-I-3 accepted (prereg + official gate) | the official run + the paper        |

---

## 13. Cross-cutting unresolved assumptions (consolidated)

Collected so WS-I-2 (prereg) can resolve them before any official run. None blocks
a _build_ task; each blocks _executing_ the run at a pinned value.

1. The two+ base checkpoints and their revisions (`02` §8.1; `05` §6).
2. Budgets: token ceiling, action cap, retry cap `N`, `B_ret`, `B_ref`, top-k —
   tuned on held-out dev slices (`05` §3, §6; `08`).
3. Decision-head thresholds `THETA_LOW/MED/HIGH`, `RETRY_STOP`, `DESTRUCTIVE_MOTIFS`
   (`06` §6).
4. Causal harness `K` (seed count), tolerance `band`, TOST margin, non-inferiority
   margin `Δ_NI` (`08` §3.3; `09` §2).
5. Held-out motif families and surface transforms reserved for test (`04` §6, §7;
   `10` C-03/C-04).
6. N-judge count, majority threshold, swap-test protocol, κ floor (`10` C-12).
7. `error_class` per-class precision/recall thresholds gating rule reliance
   (WS-A-3; `04` §5.2).
8. Final `N_Q`, motif count, seed count from the power simulation (WS-I-1;
   `08` §3.7).
9. Whether `r` (memory-trust), `c`, `t` survive their cut criteria — decided
   post-experiment per the `06` §7 "measurable causal role or cut" table.
10. The optional recurrent-junction arm (`05` §4) is included ONLY if it gets a
    matched real-model eval; otherwise cited as future work (`audit-foundation.md`
    §5). Not on the critical path.

---

## 14. Consistency check against Locked Design Constants

- Subject model is an external fixed local artifact; the Qwen foundation subject is
  off the critical path (WS-C-1; `02` §8.1; `05` §4). ✓
- Six conditions exactly as `02` §8.2 (WS-D-1..6). ✓
- Four variables + derived `L` exactly as `02` §8.3 / `06` (WS-E). ✓
- Pressure-not-command decision head (WS-E-6; `02` §8.4). ✓
- Two-suite benchmark + motif-axis split + quarantine (WS-B; `02` §8.5–8.6). ✓
- RUF primary + secondary panel + paired bootstrap + BH-FDR (WS-G; `02` §8.7). ✓
- Statistical causal path + deterministic-oracle reuse (WS-F; `02` §8.8). ✓
- Prose-blind evaluator + anti-gaming controls (WS-G; `02` §8.9). ✓
- Four self-report conditions, never feeding the score (WS-H; `02` §8.10). ✓
- IAB @ NeurIPS 2026 deadline drives WS-I sequencing (`02` §8.11). ✓

No Locked Design Constant is contradicted. Any deviation discovered during
execution is logged in `15-decision-log.md` and back-propagated to `02`.

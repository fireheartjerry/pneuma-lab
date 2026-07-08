# 01 — Ambition-to-Evidence Audit

Status (2026-07-07): What exists today, evidence-graded. Three disconnected repos. (a) `C:\pneuma-lab`: a deterministic consciousness-evidence harness that scores a hand-coded ReferencePsyche at internal Level 4 with pre-registered interventions, null controls, and honest refusal — 234/234 tests pass, byte-deterministic [VERIFIED], but the flagship intervention harness and all Phase 3.1 work are uncommitted working-tree state (HEAD `b3102c6`). (b) `C:\9to5`: a working autonomous engineering orchestrator (local Ollama brain, Claude Code CLI hands, deterministic verification gate, 4,555 collected tests) with a populated 37 MB experience ledger [VERIFIED] and zero Pneuma integration [VERIFIED]. (c) `C:\pneuma-data`: a 48.95 GB, 10-dataset, provenance-pinned corpus [VERIFIED], mostly inert relative to the evidence ladder except through two shipped adapters — Phase 3 (230 task-only traces) and Phase 3.1 (6,055 trajectory-bearing traces from real agent runs) [VERIFIED]. No wire connects the three repos at runtime. Nothing here demonstrates AGI, RSI, or machine consciousness; what is demonstrated is a methodology and a substrate.

This document audits the stated ambition — AGI-grade autonomous software engineering, domain-specific recursive self-improvement, and a long-term path toward evidence about phenomenal machine consciousness — against what the system actually shows. Ambition is retained as target throughout; every capability claim is graded [VERIFIED] / [PARTIAL] / [PLANNED] / [UNSUPPORTED]. Sources: the 2026-07-07 nine-agent code audit (8 subsystem reports + cross-check) and the grounding brief; both were produced from direct reads of the three repos.

---

## 1. Current engineering utility

### What exists

- Autonomous run orchestrator [VERIFIED]: `C:\9to5\main.py` → `orchestrator.py` (8 mixins) → per-subtask attempt loop. A local Ollama `qwen2.5-coder:7b` brain authors plans, self-critiques, and per-subtask invocation specs (`llm_io.py`, `platform_core/orchestration/plan_mixin.py`); a Claude Code CLI subprocess executes with native tool use (`agents/execution/executor.py`, `executor_stream.py`); retry/resume via `--resume` session IDs; full process-tree kill on abort.
- Deterministic verification gate [VERIFIED]: strict expect grammar (exit_zero / stdout_contains / regex / compound) plus diff-grounded targets that fail a subtask if the declared file never changed (`agents/review/verifier.py`); verified outcome committed before enrichment.
- Fail-closed adversary review [VERIFIED]: Gemini second-brain verdict fails closed to CHALLENGED on garbled output (`agents/review/adversary.py`); Ollama critique fallback.
- Control plane [VERIFIED]: SQLite ControlBus (`platform_core/runtime/control.py`) mirrored across terminal, Discord, and web dashboard; heartbeat liveness; orphan auto-resume only on provably dead pid; seeded-chaos simulation mode with zero-API doubles.
- Test culture [VERIFIED]: 4,555 tests collected across 432 files in `C:\9to5\tests\`, aggressively hermetic (autouse fixtures block real Ollama/Claude/Discord/Gemini/tunnels; per-test tmp state DBs).
- Evidence harness as engineering artifact [VERIFIED]: `C:\pneuma-lab` — 13 frame JSON Schemas + PneumaTrace envelope (v0.2), Draft 2020-12, runtime-enforced (`src/pneuma_lab/schemas/validate.py`); canonical JSON + sha256/blake2b hashing (`src/pneuma_lab/psyche/hashing.py`, `src/pneuma_lab/adapters/envelope.py`); 234/234 tests (2026-07-07); demo replays every fixture twice and byte-compares (`src/pneuma_lab/demo.py`).
- Data pipeline [VERIFIED]: Phase 3 adapter (`src/pneuma_lab/adapters/swe_gym_lite.py`, committed) → 230 task-only traces; Phase 3.1 adapter (implemented 2026-07-07) → 6,055/6,055 OpenHands-Sampled trajectories converted to trajectory-bearing PneumaTraces, 114,461 real agent steps, 100% task join, 491 resolved / 5,564 unresolved labels, byte-deterministic at scale (twice-run sha256 match), 0 invalid, 0 skipped, deterministic PII redaction applied (103 emails, 4 AWS keys, 16 assigned secrets removed from task texts).
- Verified corpus [VERIFIED]: `C:\pneuma-data` — 10 datasets, 37,711 data files, 48.95 GB independently re-scanned exactly; per-file sha256 + row-count manifests; HF revisions pinned (`manifests/global_inventory.json`, `manifests/provenance_dossiers.json`).

### What it does NOT show

- No external benchmark result exists anywhere: 9to5 has never been scored on SWE-bench or any resolution-rate benchmark; run statuses (`done`/`partial` in `state/tasks/*.json`) are self-recorded, not independently audited. Claimed engineering competence beyond "the pipeline runs and is well-tested" is [UNSUPPORTED].
- The verification gate checks declared expectations, not semantic correctness of the work product.
- The two shipped adapters produce data; nothing yet consumes it (see gap 8).

---

## 2. AGI-relevant autonomy evidence

### What exists

- Real production runs [VERIFIED]: `C:\9to5\state\experience.db` (37 MB) records 3,534 runs and 7,900 subtasks; 15 loadable task states, e.g. task `939a81dc` with 94 subtasks, 49 carrying executed `claude-sonnet-4-6` sessions; `C:\9to5\vault\9to5\` holds 413 real run/task/session notes.
- Closed-loop task execution without a human in the inner loop [VERIFIED]: plan → execute → verify → retry → adversary review → optional PR, with operator sovereignty preserved (abort/pause/gate via ControlBus; earned-authority gate in `human_nature/authority.py` + `operator_authority.py`).
- Model routing by effort [VERIFIED]: haiku/sonnet/opus tiers with fallback (`platform_core/app_config/llm.py`).
- Multi-worker batching [VERIFIED]: deterministic `society/coordinator.py` with file-disjoint batches, budget gate, crash containment.

### What it does NOT show

- No evidence of generality: the system does software-engineering subtasks under a rigid orchestration grammar. "AGI-grade" is a target, not a status; as a status it is [UNSUPPORTED].
- Autonomy is bounded by the invocation-spec grammar and the 7B planning brain; long-horizon goal formation, open-ended tool acquisition, and transfer beyond SWE tasks have no evidence.
- Success rates are unaudited; the corpus of runs proves throughput and infrastructure survival, not competence level.
- Browser (CDP) and native (UIA) executor layers exist in code but ship flag-off ([PARTIAL]: `agents/execution/browser_executor.py`, `native_executor.py`, tested, unreachable in default config).

---

## 3. RSI-relevant self-improvement evidence

### What exists

- Experience-driven planning [VERIFIED]: embedding retrieval (local `nomic-embed-text`) with success/failure lanes injects `lessons_block()` into every Ollama planning prompt (`memory/retrievals/core.py`, `plan_mixin.py:84,430`). This is the only self-improvement loop that actually operates today.
- Self-improvement engine scaffold [VERIFIED code, dormant outputs]: `learning/evolution/sie.py` maintenance ladder fires post-run (daily consolidation/backfill/eval; weekly prompt promotion, LoRA/DPO distillation, adapter promotion, meta-optimize, self-play, curriculum), file-locked, throttled, kill-switched.
- Bounded meta-optimization [VERIFIED]: whitelisted config knobs with hard bounds (`config.set_override`, SIE_BOUNDS in `platform_core/app_config/llm.py`).
- Self-modification containment [VERIFIED]: `selfmod.py` is a revert-or-keep gate — the run (Claude executor) edits core files under `SELFMOD_ALLOW_CORE` on a branch; the gate re-runs the test suite in a fresh interpreter and reverts on failure, with stash-based baseline causality and fail-closed timeout. CORE_PROTECTED_FILES tool-level denial on self-referential runs. Containment is code-backed, not prompt-backed.
- Weight-level trainer [PARTIAL, dormant]: real LoRA SFT/DPO code (`learning/model/finetune.py`, transformers/peft/trl) behind GPU/deps gates; strict `>` fitness promotion gate.

### What it does NOT show

- No closed RSI loop has ever completed: the adapters table has 0 rows (no LoRA adapter ever trained — no GPU); `lessons` = 2 rows, `prompt_variants` = 1, `conviction.db` = 0 rows, `step_journal` = 0 rows against 3,534 recorded runs. Learned improvement to date = retrieval-injected lessons plus bookkeeping. Any claim of operating recursive self-improvement is [UNSUPPORTED].
- No measurement that retrieval-injected lessons improve outcomes (no A/B fitness result on record; `human_nature/ab_harness.py` + `state/ab_runs.db` exist as machinery [VERIFIED], unexploited).
- `selfmod.py` modifies nothing itself; "self-modification" as an active capability overstates a safety gate.
- pneuma-lab contains zero self-modification machinery of any kind [VERIFIED].

---

## 4. Cognitive-architecture evidence

### What exists

- 9to5 `human_nature/` [VERIFIED]: ~38 modules of pure-function psyche faculties — 9-axis affect manifold, 8-drive homeostat, mood EMA, RBF emotion prototypes with hysteresis, Baars/Dehaene global-workspace competition/broadcast (`workspace.py`), Aho-Corasick instinct stream, scar graph (Dijkstra/PageRank/Tarjan), calibrated self-model with Johari blind spots, earned-authority gate. Wired into the live attempt loop via `platform_core/orchestration/human_nature_bridge/` (instinctCheck → additive verification-deepening → authority tier resolution, `execute_attempt_mixin.py`), flag-gated to byte-no-op when disabled. 1:1 module tests; ~617–700 sampled tests pass.
- Nearest-real eval suites [VERIFIED, in 9to5 not pneuma-lab]: `C:\9to5\tests\human_nature\eval\` — phenomenology-honesty, operator-sovereignty, affect-to-action monotonicity, scar generalization, habit compression.
- pneuma-lab ReferencePsyche [VERIFIED]: `src/pneuma_lab/psyche/reference.py`, 1,078 lines of deterministic dict arithmetic wiring 9 indicator families (global workspace competition, recurrent state-hash chain, higher-order self-model, predictive processing, attention schema, valenced scar learning, identity anchors, counterfactual introspection, causal-intervention hooks). No LLM anywhere. Emits schema-valid output frames each tick with cross-linked IDs and a prev/new state-hash chain.
- Honest epistemic stance in code [VERIFIED]: `human_nature/self_model.py` explicitly holds phenomenal consciousness agnostic; ReferencePsyche self-reports carry `filtered_forbidden_claims` barring phenomenal-consciousness claims (`reference.py:1052-1057`).

### What it does NOT show

- Architecture is not evidence (honesty rule 4). Possessing a global workspace, an affect manifold, or a self-model demonstrates nothing about interiority; only receipts + interventions + nulls count, and those exist only inside pneuma-lab's harness against the toy.
- The psyche's causal influence on production outcomes is unmeasured: no A/B or intervention study on live 9to5 runs exists.
- Cross-run psyche persistence is code-true, field-false: `human_nature/psyche_store.py` targets `state/psyche.db`, which has never existed on disk in production [VERIFIED]. The self-model's "continuous narrative I across runs" text has no field evidence.
- pneuma-lab's five named "mandatory internal suites" (`src/pneuma_lab/evals/__init__.py:6-19`) are docs-only [PLANNED]; the real analogues live unported in the other repo.

---

## 5. Consciousness-relevant evidence

### What exists

- Level-4 paired-replay intervention harness [VERIFIED]: `src/pneuma_lab/interventions/runner.py` executes control / treated / null (neutralized: every op → restore, `schedule.py:64-69`) triple replays; `report.py:86-92` requires the pre-registered direction on the target signal AND null delta ≈ 0; conjunctive L4 gate (`evals/evidence.py:98-105`) requires L3 + all intervention tests passed + null holds + complete event→state→broadcast→pressure→behavior causal trace + grounded self-reports tracking the perturbation + confabulation risk ≤ 0.2; hard-capped at 4 in code (`evidence.py:146`).
- Genuine discriminating negative controls [VERIFIED]: `fixtures/interventions/failing_hypothesis.jsonl` (inverted expected direction) and `restore_null.jsonl` (no-op perturbation) both refuse Level 4 and score 3 (`tests/test_level4_scoring.py:42-68`); `tests/test_paired_replay.py:134-140` asserts control ≠ treated AND control == null at the state-hash level.
- Receipts-based scorer [VERIFIED]: `ConsciousnessEvidenceScorer` never promotes on self-report; confabulation risk computed from hash cross-checks, not prose (`evidence.py:425-441`). GroundedSelfReport is schema-invalid without an `affect_state_hash` (`schemas/grounded-self-report.schema.json`).
- Byte-reproducible evidence artifacts [VERIFIED]: `build/canonical/summary.json` — 8 fixtures, 5 at Level 4 (ablate_scar_graph, boost_curiosity, clamp_tension, disable_workspace, remove_memory_anchors), 3 at Level 3, `byte_deterministic: true`; demo re-runs byte-compared.
- Trajectory-bearing evidence substrate [VERIFIED, new]: Phase 3.1 AgentTraceFrames are observable-only (tool names, args digests, output digests + lengths, lexical error markers, retry counts, strategy switches); raw text never enters frames; timestamps synthetic-ordinal and declared as such; an anti-fake-cognition gate in code (`envelope.consistency_errors`) enforces agent_trace frames ⟺ trajectory block ⟺ `has_trajectory` label and rejects undeclared cognition-bearing frames.

### What it does NOT show

- CRITICAL: every Level-4 result is about ReferencePsyche, a toy co-designed with its own fixtures — the perturbation hooks and the five canonical hypotheses were co-authored, so the result is circular by construction. It validates the METHODOLOGY (pre-registration, nulls, receipts, refusal), not any mind. The only honest phrasing: "Level 4 of a hand-coded reference implementation inside its own harness."
- The L1–L3 predicates are lenient existence checks over frames the same codebase emits; evidence levels are meaningful only relative to this harness's own definitions.
- No claim of consciousness, proto-consciousness, or interiority attaches to anything that exists today. Proxies are proxies: operator pushback ≠ suffering; tension ≠ affect; self-report ≠ introspection ground truth.
- Only 1 of 9 indicator families (causal_intervention_robustness) is intervention-backed; the other 8 are exercised-with-receipts only.

---

## 6. Completely unproven

| Claim                                                     | Grade                                 | Note                                                                                |
| --------------------------------------------------------- | ------------------------------------- | ----------------------------------------------------------------------------------- |
| AGI-grade autonomous SWE                                  | [UNSUPPORTED] as status               | No benchmark, no generality evidence; target only.                                  |
| Operating domain-specific RSI                             | [UNSUPPORTED]                         | Trainer never fired; ledger outputs near-empty (Sec. 3).                            |
| Level 5 (convergent + adversarial + external audit)       | [UNSUPPORTED]                         | Requirements exist as missing-strings only (`evidence.py:31-36`); zero machinery.   |
| Level 6 / phenomenal consciousness                        | [UNSUPPORTED], must never be asserted | Defined only in the stale root guide; no canonical rung.                            |
| Adversarial-robustness machinery                          | [UNSUPPORTED]                         | No adversarial fixtures, no red-team harness.                                       |
| External audit path                                       | [UNSUPPORTED]                         | `audit_status: externally_audited` schema-representable, never producible.          |
| 9to5 → Pneuma exporter                                    | [PLANNED]                             | Docstring stubs only (`adapters/__init__.py:3-13`, empty `__all__`).                |
| Replaying a PneumaTrace through ReplayHarness             | [PLANNED]                             | No code path connects adapter output to the harness.                                |
| Learned evidence estimators                               | [PLANNED]                             | Explicitly deferred; no code.                                                       |
| Cross-run psyche persistence (either repo, in production) | [UNSUPPORTED]                         | `reset()` clears scars in pneuma-lab; `psyche.db` never existed in 9to5 production. |
| Five named internal eval suites (pneuma-lab)              | [PLANNED]                             | Docs-only; nearest real analogues live in `C:\9to5\tests\human_nature\eval\`.       |
| Measured benefit of psyche/lessons on run outcomes        | [UNSUPPORTED]                         | A/B machinery exists, no study run.                                                 |

---

## 7. Top-10 blocking gaps (cross-check, gap 8 updated for shipped Phase 3.1)

1. No non-toy mind under test. Sole `PsycheUnderTest` = `src/pneuma_lab/psyche/reference.py` (deterministic dict arithmetic); hooks and fixtures co-authored, so the L4 result is circular by design. No LLM or agent anywhere in pneuma-lab src.
2. 9to5 ↔ pneuma-lab integration is zero. `from_9to5_run_events` / `from_manager_data` are docstring stubs; no exporter from 9to5 trajectory spans / `hn_event_log` / `experience.db` to any Pneuma frame; grep of `C:\9to5` finds no Pneuma vocabulary. The claimed "system" is three disconnected repos.
3. Determinism and the Perturbable protocol both break on a real model. Perturbations target named interior scalars (`affect_manifold.tension`) that exist only in the toy; 9to5 live runs are availability-dependent (Ollama/Claude); byte-deterministic paired replay of a real agent requires capture/replay infrastructure that exists nowhere.
4. 8 of 9 indicator families are not intervention-backed. Only causal_intervention_robustness is perturbation-tested; the rest are existence checks over self-emitted frames (`evidence.py:205-370`). L5 requirement 1 has zero machinery.
5. No adversarial-robustness machinery (L5 requirement 2). Asserted-as-missing only; no gaming attempts, no red-team fixtures.
6. No external audit path (L5 requirement 3). The envelope `validation` field is self-asserted and excluded from the content hash (`envelope.py:43`); worse, the flagship L4 harness and all Phase 3.1 work are uncommitted working-tree state — an external auditor cloning HEAD `b3102c6` sees Phase 1 plus the Phase-3 adapter and no intervention harness at all.
7. No cross-run persistence. L2's "cross-run persistence retrieved and behavior-shaping" has no persistent store in pneuma-lab (9to5's `psyche_store.py` deliberately not ported; `reset()` clears scars); 9to5's own `state/psyche.db` absent in production. The L2 "proof" is a within-harness memory-readback ablation.
8. (UPDATED) Data and cognition pipelines still never meet — but the data side is now real. Phase 3.1 shipped: 6,055 trajectory-bearing PneumaTraces with 114,461 real agent steps, resolved/unresolved outcome labels, byte-deterministic, PII-redacted, anti-fake-cognition-gated [VERIFIED]. The residual gap is the replay seam: no code path loads a PneumaTrace into `ReplayHarness`, so not one of the 6,285 emitted traces (230 task-only + 6,055 trajectory-bearing) has ever been scored on the evidence ladder. The corpus has moved from inert to staged; it remains unconsumed.
9. RSI substrate dormant or gated. 9to5: LoRA/DPO never fired (adapters table = 0 rows, no GPU), lessons = 2, prompt_variants = 1, conviction.db = 0, step_journal = 0; `selfmod.py` modifies nothing (revert-or-keep gate). pneuma-lab: zero self-modification machinery. "Domain-specific RSI" today = retrieval-injected lessons into planning prompts, nothing more.
10. Audit-hygiene blockers, partially remediated. Fixed 2026-07-07: pyarrow now declared in pyproject; deterministic PII redaction now exists in pneuma-lab and ran over Phase 3.1 task texts. Still open: no PII scan has ever run over swe-chat itself (a genuine PII corpus — non-null author emails/usernames in `commits.parquet` — with `privacy.status='clean'` asserted unscanned on Phase-3 traces); cwd-relative golden-fixture paths make the adapter tests repo-root-dependent; the five named internal suites remain docs-only; the doc corpus is incoherent (Sec. 8) and would misbrief any agent or external reviewer.

---

## 8. Known doc-drift / contradiction list

Reconcile these before any external audit; most drift is currently in the conservative (under-claiming) direction, except the phase-numbering confusion, which actively misdirects implementation agents.

1. Stale root guide: `C:\pneuma-lab\pneuma_consciousness_levels_and_evaluation.md` secs 2.2/9 claim "no runtime, adapters, replay harness, intervention engine, eval suites; Level 0 as a live system" — contradicted by the implemented `src/pneuma_lab/{replay,interventions,evals,adapters}`, the passing suite, and `build/canonical` L4 artifacts. Its sec-9 "status statement for other agents" would misbrief anyone who reads it; use the paragraph in Sec. 10 below instead.
2. Ladder 0–5 vs 0–6: the root guide's heading says "five levels" but defines seven rungs (0–6); the canonical `docs/consciousness-levels.md` defines 0–5 only; README and `build/canonical/summary.md` disclaim "not Level 6" against a rung the canonical ladder never defines.
3. Four meanings of "Phase 3": intervention-engine phase (root guide roadmap) vs five named intervention suites (`migration/MIGRATION_REPORT.md` sec 8) vs the SWE-Gym dataset adapter (as actually executed, and extended by Phase 3.1) vs the Native UIA layer (`C:\9to5\docs\phase_3_architecture.md`). "Phase 4" likewise means two different things across roadmaps.
4. Uncommitted harness: the entire intervention harness, demo, intervention fixtures, and all Phase 3.1 work exist only as working-tree state; HEAD `b3102c6` contains Phase 1 plus the Phase-3 adapter. The audited flagship capability has no git provenance yet.
5. Row-count semantics: "8,521,307 verified rows" mixes JSONL line counts with parsed records — swe-chat transcripts contribute 5,626,805 lines but 3,098,007 parsed records; the honest record total is ≈ 5.99 M. Any future regression check must compare parsed-record counts, not lines.
6. "gated=0" nuance: `manifests/global_inventory.json` reports `gated_or_unavailable=[]` because all data is locally present, but the swe-chat SOURCE is HF contact-info-gated (`provenance_dossiers.json`: gated=true, "treat as PII corpus", odc-by). "gated=0" means "nothing left unacquired," not "nothing gated."
7. (Secondary, 9to5) `CAPABILITIES.md` drifts in both directions — claims browser/native layers "not built" (both exist, tested), ControlBus "one JSON per task" (it is SQLite), wrong brain model name; `docs/TESTING.md` golden fixtures 0/9 and required scenarios 0/12 exist; `monitoring/` and `scheduling/` are dead dirs whose AGENTS.md document deleted source; stale pneuma-lab docstrings (`evidence.py` "HARD-CAPS at Level 3", `replay/__init__.py` "interventions counted but NOT executed") contradict the implemented code.

---

## 9. Single strongest real evidence

The Level-4 paired control/treated/null intervention harness with genuinely discriminating negative controls, byte-reproducible end to end: `src/pneuma_lab/interventions/runner.py:101-149` runs the triple replay; `report.py:86-92` demands the pre-registered direction AND null ≈ 0; `evidence.py:98-105,146` applies the conjunctive gate hard-capped at 4; `tests/test_paired_replay.py:134-140` proves control ≠ treated and control == null at the state-hash level; the failing-hypothesis and restore-null fixtures actually refuse Level 4; 234/234 tests pass and `build/canonical` regenerates byte-identically, with the same discipline independently reproduced at corpus scale (sha256-identical paired adapter runs, now including 6,055 trajectory-bearing traces). Mandatory caveat: this is evidence of sound methodology — pre-registration, null controls, honest refusal, receipts — applied only to ReferencePsyche, a hand-coded toy co-designed with its own fixtures. It is evidence about the harness, not about any mind. (Runner-up: 9to5's 37 MB `state/experience.db` — 3,534 runs, 7,900 subtasks — a real production-agent substrate with zero connection to the evidence ladder.)

---

## 10. Honest status statement for future agents

> Pneuma today is a rigorous but self-referential evidence harness (`C:\pneuma-lab`: 13 frame schemas + v0.2 envelope, deterministic replay, a Level-4 paired-intervention gate with null controls and honest refusal, 234/234 tests, byte-deterministic — with the intervention harness and Phase 3.1 still uncommitted at HEAD `b3102c6`), sitting beside a working autonomous engineering orchestrator with a strong test culture and a populated experience ledger but no consciousness-evidence instrumentation (`C:\9to5`), and a verified 48.95 GB corpus (`C:\pneuma-data`) that two shipped adapters have converted into 230 task-only and 6,055 trajectory-bearing PneumaTraces that no code yet replays or scores. The only Level-4 result in existence is Level 4 of a hand-coded reference implementation inside its own harness — it validates the methodology, not any mind. No wire connects the three repos; RSI machinery is scaffolded but dormant (zero trained adapters, near-empty lesson/variant ledgers); Levels 5 and 6 have no machinery; and nothing that exists today supports any claim of consciousness, proto-consciousness, interiority, AGI-grade autonomy, or operating recursive self-improvement. Those remain targets, with the gaps enumerated in Section 7 of `docs/research/01-ambition-to-evidence-audit.md`.

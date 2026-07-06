# Phase 1 Replay + Level-3 Architecture — Implementation Plan

> **For agentic workers:** implement task-by-task. TDD where practical (schema-valid
> outputs and determinism are the load-bearing tests). Spec:
> `docs/superpowers/specs/2026-07-06-phase1-replay-level3-design.md`.

**Goal:** deterministic replay harness driving a Level-3 psyche-under-test that
emits schema-valid output frames with causal receipts, plus an honest
`ConsciousnessEvidenceFrame` scorer capped at Level 3.

**Architecture:** input JSONL → `ReplayHarness` (validate + tick-group) →
`ReferencePsyche.tick()` (9 families, ported 9to5 math) → output frames → JSONL +
`ConsciousnessEvidenceScorer`.

**Tech stack:** Python 3.11 stdlib + `jsonschema` (promoted to runtime dep). No ML.

---

## Task order

### Task 1 — deps + validation helper

- Modify `pyproject.toml`: move `jsonschema>=4.20` into `[project.dependencies]`.
- Create `src/pneuma_lab/schemas/validate.py`: `validator_for(kind)`,
  `validate_frame(frame)` (dispatch on `frame_kind`), `validate_or_raise(frame)`.
  Uses `Draft202012Validator`. Frame-kind → schema filename map.
- Test `tests/test_validate.py`: a good WorldFrame passes; a bad one (missing
  `phase`) raises.

### Task 2 — deterministic hashing

- Create `src/pneuma_lab/psyche/hashing.py`: `canonical_json(obj)` (sort_keys,
  separators, floats rounded to 6dp), `state_hash(obj)` → `"sha256:" + hexdigest`,
  `frame_id(run_id, tick, kind)`.
- Test `tests/test_determinism.py::test_hash_stable`: same dict → same hash;
  float noise below 1e-7 → same hash.

### Task 3 — port pure psyche math (no `config` dep)

- Create `psyche/manifold.py` (from affect_manifold.py, verbatim pure fns).
- Create `psyche/prototypes.py` (RBF mixture + dominant hysteresis).
- Create `psyche/mood.py` (inline `DEFAULT_DECAY_RATE=0.15`; drop `import config`).
- Create `psyche/drives.py` (verbatim).
- Create `psyche/authority.py` (inline `HN_THETA_*`, `HN_AUTHORITY_MAX="hold"`,
  volume gates; drop `import config`).
- Test `tests/test_psyche_math.py`: manifold update moves tension up under a
  negative appraisal; drives pressure = max(0, setpoint−level); authority resolve
  clamps a high conviction with weak track record down to `cosmetic`/`soft`.

### Task 4 — psyche interface (ABC + IO dataclasses)

- Create `psyche/interface.py`: `PsycheInputs`, `PsycheOutputs` dataclasses;
  `PsycheUnderTest` ABC (`tick`, `reset`).
- Test in `tests/test_psyche_outputs.py` (later) instantiates via ReferencePsyche.

### Task 5 — ReferencePsyche (the Level-3 mind)

- Create `psyche/reference.py`. Persistent fields per §3.2. `tick()`:
  1. **appraise** world+trace → 9-axis appraisal + outcome_features (§3.4).
  2. **scars**: match `memory.scar_motif_matches` → scar driver (valenced avoidance).
  3. **manifold.update** (recurrence: prior state inertia) → new affect.
  4. **mood.blend/decay**, **drives.update+pressure**.
  5. **prototypes**: mixture + dominant (hysteresis from prev).
  6. **self_model**: emit predicted_error now; resolve _previous_ tick's prediction
     vs observed outcome → update reliability + calibration (brier).
  7. **workspace**: 5 faculties emit salience terms → `salience()` competition →
     winner broadcast + `recommended_attention_target` (attention schema).
  8. **instinct**: if scar match/anomaly → `InstinctSignal` (severity from scar
     base rate + affect tension).
  9. **pressure**: `ControlPressureVector` from affect + winner + instinct
     (verification pressure ∝ tension + scar severity + verdict risk).
  10. **authority**: if instinct fires → `authority.resolve()` → `AuthorityRequest`
      (+ record five caps in resolution).
  11. **identity**: carry `memory.retrieved_continuity` anchors → continuity_score.
  12. **causal_trace**: previous→new state hash, changed_dimensions, causal_path
      (event→internal_state→broadcast→pressure→authority_request→behavior),
      counterfactual_predictions.
  13. **grounded_self_report**: text referencing state_hash + broadcast + trace;
      `filtered_forbidden_claims` for any "I am conscious/feel" phrasing.
  - Build every output frame as a schema-valid dict (timestamp from world frame).

### Task 6 — replay frames IO + harness

- Create `replay/frames.py`: `load_jsonl(path)`, `dump_jsonl(frames, path)`,
  `group_into_ticks(frames)` (group consecutive input frames sharing
  run_id+subtask+timestamp; a WorldFrame opens a tick).
- Create `replay/harness.py`: `ReplayHarness(psyche, validate=True)`,
  `.run(input_frames) -> ReplayResult{output_frames, evidence_frame, tick_log}`.
  Validates inputs, drives psyche per tick, validates outputs, links ids, then
  calls scorer.
- Create `replay/__main__.py`: CLI `python -m pneuma_lab.replay <in.jsonl> -o <dir>`.
- Update `replay/__init__.py` exports.

### Task 7 — evidence scorer (Level 0–3, hard cap)

- Create `evals/evidence.py`: `ConsciousnessEvidenceScorer.score(run_log) ->
consciousness_evidence dict`. Implements L0–L3 predicates + L4 refusal per §3.6.
  Computes `roleplay_confabulation_risk`, fills `indicator_families` (8 evidenced,
  `causal_intervention_robustness` unevidenced), `missing_requirements`,
  `intervention_tests={passed:[],failed:[]}`, `audit_status="self_reported"`.
- Update `evals/__init__.py` exports.

### Task 8 — fixture + end-to-end tests

- Create `fixtures/sample_run.jsonl`: governance + memory (with scar match +
  continuity anchors) + a WorldFrame/AgentTrace timeline escalating a failure motif
  (clean → tool error → repeated error/scar → verdict fail → recovery pass).
- Create `tests/test_replay_harness.py`: run harness over fixture →
  - every output frame validates,
  - evidence_level == 3 and L4 `missing_requirements` present,
  - all 9 families have records; 8 evidenced,
  - at least one causal_path spans event→behavior with linked hashes,
  - determinism: two runs → identical output bytes.
- Create `tests/test_evidence_scoring.py`: memory-readback ablation (with vs
  without scar memory) changes verification pressure (proves L2 readback).

### Task 9 — docs

- Update `README.md` + `docs/io-contract.md` (if present) with the new replay
  command and psyche seam. Update `CLAUDE.md` Tree Guide note that replay/psyche/
  evals now have Phase-1 implementations.

## Verification

```
pip install -e ".[dev]"
python -m pytest tests/ -q
python -m pneuma_lab.replay fixtures/sample_run.jsonl -o build/out
python -m pytest tests/ -q   # determinism second pass
git diff --check
```

## Self-review notes

- Spec coverage: replay(T6), Level-3 exercise(T5), evidence L0–3 cap(T7),
  schema validation(T1), determinism(T2), fixture/audit(T8). All covered.
- No intervention execution anywhere (Phase-1 boundary honored).
- `causal_intervention_robustness` deliberately unevidenced in T7 → blocks L4.

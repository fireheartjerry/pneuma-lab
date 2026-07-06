# Source Map — Pneuma Lab contracts ↔ 9to5 / manager-data

A cross-walk from each Pneuma Lab schema to the 9to5 module(s) that ground it, and
from the manager-data project to the future operator-preference stream. This is the
"where did this shape come from, and where would a port pull from" map.

Reference snapshots of the 9to5 modules named below live under
[`../migration/copied-from-9to5/reference-interfaces/`](../migration/copied-from-9to5/reference-interfaces/)
(READ-ONLY; not active runtime).

## 9to5 `human_nature/` at inspection time (2026-07-06)

Branch `feat/human-nature-psyche-v2` (PR #38). The package has **40 modules** and a
sibling `human_nature_bridge/` coupling package + `notifications/psyche_cog.py`
surface + `tests/human_nature/` (≈40 test modules). Relevant modules:

| 9to5 module                                                                                   | Role                                                  | Purity                |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------- | --------------------- |
| `self_state.py`                                                                               | interior dict shape (schema v2), competence, affect   | pure                  |
| `affect_manifold.py`                                                                          | 9-axis continuous affect + update law + decay         | pure                  |
| `prototypes.py`                                                                               | smooth emotion-label projection                       | pure                  |
| `mood.py`                                                                                     | slow persistent homeostat                             | pure                  |
| `drives.py`                                                                                   | 8 core drives + derived signals + pressure            | pure                  |
| `emotions.py`, `appraisal.py`, `momentary.py`, `intuition.py`                                 | fast-affect + appraisal + intuition                   | mostly pure           |
| `personality.py`, `character_vector.py`, `charter.py`, `drift.py`                             | traits (versioned) + ratification                     | pure                  |
| `authority.py`                                                                                | 5-tier ladder + `resolve()` `min`-over-caps           | pure (reads `config`) |
| `operator_authority.py`                                                                       | domain/operator/safety/verifier ceilings              | pure (reads `config`) |
| `autonomy.py`, `conviction.py`, `opinions.py`                                                 | earned ceiling, conviction, domains                   | pure                  |
| `instinct_stream.py`, `scar_graph.py`, `motif_mining.py`, `instinct_signal.py`, `instinct.py` | streaming instinct + scar graph                       | mixed                 |
| `run_events.py`                                                                               | discrete run-event enum + log                         | pure                  |
| `workspace.py`, `attention_schema.py`                                                         | GWT competition + 10-term salience                    | pure                  |
| `self_model.py`, `conflict.py`                                                                | metacognition + dissonance                            | pure                  |
| `conflict.py`, `consolidation.py`                                                             | dissonance + teardown consolidation                   | pure                  |
| `continuity.py`, `user_model.py`, `gating.py`                                                 | identity letters, service-only user model, PRISM gate | mixed                 |
| `psyche_runtime.py`                                                                           | the per-tick glue (ensure/tick/integrate_outcome)     | orchestration         |
| `psyche_store.py`                                                                             | durable cross-run persistence (SQLite)                | I/O                   |
| `psyche_surface.py`, `psyche_commands.py`                                                     | human-facing readout + command routers                | surface               |
| `ab_harness.py`, `integration.py`                                                             | dark-launch A/B + live wiring                         | orchestration         |
| `human_nature_bridge/` (package)                                                              | per-subsystem couplings into the real run loop        | hot-path              |

Full generated map: `../migration/copied-from-9to5/human_nature-AGENTS.md`.

## Schema → source grounding

### Input frames

| Pneuma schema        | Grounded in (9to5)                                                   | Notes                                                        |
| -------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------ |
| `world-frame`        | `run_events.py` (EVENT_TYPES), verifier signals                      | `verification_signals` is read-only (verifier isolation).    |
| `agent-trace-frame`  | executor traces; `self_model.py`                                     | observable traces only; confidence is a noisy observable.    |
| `memory-frame`       | `self_state.py` competence `{p,n}`, `continuity.py`, `scar_graph.py` | continuity/competence must be _retrieved_, not just written. |
| `governance-frame`   | `operator_authority.py`, `charter.py`, `personality.py`              | ceilings + ratified dials + kill switch.                     |
| `intervention-frame` | _new to the lab_ (implied by spec §11 eval suites)                   | no direct 9to5 module — the lab formalizes ablation.         |

### Output frames

| Pneuma schema                  | Grounded in (9to5)                                                                                   | Notes                                                                                                 |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `psyche-state-frame`           | `self_state.py` (v2), `affect_manifold.py`, `drives.py`, `mood.py`, `prototypes.py`, `self_model.py` | 9 axes + 8 drives mirrored exactly.                                                                   |
| `workspace-broadcast`          | `workspace.py` (`SALIENCE_WEIGHTS`, `tick`)                                                          | 10 salience terms mirrored.                                                                           |
| `instinct-signal`              | `instinct_signal.py` (dataclass + enums)                                                             | **near-exact mirror** + lab-eval fields (base rate, FP rate, time sensitivity, explanation_trace_id). |
| `control-pressure-vector`      | spec §4 (soft-tier bidirectional modulation)                                                         | pressure dims from §4/§6; no single 9to5 module yet.                                                  |
| `authority-request`            | `authority.py` + `operator_authority.py`                                                             | `resolution` records the 5-cap `min` + binding cap.                                                   |
| `causal-trace`                 | spec §9 data flow (receipts)                                                                         | **new to the lab**; the audit backbone for Level 4.                                                   |
| `consciousness-evidence-frame` | spec §11 (eval stack), §14 (claims policy)                                                           | **new to the lab**; indicator families + evidence level.                                              |
| `grounded-self-report`         | `psyche_surface.py`, `gating.py` (PRISM)                                                             | report downstream of state; forbidden-claim filter.                                                   |

## manager-data → future operator-preference stream

| manager-data artifact                                                            | Feeds (future)                                       | Notes                                                                        |
| -------------------------------------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------------- |
| `manager_event_v1` normalized events                                             | adapter → replay input                               | Claude Code action traces; sanitized/redacted; **not integrated this pass**. |
| 13-verb manager action enum + 7 families                                         | `InterventionFrame` seeds / `GovernanceFrame` priors | operator-decision contract; possible-future preference signal.               |
| `approve/reject/retry/abort/pause/resume/none` verb map (`jerry_integration.md`) | `GovernanceFrame` operator intent                    | how an operator clone would resolve gates.                                   |
| gold/eval splits, SFT datasets, models                                           | _out of scope_                                       | private data; no training in Pneuma Lab.                                     |

> manager-data is treated as **possible future operator-preference data only** —
> never the base mind, never overfit to. See
> `../migration/copied-from-manager-data/_PNEUMA_PROVENANCE.md`.

## Divergences (Pneuma Lab is not a 1:1 port)

- **`CausalTrace`, `ConsciousnessEvidenceFrame`, `InterventionFrame`** have no
    direct 9to5 module — they are the lab's contribution: making evaluation and
    auditability first-class rather than implicit.
- Pneuma Lab schemas add eval-oriented fields (base rates, FP rates, audit status,
    counterfactual predictions) absent from the production dataclasses.
- 9to5 stores interior state as a plain dict on `TaskState.meta`; Pneuma Lab
    formalizes each slice as a versioned, validatable frame.

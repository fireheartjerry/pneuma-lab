# Pneuma Lab → NeurIPS 2026 Workshop — Technical Blueprint

**Status:** execution package under Protocol v2. The original plan was
scientifically red-teamed on 2026-07-22. `02-research-thesis.md` is the canonical
scientific contract, `16-protocol-v2-hardening.md` records the rationale and
amendment history, `17-implementation-plan-v2.md` is the executable backlog, and
`18-mathematical-formalism.md` states the estimands, causal graph, and conditional
software guarantees in reviewer-readable notation. `20-rigor-traceability-and-gaps.md`
is the claim-to-proof audit and execution-blocking gap register.
Local implementation, fixture tests, and explicitly authorized local data/model
runs may proceed. Paid compute remains separately approval-gated.

This package converts Pneuma Lab from a broad artificial-psyche research system
into a rigorous, falsifiable empirical study for a NeurIPS 2026 workshop
(primary target: **Who Verifies the Agents? — Toward Reliable Agent
Development**, deadline **2026-08-29 AoE**, 4–9pp excluding references and
appendices, double-blind and non-archival, at NeurIPS 2026 in **Sydney,
Australia**; IAB is the secondary fallback).

## The one-sentence claim

We test whether giving a software-engineering agent a **persistent, causally
active internal state** reduces fixed-denominator repeated harm after a
standardized prior failure, with causal contribution identified by the
registered InfluenceOff/clamp interventions. Notice and explanation remain
registered-secondary descriptive outputs under this gate-first study and cannot
gate the tier-primary claim.

## What the audit established (see `01` and `16`)

The repository has reusable deterministic toy-causal, trajectory, memory,
provenance, and firewall primitives, but **zero of the 39 empirical-pivot tasks
meets its acceptance criteria** at the audited commit. The v1 RUF estimand,
post-branch freeze, detector/head interface, control roster, and inference also
contained fatal design flaws. Protocol v2 fixes those before implementation.
Open-SWE-Traces is an offline trajectory-analysis source, not a runnable task
suite; executable real-repository experiments use a power-feasible SWE-Gym
subset in isolated sandboxes.

## Reading order

| #   | Document                                 | What it fixes                                                                                       |
| --- | ---------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 00  | `00-README.md`                           | Index, claim-to-evidence map, venue, and critical path                                               |
| 01  | `01-current-state-audit.md`              | Honest maturity map of every subsystem (from 15 code-tracing audits)                                |
| 02  | `02-research-thesis.md`                  | **Canonical Protocol v2:** H1–H4 families, embedded H5 co-gates, estimand, seven arms, causal/statistical locks, venue |
| 03  | `03-related-work-positioning.md`         | Audited 2025–2026 neighbours, narrow conjunction claim, scoop assessment, citation ledger           |
| 04  | `04-benchmark-specification.md`          | V1 detail; Protocol-v2 suite roles/opportunity design in 02 supersede contradictions                |
| 05  | `05-agent-condition-specification.md`    | V1 detail; seven-arm roster and fairness contract in 02 are authoritative                           |
| 06  | `06-internal-state-specification.md`     | V1 detail; revised variables/head in 02 and exact equations in 18 are authoritative                 |
| 07  | `07-experimental-protocol.md`            | V1 detail; fixed exposure/opportunities and live-branch protocol in 02 supersede contradictions     |
| 08  | `08-metrics-and-statistics.md`           | V1 detail; endpoints in 02 and exact estimands/inference in 18 are authoritative                    |
| 09  | `09-intervention-and-causal-validity.md` | V1 detail; regimes in 02 and do-interventions/identification in 18 are authoritative                |
| 10  | `10-anti-gaming-specification.md`        | V1 detail; co-gates in 02 and formal decision vector in 18 supersede contradictions                |
| 11  | `11-ablation-matrix.md`                  | V1 detail; H2 battery in 02 and controlled-effect boundary in 18 supersede contradictions           |
| 12  | `12-implementation-plan.md`              | Historical v1 39-task backlog; do not execute                                                       |
| 13  | `13-publication-plan.md`                 | Verify-Agents target, 9/4-page plans, figures, anonymous reproducibility/PDF gates                   |
| 14  | `14-risk-register.md`                    | Live ranked risks with validity gates, mitigation, and honest contingencies                          |
| 15  | `15-decision-log.md`                     | DL-01…DL-45 with supersessions, rejected alternatives, and rationale                                 |
| 16  | `16-protocol-v2-hardening.md`            | Protocol-v1 red-team, hardening rationale, and amendment history                                    |
| 17  | `17-implementation-plan-v2.md`           | **Executable Protocol-v2 backlog:** dependency order, tests, gates, and old-task mapping            |
| 18  | `18-mathematical-formalism.md`           | State/action equations, SCM and do-interventions, exact estimands/inference, and testable propositions |
| 19  | `19-innovation-candidates.md`            | Deferred novelty only; non-normative and forbidden from changing Protocol v2 in this pass             |
| 20  | `20-rigor-traceability-and-gaps.md`       | Source-of-truth map, claim→proof→test→exhibit matrix, and explicit assumption/blocker register         |

**Newcomer path:** 02 → 16 → 18 → 20 → 01 → 17. **Reviewer path:** 02 → 18 → 20 → 03 → 16 → 13 → 14.

## Single source of truth by topic

| Topic | Authoritative source | Conflict rule |
| --- | --- | --- |
| Central claim, H1–H5, seven arms, endpoint definitions, design constants, roster, and power rule | `02-research-thesis.md` §§2–8 | Overrides incompatible detail anywhere else |
| Mathematical notation, probability model, SCM/DAG, do-interventions, estimands, identification, estimators, and validity proofs | `18-mathematical-formalism.md` | Must instantiate, never expand, the scientific contract in `02` |
| Binding decisions and supersession history | `15-decision-log.md` | Latest applicable DL row controls; DL-16–DL-45 supersede named v1 choices |
| Executable task order, dependencies, acceptance tests, and gates | `17-implementation-plan-v2.md` | Controls execution; cannot redefine the science or mathematics |
| Red-team rationale and why Protocol v2 replaced v1 | `16-protocol-v2-hardening.md` | Explanatory only when `02`, `15`, `17`, or `18` is more specific |
| Current repository maturity | `01-current-state-audit.md` plus `docs/project-status.json` | The status manifest wins if dated prose disagrees |
| Claim/proof/test/exhibit coverage and unresolved blockers | `20-rigor-traceability-and-gaps.md` | Audit index only; it points back to the normative sources |
| Deferred novelty | `19-innovation-candidates.md` | Non-normative; no entry changes docs 00–18 |
| V1 detail in `04`–`12` | Historical/reference only | Never overrides Protocol v2 |

This precedence resolves the remaining v1/v2 ambiguity: `03`–`16` may
supply history, rationale, venue, risks, or compatible detail, but no conflicting
v1 condition, estimator, sample unit, intervention, or claim is executable.

## Claim → evidence map

| Claim tier            | Hypothesis | Experiment                                  | Metric/evidence                                                       | Doc    |
| --------------------- | ---------- | ------------------------------------------- | --------------------------------------------------------------------- | ------ |
| Recognition/behaviour | H1         | Seven-arm same-subject live-exposure trial   | carrier-matched pre-action `NoticeReadout` versus all five H1 comparators + fixed-denominator repeat harm | 02, 18, 20 |
| Causal state          | H2         | Influence-off, persistence reset, and randomized clamp battery | lineage-aggregated effects, dose order, powered stochastic-null equivalence | 02, 18, 20 |
| Causal attribution    | H3         | blinded nine-label variable×direction/none track | macro accuracy/recall, coverage and risk–coverage vs all four locked baselines | 02, 18, 20 |
| Generalization        | H4         | known-motif surface/repository holdouts      | held-out paired risk differences in the frozen B-live target population | 02, 18, 20 |
| Discrimination        | H5 (inside H1) | counterfactual/decoy/utility co-gates     | success, engagement, total failure, false avoidance                   | 02, 18, 20 |
| Phenomenal            | —          | **not made**                                 | —                                                                     | 02 §5  |

Across all rows, every observed branch-local refusal, timeout, premature finish,
budget exhaustion, invalid action, model error, OOM/disk exhaustion, sandbox
corruption, or runtime failure is adverse. Only immutable, arm-blind evidence of
one common exogenous outage that makes the complete seven-arm block unobservable
permits block removal.

## Critical path (from `17`)

Governance/baseline → typed schemas and the three-way label firewall →
prototype-lineage manifests, same-subject live pretreatment exposure, independent
task snapshots, and leakage-safe splits → seed-pinned live driver → state, seven
conditions, and shared candidate head → fixed-denominator evaluator → exact
seven-label assignment replay and lineage-cluster causal harness → orchestration,
development freeze, nuisance-only disjoint pilot, power simulation,
preregistration, and official-run gate. The scalar-controller grid receives at
least Pneuma's development budget, and every arm shares the complete resource-
accounting boundary. Offline trajectory enrichment can run in parallel but
cannot substitute for live treatment evidence.

## Provenance

Built from 15 parallel read-only code-tracing audits of the repository (working
notes in the session scratchpad under `audit/`) plus a verified related-work and
on-disk-data survey. Protocol-v2 hardening amendments, including DL-24–DL-45,
are recorded in `15`; no confirmatory result is claimed by this blueprint.

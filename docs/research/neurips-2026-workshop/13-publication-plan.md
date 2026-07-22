# 13 — Publication Plan

Status: planning. This document fixes _where_ the first paper goes, _how_ it is
laid out on the page, _which figures/tables/artifacts_ it ships, and _what gets
cut_ if only partial results land. It inherits every Locked Design Constant from
`02-research-thesis.md` §8; any deviation is recorded in `15-decision-log.md`.

Scope reminder: this is a **planning** document. Nothing here authorizes
implementation, training, experiments, or data conversion. It plans the
deliverable, not the science.

Terminology: "claim tier" below always refers to the six-tier ladder in
`02-research-thesis.md` §5 (1 engineering, 2 behavioural, 3 causal, 4
generalization, 5 introspection-faithfulness, 6 phenomenal — **tier 6 never
claimed**).

---

## 1. Target venue

### 1.1 Primary — IAB @ NeurIPS 2026

- **Workshop:** Interpreting Agent Behavior (IAB) — "Human-Centered
  Interpretation for Understanding Agents, Humans, and Interaction," the first
  IAB workshop. Site `iab-agents.github.io`; OpenReview group
  `NeurIPS.cc/2026/Workshop/IAB`.
- **Format:** long paper **up to 9 pages + references** (short paper up to **4
  pages + references**). NeurIPS-style, double-blind.
- **Tracks we target:** the **Empirical Studies** track (error taxonomies,
  failure-mode analysis, case studies of agent decisions) as the primary home,
  and the **trajectory-representation Special Track** ("how should we represent
  an agent trajectory?") as a secondary framing hook for our observable-only
  PneumaTrace schema. Negative results and methodological position papers are
  explicitly encouraged — this covers our E-0 disclosure and the honest-negative
  ethic in `docs/research/10-anti-fake-progress.md`.
- **Deadline:** **2026-08-29, midnight AoE.** Submissions open 2026-07-22.
  Reviews 2026-08-31 → 09-20; decisions 2026-09-29; camera-ready 2026-11-20.
  Fast-track "submission with NeurIPS reviews" alternative due 2026-10-01 (not
  our path — we submit fresh).
- **Non-archival.** See §1.3.

### 1.2 Secondary — "Who Verifies the Agents?"

- **Workshop:** "Who Verifies the Agents? Toward Reliable Agent Development"
  (`verify-agents-workshop.github.io`), co-located, same **2026-08-29**
  deadline, OpenReview submission.
- **Fit:** our clamp/ablation _verification of self-report faithfulness_ (H3),
  memory-off null (H2), and improvement-attribution framing map onto its
  "process-level vs outcome verification" and "improvement attribution" topics.
- **Page limit NOT yet published** — do not assume 9/4pp until the full CFP is
  out. Treat as fallback destination only if IAB fit weakens or is rejected;
  same paper body re-skinned toward the verification framing.
- **Submission rule:** submit to **one** primary at a time (both are
  non-archival but concurrent double-submission across two NeurIPS workshops is
  discouraged). Default: IAB. Hold "Who Verifies" as the re-target if IAB
  declines or if reviewer signal says the verification angle lands harder.

### 1.3 Non-archival implication (extension strategy)

IAB is **non-archival**: acceptance does not constitute prior publication, so
the workshop paper can later be **extended into a full archival venue** (a main
NeurIPS/ICLR/ICML track, a \*ACL venue, or a journal) without self-plagiarism
concerns. Consequence for how we write:

- The 9-page workshop paper is scoped as the **core result** (tiers 1–3 solid,
  4–5 as strengthening), deliberately leaving room for an extension that adds:
  the recurrent-hidden-state arm, the ≥2-model robustness sweep at full scale,
  the longitudinal cross-run persistence campaign (B-EVID-LONGITUDINAL), and a
  larger benchmark. Those are named as "future work" in the workshop paper and
  become the delta for the archival version.
- Artifacts (§4) are versioned so the extension re-runs from the same
  commit+config+seed binding — the workshop submission is a checkpoint, not a
  dead end.

**NeurIPS 2026:** Sydney, International Convention Centre, Dec 6–12 (workshops
Dec 11–12). One organizer sub-page shows stale "San Diego" boilerplate; **Sydney
Dec 6–12 is the correct, corroborated location** and the Aug 29 workshop date
holds.

---

## 2. Full paper outline (9-page long paper)

Page budget sums to ~9.0 pages of body (references excluded, per IAB rules).
Every section names the **claim tier(s)** it carries. Tiers reference
`02-research-thesis.md` §5.

| #   | Section                                                | Claim tier(s)            | Pages      | What it does                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| --- | ------------------------------------------------------ | ------------------------ | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| —   | **Abstract**                                           | 1–3 (5 disclaimed)       | 0.15       | One paragraph: the know-act gap, the four matched conditions, the RUF metric, the clamp/ablation causal test, the headline result, and the explicit "no phenomenal-consciousness claim" firewall.                                                                                                                                                                                                                                                                                       |
| 1   | **Introduction + contributions**                       | 1–5 stated; 6 disclaimed | 1.0        | Motivate from the know-act gap (agents know when they fail but repeat the failure). State H1 in plain English. Enumerate 4 contributions: (i) RUF cross-task repeated-failure metric; (ii) four matched conditions incl. retrieval + reflection + retry-count controls; (iii) clamp/ablation causal proof w/ holding null; (iv) prose-blind behaviour/self-report firewall. Bullet the claim tiers and place the tier-6 firewall in the second paragraph so no reviewer misreads scope. |
| 2   | **Related work**                                       | context                  | 0.9        | Five clusters from `research-related-work.md`: agent memory (MemGPT/A-MEM/Voyager), reflection (Reflexion/ExpeL/Self-Refine), SWE eval (SWE-bench/SWE-Gym/SWE-Exp/TraceProbe/Failure-as-a-Process), causal interpretability (ROME/path-patching/Turpin/Kadavath), consciousness indicators (Butlin & Long et al.) **as motivation only**. Pre-empt "isn't this Reflexion / retrieval / SWE-bench / activation-patching" with the four-differentiator table.                             |
| 3   | **Operational reframing (consciousness → motivation)** | context; 6 disclaimed    | 0.5        | The load-bearing scope section. State that machine-interiority vocabulary (scar, affect, instinct, self-model, workspace) is retained **only as operational names for numeric state variables**. Cite the indicator literature as _which structures are worth building_, not as a phenomenal claim. Name the L0 "dashboard with feelings" null as the thing we must beat, and L1 causal modulation as the real bar.                                                                     |
| 4   | **Benchmark**                                          | 1                        | 0.8        | The controlled-motif suite (inject ~12 known motifs into clean SWE-Gym-Raw / SWE-bench-Lite repos → exact motif ground truth + repeat structure + surface variation) and the real-repo suite (Open-SWE-Traces primary + SWE-Gym OpenHands-Sampled). Repo-AND-motif splits; leakage-registry quarantine of the 7 overlapping repos; `training_weight: 0.0` throughout. Failure taxonomy table lives here.                                                                                |
| 5   | **Agent conditions**                                   | 1                        | 0.6        | The six arms (Base, Retrieval-memory, Reflection, Pneuma-state, Retry-count heuristic, Pneuma-state-ablated null). Emphasise the matched-everything discipline: identical base model, tools, budget, retry cap, task order, env; only the memory/state module differs. The zeroed decision head attaches to Base to hold the action space constant.                                                                                                                                     |
| 6   | **Internal state + decision head**                     | 1                        | 0.6        | The four causally-active variables (failure-sensitivity `s_m`, confidence `c`, caution `t`, memory-trust `r`) + derived expected-loss `L`. The bounded decision head maps state → action-shaping pressure over the fixed set (`proceed … stop_and_report`); "emits pressure, not commands." Each variable ships a clamp seam.                                                                                                                                                           |
| 7   | **Causal-validity method**                             | 3                        | 0.6        | Control/treated/null paired design. The deterministic byte-equality clone gate is reused for the synthetic deterministic-oracle sub-experiments; for the live stochastic agent it is **replaced** by the statistical causal path: frozen seeds/prompts/retrieved memory, recorded transcripts, branch-divergence metric, and N-sample distributional nulls with bootstrap effect sizes.                                                                                                 |
| 8   | **Metrics**                                            | 2                        | 0.4        | Define RUF (primary) precisely; list secondaries (task success, first-attempt, recovery, action/token counts, false-avoidance, transfer, calibration, intervention effect size, cross-seed stability). All contrasts **paired**, bootstrap 95% CIs, one pre-registered primary test, multiplicity correction on secondaries.                                                                                                                                                            |
| 9   | **Results**                                            | 2                        | 1.0        | H1 headline: RUF(pneuma) < min(baselines) with non-overlapping paired-difference CI. Main results table + state-evolution plot. Report task-success parity (not bought by inertia — forward-references H5).                                                                                                                                                                                                                                                                             |
| 10  | **Ablations**                                          | 3, 4                     | 0.7        | H2 clamp/ablation (RUF(ablated) ≈ RUF(base)); dose-response on scar strength; H4 transfer across surface / held-out repo / held-out motif. Ablation table + intervention control/treated/null plot.                                                                                                                                                                                                                                                                                     |
| 11  | **Anti-gaming**                                        | 1, 2                     | 0.5        | Prose-blind evaluator; hidden motifs; decoy memories; adversarially-misleading reflections; counterfactual tasks (old strategy now correct → H5 false-avoidance guard); N-judge motif-label ensemble; immutable traces bound to commit+config+seed. Worked adversarial examples figure.                                                                                                                                                                                                 |
| 12  | **Self-report faithfulness**                           | 5                        | 0.5        | H3: four report conditions (template / unconstrained-LLM / grounded-LLM / grounded+verified). When variable `v` is clamped, the report's identified cause tracks `v` above chance; grounded+verified beats unconstrained; self-report **never feeds the behavioural score**. Faithfulness table.                                                                                                                                                                                        |
| 13  | **Limitations + ethics**                               | all; 6 firewall          | 0.5        | The machine-interiority checklist (§6). Foreground the two admitted threats: (a) prior L4 evidence is a **co-designed toy** — this paper's subject is not; (b) true cross-run persistence has never been demonstrated and is scoped honestly. E-0 negative result disclosed. Bracket 9to5/JSpace/RSI/Levels-5–6 as not-attempted.                                                                                                                                                       |
| 14  | **Reproducibility**                                    | 1                        | 0.35       | Point to the artifact package (§4): fail-closed official-run binding, seeds, model+prompt versions, env lockfiles, prereg hypothesis table, model/dataset cards. State the commit+config+data+seed binding rule.                                                                                                                                                                                                                                                                        |
| —   | **References**                                         | —                        | (excluded) | Does not count against the 9-page limit.                                                                                                                                                                                                                                                                                                                                                                                                                                                |

Budget check: 0.15+1.0+0.9+0.5+0.8+0.6+0.6+0.6+0.4+1.0+0.7+0.5+0.5+0.5+0.35 ≈
**9.1 pages** — trimmed to 9.0 by tightening related work (§2) and results
prose. Half-page slack absorbed by moving the full failure-taxonomy table to an
appendix if needed (appendices are permitted beyond 9pp at IAB as supplementary,
but no core claim may depend on appendix-only content).

---

## 3. Figures and tables

Each entry: what it shows, and which hypothesis / claim tier it supports.

| ID  | Type                           | Section | Shows                                                                                                                                                                                                                                     | Supports                                                                                      |
| --- | ------------------------------ | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| F1  | System diagram                 | §5–6    | The one-base-model + one-scaffold spine branching into the six arms → benchmark → immutable traces → prose-blind evaluator (RUF) → paired runner → self-report eval. (Mirrors the ASCII coherence diagram in `02-research-thesis.md` §9.) | Tier 1 (engineering: the system builds and runs end-to-end).                                  |
| F2  | Causal graph                   | §7      | The DAG `event → detector → state var (s_m/c/t/r) → L → decision head → action-shaping pressure → behaviour → outcome`, with the clamp point on `s_m` marked and the null arm's neutralized edge dashed.                                  | Tier 3 / H2 (the state is on the causal path; the clamp targets a real edge).                 |
| F3  | State-evolution plot           | §9      | `s_m` (and `L`) trajectory across a task sequence for the Pneuma-state arm vs the flat null arm, aligned with the point where RUF diverges.                                                                                               | Tier 2 / H1 + H2 dose-response (accumulated scar strength tracks the behavioural effect).     |
| T1  | RUF main-results table         | §9      | RUF per arm (Base / Retrieval / Reflection / Pneuma-state / Retry-count), paired difference vs Pneuma-state, bootstrap 95% CI, plus task-success and token/action budget columns proving matched budget.                                  | Tier 2 / H1 (headline); H5 (success parity).                                                  |
| F4  | Intervention plot              | §10     | Control / treated(clamp) / null RUF (or effect-size) bars with CIs; treated≈base, control=Pneuma-state, null reproduces control.                                                                                                          | Tier 3 / H2 (the clamp removes the effect; the null holds).                                   |
| T2  | Ablation table                 | §10     | Rows: full Pneuma-state, `s_m`-clamped, decay-off, cap-off, memory-trust-zeroed; columns: RUF, transfer(surface/repo/motif), false-avoidance.                                                                                             | Tier 3 / H2 (which variable carries the effect) + tier 4 / H4 (transfer survives holdout).    |
| F5  | Anti-gaming examples           | §11     | 2–3 worked cases side by side: a decoy memory that a naive agent would misfire on, an adversarially-misleading reflection, and a counterfactual task where the old punished strategy is now correct — with each arm's behaviour.          | Tier 1/2 / H5 (reduction is not bought by inertia; the metric is not gameable by narration).  |
| T3  | Self-report-faithfulness table | §12     | Rows: template / unconstrained-LLM / grounded-LLM / grounded+verified; columns: correct-cause identification rate (above chance?), grounding/unsupported-claim rate, intervention-sensitivity, behaviour-consistency.                     | Tier 5 / H3 (grounded+verified identifies the true clamped variable and beats unconstrained). |

Figure discipline (from the anti-gaming ethic): every number in every figure/table
must be **mechanically derivable from a committed `summary.json`**; no
hand-entered values. Captions state the source artifact path and commit.

---

## 4. Artifacts and reproducibility package

The package **extends the repo's existing fail-closed official-run philosophy**
(`--official` fails closed on a dirty/unpublished tree; every summary records
exact git commit + clean/dirty tree + fetched remote refs — the G-12
commit-provenance discipline). The new rule: **no result enters the paper unless
its artifact is bound to `(commit, config, data, seed)`** and that tuple is
recorded in the artifact's own header.

| Artifact                    | Contents                                                                                                                                                                            | Binding to (commit, config, data, seed)                                                                    |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Experiment spec             | Frozen description of the six arms, benchmark composition, metrics, tests, and stopping rules.                                                                                      | Committed markdown+JSON; header carries the commit it was frozen at; referenced by every run config.       |
| Prereg hypothesis table     | H1–H5 with pre-registered falsification conditions and the single primary test (from `02-research-thesis.md` §3–6).                                                                 | Committed **before** any confirmatory run; commit hash cited in the paper; run configs reference its hash. |
| Benchmark + task generators | Motif-injection generators over clean repos; real-repo adapter configs (Open-SWE-Traces, SWE-Gym OpenHands-Sampled).                                                                | Generator seed + source-corpus digest + repo/motif split manifest recorded per generated instance.         |
| Condition definitions       | One `PsycheUnderTest`/`Perturbable` implementation per arm; the zeroed decision head for Base.                                                                                      | Each arm pinned to a module version + config block hash.                                                   |
| Eval scripts                | Prose-blind RUF scorer, secondary-metric computation, bootstrap/CI + multiplicity-correction code.                                                                                  | Deterministic; output `summary.json` embeds the evaluator commit + input-trace digests.                    |
| Intervention manifests      | Control/treated/null definitions, clamp targets (`scar_graph`, `self_model`, `affect_manifold`, `memory_trust`), expected-vs-observed deltas.                                       | Manifest hash bound into each paired-run `summary.json`.                                                   |
| Canonical run config        | The single pinned config: base checkpoint id, temperature, budgets, retry cap, task order.                                                                                          | The config file's hash **is** the run identity; `--official` refuses to run on a dirty tree.               |
| Seeds                       | Model decode seeds, N-sample null seeds, generator seeds, bootstrap seeds — all enumerated, not implicit.                                                                           | Seed list committed inside the run config; echoed into every output artifact.                              |
| Model + prompt versions     | Frozen open-weight checkpoint id(s) (≥2 sizes for robustness), and byte-frozen prompt templates per arm.                                                                            | Checkpoint id + prompt-template digest recorded in run config and in each `summary.json`.                  |
| Env lockfiles               | `pip`/env lock, OS note (Windows CRLF shard gotcha flagged), tool versions.                                                                                                         | Lockfile digest recorded per official run; mismatch fails closed.                                          |
| Result tables               | The committed `summary.json` files that back T1–T3 and F3–F4.                                                                                                                       | Self-describing: each embeds commit + config hash + input digests + seeds.                                 |
| Model card                  | Subject-model card: what it is, sizes, that it is a **frozen external artifact not trained here**; the PneumaBrain-v0.1 caveat (advisory-only, not the subject, not runtime-wired). | Cites the checkpoint id + the E-0 negative result path.                                                    |
| Dataset card                | Benchmark card: source corpora, motif taxonomy, split policy, leakage-registry quarantine, SWE-bench-family **contamination disclaimer**, `training_weight: 0.0`.                   | Cites the split manifest hash + leakage-registry commit.                                                   |

Binding mechanism (single sentence for the paper): _every artifact header carries
the `(commit, config-hash, data-digest, seed-set)` tuple, `--official` refuses
to emit on a dirty or unpushed tree, and every paper number is traceable to one
committed `summary.json` — "commit-or-it-didn't-happen."_

---

## 5. Short-paper (4pp) fallback plan

Trigger: if by ~2 weeks before the deadline only **partial** results have
landed. The 4-page short paper is the guaranteed-shippable subset. Cut order (cut
from the bottom up; keep the top):

**Keep (non-negotiable core, ~4pp):**

1. Abstract + a compressed intro with the four contributions and the tier-6
   firewall (~0.75pp).
2. The operational reframing paragraph (~0.25pp).
3. Benchmark + conditions, compressed to the **synthetic controlled-motif suite
   only** (deterministic, byte-reproducible, no live-agent variance) + the four
   core arms (~1pp).
4. RUF main result on the synthetic suite: **T1** + one figure (**F3 or F4**,
   whichever landed) (~1pp).
5. Anti-gaming (compressed) + limitations/ethics + reproducibility pointer
   (~1pp).

**Cut, in this order, if results are thin:**

1. **Real-repo suite** (Open-SWE-Traces / SWE-Gym) — fall back to the synthetic
   deterministic-oracle suite alone; the byte-reproducible causal path still
   supports H2. State real-repo generalization as future work.
2. **Self-report faithfulness (H3 / §12 / T3)** — demote to a one-paragraph
   "future work"; it is tier-5 strengthening, not core.
3. **Generalization holdout depth (H4)** — keep repo-split, drop motif-split and
   surface-variation transfer if not run.
4. **The retrieval + reflection baselines** — if only Base vs Pneuma-state vs
   ablated-null ran, ship that (H1 vs Base + H2 causal), and name
   retrieval/reflection as the pre-registered next comparison. **Never** cut the
   retry-count baseline or the ablated null — they are the falsification guards
   (E-0 lesson) and the causal control; without them there is no honest claim.
5. **Second model size** — a single-model result is acceptable for the short
   paper _if_ flagged as a single-model artifact in limitations.

Degenerate floor: if even H1 does not separate, the paper becomes an **honest
negative** (per `02-research-thesis.md` §6 and the E-0 precedent) — "persistent
state did not reduce repeated failures under matched budget," with the full
method and artifacts, still submittable to IAB (negatives explicitly
encouraged). This floor is a real, planned outcome, not a failure of the plan.

---

## 6. Ethics + limitations checklist (machine-interiority specific)

Every item is a sentence the paper must contain (or a discipline it must
observe). Grouped by risk.

**Scope / claim hygiene**

- [ ] **No phenomenal-consciousness claim (tier 6).** Stated in the abstract,
      the reframing section, and limitations. `phenomenal_consciousness_claim:
    not_claimed` is the standing status.
- [ ] **Vocabulary firewall.** Every use of scar / affect / instinct /
      self-model / workspace is flagged as an operational name for a numeric
      state variable at first use.
- [ ] **No welfare / moral-status inference.** The paper measures behaviour and
      causal coupling; it takes no position on machine experience, suffering, or
      moral patienthood. Proxies are proxies: scar count ≠ trauma, tension ≠
      affect, operator pushback ≠ suffering.

**Validity threats (must be stated, not buried)**

- [ ] **Co-designed-toy threat.** Prior L4 evidence in this repo is "Level 4 of
      a hand-coded reference implementation inside its own harness" — circular by
      construction. This paper's subject is **not** co-designed with its
      fixtures; state this explicitly and let the hollow/decoy controls carry it.
- [ ] **Persistence is earned, not assumed.** True cross-run persistence has
      never been demonstrated (`reset()` clears scars; the production psyche DB
      never existed on disk). The paper claims persistence only to the extent the
      experiment demonstrates it; longitudinal persistence is scoped as future
      work (B-EVID-LONGITUDINAL).
- [ ] **E-0 disclosure.** The pre-registered E-0 negative (psyche signals AUROC
      0.339/0.349 vs retry-count 0.705, no post-hoc sign-flip) is reported as
      motivation and as the reason retry-count is a mandatory baseline and
      budgets are tightly matched.
- [ ] **Single-model / single-corpus caveats.** Any result on one model size or
      one corpus carries the caveat inline; H1 robustness needs ≥2 model sizes.

**Anti-gaming / integrity**

- [ ] **Prose-blind scoring.** The behavioural evaluator never reads rendered
      prose; self-report quality never feeds the behavioural score. The one-way
      firewall is stated and cited.
- [ ] **No self-report promotion.** Confabulation risk is computed from hash
      cross-checks between grounded reports and the causal trace, not from prose
      content.
- [ ] **Contamination + leakage disclosure.** SWE-bench-family contamination
      disclaimer; repo-grouped + motif-grouped splits; leakage-registry
      quarantine of overlapping repos stated in the dataset card.
- [ ] **Commit-or-it-didn't-happen.** Every number traces to a committed
      `summary.json` from a clean, pushed commit; `--official` fails closed.

**Data / provenance**

- [ ] **Observable-only, no raw trajectory text.** Frames carry digests +
      lengths only; deterministic PII redaction on ingested trajectories.
- [ ] **Standalone boundary.** No import from or write-back into 9to5; no live
      9to5 integration claimed. 9to5 / JSpace / RSI / Levels-5–6 explicitly
      bracketed as **not attempted**, not silently omitted.
- [ ] **No unauthorized training.** All lanes `training_weight: 0.0` /
      `not_authorized`; the paper does no weight training of the subject model.

**Reviewer-facing honesty**

- [ ] **Claim-tier labels.** Every load-bearing sentence carries its tier (1–5);
      tier 6 is disclaimed wherever interiority language appears.
- [ ] **Negative-result parity.** A result where H1 holds but H2 fails is
      reported as a negative causal result, not hidden; the honest-negative ethic
      is stated.

---

## 7. Timeline (deadline 2026-08-29)

| Milestone                                              | Target date                   | Gate                                                       |
| ------------------------------------------------------ | ----------------------------- | ---------------------------------------------------------- |
| Prereg hypothesis table committed                      | before first confirmatory run | H1–H5 + falsification conditions frozen at a pushed commit |
| Synthetic-suite core result (H1 + H2)                  | ~2026-08-08                   | Guarantees at least the short-paper floor                  |
| Real-repo + generalization (H4)                        | ~2026-08-18                   | Upgrades to full long paper                                |
| Self-report faithfulness (H3)                          | ~2026-08-22                   | Tier-5 strengthening; first cut candidate                  |
| Full draft (all figures from committed `summary.json`) | ~2026-08-25                   | Every number mechanically derivable                        |
| Internal review + limitations/ethics pass              | ~2026-08-27                   | Checklist §6 fully satisfied                               |
| Camera-ready submission                                | 2026-08-29 AoE                | `--official` clean-tree binding verified                   |

Decision point ~2026-08-15: if only synthetic H1+H2 have landed, commit to the
**short-paper fallback (§5)** rather than risk an incomplete long paper.

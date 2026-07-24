# 20 — Rigor Traceability, Preregistration Locks, and Gap Register

**Status:** planning audit, 2026-07-22. This document contains no result and
creates no estimand, metric, arm, intervention, estimator, or claim. Normative
authority remains with documents 02, 15, 17, and 18 as indexed in document 00.

## 1. Consolidation result and precedence

| Topic | Single source of truth | Reconciliation |
| --- | --- | --- |
| Claim, hypotheses, arms, metrics, design constants, roster, power rule | 02 §3–§8 | Protocol-v1 conflicts in 04–12 are retired |
| Decisions and supersessions | 15, latest applicable DL row | DL-45 freezes the gate-first roster, scope ladder, causal coverage, and primary/secondary partition without claiming power |
| SCM, DAG, do-operators, estimands, identification, estimators, tests, proofs | 18 | Subordinate to 02; mathematical notation cannot enlarge the claim |
| Execution order and acceptance evidence | 17 | V2-01–V2-39 are the only executable backlog; 12 is historical |
| Rationale | 16 | Explanatory; a more specific rule in 02/15/17/18 wins |
| Repository maturity | 01 and docs/project-status.json | Status manifest wins over stale narrative |
| Deferred novelty | 19 | Non-normative; no entry is adopted in this pass |

Resolved conflicts:

1. The primary RUF name means exactly fixed-denominator repeat_harm; every
   arm-specific post-exposure v1 denominator is retired.
2. The roster has seven labels. InfluenceOff is the Pneuma
   influence-off regime and is an H2 diagnostic, not a sixth H1 comparator or
   an eighth arm.
3. Assignment-exact Fisher inference targets the sharp global null.
   Population-average intervals and p-values use the whole-lineage bootstrap;
   the two outputs are not interchangeable.
4. The independent unit is the highest dependency lineage. Pairing carries all
   arms and nested seeds together; sequences and seeds are not independently
   resampled.
5. H1–H4 occupy four permanent Holm slots. H5 is evaluated once as H1 utility
   co-gates.
6. Component clamps identify controlled-coordinate sensitivity on registered
   eligible prefixes, not natural mediation or general mechanism necessity.
7. The notice/report firewall is a dataflow contract. Stronger module-graph
   separation requires the still-open V2-03 evidence and is not claimed now.

## 2. Locked design and bookkeeping

| Item | Locked value |
| --- | --- |
| Primary subject | Frozen Qwen2.5-Coder-7B checkpoint/configuration selected under the existing seed audit; no weight training |
| Arms | Base, Retrieval, Reflection, Retry-count, persistent Motif-count/EMA scalar, Pneuma, InfluenceOff |
| H1 comparators | Base, Retrieval, Reflection, Retry-count, persistent Motif-count/EMA scalar |
| Pilot | Exactly 30 disjoint highest-dependency authored lineages; nuisance-only projection |
| Suite A nominal roster | Exactly 96 registered sequences, six motifs, 16 sequences per motif |
| Nested schedule | Three challenges, seven arms, two fixed decoding seeds; nested under lineage |
| Causal subroster | Exactly 48 Suite-A sequences, eight per motif |
| Suite B-live | Exactly 36 sequences, four mechanically scorable known motifs, nine per motif |
| Exposure | One same-subject live verified untreated failure prefix per registered sequence/motif, cloned before arm mapping |
| Opportunities | Generator-fixed post-exposure slots; target, decoy, and counterfactual notice subsets exactly balanced in each registered cell |
| Sequence state | Independent digest-bound sandbox snapshot for each opportunity; only the arm-declared persistent carrier survives task boundaries |
| Arm mapping | Independent $M_b\sim\operatorname{Uniform}(S_7)$ |
| Execution order | Independent $O_b\sim\operatorname{Uniform}(S_7)$; joint support probability $(7!)^{-2}$ per block |
| H2 branch mapping/order | Independent fair regime and order draws on eligibility sealed from the common prefix |
| Budgets | Same ex-ante candidate, repair, retry, token, tool, and failed-call accounting boundary; notice/report meters equal and separate |
| Power alternative | Every H1 superiority component at $\Delta_{\mathrm{power}}=0.10$; true utility differences zero; frozen 0.05 non-inferiority margins |
| Power target | At least 0.80 probability that the complete H1 conjunction passes |
| Independent sample | $G^\star$ highest-dependency lineages selected by the existing deterministic joint-power rule after the nuisance-only pilot |
| Infeasibility | No confirmation if $G^\star$ cannot be instantiated inside the fixed roster, except the already-predeclared scope-narrowing rule |

The nominal counts are final planning numbers. The powered independent-lineage
count is deliberately not fabricated: it is undefined until the 30-lineage
nuisance-only pilot supplies the covariance, event-rate, attrition, detector-
error, and intracluster-correlation inputs already required by the frozen DGP.
The 96 sequences are a capacity, not a claim of 96 independent observations.

## 3. Preregistration lock table

| Lock | Exact content | Authority | Must exist before | Current status |
| --- | --- | --- | --- | --- |
| Scientific claim | H1–H4 and embedded H5, claim tiers, honest-negative regions | 02 §2–§6 | Development work | Locked in prose |
| Arm registry | Seven arms, five H1 comparators, InfluenceOff alias/regime | 02 §8.2; 18 §4.1 | Any assignment | Locked in prose; artifact open |
| State policy | Four coordinates, update equations/constants digest, pressure head | 02 §8.3–§8.4; 18 §1–§2 | Pilot | Form fixed; numeric dev artifact open |
| Exposure/opportunity roster | Prefix receipts, lineages, 96/6/16 roster, challenges, two seeds, fixed slots | 02 §3, §8.6, §8.12 | Pilot | Counts locked; concrete artifacts open |
| Outcome maps | repeat_harm, notice score, co-gates, oracle and outage rules | 02 §3, §8.7–§8.8; 18 §3, §5 | Pilot | Definitions locked; validation artifacts open |
| Notice criteria | Brier orientation, AUROC/calibration/coverage thresholds, bins, support | 18 §3.1 | Pilot | Functional locked; numeric criteria open by design |
| Intervention battery | Influence-off, persistence-off, clamps/doses, update-off, permutation, sham/restore | 02 §8.9; 18 §4.1–§4.2 | Pilot | Regimes locked; values/eligibility artifacts open |
| H3 criteria | Nine labels, target-symmetric packet, grounded+verified and four comparators, support/margins | 02 §4, §8.11; 18 §4.3 | Pilot | Functional locked; numeric criteria open by design |
| Assignment | $M$, $O$, H2 pair assignment, complete support, seeds and receipts | 02 §8.10; 18 §4.2, §7 | Any official run | Mathematical support locked; implementation open |
| Inference | Equal hierarchy, Fisher sharp null, at least 10,000 lineage bootstrap draws, max-T, IUT, Holm | 02 §8.10; 18 §5–§8 | Pilot | Locked in prose; implementation open |
| Exploratory family | Exact BH list and dependence justification | 02 §8.10; 18 §8.2 | Analysis | Open |
| Power | Joint DGP, nuisance-only projection, $\Delta_{\mathrm{power}}=0.10$, 0.80 target, $G^\star$ | 02 §8.10–§8.12; 18 §9 | Confirmation | Rule/count capacity locked; nuisance inputs and result open |
| Environment | Checkpoint, backend, quantization, prompts, tools, sandboxes, seed compatibility, all digests | 02 §8.1; 17 V2-05–V2-06 | Pilot | Open |
| Governance | Standalone boundary with no 9to5 imports, prose-blind behaviour/self-report firewall, `training_weight: 0.0` / `not_authorized`, paid-run approval | 00, 02, 17 | Always | Invariant; execution evidence open |

## 4. Claim-to-proof-to-exhibit matrix

Abbreviations: A1–A12 refer to the gap register in §5. “Proof” means a
conditional mathematical or software result, never empirical support.

| Claim | Estimand or guarantee | Identification assumption and proof/gap | Estimator and validity | Test and decision | Planned exhibit |
| --- | --- | --- | --- | --- | --- |
| Registered-secondary notice IUT against all five comparators | $\Delta_a^N=\nu(p)-\nu(a)$ for five $a$ | A1–A5, A7–A9; Theorem 1 identifies finite roster; notice construct validity remains A5 | Fixed cell→lineage→motif difference; whole-lineage bootstrap and max-T valid under Lemma 1 | Separate descriptive IUT, validity gates, and lower bounds; excluded from selected-tier power and continuation by DL-45 | T1 |
| H1-T selected-tier repeat-harm reduction | $\Delta_a^B=\mu(a)-\mu(p)$ for each tier-required $a$ | A1–A4, A6, A8–A9; Theorem 1; superpopulation step is A6 | Paired complete-block hierarchy; Fisher sharp-null p-value by Proposition 5; average-effect bootstrap by Lemma 1 | Every tier-required component estimate at least 0.05 with lower bound above zero; IUT with utility co-gates | T1 |
| H2-T state-to-action influence | $\delta_{\mathrm{off}}=\mu(p,\iota_{\mathrm{off}})-\mu(p,\iota_0)$ | A1–A4, A7–A9; Theorem 2; surgical gain-zero intervention must be evidenced | Paired eligible-prefix difference; exact assignment analysis plus lineage bootstrap | Required H2-T IUT component; powered practical equivalence can refute scoped influence | F2 |
| H2-T persistence | $\delta_{\mathrm{reset}}=\mu(p,\iota_{\mathrm{reset}})-\mu(p,\iota_0)$ | A1–A4, A7–A9; Theorem 2; no-rehydration evidence is open | Same paired intervention estimator | Required H2-T component plus reset/no-rehydration gate | F2 |
| H2-T controlled component sensitivity and dose ordering | $\delta_d^C,\delta_d^D$ in (7g) | A1–A4, A8–A9; Theorem 2; only eligible-prefix controlled effects identified | Paired clamp/dose differences, fixed orientation, lineage uncertainty | All coordinates/doses in H2-T IUT | F2 |
| H2-T wiring-null validity | $\zeta_j$ and two TOST-side margin quantities | A1–A4, A7–A9; Theorem 2; equivalence margins and stochastic support open | Paired sham/no-op/restore estimator | TOST maximum inside H2-T; restore bytes hard gate | F2 |
| Registered-secondary H3 trace-grounded report advantage | $\gamma_b^M,\gamma_b^C,\gamma_b^0,\gamma_b^R$ for unconstrained, uniform, empirical-prior, receipt-only | A5, A7–A10, A12; Theorem 3 identifies finite paired report performance, not awareness | Same-packet paired macro/coverage/specificity/AURC differences; bootstrap validity conditional on rank regularity | Descriptive H3 IUT plus nine-class/support/no-leak gates; no primary multiplicity slot | T2 |
| Registered-secondary H4 known-motif surface transfer | H1-T-like vector on surface holdout | A1–A9 plus leakage-free split; Theorem 1 | H1-T-like estimator on fixed surface roster | Descriptive $p_{H4,S}$ inside H4 IUT; no primary multiplicity slot | T2 |
| Registered-secondary H4 known-motif repository transfer | H1-T-like vector on repository holdout | A1–A9 plus repository/ancestry exchangeability; Theorem 1 | H1-T-like estimator on fixed repository roster | Descriptive $p_{H4,R}$ inside H4 IUT; no primary multiplicity slot | T2 |
| H5 discrimination rather than inertia | Frozen utility/non-inferiority $\eta_u$ and fixed-denominator co-gates | A1–A5, A8–A9; Theorem 1 and secondary-functional corollary | Paired hierarchy and component bootstrap | All selected-scope H5 components evaluated once inside H1-T | T1 |
| Candidate set is unchanged and pressure bounded | Candidate bytes invariant; log-odds shift at most $2\beta$ | Interface conformance; Proposition 1; implementation evidence open | Deterministic receipt comparison | Hard engineering gate, not a hypothesis test | F1 |
| Zero pressure is pathwise equivalent at the head | Same selected candidate for same tuple/tie key | Common upstream inputs; Proposition 2; end-to-end equivalence remains empirical | Byte/path comparison | Engineering gate plus separate powered null | F1/F2 |
| Notice and report do not affect behaviour | Missing causal arrows under the declared dataflow graph | A7; Proposition 3 for report; notice analogue follows same sink graph; V2-03 module proof open | Metamorphic receipt equality, not an effect estimator | Hard firewall gate | F1 |
| Assignment-exact sharp-null control | Sharp global null over the registered roster | A1–A4; Proposition 5 | Full-support Fisher enumeration or at least 100,000 plus-one Monte Carlo draws | Separate sharp-null p-value | T1/F2 |
| Strong FWER for confirmatory families | Four family p-values | Component super-uniformity A9; Lemmas 2–3 | IUT maxima then Holm | Four permanent slots at 0.05; logical gates stricter | T1/T2 |
| No phenomenal-consciousness claim | No estimand | Scope statement; no identification attempted | None | Never tested or inferred | None |

## 5. GAP LIST — assumptions not proved

| ID | Explicit assumption or proof boundary | What would violate it | Consequence |
| --- | --- | --- | --- |
| A1 | Consistency: each label/regime has one frozen treatment version and realizes its named potential outcome | Digest drift, hidden treatment variation, InfluenceOff not exactly the declared regime | Affected causal contrast invalid/no-go |
| A2 | SUTVA/isolation: no cross-arm, cross-task, or cross-report interference beyond declared persistence | Shared mutable sandbox, cache, sampler, batch, budget, store, or one arm changing another | Causal identification invalid/no-go |
| A3 | Exchangeability from randomized mapping/order and sealed H2 assignment | Non-uniform support, predictable/overwritten mapping, eligibility opened after assignment | Randomization identification and Fisher validity unavailable |
| A4 | Positivity and complete registered support | Any arm/regime has zero assignment probability, missing class/coordinate, or post-outcome eligibility | Family inconclusive/no-go |
| A5 | Oracle and construct validity | Metamorphic failure, low blinded agreement, prose dependence, label leakage, notice target not fixed before action | Affected notice/behaviour/report claim blocked |
| A6 | Named lineage-superpopulation exchangeability and independence | Convenience-only roster, unmerged shared ancestors, dependence across supposed clusters, undefined target population | Restrict to finite roster; no population bootstrap claim |
| A7 | Diagnostic dataflow isolation | Changing/disabling notice/report changes actor RNG, cache, prompt, state, budget, action, or later task | Firewall and downstream causal claim invalid |
| A8 | Version stability and deterministic replay where claimed | Checkpoint, quantization, prompt, tool, sandbox, precision, tie rule, or constants drift | Treatment undefined; replay/determinism claim fails |
| A9 | Bootstrap/component regularity | Too few lineages, zero variance, unsupported motif/class, inconsistent standard error, mass at rank/threshold discontinuity, non-monotone composite-null test | Population component/family gets $p=1$ and is inconclusive |
| A10 | BH independence or PRDS for exploratory p-values | Shared-lineage dependence does not satisfy the condition | No FDR-control claim; adjusted values descriptive only |
| A11 | Frozen joint power DGP is an adequate planning model | Pilot nuisance inputs outside support, unstable covariance/attrition/error model, infeasible $G^\star$ | DL-45 operationalizes the boundary through the precommitted U0→U1 utility ladder followed by core→floor→no-go; no margin widening, efficacy-driven fallback, or power claim |
| A12 | H3 verifier and packet symmetry are independent of reports | Target-specific fields/missingness, verifier reads output, report before behaviour finalization, unequal packet rosters | H3 invalid/inconclusive |

No source code can prove A5, A6, A10, A11, or semantic completeness. The
software obligations can falsify parts of A1–A4, A7–A9, and A12 but cannot turn
them into universal facts.

## 6. GAP LIST — frozen values and artifacts still open

1. Exact subject checkpoint digest, serving backend, quantization, sampler, and
   two-seed compatibility audit.
2. Concrete 96-sequence lineage registry, six motif roster, transforms,
   challenges, opportunity slots, ancestry digests, and leakage-safe splits.
3. Exact four-lane update constants, diagnostic-to-signal maps, numeric
   precision, missing-diagnostic rule, and constants digest.
4. Frozen current-only recognizer and carrier-conditioned notice artifact,
   calibration bins, AUROC/calibration/coverage thresholds, and minimum support.
5. Matched persistent scalar-controller grid winner and complete fairness ledger.
6. Exact clamp values, dose orientations, eligible-prefix predicates,
   equivalence margins, permutation, update-off, sham/restore schedules, and
   powered stochastic-null draw counts.
7. Exact nine-label H3 balance roster, report prompt/config, confidence/tie rule,
   coverage margin, absolute criteria, and receipt-only decoder artifact.
8. Exact Suite B-live repositories, licenses, base commits, test oracles,
   four-motif assignment, ancestry clusters, and 36-sequence registry.
9. Exact exploratory BH family and a defensible independence/PRDS argument if an
   FDR-control claim is desired.
10. Minimum per-motif lineage support, zero-variance behavior, bootstrap
    quantile convention, standard-error functional, and all analysis seeds.
11. Thirty-lineage nuisance-only pilot projection and the resulting frozen power
    DGP, $G^\star$, Monte Carlo error, component-failure fractions, and proof
    $\pi_{H1}(G^\star)\geq0.80$. This is the central unresolved sample-size
    blocker.
12. Module-graph separation evidence. The current formal claim is only the
    declared dataflow firewall until V2-03 is complete.

## 7. GAP LIST — open V2 tasks

At this planning checkpoint every task in document 17 remains unchecked. No
implementation work in this pass changes that fact.

| Open tasks | Blocking evidence |
| --- | --- |
| V2-01–V2-06 | Green baseline, typed contracts, prose/label firewalls, fail-closed authorization, frozen backend/seed audit, isolated sandboxes/tools |
| V2-07–V2-14 | Typed trajectory labels, recurrence features, exact Suite-A opportunities, recognizer, online signal, arm-blind evaluator, validation, end-to-end label separation |
| V2-15–V2-20 | Sequence/split/lineage registries, transforms/decoys, offline and B-live governance, immutable artifact binding |
| V2-21–V2-23 | Structured candidate protocol, metered live loop, live common-prefix causal descendants |
| V2-24–V2-31 | Retrieval, state, calibration/homeostat, notice/reranking, scalar control, reflection, Pneuma/InfluenceOff, seven-arm parity |
| V2-32–V2-37 | Fixed-denominator endpoint, intervention battery, stochastic nulls, cluster inference/power, deterministic oracle control, H3 evaluation |
| V2-38 | Dry runs, exact 30-lineage nuisance pilot, preregistration freeze, power/no-go receipt, official execution gate |
| V2-39 | Post-execution analysis/paper/reproducibility only; not an execution prerequisite, but required to complete the study |

Confirmatory execution is blocked until V2-01–V2-38 and all preceding gates in
document 17 pass. V2-39 cannot begin in this planning pass because no official
run or result exists.

## 8. What is proved and what is not

Proved conditionally on the stated interfaces/assumptions:

- bounded candidate-preserving pressure and zero-pressure head equivalence;
- finite-roster identification of seven-arm and randomized eligible-prefix
  contrasts;
- finite paired identification of the H3 report-performance functionals;
- finite-randomization validity of the Fisher sharp-null p-value;
- asymptotic whole-lineage bootstrap/max-T validity under explicit regularity;
- IUT validity and strong Holm FWER control from super-uniform components;
- the precise boundary between controlled-coordinate clamp effects and stronger
  mechanism claims;
- the precise boundary between a dataflow firewall and unimplemented
  module-graph separation.

Not proved:

- any empirical H1–H5 claim;
- notice/oracle semantic validity, lineage generalization, BH dependence, or the
  planning DGP's adequacy;
- a numerical powered lineage count or 0.80 power attainment;
- implementation conformance, module isolation, benchmark validity, or
  reproducibility;
- any training, model promotion, phenomenal awareness, or real-world prevalence
  claim.

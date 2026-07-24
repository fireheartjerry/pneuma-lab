# 13 — Publication and Reproducibility Plan

**Status:** Protocol-v2-aligned, revised 2026-07-22. This document implements
the venue decision in DL-22 and the canonical science in
`02-research-thesis.md`; `18-mathematical-formalism.md` supplies the paper's
reviewer-readable equations, SCM, estimands, and conditional propositions. It
does not predict a positive result; every paper
section has a negative/null-result form.

## 1. Venue decision

### 1.1 Primary: Who Verifies the Agents?

Submit to **Who Verifies the Agents?—Toward Reliable Agent Development @
NeurIPS 2026**. The official call specifies:

- research papers of **4–9 pages excluding references and appendices**;
- double-blind review and non-archival publication; and
- deadline **2026-08-29 AoE**.

The workshop is part of NeurIPS 2026 in **Sydney, Australia**.

The hardened paper is a direct fit: it studies process-level verification,
environment-grounded outcome signals, verifier validity, reward/metric gaming,
calibration, cost, and causal attribution in a long-horizon agent. The venue is
not merely a self-report match; its verification questions are the paper's
load-bearing method.

Primary sources:

- workshop call: <https://verify-agents-workshop.github.io/>
- official NeurIPS 2026 template:
  <https://media.neurips.cc/Conferences/NeurIPS2026/Formatting_Instructions_For_NeurIPS_2026.zip>

The template archive fetched and successfully smoke-built on 2026-07-22 has
SHA-256 `82473931e3ef710fcd3f4a8cd4119b9de32e56825f90f9e5a6d55f2d01b817d9`.
The local smoke PDF passes `qpdf` 12.3.2 syntax checks and contains embedded
Type-1 fonts only after installing MiKTeX's `cm-super` package.
Re-fetch it at anonymous source freeze; if the digest changes, inspect the diff,
log the replacement, and bind the submitted source/PDF to the new digest.

Use the official template in double-blind workshop mode:

```tex
\documentclass{article}
\usepackage[dblblindworkshop]{neurips_2026}
\workshoptitle{Who Verifies the Agents? Toward Reliable Agent Development}
```

The long-form body targets **8.7–8.8 pages** before final float placement. The
four-page version is a real empirical/methodological fallback, not a compressed
overclaim.

### 1.2 Secondary: IAB

**IAB—Interpreting Agent Behavior @ NeurIPS 2026** remains the sole fallback.
Its state-intervention, trajectory, and attribution themes also fit, but less
directly than Verify-Agents. The IAB public site advertises 2026-08-29 AoE while
the live OpenReview invitation has displayed a timestamp 24 hours earlier; if
we pivot, the earlier platform timestamp is operationally binding unless the
organizers resolve the discrepancy.

Do not submit concurrently to both workshops. Re-target only after withdrawal,
rejection, or an explicit organizer-compatible route.

### 1.3 Non-archival status

Verify-Agents' non-archival status does not itself preclude a later archival
extension. The later venue's overlap, disclosure, and citation rules still
apply. The workshop paper is a versioned evidence checkpoint, not an excuse to
reuse text or results without disclosure.

## 2. Paper identity and scope

Working title:

> **Can Persistent Internal State Prevent Repeated Agent Failures? A Causal
> Verification Study**

Scope sentence, repeated in the abstract, introduction, and limitations:

> “Internal state” denotes measurable machine-addressable controller variables;
> we make no claim about consciousness, sentience, or phenomenal experience.

The paper's verified novelty claim is the conjunction of a non-prose state on
the action path, same-subject live pretreatment exposure and fixed independently
snapshotted opportunities, randomized live state intervention, a treatment/
outcome/report firewall, and cross-task repeat-harm scoring with utility co-gates.
It does not claim that memory, reflection, recurrence tracking, or intervention
is individually new.

## 3. Nine-page outline

| Section | Target pages | Required content |
| --- | ---: | --- |
| Abstract | 0.20 | Anchor question; standardized-exposure estimand; seven matched arms; randomized clamps; headline result stated with interval or explicit null; no-consciousness sentence. |
| 1. Introduction | 0.75 | The repeat-failure problem; E-0 warning; three contributions; Verify-Agents framing; claim boundary. |
| 2. Related work | 0.60 | Closest 2025–2026 memory, coding, intervention, process-verification, and self-report work; concede component overlap; defend only the conjunction. |
| 3. Study contract | 0.70 | H1–H4 family decisions with H5 utility/discrimination co-gates embedded in H1; current-only shared recognizer plus carrier-matched inert notice readouts for every arm; same-subject live pretreatment exposure; fixed opportunities and `repeat_harm`. |
| 4. Benchmark and labels | 0.85 | Suite A independent task snapshots and prototype/generator lineages; Suite B-offline trajectory validity; B-live's mechanically scorable known-motif target; actor/updater/evaluator separation. |
| 5. Conditions and state | 0.85 | Seven arms; four variables `s_m,c,t,r_m`; selected last-bit/count/EWMA/Beta scalar falsifier with at least equal dev budget; complete resource caps/accounting; bounded reranking. |
| 6. Causal and statistical design | 0.95 | Frozen common prefix/live descendants; Influence-off and persistence reset; randomized clamps/doses/shams/permutation; powered stochastic equivalence; independent uniform policy mapping `M` and stream order `O`; Fisher sharp-null replay of `M` conditional on `O`; lineage-cluster bootstrap intervals; family IUT/Holm; pilot firewall. |
| 7. Behavioural results | 1.05 | Carrier-matched pretreatment recurrence readouts for every arm; all five `NoticeScore` contrasts with simultaneous lower bounds >0 and frozen validity gates; all five repeat-harm contrasts additionally require point estimate ≥0.05 and lower bound >0 without claiming the true effect is ≥0.05; utility co-gates; complete resource frontier. |
| 8. Causal and attribution results | 0.75 | Intact vs Influence-off/persistence-off; component/dose/null results; first-divergence distributions; target-symmetric nine-label attribution vs receipt-only decoder; coverage/risk–coverage; report track stays separate. |
| 9. External validity and anti-gaming | 0.65 | Surface/repo known-motif holdouts; explicitly scoped B-live population; decoys/counterfactuals/new failures; branch-local failures adverse; scorer and arm-blinding audits. |
| 10. Limitations, ethics, and conclusion | 0.55 | Power/model/task limits; standardized-exposure scope; detector error; negative findings; no phenomenal claim; safety/data/compute limits. |
| Reproducibility statement | 0.20 | Anonymous artifact id and bundle hash; code/config/data/model/prompt/seed binding; cost ledger. |
| **Total body** | **8.10** | Leaves roughly 0.6–0.7 pages for figures, float movement, and final prose while staying below 9. |

References and appendices are excluded by the primary CFP, but no core claim,
critical exclusion, or decisive negative may exist only in an appendix.

## 4. Main-body evidence budget

Keep the main paper to four information-dense exhibits:

| ID | Exhibit | Non-negotiable content |
| --- | --- | --- |
| F1 | System and causal-design diagram | Seven shared-scaffold arms; current-only recognizer; separate updater and arm-blind evaluator; same-subject live common exposure; independent task snapshots and cloned live descendants; separate report path. |
| T1 | H1 results | Per-arm `repeat_harm`; five paired notice and five paired behaviour effects; separate Fisher sharp-global-null p-values and motif-stratified authored-lineage cluster-bootstrap studentized max-T simultaneous one-sided bounds; carrier-matched pretreatment notice endpoint; utility co-gates; full candidate/reflection/maintenance/repair/token/tool/retry/failed-call accounting. |
| F2 | Intervention figure | Intact, Influence-off, persistence-off, update-off, randomized `s_m` dose, permutation, sham/restore; powered stochastic-null bounds, outcome effect, and first post-intervention intent divergence. |
| T2 | Robustness and attribution | Surface/repo holdouts, motif heterogeneity, scoped B-live result, nine-label macro accuracy/recall, coverage/risk–coverage, receipt-only decoder, and no-change specificity. |

Appendix exhibits include the full motif rulebook, prototype-lineage registry,
recorded seven-label assignments, sequence-flow diagram, per-seed nested results,
complete co-gate table, stochastic-equivalence/null diagnostics, nine-label
confusion matrices and decoder baselines, resource–utility curves, exclusions/
attrition, and the entire negative-results ledger.

Figure/table generation consumes only frozen typed result artifacts. Plot code
must never read report prose, raw prompts, or condition names before pseudonym
unblinding.

## 5. Four-page fallback

A four-page empirical paper may claim H1/H2 only if it retains:

- a powered live Suite-A result from the stochastic coding model;
- Base, Retrieval, Reflection, Retry-count, Motif-count/EMA, Pneuma, and
  Influence-off;
- the common exposure and fixed-denominator endpoint;
- all utility/anti-gaming co-gates;
- same-subject live exposure, independently snapshotted opportunities, and
  prototype/generator-lineage accounting;
- randomized live Influence-off and persistence-off branches, powered stochastic
  null validation, and exact seven-label assignment replay; and
- an honest decision region with uncertainty.

It may cut Suite B-live, most Suite B-offline analysis, H3, H4, the second model,
and extended component ablations. A deterministic oracle is only an engineering
positive control and cannot support a behavioural or causal claim about an LLM.

Suggested body budget:

| Section | Pages |
| --- | ---: |
| Abstract + introduction | 0.65 |
| Estimand, benchmark, seven arms | 1.05 |
| Causal/statistical method | 0.75 |
| Behavioural + Influence-off results | 1.00 |
| Limitations + reproducibility | 0.55 |
| **Total** | **4.00** |

If no powered live result exists, submit a clearly labelled method/negative
paper that validates the benchmark and shows why the causal question remained
unresolved. Do not promote deterministic fixtures, pilots, or underpowered
trends into H1/H2 evidence.

## 6. Reproducibility package

The anonymous review bundle contains:

| Component | Required binding |
| --- | --- |
| Paper source | Official template files and recorded SHA-256 values; deterministic build command; PDF/source-bundle hashes. |
| Source snapshot | Anonymous bundle/tree digest; no remote URL or ownership metadata during review; post-decision mapping to the real commit. |
| Preregistration | H1–H4 family decisions, H5 co-gates embedded only in H1, point-estimate/interval rules, 0.05 non-inferiority margins, lineage/opportunity manifests, strict exogenous whole-block exclusion, actual seven-label assignment mechanism, sample size, multiplicity, model/prompt versions, intervention schedule, and dev-frozen criteria. |
| Run configs | Condition, pseudonymous seven-label block assignment, prototype/generator-lineage digest, model/checkpoint digest, sampler, prompts, candidate count, complete caps, tools, independent sandbox/task/sequence digests, and seeds. |
| Environment | OS/container lock, Python lockfile, package hashes, model-serving versions, deterministic flags, hardware class. |
| Data card | Source/license/provenance, governed raw-to-derived transform, split/quarantine manifests, motif rulebook, privacy constraints, known data limitations. |
| Model card | Exact checkpoint/quantization/license, serving stack, seed behavior, known limitations, development vs confirmatory role. |
| Execution artifacts | Immutable typed traces, same-subject live exposure and independent opportunity receipts, environment-test evidence, state/intervention/persistence receipts, stochastic-null draws, and blinded arm map held separately. |
| Analysis | Frozen scoring/statistics code, lineage-level inputs, recorded assignment replay and bootstrap seeds, H1–H4 family decisions, intervals/effect sizes, strict whole-block exclusions/worst-case attrition, decoder results, and negative-results ledger. |
| Resource ledger | Local and paid hardware-hours, every candidate/reflection/maintenance/repair/fallback call, input/output token, attempted tool action, retry, failed call, wall time, energy proxy where available, current provider price, and actual USD cost; paid total ≤$50. |

During anonymous review, use pseudonymous artifact and run ids. Preserve
cryptographic content/config/data hashes without exposing repository ownership.
After the decision, release the mapping from anonymous source-bundle digest to
the public commit if permitted.

## 7. Double-blind and PDF gates

Before every submission build, fail closed if any check fails:

- main-body page count is ≤9 or ≤4 as applicable;
- no undefined references/citations or overfull boxes;
- all fonts are embedded and no Type 3 fonts appear;
- PDF metadata contains no author, username, local path, or identifying tool
  history;
- authorship is Anonymous; acknowledgments and identifying ownership are absent;
- no local username, absolute path, repository remote, secret, API key, or
  identifying artifact URL appears in source, logs, PDF, or bundle;
- condition/run ids are pseudonymized and the unblinding map is excluded;
- code/config/data/model/prompt/seed hashes reconcile across paper tables and
  artifacts; and
- PDF and source-bundle digests are recorded.

The review artifact uses an anonymous URL only. A raw public commit hash is not
quoted if it can deanonymize ownership; use a source-bundle content digest and
publish the mapping later.

## 8. Ethics and limitations checklist

- State explicitly that internal-state vocabulary is operational and carries no
  consciousness, sentience, welfare, or moral-status conclusion.
- Report standardized-exposure artificiality and separate it from natural-
  sequence policy value.
- Report model-size, seed, task, repository, prototype/generator-lineage, motif,
  detector/evaluator, and power limits with no extrapolation beyond tested
  regimes; restrict B-live conclusions to its frozen mechanically scorable
  known-motif population.
- Treat raw software traces as governed data: minimize raw prose, preserve
  licenses/provenance, scan for secrets/PII, and publish typed/redacted artifacts.
- Run live tools only in isolated disposable sandboxes with network and
  destructive-action restrictions. Never operate on user repositories.
- Report all preregistered outcomes, including E-0, invalid runs, nulls, harms,
  false avoidance, new failure substitution, branch-local non-engagement as
  adverse, and the narrowly evidenced common exogenous whole-block outages.
- Keep report prose causally inert and outside every behavioural score.
- Report compute and paid cost; do not spend paid credits without explicit user
  approval.
- Preserve the standalone boundary: no import from or write to 9to5.

## 9. Execution timeline

| Date | Gate |
| --- | --- |
| 2026-07-22–07-24 | Protocol v2, venue, related work, canonical docs, and fresh baseline reconciled. |
| 2026-07-25–08-02 | Core schemas, Suite-A fixtures, three-way label firewall, live driver, state/head, seven arms, metric, causal/statistical harness implemented test-first. |
| 2026-08-03 | Every arm/intervention dry-runs locally; blind/firewall/determinism/property gates pass; all motifs, transforms, checkpoint rules, notice/evaluator criteria, hyperparameters, margins, and controller grids freeze on development data before pilot access. |
| 2026-08-04–08-06 | Disjoint prototype-lineage pilot exposes pooled/blinded nuisance variance, event rates, ICC, detector error, and attrition only; it cannot tune criteria, margins, transforms, controllers, or effects. |
| 2026-08-07–08-09 | Deterministic power rule fixes lineage sample size; pilot lineages remain excluded; preregistration and official manifests/split are sealed. |
| Approval checkpoint | Present exact paid matrix, provider/hardware/price, runtime, and worst-case cost. No RunPod action before user approval. |
| 2026-08-10–08-16 | Confirmatory Suite-A and causal battery; immutable receipts and cost ledger. |
| 2026-08-17–08-20 | Suite-B offline validation and power-feasible SWE-Gym external validation. |
| 2026-08-21–08-24 | Frozen analysis, figures/tables, long paper, and four-page fallback. |
| 2026-08-25–08-27 | Independent review, claim audit, reproduction, anonymity/PDF gates. |
| **2026-08-28** | Submit with a one-day operational buffer before the 2026-08-29 AoE deadline. |

Any slip is handled by reducing optional scope in this order: extended
ablations, second-model breadth, B-live breadth, H3/H4, then long-to-short form.
The common-exposure estimand, all five H1 comparators, Influence-off, utility
co-gates, prototype-lineage inference with the actual seven-label assignment,
the persistence reset required to credit carryover, stochastic-null equivalence,
and honest decision regions are never cut from an H1/H2 claim.

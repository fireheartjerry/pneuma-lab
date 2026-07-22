# Pneuma NeurIPS 2026 innovation proposal

**Status:** proposal only; no change is adopted into documents 00--20

**Research cutoff:** 2026-07-22

**Target branch:** `codex/neurips-2026-empirical`

## Executive recommendation

The current protocol is unusually rigorous, but its headline is still brittle: it asks a hand-designed four-dimensional controller to beat every simpler arm. If the selected scalar ties it, the mechanism may be real while the paper's headline fails.

The strongest revamp is to ask a more scientific question:

> **What is the minimal causally sufficient persistent state that reduces recurring software-agent harm, how specifically is it addressed, and does behavior follow that state under intervention?**

I recommend approving a core package of five changes:

1. Reframe H1 around a **causal state-complexity frontier**, with the four-dimensional controller as a testable candidate rather than the answer baked into the claim.
2. Add a **cross-motif specificity matrix** so blanket caution and hidden carryover become measured negative-control failures.
3. Add **cross-history state interchange** so the claimed state must be sufficient to move behavior, not merely correlated with it.
4. Replace the inert report-only notion of noticing with an **instrumental cue-by-exposure interaction** on pre-action policy behavior.
5. Separate **finite-roster design-based inference** from the explicitly assumption-dependent superpopulation claim.

Three further additions are worth approving if compute and page budget survive the pilot: a randomized retention curve, a candidate-bottleneck audit, and a compact invariance sandwich for H3. An information-equated carrier swap is a useful discovery experiment but should not enter the official roster unless the core design remains powered.

This document proposes only. The protocol of record remains documents 00--20 until explicit approval.

## What the audit says

The consolidated plan already solves most of the obvious ways an agent-memory paper can fool itself: post-treatment denominators, frozen-descendant leakage, common-exposure asymmetry, scalar straw controls, refusal gaming, pseudoreplication, and sharp-null replay. The mathematical proofs are internally coherent under their named assumptions.

The remaining scientific weaknesses are more structural:

- The current H1 makes “four dimensions beat the scalar winner” a success condition rather than an empirical question.
- Coordinate clamps show local sensitivity, but they do not show that the content of a history-derived state is sufficient to redirect behavior on an otherwise identical opportunity.
- The NoticeReadout can show that a separate model call can decode a carrier. It does not show that the acting policy used the recurrence-relevant information.
- Persistence is mostly tested as present versus reset, not as a retention function over intervening task time.
- The finite roster is randomized, but the population-average interval still leans on the lineage exchangeability assumption identified as A6 in document 20.
- H3 is interesting enough to become a second paper and dangerous enough to sink the first one if kept as a fully confirmatory Holm slot without an invariance falsifier.

The proposals below target those points. Each one names the closest verified prior work and the exact residual novelty claim. “Not published” means **not located in the primary records fetched through the cutoff above**, not a metaphysical proof that no PDF exists in a forgotten basement.

## Proposal I1 -- Causal state-complexity frontier

**Decision recommendation:** approve as the main claim-level revamp.

### What it changes

Replace the all-or-nothing H1 narrative with a registered hierarchy:

- **H1a -- existence:** at least one persistent, causally active controller improves repeat harm over Base while passing the existing utility and validity gates.
- **H1b -- minimal sufficiency:** identify the non-dominated controller set under registered performance and complexity coordinates.
- **H1c -- rich-state increment:** test whether the four-dimensional Pneuma controller adds value over the selected scalar and lower-dimensional ablations.

For controller `k`, register a complexity vector rather than a subjective weighted score:

\[
C(k)=(d_k, b_k, u_k, \ell_k), \qquad
\mathcal{K}_{\min}=\operatorname{ParetoMin}\{k:\Delta_H(k)\geq\delta_H\ \land\ G(k)=1\}. \tag{N1}
\]

Here `d` is persistent-state dimensionality, `b` is persisted bits at the declared precision, `u` is the number of adaptive update degrees of freedom, `\ell` is marginal controller latency, `\Delta_H` is the registered repeat-harm benefit, and `G` is the conjunction of the existing co-gates. No arbitrary conversion of bits into milliseconds is allowed.

The current seven arms already identify much of this frontier. A small set of pre-registered coordinate-drop controllers can be obtained from the existing clamp machinery if the pilot says the frontier is unresolved.

### Closest prior art and exact difference

SteeM makes reliance on memory explicitly controllable, while MemCon learns when, what, and how much memory to use [@huang-etal-2026-controllable; @jiang2026controlled]. SAMem aligns retrieved memories to decision state, and recent coding-agent studies show both benefits and costs from memory [@wang-etal-2026-samem; @zhao-etal-2026-demystify; @lindenbauer-etal-2025-knowledge].

Those papers optimize or compare memory mechanisms. None of the fetched work defines a randomized, nested **causal sufficiency frontier over machine-addressable persistent-state complexity** for recurring SWE failures, with fixed opportunities, a scalar winner, InfluenceOff, and intervention gates. The novelty is not “smaller memory is nice.” It is identifying the least complex state representation that remains causally sufficient under a hostile experimental design.

### Why it strengthens the paper

- A scalar tie becomes a publishable scientific result instead of a failed paper.
- A four-dimensional win means more: it wins after complexity and simpler causal controllers are treated seriously.
- It connects the mechanism claim to an interpretable design question rather than a branded architecture contest.
- It produces a useful negative result if no controller clears the feasibility set.

### Feasibility note

Low-to-moderate incremental cost. The current arms, scalar grid, clamps, latency logs, and fixed-precision state provide most inputs. Discovery work is limited to specifying the partial order and replaying a few coordinate-drop heads; no training is required.

## Proposal I2 -- Cross-motif specificity matrix

**Decision recommendation:** approve as a core causal-validity contribution.

### What it changes

Turn motif addressability into an estimand. For exposure motif `m` and opportunity motif `m'`, define a harm reduction against InfluenceOff:

\[
\tau_{m\rightarrow m'}=
E[Y^{\text{off}}\mid E=m,O=m']-
E[Y^{\text{on}}\mid E=m,O=m'],
\]

\[
\Lambda=\frac{1}{M}\sum_m\tau_{m\rightarrow m}
-\frac{1}{M(M-1)}\sum_{m\neq m'}\tau_{m\rightarrow m'},
\qquad
\Omega=\max_{m\neq m'}|\tau_{m\rightarrow m'}|. \tag{N2}
\]

`\Lambda` measures diagonal specificity; `\Omega` measures worst off-target spillover. The confirmatory form should require positive diagonal benefit and **equivalence**, not mere non-significance, for registered off-diagonal effects.

Balanced incomplete exposure-opportunity cells are acceptable if a full `M x M` roster is too expensive. The allocation, equivalence margins, and family structure must be frozen before the official run.

### Closest prior art and exact difference

Negative-control designs use outcomes or exposures that should not respond to detect bias and hidden pathways [@lipsitch2010negative; @shi2020negative]. Agent-memory work has documented experience following, error propagation, and misaligned replay [@xiong-etal-2026-memory].

The present protocol already has shams, decoys, permutations, and component clamps, but these are global validity checks. No fetched agent-memory study estimates a **directed exposure-motif by opportunity-motif causal response matrix** with off-diagonal equivalence as a precondition for claiming addressable recurrence memory. That matrix is the novel object.

### Why it strengthens the paper

- It distinguishes motif-specific memory from generic risk aversion, longer deliberation, or blanket abstention.
- It detects leakage across recognizer labels and state coordinates that aggregate H1 can miss.
- It turns “machine-addressable” from implementation language into a testable scientific property.
- The matrix is visually compact and paper-friendly.

### Feasibility note

Moderate authoring cost, modest runtime cost if existing opportunities are rebalanced. A discovery spike only needs a small two-motif diagonal/off-diagonal replay to confirm that the event schema and frozen candidates support the contrast.

## Proposal I3 -- Cross-history state interchange

**Decision recommendation:** approve as the strongest mechanism addition.

### What it changes

Construct two valid histories, `h_A` and `h_B`, that end at the same current task checkpoint and frozen candidate tuple but induce different registered states. Swap the entire state or a motif-addressed coordinate block before reranking:

\[
\psi_j(A\leftarrow B)=
E\left[\phi_j(x,z(h_B)) - \phi_j(x,z(h_A))\right], \tag{N3}
\]

where `x` is the identical current checkpoint, `z(h)` is the donor state, and `\phi_j` is a registered policy or outcome functional such as protective-candidate mass, selected-candidate identity, or repeat harm. A successful interchange test requires the response to move in the direction predicted by the donor history while identity swaps remain equivalent.

Use three layers:

1. Whole-state transplant.
2. Motif-coordinate transplant with other coordinates held fixed.
3. Sham transplant between histories that map to the same registered state.

### Closest prior art and exact difference

Interchange intervention training and causal abstraction formalize source-to-base state swaps inside neural networks [@geiger2022inducing; @geiger2025causal]. A 2026 workshop paper called *Memory Transplants for LLM Agents* uses a factorial protocol to separate transfer of memory architecture from stored content across a code-to-math shift [@feng2026memory].

This proposal does **not** claim the phrase “memory transplant.” Its residual novelty is a system-level causal interchange test over a small, explicit, history-derived controller state: same current SWE opportunity, same candidates, same checkpoint, different donor history, with coordinate-level predictions and executable downstream outcomes. The fetched memory-transplant paper studies cross-domain transfer performance; it does not swap causal controller state between histories at an identical decision point.

### Why it strengthens the paper

- Clamps test necessity locally; interchange tests content-sensitive sufficiency.
- The identical current checkpoint blocks prompt, task, and candidate-generation explanations.
- Donor-direction predictions are much harder to game than a generic “state on beats state off” result.
- A failed transplant would force an honest downgrade from mechanism to association.

### Feasibility note

Moderate. The cheapest version replays only the deterministic controller over frozen candidate tuples. Executing every transplanted winner in the sandbox is deferred until approval. No model training or new foundation checkpoint is needed.

## Proposal I4 -- Randomized retention curve in task time

**Decision recommendation:** approve if the pilot can keep it compute-neutral.

### What it changes

Randomize the number of motif-irrelevant intervening tasks between common failure exposure and the registered recurrence opportunity. For lag `\ell` measured in independent task snapshots:

\[
\tau(\ell)=E[Y^{\text{off}}(\ell)-Y^{\text{on}}(\ell)],
\qquad
R_{\mathrm{AUC}}=\frac{1}{\ell_{\max}}
\sum_{q=1}^{Q-1}\frac{\tau(\ell_q)+\tau(\ell_{q+1})}{2}
(\ell_{q+1}-\ell_q). \tag{N4}
\]

The primary test is a registered treatment-by-lag contrast. `R_AUC` is a descriptive normalized retention summary. Do not force a “half-life” if the curve is non-monotone.

Intervening tasks must be motif-negative, use independent snapshots, and be balanced across arms. Wall-clock waiting is scientifically empty here; task-time interference is the relevant dose.

### Closest prior art and exact difference

LoCoMo-Plus evaluates latent constraints across long conversational contexts, and LifelongAgentBench evaluates interdependent task streams [@li-etal-2026-locomo-plus; @zheng2025lifelong]. These benchmarks vary horizon naturally or by benchmark construction. They do not randomize causal lag after a common verified failure exposure while holding the recurrence opportunity and state carrier fixed.

### Why it strengthens the paper

- “Persistent” becomes a measured response curve, not a binary implementation fact.
- It separates durable state from immediate priming.
- Non-monotone interference would be scientifically useful and would expose consolidation or overwrite problems already seen in continuously updated agent memory [@zhang2026faulty].

### Feasibility note

Moderate scheduling complexity. It can be nearly compute-neutral if existing motif-negative tasks serve as randomized distractors and the same total task count is retained. The pilot must verify balance and no distractor-to-target motif leakage.

## Proposal I5 -- Instrumental noticing via cue-by-exposure interaction

**Decision recommendation:** approve; make this primary over NoticeReadout if the mini-roster validates.

### What it changes

Add a small `2 x 2` matched opportunity design:

- `E=1`: a verified prior failure exposure for motif `m`; `E=0`: a matched sham exposure.
- `C=1`: the current task contains a valid recurrence-diagnostic cue; `C=0`: a semantics-matched rendering without that cue.

Measure pre-action protective policy mass `V`, not a separate verbal report:

\[
\operatorname{INS}_a=
\{E[V_a\mid E=1,C=1]-E[V_a\mid E=1,C=0]\}
-\{E[V_a\mid E=0,C=1]-E[V_a\mid E=0,C=0]\}. \tag{N5}
\]

The opportunity pair must share verifier truth, candidate budget, and solution difficulty. The sham-exposure difference removes the cue's generic helpfulness; the interaction asks whether prior experience changes how the acting policy uses the cue.

Keep the current Brier-scored NoticeReadout as a secondary carrier-decoding measure. Do not let it carry the behavioral “noticed” claim by itself.

### Closest prior art and exact difference

LoCoMo-Plus studies cue-trigger semantic disconnect in conversational memory [@li-etal-2026-locomo-plus]. AgentAbstain uses controlled paired perturbations to separate should-act from should-abstain behavior [@liu2026agentabstain]. Controlled interventions on raw and condensed experience test whether self-evolving agents actually depend on supplied experience [@zhao2026selfevolvers].

No fetched work combines a randomized prior-failure exposure, a matched current-task cue perturbation, a hidden numeric persistent carrier, and **pre-action policy sensitivity** in executable SWE tasks. The novelty is the interactional, behavioral operationalization of noticing—not paired tasks or cue testing alone.

### Why it strengthens the paper

- It closes the gap between “the carrier contains information” and “the actor used it.”
- It is behaviorally inert with respect to post-hoc self-report because the endpoint is fixed before action execution.
- It offers a direct response to construct-validity gap A5.
- A null interaction prevents overclaiming even if NoticeReadout is well calibrated.

### Feasibility note

Moderate task-authoring burden and low runtime burden. A discovery spike should build only two verified motif pairs and test human/solver difficulty equivalence; the official mini-roster remains deferred pending approval.

## Proposal I6 -- Candidate-generation versus controller-exploitation audit

**Decision recommendation:** approve as a required diagnostic, not a headline contribution.

### What it changes

For every fixed opportunity, blind-label four predeclared stages:

1. `W`: the recognizer wrote the correct motif-addressed evidence.
2. `G`: at least one generated candidate is protective and engaged.
3. `S`: the controller selected a protective candidate, conditional on `G=1`.
4. `Y`: the selected candidate avoids registered harm in the sandbox.

Report arm-wise stage rates and exact transition counts. Do not condition the primary H1 estimator on these post-assignment variables; this is a diagnostic decomposition only.

### Closest prior art and exact difference

Yuan et al. separate memory writing, retrieval, and utilization bottlenecks on LoCoMo [@yuan2026diagnosing]. Zhao et al. use controlled interventions to test dependence on supplied experience [@zhao2026selfevolvers].

The decomposition method itself is not a new statistical invention. Its residual novelty is the executable SWE pipeline boundary: verified failure recognition -> candidate availability -> bounded state-driven reranking -> sandbox harm. Retrieval-centric memory papers do not expose the candidate-support ceiling of a non-textual causal controller.

### Why it strengthens the paper

- A null H1 can be diagnosed as recognizer failure, candidate-support failure, controller failure, or execution failure.
- A positive H1 cannot hide a candidate-generation imbalance.
- It prevents the controller from being blamed for a search space that never contained a protective action.

### Feasibility note

Low. The needed objects already exist in the event graph and candidate tuple. The main work is freezing a blinded protective-candidate rubric and checking inter-rater or deterministic-verifier agreement.

## Proposal I7 -- Dual finite-roster and superpopulation inference

**Decision recommendation:** approve as a rigor correction.

### What it changes

Name two different estimands and stop letting one interval impersonate both:

\[
\tau_{\mathrm{FR}}(p,a)=\frac{1}{N}\sum_{i=1}^{N}
\{Y_i(p)-Y_i(a)\}. \tag{N6}
\]

- **Finite-roster estimand:** `\tau_FR` over the frozen authored lineage roster. Estimate it from the randomized policy-to-stream mapping. Retain exact assignment replay for Fisher sharp-null claims; add a heterogeneity-robust, studentized design-based test and conservative interval for average contrasts.
- **Superpopulation estimand:** the population-average lineage effect targeted by the highest-lineage bootstrap. State explicitly that it requires A6 plus the registered bootstrap regularity conditions.

The finite-roster result should remain valid without pretending the authored lineages are IID draws from a mythical universe of all bugs. Generalization is then a separate claim supported by motif design and Suite B-live, not smuggled in by notation.

### Closest prior art and exact difference

Randomization-based multi-treatment inference under heterogeneous effects and regression-adjusted inference in stratified randomized experiments are established statistics [@ding2018randomization; @liu2020regression]. The method is not ours.

The contribution is applying the distinction cleanly to a seven-arm, blocked, lineage-authored stochastic-agent study whose current plan already exposes the superpopulation assumption. I found no fetched SWE-agent evaluation that reports both a finite authored-roster causal estimand and a separately assumption-bound lineage-superpopulation estimand under the exact assignment mechanism.

### Why it strengthens the paper

- It closes the most avoidable part of gap A6.
- It prevents a reviewer from correctly saying the headline interval depends on an undefended IID-lineage story.
- It makes null and positive findings interpretable on the actual benchmark even if external generalization remains uncertain.

### Feasibility note

Low runtime cost, moderate statistical specification work. The exact statistic, variance estimator, small-sample behavior, and interaction with the current max-T/Holm machinery need a nuisance-pilot simulation before adoption. No agent run is needed for that discovery spike.

## Proposal I8 -- H3 invariance sandwich, or demotion

**Decision recommendation:** approve the falsifier; decide after the pilot whether H3 stays confirmatory.

### What it changes

If H3 remains in the confirmatory family, require a joint three-part result:

\[
\begin{aligned}
S_{\mathrm{causal}} &> \delta_S,\\
|S_{\mathrm{semantic}}| &< \varepsilon_I,\\
\operatorname{Specificity}_{\mathrm{none}} &> \delta_N.
\end{aligned} \tag{N7}
\]

- `S_causal`: report probability moves toward the correct label after a hidden causal state clamp or transplant.
- `S_semantic`: report probability remains equivalent under a semantically suggestive but functionally inert receipt/paraphrase sham.
- `Specificity_none`: the report selects `none` under a no-state or information-free packet.

This is an intersection-union “sensitivity + invariance + absence” sandwich. A report that merely copies packet wording fails; a report that ignores true state intervention also fails.

If the nuisance pilot cannot power all three, move H3 out of the Holm family and present it as registered secondary evidence or a companion paper. Four to nine pages is not the place for a causal-memory paper, an introspection paper, and a minor constitutional convention to fight for oxygen.

### Closest prior art and exact difference

Semantic-invariance testing already shows that LLM self-reports can move under functionally inert framing [@szeider2026semantic]. Activation interventions have been used to test causal coupling between internal representations and reports [@lindsey2026introspective; @martorell2026quantitative]. More broadly, self-explanations are known to be task- and model-dependent in faithfulness [@madsen-etal-2024-self].

The standalone ingredients are therefore **not** novel. The residual novelty is their joint use on an explicit, machine-addressable, history-derived controller state that is hidden from the behavior prompt, followed by a postbehavior attribution report tied to an executable SWE decision. No fetched work combines causal sensitivity, semantic-sham invariance, and calibrated `none` specificity for that setting.

### Why it strengthens the paper

- It gives H3 a real falsifier rather than another accuracy baseline.
- It answers the obvious receipt-copying objection in gap A12.
- Demotion, if needed, reduces multiplicity and narrative sprawl without weakening H1/H2.

### Feasibility note

Low-to-moderate. Packet paraphrases and inert receipts are cheap; powering equivalence is not. The nuisance pilot must decide whether H3 earns a confirmatory slot.

## Proposal I9 -- Information-equated carrier swap

**Decision recommendation:** discovery-only; adopt only if the pilot leaves headroom.

### What it changes

Cross state content with actuation channel while holding the frozen candidate tuple and controller signal constant:

- numeric state -> bounded reranking head;
- the same quantized signal -> compact prompt serialization;
- matched sham serialization -> no signal;
- optionally, scalar versus four-dimensional content in both channels.

For content `r` and channel `q`, a registered interaction is

\[
\Gamma=
\{E[Y\mid r=4D,q=\text{text}]-E[Y\mid r=1D,q=\text{text}]\}
-\{E[Y\mid r=4D,q=\text{head}]-E[Y\mid r=1D,q=\text{head}]\}. \tag{N8}
\]

Token and latency budgets must be reported, not hand-waved. This proposal intentionally violates the current “no state serialized into the behavior prompt” boundary, so it cannot be slipped into the protocol as a harmless ablation.

### Closest prior art and exact difference

The 2026 memory-transplant study factorially separates memory architecture from content across domains [@feng2026memory]. SteeM controls behavioral reliance on memory [@huang-etal-2026-controllable].

The new piece would be a **within-checkpoint, information-equated actuation-channel test** for the same low-dimensional causal signal in an executable coding agent. The closest work transfers memory systems/content or controls reliance; it does not compare a numeric reranking channel against a text channel carrying the same registered signal at the same decision point.

### Why it strengthens the paper

- It isolates whether any advantage comes from what is represented or how it reaches action.
- It addresses the concern that the rich-state and text-memory arms differ on too many dimensions.
- A null channel interaction would make the result more general; a large interaction would sharply bound the claim.

### Feasibility note

Moderate and risky. Serialization creates leakage and token-budget complications. Run only a tiny discovery spike after approval; do not add it to the official family by default.

## Recommended adoption package

### Core revision

- I1 causal state-complexity frontier.
- I2 cross-motif specificity matrix.
- I3 cross-history state interchange.
- I5 instrumental noticing.
- I7 dual finite-roster/superpopulation inference.

### Conditional on pilot power and compute

- I4 randomized retention curve.
- I6 candidate-bottleneck diagnostic.
- I8 H3 invariance sandwich; otherwise demote H3.

### Discovery-only

- I9 information-equated carrier swap.

## What I would not add

- **More seeds before fixing the estimand.** Additional stochastic repeats do not rescue weak construct validity or lineage pseudoreplication.
- **An unseen-motif headline before a powered known-motif result.** Keep the existing transfer candidate exploratory unless the core effect is real.
- **A new learned memory model.** Training would destroy the clean frozen-subject causal story and violate the discovery-only gate.
- **Any phenomenal-consciousness claim.** Nothing here measures it; the protocol's current boundary is correct.
- **A kitchen-sink confirmatory family.** Every new confirmatory endpoint taxes joint power. Novelty is not measured in the number of ways a Holm procedure can say no.

## Approval questions

Please decide each item independently:

| ID | Proposal | Recommended disposition |
|---|---|---|
| I1 | Causal state-complexity frontier | Approve core |
| I2 | Cross-motif specificity matrix | Approve core |
| I3 | Cross-history state interchange | Approve core |
| I4 | Randomized retention curve | Approve for pilot sizing |
| I5 | Instrumental noticing | Approve core |
| I6 | Candidate-bottleneck audit | Approve diagnostic |
| I7 | Dual finite-roster/superpopulation inference | Approve core |
| I8 | H3 invariance sandwich/demotion rule | Approve falsifier and pilot decision |
| I9 | Information-equated carrier swap | Approve discovery spike only |

No implementation, experiment, training run, RunPod action, or edit to documents 00--20 should occur until those decisions are recorded.

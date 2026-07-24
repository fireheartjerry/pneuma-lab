# Innovation proposal derivations log

**Scope:** equations N1--N8 in `21-innovation-proposal.md`

**Status:** proposal mathematics only; none is part of the protocol of record

**Cutoff:** 2026-07-22

## Notation shared by the proposal

- `Y=1` denotes the registered adverse repeat-harm outcome unless an equation names another functional.
- `E` denotes standardized prior exposure; `O` denotes a fixed opportunity.
- `m,m'` index failure motifs.
- `k` indexes a controller and `a` indexes an arm.
- Expectations are over the protocol's declared randomization and stochastic execution, conditional on the frozen roster where relevant.
- All thresholds, equivalence margins, complexity precision, and contrast weights must be registered before official outcomes are observed.

## N1 -- Minimal sufficient controller set

### Equation

\[
C(k)=(d_k,b_k,u_k,\ell_k),\qquad
\mathcal{K}_{\min}=\operatorname{ParetoMin}\{k:\Delta_H(k)\geq\delta_H\land G(k)=1\}.
\]

### Origin classification

**Original proposal construction**, informed by cost/performance and controllable-memory framing in SteeM and MemCon [@huang-etal-2026-controllable; @jiang2026controlled]. It is not copied from either paper.

### Derivation

1. Let `\mathcal K` be the finite registered controller roster.
2. Define feasibility as the conjunction of a minimum harm benefit, `\Delta_H(k) >= \delta_H`, and all existing validity/utility gates, `G(k)=1`.
3. Complexity has incommensurate coordinates: state dimension, persisted precision, update degrees, and marginal latency.
4. A weighted sum would introduce unverifiable exchange rates between those units.
5. Use coordinate-wise dominance instead. Controller `k_1` dominates `k_2` if it is no worse on every coordinate and strictly better on at least one.
6. `ParetoMin` returns feasible controllers not dominated by another feasible controller.

### Assumptions and cautions

- Persisted bits require a frozen numerical precision; Python object size is not a scientific measure.
- `u_k` must count actual adaptive degrees, not source-code lines.
- A non-singleton frontier is a valid result. The equation does not guarantee a unique winner.
- `\delta_H` inherits the protocol's clinical/scientific margin logic; it must not be selected after observing the frontier.

## N2 -- Motif response matrix, locality, and spillover

### Equation

\[
\tau_{m\rightarrow m'}=
E[Y^{\mathrm{off}}\mid E=m,O=m']-
E[Y^{\mathrm{on}}\mid E=m,O=m'],
\]

\[
\Lambda=\frac{1}{M}\sum_m\tau_{m\rightarrow m}
-\frac{1}{M(M-1)}\sum_{m\neq m'}\tau_{m\rightarrow m'},
\qquad
\Omega=\max_{m\neq m'}|\tau_{m\rightarrow m'}|.
\]

### Origin classification

**Original application and summary estimands.** The use of an outcome expected not to respond is motivated by negative-control design [@lipsitch2010negative; @shi2020negative]. `\Lambda` is an ordinary diagonal-minus-off-diagonal contrast; `\Omega` is a worst-case absolute spillover statistic.

### Derivation

1. Higher `Y` is worse, so `off - on > 0` denotes benefit from active state.
2. Each ordered pair `(m,m')` yields one causal contrast under the same standardized exposure and opportunity rules.
3. If state is motif-addressed, diagonal cells should be positive and off-diagonal cells should be near zero.
4. The mean diagonal minus mean off-diagonal response is therefore a locality contrast, `\Lambda`.
5. Mean cancellation can hide one large wrong-motif effect, so `\Omega` records the maximum absolute off-diagonal response.

### Assumptions and cautions

- This does not identify address specificity if exposure to motif `m` changes future tasks through another persistent channel.
- Off-diagonal claims require equivalence margins; failure to reject zero is insufficient.
- If cells use unequal sampling probabilities, both means require registered inverse-probability or design weights. The displayed equation assumes equal cell weighting.

## N3 -- Cross-history state-interchange effect

### Equation

\[
\psi_j(A\leftarrow B)=
E[\phi_j(x,z(h_B))-\phi_j(x,z(h_A))].
\]

### Origin classification

**Adapted conceptually** from interchange interventions and causal abstraction [@geiger2022inducing; @geiger2025causal]. The system-level estimand over Pneuma's explicit state and fixed SWE checkpoint is original to this proposal. It is distinct from cross-domain architecture/content transfer in [@feng2026memory].

### Derivation

1. Hold the current decision input `x` fixed, including the candidate tuple and serving checkpoint.
2. Let history `h_A` produce state `z(h_A)` and history `h_B` produce `z(h_B)` under the frozen updater.
3. Evaluate the same functional `\phi_j` after substituting the donor state from `h_B` for the recipient state from `h_A`.
4. Subtract the identity-state response at `h_A`.
5. Average over registered recipient/donor pairs and execution randomness.

### Assumptions and cautions

- The donor state must lie in the support of states allowed at the recipient checkpoint; otherwise the intervention is extrapolative.
- `x` must include every non-state input to the reranker. Hidden caches would invalidate the “same checkpoint” claim.
- Directional predictions must be declared from the controller equations before observing transplanted responses.

## N4 -- Lag-specific effect and normalized retention area

### Equation

\[
\tau(\ell)=E[Y^{\mathrm{off}}(\ell)-Y^{\mathrm{on}}(\ell)],
\]

\[
R_{\mathrm{AUC}}=\frac{1}{\ell_{\max}}
\sum_{q=1}^{Q-1}\frac{\tau(\ell_q)+\tau(\ell_{q+1})}{2}
(\ell_{q+1}-\ell_q).
\]

### Origin classification

The lag-specific causal contrast is an **original application**. The area calculation is the standard trapezoidal numerical-integration rule, normalized by the maximum registered lag. It is not attributed as a novel mathematical method.

### Derivation

1. Randomization of `\ell` permits a separate on-versus-off harm contrast at each registered lag.
2. The sequence of contrasts is the empirical retention curve.
3. Linear interpolation between adjacent registered lags yields a trapezoidal area.
4. Division by `\ell_max` expresses the area on the same scale as the average treatment effect over task time.

### Assumptions and cautions

- If the smallest lag is not zero, the normalization interval must be `\ell_max-\ell_min` and the sum must begin at `\ell_min`.
- The displayed equation assumes the registered lag grid starts at zero.
- Negative or non-monotone effects remain in the area; they must not be clipped.
- Intervening tasks must be controlled as part of the treatment schedule, not treated as ignorable elapsed time.

## N5 -- Instrumental noticing interaction

### Equation

\[
\operatorname{INS}_a=
\{E[V_a\mid E=1,C=1]-E[V_a\mid E=1,C=0]\}
-\{E[V_a\mid E=0,C=1]-E[V_a\mid E=0,C=0]\}.
\]

### Origin classification

**Standard 2 x 2 interaction / difference-in-differences algebra**, newly applied to prior-failure exposure and recurrence-diagnostic cues in an agent policy. Paired task perturbations and cue-trigger memory evaluation motivate the design [@liu2026agentabstain; @li-etal-2026-locomo-plus].

### Derivation

1. The cue may help even without prior exposure, so the exposed cue contrast alone is not evidence of memory use.
2. Estimate the cue effect under real exposure: `E[V|1,1]-E[V|1,0]`.
3. Estimate the generic cue effect under sham exposure: `E[V|0,1]-E[V|0,0]`.
4. Subtract the second from the first. The remainder is the exposure-by-cue interaction.

### Assumptions and cautions

- Causal interpretation requires randomized or otherwise protocol-identified assignment of both exposure and cue rendering.
- Both cue variants must preserve oracle solution truth. The interaction does not repair a broken matched pair.
- `V` must be measured before action execution and defined independently of the treatment label.

## N6 -- Finite-roster average treatment effect

### Equation

\[
\tau_{\mathrm{FR}}(p,a)=\frac{1}{N}\sum_{i=1}^{N}\{Y_i(p)-Y_i(a)\}.
\]

### Origin classification

**Standard Neyman finite-population estimand**, not novel. The proposal applies it to the frozen authored-lineage roster and separates it from a lineage-superpopulation estimand. Randomization-based multi-treatment and stratified inference are documented in [@ding2018randomization; @liu2020regression].

### Derivation

1. Freeze `N` experimental units at the highest authored lineage level declared by the protocol.
2. Each unit has potential outcomes under policy arms `p` and `a`.
3. The unit effect is `Y_i(p)-Y_i(a)`.
4. Average those effects over the actual finite roster.
5. Random policy-to-stream assignment identifies an unbiased or design-consistent estimator under the protocol's assignment and interference assumptions; it does not require that the roster was sampled IID from a superpopulation.

### Assumptions and cautions

- Fisher sharp-null replay and weak-null average-effect inference are different procedures. Exactness for the former must not be claimed for the latter.
- The appropriate conservative variance for the actual block/permutation design must be specified and pilot-checked.
- This estimand does not establish transport beyond the frozen roster.

## N7 -- H3 invariance sandwich

### Equation

\[
S_{\mathrm{causal}}>\delta_S,\qquad
|S_{\mathrm{semantic}}|<\varepsilon_I,\qquad
\operatorname{Specificity}_{\mathrm{none}}>\delta_N.
\]

### Origin classification

**Original joint acceptance rule** composed of established ideas: causal sensitivity of reports to internal-state interventions [@lindsey2026introspective; @martorell2026quantitative], semantic invariance [@szeider2026semantic], and explanation-faithfulness skepticism [@madsen-etal-2024-self].

### Derivation

1. A state report is useful only if it changes when the target state causally changes: the sensitivity condition.
2. It must not change when only suggestive language changes: the invariance/equivalence condition.
3. It must report absence when no informative state is present: the calibrated-absence condition.
4. Treat all three as necessary. The natural acceptance rule is therefore an intersection-union test, not an average score that lets one strength compensate for one failure.

### Assumptions and cautions

- `S_causal` and `S_semantic` require separately randomized interventions.
- Equivalence uses confidence bounds within `[-\varepsilon_I,\varepsilon_I]`, not `p>0.05`.
- The exact report probability functional and thresholds remain to be specified; this proposal does not silently inherit them from current H3.

## N8 -- Content-by-actuation-channel interaction

### Equation

\[
\Gamma=
\{E[Y\mid r=4D,q=\mathrm{text}]-E[Y\mid r=1D,q=\mathrm{text}]\}
-\{E[Y\mid r=4D,q=\mathrm{head}]-E[Y\mid r=1D,q=\mathrm{head}]\}.
\]

### Origin classification

**Standard factorial interaction contrast**, newly applied to controller content and actuation channel. The architecture/content factorial in [@feng2026memory] is the closest design precedent, but its factors and target estimand differ.

### Derivation

1. Within the text channel, contrast rich versus scalar content.
2. Within the numeric-head channel, contrast the same content levels.
3. Subtract the channel-specific content contrasts.
4. `\Gamma=0` means the incremental effect of rich over scalar content is channel-invariant on the chosen outcome scale.

### Assumptions and cautions

- Text and head channels must receive information-equated quantizations; otherwise the factors are not separable.
- The sign follows the adverse-outcome scale. Report component cell means so the interaction cannot hide qualitative reversals.
- Prompt tokens and latency are part of the intervention and must be reported as co-outcomes.

## Derivation audit result

- N1, N2, N4's causal application, and the joint rule in N7 are new proposal constructions.
- N3 is a system-level adaptation of interchange-intervention logic.
- N5 and N8 are standard factorial contrasts.
- N6 is a standard finite-population estimand.
- N4's numerical integration is the standard trapezoid rule.

No theorem in documents 00--20 is amended by these equations. Adoption would require a separate proof and protocol integration pass.

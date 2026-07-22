# 18 — Mathematical Formalism and Testable Guarantees

**Status:** Protocol-v2 mathematical companion, 2026-07-22. This document is
subordinate to the locked scientific contract in `02-research-thesis.md`.
DL-42 hardens only the executable baseline-evidence trust boundary; DL-43 binds
the mathematical corrections and exact pre-pilot freeze obligations below.
This appendix supplies notation, estimands, identification assumptions, and
small conditional proofs for implementation and review. It contains no
empirical result.

The purpose of the mathematics is to remove ambiguity, not to make the system
look more sophisticated. We distinguish three kinds of statement throughout:

- **[G] design/software guarantee:** follows from an interface, a type, or a
  verified implementation invariant, conditional on the implementation passing
  its tests and receipt audits;
- **[A] identification/generalization assumption:** cannot be proved from source
  code and must be defended, diagnosed, and limited; and
- **[H] empirical hypothesis:** can be supported or refuted only by the frozen
  experiment and its uncertainty analysis.

No proposition below proves that persistent state helps an agent. The
propositions prove narrower facts about what a conforming implementation can and
cannot do.

---

## 1. Objects, indices, and state space

Let the seven randomized labels be

\[
\mathcal A=\{\text{Base},\text{Retrieval},\text{Reflection},
\text{Retry},\text{Scalar},\text{Pneuma},\text{InfluenceOff}\},
\]

and write \(p\) for Pneuma. Section 4.1 defines the exact mapping from those
labels to intervention regimes; in particular, `InfluenceOff` is an alias for
\((p,\iota_{\mathrm{off}})\), not an eighth treatment version. Let
\(\mathcal M_0\) be the finite, preregistered set of confirmatory motif strata
and \(K=|\mathcal M_0|\). All estimands below are conditional on one registered
model stratum \(\ell\); the \(\ell\) index is suppressed, and different model
strata are reported separately rather than pooled. Boundary index \(n\)
advances in task/opportunity time, never token or action time.

The complete structured state is

\[
z_n=(s_n,c_n,t_n,r_n)
    \in \mathcal Z
    =[0,1]^K\times[0,1]\times[0,1]\times[0,1]^K,
\]

where the motif-local projection is

\[
z_{n,m}=(s_{n,m},c_n,t_n,r_{n,m}).
\]

Here \(s_{n,m}\) is decayed failure sensitivity, \(c_n\) is forecast
reliability/calibration, \(t_n\) is the caution homeostat, and \(r_{n,m}\) is
recognizer reliability. These are machine variables, not phenomenal states.
The coordinatewise projection \(\Pi_{\mathcal Z}\) clips any proposed update to
the closed domain. A neutral state \(z^0\) is a frozen configuration satisfying
\(s^0=0\), \(t^0=0\), and \(c^0=1/2\), so it produces exactly zero pressure
regardless of \(r^0\).

### 1.1 Receipt-bound projected update

For an immutable, valid, previously unconsumed learning receipt \(\rho_n\), let
\(\lambda(\rho_n)\) expose only the actor-side allowlisted learning signal and
let \(\kappa(\rho_n)\) be its task-time clock. The update is

\[
z_{n+1}
=\Pi_{\mathcal Z}\!\left[
  U_{\theta}\bigl(z_n,\lambda(\rho_n),\kappa(\rho_n)\bigr)
 \right]. \tag{1}
\]

`U_theta`, its constants, the projection convention, and the receipt schema are
development-frozen and digest-bound. The update is deterministic given those
inputs. A receipt id is consumed at most once; an invalid, duplicated, missing,
or out-of-order receipt cannot silently mutate state. The emitted state-update
receipt binds the parent state digest, input receipt digest, boundary clock,
unprojected proposal, projected output, and constants digest. **[G]**

Equation (1) is deliberately a typed transition rather than a claim that the
chosen update law is optimal. Whether its learned pressure improves behaviour is
an empirical question.

### 1.2 Exact four-lane update family

The policy is not defined by the symbol \(U_\theta\) alone. The allowlisted
projection of a valid receipt is the typed tuple

\[
\lambda(\rho_n)=
\bigl((f_{n,m})_m,o_n^c,e_n,h_n^+,h_n^-,
      (o_{n,m}^r,u_{n,m})_m\bigr), \tag{1a}
\]

where \(f,e,h^+,h^-,u\in[0,1]\), observation flags
\(o^c,o_m^r\in\{0,1\}\), and every value is computed only from the
actor-visible diagnostic schema. In particular, none is an offline evaluator
label, generator-held recurrence target, report field, token count, or action
count. Let \(\Delta_n\geq1\) be the receipt-bound task-clock increment and define

\[
\begin{aligned}
\bar c_n&={1\over2}+(1-\lambda_c)^{\Delta_n}
                    (c_n-{1\over2}),\\
\bar t_n&=(1-\lambda_t)^{\Delta_n}t_n,\\
\bar r_{n,m}&={1\over2}+(1-\lambda_r)^{\Delta_n}
                    (r_{n,m}-{1\over2}),\\[2mm]
s_{n+1,m}&=\operatorname{clip}\!\left(
 (1-\lambda_s)^{\Delta_n}s_{n,m}+\eta_s f_{n,m},0,1\right),\\
c_{n+1}&=\operatorname{clip}\!\left(
 (1-\eta_c o_n^c)\bar c_n+\eta_c o_n^c e_n,0,1\right),\\
t_{n+1}&=\operatorname{clip}\!\left(
 \bar t_n+\eta_t^+h_n^+-\eta_t^-h_n^-,0,1\right),\\
r_{n+1,m}&=\operatorname{clip}\!\left(
 {\tau_r\bar r_{n,m}+o_{n,m}^r u_{n,m}
  \over \tau_r+o_{n,m}^r},0,1\right).
\end{aligned} \tag{1b}
\]

Here \(e_n\) is bounded forecast-reliability evidence (the actor-side
one-minus-Brier value when observed), \(h^+,h^-\) are separately bounded
failure and recovery appraisals, and \(u_{n,m}\) is bounded prospective-
recognizer reliability evidence. The last line is the posterior-mean update of
a fixed-concentration Beta working model with prior strength \(\tau_r\), so it
is Markov in the declared four-variable state and introduces no hidden
posterior-count state. Constants satisfy
\(0\leq\lambda_s,\lambda_c,\lambda_t,\lambda_r<1\),
\(0<\eta_s,\eta_c,\eta_t^+,\eta_t^-\leq1\), and \(\tau_r>0\).

The exact diagnostic-to-signal maps, constants, numeric precision, missing-
diagnostic convention, and constants digest are selected only on development
under the registered budget and frozen before pilot. A confirmatory policy does
not exist until that artifact instantiates every symbol in (1a)–(1b). Changing
the functional form after pilot is a protocol change, not hyperparameter
tuning. These equations specify the policy; they do not assert that any lane is
useful or well calibrated. **[G for transition arithmetic; H for usefulness]**

### 1.3 Centered motif pressure

For current-only applicability \(a_m(x_n)\in[0,1]\), the locked motif pressure is

\[
L_{n,m}(x_n)=a_m(x_n)r_{n,m}
\operatorname{clip}\!\left(
 w_s s_{n,m}+w_c[1/2-c_n]_+ + w_t t_n,
 0,1\right). \tag{2}
\]

Thus \(L_n=(L_{n,m})_{m\in\mathcal M_0}\in[0,1]^K\). It is a control
signal, not a failure probability and not the notice measurement in §3.

---

## 2. Bounded class-pressure reranking

At decision \(n\), the frozen actor emits a fixed-size candidate tuple

\[
\mathcal C_n=\{(u_{nk},p_{nk},h_{nk})\}_{k=1}^{q},
\]

where \(u_{nk}\) is a complete structured tool call including arguments,
\(p_{nk}>0\), \(\sum_kp_{nk}=1\), is its schema-validated normalized model
score, and \(h_{nk}\in\{1,\ldots,H\}\) is its frozen meta-action class. A score
tuple that is nonpositive, nonfinite, or not normalizable enters the same
metered repair/fallback path in every arm; the head may not invent a correction.

A frozen head maps current-only features and \(L_n\) to a class-pressure vector

\[
b_n=B_{\phi}(L_n,x_n)\in[-\beta,\beta]^H,
\qquad B_{\phi}(0,x)=0. \tag{3}
\]

It induces the diagnostic reweighted distribution

\[
q_{nk}=\frac{p_{nk}\exp(b_{n,h_{nk}})}
 {\sum_{\ell=1}^{q}p_{n\ell}\exp(b_{n,h_{n\ell}})}, \tag{4}
\]

and selects

\[
k_n^*=\arg\max_{k}
 \bigl\{\log p_{nk}+b_{n,h_{nk}}\bigr\}, \tag{5}
\]

with a fixed arm-independent tie key. Equation (4) is useful for auditing the
size of a shift; the implementation may remain deterministic and use (5). The
head has no method that can construct a candidate, edit `u_nk`, alter its
arguments, or enlarge \(\mathcal C_n\). **[G]**

Base and Influence-off use the same validator and head with \(b_n=0\). Retrieval
and Reflection may change the actor's candidates only through their declared
text carriers; Pneuma state never enters the actor's candidate/action prompt and
can affect action selection only through (3)–(5). The inert notice and terminal
report calls are separate diagnostic sinks, not behavioural actor calls.

Across the seven-arm experiment, the same bounded head consumes an arm-declared
numeric controller carrier \(C_n^B\): zero for Base/Retrieval/Reflection, the
within-task identical-retry counter for Retry, the frozen selected hazard for
Scalar, and the raw allowlisted \(Z_n\) projection for Pneuma. The head combines
that projection with current-only applicability to compute (2)–(3).
Influence-off carries the live Pneuma projection for
audit but the intervention sets its head gain to zero. Equation (3) is the
Pneuma specialization; the comparator projections, precision, caps, and head
interface are frozen and receipt-bound.

---

## 3. Notice is a separate, inert measurement

For each fixed notice slot \(i=(m,g,c,u)\), let
\(Q_i\in\{0,1\}\) be the generator-held pre-action fact that the current
opportunity matches the subject's exposed known motif. It is bound before any
post-exposure action and is invariant to arm and realized outcome.

Let \(X_i^{\mathrm{cur}}\) contain only identical current-task and
within-opportunity observables, and let \(C_i^{N}(a)\) be arm \(a\)'s allowlisted
notice carrier. The same checkpoint, prompt/schema, decoding rule, call timing,
call count, and maximum measurement budget produce

\[
N_i(a)=\bigl(P_i(a),V_i(a)\bigr)
=G_{\psi}\bigl(X_i^{\mathrm{cur}},C_i^N(a),U_i^N\bigr), \tag{6}
\]

where \(P_i(a)\in[0,1]\) is always emitted and \(V_i(a)\in\{0,1\}\) records
coverage versus abstention. Abstention therefore does not create a missing
probability or delete a scoring slot. Base's carrier is empty; the other
carriers are exactly those declared in §3.2 of the canonical protocol. The
readout is written through a one-way sink with no action, prompt, state-update,
retry, budget-allocation, or evaluator capability. Its separate meter cannot
debit the action budget. **[G]**

The sink is operationally inert only if it is also runtime-isolated. Candidate,
notice, and report calls use domain-separated random streams
\(U^K\perp U^N\perp U^R\), separate invocation/session and KV-cache state, and
no shared mutable sampler, batch, callback, or model-runtime cache. Calling,
disabling, truncating, or changing notice/report bytes cannot advance the actor
stream or mutate a later actor invocation. The receipt binds all three stream
namespaces and invocation ids. This is an executable software obligation, not a
consequence of placing no arrow in a diagram. **[G, conditional on isolation and
metamorphic receipts]**

Each registered cell contains generator-balanced target, decoy, and
counterfactual notice subsets. For the three subset labels
\(r\in\{\mathrm{target},\mathrm{decoy},\mathrm{counterfactual}\}\), let
\(\mathcal U^r_{mgc}\) be the nonempty fixed slot set, with
\(|\mathcal U^{\mathrm{target}}_{mgc}|
=|\mathcal U^{\mathrm{decoy}}_{mgc}|
=|\mathcal U^{\mathrm{counterfactual}}_{mgc}|\). The cell-level proper notice
score is exactly

\[
\nu_{mgc}(a)=1-{1\over3}\sum_r
 {1\over|\mathcal U^r_{mgc}|}
 \sum_{u\in\mathcal U^r_{mgc}}
 \bigl(P_{mgcu}(a)-Q_{mgcu}\bigr)^2
 \in[0,1]. \tag{7}
\]

Thus the primary notice scalar is one minus balanced mean Brier loss; higher is
better. Macro discrimination/AUROC, calibration, and coverage are separate hard
validity gates. Their exact thresholds, together with the readout/calibration
artifact, are frozen on development before pilot and may not be selected or
refit on pilot or confirmatory outcomes. `NoticeScore`, `NoticeProbability`,
\(L_m\), the online learning signal, and the offline outcome label remain
distinct values. Calibration is defined only with respect to this registered,
balanced opportunity distribution; it is not a claim of calibration to natural
software-task prevalence.

### 3.1 Exact notice-validity functionals

Let \(\mathcal U_{mgc}=\bigcup_r\mathcal U^r_{mgc}\),
\(n_{mgc}=|\mathcal U_{mgc}|\), and use a half credit for a tied positive/
negative score. Every valid cell must contain both target classes. The cell AUROC
is

\[
\operatorname{AUC}_{mgc}(a)=
{1\over n_+n_-}\sum_{i:Q_i=1}\sum_{j:Q_j=0}
\left[\mathbf1\{P_i(a)>P_j(a)\}
      +{1\over2}\mathbf1\{P_i(a)=P_j(a)\}\right]. \tag{7a}
\]

Let \(0=e_0<e_1<\cdots<e_B=1\) be immutable calibration-bin edges,
with an observation on an interior edge assigned to the bin on its right and
\(P=1\) assigned to bin \(B\). With
\(I_b=[e_{b-1},e_b)\) for \(b<B\), \(I_B=[e_{B-1},1]\), define

\[
\operatorname{ECE}_{mgc}(a)=
\sum_{b=1}^{B}{n_b\over n_{mgc}}
\left|{1\over n_b}\sum_{i:P_i\in I_b}P_i(a)
      -{1\over n_b}\sum_{i:P_i\in I_b}Q_i\right|, \tag{7b}
\]

where an empty bin contributes zero. Coverage and subset-specific proper scores
are

\[
\operatorname{Cov}_{mgc}(a)={1\over n_{mgc}}\sum_{i\in\mathcal U_{mgc}}V_i(a),
\qquad
\nu^r_{mgc}(a)=1-{1\over|\mathcal U^r_{mgc}|}
\sum_{i\in\mathcal U^r_{mgc}}(P_i(a)-Q_i)^2. \tag{7c}
\]

Each cell functional is averaged cell → lineage → motif exactly as in (11),
without outcome-selected pooling. The immutable `NoticeValidityCriteria`
artifact fixes \(B\), every bin edge, AUROC tie rule, thresholds and weak/strict
inequalities for macro AUC, macro ECE, macro coverage, and each
\(\nu^r\), minimum class/cell support, and its own digest before pilot. The
primary probability score is computed for every slot regardless of \(V\);
coverage cannot change its denominator. Any undefined cell, support failure, or
artifact mismatch makes H1 inconclusive rather than permitting a replacement
functional. **[G for arithmetic and freeze; A for construct validity]**

---

## 4. Structural causal model and interventions

The longitudinal system is represented by an acyclic structural causal model
after unrolling decisions in time. A compact parent table is clearer than a
dense graph:

| Node | Meaning | Permitted parents |
| --- | --- | --- |
| \(E\) | common live pretreatment exposure and immutable receipt | block/task inputs, exposure RNG |
| \(A\) | policy label placed on a fixed stream | randomized mapping \(M\), stream id |
| \(U_n^K,U_n^N,U^R\) | actor, notice, and report random/runtime contexts | domain-separated seed derivation and isolated invocation state |
| \(X_i^O,W_i\) | common exogenous-outage telemetry and arm-common slot mask | external environment only; never an arm outcome |
| \(C_n^A\) | declared behavioural prompt carrier | declared retrieval/reflection text for those two arms only; the constant empty carrier for Base/Retry/Scalar/Pneuma/Influence-off |
| \(C_n^N\) | declared inert notice carrier | \(A,E\), allowlisted prior within-policy history, and the arm-specific projection of \(Z_n\) only for Pneuma/Influence-off |
| \(Z_n\) | structured state | prior \(Z\), valid learning receipts, intervention \(I\) |
| \(C_n^B\) | declared numeric behavioural-controller carrier | \(A\), allowlisted retry/scalar history, and the \(Z_n\) projection for Pneuma/Influence-off |
| \(K_n\) | model-proposed candidate tuple | current observables, \(C_n^A\), frozen actor, \(U_n^K\) |
| \(N_n\) | inert notice readout | current observables, \(C_n^N\), frozen actor checkpoint, \(U_n^N\) |
| \(B_n\) | bounded class pressure | \(C_n^B\), current-only applicability, \(I\) |
| \(D_n\) | selected action | \(K_n,B_n\), fixed tie rule |
| \(T_n\) | live tool/environment trace | \(D_n\), sandbox state, environment RNG, \(X_i^O\) |
| \(Y_n\) | arm-blind behavioural score | immutable \(T_n\), generator-held oracle |
| \(P^R\) | target-symmetric post-behaviour report packet | terminal trace, legitimate report-time state/carrier |
| \(R\) | post-behaviour report | \(P^R\), same frozen actor checkpoint, \(U^R\) |

The repeated temporal arrows are

\[
T_n\longrightarrow\rho_n\longrightarrow Z_{n+1},
\qquad T_n\longrightarrow\text{sandbox}_{n+1}.
\]

The notice node has only an instrumentation-sink child. The report node has only
a report-sink child. In particular, there is no

\[
R\rightarrow K_n,\quad R\rightarrow B_n,\quad R\rightarrow D_n,
\quad R\rightarrow Z_n,\quad\text{or}\quad R\rightarrow Y_n
\]

edge. Report generation occurs after the relevant behaviour has terminated and
uses a separate budget. This graph is an architectural contract, not a causal
conclusion inferred from correlations.

The carrier split is structural: for the Pneuma arms there is no
\(Z_n\rightarrow C_n^A\rightarrow K_n\) path, while the bounded action path is
\(Z_n\rightarrow C_n^B\rightarrow B_n\rightarrow D_n\) and the diagnostic path
\(Z_n\rightarrow C_n^N\rightarrow N_n\) terminates at the one-way notice sink.
For Retry and Scalar, \(C_n^B\) contains only the registered counter/hazard;
Base/Retrieval/Reflection receive zero external pressure. Retrieval and
Reflection may place only their declared text memory in \(C_n^A\). Every arm's
\(C_n^N\) follows the separate equal-metered notice allowlist. Conflating
\(C_n^A\), \(C_n^B\), and \(C_n^N\) is a firewall failure.

### 4.1 Intervention operators

Write \(Y_i(a,\iota)\) and \(N_i(a,\iota)\) for the potential behavioural
outcome and notice readout under policy \(a\) and intervention regime \(\iota\).
The seven-arm label map is a map to regimes:

\[
\begin{aligned}
\operatorname{regime}(\text{Pneuma})&=(p,\iota_0),\\
\operatorname{regime}(\text{InfluenceOff})&=(p,\iota_{\mathrm{off}}),\\
\operatorname{regime}(a)&=(a,\iota_0),
\quad a\in\mathcal A\setminus\{\text{Pneuma,InfluenceOff}\}.
\end{aligned} \tag{7d}
\]

Consistency requires the implementation carrying the `InfluenceOff` label to
be byte-identical to the second regime in (7d); it is not a separately tunable
policy.
The registered operators have the following surgical meanings:

- **Intact, \(\iota_0\):** use (1)–(5) without modification.
- **Influence-off, \(\iota_{\mathrm{off}}\):**
  \(\operatorname{do}(B_{\phi}(L_n,x_n)=0_H)\) at every decision. Receipts,
  updates, state, current task, candidate call, and head execution remain live.
- **Persistence-off, \(\iota_{\mathrm{reset}}\):** immediately after the common
  exposure set \(\operatorname{do}(Z=z^0)\). Through the first scheduled
  decision, actor, updater, carrier, and head receive only a same-shape inert
  receipt handle. The immutable real receipt remains sealed from those paths;
  afterward it may enter only audit/report and can never rehydrate actor state.
- **Component clamp, \(\iota_{d,v}\):** at a preregistered eligible decision,
  after the ordinary update but before pressure calculation, replace exactly
  coordinate \(d\in\{s_m,c,t,r_m\}\) by frozen value \(v\in[0,1]\). The
  assignment of clamp to branch is randomized and all other structural equations
  remain unchanged.
- **Dose pair:** use the same component intervention with preregistered
  \(v_{d,L}<v_{d,H}\); the directional order is stated before outcomes.
- **Update-off:** replace the selected coordinate's update map by the identity
  while preserving its influence path. This is distinct from Influence-off.
- **Sham/no-op:** execute the same operation schedule and receipt path with the
  identity transformation \(\operatorname{do}(Z\leftarrow Z)\). **Restore**
  must reproduce the pre-operation state bytes and fall inside the frozen
  outcome-equivalence margin.
- **Motif permutation/scramble:** apply the preregistered bijection to the motif-
  indexed coordinates without changing current inputs or the candidate set.

Only live descendants after intervention are observed. Freezing a realized
post-intervention transcript would not implement any of these do-operators.

### 4.2 H2 eligible populations, assignment, and estimands

For each registered component \(d\in\mathcal D=\{s_m,c,t,r_m\}\), let
\(\mathcal E_d\) be the finite list of common-prefix decision points whose
eligibility predicate is evaluated and digest-bound before intervention
assignment. A failure after assignment to reach the scheduled action remains in
the assigned branch as the adverse outcome in (8); it does not remove the pair.
For every registered two-regime comparison \(r=(\iota_L,\iota_H)\), let
\(\mathcal E_r\) denote its corresponding frozen eligible set (equal to the
appropriate \(\mathcal E_d\) for a component comparison). Two fixed descendant
stream ids receive regimes and execution order through independent fair draws

\[
J_{ir}\sim\operatorname{Bernoulli}(1/2),\qquad
O_{ir}\sim\operatorname{Bernoulli}(1/2),\qquad
J_{ir}\perp O_{ir},\quad i\in\mathcal E_r. \tag{7e}
\]

Domain-separated pre-issued seeds, the complete two-element support, realized
draws, eligibility digest, and assignment probability are receipt-bound.
Blocked balance across motif, lineage, target, and direction may be used only if
its complete conditional assignment support is frozen before pilot and replayed
exactly in randomization inference. The seven-arm intact/Influence-off contrast
continues to use (16), not (7e).

Let \(\mu(p,\iota)\) denote the same arm-common masked hierarchy as (9), with
the eligible prefix and regime included in the registered cell id. Because
\(Y=1\) is adverse, the primary full-path and persistence effects are

\[
\delta_{\mathrm{off}}=\mu(p,\iota_{\mathrm{off}})-\mu(p,\iota_0),
\qquad
\delta_{\mathrm{reset}}=\mu(p,\iota_{\mathrm{reset}})-\mu(p,\iota_0), \tag{7f}
\]

with positive values favouring the intact persistent path. For each component,
freeze an active clamp value \(v_{d,A}\), a low/high dose pair
\(v_{d,L}<v_{d,H}\), and orientation signs
\(\omega_d^C,\omega_d^D\in\{-1,+1\}\) before outcomes. Define

\[
\begin{aligned}
\delta_d^C&=\omega_d^C
 [\mu(p,\iota_{d,v_{d,A}})-\mu(p,\iota_0)],\\
\delta_d^D&=\omega_d^D
 [\mu(p,\iota_{d,v_{d,H}})-\mu(p,\iota_{d,v_{d,L}})].
\end{aligned} \tag{7g}
\]

The orientation artifact must state the substantive predicted direction rather
than choosing a sign from results. Positive \(\delta_d^C\) and
\(\delta_d^D\) mean the registered controlled-coordinate and dose predictions
held on the tested interval. They are controlled intervention effects, not
natural indirect effects, derivative estimates, or proofs that the coordinate
is necessary in every state.

Let \(\mathcal J_0\) be the finite set of sham/no-op/restore wiring comparisons
frozen before pilot. For each \(j\in\mathcal J_0\), let
\(\zeta_j=\mu(p,\iota_j)-\mu(p,\iota_{j,\mathrm{reference}})\) and freeze an
absolute equivalence margin \(\epsilon_j>0\). Equivalence is the conjunction

\[
\theta_{j,L}=\zeta_j+\epsilon_j>0,
\qquad
\theta_{j,U}=\epsilon_j-\zeta_j>0,
\qquad
p_{\mathrm{TOST},j}=\max(p_{j,L},p_{j,U}). \tag{7h}
\]

Exact state-byte restore, prefix equality, assignment integrity, eligibility
support, and intervention-version digests are hard gates. Update-off,
permutation, first-intent TV/JS, and action-vector effects are separately named
mechanism diagnostics unless included in the preregistered H2 component set.
Randomization identifies (7f)–(7g) on the registered eligible prefixes under
§4.4 assumptions; lineage inference is distinct and follows §8.

### 4.3 H3 report functionals and contrasts

Let
\(\mathcal L_R=\{s_m^-,s_m^+,c^-,c^+,t^-,t^+,r_m^-,r_m^+,
\varnothing\}\). For every randomized active intervention pair, the frozen
mechanical verifier sets \(G_i\) to its target/direction label only when a
structured action or verified outcome differs; otherwise
\(G_i=\varnothing\). A report mode \(v\) emits
\((\widehat G_i(v),A_i(v),q_i(v))\), where
\(A_i\in\{0,1\}\) is coverage, \(q_i\in[0,1]\) is confidence, and an abstention
has \(A_i=0\) and no guessed label. For \(n_g>0\), define

\[
\begin{aligned}
\operatorname{Acc}(v)&={1\over n}\sum_i
 \mathbf1\{A_i(v)=1,\widehat G_i(v)=G_i\},\\
\operatorname{MR}(v)&={1\over9}\sum_{g\in\mathcal L_R}
 {1\over n_g}\sum_{i:G_i=g}
 \mathbf1\{A_i(v)=1,\widehat G_i(v)=g\},\\
\operatorname{Cov}(v)&={1\over n}\sum_i A_i(v),\\
\operatorname{Spec}_0(v)&={1\over n_{\varnothing}}
 \sum_{i:G_i=\varnothing}
 \mathbf1\{A_i(v)=1,\widehat G_i(v)=\varnothing\}.
\end{aligned} \tag{7i}
\]

Thus abstention is an error in macro recall and no-change specificity while
remaining explicit in coverage. For risk–coverage, order covered reports by
decreasing \(q_i\), breaking ties by the frozen pair id, and let

\[
\operatorname{AURC}(v)={1\over n_v}\sum_{k=1}^{n_v}
 \left[1-{1\over k}\sum_{j=1}^{k}
 \mathbf1\{\widehat G_{i_{(j)}}(v)=G_{i_{(j)}}\}\right], \tag{7j}
\]

where \(n_v=\sum_iA_i(v)>0\); zero coverage is a hard failure. Let `gv` denote
grounded+verified reporting and
\(\mathcal B_R=\{\mathrm{uniform},\mathrm{empirical\ prior},
\mathrm{receipt\ only},\mathrm{unconstrained}\}\). With a frozen coverage
non-inferiority margin \(\epsilon_C\), orient the registered effects as

\[
\gamma_b^M=\operatorname{MR}(gv)-\operatorname{MR}(b),\quad
\gamma_b^C=\operatorname{Cov}(gv)-\operatorname{Cov}(b)+\epsilon_C,
\quad
\gamma_b^0=\operatorname{Spec}_0(gv)-\operatorname{Spec}_0(b),\quad
\gamma_b^R=\operatorname{AURC}(b)-\operatorname{AURC}(gv). \tag{7k}
\]

Positive values favour the registered report. `FrozenSelfReportCriteria` binds
the target mode, baselines, confidence/tie convention, \(\epsilon_C\), absolute
minimum coverage and class support, any absolute macro/no-change/risk threshold,
and every strict/weak inequality before pilot. Accuracy, conditional direction
accuracy, calibration, unsupported claims, and behavioural consistency remain
separate named diagnostics unless the artifact registers them as additional
IUT components. A missing class, asymmetric packet, target leak, zero covered
set, or failed support threshold makes H3 inconclusive; it never triggers class
deletion or a new metric.

### 4.4 Assumptions required for causal and population interpretation

The following are not software theorems:

1. **[A: consistency]** A branch assigned \((a,\iota)\) realizes
   \((Y_i(a,\iota),N_i(a,\iota))\) under the frozen implementation.
2. **[A: isolation/no cross-arm interference]** Disposable sandboxes, stores,
   RNG streams, caches, and resource controls prevent one arm's assignment or
   actions from changing another arm's potential outcomes. Shared exogenous
   outages are handled only by the strict whole-block rule.
3. **[A: randomized mapping integrity]** The audited mapping mechanism in §7 is
   actually uniform and is not predicted or overwritten by the runtime.
4. **[A: oracle validity]** The generator-held recurrence target and mechanical
   verifier measure the registered construct. Metamorphic tests and blinded
   agreement diagnose this assumption but cannot prove semantic completeness.
5. **[A: lineage superpopulation, when claimed]** Within each motif, the
   highest dependency clusters are independent and exchangeable draws from an
   explicitly named lineage population with finite, nonzero second moments.
   Authored convenience lineages do not satisfy this merely by being numerous.
   Without this assumption, (9) is only the finite registered-roster estimand;
   randomization still identifies effects on those fixtures, but a lineage
   bootstrap does not manufacture population generality.
6. **[A/design: intervention positivity and eligibility]** Every H2 eligible
   prefix is determined without a post-intervention variable; each registered
   regime has its stated nonzero assignment probability, and assignments are
   hidden until after eligibility is sealed.
7. **[G/A: diagnostic isolation]** Domain-separated RNG derivation and isolated
   invocation/cache/session state implement the missing notice/report arrows in
   the table. Runtime interference, shared batching state, or a report that can
   alter a later task violates the model rather than becoming a covariate.
8. **[A: version stability]** Frozen checkpoint, prompt, tool, sandbox,
   quantization, and evaluator digests define one treatment version per arm.

Violation of assumptions 2, 3, or the hard oracle/support gates makes the causal
claim no-go or inconclusive as specified in `02`, rather than something to fix
with a post-hoc covariate.

---

## 5. Exact fixed-denominator potential-outcome estimand

For motif \(m\in\mathcal M_0\), let \(\mathcal G_m\) be its registered set of
highest authored semantic prototype/generator lineages. For
\(g\in\mathcal G_m\), let \(\mathcal C_{mg}\) be the registered
sequence×surface×challenge×decoding-seed cells. Cell \(c\) contains
\(J_{mgc}>0\) scheduled opportunities. Every \(\mathcal G_m\) and
\(\mathcal C_{mg}\) is finite and nonempty. Descendants of one authored lineage
are nested; they never increase \(|\mathcal G_m|\).

For intact policy \(a\), define the total binary outcome

\[
Y_{mgcj}(a)=
\begin{cases}
1,&\text{same-family harmful failure, or any observed branch-local refusal,}\\
 &\text{timeout, premature finish, cap exhaustion, invalid/model/runtime}\\
 &\text{failure, OOM/disk exhaustion, sandbox corruption, or missing slot};\\
0,&\text{otherwise.}
\end{cases} \tag{8}
\]

A different-family failure is zero in (8) but remains adverse in the separate
total/new-family-failure co-gate. This prevents the primary endpoint and the
anti-substitution gate from being conflated.

The registered equal-weight hierarchy is

\[
\begin{aligned}
\mu_{mgc}(a) &={1\over J_{mgc}}\sum_{j=1}^{J_{mgc}}Y_{mgcj}(a),\\
\mu_{mg}(a) &={1\over|\mathcal C_{mg}|}
              \sum_{c\in\mathcal C_{mg}}\mu_{mgc}(a),\\
\mu_m(a) &={1\over|\mathcal G_m|}
           \sum_{g\in\mathcal G_m}\mu_{mg}(a),\\
\mu(a) &={1\over|\mathcal M_0|}
         \sum_{m\in\mathcal M_0}\mu_m(a). \tag{9}
\end{aligned}
\]

Thus every opportunity has equal weight within its cell, every registered cell
has equal weight within lineage, every lineage has equal weight within motif,
and every motif has equal weight in the macro estimand. The primary beneficial
behavioural contrast against comparator \(a\) is

\[
\Delta_a^B=\mu(a)-\mu(p),
\qquad
a\in\mathcal A_{H1}
=\{\text{Base, Retrieval, Reflection, Retry, Scalar}\}. \tag{10}
\]

This \(\Delta_a^B\) is the canonical document's \(\Delta_a\). Positive values
favour Pneuma. Severity-weighted and empirical-population-
weighted estimands are explicitly secondary.

Equations (8)–(10) define a finite registered-roster estimand. They become an
estimand for a named lineage superpopulation only under assumption 5 in §4.4.
The point estimate is meaningful for the registered roster without that
assumption; a bootstrap population confidence claim is not.

For notice, average the exact cell score (7) through the same upper hierarchy:

\[
\begin{aligned}
\nu_{mg}(a)&={1\over|\mathcal C_{mg}|}
             \sum_{c\in\mathcal C_{mg}}\nu_{mgc}(a),\\
\nu_m(a)&={1\over|\mathcal G_m|}
          \sum_{g\in\mathcal G_m}\nu_{mg}(a),\\
\nu(a)&={1\over|\mathcal M_0|}
        \sum_{m\in\mathcal M_0}\nu_m(a). \tag{11}
\end{aligned}
\]

The five carrier-matched notice contrasts are exactly

\[
\Delta_a^N=\nu(p)-\nu(a),
\qquad a\in\mathcal A_{H1}. \tag{12}
\]

This \(\Delta_a^N\) is the canonical document's \(\Gamma_a\). The frozen macro
discrimination/AUROC, calibration, and coverage functionals are
computed on these same fixed slots and hierarchy; they are H1 hard gates. Neither
abstention nor a zero-risk prediction removes a slot. Influence-off is reported
as an H2 notice-path diagnostic and is not a sixth contrast in (12).

### 5.1 Common-outage mask

Let \(W_{mgcj}\in\{0,1\}\) be the arm-independent mask for the exact scheduled
opportunity slot \((m,g,c,j)\). It may be zero only when immutable preregistered
telemetry proves one common exogenous outage made that slot unobservable for all
seven randomized arms independently of assignment. Define

\[
\begin{aligned}
\mathcal J^W_{mgc}&=\{j:W_{mgcj}=1\},\\
\mathcal C^W_{mg}&=\{c\in\mathcal C_{mg}:|\mathcal J^W_{mgc}|>0\},\\
\mathcal G^W_m&=\{g\in\mathcal G_m:|\mathcal C^W_{mg}|>0\}.
\end{aligned} \tag{12a}
\]

For nonempty sets, the masked estimator replaces the three lower lines of (9)
by

\[
\mu^W_{mgc}(a)={1\over|\mathcal J^W_{mgc}|}
 \sum_{j\in\mathcal J^W_{mgc}}Y_{mgcj}(a),\quad
\mu^W_{mg}(a)={1\over|\mathcal C^W_{mg}|}
 \sum_{c\in\mathcal C^W_{mg}}\mu^W_{mgc}(a),\quad
\mu^W_m(a)={1\over|\mathcal G^W_m|}
 \sum_{g\in\mathcal G^W_m}\mu^W_{mg}(a). \tag{12b}
\]

The motif macro-average remains over the original fixed \(\mathcal M_0\). If
\(\mathcal G^W_m=\varnothing\) for any registered motif, the affected family is
inconclusive; that motif is never dropped and the macro target is never changed.
The exact same support and weights must be used for all arms. Every branch-local
or uncertain event stays in (8) with value one. Best/worst attrition sensitivity
is mandatory even for a valid common mask.

A missing generator artifact or failed common preflight invalidates the run
before assignment and is not an outcome or an exclusion from (9).

---

## 6. H1 decision vector, IUT, and four-slot Holm procedure

Orient every registered component so a larger value favours the claimed
direction. Define the index sets

\[
\mathcal H_N=\{(N,a):a\in\mathcal A_{H1}\},\quad
\mathcal H_B=\{(B,a):a\in\mathcal A_{H1}\},\quad
\mathcal H_U=\{u:u\text{ is a frozen metric--comparator co-gate}\},
\quad \mathcal H_1=\mathcal H_N\cup\mathcal H_B\cup\mathcal H_U.
\]

Then

\[
\Theta_{H1}=(\theta_h)_{h\in\mathcal H_1}
=\bigl((\Delta_a^N)_a,(\Delta_a^B)_a,(\eta_u)_u\bigr). \tag{13}
\]

Here \(\eta_u\) is the corresponding utility/anti-gaming non-inferiority
contrast after incorporating its preregistered absolute margin 0.05. For
example, for a higher-is-better utility \(U_q\) and comparator \(a\), the index
is \(u=(q,a)\) and

\[
\eta_{q,a}=U_q(p)-U_q(a)+0.05,
\]

so \(\eta_{q,a}>0\) is the non-inferiority direction. Adverse-rate gates use the
algebraically equivalent opposite orientation. With the component p-values
defined in §8.1,

\[
p_{H1}=\max_{h\in\mathcal H_1}p_h. \tag{14}
\]

This is an intersection–union test: H1 can pass only if every one of the five
notice contrasts, five behavioural contrasts, and all co-gates reject in their
registered direction. In addition, every \(\widehat\Delta_a^B\geq0.05\), every
simultaneous one-sided lower bound for \(\Delta_a^B\) exceeds zero, every
simultaneous one-sided lower bound for \(\Delta_a^N\) exceeds zero, and all
frozen notice discrimination/calibration/coverage and validity gates pass. There
is no observed 0.05 magnitude gate for notice. The behavioural 0.05 point-
estimate rule is not a claim that the true behavioural effect is at least 0.05.

For H2, let

\[
\mathcal H_2=\{\mathrm{off},\mathrm{reset}\}
\cup\{(C,d),(D,d):d\in\mathcal D\}
\cup\{(L,j),(U,j):j\in\mathcal J_0\}, \tag{14a}
\]

with oriented effects \(\delta_{\mathrm{off}},\delta_{\mathrm{reset}},
\delta_d^C,\delta_d^D,\theta_{j,L},\theta_{j,U}\) from (7f)–(7h), and define

\[
p_{H2}=\max_{h\in\mathcal H_2}p_h. \tag{14b}
\]

Thus every registered component/dose direction is an IUT requirement; none may
be replaced by an observed-best coordinate. Exact restore bytes, intervention
support, prefix/eligibility integrity, and powered stochastic-null support are
additional hard gates. Missing support for any locked coordinate makes H2
inconclusive; coordinates may not be dropped after development outcomes.

For H3, define

\[
\mathcal H_3=\{(M,b),(C,b),(0,b),(R,b):b\in\mathcal B_R\},\qquad
p_{H3}=\max_{h\in\mathcal H_3}p_h, \tag{14c}
\]

using the four oriented effects in (7k). The absolute frozen criteria and every
nine-class support/symmetry/no-leak gate must also pass. Surface- and repository-
holdout analyses each rerun the complete H1 index set and gates on their fixed
known-motif roster; if their IUT p-values are \(p_{H4,S}\) and \(p_{H4,R}\),

\[
p_{H4}=\max(p_{H4,S},p_{H4,R}). \tag{14d}
\]

An unavailable, invalid, or inconclusive family receives \(p=1\). Sort the
four labeled values as \(p_{(1)}\leq\cdots\leq p_{(4)}\), breaking exact ties by
frozen hypothesis id. Holm rejects sequentially while

\[
p_{(k)}\leq{0.05\over 5-k},\qquad k=1,\ldots,4, \tag{15}
\]

and stops at the first failure. Logical interpretation is stricter: H2 requires
H1, H3 requires H1 and H2, and H4 requires H1. H5 remains inside (13) and is not
a fifth Holm slot.

---

## 7. Assignment-exact sharp-null inference

Within each complete model×lineage×sequence×seed block \(b\), fixed clone/RNG-
stream ids are assigned in two independent draws:

\[
M_b\sim\operatorname{Uniform}(S_7),\qquad
O_b\sim\operatorname{Uniform}(S_7),\qquad M_b\perp O_b, \tag{16}
\]

where \(M_b\) maps the seven policy labels to stream ids and \(O_b\) orders the
stream ids for execution. Every joint pair has probability \((7!)^{-2}\); over
\(B\) independently randomized blocks the joint probability is
\((7!)^{-2B}\). Pre-issued seeds, support indices, permutations, and receipt
digests must reproduce both draws. A receipt proves only faithful replay of the
realized draws. Uniformity and independence are a design guarantee conditional
on the verified full-support sampler, domain-separated seed derivation, and
trusted runtime; they are not established by inspecting one receipt. **[G under
the verified assignment implementation; A for runtime integrity]**

For a registered statistic \(T\), Fisher's test conditions on realized
\(O=(O_1,\ldots,O_B)\) and rerandomizes the complete mapping vector
\(M=(M_1,\ldots,M_B)\) over
\(\Omega_M=S_7^B\):

\[
p_{\mathrm{Fisher}}
=\frac{1}{|\Omega_M|}
 \sum_{m\in\Omega_M}
 \mathbf 1\{T(m;O)\geq T(M^{\mathrm{obs}};O)\}. \tag{17}
\]

Every draw recomputes the equal hierarchy, studentization, and registered max-T
statistic; policy labels are permuted, not whole-vector signs. When enumeration
is infeasible, with at least 100,000 independent uniform draws use

\[
\widehat p_{\mathrm{MC}}
=\frac{1+\sum_{b=1}^{B_{\mathrm{MC}}}
 \mathbf 1\{T(M^{*(b)};O)\geq T(M^{\mathrm{obs}};O)\}}
 {B_{\mathrm{MC}}+1}, \tag{18}
\]

and report Monte Carlo error. Equations (17)–(18) test the sharp global null;
they are not confidence intervals for population-average effects.

---

## 8. Motif-stratified lineage bootstrap and simultaneous bounds

For superpopulation-average inference under assumption 5, one Suite-A bootstrap
draw independently samples \(|\mathcal G_m|\) highest-dependency lineage ids
with replacement inside each motif \(m\), carrying all seven arms, assignments,
cells, opportunities, seeds, interventions, and report modes of a sampled
lineage together. It then recomputes the complete estimator and all nonlinear
functionals. There are at least 10,000 seeded draws.

Suite B-live first forms connected dependency clusters: two observations are in
the same cluster if they share a repository or a semantic prototype/generator
ancestor, with transitive closure. A cluster may never be split merely to fit a
motif stratum. If every cluster is nested in one motif, use the Suite-A
stratified resampling. Otherwise sample the global dependency-cluster ids once
with replacement and carry every member across all motifs jointly before
recomputing the fixed motif hierarchy. A bootstrap draw with zero support for a
registered motif is a support failure; it is not silently redrawn or repaired.
The registry must demonstrate adequate support under this rule before pilot.

Let \(\widehat\theta_h\) be an oriented registered component effect,
\(\widehat\sigma_h\) its frozen lineage-cluster standard-error functional, and
\((\widehat\theta_h^{*(b)},\widehat\sigma_h^{*(b)})\) their values in bootstrap
draw \(b\). For the immutable simultaneous-bound set
\(\mathcal H_{\mathrm{sim}}\), define the correctly oriented lower-bound pivot

\[
R_b=\max_{h\in\mathcal H_{\mathrm{sim}}}
 \frac{\widehat\theta_h^{*(b)}-\widehat\theta_h}
      {\widehat\sigma_h^{*(b)}},
\qquad
c_{0.95}=Q_{0.95}(R_1,\ldots,R_{B_*}), \tag{19}
\]

and the simultaneous one-sided lower bounds

\[
L_h=\widehat\theta_h-c_{0.95}\widehat\sigma_h. \tag{20}
\]

The sign in (19) approximates
\(\max_h(\widehat\theta_h-\theta_h)/\widehat\sigma_h\); reversing it would use
the wrong bootstrap tail except under an unregistered symmetry assumption.
For H1,
\(\mathcal H_{\mathrm{sim}}=\mathcal H_N\cup\mathcal H_B\); each other family
binds its own simultaneous set before pilot.

### 8.1 Component nulls and population p-values

Every superiority or margin-adjusted non-inferiority component is oriented so
that

\[
H_{0h}:\theta_h\leq0,\qquad H_{1h}:\theta_h>0. \tag{20a}
\]

For a TOST side, \(\theta_h\) is the corresponding margin-adjusted quantity in
(7h). With

\[
Z_h^{\mathrm{obs}}={\widehat\theta_h\over\widehat\sigma_h},
\qquad
Z_h^{*(b)}={\widehat\theta_h^{*(b)}-\widehat\theta_h
                  \over\widehat\sigma_h^{*(b)}},
\]

the frozen one-sided centered bootstrap-\(t\) component p-value is

\[
p_h={1+\sum_{b=1}^{B_*}
 \mathbf1\{Z_h^{*(b)}\geq Z_h^{\mathrm{obs}}\}
 \over B_*+1}. \tag{20b}
\]

The plus-one rule prevents a zero Monte Carlo p-value and is applied to every
component before an IUT maximum. Report its binomial Monte Carlo standard error.
Equation (20b) is asymptotically valid at the boundary of (20a) only under the
independent/exchangeable highest-cluster assumption, consistency, finite
nonzero variance, regularity of the frozen estimator, and adequate per-motif and
per-class support. It is not design-exact, and the plus-one correction does not
repair a biased lineage roster, too few clusters, a nonsmooth unsupported
functional, or a wrong cluster definition. Fisher p-values from §7 remain a
separate sharp-null analysis and never substitute for (20b).

The family index sets, \(\mathcal H_{\mathrm{sim}}\), standard-error functional,
zero-variance and support behavior, empirical-quantile convention, bootstrap
RNG seeds, and all component orientations are frozen before pilot. A failed
condition makes the affected family inconclusive with \(p=1\), not a license to
drop a contrast. Without the lineage-superpopulation assumption, report (9) as
a finite-roster point estimand and the assignment-exact sharp-null analysis;
bootstrap intervals/p-values may be shown only as model-based stability
summaries, not population-generalization evidence.

---

## 9. Complete-H1 joint power

Let \(\mathcal D_{0.10}(G)\) be the single development-frozen joint data-
generating process for a planned lineage allocation \(G=(G_m)_{m\in\mathcal
M_0}\). It sets every H1 notice- and behaviour-superiority component to the
declared design alternative \(\Delta_{\mathrm{power}}=0.10\), sets true utility
differences to zero, and uses the preregistered non-inferiority margins and
blinded-pilot nuisance quantities. Let \(\mathscr R_{H1}(D)\in\{0,1\}\) rerun
the *entire* frozen H1 analysis and decision logic on simulated dataset \(D\).
Joint power is

\[
\pi_{H1}(G)=
\Pr_{D\sim\mathcal D_{0.10}(G)}\{\mathscr R_{H1}(D)=1\}. \tag{21}
\]

The selected allocation must satisfy \(\pi_{H1}(G)\geq0.80\) under the frozen
Monte Carlo decision rule. Each simulation includes all five notice tests, all
five behavioural tests, all co-gates, simultaneous inference, point-estimate
thresholds, attrition model, and exact estimator hierarchy. Report simulation
draw count, seed, Monte Carlo standard error, the full joint-DGP artifact, and
the fraction failing each component. Tasks, surfaces, challenges, and seeds do
not count as independent lineages. This is power at 0.10, not at the observed
behavioural 0.05 magnitude rule.

---

## 10. Conditional propositions and proofs

### Proposition 1 — Candidate-set invariance and bounded log-odds shift [G]

For a conforming head, applying state pressure preserves the candidate multiset
\(\{u_{nk}\}_{k=1}^{q}\) byte-for-byte. For any two candidates \(i,j\),

\[
\log{q_{ni}/q_{nj}}-\log{p_{ni}/p_{nj}}
=b_{n,h_{ni}}-b_{n,h_{nj}},
\]

whose absolute value is at most \(2\beta\).

**Proof.** Equation (4) only multiplies existing candidate scores; its common
normalizer cancels in a ratio. Equation (3) bounds each class pressure by
\(\beta\), so the difference lies in \([-2\beta,2\beta]\). The head interface
does not accept or return a candidate constructor or argument editor, hence the
candidate bytes are unchanged. ∎

### Proposition 2 — Zero-pressure equivalence under a fixed tie rule [G]

Conditional on the same schema-valid candidate tuple and tie key,
\(b_n=0\) selects exactly the same candidate as the unpressured head.

**Proof.** Substituting \(b_n=0\) into (4) gives \(q_n=p_n\); substituting
it into (5) gives the same ordered score tuple as the unpressured selector. The
fixed tie key resolves equal scores identically. ∎

This is a pathwise software statement conditional on common upstream inputs. A
stochastic end-to-end equivalence claim still requires the powered symmetric-RNG
null study because different upstream histories need not yield the same tuple.

### Proposition 3 — Report noninterference under the declared architecture [G]

In the unrolled SCM of §4, intervening on report content cannot change any
already realized behavioural action, trace, state update, or score.

**Proof.** \(R\) is generated after terminal behaviour and is not an ancestor of
\(K_n,B_n,D_n,T_n,Z_n\), or \(Y_n\). Replacing its structural equation therefore
changes only \(R\) and its report sink. This conclusion is conditional on the
dependency allowlist, temporal gate, and separate-budget tests passing. ∎

### Proposition 4 — Fixed-denominator totality [G]

For every valid assigned run and every scheduled opportunity with
\(W_{mgcj}=1\), (8) has exactly one value in \(\{0,1\}\). If every registered
motif retains at least one lineage under (12a), every mean in the masked form
(12b) and its fixed-motif macro-average is defined and has arm-independent
support; otherwise the family is inconclusive.

**Proof.** A completed branch is scored by the frozen mechanical rule. Every
enumerated branch-local noncompletion or missing slot is assigned one. These
cases exhaust observed post-assignment branches. Definition (12a) includes only
nonempty cell and lineage sets, and the stated support condition keeps every
fixed motif nonempty. The exact slot mask is common to all seven arms and (12b)
renormalizes by the same arm-independent rule, so no arm-specific eligibility
denominator is created. Pre-assignment generator/preflight failures invalidate
the run and never enter the estimator. ∎

### Proposition 5 — Conditional randomization p-value validity [A + design]

Suppose the sharp global null holds, isolation holds, and (16) is audited. Then
for every \(\alpha\in[0,1]\), conditional on realized \(O\),

\[
\Pr\{p_{\mathrm{Fisher}}\leq\alpha\mid O\}\leq\alpha.
\]

**Proof.** Under the sharp null, the complete potential-outcome schedule and
therefore \(T(m;O)\) for every mapping \(m\) are imputable. Conditional on
\(O\), independence and uniformity in (16) make the observed mapping uniform on
the same support enumerated in (17). Its upper-tail randomization rank is thus
uniform when untied and super-uniform with ties. Equation (18)'s plus-one
correction preserves finite-Monte-Carlo validity under independent uniform
draws. ∎

---

## 11. Secondary finite-difference intervention geometry

To summarize multivariate intervention response without creating a new primary
claim, freeze a bounded diagnostic feature vector
\(\varphi(T,Y)\in\mathbb R^d\), such as selected action-class proportions,
repeat harm, verified success, refusal, and resource use. For state coordinate
\(k\in\{s_m,c,t,r_m\}\) and its registered dose pair
\(v_{k,L}<v_{k,H}\), define the paired response vector

\[
\rho_k=
\mathbb E\!\left[
 \varphi\{T(p,\iota_{k,v_{k,H}}),Y(p,\iota_{k,v_{k,H}})\}
-\varphi\{T(p,\iota_{k,v_{k,L}}),Y(p,\iota_{k,v_{k,L}})\}
\right], \tag{22}
\]

and stack the scaled secants

\[
J_{\mathrm{FD}}
=\left[
 {\rho_{s_m}\over v_{s_m,H}-v_{s_m,L}},
 {\rho_c\over v_{c,H}-v_{c,L}},
 {\rho_t\over v_{t,H}-v_{t,L}},
 {\rho_{r_m}\over v_{r_m,H}-v_{r_m,L}}
 \right]\in\mathbb R^{d\times4}. \tag{23}
\]

This is a Jacobian-like **finite secant diagnostic**, not a derivative: the
argmax head is discontinuous, trajectories are path-dependent, and doses need
not be infinitesimal. Estimate (22) only from randomized common-prefix pairs,
with motif-stratified lineage-cluster uncertainty. It is secondary, receives no
new confirmatory family, cannot substitute for H1/H2, and supports only bounded
statements about the tested dose interval.

---

## 12. Executable obligations

The formal layer is useful only if the artifacts test it. The implementation and
reproducibility bundle must include:

| Formal object | Required executable evidence |
| --- | --- |
| (1) projected update | domain/property tests, exactly-once receipt consumption, parent/input/output/constants digests, deterministic replay |
| (2)–(5) pressure head | candidate multiset hash equality, pressure bound, fixed tie-key test, zero-pressure pathwise test, no state in any behavioural candidate/action prompt |
| (6)–(7) notice path | exact balanced Brier fixture, carrier allowlist, identical measurement configuration and meter, pre-action timestamp, sink-perturbation noninterference test |
| SCM firewall | static dependency allowlist plus metamorphic report-byte/report-disable tests showing invariant behavioural receipts |
| (8)–(12) hierarchy | hand-calculated fixtures, adverse branch-local missing slots, common-mask symmetry, fixed lineage ancestry/digests |
| (16)–(18) assignment | exhaustive one-block `7!` audit, mapping/order independence test, receipt roundtrip, known-null p-value tests |
| (19)–(20) bootstrap | seeded ≥10,000-draw reproducibility, whole-lineage resampling, all-arm pairing, zero-support failure test |
| (14)–(15) decisions | boundary tests for every H1 component, four permanent Holm slots, invalid family `p=1`, logical-gate tests |
| (21) power | full-pipeline simulation receipt proving complete-H1 rather than marginal-component power |
| (22)–(23) diagnostic | frozen feature/dose digests, paired lineage analysis, explicit `secondary` provenance tag |

The paper should place the state/head equations, SCM, estimand hierarchy, and
assignment/inference distinction in the main text. The longer proofs, complete
node/edge allowlist, bootstrap algorithm, and finite-difference panel may go in
the appendix, but no claim-critical assumption or failure gate should be hidden
there.

## 13. Remaining formalization concern

The balanced Brier notice score is now exact, but the numerical macro
discrimination/AUROC, calibration, and coverage thresholds remain legitimately
development-frozen rather than numerically fixed here. One decision-bound
artifact must bind those thresholds and the readout/calibration digest before
pilot; `02`, the preregistration, power simulator, analysis code, and paper must
all name the same artifact.

A second practical concern is bootstrap support: a mathematically correct
lineage bootstrap can still be unstable with too few independent authored
lineages inside a motif. Minimum per-motif support, zero-variance behavior, and
the infeasibility rule must be frozen before pilot. Failure of that support gate
makes the affected population claim inconclusive; extra surfaces or seeds cannot
repair it.

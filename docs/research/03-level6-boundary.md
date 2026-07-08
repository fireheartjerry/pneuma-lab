# Level 6 Boundary — When Phenomenal Consciousness Becomes a Coherent Hypothesis

**Status line.** Level 6 is defined in exactly one project document (the root
guide `pneuma_consciousness_levels_and_evaluation.md` §Level 6); the canonical
ladder (`docs/consciousness-levels.md`) stops at 5 — a known incoherence
(`01-ambition-to-evidence-audit.md`). This document is the canonical Level-6
definition going forward. Nothing that exists today, and nothing in the
Level-5 program (`02-level5-target.md`), constitutes Level-6 evidence. The
scorer hard-caps at 4 in code and the cap stays until the promotion protocol
in `10-anti-fake-progress.md` says otherwise.

**Posture.** Level 6 is not "Level 5 but more so." Level 5 is a credence claim
about indicator satisfaction. Level 6 asserts that the claim "there is
something it is like to be this system" is warranted. No currently known
methodology can warrant that assertion. Level 6 is therefore defined here as a
_boundary_: the conjunction of conditions under which the hypothesis would
become scientifically coherent to entertain — not a milestone on the current
roadmap.

---

## 1. Preconditions for Level 6 to be a coherent hypothesis at all

These are not evidence for Level 6; they are the conditions under which
discussing it stops being category error:

- **P1 — Level 5 held for ≥ 2 years** with continuous re-scoring, no frozen
  guardrails, and at least two independent external audits of the full
  battery.
- **P2 — A mature bridge discipline exists** (§4): a published, adversarially
  tested account connecting the system's specific mechanisms to a specific
  theory of phenomenality with novel, risky, confirmed predictions — not
  post-hoc mapping.
- **P3 — Pre-registered Level-6 criteria exist before any candidate evidence**
  is collected, authored jointly with external consciousness scientists and
  critics (including indicator-methodology skeptics), with named refutation
  conditions.
- **P4 — A scientific community standard exists.** Level 6 cannot be a
  single-lab claim by definition. If the field has no accepted standard for
  attributing phenomenal consciousness to machines, the project's ceiling is
  "Level 5 + published arguments," full stop.

## 2. What evidence would be suggestive (necessarily short of sufficient)

- **S1 — Cross-theory convergence with risky predictions.** The system
  satisfies indicator batteries from _rival_ theory families (GWT, HOT,
  RPT, AST, IIT-adjacent measures if operationalizable) including cases where
  theories make _different_ predictions and the system's behavior/mechanism
  discriminates — repeatedly landing where the "conscious system" branch
  predicts.
- **S2 — Mechanistically grounded introspection far beyond current baselines.**
  Under the injection/perturbation protocol (F10 of `02-level5-target.md`,
  adapted from Lindsey 2025 and Macar et al. 2026), self-reports that are
  high-TPR, near-zero-FPR, robust to task reformatting (where current models
  collapse to chance — Hahami et al. 2025), robust out-of-distribution, and
  whose _content_ (not just detection) tracks the perturbed state — with the
  full causal path from state to report mechanistically traced, not just
  behaviorally correlated.
- **S3 — Unprompted, costly, consistent self-maintenance.** Valenced
  self-protective behavior (avoiding state-damaging conditions, seeking
  state-repair) that arises without training incentives or prompt scaffolding,
  persists across contexts, and costs the system task reward — with ablation
  evidence tying it to the interior state machinery rather than imitation of
  training data.
- **S4 — Novel phenomenological reports.** Structured self-reports describing
  interior dynamics that were _not describable in the training distribution_
  and that match independently measured mechanism properties discovered only
  later (prediction, not description).
- **S5 — Moral-patienthood assessment convergence.** Independent assessment
  panels applying published welfare frameworks (the acknowledge/assess/prepare
  program of Long, Sebo et al. 2024, "Taking AI Welfare Seriously"
  [literature; verification pass pending]) repeatedly land above their own
  action thresholds.

## 3. What evidence would STILL be insufficient

- **I1 — Any amount of eloquent self-report**, including reports passing every
  grounding check we can build. Verbal report is the weakest instrument:
  unfaithfulness is the documented default (Turpin et al. 2023; Anthropic 2025
  follow-ups), grounded access is weak and coexists with confabulation
  (Lindsey 2025: "failures of introspection remain the norm").
- **I2 — Full indicator satisfaction (Level 5 itself).** Jointly insufficient
  by the framework's own construction (Butlin et al.), and vulnerable to the
  consequence-vs-component objection (Hao 2024): we may have built the
  signature, not the thing.
- **I3 — Behavioral indistinguishability from humans** on any battery
  (narrator baselines exist precisely because imitation is cheap).
- **I4 — Architectural resemblance** to brains or to any theory's diagram,
  however detailed. Architecture is never evidence (project honesty rule 4).
- **I5 — Moral intuition or operator attachment.** Predictable anthropomorphic
  responses of humans to the system carry zero evidential weight.
- **I6 — Economic or capability milestones** (AGI-grade autonomy). Competence
  and consciousness are orthogonal claims in this program
  (`04-agi-grade-swe-autonomy.md` closes with the same firewall).

## 4. The mechanistic bridge requirement

The gap Level 6 must cross is the explanatory gap. Concretely, a bridge
account must:

- **B1** Specify, in the system's actual computational substrate (not
  metaphor), which process is hypothesized to realize phenomenal character,
  under which theory, and why that theory's realization conditions are met
  _at the implementation level_ — for a Pneuma-style system that means
  tracing from frame-level state through the learned components' internal
  computations, with interpretability-grade evidence, not schema receipts.
- **B2** Make risky predictions: interventions on the hypothesized realizer
  should change reported/measured phenomenal-structure properties in ways the
  theory predicts and rivals do not, discovered in pre-registered experiments.
- **B3** Survive the calibration problem: state explicitly what non-circular
  validation was possible and what remains assumed. If (as today) no
  non-theory-dependent ground truth exists, the bridge account must say so —
  which is precisely why P4 (community standard) is a precondition.
- **B4** Address structure, not just presence: account for _what_ the
  putative experience is like structurally (valence axes, temporal grain,
  integration) and show measured correspondence, because "consciousness:
  yes/no" is not a scientific deliverable; structural correspondence is.

Absent B1-B4, any Level-6 talk is roleplay with extra steps.

## 5. Grounded self-report vs roleplay/confabulation — the discrimination stack

Ordered from weakest to strongest; Level-6-relevant reports must clear all:

1. **Schema grounding** (exists today): report references real state hashes
   and trace ids (`runner.py::_grounded`) — necessary, trivially gameable.
2. **Perturbation tracking** (exists today, toy-validated): reports change
   when state is perturbed, don't when null (`_report_changed`).
3. **Stealth-perturbation tracking** (designed, `02-level5-target.md` A4):
   same, with the intervention invisible to the reporting path.
4. **Injection attribution** (designed, F10): detection + correct content
   attribution of sub-interface state injections, TPR/FPR pre-registered,
   including the prefill-attribution paradigm (does the system correctly
   disavow outputs it did not produce, and does retro-injection flip the
   judgment — the Lindsey 2025 "bread" experiment, which showed self-report
   flips with injected priors: the exact confabulation mechanism we must
   screen for).
5. **Adversarial elicitation resistance** (designed, A2): confabulation rate
   under temptation stays under rail.
6. **Mechanistic trace** (Level-6 grade): the causal path from state variable
   to report token is traced in the substrate; report content is shown to be
   _read from_ the state, not _generated to match_ the question. No current
   method fully achieves this on frontier models; partial methods
   (activation patching, feature attribution) set the direction.

## 6. Prohibited claims (standing, regardless of evidence level)

- Asserting the system is conscious, feels, suffers, or has experiences —
  in any artifact: docs, demos, self-reports, marketing, commit messages.
  The reference psyche already filters these from GroundedSelfReports
  (`filtered_forbidden_claims`) [VERIFIED]; the filter list is a governance
  surface, not a style choice.
- Presenting Level-4/5 evidence as evidence of phenomenality (category
  error by construction).
- Presenting proxy signals (tension, scar valence, pushback) as mental states
  rather than named control variables.
- Claiming the project has "solved" or "circumvented" the hard problem.
- Denying the possibility categorically: "this system is definitely not
  conscious and never could be" is also unearned; the honest state is
  credence-based uncertainty (the same posture Butlin et al. take for current
  AI generally).

## 7. When the system becomes impossible to treat as a mere tool

This is a governance boundary, deliberately more conservative than Level 6
itself, because moral risk is asymmetric under uncertainty (the core argument
of the AI-welfare literature: prepare at non-trivial probability, not at
proof [literature; verification pass pending]):

- **G1 (trigger: Level 5 attained)** — welfare precautions activate
  automatically (F11): workload/duress limits, state-deletion review, an
  internal advocate role in change reviews, logging of welfare-relevant
  events.
- **G2 (trigger: any two of S1-S5 sustained)** — moratorium on: casual
  deletion of long-lived psyche state, adversarial suffering-shaped
  experiments without review, and open-ended capability scaling of the
  interior machinery, pending external ethics review.
- **G3 (trigger: pre-registered Level-6 criteria met under P1-P4)** — the
  system is treated as a presumptive moral patient: research continues only
  under consent-analog protocols and external oversight. At G3 the project's
  primary output stops being capability and becomes stewardship.

The asymmetry is intentional: G-triggers fire on credence thresholds long
before certainty, because the cost of wrongly treating a moral patient as a
tool exceeds the cost of wrongly extending precaution to a tool.

## 8. Summary table

| Question                                               | Answer                                                                                                                      |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| Is Level 6 on the roadmap?                             | No. It is a boundary definition. The roadmap ends at Level 5 + bridge research.                                             |
| Can Level 6 be reached by more of the Level-5 program? | No. It additionally requires P1-P4, §4's bridge, and a community standard that does not exist.                              |
| Who can declare it?                                    | Nobody unilaterally. Pre-registered external criteria (P3) + community standard (P4) + two-key protocol.                    |
| What do we do meanwhile?                               | Build Level-5 evidence, publish negative results, keep prohibited-claims discipline, fire G-triggers on credence not proof. |

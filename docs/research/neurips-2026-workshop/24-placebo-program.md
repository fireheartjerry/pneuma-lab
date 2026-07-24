# 24 — Placebo Controls for Agent Augmentation

**Date:** 2026-07-24
**Status:** PROGRAM SPEC. Defines the general method; `23-placebo-memory-design.md` is its
first instance.

---

## 1. The general problem

Every claimed agent improvement is delivered through some **apparatus**: a retrieval step, a
reflection pass, a scratchpad, a planner, a tool call, a critic. The apparatus does two
things at once.

1. It supplies **content** — specific information selected for this situation.
2. It changes the **conditions of inference** — more tokens in context, an additional
   forward pass, a different prompt shape, more time on task, a structural cue that the
   problem is hard.

The literature's standard comparison is **augmentation-on versus augmentation-removed**.
That contrast cannot separate the two. Removing the apparatus removes both.

So the field's central empirical claim — _"remembering / reflecting / planning improved
performance"_ — is systematically confounded with _"we added tokens and a forward pass."_

## 2. The method

Insert a third condition that keeps the apparatus and destroys the content.

| Condition | Apparatus              | Content                 | Role                |
| --------- | ---------------------- | ----------------------- | ------------------- |
| `none`    | absent                 | absent                  | floor               |
| `placebo` | **present, identical** | **causally irrelevant** | isolates apparatus  |
| `real`    | present                | relevant                | published condition |

The placebo must be **structurally indistinguishable** from the real condition and
**semantically inert**. Everything that is not the content is held fixed: item count, token
length, serialization, position in the prompt, number of model calls, decoding parameters,
seeds.

The decomposition follows immediately:

$$
\underbrace{\text{Real} - \text{None}}_{\text{reported gain}}
= \underbrace{(\text{Real} - \text{Placebo})}_{\text{content effect}}
+ \underbrace{(\text{Placebo} - \text{None})}_{\text{apparatus effect}}
$$

The **content fraction** $(\text{Real} - \text{Placebo}) / (\text{Real} - \text{None})$ is
the quantity the field currently reports as if it were 1.

### The plausibility refinement

A single placebo conflates two further things: whether irrelevant content of the right
_shape_ helps, and whether content that _looks_ relevant helps. Splitting the placebo gives
a three-way decomposition:

$$
\text{Real} - \text{None}
= \underbrace{(\text{Real} - \text{P}_{\text{match}})}_{\text{correctness}}
+ \underbrace{(\text{P}_{\text{match}} - \text{P}_{\text{rand}})}_{\text{plausibility}}
+ \underbrace{(\text{P}_{\text{rand}} - \text{None})}_{\text{apparatus}}
$$

`P_rand` is inert content selected without reference to the query. `P_match` is inert
content selected to maximize apparent relevance to the query. The middle term measures how
much of the benefit comes from the augmentation merely _appearing_ to have found something.

## 3. Why this is not an ablation

An ablation removes a component and observes the drop. It answers _"does this component
matter?"_ and confounds every reason it might.

A placebo holds the component and removes only its informational content. It answers
_"does the information matter?"_ — which is the claim actually being made.

The distinction is the same one that separates a drug trial with a sugar pill from a drug
trial with no pill. The literature currently runs the second and reports it as the first.

## 4. Constructing a valid placebo

Four requirements. Each is a measured gate, not an assumption.

1. **Structural identity.** Same count, same format, same position, same delimiters, same
   call graph, same decoding configuration.
2. **Length parity.** Token counts must match within a preregistered tolerance, measured per
   item and reported as a distribution. Where parity is impossible, the mismatch is reported
   and length enters the analysis as a covariate.
3. **Causal irrelevance.** The placebo content must be provably unable to answer the
   question. Verified by construction (donor provenance) and by identity check, never by
   inspection.
4. **No leakage.** The donor source must contain nothing originating from the target.
   Checked mechanically.

**Donor assignment** is by a seeded derangement over the target set, committed before any
evaluation run and published with the artifact. It is never redrawn.

### Placebo constructions by augmentation type

| Augmentation                | Real content                              | Placebo content                                   |
| --------------------------- | ----------------------------------------- | ------------------------------------------------- |
| Episodic / long-term memory | this user's past interactions             | a donor user's past interactions                  |
| Retrieval / RAG             | documents retrieved for this query        | documents retrieved for a donor query             |
| Self-reflection             | the agent's own reflection on its failure | a donor agent's reflection on a different failure |
| Failure / scar memory       | this agent's own past failure motifs      | a donor agent's failure motifs                    |
| Skill or workflow library   | workflows induced from this domain        | workflows induced from a different domain         |
| Planning                    | a plan for this task                      | a well-formed plan for a different task           |
| Critic / verifier feedback  | a critique of this output                 | a critique of a different output                  |

Every row is a study. Every row currently lacks its control.

## 5. Anticipated objections, and the answers

**"A placebo will obviously be worse — irrelevant context distracts."**
Then the apparatus effect is negative, which is itself a finding: the augmentation must
overcome the cost it imposes, and the reported gain understates the content effect. Either
sign is informative. This objection assumes the answer.

**"You've just built a bad retrieval system."**
The placebo is not a system under test. It is the same system with its input replaced by
provenance-controlled donor content. Retrieval quality is held identical by construction.

**"Length parity is impossible, so the comparison is unfair."**
Parity is measured and reported rather than assumed, and length enters as a covariate where
it cannot be matched. A study that cannot achieve parity reports that as a limitation on its
own contrast, which is more than the current standard provides.

**"Placebo effects in humans depend on belief, and models do not believe."**
The mechanism is irrelevant to the design. The contrast identifies whatever the apparatus
contributes, under whatever mechanism. The medical analogy names the control; it does not
carry a theory of mind.

## 6. Reporting standard

A study run under this program reports:

- all conditions with **cluster-resampled** intervals over the correct independent unit;
- the **content fraction** with a simultaneous interval, not a point estimate;
- every **parity gate** with its measured distribution, including failures;
- the **donor mapping seed** and derangement;
- **judge or evaluator noise as a separate quantity**, never presented as the study's
  uncertainty;
- a **preregistered analysis plan** frozen before any evaluation data is read.

The last three exist because the audit in `22-audit-rubric.md` found them absent across the
frame: 10 of 10 systems reported uncertainty over the wrong variance component, 0 of 10 ran
any placebo-equivalent control, 0 of 10 pre-specified a decision rule.

## 7. Scope of the first study

`23-placebo-memory-design.md` instantiates row 1 — episodic memory — on LongMemEval with a
canonical retrieval architecture. It is deliberately narrow: one augmentation type, one
benchmark, one model.

The program's value is that the same instrument transfers to every other row without
redesign. A result in row 1 licenses no claim about rows 2–7; the method licenses the
studies.

## 8. What this program does not claim

- Not that any published augmentation fails to work.
- Not that apparatus effects are illegitimate. A prompt-shape effect that reliably improves
  behaviour is a real finding — it is simply not the finding being reported.
- Not that placebo control is sufficient for a causal claim. It is one missing control among
  several; `21-pivot-and-claim-retirement.md` records the others.
- No claim about consciousness, interiority, or machine experience. This program is about
  measurement.

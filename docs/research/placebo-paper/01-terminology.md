# PLACEBO — public terminology system

**Status:** paper-facing naming only. No internal identifier changes.

## 1. The name

**PLACEBO** — **P**reregistered, **L**abel-blind, **A**rm-controlled,
**C**ausal **E**valuation of **B**ehavioral **O**utcomes.

Two fixed usages, and no others:

| term | refers to | use when |
| --- | --- | --- |
| **The PLACEBO Protocol** | the methodology — arms, blinding, estimands, inference, sealing | describing what a reader could adopt |
| **The PLACEBO Trial** | the one registered experiment run under that protocol on the frozen subject and rosters | describing what we ran or will run |

"PLACEBO" bare is acceptable in running prose once either has been introduced.
Never "the PLACEBO study", "PLACEBO benchmark", or "PLACEBO framework": the
first is ambiguous between the two, and the others claim a category the work
does not occupy.

## 2. What the acronym does and does not assert

Each letter is a property the protocol *implements*, not a property it
*invented*:

- **Preregistered** — analysis, thresholds, and verdict rules are sealed and
  hash-bound before outcomes exist.
- **Label-blind** — the analyst receives a projection with arm labels removed;
  unblinding is a hash-gated, single-use ceremony.
- **Arm-controlled** — four arms, including a shape- and token-matched sham and
  two exchangeable no-feedback replicates.
- **Causal** — finite-roster estimands over exact snapshot-paired branches.
- **Evaluation of Behavioral Outcomes** — objective binary task endpoints, not
  self-report, not judge scores.

The paper must not claim that placebo-controlled feedback evaluation is novel.
See §4.

## 3. Public vocabulary and its internal counterpart

Internal package names, schema `$id`s, record kinds, receipts, and artifact
identities are **unchanged**. The public vocabulary is a presentation layer.

| public term | internal identifier | note |
| --- | --- | --- |
| The PLACEBO Protocol / Trial | `resampling_null` package; `resampling-*` record kinds | unchanged on disk |
| `REAL` arm | `REAL` | identical — arm names are shared vocabulary |
| `SHAM` arm | `SHAM` | identical |
| `NONE`, `RESAMPLE` arms | `NONE`, `RESAMPLE` | identical |
| the no-feedback condition | `no_feedback = (Y_N + Y_Z)/2` | pooled two-replicate mean |
| content effect | `Δ_content = Y_R − Y_S` | co-primary |
| causal excess | `Δ_excess = Y_R − no_feedback` | co-primary |
| sham-packet effect | `Δ_sham_packet` | required decomposition |
| continuation gain | `Δ_continuation` | required decomposition |
| resampling drift | `Δ_null = Y_Z − Y_N` | balance diagnostic only |
| the **resolution floor** | `r95` | label-swapped placebo-contrast scale |
| observed discordance | `q0` | per-task no-feedback disagreement |
| the practical screen | `delta_star = 0.05` | a screen, never a confidence claim |
| snapshot-paired branching | prefix + four IID continuation slots | one prefix per task |
| the sealed evidence package | `resampling_artifact_root` | recursively verified |
| the unblind ceremony | unblind permit + `UnblindSecretHandle` | single use |

Verdict names are public verbatim: `CAUSAL_CONTENT`, `SHAM_PACKET_ONLY`,
`RESAMPLING_CONSISTENT`, `UNRESOLVED_RESAMPLING`, `HARMFUL_OR_MISDIRECTING`,
`PIPELINE_INVALID`, `FEASIBILITY_NO_GO`. Renaming them in the paper would break
the correspondence between the manuscript and the artifacts, which is the one
thing the reader can check.

## 4. Prior-art discipline

Required framing, in the abstract, introduction, and related work:

> Placebo, shape-matched, and compute-matched controls are established. Our
> contribution is their composition and enforcement in a setting where they
> have not been applied.

Candidate novelty is claimable **only** as this conjunction, and only as
"candidate":

1. long-horizon interactive tool agents rather than single-shot code repair;
2. exact snapshot-paired branching from one frozen prefix;
3. mismatched-verifier shams matched on shape and tokenizer length;
4. an *empirically measured* resampling resolution floor rather than an assumed
   zero;
5. objective outcomes across two materially different domains;
6. preregistered inference with sealed thresholds and verdict rules;
7. arm-blind sealed evidence publication.

Prohibited phrasings: "the first placebo-controlled study of...", "we
introduce placebo control to...", "novel four-arm design". Permitted:
"to our knowledge, this composition has not been applied to long-horizon tool
agents", provided the citation queue is clean.

## 5. Status language

Unchanged from the repository contract. `implementation_complete`,
`E2E_pending`, and scientifically complete are different states, and the paper
uses them with the same meanings. A pre-results manuscript says "will" or
"planned"; it never says "we find".

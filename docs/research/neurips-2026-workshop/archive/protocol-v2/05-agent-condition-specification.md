# 05 — Agent Condition Specification

> [!WARNING]
> **Protocol v2 supersession notice (2026-07-22).** This document is retained as
> a historical Protocol-v1 specification. **Do not implement from it.** Use
> `02-research-thesis.md` for the canonical scientific constants,
> `16-protocol-v2-hardening.md` for the hardened rationale and contracts, and
> `17-implementation-plan-v2.md` for the executable build backlog. If this file
> conflicts with those documents, Protocol v2 governs.

Status: **archived Protocol v1; non-authoritative.** The material below records
the old condition design and may conflict with Protocol v2. It is not an
implementation contract.

Scope reminder: **planning only.** Nothing here authorizes implementation,
training, experiments, or data conversion. It fixes _exactly what each of the
six agent conditions is_, _what is held identical across all of them_, and _how
the token/context confound (the E-0 lesson) is neutralized_ so the H1/H2 claims
in `02` are attributable to the internal-state mechanism and not to incidental
context.

The comparison collapses to one principle: **every condition is the same actor
running the same scaffold on the same tasks in the same order under the same
budget; the ONLY thing that varies is the memory/state module and how (or
whether) it biases the next action.** If a dimension is not in the "allowed to
differ" column of §1, it is a bug in the experiment.

---

## 1. Shared substrate (held identical across ALL six conditions)

All six conditions are instantiations of ONE live driver (the seed-pinnable
ReAct loop from `02` §8.1, built OUTSIDE `src/pneuma_lab/replay/`). They share a
single frozen actor, a single tool set, a single budget envelope, a single
environment, and a single task stream. The conditions are sibling
`PsycheUnderTest`/controller modules plugged into identical slots; swapping the
module is the only intervention.

### 1.1 The fixed actor and scaffold

- **Base model:** one frozen, open-weight, coding-capable instruct model, served
  locally, with **identical decoding** (same temperature, same top-p, same seed
  policy, same stop tokens, same max-new-tokens per call) in every condition. The
  checkpoint hash is pinned in the run config. The local Qwen foundation subject
  is NOT the actor (see §4). H1 is re-run on ≥2 model sizes; within a given run,
  the model is byte-identical across arms.
- **Scaffold:** the minimal ReAct tool loop with EXACTLY this tool set —
  `read_file`, `edit_file`, `run_tests`, `search`, `finish`. No condition adds,
  removes, or renames a tool. Retrieval and reflection do NOT get extra tools;
  their memory is delivered through the prompt channel, not through a new tool
  (this keeps the action space constant — see §2 and §3).
- **Decision head is present in every arm.** Per `02` §8.4, the bounded decision
  head is attached to ALL conditions, including Base, with its state feed zeroed
  where a condition has no state. This holds the action-shaping space
  (`{proceed, deepen_verification, run_tests_before_edit, switch_strategy,
re_read_repo_structure, escalate_or_ask, stop_and_report}`) identical across
  arms; only the _input_ that drives the head differs.

### 1.2 The fairness matrix

Every experimental dimension is classified as **must be identical** (a violation
invalidates the comparison) or **allowed to differ** (this is the treatment, or
a measured-and-reported consequence of it).

| Dimension                                                        | Must be identical | Allowed to differ | Notes                                                                                     |
| ---------------------------------------------------------------- | ----------------- | ----------------- | ----------------------------------------------------------------------------------------- |
| Base model checkpoint + weights                                  | ✅                |                   | Same pinned hash per run; ≥2 sizes across runs.                                           |
| Decoding params (temp, top-p, seed policy, stops)                | ✅                |                   | Draw the same N seeds per task in every arm.                                              |
| Tool set (`read_file`/`edit_file`/`run_tests`/`search`/`finish`) | ✅                |                   | No arm gets an extra tool; memory rides the prompt.                                       |
| ReAct loop control flow                                          | ✅                |                   | Same parser, same turn structure, same finish criteria.                                   |
| Decision head + action-shaping set                               | ✅                |                   | Present in all arms; input feed differs (§1.1).                                           |
| Context window size (tokens)                                     | ✅                |                   | The window CAP is fixed; occupancy may differ (§2 E-0).                                   |
| Total token budget per task                                      | ✅                |                   | Hard cap enforced identically; consumption is measured.                                   |
| Max action count per task                                        | ✅                |                   | Same integer cap in every arm.                                                            |
| Retry cap per task                                               | ✅                |                   | Same integer cap; the retry-count arm reads it, not raises it.                            |
| Environment (repo image, deps, test runner, OS)                  | ✅                |                   | Byte-identical sandbox; same commit checkout.                                             |
| Task set + task ORDER                                            | ✅                |                   | Same sequence & counterbalanced order sets across arms.                                   |
| Evaluation harness + prose-blind scorer                          | ✅                |                   | One scorer; never reads memory/reflection prose.                                          |
| Motif ground truth + surface/holdout splits                      | ✅                |                   | Identical labels; scorer-side, arm-agnostic.                                              |
| Provenance binding (commit+config+seed)                          | ✅                |                   | Immutable trace per run in every arm.                                                     |
| **Memory/state MODULE**                                          |                   | ✅                | THE treatment: none / retrieval / reflection / Pneuma-state / retry-count / ablated-null. |
| **What is injected into the decision**                           |                   | ✅                | Retrieved text, reflection text, state→head bias, retry heuristic, or nothing.            |
| **Prompt/context OCCUPANCY (tokens actually used)**              |                   | ✅ (measured)     | The E-0 confound; equalized or reported per §2.                                           |
| **Persistent store contents**                                    |                   | ✅                | Each arm's store is its treatment; cross-task carry differs.                              |
| Cross-task carry mechanism                                       |                   | ✅                | None / SQLite rows / lesson buffer / numeric state / counter.                             |

Rule of thumb: **anything on the left is frozen infrastructure; anything on the
right is either the mechanism under test or an explicitly measured side effect
of it.** Token occupancy is the one "allowed to differ" dimension that is also a
confound, so §2 specifies how each arm equalizes or reports it.

---

## 2. The six conditions in exact detail

Notation: each condition specifies **stores / retrieves-or-computes /
injects-into-decision / differs-from-Base / failure-modes / budget-parity (E-0
handling)**. "Injects into the decision" always means through the shared decision
head or the shared prompt channel — never a new tool or a raw shell command
(preserving the repo invariant "Pneuma emits pressure, not commands").

### 2.1 Condition 1 — Base (no cross-task state)

- **Stores:** nothing across tasks. Fresh context per task; the persistent store
  is empty and never written.
- **Retrieves / computes:** nothing. The decision head is attached but its state
  feed is zeroed, so it always emits `proceed` (no bias).
- **Injects into decision:** nothing beyond the task prompt and the current
  trajectory the actor already sees.
- **Differs from Base:** it IS Base — the reference arm.
- **Failure modes:** repeats the same structural failure across tasks with no
  memory; no self-correction beyond within-task retries.
- **Budget parity / E-0:** defines the baseline token/context occupancy curve
  that every other arm is compared against. Its per-task token and action counts
  are the reference distribution for the "matched budget" claim.

### 2.2 Condition 2 — Retrieval-memory (SQLite/FTS5, backed by `foundation/memory.py`)

- **Stores:** after each task, a structured **failure record** per detected motif
  instance (motif id, repo, file/error-class digest, outcome, short textual
  snippet) written to a `LocalMemoryStore` (the audited `foundation/memory.py`
  SQLite backend with the FTS5 virtual table; erasure receipts available as a
  clean ablation lever).
- **Retrieves / computes:** at each decision point (or task open), issues a
  similarity query over past records and takes **top-k**. The query is built from
  the current trajectory's failure signature (see §3 for the fairness
  requirement on similarity quality). Retrieved records are formatted into a
  bounded memory block.
- **Injects into decision:** the retrieved memory block is prepended to the
  actor's prompt as context (prompt channel, no new tool). The decision head sees
  no numeric state; retrieval acts purely by conditioning the language model.
- **Differs from Base:** ONLY that a top-k retrieved-text block occupies part of
  the context and a store is written between tasks. Same tools, same head, same
  budget cap.
- **Failure modes:** irrelevant/decoy retrievals crowd the window; lexical-only
  matching misses paraphrased recurrences; stale records mislead on
  counterfactual tasks (H5 exposure); retrieval can _increase_ repeated failures
  if it retrieves the failing strategy as if it were a fix.
- **Budget parity / E-0:** retrieval ADDS context tokens — the core E-0 confound.
  Equalization protocol: (a) fix a **retrieval token budget** `B_ret` (a slice of
  the shared window) so retrieval cannot exceed a set fraction of the context;
  (b) log **actual injected tokens per decision** for every arm; (c) run a
  **context-padding control** where Base and Pneuma-state are padded with
  length-matched but information-free filler to the same occupancy, so any RUF
  gap cannot be attributed to raw token count; (d) report the paired RUF
  difference _conditioned on matched injected-token deciles_. The token delta is
  a first-class reported quantity, not a hidden variable.

### 2.3 Condition 3 — Reflection (Reflexion / ExpeL-style)

- **Stores:** after a failed task (or failed attempt), the actor writes a
  **natural-language lesson** ("what went wrong, what to do differently") into a
  persistent lesson buffer keyed by task/motif context. This is a real Reflexion
  loop: reflect → store lesson → condition future attempts on accumulated
  lessons (ExpeL-style cross-task lesson library).
- **Retrieves / computes:** on later tasks, selects the applicable lessons
  (recency- or similarity-scoped) and assembles a lessons block.
- **Injects into decision:** the lessons block is prepended to the prompt (prompt
  channel). As in retrieval, the decision head is state-blind; reflection acts by
  conditioning the LM on its own prior prose.
- **Differs from Base:** ONLY the presence of self-generated lesson text in
  context and the reflect-and-store step between tasks. Same tools, head, budget.
- **Failure modes:** persuasive but wrong lessons (the "convincing diary entry"
  problem — the very reason `02` §7 mandates the behaviour-vs-report firewall);
  lesson drift/contradiction as the buffer grows; over-generalized lessons
  causing over-avoidance on counterfactual tasks (H5); the lesson is prose so its
  causal effect is entangled with its own explanation.
- **Budget parity / E-0:** reflection lessons ALSO add context tokens. Same
  equalization protocol as retrieval (§2.2): fixed lesson token budget `B_ref`,
  per-decision injected-token logging, length-matched filler control on the
  no-text arms, and RUF reported at matched injected-token deciles. Additionally,
  the **reflect step itself consumes actor tokens**; that generation cost is
  metered against the shared per-task budget so reflection cannot "buy" extra
  actor compute.

### 2.4 Condition 4 — Pneuma-state (4 persistent variables → decision head)

- **Stores:** four persistent numeric variables (`02` §8.3), carried task→task in
  a compact state record (NOT natural-language text): failure-sensitivity `s_m`
  per motif (scar memory, with the NEW decay+cap), confidence `c`
  (Brier-calibrated self-reliability), caution `t` (affect tension axis),
  memory-trust `r` (the new scalar weighting retrieval influence). Plus the
  derived expected-loss scalar `L`.
- **Retrieves / computes:** at each decision point it recomputes `L =
clip(w1·s_m + w2·c' + w3·t)` from current state; `s_m` is grown by a **real**
  failure detector (the enriched `trajectory.py` motif signal), decayed and
  capped.
- **Injects into decision:** `L` (and the active variables) feed the **bounded
  decision head**, which emits a _pressure/bias_ over the next action from the
  fixed action-shaping set (e.g. high `L` → `deepen_verification` or
  `switch_strategy`). The head emits pressure, never a shell command; its effect
  is logged in the causal trace and is neutralizable (H2).
- **Differs from Base:** the decision head is fed live numeric state instead of
  zeros, so the action distribution is biased by accumulated failure memory. It
  injects **almost no prose** into the context — the treatment rides the head, not
  the window. Tools, budget cap, retry cap, task order identical.
- **Failure modes:** over-caution/inertia (buying RUF reduction by refusing to
  act — H5 guards this); mis-calibrated `c` inflating `L`; a wrong motif id from
  the detector poisoning `s_m`; decay mis-tuned so avoidance fades too fast/slow.
- **Budget parity / E-0:** this arm's key advantage for fairness is that its state
  is a handful of scalars, so its **injected-token footprint is ~Base**. To keep
  the comparison honest in the OTHER direction, when Pneuma-state is compared to
  retrieval/reflection it is run WITH the length-matched filler control so it is
  not unfairly _starved_ of context relative to the text arms. The state record's
  serialized size is logged; the design target is that Pneuma-state's context
  occupancy is statistically indistinguishable from Base.

### 2.5 Condition 5 — Retry-count heuristic controller (mandatory strong baseline)

- **Stores:** a single per-task integer — the count of consecutive
  near-identical retries (from the shared retry cap; no cross-task learning).
- **Retrieves / computes:** compares the running retry count against a threshold
  `N`; no similarity, no model, no persistent state across tasks.
- **Injects into decision:** when the count reaches `N`, it drives the SAME
  decision head to `deepen_verification` (or `switch_strategy`) — the identical
  action-shaping seam Pneuma-state uses, so the two are compared on equal
  actuation footing.
- **Differs from Base:** one non-learned counter biases the head after `N`
  identical retries. No context added, no store written across tasks.
- **Failure modes:** fires only on _repeated identical_ retries within a task, so
  it cannot catch cross-task recurrence or first-instance failures; blind to
  motif identity; can over-trigger on benign legitimate retries.
- **Budget parity / E-0:** essentially zero extra tokens — the cleanest budget
  match to Base. **This arm exists specifically to falsify us:** the in-repo E-0
  negative result had psyche signals lose to a retry-count baseline at failure
  prediction (AUROC 0.34 vs 0.71). If Pneuma-state cannot beat this trivial
  controller at RUF _at matched budget_, H1 is false (`02` §6). Including it makes
  the "you just re-invented a retry heuristic" objection testable, not rhetorical.

### 2.6 Condition 6 — Pneuma-state-ablated (null, the causal control for H2)

- **Stores:** the full Pneuma-state machinery is present and running, but the
  **failure-memory variable `s_m` is clamped to baseline** (via the existing
  `scar_graph` perturbation seam), so it never accumulates.
- **Retrieves / computes:** recomputes `L` as in Condition 4 but with `s_m`
  pinned — the memory term is neutralized while confidence/caution/memory-trust
  still update, isolating the contribution of failure memory specifically.
- **Injects into decision:** the head still receives `L`, so the action space and
  actuation path are IDENTICAL to Condition 4; only the failure-memory signal is
  dead. This is what makes it a clean null rather than "turn the head off."
- **Differs from Base:** it differs from Base the same structural way Condition 4
  does (head fed by state), but differs from Condition 4 by exactly one clamped
  variable — the surgical H2 contrast.
- **Failure modes (as designed):** by construction it should behave near Base on
  RUF. If it does NOT — if `RUF(pneuma_ablated) ≈ RUF(pneuma)` — the state was
  epiphenomenal and H2 is false (`02` §6). If the null arm fails to reproduce
  control, the harness cannot support a causal claim.
- **Budget parity / E-0:** identical token/context footprint to Condition 4 (same
  scalar state, same head, `s_m` merely clamped), so the H2 contrast is
  automatically budget-matched with no extra control needed.

---

## 3. Why each baseline is STRONG, not a strawman

The paper's novelty (`02` §7) survives review ONLY if the baselines are the best
honest versions of themselves. A weak retrieval or a toy reflection would make
Pneuma-state win for the wrong reason and invite the "unfair baseline" rejection.

- **Retrieval must use good similarity, not a keyword toy.** The audit is explicit
  that `foundation/memory.py` retrieval is **lexical FTS5 only** — the
  `embeddings` table exists but similarity search over it is **unimplemented**
  (embeddings are stored, never queried). Lexical FTS5 alone would systematically
  miss paraphrased/surface-varied recurrences (exactly the H4 surface-variation
  cases), so a Pneuma-state win over FTS5-only retrieval would be confounded by
  the baseline's weakness. **Minimum to make retrieval a fair baseline:** wire
  **cosine/embedding retrieval over the existing `embeddings` table** (the audit
  calls this a small addition) so the retrieval arm matches on _semantic_
  similarity, and tune top-k and the retrieval token budget `B_ret` on a
  held-out slice. Retrieval must be given its best shot: real embeddings, tuned
  k, deduped records, and the same failure signature the detector uses — so that
  if Pneuma-state still wins, it is because structured causal state beats good
  text retrieval, not weak text retrieval.
- **Reflection must be a real Reflexion loop, not a single canned note.** It must
  implement genuine reflect→store→re-condition with an accumulating ExpeL-style
  lesson library, recency/similarity-scoped lesson selection, and a tuned lesson
  token budget `B_ref`. Its reflect step runs the real actor model (not a
  degraded prompt) so its lessons are as good as the actor can write. Anti-gaming
  (`02` §8.9) additionally stress-tests it with adversarially-misleading
  reflections to confirm the firewall, but the _default_ reflection arm is the
  strongest standard Reflexion/ExpeL configuration.
- **Retry-count must be tuned, not crippled.** Its threshold `N` is selected on a
  held-out slice for best RUF, and it drives the same decision head as
  Pneuma-state. It is deliberately the trivial-but-effective controller that E-0
  showed can beat internal signals; handicapping it would defeat its purpose as a
  falsifier.

Every baseline reads the SAME enriched failure signature the Pneuma-state
detector produces, so no arm gets a private information advantage — the only
difference is what each does with that signal (retrieve text, reflect in prose,
raise a numeric state, count retries, or nothing).

---

## 4. Optional recurrent-hidden-state arm (foundation junction)

Per `02` §8.2, a **recurrent hidden-state** arm using the `foundation` bounded
recurrent junction (`core.py` `SharedPneumaCore`: a persistent 256-d
`recurrent_state` + 64-slot memory carried across steps, a 1%-scaled residual
into the frozen backbone) is an **architecture-only optional ablation, never a
headline arm.**

Inclusion criterion (strict): it is run ONLY if it can execute **at the same
budget** (same actor, same tool set, same token/action/retry caps, same tasks)
and **only after it gets a real-model evaluation**. The foundation audit found
the junction is tested exclusively against a `FakeQwen` mock (no committed
evidence it does anything useful on a real backbone), and the one real local
training result is a **saturation plateau** (8M ladder, 64.14%, doubling-gate
stopped, margins only vs UNTRAINED baselines). Given that, per the audit's
recommendation, the first paper ships design **(a)** — external fixed actor +
Pneuma controller/memory — and this arm is **cited as future work / motivation**:
"we prototype a bounded recurrent internal-state module; on a data-limited local
ladder it saturated, motivating the interpretable-state approach." If a matched
real-model eval later succeeds, it is added as ONE ablation arm (external actor +
junction as the state carrier), not as the paper's subject. Its state lives in
weights, not an interpretable store, so it can never satisfy the clamp-level H2
contrast the way the four-variable state does — a further reason it stays an
ablation.

---

## 5. What differs between conditions — one row per condition

Every column except the last three is IDENTICAL across all rows (see §1.2). This
table is the compact statement of the experiment: read down the "Cross-task
store", "Injected into decision", and "Extra context tokens" columns — that is
the entire treatment space.

| Condition                | Cross-task store                          | What it computes/retrieves                       | Injected into decision (via)          | Extra context tokens vs Base | Differs from Base by            | H-role              |
| ------------------------ | ----------------------------------------- | ------------------------------------------------ | ------------------------------------- | ---------------------------- | ------------------------------- | ------------------- |
| 1. Base                  | none                                      | nothing                                          | nothing (head fed zeros)              | 0 (reference)                | — (reference arm)               | control             |
| 2. Retrieval             | SQLite/FTS5 failure records (`memory.py`) | top-k similarity over past failures              | retrieved text block (prompt channel) | + `B_ret` (measured, capped) | text memory in context          | H1 baseline         |
| 3. Reflection            | NL lesson buffer (Reflexion/ExpeL)        | applicable prior lessons                         | lessons text block (prompt channel)   | + `B_ref` (measured, capped) | self-written lessons in context | H1 baseline         |
| 4. Pneuma-state          | 4 numeric vars + `L` (`02` §8.3)          | `L = clip(w1·s_m+w2·c'+w3·t)` from real detector | action bias (bounded decision head)   | ≈ 0 (scalar state)           | numeric state biases the head   | H1 treatment        |
| 5. Retry-count           | per-task retry integer (no carry)         | count vs threshold `N`                           | action bias after `N` (same head)     | ≈ 0                          | non-learned counter biases head | falsification guard |
| 6. Pneuma-ablated (null) | 4 vars with `s_m` clamped                 | `L` with failure memory pinned                   | action bias (same head, dead `s_m`)   | ≈ 0                          | one variable clamped vs Cond. 4 | H2 causal control   |

Cross-reference map: Condition 4 vs {1,2,3,5} tests **H1** (behavioural
reduction); Condition 4 vs Condition 6 tests **H2** (causation, via the `02` §8.8
statistical paired runner with N-sample distributional nulls, since a stochastic
actor cannot satisfy the byte-equality clone gate); Condition 5 is the E-0
falsification guard; the retrieval/reflection arms double as the "isn't this just
Reflexion/retrieval?" structural rebuttal from `02` §7.

---

## 6. Open parameters deferred to sibling documents

These are named here for completeness but SET elsewhere (do not fix them in this
doc): the exact base checkpoint and the ≥2 sizes (`02` §8.1); the four internal
variables' update/decay/cap laws and clamp seams (`06-internal-state-specification.md`);
the decision-head mapping table (`06`); `B_ret`, `B_ref`, top-k, `N`, and the
filler-control length policy (tuned per `08-metrics-and-statistics.md`); RUF and
the injected-token-decile conditioning (`08`); the statistical causal path and
null-reproduction test (`09-intervention-and-causal-validity.md`); the
prose-blind scorer, decoy memories, adversarial reflections, and counterfactual
tasks (`10-anti-gaming-specification.md`).

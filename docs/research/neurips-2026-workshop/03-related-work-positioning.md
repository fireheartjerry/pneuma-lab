# 03 — Related Work and Positioning

Status: canonical-consistent. This document inherits every claim from
`02-research-thesis.md` §8 (Locked Design Constants) and the maturity map in
`01-current-state-audit.md`. It positions the first paper against prior work,
names its closest neighbors, pre-empts reviewer objections, and flags citation
uncertainty honestly. Source material: the URL-cited related-work map archived in
the session scratchpad (`audit/research-related-work.md`, compiled 2026-07-22).

Planning only. No implementation, no experiments, no data conversion.

**The four differentiators the paper owns** (the contrast axes used throughout;
verbatim from thesis §7):

1. **Persistent, structured, causally-active state** — a live internal variable
   that gates the action, not natural-language text re-injected from a store.
2. **Clamp/ablation causal proof** — paired control/treated/null replay with an
   _a priori_ expected-vs-observed delta and a holding null (thesis §8.8).
3. **Behaviour-vs-self-report firewall** — a prose-blind behavioural scorer;
   self-report is a separate, non-scored channel (thesis §8.9–8.10).
4. **Repeated-structural-failure metric** — the `RUF` cross-task recurrence rate
   (thesis §8.7), orthogonal to per-task resolve rate / Pass@1.

Machine-consciousness indicator work (Cluster 5) is cited **strictly as
motivation**. The paper makes **no phenomenal-consciousness claim** (thesis §5,
tier 6; `phenomenal_consciousness_claim: not_claimed`).

---

## 1. Five clusters

### Cluster 1 — LLM agent memory systems

| Work                            | ID / venue                               | One-line what-it-does                                                                                                     |
| ------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| MemGPT (Packer et al.)          | arXiv:2310.08560; COLM 2024 (UNVERIFIED) | OS-style virtual context that pages **text** between main/recall/archival tiers via function calls.                       |
| Generative Agents (Park et al.) | arXiv:2304.03442; UIST 2023              | A **memory stream** of NL observations scored by recency/importance/relevance; reflection synthesizes higher-level notes. |
| Voyager (Wang et al.)           | arXiv:2305.16291; venue UNVERIFIED       | A retrieval **skill library of executable code** indexed by description embeddings.                                       |
| A-MEM (Xu, Liang et al.)        | arXiv:2502.12110; NeurIPS 2025           | A Zettelkasten **linked note graph** with agentic link-generation and memory evolution.                                   |
| Reflexion (Shinn et al.)        | arXiv:2303.11366; NeurIPS 2023           | Verbal reflections held in an **episodic memory buffer** and re-injected (also a Cluster-2 baseline).                     |

**Precise gap Pneuma fills.** In every system here, "memory" is externalized
NL/code whose _only_ channel of influence on behaviour is **token re-injection
into the context window**; even A-MEM's graph is structure _over text_ consulted
by retrieval, never a variable in the forward pass. None clamps/ablates an
internal state against a null to prove memory's causal role, and none targets
**repeated structurally-similar failures** (all report aggregate task
success / QA accuracy). Pneuma carries state that gates the action, proves its
role by clamp/ablation with expected-vs-observed deltas, and scores
failure-recurrence reduction (`RUF`). MemGPT's SQLite/FTS5-style store is
reused, honestly, as our **retrieval baseline** (`foundation/memory.py`,
thesis §8.2) — not as a differentiator.

### Cluster 2 — Self-reflection / verbal reinforcement / self-improvement

| Work                        | ID / venue                               | One-line what-it-does                                                                                            |
| --------------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Reflexion (Shinn et al.)    | arXiv:2303.11366; NeurIPS 2023           | NL reflection after failure, stored in an episodic buffer and re-injected as prompt.                             |
| Self-Refine (Madaan et al.) | arXiv:2303.17651; NeurIPS 2023           | One LLM writes NL feedback on its own output and re-injects to revise, within an episode.                        |
| CRITIC (Gou et al.)         | arXiv:2305.11738; ICLR 2024 (UNVERIFIED) | Self-correction grounded in **external tools** (search, code interpreter).                                       |
| ExpeL (Zhao et al.)         | arXiv:2308.10144; AAAI-24                | Cross-task NL "insights" extracted from a trajectory experience pool, injected at test time.                     |
| Retroformer (Yao et al.)    | arXiv ID / venue UNVERIFIED              | A retrospective model tunes the agent's prompt via SFT+PPO; the actuated artifact is still injected prompt text. |

**Precise gap Pneuma fills.** The whole cluster stores _prose_ that is
re-injected: prose is not machine-addressable (cannot be diffed / snapshot /
held byte-identical), so no clean causal test; its "ablations" toggle whether a
text block is present and read task score — indistinguishable from generic
"extra context primed the decoder"; and the reflection text is simultaneously
the mechanism _and_ the self-explanation, so the metric is gameable by fluent
rationalization. Pneuma uses re-appliable structured state, a paired
control/treated/null clamp, and a prose-blind scorer measuring `RUF`. Reflexion
and ExpeL are **included as baselines under identical budget** (thesis §8.2,
conditions 3 and 2-adjacent), not merely cited.

### Cluster 3 — SWE agents and their evaluation

| Work                                                | ID / venue                          | One-line what-it-does                                                                                                  |
| --------------------------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| SWE-bench (Jimenez et al.)                          | arXiv:2310.06770; ICLR 2024         | 2,294 real GitHub issue→PR tasks; success = hidden tests pass (per-task, memoryless).                                  |
| SWE-bench Verified (OpenAI)                         | 2024 announcement + HF dataset      | 500 human-validated instances; de-facto standard test set, same contract.                                              |
| SWE-agent (Yang et al.)                             | arXiv:2405.15793; NeurIPS 2024      | Agent-Computer Interface; produces the trajectory format others consume; fresh episode per task.                       |
| SWE-Gym (Pan et al.)                                | arXiv:2412.21139; ICML 2025         | First _training_ env (2,438 executable instances); cross-task gains come via **weight updates**, reports resolve rate. |
| SWE-Exp (Chen et al.)                               | arXiv:2507.23361; 2026              | A **cross-task experience bank** (success + failure) — nearest memory competitor; reports only Pass@1 = 73.0%.         |
| TraceProbe / "What Resolve Rate Hides" (Shu et al.) | arXiv:2607.06184; 2026 (UNVERIFIED) | 9-type action taxonomy naming **single-trajectory** anti-patterns (e.g. search loops).                                 |
| Failure as a Process (Zhao et al.)                  | arXiv:2607.09510; 2026 (UNVERIFIED) | Root-cause failure taxonomy _within a single trajectory_ (Epistemic / Competence / Environment).                       |

**Precise gap Pneuma fills.** The field splits into (1) memoryless per-task
resolve-rate benchmarks, (2) _within-run_ failure analyses, and (3)
memory/experience methods that still report only aggregate Pass@1. None occupies
Pneuma's cell, which differs on three axes at once: **unit** (a
structurally-similar failure class recurring _across_ tasks — two systems with
identical Pass@1 can have very different repeated-failure rates); **metric**
(`RUF` reduction, not bundled Pass@1); **causal attribution** (memory-on vs
memory-off/null ablation, not a bundled resolve-rate gain). SWE-Gym's gains
entangle "learned the domain" with "stopped repeating an error"; our memory-off
null disentangles them. Benchmark data (Open-SWE-Traces, SWE-Gym
OpenHands-Sampled) is reused via existing adapters (thesis §8.5).

### Cluster 4 — Causal / interpretability methods for internal states

| Work                                                                   | ID / venue                      | One-line what-it-does                                                                                       |
| ---------------------------------------------------------------------- | ------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| ROME / Causal Tracing (Meng et al.)                                    | arXiv:2202.05262; NeurIPS 2022  | Corrupt-then-restore hidden states (causal mediation) for single-shot factual recall; rank-one weight edit. |
| Causal Mediation Analysis in LMs (Vig et al.)                          | NeurIPS 2020                    | Intervene on neurons/heads as mediators (direct/indirect effects) on transient activations (bias).          |
| Path Patching / Causal Scrubbing (Goldowsky-Dill et al. / Chan et al.) | arXiv:2304.05969 / Redwood 2023 | Patch or resample-ablate activations along circuit edges to test necessity/sufficiency.                     |
| LMs (Mostly) Know What They Know (Kadavath et al.)                     | arXiv:2207.05221; 2022          | Behavioral calibration self-eval (P(True), P(IK)); touches self-report but no intervention.                 |
| CoT Unfaithfulness (Turpin et al.)                                     | arXiv:2305.04388; NeurIPS 2023  | **Input biasing** shows chain-of-thought explanations misstate the true cause.                              |

**Precise gap Pneuma fills.** Every canonical causal method operates on
**transient within-forward-pass activations**, overwhelmingly for single-shot
factual recall or bias. The two faithfulness papers use behavioral calibration
(Kadavath) or input-side perturbation (Turpin) — neither clamps/ablates an
_internal state_ to certify that a self-report names the true internal cause.
Pneuma differs on two couplings: the intervention target is **persistent,
structured, cross-episode agent state** (scar/affect/self-model/memory-trust,
surviving between episodes), not activations that vanish at pass end; and the
clamp/ablation is a **faithfulness oracle** — the paired control/treated/null
design checks that the self-report moves in the predicted direction _only when_
the responsible state is perturbed (thesis H3). We borrow the corrupt-then-
restore _logic_ but relocate it from circuit localization to cross-episode-state
faithfulness certification.

### Cluster 5 — Machine-consciousness indicators (MOTIVATION ONLY — no claim)

> This cluster motivates _why_ persistent causally-active state and
> workspace-broadcast architectures are worth building and measuring. The paper
> makes **no phenomenal-consciousness claim** and takes no position on machine
> experience (thesis §5 tier 6; §2).

| Work                                                 | ID / venue                                              | One-line what-it-does                                                                                                                             |
| ---------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Butlin, Long, et al. (2023)                          | arXiv:2308.08708                                        | Derives assessable **indicator properties** from neuroscientific theories; concludes no current AI is conscious but no obvious technical barrier. |
| Global Workspace Theory (Baars 1988; Dehaene et al.) | Prog. Brain Res. 2005 (S0079612305500049); GWT overview | Information becomes conscious when "broadcast" across a shared workspace / prefrontal-parietal network.                                           |
| Chalmers (2023)                                      | arXiv:2303.07103                                        | Names the _absence_ of recurrence, a global workspace, and unified agency as what LLMs lack.                                                      |
| Long, Sebo, Butlin et al. (2024)                     | arXiv:2411.00986                                        | "Taking AI Welfare Seriously" — an uncertainty-management stance, not a consciousness assertion.                                                  |

**Precise gap Pneuma fills.** These works give a rubric of _which architectural
properties are worth building and measuring_ (persistent state, workspace
broadcast, recurrent processing, self-monitoring) but stop at
assessment/verdict; they do not deliver a falsifiable behavioural+causal test on
a real agent. Pneuma supplies exactly that test — controlled clamp/ablation over
paired replay on a software-engineering agent — and stays firewalled from any
phenomenal claim.

---

## 2. Closest neighbors

These five are the most dangerous neighbors: cite and distinguish each
explicitly. A ✓ means the neighbor _lacks_ our differentiator (so it separates
us); the cell says how.

| Neighbor                     | ID               | Persistent structured causally-active state                                                      | Clamp/ablation causal proof                                                              | Behaviour-vs-self-report firewall                  | Repeated-structural-failure metric                                  |
| ---------------------------- | ---------------- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------- |
| **SWE-Exp** (Chen et al.)    | arXiv:2507.23361 | ✓ carries a cross-task experience bank, but as **re-injected text**, not a forward-pass variable | ✓ no intervention; reports bundled Pass@1 = 73.0%                                        | ✓ experience prose is both mechanism and rationale | ✓ never quantifies repeated-failure reduction — reports Pass@1 only |
| **Reflexion** (Shinn et al.) | arXiv:2303.11366 | ✓ verbal reflections in an episodic buffer, re-injected as prompt text                           | ✓ ablations toggle feedback _variants_, never clamp a state on a byte-identical timeline | ✓ reflection _is_ mechanism-and-explanation-in-one | ✓ scores end-task success, not cross-task recurrence                |
| **ExpeL** (Zhao et al.)      | arXiv:2308.10144 | ✓ cross-task NL "insights" injected at test time; text, not state                                | ✓ whether its ablation ever holds behaviour fixed is UNVERIFIED; no null-arm clamp       | ✓ insight prose doubles as explanation             | ✓ reports aggregate task performance                                |
| **A-MEM** (Xu, Liang et al.) | arXiv:2502.12110 | ✓ most "structured" prior memory — but a linked note graph _over text_, consulted by retrieval   | ✓ QA benchmark + coarse module ablation, no clamp-against-null                           | ✓ no separate non-scored self-report channel       | ✓ reports QA accuracy                                               |
| **MemGPT** (Packer et al.)   | arXiv:2310.08560 | ✓ nearest neighbor to _managed_ memory, but pages **text** between tiers                         | ✓ no causal intervention on state                                                        | ✓ no firewall                                      | ✓ no recurrence metric; reused by us as the retrieval baseline      |

**How our four differentiators separate us, in one line each.** (1)
_Carrier:_ ours is persistent structured state that gates the action and is
snapshot/clone-equivalent; theirs is free-text re-injected. (2) _Causality:_ we
clamp/ablate the state on a byte-identical (synthetic) or seed-frozen
(statistical) timeline, require the observed delta to match an a-priori expected
delta, and require the restore/null to hold; none of them intervenes on its own
memory. (3) _Anti-gaming:_ we firewall a prose-blind non-scored self-report from
the behavioural score; in all five the prose is simultaneously mechanism and
explanation. (4) _Metric:_ we score `RUF` cross-task recurrence; all five report
resolve rate / Pass@1 / QA accuracy. Correct framing for the paper: SWE-Exp and
Reflexion show cross-task text _correlates with_ improvement; Pneuma shows a
_specific structured state causally_ reduces recurrence of a failure class under
a clamp, independent of what the agent says — same problem family, strictly
stronger evidential contract.

---

## 3. Reviewer-objection table

| Objection                                                        | Concrete rebuttal grounded in our design                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| "This is just Reflexion / written reflection with a new name."   | Reflexion is **included as a baseline under identical base model, tools, budget, retry cap, and task order** (thesis §8.2, condition 3). If our numeric-state condition does not beat it on `RUF`, H1 is falsified (thesis §6). The clamp isolates structured state _over_ text: Reflexion re-injects prose (not diffable / not snapshot-identical) and its ablations toggle feedback variants; we clamp a specific state variable on a byte-identical timeline and require an a-priori delta plus a holding null.                         |
| "This is just retrieval memory / MemGPT."                        | In MemGPT the store influences behaviour **only** via token re-injection; remove the re-injection and the effect is zero because it was never in the computation. Our state participates in the decision head directly (thesis §8.4), so its influence is testable independent of any prompt text. MemGPT's store is precisely our **retrieval baseline** (`foundation/memory.py`) — we out-condition it, not relabel it.                                                                                                                  |
| "The internal state is hand-designed, not learned — so what?"    | We claim a **causal** result, not an emergent-representation result. The four variables (thesis §8.3) are chosen for having a measurable causal role or being cut; each ships a clamp seam. Hand-design is a feature: it makes the state addressable, snapshot/clone-equivalent, and cleanly ablatable — the precondition for the causal test that learned prose memory cannot support. An optional recurrent-hidden-state arm (thesis §8.2) probes the learned-state variant as an ablation.                                              |
| "SWE-bench / synthetic motifs are toy tasks."                    | Two-suite design (thesis §8.5): a synthetic controlled-motif suite for exact motif ground truth _and_ a **real-repo suite** (Open-SWE-Traces: 207k step-level trajectories, ~41% resolved, 2 models × 2 harnesses; plus SWE-Gym OpenHands-Sampled). H4 requires the effect to survive surface variation and **held-out repos and motifs** (thesis §6), so identifier memorization falsifies us. Splits are leakage-quarantined (7 overlapping repos registered).                                                                           |
| "Isn't clamping just prompt ablation by another name?"           | No. Prompt ablation toggles whether a text block is in context and reads task score — it cannot distinguish "the content caused it" from "extra tokens primed the decoder." We clamp a **numeric state variable inside the decision head** while holding the prompt, tools, seed, and retrieved memory fixed (thesis §8.8): frozen model seeds, frozen prompts, frozen retrieved memory, recorded transcripts, plus an N-sample distributional null. The treated-minus-null contrast, not the presence/absence of text, carries the claim. |
| "Your own signals didn't even predict failure (the E-0 result)." | Stated honestly up front (audit §7): E-0 replayed psyche signals scored AUROC 0.339/0.349 vs a retry-count baseline of 0.705 at _passive prediction_. Consequence, not concealment: retry-count is a **mandatory strong baseline** (thesis §8.2, arm 5), budgets are tightly matched, and the DV is **behavioural repeat-reduction under causal gating**, not passive prediction — a different quantity.                                                                                                                                   |
| "Where is the persistence — scars reset every run."              | Acknowledged as currently aspirational (audit §7.3): today's persistence is tautological (fixed +0.1 on a fixture motif). Genuine longitudinal persistence on real data is a **build and a claim to earn** (blocker B-EVID-LONGITUDINAL), with decay and cap added to the failure-sensitivity variable (thesis §8.3). The paper reports measured cross-run persistence, not asserted persistence.                                                                                                                                          |

---

## 4. Citation-status table

Carried forward honestly from the source map's flags. **Do not invent
citations.** VERIFIED = primary text or authoritative source confirmed the
claim; UNVERIFIED = corroborated only by secondary sources or abstract-level;
NOT FOUND = could not confirm and must be checked before camera-ready.

| Reference                                              | ID                            | Status                                                                                 | What to confirm before citing                                                                       |
| ------------------------------------------------------ | ----------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| MemGPT                                                 | arXiv:2310.08560              | arXiv VERIFIED; **venue (COLM 2024) UNVERIFIED**                                       | Confirm proceedings-level venue or cite as arXiv.                                                   |
| Generative Agents                                      | arXiv:2304.03442              | VERIFIED (UIST 2023)                                                                   | —                                                                                                   |
| Voyager                                                | arXiv:2305.16291              | arXiv VERIFIED; **venue UNVERIFIED**                                                   | Confirm venue or cite as arXiv/preprint.                                                            |
| A-MEM                                                  | arXiv:2502.12110              | VERIFIED (NeurIPS 2025)                                                                | —                                                                                                   |
| Reflexion                                              | arXiv:2303.11366              | VERIFIED (NeurIPS 2023)                                                                | —                                                                                                   |
| Self-Refine                                            | arXiv:2303.17651              | VERIFIED (NeurIPS 2023)                                                                | —                                                                                                   |
| CRITIC                                                 | arXiv:2305.11738              | arXiv VERIFIED; **venue (ICLR 2024) UNVERIFIED**                                       | Confirm ICLR 2024 acceptance.                                                                       |
| ExpeL                                                  | arXiv:2308.10144              | VERIFIED (AAAI-24); **ablation-holds-behaviour-fixed UNVERIFIED**                      | Read the ablation protocol before asserting it does/doesn't hold behaviour fixed.                   |
| Retroformer                                            | ID / venue UNVERIFIED         | **UNVERIFIED (author, arXiv id, venue)**                                               | Locate and verify arXiv id + author list before citing; drop if unconfirmable.                      |
| SWE-bench                                              | arXiv:2310.06770              | VERIFIED (ICLR 2024)                                                                   | —                                                                                                   |
| SWE-bench Verified                                     | OpenAI 2024 announcement + HF | VERIFIED (announcement)                                                                | Cite announcement + dataset; no paper venue.                                                        |
| SWE-agent                                              | arXiv:2405.15793              | VERIFIED (NeurIPS 2024)                                                                | —                                                                                                   |
| OpenHands / OpenDevin                                  | arXiv:2407.16741              | VERIFIED (ICLR 2025)                                                                   | —                                                                                                   |
| SWE-Gym                                                | arXiv:2412.21139              | VERIFIED (ICML 2025)                                                                   | —                                                                                                   |
| **SWE-Exp**                                            | arXiv:2507.23361              | arXiv VERIFIED; **Pass@1 = 73.0% figure abstract-level, venue UNVERIFIED**             | Confirm the 73.0% number and venue from the paper body (load-bearing — it is the closest neighbor). |
| TraceProbe / "What Resolve Rate Hides"                 | arXiv:2607.06184              | **UNVERIFIED** (2026 id; abstract-level)                                               | Verify id, authors, and the within-vs-cross-trajectory claim.                                       |
| Failure as a Process                                   | arXiv:2607.09510              | **UNVERIFIED** (2026 id; taxonomy percentages abstract-level)                          | Verify id and the Epistemic/Competence/Environment split.                                           |
| Understanding Code Agent Behaviour (Majgaonkar et al.) | arXiv:2511.00197              | **UNVERIFIED**                                                                         | Verify id and authorship.                                                                           |
| ROME / Causal Tracing                                  | arXiv:2202.05262              | VERIFIED (NeurIPS 2022)                                                                | —                                                                                                   |
| Causal Mediation (Vig et al.)                          | NeurIPS 2020                  | VERIFIED                                                                               | —                                                                                                   |
| Path Patching                                          | arXiv:2304.05969              | ID/title VERIFIED; **author spelling not byte-verified**                               | Confirm author list spelling.                                                                       |
| Causal Scrubbing                                       | Redwood / AlignmentForum 2023 | VERIFIED (blog/forum, non-archival)                                                    | Cite as technical report / forum post.                                                              |
| Kadavath et al.                                        | arXiv:2207.05221              | VERIFIED                                                                               | —                                                                                                   |
| Turpin et al. (CoT Unfaithfulness)                     | arXiv:2305.04388              | VERIFIED (NeurIPS 2023)                                                                | —                                                                                                   |
| Mao et al. "What Happens Inside Agent Memory?"         | arXiv:2605.03354              | **UNVERIFIED** (excerpts only)                                                         | Verify before citing; relevant as a near-miss (within-model, not cross-episode clamp).              |
| Azaria & Mitchell                                      | arXiv:2304.13734              | VERIFIED (adjacent)                                                                    | Optional; transient-activation probe.                                                               |
| Butlin, Long, et al.                                   | arXiv:2308.08708              | VERIFIED; **"agency/embodiment as a named theory" UNVERIFIED**                         | Cite theories as indicator dimensions, not as a 6th named theory.                                   |
| GWT (Baars 1988; Dehaene et al.)                       | S0079612305500049 + overview  | Baars/Dehaene VERIFIED; **year-by-year Dehaene citations via secondary overview only** | Confirm individual Dehaene year citations if used precisely.                                        |
| Chalmers (2023)                                        | arXiv:2303.07103              | VERIFIED                                                                               | —                                                                                                   |
| Long, Sebo, Butlin et al. (2024)                       | arXiv:2411.00986              | VERIFIED                                                                               | —                                                                                                   |
| MIRAGE-Bench                                           | arXiv:2507.21017              | **UNVERIFIED** (color, not load-bearing)                                               | Cite only if verified; otherwise omit.                                                              |

Workshop-target facts (from the source map, for `02`/`11` cross-reference):
IAB workshop and "Who Verifies the Agents?" both **CONFIRMED**, both deadline
**2026-08-29**; IAB page limits **9pp long / 4pp short + refs (CONFIRMED)**;
"Who Verifies the Agents?" page limits **NOT FOUND** (do not assume a number).
NeurIPS 2026 = Sydney, Dec 6–12 (a stale `/Dates` sub-page says "San Diego" —
that page is wrong).

---

## 5. Positioning statement (drop-in for the intro)

No prior line of work occupies our cell. Memory agents (MemGPT, Generative
Agents, Voyager, A-MEM) and reflection methods (Reflexion, Self-Refine, ExpeL,
and the SWE-specific SWE-Exp) carry learning as **re-injected text** and validate
it by **outcome**, never by clamping an internal state against a holding null.
SWE-agent evaluation (SWE-bench and SWE-bench Verified, SWE-Gym, and even the
memory-bearing SWE-Exp at Pass@1 = 73.0%) scores **memoryless per-task resolve
rate**, and single-trajectory failure analyses (Failure-as-a-Process, TraceProbe)
stay **within one run**. Causal interpretability (ROME, path patching, causal
scrubbing) intervenes on **transient activations** for factual recall, while
self-report faithfulness work (Turpin, Kadavath) perturbs the **input** or
measures **calibration** rather than ablating persistent state to certify a
report. We are the first to combine (1) persistent, structured, causally-active
internal state that gates the action, (2) a clamp/ablation causal proof against a
holding null with an a-priori expected-vs-observed delta, (3) a prose-blind
behaviour-vs-self-report firewall, and (4) a repeated-structurally-similar-failure
metric (`RUF`) — with machine-consciousness indicator work (Butlin, Long, et al.;
Global Workspace Theory) cited strictly to motivate _which_ architectural
properties are worth measuring, and no phenomenal-consciousness claim made.

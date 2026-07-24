# 27 — The Audit Frame

**Date:** 2026-07-24
**Status:** FROZEN. Membership fixed by the procedure in `22-audit-rubric.md` §1.
Amendments require a dated entry in `15-decision-log.md`.

**Frame size: N = 28 + self-inclusion = 29.** RET-LLM removed by DL-57. Cap raised from 25 to 30 by DL-55; nothing truncated,
therefore no ordering dependency.

---

## 1. Strata

The frame contains two different objects and they are analyzed separately.

**System papers (23).** Propose a memory mechanism and claim it improves performance.
The claimed effect is theirs to defend.

**Benchmark papers (5).** Define a measurement. They make no claim that their own memory
helps — but **every system evaluated on them inherits their sample structure.** A benchmark
built from ten conversations imposes ten clusters on every downstream user, forever. This
stratum is arguably the more consequential of the two.

**Self-inclusion (1).** Pneuma Lab's own E-0 reference-psyche transfer result
(`build/e0/report.json`), coded under the identical rubric, reported in the main table
without mitigation. Mandatory per `22-audit-rubric.md` §1.

## 2. Members

| #   | System                | arXiv      | Stratum   | Coded       |
| --- | --------------------- | ---------- | --------- | ----------- |
| 1   | Reflexion             | 2303.11366 | system    | yes         |
| 2   | Voyager               | 2305.16291 | system    | yes         |
| 3   | Generative Agents     | 2304.03442 | system    | yes         |
| 4   | MemGPT                | 2310.08560 | system    | yes         |
| 5   | LongMem               | 2306.07174 | system    | in progress |
| 6   | ExpeL                 | 2308.10144 | system    | yes         |
| 7   | MemoryBank            | 2305.10250 | system    | in progress |
| 8   | ChatDB                | 2306.03901 | system    | in progress |
| 9   | A-MEM                 | 2502.12110 | system    | yes         |
| 10  | Think-in-Memory       | 2311.08719 | system    | in progress |
| 11  | Mem0                  | 2504.19413 | system    | yes         |
| 12  | Agent Workflow Memory | 2409.07429 | system    | yes         |
| --  | ~~RET-LLM~~           | 2305.14322 | REMOVED   | DL-57: exclusion 2, no quantitative evaluation |
| 14  | Zep                   | 2501.13956 | system    | in progress |
| 15  | SWE-Exp               | 2507.23361 | system    | yes         |
| 16  | MemLLM                | 2404.11672 | system    | in progress |
| 17  | AgeMem                | 2601.01885 | system    | in progress |
| 18  | LongMemEval           | 2410.10813 | benchmark | yes         |
| 19  | LoCoMo                | 2402.17753 | benchmark | in progress |
| 20  | MemoryAgentBench      | 2507.05257 | benchmark | in progress |
| 21  | MemBench              | 2506.21605 | benchmark | in progress |
| 22  | MemoryArena           | 2602.16313 | benchmark | in progress |
| 23  | ReasoningBank         | 2509.25140 | system    | queued      |
| 24  | Memento               | 2508.16153 | system    | queued      |
| 25  | Trace2Skill           | 2603.25158 | system    | queued      |
| 26  | G-Memory              | 2506.07398 | system    | queued      |
| 27  | Agent Skill Induction | 2504.06821 | system    | queued      |
| 28  | MemoryOS              | 2506.06326 | system    | queued      |
| 29  | AgentCL               | 2606.02461 | system    | yes         |
| 30  | JARVIS-1              | 2311.05997 | system    | yes         |
| 31  | GITM                  | 2305.17144 | system    | yes         |

Rows 30-31 admitted by DL-67 after the survey bibliography was hand-verified; both are
survey-cited and meet criterion 1, and the original automated extraction dropped them.
| 30  | **E-0 (ours)**        | —          | self      | pending     |

Rows 23–29 admitted by DL-55; see §4.

## 3. Named exclusions, with the deciding rule

Recorded so a reader can see exactly what the frame does and does not reach.

| System                                                    | arXiv      | Excluded by                                                               |
| --------------------------------------------------------- | ---------- | ------------------------------------------------------------------------- |
| ReadAgent                                                 | 2402.09727 | Criterion 1 — gist memory is within-document; no cross-episode write path |
| Cognee                                                    | 2505.24478 | Exclusion 1 — pure RAG over a static KG; no experience write path         |
| Memento 2                                                 | 2512.22716 | Exclusion 2 — purely theoretical; zero results tables                     |
| MemDelta                                                  | 2606.29914 | Criteria 1–2 — proposes no memory system; it is a methodology critique    |
| _Are Online Skill and Memory Modules Worth Their Tokens?_ | 2606.15017 | Criteria 1–2 — audits AWM/ASI/ReasoningBank; proposes no system           |
| Agent-memory survey                                       | 2603.07670 | Exclusion 2 — it is the frame-defining source, not a member               |
| Letta, LangMem                                            | —          | No standalone paper. Letta is the product successor to MemGPT (#4).       |

**MemDelta and 2606.15017 are excluded as members but are direct prior art and must be cited.**
MemDelta anticipates the F5 `inert_null` distinction (_"verbatim RAG matches full-context
GPT-4o-mini, 47.2% vs 49.8%, p=0.34"_); 2606.15017 anticipates F7 budget parity (_"the vanilla
baseline matches or surpasses all three augmentation methods... their apparent gains often
vanish against a budget-matched actor"_). Both are load-bearing for the related-work section
and for correctly scoping our own secondary findings.

## 4. Admitted by amendment — the seven the original procedure missed

Seven systems satisfy all four inclusion criteria but were **not reachable** by the original
§1 procedure: no seed compares against them (all seeds predate them) and the survey
bibliography does not cite them.

| System | arXiv | First author | Date | S2 citations |
| --- | --- | --- | --- | --- |
| ReasoningBank | 2509.25140 | Siru Ouyang | 2025-09-29 | 142 |
| Memento | 2508.16153 | Huichi Zhou | 2025-08-22 | 80 |
| Trace2Skill | 2603.25158 | Jingwei Ni | 2026-03-26 | 61 |
| G-Memory | 2506.07398 | Guibin Zhang | 2025-06-09 | — |
| Agent Skill Induction (ASI) | 2504.06821 | Zora Zhiruo Wang | 2025-04-09 | — |
| MemoryOS | 2506.06326 | Jiazheng Kang | 2025-05-30 | — |
| AgentCL | 2606.02461 | Yiheng Shu | 2026-06-01 | — |

**Decision reversed, 2026-07-24 (DL-55): all seven are ADMITTED.**

The original decision to exclude them rested on OpenAlex citation counts showing them as a
zero-citation tail, making any truncation arbitrary. Semantic Scholar shows that was wrong by
one to two orders of magnitude — ReasoningBank has 142 citations, Memento 80, Trace2Skill 61.
Excluding prominent systems from an audit of this literature because our own sampling
procedure under-reached them is not defensible, and "the procedure did not reach it" is a weak
answer when we wrote the procedure.

The $N$ cap is raised from 25 to 30 so that admitting them forces no truncation. The cap was a
convenience constraint on coding effort, not a scientific one; for an audit, coverage
dominates. With no truncation the frame has no ordering dependency, which also neutralises the
citation-source disagreement recorded in §5.

**This amendment changes §1 sampling reach only. The nine coding fields are untouched, so no
previously coded paper requires recoding.**

## 5. Two recorded corrections

1. **"ASI" is Agent Skill Induction** (arXiv:2504.06821, Wang et al., same group as AWM).
   There is no paper titled "Agentic Self-Improvement"; an earlier internal brief had this
   wrong. Confirmed against 2606.15017, which evaluates "AWM, ASI, and ReasoningBank"
   together.
2. **Citation counts are not usable for ordering.** OpenAlex and Semantic Scholar disagree by
   an order of magnitude on the same papers — Reflexion 272 vs 4,460; A-MEM 9 vs 767 — enough
   to reorder the table materially. Because the frame is not truncated at $N=22$, ordering
   does not affect membership and no ranking is frozen. Any published ordering must state its
   source and its disagreement with the alternative.

## 6. Outstanding

- Survey bibliography (2603.07670) should be re-checked by hand before freeze; the first two
  automated extractions disagreed with each other, and rows 5, 8, 10, 13, 16, 20–22 derive
  from it.
- E-0 self-audit not yet coded.

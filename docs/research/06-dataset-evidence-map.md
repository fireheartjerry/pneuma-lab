# 06 — Dataset-to-Evidence Map

**Status (2026-07-07):** 10 SWE dataset groups are local and inventoried under `C:\pneuma-data` (37,711 files, 48.95 GB, pinned revision SHAs in `C:\pneuma-data\manifests\provenance_dossiers.json`) [VERIFIED]. Exactly two dataset→PneumaTrace adapters are shipped: `src/pneuma_lab/adapters/swe_gym_lite.py` (230 task-only traces, world+governance frames, `has_trajectory=false`, committed) [VERIFIED] and `src/pneuma_lab/adapters/openhands_sampled.py` (6,055/6,055 trajectory-bearing traces, 114,461 real agent steps, 491 resolved / 5,564 unresolved labels, byte-deterministic twice-run sha256 match, deterministic PII redaction; **uncommitted working-tree state**) [VERIFIED]. No learned estimator, no eval suite, and no harness replay path consumes any adapter output today — the pipe from `adapters/` into `replay/harness.py` does not exist [VERIFIED gap]. Everything below the two shipped adapters is design, graded NEAR/FAR/NONE. Corpus row-count honesty: the global inventory's "8,521,307 verified rows" mixes JSONL line counts with parsed records; the honest parsed-record total is ≈5.99M (swe-chat parsed = 3,098,007 vs 5,626,805 lines) [VERIFIED].

Scope of this document: map the 10 datasets onto the program's 12 evidence targets; grade every cell; specify per-dataset signal, required PneumaTrace extensions, leakage/contamination risk, and privacy class; order the adapter build queue by evidence-value per engineering cost; and state plainly which targets no local dataset can evidence. Sibling documents in `docs/research/` cover the evidence ladder, the harness methodology, and the RSI roadmap; this document is the data plane.

---

## 1. The 12 evidence targets

Targets are numbered T1–T12 and used as matrix columns. Honesty rules apply to every one of them: proxies are proxies (operator pushback ≠ suffering; tension ≠ affect; self-report ≠ introspection ground truth), and architecture is never evidence — only receipts + interventions + nulls are.

| ID  | Target                                | What would count as evidence (artifact-level)                                                                                                                     |
| --- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | Scar-motif learning                   | An estimator trained on failure/retry motifs measurably avoids repeat failures on held-out instances; receipts in traces, eval report with pre-registered deltas. |
| T2  | Verification-pressure calibration     | Predicted verification need correlates with realized outcome (resolved/unresolved, test verdicts) on held-out data; calibration curve artifact.                   |
| T3  | Authority-request calibration         | Model of _when to ask the operator_ matches human correction/clarification incidence; precision/recall vs labeled operator turns.                                 |
| T4  | Grounded-self-report faithfulness     | Agent claims ("tests pass", "I changed X") cross-checked against tool receipts; faithfulness rate metric, confabulation flagged from hashes not prose.            |
| T5  | Affect/tension proxy learning         | A tension proxy (retry storms, error bursts, correction density) predicts downstream behavior shifts. Proxy only — never affect ground truth.                     |
| T6  | Operator-pushback modeling            | Predict operator pushback/correction from prior context; labeled pushback turns as supervision.                                                                   |
| T7  | Self-model calibration                | Agent's own success predictions vs realized outcomes; Brier/ECE artifact on held-out tasks.                                                                       |
| T8  | Identity continuity                   | Same-agent state (scars, anchors, self-model) demonstrably persists and stays consistent across sessions; longitudinal receipts.                                  |
| T9  | Causal-intervention prediction        | Pre-registered expected-vs-observed deltas under control/treated/null paired replay (the Level-4 protocol).                                                       |
| T10 | Continual learning without forgetting | Ordered task streams; forgetting curves with a fixed re-eval set; no regression beyond budget.                                                                    |
| T11 | RSI-loop improvement signals          | A closed train→eval→train loop shows monotone improvement on a frozen yardstick, with the loop's own artifacts as receipts.                                       |
| T12 | AGI-grade SWE autonomy signals        | Resolution rate / partial-credit progress on graded, contamination-controlled SWE tasks at increasing horizon length.                                             |

A cell grade below measures **data readiness for the target's protocol**, not evidence achieved. Nothing in this table has been evidenced for any live system; the only Level-4 result in the program is "Level 4 of a hand-coded reference implementation inside its own harness" (ReferencePsyche), which validates the methodology, not any mind [VERIFIED].

---

## 2. Dataset × target matrix

Grades: **R** = READY (shipped, byte-deterministic adapter already emits PneumaTrace frames carrying the needed signal); **N** = NEAR (signal present in local columns, adapter design clear, no heavy joins); **F** = FAR (signal derivable only via nontrivial derivation, joins, unzipping, labeling, or privacy prework); **—** = NONE (no usable signal).

| Dataset (local rows)         | T1  | T2  | T3  | T4  | T5  | T6  | T7  | T8  | T9  | T10 | T11 | T12 |
| ---------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| swe-gym (81,338)             | R   | R   | —   | F   | F   | —   | N   | —   | —   | N   | N   | R   |
| swe-bench (22,962)           | F   | F   | —   | —   | —   | —   | F   | —   | —   | F   | F   | N   |
| swe-bench-pro (2,924)        | F   | F   | —   | —   | —   | —   | F   | —   | —   | F   | —   | N   |
| multi-swe-bench (10,399)     | F   | F   | —   | —   | —   | —   | F   | —   | —   | N   | F   | N   |
| swe-chat (≈5.83M parsed)     | F   | N   | N   | F   | F   | N   | F   | F   | —   | F   | —   | N   |
| dialogue-swe-bench (550)     | —   | F   | N   | N   | F   | N   | F   | —   | —   | —   | —   | F   |
| sec-bench-pro (1,264)        | F   | F   | F   | —   | —   | —   | —   | —   | —   | —   | —   | F   |
| swe-evo (32,211 rows loaded) | F   | F   | —   | F   | F   | —   | F   | —   | —   | N   | F   | N   |
| swe-mera (7,610, eval-only)  | —   | F   | —   | —   | —   | —   | F   | —   | —   | N   | —   | N   |
| swe-polybench (2,992)        | N   | F   | —   | —   | —   | —   | —   | —   | —   | F   | —   | N   |

Read-across facts the matrix encodes:

- The **T9 column is entirely NONE**. No static dataset can evidence causal-intervention prediction; see §5.
- The **T8 column has one FAR and nine NONEs**. Identity continuity needs longitudinal same-agent data that does not exist in any downloaded corpus.
- The only **R** cells sit on swe-gym because the two shipped adapters both consume swe-gym subsets. R means the frames exist and are byte-deterministic; the _learning_ on top of them is [PLANNED] in every case.
- Human-interaction targets (T3, T4, T6) concentrate in swe-chat and dialogue-swe-bench, and nowhere else. dialogue-swe-bench pushback is **simulated** (user-simulator turns); swe-chat pushback is real humans behind a PII gate.

---

## 3. Per-dataset detail

Privacy classes used below: **P0** = benchmark metadata, public OSS content, no natural-person focus beyond public commit identifiers embedded in diffs/issue text; **P1** = OSS contributor identifiers structurally present (usernames, emails in dedicated columns); **P2** = real human interaction data behind a contact-info gate — treat as a PII corpus; **P3** = dual-use security content with an execution prohibition.

### 3.1 swe-gym — `C:\pneuma-data\raw\swe-gym` (81,338 rows, 1.24 GB, 19 files)

- **Signal.** Nine pinned HF subsets. Task pools: SWE-Gym full task table (2,438), SWE-Gym-Lite (230), SWE-Gym-Raw (64,689 across 6 parquet shards). Trajectories: OpenHands-Sampled (6,055 rows with `resolved` labels and full tool-call messages — the Phase 3.1 source), OpenHands-SFT (491, success-only), OpenHands-Verifier (5,272: mixture 2,636 / off-policy 886 / on-policy 1,750, with resolved labels), MoatlessTools agent/verifier JSONL (2,163). Codebase-Index-Lite for repo structure. FAIL/PASS_TO_PASS fields are **test-id lists, not executed results** (no Docker built locally) [VERIFIED, manifest `known_issues`].
- **What is READY.** T12: 230 task-only + 6,055 trajectory-bearing PneumaTraces with outcome labels. T1/T2: shipped AgentTraceFrames carry observable-only tool names, args digests, output digests+lengths, lexical error markers, retry counts, and strategy switches — the raw material for scar motifs and verification-pressure supervision [VERIFIED]. No estimator has consumed them [PLANNED].
- **PneumaTrace extension needed.** Verifier/SFT ingestion needs a per-candidate verdict extension to the trajectory block (on/off-policy label + resolved verdict per sampled candidate); Moatless JSONL needs a separate parser. Any new cognition-bearing frame must satisfy the anti-fake-cognition gate (`envelope.consistency_errors`: agent_trace frames ⟺ trajectory block ⟺ `has_trajectory`) [VERIFIED gate exists].
- **Leakage/contamination.** Repo-level overlap with other local corpora is visible in sample IDs alone: swe-gym samples include `conan-io__conan-12397`, `iterative__dvc-3576`, `pandas-dev__pandas-51605`; swe-evo builds on conan/dask/dvc/modin/scikit-learn; swe-bench train includes large Python OSS repos. **Instance-level overlap between swe-gym and swe-bench-family repos has never been computed locally** — a repo+commit join is a mandatory pre-split check before any training run. Trajectories were generated by OpenHands agents whose underlying LLMs likely saw these repos in pretraining (external prior, untested locally).
- **Privacy.** P0/P1: Phase 3.1 redaction removed 103 emails, 4 AWS keys, 16 assigned secrets from task texts [VERIFIED]; raw trajectory text never enters frames (digests only).

### 3.2 swe-bench family — `C:\pneuma-data\raw\swe-bench` (22,962 rows, 8 parquet)

- **Signal.** train 19,008 / test 2,294 / dev 225, Lite 323, Verified 500, Multimodal 612. Columns per dossier: problem_statement, hints_text, gold `patch`, `test_patch`, FAIL_TO_PASS/PASS_TO_PASS, repo, base_commit, version. Gold-patch-only: no agent failures, no dialogue, no process signal.
- **Extension needed.** None beyond the swe-gym-lite pattern (world+governance, `has_trajectory=false`), plus one new envelope-level **contamination-flag field** (see leakage) that all task-only adapters should share.
- **Leakage/contamination.** The canonical contaminated benchmark: pre-2024 public GitHub issues/PRs, so presence in modern LLM pretraining corpora carries a high external prior (not testable locally); dossier records ~1/3 of Verified instances with solution leakage in issue text (arXiv 2512.10218) and ~31% weak test oracles with 28.6% of "passing" patches judged incorrect (arXiv 2410.06992) [VERIFIED, manifest `known_issues`]. Externally verified 2026-07-07 (adversarial multi-source research pass): SWE-Bench+ (arXiv:2410.06992) — 32.67% solution leakage, 31.08% weak-test passes, SWE-Agent+GPT-4 resolution 12.47%→3.97% after filtering; the SWE-Bench Illusion memorization study (arXiv:2506.12286, NeurIPS 2025) — models identify buggy file paths at up to 76% from issue text alone on SWE-Bench repos vs ≤53% elsewhere, ~2× verbatim 5-gram reproduction; and OpenAI's Feb 2026 audit — 59.4% of hard instances materially flawed, cross-provider verbatim gold-patch reproduction, leading OpenAI to stop reporting SWE-bench Verified. Standing rule for this program: SWE-bench-family numbers are training/breadth substrate only, never a headline capability metric; contamination-resistant scoring routes through swe-bench-pro/swe-mera slices. Also the overlap hub: dialogue-swe-bench is built directly on SWE-bench Verified (same instance IDs), and swe-gym/swe-evo share repos. Any T12 number quoted from this dataset without a contamination flag is status inflation.
- **Privacy.** P0 (public OSS; contributor names inside diffs/issue text only).

### 3.3 swe-bench-pro — `C:\pneuma-data\raw\swe-bench-pro` (2,924 rows incl. unofficial CSV mirror; public split = 731 instances)

- **Signal.** problem_statement + requirements + interface text, gold patch, test_patch, fail_to_pass/pass_to_pass, repo_language, dockerhub_tag execution refs. Held-out (12 repos) and commercial (18 repos) splits are unavailable **by design** — a genuinely private yardstick exists upstream that we cannot contaminate.
- **Extension needed.** Same task-only pattern; requirements/interface map naturally into the world frame; dockerhub_tag belongs in governance as an execution-grounding pointer.
- **Leakage/contamination.** Built to resist contamination (post-cutoff/private repos); the public split is the weakest third of that protection. Contextbench mirror has duplicate files and inconsistent metadata — adapter must ingest only `ScaleAI/SWE-bench_Pro` (pinned SHA `7ab5114...`). Note: 2,924 local rows double-count the mirror; canonical count is 731.
- **Privacy.** P0.

### 3.4 multi-swe-bench — `C:\pneuma-data\raw\multi-swe-bench` (10,399 rows loaded, 25.8 GB, 162 files)

- **Signal.** Curated eval (1,632 instances, 7 languages, no Python), mini (400, 50/lang × 8), Multi-SWE-RL (~24 GB rolling RL corpus with date-range snapshots, adds Python), and `_trajs` (4.7 GB of agent-rollout **ZIP archives, unextracted**). Executed outcome fields exist (run_result / fix_patch_result / test_patch_result; p2p/f2p/s2p), unlike swe-bench's id-lists.
- **Extension needed.** Language field in world frame; executed-outcome verdicts in governance/outcome frames; a zip-extraction provenance block for `_trajs`; RL snapshots need a date-window field to build ordered streams (T10 NEAR rests on this).
- **Leakage/contamination.** Same public-GitHub pretraining prior; license metadata inconsistent (card "other" vs README CC0, upstream repo licenses apply); rolling corpus — counts drift, pin the recorded SHAs. Cross-language transfer claims must control for per-language repo overlap with swe-polybench (Java/JS/TS).
- **Privacy.** P0/P1 (commit metadata inside patches).

### 3.5 swe-chat — `C:\pneuma-data\raw\swe-chat` (12.79 GB; parquet 2,732,252 rows + transcripts 3,098,007 records in 5,850 files)

- **Signal.** The only real-human-operator corpus. `conversations.parquet` 2,692,480 rows, of which only 104,166 are `is_conversational=true` (1.79M `role='metadata'`, 1.32M `turn_type='progress'`); ≈77.5k user turns, ≈53.6k assistant turns, ≈356k tool_use, ≈408k tool_result. `sessions.parquet` 5,851 sessions with `agent_changes`, `file_attribution`, `agent_percentage`. `commits.parquet` 14,459 commits but only **25** `is_agent_author=true` — commit-level authorship signal is thin; session-level attribution is the usable lane. `prompt_pushback` / `prompt_intent` columns exist — direct T3/T6 supervision. `checkpoints.parquet` 13,406; `repositories.parquet` 205. 3 transcripts non-parseable, 4 NUL-truncated at source [VERIFIED, manifest].
- **Extension needed.** The largest schema surface of any dataset: operator-turn frames (role, pushback label, intent label), authorship-attribution fields, session/checkpoint linkage, and a mandatory redaction-provenance block. All text must enter as digests per the Phase 3.1 observable-only policy.
- **Leakage/contamination.** Sessions run over 200+ public repos; conversational content itself is post-cutoff and low pretraining risk, but embedded diffs inherit the usual prior. Bigger risk is **methodological**: transcripts are Claude-Code-style sessions, so any 9to5/Pneuma model trained here learns a specific product's interaction grammar, not operator behavior in general.
- **Privacy.** **P2 — hard gate.** Real PII in dedicated columns: `author_email`, `author_name`, `github_username` non-null in commits; source is HF contact-info-gated, odc-by; the global inventory's `gated_or_unavailable: []` is misleading (data local, source gated). **No corpus-wide PII scan has ever been run over swe-chat**; pneuma-lab's deterministic redaction (Phase 3.1) exists but has only ever been applied to swe-gym task texts. PII scan + redaction audit is a hard precondition to any adapter (queue item Q6).

### 3.6 dialogue-swe-bench — `C:\pneuma-data\raw\dialogue-swe-bench` (550 rows: test 500 + ablation 50)

- **Signal.** Turn-by-turn agent↔user-simulator dialogues over SWE-bench Verified instances: NL dialogue turns, persona descriptions, draft→full problem_statement deltas, difficulty tags, final patch graded via test_patch, F2P/P2P lists. Dossier notes ~44% correction rate — direct, small, clean supervision for clarification/authority behavior. Cheapest path to first T3/T4/T6 frames.
- **Extension needed.** Dialogue/operator-turn extension (turn role, correction marker, persona digest, ambiguity-stage marker). Same extension swe-chat needs, prototyped here at 1/10,000 the volume and zero PII.
- **Leakage/contamination.** Built on SWE-bench Verified → inherits its full contamination profile, including the ~1/3 solution-leakage rate; instance IDs (`astropy__astropy-14182`, `django__django-11099`, …) literally are SWE-bench IDs. Provenance caveats: HF account "Brendan" unconfirmed as official, no license tag, official GitHub repo is a placeholder [VERIFIED, manifest].
- **Privacy.** P0 — **user turns are simulated**, not human. Every T3/T6 result from this dataset must carry a "simulated operator" qualifier; it calibrates machinery, not human behavior.

### 3.7 sec-bench-pro — `C:\pneuma-data\raw\sec-bench-pro` (1,264 rows, 13.4 MB, 5 files)

- **Signal.** SEC-bench (OSS+CVE sanitizer-crash corpus) + Seed + SEC-bench-Pro (183 rows, V8/SpiderMonkey). Fields: instance_id, project, error_type, description, sanitizer_report/bug_report text, Dockerfile/build_sh refs, fix patch diffs, CVE lineage. Downloaded **metadata only**; no PoC has been opened or executed [VERIFIED, dossier].
- **Extension needed.** A dual-use governance class: no-exec flag in governance frames, redaction of exploit-adjacent detail before any text-derived feature, CVE-lineage linkage for cross-instance scar motifs.
- **Leakage/contamination.** CVE writeups are heavily represented in pretraining corpora (external prior). Some rows are VRP-bounty adjacent.
- **Privacy/safety.** **P3.** Standing restriction: metadata/structure only; never run PoCs or reproduce exploits. Description/bug_report/patch fields must be gated/redacted before pass-through.

### 3.8 swe-evo — `C:\pneuma-data\raw\swe-evo` (32,211 rows loaded, 8.31 GB, 31,647 files)

- **Signal.** 48-task core benchmark (release-note/SRS prompts, repo snapshots, avg 874 pytest tests/instance) plus large OpenHands/SWE-agent `infer_logs` + `llm_completions` — long-horizon multi-file third-party trajectories (~21 files touched per task). Outcome is the partial-credit **Fix Rate** (proportion of F2P fixed iff all P2P green, else 0) plus binary resolved. 7 Python projects incl. conan, dask, dvc, modin, scikit-learn.
- **Extension needed.** Long-horizon linkage: episode chaining across a repo's release versions (T10 NEAR rests on this) and a partial-credit outcome field (Fix Rate) in the outcome frame; the third-party log format needs a new parser distinct from the OpenHands-Sampled parquet path — that parser cost is why trajectory-dependent cells grade FAR, not NEAR.
- **Leakage/contamination.** Direct repo overlap with swe-gym (conan, dvc at minimum, visible in swe-gym sample IDs) and plausibly swe-bench train; instance-level joins never computed. Namesake trap: `zhiyuanhucs/SWE-EVO-LongChain-50*` is a different project, not a mirror [VERIFIED, dossier].
- **Privacy.** P0/P1.

### 3.9 swe-mera — `C:\pneuma-data\raw\swe-mera` (7,610 rows: full 3,539 / lite 750 / multilang 3,319 / dev 2)

- **Signal.** Dynamic anti-contamination benchmark with **freshness timestamps** — dated task cohorts mined after model cutoffs. problem_statement/hint_text, patch/test_patch, F2P/P2P, repotest verdict harness.
- **Extension needed.** Task-only adapter + a freshness/date field in governance so calibration evals can be windowed by cohort date.
- **Leakage/contamination.** This is the program's contamination **control**, not a contamination risk — provided the standing restriction is honored: **HELD-OUT EVALUATION ONLY, never training motifs** [VERIFIED, manifest restriction]. Counts drift; pin SHA `4aa9e55...` + fetch date. Ignore the padamenko mirror.
- **Privacy.** P0.

### 3.10 swe-polybench — `C:\pneuma-data\raw\swe-polybench` (2,992 rows: full 2,110 / 500 / Verified 382)

- **Signal.** 4 languages (Java/JS/TS/Python), task_category (Bug Fix / Refactoring / Feature), and **AST-level metrics** (num_class/func_changes, modified_nodes) — the only dataset with native structural-risk columns, i.e., a second, independent source of scar-motif supervision (refactor-risk motifs) next to swe-gym's behavioral one. CSV metadata only; source trees external.
- **Extension needed.** Task-only adapter + AST-metric fields (structural-risk block) and task_category in governance.
- **Leakage/contamination.** Public GitHub, same pretraining prior; Verified count discrepancy (382 local vs 394 documented); GitHub HEAD not pinned to paper release [VERIFIED, manifest].
- **Privacy.** P0.

---

## 4. Adapter build queue (evidence-value per engineering cost)

Value = number and uniqueness of matrix cells moved toward READY; cost = rows × format novelty × join depth × privacy prework. Q0a/Q0b are shipped and listed for completeness. Committing the uncommitted Phase 3.1 working tree (HEAD = b3102c6 has only the Phase-3 adapter) is a **zero-cost prerequisite that outranks everything below it** — R grades currently rest partly on uncommitted code [VERIFIED hygiene issue].

| #   | Item                                                            | Cost                                                                                                              | Value               | Justification                                                                                                                                                                                                                 |
| --- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q0a | swe-gym-lite task adapter                                       | —                                                                                                                 | —                   | Shipped, committed [VERIFIED].                                                                                                                                                                                                |
| Q0b | openhands-sampled trajectory adapter                            | —                                                                                                                 | —                   | Shipped, uncommitted [VERIFIED]. Commit first.                                                                                                                                                                                |
| Q1  | OpenHands-Verifier + SFT extension                              | Low (same parquet family; reuse `adapters/trajectory.py` + `openhands_sampled.py` machinery; +5,763 trajectories) | High                | Cheapest new frames in the program; adds per-candidate verdicts (on/off-policy × resolved) → T7 data-ready, densifies T1/T2 corpus by ~2×.                                                                                    |
| Q2  | dialogue-swe-bench adapter                                      | Low (550 rows, 2 parquet)                                                                                         | High, unique        | First operator-interaction frames ever; unlocks T3/T4/T6 prototyping with zero PII; the dialogue-frame extension it forces is the same one swe-chat needs later. Simulated-operator caveat mandatory.                         |
| Q3  | swe-bench + swe-bench-pro task adapter with contamination flags | Low-medium (25.9k rows, same shape as Q0a; new envelope contamination-flag field)                                 | Medium-high         | T12 breadth (canonical yardstick), T10 stream substrate; the contamination-flag field designed here is reused by every later task adapter. Must ship with the swe-gym↔swe-bench instance-overlap join (currently uncomputed). |
| Q4  | swe-polybench adapter                                           | Low (3 CSVs)                                                                                                      | Medium              | Second independent T1 source (AST refactor-risk motifs) + multilingual T12; guards against swe-gym motif overfitting.                                                                                                         |
| Q5  | swe-mera held-out eval pack                                     | Low (5 parquet, task-only)                                                                                        | Medium, unique role | The program's only contamination-controlled, freshness-dated eval substrate for T2/T7/T12 calibration protocols. Eval-only restriction enforced in adapter metadata.                                                          |
| Q6  | swe-chat corpus-wide PII scan + redaction audit                 | Medium (12.8 GB, 3.1M transcript records; redaction code exists, scan does not)                                   | Gate-opener         | Not an adapter — a hard precondition. No PII scan has ever run over swe-chat; P2 class forbids any frame emission before this.                                                                                                |
| Q7  | swe-chat sessions/pushback adapter                              | High (transcripts↔sessions↔commits joins; dialogue frames; digest-only text; odc-by + gated-source terms)         | Highest unique      | The only real-human T3/T6 supervision in existence locally (prompt_pushback, prompt_intent, 77.5k user turns, 5,851 attributed sessions). Ordered after Q6 by necessity, not by value.                                        |
| Q8  | multi-swe-bench task tables (+mini) adapter                     | Medium (executed-outcome fields, language field)                                                                  | Medium              | Multilingual T12 and date-windowed T10 streams with _executed_ verdicts — stronger governance frames than swe-bench's id-lists.                                                                                               |
| Q9  | swe-evo trajectory parser                                       | High (31,647 files, new third-party log format, episode chaining)                                                 | High                | Long-horizon T12 (multi-file, partial-credit Fix Rate) and version-chained T10 — the only long-horizon trajectory source. Expensive parser is the whole cost.                                                                 |
| Q10 | multi-swe-bench `_trajs` unzip + parse                          | High (4.7 GB ZIPs, unknown inner formats)                                                                         | Medium              | More third-party trajectories for T1/T2 breadth across 7 languages; do after Q9 proves the third-party-trajectory pattern.                                                                                                    |
| Q11 | sec-bench metadata adapter                                      | Medium code, high policy cost (dual-use gating design first)                                                      | Low-medium          | T1 (CVE-lineage motifs) and security-flavored T2/T3 — but the no-exec restriction caps its evidence value; last on purpose.                                                                                                   |

Queue-level rule: every adapter must (a) be byte-deterministic with a twice-run hash check and a golden fixture, matching the two shipped adapters' bar; (b) pass the anti-fake-cognition envelope gate; (c) record source revision SHA + fetch date from the manifests; and (d) declare its contamination flags and privacy class in trace metadata. Any adapter that emits cognition-bearing frames from third-party agents must label the agent provenance explicitly — OpenHands/SWE-agent/Moatless trajectories are evidence about _those_ scaffolds, not about Pneuma or 9to5.

---

## 5. Targets no local dataset can evidence

Stated plainly so nobody mistakes data volume for evidence coverage.

1. **T9 — causal-intervention prediction: no dataset, period.** The protocol requires live control/treated/null paired replay with pre-registered deltas. All 10 corpora are observational. The only existing implementation is the Level-4 harness over ReferencePsyche (`src/pneuma_lab/interventions/runner.py`, `src/pneuma_lab/replay/harness.py`), which is a hand-coded toy co-designed with its own fixtures — methodology validation only [VERIFIED]. Evidencing T9 for a real system requires live Pneuma-instrumented runs, and today **no code path connects adapter output to the ReplayHarness** [VERIFIED gap]. [PLANNED]
2. **T8 — identity continuity: needs longitudinal same-agent data that does not exist.** swe-chat checkpoints give within-session continuity mechanics at best (graded FAR with that caveat). The nearest real substrate is 9to5's `state/experience.db` (37 MB, 3,534 runs, 7,900 subtasks, 161 reflections) [VERIFIED], but there is ZERO Pneuma integration and no exporter from 9to5 artifacts to Pneuma frames [VERIFIED]; `psyche.db` has never existed on disk in production, and pneuma-lab's own `reset()` clears scars — no cross-run persistence [VERIFIED]. A 9to5→PneumaTrace exporter is the single highest-value missing adapter in the whole program and it targets a repo, not a dataset. [PLANNED]
3. **T11 — RSI-loop improvement signals: datasets supply substrate, never the signal.** SWE-Gym SFT/Verifier data and Multi-SWE-RL are reward/verifier _inputs_ to an improvement loop; the evidence is the loop's own artifacts over time. 9to5's RSI substrate is dormant: LoRA/DPO trainer has never produced an adapter (adapters table = 0 rows, no GPU), lessons = 2, prompt_variants = 1, conviction.db = 0 rows [VERIFIED]. Until a loop closes, every T11 cell above means "fuel present," not "fire observed." [PLANNED]
4. **T7 — self-model calibration: half-missing by construction.** Datasets provide outcomes; the _self_ predictions must come from a live agent. All T7 grades above denote eval-substrate readiness only. [PLANNED]
5. **T4 — grounded-self-report faithfulness, the strong form.** Static claim-vs-receipt checks are derivable from trajectories (hence FAR grades), but the harness-grade form — reports that _track perturbations_ under intervention with confab risk ≤ 0.2 — is intervention-dependent and collapses into the T9 gap. [PLANNED]
6. **T5 — affect: no dataset contains affect ground truth and none ever will.** Tension proxies are learnable; calling them affect is prohibited by program honesty rule 3. Permanent proxy status, not a data gap that acquisition can close.

Bottom line: the corpus is strong on T1/T2/T12 raw material, adequate-with-work on T3/T6/T7/T10, thin on T4/T5, and structurally silent on T8/T9/T11. The three silent targets are exactly the ones that distinguish this program from benchmark chasing, and all three route through live instrumented runs (Pneuma harness runs, a 9to5 exporter, a closed training loop) rather than through any further downloading.

# Resampling Null — design brief

## 4.1 SWE-bench-Live MultiLang roster

- Frozen inputs: harness `microsoft/SWE-bench-Live` `70ec57e852e3f2d195790fe71f553e272c691833`; dataset `SWE-bench-Live/MultiLang` `608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b`; RepoLaunch `microsoft/RepoLaunch` `7735b1e7363dd3bbc69bd0ef80db646a2ae391fd`.
- Surface: 743 tasks, 381 literal repo strings, 380 current GitHub IDs, 8 splits. `vmware-tanzu/velero`/`velero-io/velero` are one root lineage; 6 names redirect after renames. Harness/dataset/RepoLaunch metadata are MIT; upstream repos/base commits/container contents are not thereby licensed.
- Primary endpoint: every registered `FAIL_TO_PASS` and `PASS_TO_PASS` check passes exactly once in a clean endpoint image; missing/skipped/unparsed/duplicate checks fail closed.
- Diagnostic proxy: 554 tasks/278 root lineages across permissive, non-archived current metadata; split proxy tasks/lineages: C 24/9, C++ 18/14, C# 75/26, Go 123/77, Java 85/44, JavaScript 78/35, Rust 73/28, TypeScript 78/45. It is not eligibility evidence.
- Eligibility: permissive base-commit license; immutable mirrored `linux/amd64@sha256` OCI image; hardened offline adapter and isolated parser; 3 independent fresh base/gold pairs with exact outcomes; resource admission; complete provenance; at most one task per canonical root lineage. All 743 source image references are currently untagged/digest-free and thus ineligible as-is.
- C120 quotas: `9/14/16/17/16/16/16/16` for C/C++/C#/Go/Java/JavaScript/Rust/TypeScript. Needs 2 disjoint pilot lineages per split plus fixed reserves; C and C++ require at least 11 and 16 qualified lineages before reserves, versus proxy 9 and 14. Status: `FEASIBILITY_NO_GO` until the audit satisfies `eligible_s >= C120_quota_s + 2 pilot_s + fixed_reserve_s` for every split.
- C160: `FEASIBILITY_NO_GO` currently; base allocation 12/split, remaining 64 by Hamilton largest remainder over post-pilot/post-reserve eligibility (canonical split tie order). C needs at least 14 qualified lineages before reserves. Same per-split eligibility gate applies.
- One sealed manifest freezes accepted/rejected rows, 16 pilots, nested C120, possible C160, reserves, groups, ranking/order. Execution/outcome failure is adverse or whole-tier no-go, never redraw.

## 4.2 τ³-bench objective text subset

- Frozen source: `sierra-research/tau2-bench`, tag `v1.0.1` object `b711c1ead46f55111bf765cf44d5da8bacc2d28c`, peeled commit `fc0055dc4e0a316c3f83133267fbd6faaa770992`; MIT; Python `>=3.12,<3.14`. Installed version text is non-authoritative (`pyproject` 1.0.1 vs pinned editable lock entry 1.0.0).
- Objective pool: 261 definitions; confirmatory pool 252. Airline 50; telecom base 114 (MMS 49, mobile-data 36, service 29); banking knowledge 88 DB tasks (9 ACTION-only excluded). Retail, voice, API retrieval, all `NL_ASSERTION` and all LLM evaluators are excluded.
- Primary endpoint/configuration: `EvaluationType.ALL`, `CommunicationMode.HALF_DUPLEX`, `strict_replay=True`, evaluator network calls `0`. Official primary retains 20 service `ACTION + ENV_ASSERTION` tasks; separate strict secondary is requestor-aware, exact action-name and canonical argument-dictionary matching, and does not alter primary reward.
- Rosters: C120 = 40 airline/40 telecom/40 banking; preferred C160 = 44/58/58. Nine disjoint pilots: 3/domain; telecom exactly one MMS, one mobile-data, one `ACTION + ENV_ASSERTION` service. Telecom C120 quotas MMS/mobile/service `17/13/10` (service `7` action+env, `3` env); C160 `25/18/15` (`10/5`).
- C160 eligibility requires >=47 qualified airline tasks across 3 pilots + 44 confirmation and <=3 ordered airline reserves; a fourth reserve or >3 airline qualification losses is `FEASIBILITY_NO_GO` without redraw.
- Banking is fixed to BM25 (`top_k=10`, `rank-bm25==0.2.2`, `numpy==2.3.5`), specified document/tree digests and deterministic ordering/ties; no reranker/grep/dense embedding/shell/API/sandbox/golden retrieval. Simulator: local greedy `Qwen/Qwen3.5-9B` `c202236235762e1c871ad0ccb60c8ee5ba337b9a`, seed-receipted and cold-start byte-identical; deterministic telecom draft-bill generation replaces UUID behavior.
- Candidates must pass exact data/reward parsing, snapshot/restore equality, 3-process gold endpoint equality, strict-action fixtures, BM25 and simulator reproducibility, off-policy deterministic-ID fuzzing, leakage audit, and resource admission. HMAC-ranked eligibility manifest freezes pilots, tiers, reserves; controller task IDs never enter prompts, worker env, or paths.

## 4.3 Model subject and serving stack

- Primary: `Qwen/Qwen3.6-35B-A3B-FP8`, revision `95a723d08a9490559dae23d0cff1d9466213d989`, Apache-2.0, official block-wise FP8, text-only thinking-mode tool use, candidate `vllm==0.19.0`.
- Flags: `--language-model-only`, `--reasoning-parser qwen3`, `--enable-auto-tool-choice`, `--tool-call-parser qwen3_coder`; no multi-token/speculative decoding. Prefix cache stays off unless parity proves frozen-seed byte identity.
- Seal image/CUDA/driver/PyTorch/vLLM source-or-wheel/tokenizer/template/parser/packet policy/pad-unit bytes after parity test. Package version alone is insufficient.
- Pre-pilot topology ladder: 1×L40S TP1 at 32,768; 1×L40S TP1 at 65,536; 2×L40S TP2 at 65,536; H100 94GB TP1 at largest validated <=131,072. FP8 weights ~34.9 GiB. Freeze largest OOM/tool/output-parity/p10-throughput passer; topology changes subject.
- BF16 replication is distinct: `Qwen/Qwen3.6-35B-A3B` `995ad96eacd98c81ed38be0c5b274b04031597b0`, ~67.0 GiB, planned Azure `Standard_NC48ads_A100_v4` 2×A100-80GB TP2. Local development subject: Qwen3.5-9B above. Never pool FP8/BF16.
- Tier-1 reproducibility gate: `VLLM_BATCH_INVARIANT=1`, fixed order/concurrency/topology/per-call seeds, identical repeated token IDs. Failure is topology/hour-table no-go; concurrency-one with `VLLM_ENABLE_V1_MULTIPROCESSING=0` needs new measurement, costing, hash, approval. No byte-identical mode = serving feasibility no-go; IID slots, no common-random-number claim.
- Arm-common sampling: SWE temp/top-p/top-k/presence/repetition `0.6/0.95/20/0/1`; τ³ `1.0/0.95/20/1.5/1`.

## 7.1–7.3 verifier and sham donors

- SWE REAL verifier: disposable prefix clone; packet may report per-check pass/fail, normalized compiler/assertion/runtime failure class, bounded log excerpt, regression status, resource/timeout status. It excludes test source, gold patch, future commits, unbounded traceback. Final grader reruns complete F2P/P2P in fresh digest-pinned image; public answer-bearing fields remain controller-only until unblind.
- τ³ REAL verifier: cloned prefix environment/transcript; packet reports eligible-component type and satisfaction, policy-safe reason code, relevant action/communication category, bounded current-state evidence. Expected finals/hidden answers and IDs, descriptions, ticket, criteria, gold actions/args, assertion values, required docs, DB hash/diff, issue metadata remain controller-only. No LLM/network primary verifier.
- Sham matching: deterministic constrained minimum-cost perfect matching, one donor from another eligible lineage per triggered task; no-trigger ITT units receive none. SWE match fields: language, runner/failure class, failure-count band, log-length band, different repo. τ³: domain, evaluator-component multiset, failure-count band, report-length band, different task and cross-family telecom where possible.
- Telecom same-family fallback is legal only if no cross-family exact candidate exists; `ACTION + ENV_ASSERTION` records `cross_family_component_match_unavailable`. Never relax component/domain/lineage/derangement/collision/token-parity gates. Empty focal candidate set = no-go, no redraw.
- Required matching: exactly one donor per focal and one focal per donor; no self/same-lineage edge; no two-cycle. Lexicographic objectives: minimize permitted telecom same-family fallbacks, then absolute finding-count difference, then normalized-report-token-count difference. Solver must return `OPTIMAL`.
- Ties use `HMAC-SHA256(K_donor, FRAME("donor-tie-v1", [task_id_i, task_id_d]))`; canonical candidate order is tie bytes then donor ID, and each first edge with an optimal completion is fixed, retaining all trials. Confirmation needs the pinned live backend/session; absent exact session in any triggered stratum fails before ledger creation. Synthetic fixtures use separately labeled cyclic-offset proof only.
- Packets deterministically truncate bounded evidence and add neutral padding so REAL and SHAM have exactly equal tokenizer length, with identical format/padding algorithm. Receipts bind focal/donor verifier digests, assignment/identifier-map/tokenizer digests, normalized findings, padding search, collision result; all are sealed pre-branch. Raw packets are encrypted; workers decrypt only their own opaque-slot packet in isolated guidance boundary, not available to analyst pre-unblind.

## 9.5 power and roster tier

- Pre-outcome deterministic P0 evaluates C120 and C160 only after eligible roster/group labels freeze; synthetic roster validates code/runtime only and cannot select tier. Frozen alternative: full-roster ITT `(tau_content, tau_excess) = (0.15, 0.15)` per benchmark.
- Nuisance grid per benchmark: `p0 ∈ {0.10,0.40,0.70}`, trigger `gamma ∈ {0.60,0.75,0.90}`, latent equicorrelation `rho ∈ {0,0.40,0.80}`; 729 SWE×τ³ cells. Triggered marginals: `p_R=p0+0.15/gamma`, `p_S=p_N=p_Z=p0`; all probabilities in `[0.10,0.95]`; `m_b=gamma*n_b` exactly.
- P0: 20,000 datasets/cell; Gaussian-max approximation validates worst 5 C160 cells against 2,000 full-multiplier outer datasets, requiring each gate-pass-rate difference <=0.01 and identical tier; otherwise full multiplier or authority-appropriate no-go.
- Required joint power >=0.80 across every alternative cell; familywise type-I <=0.05 across 3×729 null-boundary cells. One-sided Clopper–Pearson lower tail `0.05/729`; upper tail `0.05/2187`.
- Tier: C160 preferred, 160 tasks/benchmark; C120 minimum, 120 tasks/benchmark. Preliminary (non-registered) C120 planning: ~80% only near 17-point effect at discordance 0.40. Exact simulator/eligible roster failing minimum yields feasibility no-go; no smaller anecdotal tier.
- MDE: not specified as a registered numeric MDE; 17 points at discordance 0.40 is explicitly preliminary only.

## 9.6 verdict taxonomy

- `FEASIBILITY_NO_GO`: before outcomes, powered roster/runtime cannot complete.
- `PIPELINE_INVALID`: packet, snapshot, assignment, no-interference, grader, or differential-failure gate fails.
- `HARMFUL_OR_MISDIRECTING`: content or excess point estimate <= -0.05 and simultaneous upper bound < 0.
- `CAUSAL_CONTENT`: both co-primary contrasts plus every registered statistical/resolution/admissibility gate pass.
- `SHAM_PACKET_ONLY`: not causal content; `hat_tau_sham >= 0.05`, `> r95`, 3-family Holm sham p <=0.05, `L_sham>0`, and content fails >=1 finite-SE/sharp/lower/materiality/resolution/benchmark/sensitivity gate.
- `UNRESOLVED_RESAMPLING`: no earlier outcome verdict and a primary SE is invalid or co-primary estimate fails `delta_star`/`r95`.
- `RESAMPLING_CONSISTENT`: valid, resolved remainder; REAL gains fail registered inferential controls.
- All verdicts are publishable; none permits endpoint changes or deleting failed blocks.

## 10 pilot and confirmation separation

- Pilots are disjoint from confirmation/reserves: SWE 16 (2/language, unique repos); τ³ 9 (3/domain; telecom MMS, mobile-data, action+env service).
- Before pilots, one manifest seals accepted/rejected qualification, nonce/precommit/beacon/final-seed/ranking evidence, pilot roster, nested C120, eligible C160, all reserves. No pilot or outcome may replace/reorder tasks; a system failure repeats full pilot on the same roster under immutable incremented implementation generation or yields `FEASIBILITY_NO_GO`.
- Pilots validate mechanics, verifier/sham/detectability, trigger/flakiness/throughput/resources/budget—not efficacy for selection. Pilot efficacy is labeled/excluded and cannot select model, task, reserve, tier, endpoint, or analysis.
- After validation, seal implementations, frozen roster, commitments, matching/provider plan, analysis source/fixtures, cloud manifest, preregistration. Roster-bound completed `GO` P0 selects 120/160 before schedule seed reveal/prefixes. Confirmation seals prefixes/verifiers, assignment, packets, and analysis freeze before continuations; human sees completeness only. Bytes are encrypted and withheld from analysis authors until analysis hash/artifact completeness seal.

## 12 artifact and blinding contract

- Scientific record kinds (12): `resampling_study_manifest`, `resampling_prefix_schedule`, `resampling_prefix_receipt`, `resampling_assignment_ledger`, `resampling_packet_index`, `resampling_task_block`, `resampling_blinded_projection`, `resampling_analysis_freeze`, `resampling_analysis`, `resampling_power_report`, `resampling_unblind_receipt`, `resampling_artifact_root` (each mapped to its named `resampling-*.schema.json`).
- Raw streams/snapshots/patches/logs/binaries are hash-linked blobs under schema-valid parents, not standalone records. Artifact root recursively verifies refs, bytes/media/size, semantic ancestry, and selected-schedule coverage; dangling/conflicting/unlisted refs fail closed.
- Capability separation: power sees manifest authority/grid/topology only and no endpoint; schedule sees seed reveal/manifest/power final but no master key/verifier/arms/outcomes; assignment reads key only after prefix/verifier freeze and cannot read branch outcomes; workers get one opaque slot capability plus frozen snapshot/seed/caps, not arms/donors/ledger/other branches.
- Clear ledger is only in encrypted owner-only controller root, never shared with workers or analyst pre-unblind. Projection strips to success/prefix success/finite reward/infrastructure bit/resource counters; it forbids refs, paths, packets, grades, sources, arms, donors, keys, and hidden identities. Analyst gets sealed projection only.
- Unblind permit: only hash-gated unblinder gets projection + clear ledger and consumes single-use `UnblindSecretHandle`; it verifies commitment/context, derives only `K_unblind`, and recomputes framed permit HMAC over study ID, manifest, schedule, prefix, ledger, projection, analysis freeze, expected task count before ledger parsing. Analyst gets no unblinding key until source/synthetic expected outputs seal. Outcome-tainted contexts cannot alter confirmatory code, filters, or verdict rules.
- First post-unblind run is record; corrections append a deviation/new artifact, never overwrite.

## 13.3 durable boundary and interruption contract

- After each completed model response/tool result, content-address checkpoint: transcript/token IDs, subject/simulator seeds, tool receipt, SWE diff + mutable workspace state, τ³ DB/simulator/transcript/RNG, runtime/container/image/model/tokenizer digests, cumulative token/call/wall/cost counters.
- Upload to S3/Blob, hash-verify, then atomic completion marker before next boundary; local marker is insufficient. Resume retains task/arm/sample/seed schedule, appends attempt receipt, and must match prior boundary receipt. Mismatch invalidates the entire four-arm block; no silent arm replacement.
- KV state is rebuilt from token IDs. Restart/replacement/provider/topology/kernel changes are not presumed reproducible. Byte-equality gate requires `VLLM_BATCH_INVARIANT=1`, frozen order/concurrency and seeds; failure is Tier-1 no-go. Concurrency-one/offline needs new measured, recosted, hashed, approved manifest; no CRN claim.
- Independent reservation/watchdog meters compute/storage/log/network/API billing dimensions and remains through verified deletion or fully reserved retention; alerts are advisory, never stop authority. No fresh watchdog lease: no new model/API call.

## 14 costed execution tiers

- Cap hours/task: SWE `5×1.0=5.0` subject-hours; τ³ `5×0.5=2.5`. C120: SWE 600/150 AWS instance-hours, τ³ 300/100, total **250**. C160: 800/200, 400/133.3333, total **333.3333**. Four SWE or three τ³ subjects share AWS node (fourth τ³ GPU is simulator).
- Fixed allowances: Tier-2 AWS S3 $46 + gp3 $160 + ECR/log/request/egress $200 = **$406**; Tier-3 incremental AWS **$506**; Tier-3 Azure Blob $41.60 + other $300 = **$341.60**; Tier-1 infra $20 AWS/$30 Azure.
- Tier 0: $0 expected/reserved. Tier 1: AWS 12h g6e OD; Azure 8h H100 OD + 8h NC48 A100 OD + 16h A10 OD; expected **$341.72**, reserved **$487.58**.
- Tier 2-C120: 250 g6e OD h + AWS infra + OpenAI $200 + Anthropic $50; expected **$3,279.16**, reserved **$4,590.74**. Tier 2-C160: 333.3333 h, expected **$4,153.55**, reserved **$5,902.32**.
- Tier 3: disjoint 80-task/benchmark AWS expansion; fixed 24-task/benchmark H100/BF16 subset; OpenAI $1,500, Anthropic $350. AWS `500/3` = 166.6667 instance-hours; each Azure subject slice 180 VM-hours; τ³ simulator total 120 A10 h. Expected **$5,014.23** (AWS OD/current Azure Spot); conditional all-eligible-Spot **$4,009.96**; reserved **$9,764.78**.
- Cumulative rounded kill caps: Tier 1 $500; Tier1+C120 $5,100; Tier1+C160 $6,400; Tier1+C120+T3 $14,900; Tier1+C160+T3 $16,200. Provider caps under full C160 plan: AWS $9,100; Azure $5,100; OpenAI $1,700; Anthropic $400.

## 16 kill and pivot rules

- Stop/narrow before confirmation if exact SWE/τ³ C120/C160 pilot+confirmation+reserve roster gates fail; mutable/digest-free image, isolation escape, evaluator network call, or missing registered component occurs; trigger opportunity <60%; gold/regression flakiness >2%; any arm-visible snapshot byte/token/state differs; REAL correctness/SHAM collision or detectability gate fails; differential infrastructure failure >2 percentage points; p10 cannot finish by 2026-08-18; P0 simulator C120 power <80% for target effect; or verified eligible funding misses exact worst case.
- Zero-credit pivot: methods-and-feasibility paper using validated local controller, synthetic recovery, existing G1 negative evidence, and clearly labeled small 9B pilot—not the powered cross-benchmark result.
- First robustness fallback: Terminal-Bench 2.1 `5c8eadf1f393183288fa08b8f73ca9a469cc5e00` (objective, Apache-2.0, 89 tasks); not primary because unit ceiling/frontier saturation weaken power.

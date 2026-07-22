# Novelty and provenance ledger

**Cutoff:** 2026-07-22

**Scope:** sources actually cited by the innovation proposal

**Interpretation:** absence claims are bounded by the primary-source searches and fetched records below. They are not claims that an unindexed manuscript cannot exist.

## Idea-level novelty ledger

| ID | Closest verified prior work | What prior work already publishes | What remains ours | Why the residual claim is not the prior claim | Novelty confidence |
|---|---|---|---|---|---|
| I1 | SteeM [@huang-etal-2026-controllable]; MemCon [@jiang2026controlled]; SAMem [@wang-etal-2026-samem]; coding-memory studies [@zhao-etal-2026-demystify; @lindenbauer-etal-2025-knowledge] | Controllable memory reliance; learned memory-operation policies; state-aligned retrieval; positive and negative effects of memory in coding agents. | A randomized Pareto frontier over the dimensionality, persisted precision, update degrees, and latency of a causally active state, with a minimal-sufficiency estimand for recurring SWE harm. | The prior work optimizes or compares memory mechanisms. It does not identify the least-complex machine-addressable state that survives fixed-opportunity causal interventions against a selected scalar winner. | Medium-high |
| I2 | Negative controls [@lipsitch2010negative; @shi2020negative]; experience-following/error propagation [@xiong-etal-2026-memory] | Negative controls detect noncausal pathways; retrieved experiences can propagate errors or induce behavior by similarity. | A directed exposure-motif by opportunity-motif causal response matrix with diagonal benefit and off-diagonal equivalence. | Existing controls are global, observational, or retrieval-centric. The proposed matrix makes address specificity itself the estimand in an executable agent experiment. | High |
| I3 | Interchange intervention training and causal abstraction [@geiger2022inducing; @geiger2025causal]; Memory Transplants [@feng2026memory] | Source-to-base neural-state swaps; a formal causal-abstraction language; architecture/content transfer across code-to-math. | Cross-history swaps of Pneuma's explicit state at the same current SWE checkpoint and candidate tuple, with coordinate-level donor predictions and executable outcomes. | Memory Transplants changes domain, architecture, or stored content and measures transfer. The proposal holds the current decision fixed and tests whether behavior follows a donor history's causal controller state. | High |
| I4 | LoCoMo-Plus [@li-etal-2026-locomo-plus]; LifelongAgentBench [@zheng2025lifelong]; memory-update degradation [@zhang2026faulty] | Long-context latent-constraint memory; interdependent lifelong task streams; degradation under repeated consolidation. | A randomized treatment-by-task-lag curve after common verified failure exposure with the target opportunity and carrier fixed. | Prior horizons are benchmark properties or update sequences, not randomized causal lag doses for recurrence avoidance. | High |
| I5 | LoCoMo-Plus [@li-etal-2026-locomo-plus]; AgentAbstain [@liu2026agentabstain]; experience-faithfulness interventions [@zhao2026selfevolvers] | Cue-trigger memory evaluation; controlled paired action/abstention perturbations; causal dependence on raw or condensed experience. | A cue-by-prior-failure-exposure interaction on pre-action protective policy mass in executable SWE tasks with a hidden numeric carrier. | None of the fetched designs crosses verified prior failure with a matched current cue while measuring the acting policy before execution. | Medium-high |
| I6 | Retrieval/utilization diagnostics [@yuan2026diagnosing]; experience-faithfulness interventions [@zhao2026selfevolvers] | Pipeline diagnosis for memory write, retrieval, and use; causal experience dependence. | A recognizer -> protective-candidate support -> bounded reranker selection -> sandbox-outcome audit. | The general decomposition idea is prior art. The new application exposes the candidate-support ceiling of a non-textual controller in SWE. This is a diagnostic contribution, not a new statistical method. | Medium |
| I7 | Heterogeneity-robust randomization inference [@ding2018randomization]; stratified finite-population inference [@liu2020regression] | Design-based average-effect inference without a superpopulation model. | A dual estimand/reporting contract for the exact seven-arm authored-lineage assignment and the separately assumption-bound lineage superpopulation. | The statistics are prior art. The residual methodological contribution is their explicit use in stochastic SWE-agent evaluation; novelty should not be claimed beyond that application. | Medium |
| I8 | Semantic invariance [@szeider2026semantic]; causal internal-state/report coupling [@lindsey2026introspective; @martorell2026quantitative]; self-explanation faithfulness [@madsen-etal-2024-self] | Functionally inert semantic shams can move reports; activation interventions can causally move reports; self-explanations are not generally trustworthy. | A joint sensitivity + semantic-invariance + calibrated-absence IUT for reports about an explicit history-derived controller state after an executable SWE decision. | Every ingredient has precedent. The residual novelty is the joint falsification sandwich tied to a hidden, machine-addressable state and behavior. | Medium |
| I9 | Memory Transplants [@feng2026memory]; SteeM [@huang-etal-2026-controllable] | Factorial separation of architecture/content transfer; controllable memory dependence. | A within-checkpoint, information-equated comparison of numeric-head and text-prompt actuation channels carrying the same quantized controller signal. | Prior work changes memory systems, content, or reliance. It does not hold the decision checkpoint and signal fixed while changing only the actuation channel. | Medium-high |

## Collision checks that changed the proposal

- The phrase and broad idea **memory transplant** are already published in a 2026 ICLR workshop paper. I3 therefore makes no naming claim and narrows novelty to a same-checkpoint cross-history state interchange.
- **Semantic invariance for LLM self-reports** is already an explicit 2026 preprint contribution. I8 treats it as borrowed prior art and claims only the joint sandwich in Pneuma's system-state setting.
- Retrieval-versus-utilization decomposition is already a 2026 MemAgents contribution. I6 is labeled a diagnostic application rather than a headline novelty claim.
- Controllable and learned memory use are already active 2026 topics. I1 is not “adaptive memory”; it is a causal minimal-sufficiency frontier under randomized recurrence interventions.

## Citation verification register

Every cited record was fetched from a primary or authoritative record during this research pass. Peer-review status is recorded because “real” and “peer reviewed” are not synonyms.

| Cite key | Persistent identifier | Fetched authoritative record | Record status | Used for |
|---|---|---|---|---|
| `huang-etal-2026-controllable` | DOI `10.18653/v1/2026.acl-long.670` | <https://aclanthology.org/2026.acl-long.670/> | ACL 2026 long paper | I1, I9 |
| `jiang2026controlled` | arXiv `2607.13591` | <https://arxiv.org/abs/2607.13591> | Preprint, submitted 2026-07-15 | I1 |
| `wang-etal-2026-samem` | DOI `10.18653/v1/2026.findings-acl.722` | <https://aclanthology.org/2026.findings-acl.722/> | Findings of ACL 2026 | I1 |
| `zhao-etal-2026-demystify` | DOI `10.18653/v1/2026.findings-acl.525` | <https://aclanthology.org/2026.findings-acl.525/> | Findings of ACL 2026 | I1 |
| `lindenbauer-etal-2025-knowledge` | DOI `10.18653/v1/2025.realm-1.30` | <https://aclanthology.org/2025.realm-1.30/> | REALM 2025 workshop | I1 |
| `lipsitch2010negative` | DOI `10.1097/EDE.0b013e3181d61eeb` | <https://dash.harvard.edu/entities/publication/73120379-21f6-6bd4-e053-0100007fdf3b> | Epidemiology 2010 article; repository copy | I2 |
| `shi2020negative` | DOI `10.1007/s40471-020-00243-4` | <https://pmc.ncbi.nlm.nih.gov/articles/PMC8118596/> | Current Epidemiology Reports 2020 review | I2 |
| `xiong-etal-2026-memory` | DOI `10.18653/v1/2026.acl-long.27` | <https://aclanthology.org/2026.acl-long.27/> | ACL 2026 long paper | I2 |
| `geiger2022inducing` | PMLR `v162/geiger22a` | <https://proceedings.mlr.press/v162/geiger22a.html> | ICML 2022 paper | I3 |
| `geiger2025causal` | JMLR `26(83)` | <https://jmlr.org/papers/v26/23-0058.html> | JMLR 2025 article | I3 |
| `feng2026memory` | OpenReview `AIJsjIqfsp` | <https://openreview.net/pdf?id=AIJsjIqfsp> | ICLR 2026 MemAgents workshop paper | I3, I9 |
| `li-etal-2026-locomo-plus` | DOI `10.18653/v1/2026.acl-long.1150` | <https://aclanthology.org/2026.acl-long.1150/> | ACL 2026 long paper | I4, I5 |
| `zheng2025lifelong` | arXiv `2505.11942` | <https://arxiv.org/abs/2505.11942> | Preprint | I4 |
| `zhang2026faulty` | arXiv `2605.12978` | <https://arxiv.org/abs/2605.12978> | Preprint | I4 |
| `liu2026agentabstain` | arXiv `2607.10059` | <https://arxiv.org/abs/2607.10059> | Preprint, submitted 2026-07-11 | I5 |
| `zhao2026selfevolvers` | arXiv `2601.22436` | <https://arxiv.org/abs/2601.22436> | ICML 2026 per arXiv record | I5, I6 |
| `yuan2026diagnosing` | arXiv `2603.02473` | <https://arxiv.org/abs/2603.02473> | ICLR 2026 MemAgents workshop per arXiv record | I6 |
| `ding2018randomization` | DOI `10.1093/biomet/asx059` | <https://academic.oup.com/biomet/article/105/1/45/4582744> | Biometrika 2018 article | I7 |
| `liu2020regression` | DOI `10.1093/biomet/asaa038` | <https://academic.oup.com/biomet/article-abstract/107/4/935/5857286> | Biometrika 2020 article | I7 |
| `szeider2026semantic` | arXiv `2603.01254` | <https://arxiv.org/abs/2603.01254> | Preprint | I8 |
| `lindsey2026introspective` | arXiv `2601.01828` | <https://arxiv.org/abs/2601.01828> | Preprint | I8 |
| `martorell2026quantitative` | arXiv `2603.18893` | <https://arxiv.org/abs/2603.18893> | Preprint | I8 |
| `madsen-etal-2024-self` | DOI `10.18653/v1/2024.findings-acl.19` | <https://aclanthology.org/2024.findings-acl.19/> | Findings of ACL 2024 | I8 |

## Search boundaries

The verification pass used combinations of the following concepts against arXiv, ACL Anthology, OpenReview, PMLR/JMLR, Oxford Academic, and DOI-indexed journal records:

- persistent memory + coding/SWE agent + recurring failure;
- minimal/sufficient/controllable state or memory complexity;
- state transplant, memory transplant, interchange intervention, activation patching;
- motif specificity, negative controls, error propagation, experience following;
- randomized lag, retention, lifelong agent benchmark, multi-session memory;
- paired cue perturbation, notice, abstention, experience faithfulness;
- retrieval versus utilization bottlenecks;
- finite-population and randomization-based multi-treatment inference;
- self-report faithfulness, semantic invariance, and causal introspection.

The optional local literature landscape was used only as a discovery aid. No entry was cited unless its primary record was fetched again in this pass.

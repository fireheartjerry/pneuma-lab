# PLACEBO Trial source ledger

**Snapshot:** 2026-08-04
**Canonical manuscript:** `paper/placebo_protocol.tex`

The manuscript currently cites **26 unique records** from a combined library of
**89 unique BibTeX entries**. Every active key resolves. This ledger answers two
different questions: which record is being cited, and what argumentative job it
does. Bibliographic existence alone is not evidence for a stronger claim than
the cited source makes.

| Active key | Primary record | Role in this paper |
| --- | --- | --- |
| `arl_pivotal_retry_2026` | arXiv:2607.03702 | Prefix-anchored retry as a method rather than a causal control |
| `berger_intersectionunion_1982` | doi:10.1080/00401706.1982.10487790 | Intersection--union logic for the co-primary success rule |
| `bjarnason_randomness_2026` | arXiv:2602.07150 | Stochastic variation in repeated agent evaluation |
| `bowyer_dontusetheclt_2025` | arXiv:2503.01747 | Benchmark-level uncertainty and invalid item-level approximations |
| `card_littlepower_2020` | doi:10.18653/v1/2020.emnlp-main.745 | Power as an empirical NLP design problem |
| `chernozhukov_multiplier_2013` | arXiv:1212.6906 | Multiplier-bootstrap basis for max-statistic inference |
| `gehring_rlef_2024` | arXiv:2410.02089 | Execution feedback bundled with additional code-generation attempts |
| `huang_howmanytasks_2026` | arXiv:2607.12338 | Task-count and benchmark-resolution analysis |
| `ich_e10_2000` | official ICH E10 guideline | Assay sensitivity and interpretable control comparisons |
| `iscan_falsificationnotexposure_2026` | arXiv:2606.31511 | Falsification versus exposure in controlled code-agent feedback |
| `iscan_formnotcontent_2026` | arXiv:2607.12962 | Packet form versus task-specific content |
| `iscan_scaffoldnotvocabulary_2026` | arXiv:2606.06454 | Scaffold versus vocabulary controls |
| `kaliyev_noisefloor_2026` | arXiv:2606.20695 | Adjacent measured noise-floor protocol |
| `kotawala_resolutiondiagnostics_2026` | arXiv:2605.30315 | Resolution diagnostics for benchmark comparisons |
| `kwon_pagedattention_2023` | arXiv:2309.06180 | vLLM/PagedAttention serving context |
| `miller_errorbars_2024` | arXiv:2411.00640 | Correct units for benchmark uncertainty |
| `min_rethinkingdemonstrations_2022` | doi:10.18653/v1/2022.emnlp-main.759 | Demonstration form and label-space effects beyond correctness |
| `qwen36_modelcard_2026` | HF revision `95a723d...3d989` | Frozen subject-model identity |
| `reflect_error_attribution_2026` | arXiv:2606.09071 | Bare-prefix resampling as an untargeted retry baseline |
| `romano_wolf_stepdown_2005` | doi:10.1198/016214504000000539 | Stepdown multiple-testing procedure |
| `shinn_reflexion_2023` | arXiv:2303.11366 | Verbal feedback plus repeated attempts in an agent loop |
| `siska_robustness_2024` | doi:10.18653/v1/2024.acl-long.560 | Dependence-aware robustness of benchmark rankings |
| `swebench_live_2025` | arXiv:2505.23419 | Multilingual live repository-repair environment |
| `tau_bench_2024` | arXiv:2406.12045 | Stateful tool--agent--user environment |
| `try_again_dont_look_back_2026` | arXiv:2607.26117 | Closest retry-versus-self-repair comparison |
| `unreliable_feedback_2026` | arXiv:2606.21409 | Harm from unreliable tool feedback |

## Verification trail

- `paper/refs.bib` is the shared audited bibliography.
- `paper/placebo/refs-placebo.bib` contains records introduced for the PLACEBO
  manuscript.
- `paper/placebo/citation-queue.json` records primary-source checks for the
  high-risk and newly introduced citations. Every queue entry is `verified`.
- The paper build uses both libraries, and the bibliography checker compares
  cited keys against their union.

Before submission, re-run the bibliography and manuscript checks against the
exact commit being uploaded. A resolved key does not license paraphrasing beyond
the source's actual scope.

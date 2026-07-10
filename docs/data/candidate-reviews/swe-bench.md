# Dataset Status Review: SWE-bench (family)

**Decision: EVAL-ONLY — benchmark contamination + no explicit artifact
license.** The canonical SWE-agent evaluation benchmark; using it as a training
source would contaminate evaluation. Not a training lane.

## Source

| Field            | Value                                                                                          |
| ---------------- | ---------------------------------------------------------------------------------------------- |
| HF repos         | `SWE-bench/SWE-bench`, `SWE-bench/SWE-bench_Verified`, plus Multimodal/Lite variants           |
| Revision (base)  | `7074ef12ea2a6f70a228943c1336553333c22786`                                                     |
| Declared license | harness code MIT; **HF dataset content: no explicit tag** (inherits 12 upstream repo licenses) |
| Local status     | downloaded (official `SWE-bench/*` org, pinned)                                                |
| Shape            | issue text, gold patch, test_patch, FAIL/PASS_TO_PASS oracle, images (Multimodal only)         |

## Why eval-only

1. **Evaluation contamination.** SWE-bench (and Verified) is the primary public
   SWE benchmark. Training PneumaBrain-v0 on it would invalidate any SWE-bench
   evaluation of that model. It is held-out by role.
2. **Known label quality issues (dossier).** ~1/3 of Verified instances have
   solution leakage in the issue text (arXiv 2512.10218); ~31% weak-test
   oracles and 28.6% of passing patches judged incorrect (SWE-Bench+, arXiv
   2410.06992). These make it a poor training target and a careful eval set.
3. **No explicit HF artifact license.** Content inherits 12 upstream repo
   licenses; there is no single declared dataset license to authorize
   redistribution-style training use.

## Lane status

- `current_stage: eval-only`, `training_readiness: eval-only`.
- `model_use_tier: eval_only`, `training_weight: 0.0`.
- Heavy repo overlap with SWE-Gym / Open-SWE-Traces (SWE-bench family) — another
  reason it must stay on the eval side of any split.

## Next step

Wire as a **held-out evaluation** benchmark once an eval harness exists. No
training conversion is planned. If an explicit dataset license ever appears it
still would not override the contamination role.

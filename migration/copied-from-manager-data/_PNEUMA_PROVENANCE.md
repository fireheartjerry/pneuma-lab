# Reference material copied from `C:\manager-data` (READ-ONLY, HISTORICAL CONTEXT)

Copied verbatim from the manager-data project on 2026-07-06. (The `README.md`
in this directory is manager-data's OWN readme, copied as-is; this file is the
Pneuma Lab provenance note.)

> ⚠️ **This is possible-future operator-preference context only — NOT the base mind.**
> `C:\manager-data` is an older project that turns Jerry's Claude Code action
> traces into an ML dataset for a "manager model" (a clone of the operator's gate
> decisions). Pneuma Lab may _eventually_ consume a sanitized operator-preference
> stream derived from it (→ `GovernanceFrame` / `InterventionFrame`), but this
> first pass does **not** integrate it, and Pneuma Lab must **never overfit** to
> Jerry's data or treat it as the psyche's identity.

## What was and was NOT copied

**Copied (sanitized, already-tracked docs):**

| File                   | What                                                                                                                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `README.md`            | The pipeline overview: 10 stages, the `manager_event_v1` normalized schema, the 13-verb manager action enum + 7 action families, current dataset state.                               |
| `jerry_integration.md` | How a fine-tuned operator clone would wire into 9to5's control plane (shadow mode → confidence-gated autonomy), and the `approve/reject/retry/abort/pause/resume/none` verb contract. |

**NOT copied (and why):**

- **No data.** Everything under `manager_data/{raw,normalized,datasets,manifests,
reports,models}/` is private, multi-GB, and secret-bearing (gitignored in its
    own repo). None of it was read or copied.
- **No secrets.** `.secrets/anthropic_api_key.txt` was never opened.
- **No pipeline scripts / training code.** Pneuma Lab does not train models in
    this pass; the normalization/labeling/SFT scripts are out of scope.
- **No raw Claude Code logs / traces.** Only the two summary docs above.

## Relevance to Pneuma Lab

The manager-data project independently defines an **operator-decision contract**
— a discrete action enum (`continue`, `ask_user`, `spawn_verifier`, `run_tests`,
`inspect_diff`, `retry`, `reroute`, `stop_task`, `accept_completion`,
`reject_completion`, `escalate_risk`, `summarize_state`, `spawn_specialist`) and a
control-verb map (`approve/reject/retry/abort/pause/resume/none`). That is exactly
the shape a future **operator-preference input stream** would take, feeding Pneuma
Lab's `GovernanceFrame` (what the operator would want) and seeding
`InterventionFrame` experiments (does the psyche move the way the operator's own
gate decisions imply it should?). Cross-walk lives in `../../docs/source-map.md`.

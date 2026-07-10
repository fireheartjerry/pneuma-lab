# Dataset Status Review: SWE-chat

**Decision: BLOCKED — privacy / provenance (PII, gated).** Not onboarded for
conversion. No adapter, no converter, no `PneumaTrainingExample` output.

## Source

| Field            | Value                                                                                                                                                                     |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HF repo          | `SALT-NLP/SWE-chat`                                                                                                                                                       |
| Revision         | `f66cca95b14caaa4177f7ed5eaa424608dadcffa`                                                                                                                                |
| Declared license | `odc-by` (ODC-BY); underlying repos retain own licenses                                                                                                                   |
| Gating           | HF `gating='auto'` — requires HF login + accepting contact-info-sharing terms                                                                                             |
| Local status     | **GATED — NOT DOWNLOADED** (no HF token configured in this environment)                                                                                                   |
| Shape            | conversations.parquet (~1.31GB), commits.parquet (~1.08GB), transcripts/ (~990 per-session jsonl); ~6,000 sessions, 63k prompts, 355k tool calls, 2.7M events, 200+ repos |

## Why blocked

1. **Real human user data (PII corpus).** SWE-chat contains real user prompts,
   authorship metadata, and contact-info-gated session data. The dossier flags
   it explicitly: "PRIVACY/GOVERNANCE: real human user data, contact-info-gated
   — treat as PII corpus."
2. **Access gate not satisfied.** Acquisition requires an HF token plus explicit
   terms acceptance; neither is configured here, and the bytes are not present.
3. **Project hard rule.** "Do not process SWE-chat unless privacy gates are
   explicitly satisfied." They are not.

## Next unblock step

1. Provision an HF token and accept the SWE-chat gate/terms (human decision).
2. Complete a **PII/privacy review and redaction plan** (authorship,
   contact-info, user text) with a committed `redaction_receipt` policy before
   any bytes are read into frames.
3. Only then design a digest-only adapter analogous to `open_swe_traces.py`
   (tool-call trajectories are the richest signal), with `privacy_status`
   gated on the redaction receipt.

Until all three hold, SWE-chat stays `provenance-blocked` / `training_readiness:
blocked`, `training_weight: 0.0`.

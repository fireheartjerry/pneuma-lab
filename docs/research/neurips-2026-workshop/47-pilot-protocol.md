# 47 — Pilot Protocol

**Status:** Step 13 protocol implementation complete; authorization and execution pending

This freezes two admissible context rungs on the approved one-GPU
`g6e.2xlarge`/L40S topology—TP1 at 32,768 and 65,536 tokens—plus maximum
cost/runtime/retries/sample count, exact bound-hash slots, and the deterministic
selection rule: choose the largest rung that passes OOM, tool-call,
output-parity, and p10-throughput gates. Efficacy is rejected as a selection
input, and no new rung may be invented, interpolated, or substituted with TP2
or H100 hardware. Azure is not a fallback for this protocol; it remains
separately governed.

This document supersedes the plan's intended filename only because committed
Step 7A evidence already occupies `41-image-recipe-preparation.md`; no prior
document is renamed or rewritten. `G-ROSTER`, real input/image receipts,
external verification, launch review, quota, and a hash-bound human/spend
authorization remain prerequisites to any pilot. No pilot has run.

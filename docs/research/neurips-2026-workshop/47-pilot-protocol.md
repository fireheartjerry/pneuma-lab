# 47 — Pilot Protocol

**Status:** Step 13 implementation is complete; external authorization and
execution remain pending. The preregistered one-GPU p10 output-throughput floor
is **8.0 tokens/sec**, selected under DL-165 before any admission measurement.

This freezes two admissible context rungs on the approved one-GPU
`g6e.2xlarge`/L40S topology—TP1 at 32,768 and 65,536 tokens—plus maximum
cost/runtime/retries/sample count, exact bound-hash slots, and the deterministic
selection rule: choose the largest rung that passes OOM, tool-call,
output-parity, and p10-throughput gates. Efficacy is rejected as a selection
input, and no new rung may be invented, interpolated, or substituted with TP2
or H100 hardware. Azure is not a fallback for this protocol; it remains
separately governed.

The receipt gate re-hashes the exact protocol bytes before it accepts a
throughput result. A receipt with `p10_throughput=true` must both name that
exact digest and show a measured p10 at or above its registered floor; a merely
positive measurement is not a passing admission.

## Registered p10 floor

At each tested rung, the p10 of measured output-token throughput must be at
least **8.0 tokens/sec**. This is a serviceability floor, not a prediction or
performance claim: at the slow tail it bounds a 128-token generated response
to 16 seconds and a 256-token response to 32 seconds. It deliberately does
not weaken the separate OOM, tool-call, output-parity, hash-binding, cost, or
authorization gates.

The measurement estimator is frozen before execution: each rung receives one
excluded warmup followed by exactly ten sequential observations of exactly 128
output tokens at temperature zero, batch size one, and concurrency one. EOS is
ignored so an early stop cannot inflate throughput. The p10 estimator is the
nearest-rank tenth percentile, `sorted(samples)[ceil(0.10 * n) - 1]`; with ten
observations this is the minimum observed rate. Receipts retain all ten raw
rates, elapsed times, token counts, and output-token digests. A summary p10 is
recomputed from those raw observations and cannot self-certify.

The threshold is bound to the approved topology SHA-256
`57339eb1e651f42c4b769a826999acffcfb0029e0e9890645de7a066e6ad1720` and
pilot-protocol schema SHA-256
`2fef9fd67c7b1a1046ea61f523bef69d19a57a60735057b1e158c0f22eb85ae0`.
Changing either requires a new threshold decision; a future pilot receipt must
also bind canonical machine-readable protocol bytes through `protocol_sha256`.

This document supersedes the plan's intended filename only because committed
Step 7A evidence already occupies `41-image-recipe-preparation.md`; no prior
document is renamed or rewritten. `G-ROSTER`, real input/image receipts,
external verification, launch review, quota, and a hash-bound human/spend
authorization remain prerequisites to any pilot. No pilot has run.

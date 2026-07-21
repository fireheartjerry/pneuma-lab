# Session: foundation 2M stage — multi-lane training and a passed kill gate (2026-07-20)

Continuation of the same-day 100K/500K sessions. Everything local; paid
compute $0; no cloud resource created in this session.

## Unblocking work (commits `0cd8cd5`..`c596d05`)

1. **Data**: the full Open-SWE-Traces corpus (84 raw parquet shards) was
   converted by the existing digest-only adapter into the processed lane
   `processed/open-swe-traces/pneuma-trace` — 160,731 valid traces, 0
   invalid, 10.2 GB. The lane's CC-BY-4.0 posture is recorded in a new
   committed license receipt (conservative
   `local_research_candidate_no_redistribution`; MiniMax/Qwen model-output
   ToS noted as not independently verified).
2. **Policy**: `payload_access_2m` column; at 2m the suite opener approves
   exactly two lanes via a per-family approved-lane table.
3. **Conversion**: the OST converter gained the verified-stream surface
   (mirror of the OpenHands one), so preparation never reopens payload
   paths.
4. **Preparation/authorization**: stage-keyed two-lane pipeline with
   per-lane conversion artifacts, both license receipts pinned, the
   committed cross-dataset leakage registry enforced as a quarantine
   receipt (7 overlapping repos quarantined), per-lane coherence
   verification, lane weights {openhands 1.0, open-swe-traces 1.0}.
   Pre-2m outputs proven byte-identical (worktree A/B against HEAD).
5. **Kill-gate machinery**: new `pneuma_lab.foundation.variants` harness +
   `variant-eval` CLI (honest `held_out_risk_prediction_correctness`
   semantics, measured overheads, deterministic untrained baselines,
   disclosure in every file) and per-boundary `validation_batches.json`
   persistence in the runner (closing the known evaluate gap).
6. **Ceilings**: multi-lane artifact ceilings re-scaled to measured
   full-lane sizes (553 MiB examples, 67 MiB split receipt).

## The 2M run

- prepare ×2: byte-identical candidate
  (`B3842C5C…4322F7`); shard `6b00ce4c…34ca` — ~105K train / 16.8K
  validation / 13.3K held-out examples, 31,652 quarantined.
- Authorization scope digest
  `20a569bfe4a438863c896dfa74844f9cb050a1c83a912727d094ef20ee8b936c`,
  operator `student-operator`, code commit `c596d05`.
- Train @2e-4: run `foundation-2m-20a569bfe4a43886`, **330 optimizer
  steps, 1,997,114 of 2,000,000 tokens**, best/last validation loss
  0.0875/0.0909, clean checkpoints, no pauses.

## Falsification kill gate: PASSED

`variant-eval` on 3,399 repo-disjoint held-out tasks (10,580 train +
3,399 validation records in the evaluation shard):

| Variant              | Resolved rate | p95 overhead | FLOPs overhead |
| -------------------- | ------------- | ------------ | -------------- |
| untouched_qwen       | 35.86%        | 0            | 0              |
| continued_deltanet   | 35.86%        | +5.4%        | 8.7e-06        |
| feed_forward_adapter | 35.86%        | +1.4%        | 6.1e-06        |
| pneuma_recurrent     | **64.14%**    | −2.7%        | 1.6e-05        |

`evaluate` decision: kill=false, absolute improvement +0.2827 over the
strongest baseline, bootstrap CI95 [0.2510, 0.3151] strictly above zero,
zero gate failures. Honesty constraints: task semantics are the held-out
risk-prediction proxy (not SWE-agent task resolution) and the two
pre-registered baselines carry deterministic UNTRAINED initializations
(baseline training is not separately authorized); every emitted file and
the index disclose both. The run-level regression gate reports p95/FLOPs
unmeasured (the trainer does not instrument them); the junction overheads
measured by the variant harness are far inside the pinned limits and are
carried in the local gate report with provenance.

Artifacts: `build/foundation/runs/2m-2e-4/` (manifest, events,
validation_batches.json, evaluation_report.json, local_gate_report.json,
checkpoints through 330), `build/foundation/variants/2m/` (four variant
results + index), and six claim-bounded section reports under
`build/foundation/runs/foundation-2m-20a569bfe4a43886/reports/`.

## Cloud readiness (code only this session)

The cloud authorization scope now mirrors the two-lane 2m binding
(authorization schema v0.5.0), cloud finalize/verify path fixed (it was
never wired), and the bundle packs the gate report. The
no-redistribution/private-transfer reconciliation: license receipts pin
`cloud_redistribution_allowed: false`; a single-job ephemeral transfer of
derived digest-bearing artifacts is separately controlled by the cloud
scope's `source_data_policy.private_cloud_transfer_allowed` and the $45
lifetime budget gates.

## Cloud reproduction (2026-07-21, completed)

The one-time RunPod reproduction ran under a separately finalized
two-lane cloud authorization (scope digest `35f23296…`, live A40 quote
$0.44/hr, $35 all-in tax-inclusive job ceiling; the operator's $50
credit load exceeds the $38/$45 caps so the job ceiling — not the load —
is what the gates bind). Pod lifecycle was driven over the RunPod REST
API with an operator-provided key (never committed or logged):

- Two false starts, both terminated within minutes: a pod that booted
  before the account SSH key registered, and a host whose driver topped
  out at CUDA 12.8 (the locked torch needs CUDA 13 wheels;
  `allowedCudaVersions: ["13.0"]` fixed placement).
- Pod-side verification required two artifacts the tar bundle omits by
  design: the git history (shipped as a `git bundle`, checked out clean
  at the bound commit `92d307d`) and the ~750MB per-lane conversion
  evidence (streamed over SSH; digests verified against local). Both are
  pre-existing bundle-design debt, now documented.
- Run `foundation-2m-35f2329653ca804e`: preflight verified the full
  two-lane cloud authorization on the pod, then 330 optimizer steps,
  status `completed`, best/last validation loss 0.08654/0.09223 —
  closely reproducing the local run (0.08746/0.09091).
- `pneuma-results.tar.gz` (manifest, validation_batches.json, terminal
  checkpoints) retrieved to `build/foundation/cloud/`; the pod was
  terminated and the API confirms zero pods and zero network volumes
  remain. Lifetime cloud jobs: 1 of 1. Actual paid compute: under $2.

## Verification

- Full suite green at every commit boundary (last: 2044 passed, 3
  skipped).
- `python -m pneuma_lab.status --check` and the operator-guide checker
  pass after the status/title updates in this commit.

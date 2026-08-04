# Pre-experiment AWS qualification closure — 2026-08-04

## Verdict — action-018

**B — post-launch terminal no-go.** The fresh action
`dual-l40s-qualification-018` passed the pre-launch semantic, provider,
image, IAM, plan, and KMS gates and reached exactly one CloudTrail-proven
size-two Batch submission. The concrete runner then hit an unclassified
`batch describe-jobs` provider subprocess failure. No post-launch retry was
made.

Independent AWS reads later showed the original parent and both original
children succeeded once, with two distinct worker identities and two valid
fixture raw artifacts. That is useful forensic evidence, but it is not a
qualification pass: the runner did not complete its required admission,
artifact-verification, and freeze/restore recovery receipt. The terminal
receipt therefore remains `no_go` by contract. No official P0/Step 4B
experiment, benchmark/model workload, pilot, subject workload, unblind,
scientific analysis, or claim promotion ran.

## Sealed action facts

- Immutable fixture image: `sha256:75ed10fa3237b12e122e7b5947b7b68639da6043571b3c6024fc436c686c212e`.
- IAM: **17/17 live decisions passed**. Five exact input reads and two exact
  worker-indexed raw writes were allowed; output reads, wrong-worker output,
  other-action/unrelated objects, listing, delete, abort, decrypt, and IAM
  administration were denied. Policy SHA-256:
  `e3a197a17b5f813b995ce4910032ab366b20904fec2867d65f282fbf80c18f2e`;
  inventory SHA-256:
  `e929c24942f15592d68ecc12559b9e72f26f3b4d96442125767b5e29d821b11d`;
  matrix SHA-256:
  `559d67ebf6cd5b0b549994879589e3c76240fa01c03af1cbc00bbae816cdb87`.
  Post-apply policy readback matched the expected hash exactly.
- Plan binding: saved plan
  `b9f4473e890ea6e9e91e3700c954f6f2a2011557da6aadd18ba105cf5c5f869c`;
  raw Terraform show
  `17c37a1fa57ac8eec0cf219603092d025510f9c336f418cf125e00d74331e211`;
  composite binding
  `33af0b173b7071ec9ede0780eb08810c6d13cb21548ccf8154f09bdcfd772bde`.
- Authority: package
  `2df1e8a7b4c72f39a008d52ba0953a84e90a625639bb98e9082e2600c01b21a7`;
  envelope body
  `e7507e2bbfa2eb63cd25d5df576124c1121dc5069fa0e214da8ed952ffa9fee3`;
  admission body
  `77455dffae94ca338b453c446e1f81102f7c7e9586b0f7c9a81267b2084f4b3a`;
  envelope signature
  `be4262cff6e5986a9461f2cdcc219e73449ea670dd09a61740f9dc6a0ce6aee0`;
  admission signature
  `2143d1a387551e95f34932bf8b92ec3ab3f2f758dae73467eef3b16b921b0d68`;
  KMS verification
  `c74da234caf19f14e81fdf8a2f71bad8083e03bd09257895893473d2d0532537`.
  Both explicit human-signed envelopes verified with `ED25519_SHA_512`.
- Spot projection: **USD 4.4842**, strictly below USD 100. Observed worker
  durations were **6.614 s** and **6.691 s**.
- Worker identity hashes:
  `1ec91865249a62ac3d9cf6f99fbe2da1dba47d101f4080f84e0583cb32bd1178` and
  `7db3c3801867170ebb5a5cbd6ea7a4c456c525480a401cc6dafdf4e34ad19abb`.
- Raw artifact hashes:
  `46a8b755f9b5acd37ef143d799d00c8211300965f074da913955b6168fd9315c` and
  `bbff8c9dc8215109a8997cfc1313e2fc818ebea8580fc0c5bf82ad5636a9ec42`.
- Recovery: **not run** because the runner's admission path did not reach its
  required successful-child terminal state.

## Launch, repair, and teardown

CloudTrail proves exactly one `SubmitJob` event: event-ID SHA-256
`532012010fadec2ac7fa8c5019c6833714d29e706bb696453a5c5809deedf495`, parent
job-ID SHA-256
`23dec859ef1c01cfbabf97d680eef627517838a243224ca4e7ddc6c386450ba3`, array
size two, and one attempt. The observed provider failure is recorded only as
`ProviderSubprocessError` for `batch describe-jobs`, with error-code
`unknown` and stderr SHA-256
`c537fe804f9d57c406ae22cacdd051d8ab40d0c15995d726b3c7ff428fb2aaf2`.
No deeper AWS or capacity cause is asserted.

The focused source repair in pushed commit `1c8ef21` gives Batch observation
reads a bounded retry path even for an unclassified provider error. The new
regression is
`tests/cloud/test_ephemeral_runner.py::test_concrete_cli_retries_unclassified_batch_observation_failure`.
This is a readiness repair only; action-018 is exhausted and was not
relaunched.

Queue and compute environment were disabled/drained, then all four approved
Terraform resources were destroyed under the lock. Final provider absence is
proved by
`evidence/dual-l40s-qualification-018-final-provider-absence-20260804.json`
(file SHA-256
`59f0087cfe42c5cb20e522689f4ea4637d0f7e1cd33c3054c669a5ba24e63050`;
canonical absence SHA-256
`3b92c804efdf40c74b9b0bda3786a681de7bc3e989c4b2c8f2884e122cd4408b`).
The two raw objects and inactive AWS job-definition history are retained
evidence, not live qualification resources.

The focused hostile review using these actual receipts is recorded at
`evidence/dual-l40s-qualification-018-hostile-launch-review-20260804.json`
(SHA-256
`9b37d72ff33e95e88aabe46d729d3cd4b9fd80f84587c6355fe07899ca694218`). The
schema-bound execution receipt is
`evidence/dual-l40s-qualification-018-execution-receipt-20260804.json`
(SHA-256
`738af3190c747da28b0308ad5179965bb3b3224481e56141b41396ea0cc4bdeb`).

## Remaining blockers before the separately authorized official study

1. Canonical dual-L40S qualification remains unpassed because the runner-owned
   recovery receipt was not completed; no new launch is authorized by this
   closure.
2. Step 14 remains `launch_blocked` until fresh authority-backed P0 power/tier,
   packet, assignment, detectability, unblind, and release receipts exist.
3. Tasks 6–10 remain `implementation_complete; E2E_pending`; Task 10 is still
   implementation/release preparation, not a scientific result.

This document is infrastructure closure only. It does not authorize or imply
the official P0/Step-4B study.

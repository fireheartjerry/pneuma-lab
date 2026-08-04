# Pre-experiment AWS qualification closure — action-019 — 2026-08-04

## Verdict

**A — qualification passed.** `dual-l40s-qualification-019` completed the
fixed fixture-only lane exactly once: two independent `g6e.2xlarge` Spot
workers, one L40S and 8 vCPUs each, one size-two Batch array, one attempt per
child, both children `SUCCEEDED`, two distinct worker identities, immutable raw
artifacts, the freeze/restore recovery boundary, and complete teardown.

Action-018 remains a historical post-launch no-go. It was not reused or
relaunched. No official P0/Step-4B experiment, benchmark/model workload,
pilot, subject workload, unblind, scientific analysis, or claim promotion ran.

## Sealed qualification facts

- Immutable image: `sha256:75ed10fa3237b12e122e7b5947b7b68639da6043571b3c6024fc436c686c212e`.
- Plan: saved bytes
  `baaa7620c4384d248244cece1f511de7731deb7fb5ad44231cf4d9626513a8f5`;
  raw Terraform show
  `ab65b5cb5078c47190385004f314723e6e3b75a9649768c2cf4849cd790a5554`;
  composite binding
  `ada75565fcdd702df65977b6f440a6246dcedd3112b94f6f417b730a6b32be64`.
- IAM: **17/17 live simulation decisions passed**. The exact five input reads
  and two worker-indexed writes were allowed; output reads, wrong-worker and
  other-action paths, listing, delete, abort, decrypt, and IAM administration
  were denied. Policy SHA-256
  `cd551ea6b3b689140b3cb8d4865b6c272b692d6bf7616930419b65c29583b81b`;
  inventory SHA-256
  `f7a62c38814fee40f9dfbd01f44335d11bd588ff67e40b6b64bc542cb45f78a2`;
  matrix SHA-256
  `56ce5ae76f537b836ee7f4dae2e8b9832fd0ba2c1149627c53e59429b2ed3144`.
  Post-apply IAM readback matched the expected policy hash.
- Authority: package SHA-256
  `96ffa5d0c2549af42a9acdb1a999f23c3bc2a0aa0011ec81e8e1e30f7e827bdc`;
  envelope body
  `d831190c744a1f932cc905530191a9b4988843360269e35031adcf4e78765dd9`;
  admission body
  `878b1bee2c9b4fadd90552fc52f296155fe11d2da9b61e918e3449e8258b00cc`;
  envelope signature
  `409e74259181db19d4e6dcbdc15c837fd6fec1b53a1079db3bf29e89c0f3e649`;
  admission signature
  `4a666839078b7aef6f2aa9f2bb02c20448e1bdc6b3704f39ee25bd8d356e2fb9`;
  KMS verification
  `c74da234caf19f14e81fdf8a2f71bad8083e03bd09257895893473d2d0532537`.
  Both signatures verified with `ED25519_SHA_512`.
- Spot projection: **USD 4.4842**, below the USD 100 ceiling. Observed worker
  durations: **6.583 s** and **6.631 s**.
- CloudTrail proves one SubmitJob event, event-ID SHA-256
  `1326517e41c839f2ff609a1734ec5e87b823c69674cac679d574061490d4f677`, with
  parent SHA-256
  `8ef5717400cafb86ed87672438d4e52535c5df1abcd5e95203ba8a7964aa1555`.
- Worker identities:
  `338386d03bda4d128982d42653c80d371523898f2145d72cf9763322aec7becb` and
  `7e3f481b03527e6787216ddd09623bdaaf882d74459766df81710f7f2cd8743a`.
- Raw artifacts:
  `793e77f6a4e7e5456e885888c38a2f1c63abe0553fdbd879ee29e7eabfad9743` and
  `6613dbf8f72e99532ba2c5d5be56b92135d5abaf646b044cb2e4084bf7f50a69`.
- Recovery boundary:
  `279734994f5e32893f275cd65f36410627d42a739ad0c102bf7da222d78ad88b`.

## Teardown and hostile review

Disable/drain and locked Terraform destroy completed. Fresh provider reads
prove the queue, compute environment, active job definition, launch template,
instances, volumes, network interfaces, security group, and jobs are absent.
The final proof is
`evidence/dual-l40s-qualification-019-final-provider-absence-20260804.json`
(SHA-256
`50690d50a1cb3e85f486a363b29620f4b991aa5a8c6569040ead777b52eb0fad`). Three
objects remain intentionally retained as evidence: the two worker raw files
and `interruption/boundary.json`; AWS also retains inactive job-definition
history. These are not live resources.

The focused hostile review against the actual receipts is
`evidence/dual-l40s-qualification-019-hostile-launch-review-20260804.json`
(SHA-256
`47821f724d505ba3c9a99bd25757f27610a747f3edc0ea6178e6aeabc519f9e1`). The
schema-bound execution receipt is
`evidence/dual-l40s-qualification-019-execution-receipt-20260804.json`
(SHA-256
`a68a6eef44f75af7d8fd61660355887b90b03fa1a678e77836932cef335f4ba2`).

## Continuity and release preparation

The read-only Task 6 and Task 7 Step-4A continuity scripts both passed. The
focused Task-10 release and Step-14 receipt-gate tests passed, and the project
status checker passed. These checks validate implementation continuity only;
they do not create P0 authority or scientific evidence. Tasks 6–10 remain
`implementation_complete; E2E_pending`, Task 10 remains release preparation,
and Step 14 remains `launch_blocked`.

## Remaining blockers before the separately authorized official study

1. Fresh authority-backed P0 power/type-I and tier-finalization receipts.
2. Sealed packet/capability, roster/assignment/task-block, detectability, and
   leakage-audit receipts.
3. The frozen analysis graph, authority-bound unblind permit, paired
   blinded/unblinded publication, and independent post-unblind receipts.
4. A fresh ten-role hostile Step-14 release review resolving all critical and
   important findings, plus venue/compliance verification.
5. A separate official P0/Step-4B authority package and launch receipt. The
   official experiment, benchmark/model workload, pilot, unblind, scientific
   analysis, and claim promotion remain outside this lane.

This report is infrastructure closure only. It does not authorize or imply
the official P0/Step-4B study.

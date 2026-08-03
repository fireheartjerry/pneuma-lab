# Pre-experiment AWS qualification closure — 2026-08-03

## Verdict

**B — post-launch terminal no-go.** Action
`dual-l40s-qualification-011` was launched exactly once. CloudTrail proves one
size-two Batch array with one permitted attempt. Both children became `FAILED`
with provider status reason `JobQueue deleted` and zero attempts. The required
two-worker qualification therefore did not pass; no retry or successor launch
was performed.

No official P0/Step 4B experiment, benchmark/model workload, pilot, subject
workload, unblind, scientific analysis, or claim promotion occurred.

## Sealed facts

- Immutable fixture-only image:
  `sha256:5433527fb588c009d6cf16a5ac4278c463bbb5fab0c0a6826147b4c98f2e83ff`
- IAM simulation: **pass**. Five exact input `GetObject` reads and two exact
  worker-indexed `PutObject` writes were allowed. Output reads, wrong-worker,
  other-action, unrelated-object, `ListBucket`, delete, and abort were denied
  in the sealed action-011 15-case matrix. The current source contract adds
  separate denied `kms:Decrypt` and `iam:PutRolePolicy` checks, for 17 fixed
  checks total; those two checks were not part of the historical action-011
  record. Policy SHA-256:
  `73666739e4e41f136fd11049715130e9b5086e6cafc21cee642ebe179fb0f24b`.
- Plan hashes:
  - saved plan:
    `7c665827ed95bd4d55657e81ee9c2edf718f287cd58af325b4c714ce2b901ddc`
  - raw Terraform show:
    `01387c775cf497046bbcc4cc6a82b08052f836a127dca214660bacf03ed70141`
  - composite binding:
    `f4b627f943a0989222fd0aab53d8d01329ccca733de12135b54777914d5d0516`
- Authority hashes:
  - package:
    `8b3ae0892add4452464c00b0982f2dccc24a9a5cdf8dd944e6fa8783c8eddb7e`
  - envelope body:
    `606852028e73aafb61498e4b6e47e4428c33f81032c915901ba95b4198784c82`
  - admission body:
    `5cd6042eb58687c969d21dd54d03f0ed07116785ce5285a1aa399fefa6783016`
  - both signatures verified with `ED25519_SHA_512`.
- Spot projection: **USD 4.4842** for two `g6e.2xlarge` workers at 3,600
  seconds, below the USD 100 bound. Observed worker duration: **none**;
  neither child reached `STARTING`/`RUNNING`.
- Worker identity hashes: **none**. Raw artifact hashes: **none**; the
  action output prefix contains zero objects. Recovery: **not run**, because
  admission never reached two successful children.

## Teardown proof

Fresh AWS reads show no live action-scoped jobs, active job definition, queue,
compute environment, launch template, instance, volume, network interface, or
security group. AWS retains the deregistered `INACTIVE` job-definition revision
as provider history; it is not runnable. The initial verifier incorrectly
treated that history and terminal Batch job records as residual resources; the
narrow repair and focused regression now model AWS semantics correctly.

Receipt:
`evidence/dual-l40s-qualification-011-execution-receipt-20260803.json`
(SHA-256
`2452cc4a1a531e39bf170c038c8ba56829b57ea77b58ea532b2f61acb3990854`).
The receipt is now bound to
`cloud-ephemeral-dual-worker-qualification-receipt.schema.json`; direct
validation and the focused retry-drift regression pass.

## Concrete runner repair after hostile audit

The concrete runner previously emitted a legacy flat receipt shape and discarded
Batch child observations when admission failed. The repair now captures the
single CloudTrail `SubmitJob` evidence, preserves the parent and both child
status records through teardown, proves the output-prefix object count and
inactive job-definition history, and emits only the registered schema-bound
receipt after a submitted lifecycle. Pre-launch failures do not write a fake
execution receipt. Focused provider-free cloud/schema regressions pass; no AWS
resource was created and action-011 was not retried.

## Hostile closure review

The focused hostile review checked the actual receipt, ledger rows, runner,
image/plan bindings, IAM claims, single-launch boundary, and absence proof. It
confirmed the no-go and found no basis to call this a successful qualification.
It also noted that the literal cause of the queue deletion is not proven by
the retained evidence; this closure records only AWS Batch's observed status
reason and invents no root cause.

## Concrete runner readiness repair after the follow-up seam audit

A fresh read-only agent-session audit found two remaining concrete bypasses in
the executable path. The CLI accepted a caller-provided IAM-matrix digest
without performing the simulation, and the runner could be pointed at an
action ID already represented in retained evidence. Both are repaired:

- `iam simulate-principal-policy` now runs the fixed 15-case matrix derived
  from the parsed action plan: five exact input reads, two worker-indexed raw
  writes, and eight denied reads/writes/list/delete/abort cases. The future
  path adds two more denied checks for KMS decrypt and IAM policy
  administration (17 fixed checks total); the sealed action-011 record remains
  the historical 15-case matrix. Every retained record is sanitized, bound to
  the independently verified attached role and action-specific policy hash,
  and rehashed before apply and again at receipt serialization.
- The attached worker role ARN returned by the profile/read-role checks is
  carried into the parsed plan for IAM simulation; the instance-profile ARN is
  never substituted. Reuse of an action ID already present in the evidence
  directory, or overwrite of its receipt path, fails before provider mutation.

Focused provider-free IAM, runner, receipt, and schema regressions pass. This
was a source/readiness repair only: it did not create AWS resources, relaunch
action-011, or cross the official P0/Step 4B scientific boundary.

## Concrete seam and policy-source repair after the second audit

The next adversarial pass found and repaired four executable-path gaps without
launching AWS: the concrete Batch submit now sends and CloudTrail-verifies the
3,600-second attempt timeout; IAM simulation retrieves the real S3 bucket
policy and includes its canonical policy bytes in every simulation while
retaining only a sanitized digest; the runner independently fetches the live
KMS Ed25519 public key, matches it to the committed registry, and verifies both
authority signatures; and the authoritative spend ledger is part of the
action-freshness check. The future dual-L40S signing package now binds the
exact saved-plan/show/composite bytes together with the action policy hash,
immutable image digest, four-AZ subnet map, output prefix, fresh projection,
action id, and zero-retry limit.

The Terraform worker inline policy was also repaired at source: its S3
permissions are five exact fixture-input `GetObject` resources and two exact
worker-indexed raw-output `PutObject` resources, with no `ListBucket`, output
read, delete, decrypt, IAM, wildcard-resource, or multipart-abort grant. The
unrelated DynamoDB and managed role policies remain intact. Focused cloud,
signing, schema, and Terraform regressions pass. These changes improve the
next fresh qualification package; they do not alter the sealed action-011
no-go receipt or authorize a retry.

## Raw-show and live-policy binding repair

The final source audit repaired two smaller fail-closed seams without touching
AWS. Account-plan admission now requires the exact lowercase SHA-256 of the
raw Terraform-show bytes and reports a typed cloud error for missing or
malformed metadata. Before IAM simulation, the concrete adapter reads the
`bounded-experiment-access` inline policy from the provider-verified attached
worker role, canonicalizes only its digest, and rejects live policy drift from
the fresh action authority. A focused regression covers that rejection. The
dual-worker topology is now consistent in both permanent agent guides. Action
011 remains exhausted; there was no relaunch, provider mutation, or scientific
workload.

## Plan/show consistency hardening

The future qualification runner now fails closed on malformed or conflicting
Terraform-show digest metadata, and the locked apply re-read reports an
explicit cloud error before mutation if its raw-show digest is unavailable or
invalid. A focused regression covers conflicting plan/show metadata. This is
source-only hardening; action-011 remains exhausted and unchanged.

## Runtime and IAM boundary hardening

The future fixed image path now requires the action ID, artifact prefix, and
output-root environment variables to agree on the exact
`.../<action-id>/outputs/` prefix before any fixture input is materialized or
published. Terraform-show admission now also requires a managed Batch compute
environment and rejects a custom AMI field nested in compute resources. The
IAM simulation adds explicit denied checks for KMS decrypt and IAM policy
administration. Focused probe, runner, Terraform, IAM, and image-fixture tests
pass; this does not alter the sealed action-011 terminal no-go.

## Source/image and plan-semantics closure repair

The next source-only audit repaired three remaining fail-open seams. Future
qualification signing now rejects conflicting IAM policy-hash representations
instead of selecting the first truthy field. Terraform-show admission requires
`us-east-1`, a concrete VPC binding, and no `command`, `entrypoint`, or
`entryPoint` override that could erase the image ENTRYPOINT. The concrete
ephemeral runner now requires the immutable fixture-image digest to match
exactly one complete build receipt whose ECR immutability, AWS CLI v2, package,
schema, fixed-entrypoint, network-none, no-model, five-input, and immutable
worker-artifact checks pass.

The sealed action-011 image digest
`sha256:5433527fb588c009d6cf16a5ac4278c463bbb5fab0c0a6826147b4c98f2e83ff`
was built from source commit
`e36dd15ac2524c29d0fb02a8705ec7fcc48fb34a`, while these post-launch source
repairs are newer. The digest and receipt remain valid historical evidence;
the new runner will correctly refuse to reuse that source/image pair for a
future action. No rebuild, relaunch, retry, or AWS mutation was performed.
Focused image, signer, plan, runner, qualification, and account-verification
tests pass.

## Direct-runner and binding-source closure repair

The next source-only audit closed a direct API freshness bypass: callers that
omit an evidence directory now use the repository's authoritative evidence
root, so an exhausted action cannot be replayed by calling `execute()`
directly. Concrete teardown now disables the queue and compute environment
before draining the submitted Batch parent and both array children, with one
bounded termination request only after the drain window expires. The parser
also requires both top-level and nested exact raw Terraform-show hashes,
exact action tags on compute, launch-template, queue, and job resources, and a
single order-1 queue-to-compute binding. The signing path rejects conflicting
image, subnet, output, projection, and retry representations rather than
choosing a first truthy source, and requires the exact composite plan binding
for a dual-L40S qualification package.

Focused runner, parser, signer, IAM, receipt, image, AWS-account, and Ruff
checks pass. This was source-only closure work: action 011 remains exhausted,
there was no AWS mutation or retry, and the official scientific boundary is
unchanged.

## Plan/resource and submit-binding closure repair

The final executable-path audit closed four additional fail-closed seams. The
loaded Terraform plan now requires matching top-level and parsed saved-plan,
raw-show, and derived composite digests; the locked apply rehashes all three
immediately before mutation. Resource names must be concrete and bind
`name_prefix` to the action id and worker suffix. The live queue readback must
point at the exact live compute-environment ARN before submission.

The concrete Batch submit path now sends exactly the six qualification tags,
and the sole CloudTrail `SubmitJob` event must match the action job name,
queue, job-definition name/revision, fixed array/retry/timeout contract, and
full tag map. Authority receipt validation independently recomputes the
Terraform composite binding. Focused negative regressions, Ruff, Terraform
format/validation, project status, image fixture, graph refresh, and diff
checks pass. These are source-only repairs; action-011 remains the single
sealed terminal no-go and was not retried or relaunched.

## Terraform variable/resource parity repair

The post-no-go parser audit closed one remaining cross-field seam: planned
compute-environment subnet and security-group values must now equal the
`subnet_ids` and `security_group_ids` Terraform variables exactly. A conflicting
variable cannot be silently replaced by a resource value or accepted through a
fallback. The negative mismatch regression and bounded cloud/static checks
pass. This repair created no AWS resources, spend, action, authority package,
or ledger reservation; action-011 remains exhausted.

## Shared Terraform locking and Step 14 gate hardening

The qualification stack now uses the existing verified artifact bucket as an
encrypted S3 backend with a fixed state key and Terraform-native
`use_lockfile` locking, with Terraform 1.10.0 as the minimum supported version.
This makes the locked apply/destroy contract serialize across operator hosts,
not only within one checkout. A new Step 14 regression proves the spec builder
returns a nonzero result when a required production execution-surface receipt
is absent. These are source-only repairs; live backend initialization was not
performed, no AWS spend or mutation occurred, and action-011 remains exhausted.

The concrete runner now actually consumes that backend contract: it performs
`terraform init -reconfigure -lockfile=readonly` before reading the saved plan,
and refuses plan load, apply, or destroy if initialization did not succeed.
The corresponding adapter regression passes. No AWS backend initialization or
resource mutation occurred.

## Step 14 real-power input and authority-gate repair

The Step 14 campaign builder no longer uses the prose power/design brief as
the `power_report` input. It now requires the canonical Task-10 sealed
`p0-power-report.json` and independently verified `p0-core-receipt.json` under
the canonical run root as digest-bound receipts. Both are absent in the
current checkout, and the builder exits nonzero naming both paths; the gate
therefore remains honestly `launch_blocked`.

A complete synthetic regression now exercises `validate_authority_evidence`
and rejects tampered Terraform-show authority bytes. No scientific authority,
P0 lineage, or provider action was created.

## Runner absence, action-freshness, and tfvars binding repair

The concrete runner now requires complete provider absence evidence at both
preflight and post-destroy boundaries, including an empty action-scoped output
prefix with exactly zero objects. It also searches retained evidence by exact
action-token boundaries across nested relative paths, preventing both
`qual-1`/`qual-10` collisions and directory-based freshness bypasses.

The `--execute` path now requires an explicit regular mode-600 `.tfvars` file,
hashes its bytes when loading the saved plan, rejects changes before apply or
destroy, and passes that exact file to the locked destroy command. Focused
negative regressions pass. These are source-only repairs; the stale action-011
image, plan, authority package, and provider outcome remain historical and no
relaunch occurred.

The adapter also rejects symlink/non-regular saved plans and resolves accepted
plan paths before invoking Terraform with `-chdir`, closing a relative-path
interpretation seam.

## Qualification image receipt integrity repair

Image binding now rejects receipts with an unregistered record identity,
malformed canonical self-digest, or missing builder termination/fresh provider
absence proof. A tampered-receipt regression passes, and the historical
action-011 image receipt remains valid only for its old source commit; it is
still rejected for the current checkout.

## Receipt and terminal-context hardening

The future authority/receipt path now rejects missing, boolean, non-finite, or
malformed projection values with typed cloud errors. The runner also retains
the complete post-submit execution context when provider absence validation
returns a record that fails the teardown contract, instead of emitting only a
bare validation exception. Its generic result surface leaves
`submit_count_proven` unproven until the concrete CloudTrail check captures the
single matching submission; the concrete receipt path requires that live
evidence. Focused runner/receipt regressions and Ruff pass. No AWS mutation,
new action, ledger row, relaunch, or scientific workload occurred.

## Remaining blockers before the separately authorized official study

1. The dual-L40S qualification is not passed. Action 011 is exhausted; any
   future qualification attempt requires a fresh action and authority package,
   plus a fresh immutable image receipt bound to the current source revision.
2. Step 14 remains `launch_blocked`: the real authority-backed P0 power/tier
   receipt and packet, assignment, detectability, and unblind receipts are
   still missing from the canonical index.
3. Tasks 6–10 remain `implementation_complete; E2E_pending`; bounded Step 4A
   continuity, analysis, and Task 10 release preparation are not a scientific
   result of record.
4. The official P0/Step 4B authority, canonical lineage, execution, unblind,
   analysis, and claim-promotion gates remain separately authorized work and
   were not performed here.

The precise unsigned handoff checklist is
`59-unsigned-p0-step14-checklist-20260803.md`.

## Latest Batch identity and plan-admission repair

The future concrete runner now binds each Batch child response to the exact
requested `parent_job_id:index` and provider array index, orders the two worker
identities by index, and retains observed parent/child context on malformed
identity or raw-artifact retrieval failure. A partial raw-artifact map is
reported as typed `raw_artifact_retrieval_failure`; it cannot be mistaken for
successful two-worker evidence. Terraform-show parsing also rejects a missing
or ambiguous job-definition type/platform and requires explicit `container`
plus EC2-only capabilities.

Focused cloud/receipt/provider tests, changed-file Ruff, Terraform checks,
status validation, the CPU-only fixture check, and graph refresh pass. This
was source-only closure work: action-011 remains exhausted, no AWS mutation or
new ledger row occurred, and no official scientific work was run.

## Latest Terraform cross-resource binding repair

Terraform-show admission now compares a concrete queue
`compute_environment` ARN to the planned compute-environment ARN and requires
exactly one compute-environment launch-template binding. When Terraform
renders concrete IDs, the bound launch-template ID must equal the declared
launch-template resource ID. Focused queue/template mismatch regressions and
changed-file Ruff pass. AWS reauthentication did not yield operator
credentials, so no fresh image, plan, AWS mutation, action, or relaunch was
performed; action-011 remains the single sealed terminal no-go.

## Latest freshness and provider-role hardening

The runner now applies the same alphanumeric action-token boundary when
searching retained evidence and the authoritative spend ledger. Terraform-show
admission and provider readback now require and verify the concrete Spot fleet
role ARN instead of allowing a missing role to skip verification. A focused
ledger-boundary regression and Spot-role regression pass. No AWS mutation or
qualification relaunch occurred.

## Continuity and release-gate revalidation

The read-only Task 6 continuity check passed graph/freeze/projection/blinding,
taint, task-block, and unchanged-root checks over the preserved implementation
verification root. The read-only Task 7 check passed authority reload, seed,
roster, live vocabulary, gate, verdict, and row-count checks; both remain
implementation verification only. The Step 14 campaign-spec builder correctly
exited 2 and named the missing canonical P0 power report and P0 core receipt,
so `launch_blocked` remains the honest disposition.

## Latest source-only semantic and evidence hardening — 2026-08-03

The future qualification path now closes three concrete fail-open seams found
by independent bounded agent-session audits:

- Terraform provider-generated IDs may remain unknown in a fresh create plan,
  but the parser now requires Terraform's exact configuration reference graph
  for both the compute-environment launch template and queue binding. Multiple
  alias/index matches are rejected as ambiguous.
- The concrete AWS adapter enumerates every inline and attached managed policy
  on the verified worker role, follows IAM pagination, and retains only
  sanitized policy/document hashes. Any Allow for S3 outside the five exact
  fixture reads and two exact worker writes—including wildcard, ListBucket,
  other-action, NotAction, or NotResource forms—is rejected before apply.
  The live 17-case IAM simulation remains required.
- CloudTrail matching now covers the exact action job name as well as the
  submitted parent ID, so a duplicate same-action submission cannot evade the
  one-submit proof. Teardown discovers all action-named Batch jobs across
  terminal and active states before disable/drain/destroy.

The CPU-only image fixture check now executes both worker indexes and verifies
two immutable, byte-identical raw objects. The image-build bootstrap also pulls
the exact fresh ECR digest after push and re-inspects its fixed ENTRYPOINT,
empty CMD, source label, and base label; the future image receipt must bind
that digest-bound config check. Focused cloud/image/bootstrap tests, Ruff,
Terraform validation, status validation, fixture smoke, and graph refresh all
pass. The default AWS CLI session is expired, so no fresh plan, image build,
IAM mutation, action, ledger row, relaunch, or scientific workload occurred.
Action-011 remains the sealed terminal no-go.

## Final source-only audit closure — 2026-08-03

The final bounded agent-session audit was converted into focused fail-closed
repairs. The plan parser now proves exact single-base Terraform references,
rejects extra planned resources and malformed unknown markers, and verifies
the profile/role chain through RoleId. Worker IAM capture rejects incomplete
pagination and broad resource-policy S3 grants, while newly emitted receipts
retain a separate sanitized policy-inventory digest.

CloudTrail submit evidence now requires the actual returned parent ID. Drain
and absence verification require complete rows for every requested Batch job,
retain the drained set, and scan action-named CloudTrail submissions even when
the queue has already been deleted. A post-submit receipt-construction error
is retained as a sanitized terminal record. The image-builder sidecar now
self-binds raw post-push inspect bytes and the two-worker fixture runtime, and
the validator requires AWS CLI v2 plus those sidecars. Focused tests, lint,
Terraform, status, fixture, and graph checks pass. AWS credentials are
expired, so no fresh image/plan/provider mutation or relaunch occurred.

## Action-012 image-build terminal disposition — 2026-08-03

After AWS credentials were restored, the fresh action
`qualification-image-build-012` was executed once under its signed admission.
The builder instance `i-062fdd2f4f6469517` completed its CPU-only fixture and
ECR push, but the required post-push image-config receipt was zero bytes. The
concrete cause is a local bootstrap semantic defect: the stdin-backed
`python3 -` sidecar was launched without Docker `--interactive`, so Python
received EOF and exited successfully without emitting the receipt. The
bootstrap incorrectly recorded `COMPLETE`; the image is rejected and is not
qualified for Batch. No Batch job or scientific workload was submitted, no
retry occurred, and no worker/raw/recovery result exists.

Action-012 evidence is bound by plan/composite
`d2b7152292f40de9038b8c18f8326c78ea1a265952db1b1407a4ee1787680bfe`, signed
package `d333a1e86a116779b3f8326be8462f4fd99164d041e36aac767ecca68dd9fbf4`,
envelope `e66de41e3efc1897d11258d7b1a3d6f6ae0d4b0de31d8285d74a8839b084ca11`,
admission `bf4f1681102f79e340fd625998adaaaf884a2befe5ed25b73afc53bac1c9bb02`,
and terminal receipt `3e5f64464e6eb6c4d77e8dcb6fc91e1c578a32a92408ac7f0c5ebb0c68b00b95`.
The pushed image digest is
`sha256:5844cad087fa1b99b88f456693612743567eb80d2c481b316443033855b0ff4d`;
its fixture and CLI checks passed, but the empty receipt is a hard rejection.

The builder terminated itself after 445 seconds. Final absence proof found no
action instance, root volume, ENI, IAM instance profile/role, or security
group. The rejected ECR digest/tag and raw S3 output remain retained as
forensic evidence. The committed `--interactive` repair is source-only and
requires a separately fresh, newly bound image-build action before any future
Batch admission. This lane therefore closes honestly as a terminal no-go, not
as a qualification pass; official P0/Step-4B work remains excluded and
blocked.

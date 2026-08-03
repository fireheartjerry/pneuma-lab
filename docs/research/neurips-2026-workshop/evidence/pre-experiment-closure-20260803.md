# Pre-experiment closure — 2026-08-03

## Current disposition

`post_launch_terminal_no_go`. The stale action-004 IAM-preflight report that
previously occupied this path is superseded by the final action-011 closure.

The fresh action `dual-l40s-qualification-011` passed the plan, account,
image, IAM, authority, and projection gates, then launched exactly one
size-two Batch array. Both children ended `FAILED` with provider status reason
`JobQueue deleted` and zero attempts. No worker started, no raw artifact or
worker identity exists, and no recovery drill ran. No retry occurred.

## Sealed qualification evidence

- Immutable fixture-only image:
  `sha256:5433527fb588c009d6cf16a5ac4278c463bbb5fab0c0a6826147b4c98f2e83ff`
- IAM policy SHA-256:
  `73666739e4e41f136fd11049715130e9b5086e6cafc21cee642ebe179fb0f24b`
- IAM simulation matrix SHA-256:
  `12301cd1b1bcaf51d8458de4d012f1a3be960a7cb589e833209d54cf52be3b2c`
- Saved plan SHA-256:
  `7c665827ed95bd4d55657e81ee9c2edf718f287cd58af325b4c714ce2b901ddc`
- Raw Terraform show SHA-256:
  `01387c775cf497046bbcc4cc6a82b08052f836a127dca214660bacf03ed70141`
- Composite plan binding:
  `f4b627f943a0989222fd0aab53d8d01329ccca733de12135b54777914d5d0516`
- KMS package SHA-256:
  `8b3ae0892add4452464c00b0982f2dccc24a9a5cdf8dd944e6fa8783c8eddb7e`
- Spot projection: USD 4.4842, strictly below USD 100.

The complete sanitized receipt is
`dual-l40s-qualification-011-execution-receipt-20260803.json` with SHA-256
`2452cc4a1a531e39bf170c038c8ba56829b57ea77b58ea532b2f61acb3990854`.

## Teardown

Fresh provider reads prove live jobs, active definition, queue, compute
environment, launch template, instances, volumes, ENIs, and security group
absent; the action output prefix is empty. AWS retains only the deregistered
`INACTIVE` job-definition revision as provider history. The teardown verifier
repair and focused regression are committed.

## Post-closure runner hardening

The concrete qualification CLI was adversarially audited after action-011. It
now preserves terminal Batch parent/child observations, captures the exact
single-launch CloudTrail evidence, proves the empty action output prefix, and
builds the registered schema-bound receipt. It refuses to write an execution
receipt for pre-launch failures. Focused provider-free cloud/schema tests pass;
no AWS launch or retry occurred during this repair.

## Follow-up readiness seam repair

The concrete runner now performs and validates the exact 15-case live IAM
simulation matrix before Terraform apply. Its sanitized digest is bound to the
parsed plan's independently verified attached worker role and action-specific
policy hash; the old caller-supplied matrix-hash argument is gone. The runner
also rejects reuse of action IDs already represented in retained evidence and
refuses receipt overwrite. Focused IAM/runner/receipt/schema regressions pass.
No AWS mutation, relaunch, or scientific workload occurred.

## Second executable-path seam repair

The follow-up audit repaired the concrete Batch timeout binding, live S3
bucket-policy-aware IAM simulation, independent live KMS public-key/signature
verification, authoritative spend-ledger freshness, and future qualification
package binding. The package now binds the exact plan bytes, action policy
hash, immutable image, four-AZ map, action-scoped output prefix, fresh
sub-USD-100 projection, action id, and zero retries. The Terraform worker
policy source now grants only the five exact input reads and two exact raw
output writes required by the fixed publisher; no S3 list/read/delete/decrypt,
wildcard, or unnecessary multipart permission remains in that inline policy.
Focused cloud, signer, schema, and Terraform tests pass. This is readiness
repair only: the sealed action-011 terminal no-go is unchanged and no AWS
resource or scientific workload was launched.

## Final source-binding repair

The future qualification path now rejects account plans without an exact,
lowercase SHA-256 binding for the raw Terraform-show bytes. It also reads and
hash-checks the exact `bounded-experiment-access` inline policy on the verified
worker role immediately before IAM simulation, failing closed on policy drift.
The focused regression is green. This changes no sealed action-011 fact and
authorizes no relaunch or official scientific work.

## Plan/show consistency hardening

The future qualification path now rejects malformed or conflicting top-level
and nested Terraform-show SHA-256 metadata. Locked apply also reports an
explicit typed failure if the reread raw-show digest is unavailable or invalid,
before any mutation. The focused conflict regression is green. This is
source-only hardening; action-011 remains exhausted and unchanged.

## Runtime, managed-AMI, and IAM boundary hardening

The future fixed image path now checks that the action ID, artifact prefix, and
output-root environment variables identify the same exact action-scoped output
prefix before materialization or publication. Terraform-show admission now
requires an AWS Batch managed compute environment and rejects a custom AMI
field nested in compute resources. Future IAM simulation adds explicit denied
checks for KMS decrypt and IAM policy administration. Focused probe, runner,
Terraform, IAM, and image-fixture tests pass; the sealed action-011 receipt is
unchanged and was not retried.

## Terraform variable/resource parity repair

The future qualification parser now requires the planned compute-environment
subnets and security groups to match the bound Terraform `subnet_ids` and
`security_group_ids` variables exactly. A focused negative regression and all
bounded cloud/static checks pass. This was source-only closure work with no AWS
mutation, spend, new action, or ledger reservation; the action-011 no-go is
unchanged.

## Shared Terraform locking and Step 14 gate hardening

The qualification stack now declares encrypted S3 state with Terraform-native
`use_lockfile` locking and retains the 60-second lock timeout on apply and
destroy. The Step 14 spec-builder test now executes the missing-receipt path and
proves it fails closed. Backend initialization was not run against AWS; no
provider mutation, spend, new action, or scientific workload occurred.

The concrete runner now initializes the committed backend with
`terraform init -reconfigure -lockfile=readonly` before reading the saved plan,
and the adapter rejects load/apply/destroy without that successful state. The
lock-timeout mutation contract remains intact.

## Step 14 real-power input and authority-gate repair

The Step 14 builder now requires the canonical sealed P0 power/tier report and
independent canonical artifact-root receipt at
`build/research/neurips-2026-workshop/p0-canonical/power/p0-power-report.json`
and `build/research/neurips-2026-workshop/p0-canonical/p0-core-receipt.json`.
The current checkout lacks both, so generation exits nonzero instead of using
the prose design brief as a power-report substitute. A complete synthetic
authority-binding regression is green; no P0 authority or scientific work was
created.

## Remaining gates before official P0 / Step 4B

1. The dual-L40S qualification is not passed; action-011 is exhausted. No
   relaunch is permitted in this closure.
2. Step 14 remains `launch_blocked` pending the real authority-backed P0
   power/tier receipt and packet, assignment, detectability, and unblind
   receipts.
3. Tasks 6–10 remain `implementation_complete; E2E_pending`; bounded Step 4A
   continuity, analysis, and Task 10 release preparation do not constitute a
   scientific result.
4. The official P0/Step 4B authority, lineage, execution, unblind, analysis,
   and claim-promotion gates remain separately reserved and were not run.

No scientific result, benchmark/model result, pilot, unblind, analysis, or
claim promotion exists.

The current source-only runner hardening additionally requires complete empty
output-prefix proof at preflight and teardown, exact action-token freshness
matching across nested evidence paths, and an explicit mode-600 `.tfvars` file
whose bytes remain unchanged through locked apply and destroy. These checks
are covered by focused regressions; they do not alter the terminal action-011
no-go or authorize another launch.

The latest source-only repair makes malformed or non-finite authority
projections typed failures, preserves the full post-submit context when
teardown absence validation fails, and prevents the generic runner from
claiming an exactly-once submission before CloudTrail evidence is captured.
Focused regressions pass. No new action, spend-ledger row, AWS mutation, or
scientific workload was created.

The saved-plan path is now required to be a regular file and is normalized to
an absolute path before Terraform `-chdir` execution.

Qualification image binding also validates the registered receipt identity,
canonical receipt digest, and fresh builder-absence proof before accepting an
image/source pair.

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

# 51 — Minimal AWS bootstrap action request

**Prepared:** 2026-07-31
**Decision:** `not_authorized`

## Exact action

Create only the non-compute substrate required to make a later account-bound
Terraform plan possible in the authenticated AWS account and `us-east-1`:

1. a private, encrypted, versioned S3 artifact bucket named
   `pneuma-phase-b-892077329800`, with public access blocked and no public
   policy or ACL;
2. a `PAY_PER_REQUEST` DynamoDB lease table named `pneuma-phase-b-leases`,
   keyed by string attribute `lease_key`, with point-in-time recovery enabled;
3. a dedicated security group in the existing default VPC, with no ingress and
   only the minimum egress needed for later package/model retrieval;
4. a Batch service role and ECS instance role/instance profile, each limited to
   the AWS managed baseline required for a disabled Batch compute environment;
5. local, redacted creation receipts and a backend-free/account-bound Terraform
   plan that references these exact resource identifiers.

## Hard ceilings and exclusions

- Maximum provider scope: exactly the five resources/classes above in
  `us-east-1`.
- Maximum direct cost: USD 2.00 for the first 30 days, excluding any later
  storage explicitly uploaded by a separate authority.
- No EC2 instance, AWS Batch compute environment, job definition, ECR
  repository/image push, AMI, EBS volume/snapshot, model or benchmark download,
  GPU use, endpoint, reservation, quota change, experiment, or Azure action.
- If any command would create compute capacity or exceed the resource list, it
  must stop before mutation.

## Why this is separate

The currently authenticated account has a default VPC but no S3 bucket and no
DynamoDB table. The primary Terraform module consumes these identifiers and
also requires later image and AMI receipts; this bootstrap does not create or
authorize those later artifacts or the compute environment.

## Approval form

A valid authorization must identify this document by its whole-file SHA-256,
say `authorize B1`, repeat the USD 2.00/30-day ceiling, and come from the human
operator. Any byte change invalidates the approval. General cloud permission,
credits, or approval of a different digest is insufficient.

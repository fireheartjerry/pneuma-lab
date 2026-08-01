# 52 — B1 AWS bootstrap receipt

**Date:** 2026-07-31
**Authority:** B1 authorization over document 51 SHA-256
`ddaa278d57610454e895494d84a45118b66223a274a326d51ed09d18286c4cc6`
**Scope:** non-compute bootstrap only, `us-east-1`

## Created and verified

- Private artifact bucket `pneuma-phase-b-…9800`: public-access block fully
  enabled, AES-256 default encryption, versioning enabled, and
  `BucketOwnerEnforced` ownership.
- `pneuma-phase-b-leases`: `PAY_PER_REQUEST`, KMS server-side encryption, and
  point-in-time recovery enabled for 35 days.
- Dedicated bootstrap security group ending `…477eb`: no ingress; egress only
  TCP 443 to IPv4 destinations and UDP/TCP 53 to the default-VPC resolver
  (`172.31.0.2/32`).
- Batch service role and ECS instance role/profile, each with only its AWS
  managed baseline (`AWSBatchServiceRole` and
  `AmazonEC2ContainerServiceforEC2Role`, respectively).
- A backend-free account-bound Terraform plan consisting solely of data reads
  for these five identifiers. It showed output values only and no resource
  actions.

## Account-bound plan receipt

The authenticated CloudShell plan read the exact S3 bucket, DynamoDB table,
security group, Batch role, and ECS instance profile. It used Terraform 1.15.8
with `hashicorp/aws` 5.91.0. Compact content digests retained from that run:

| artifact | SHA-256 |
| --- | --- |
| read-only Terraform configuration | `4df3ca5ec4428e3caf048823d0e9bbf37d1b8e1cf4c5beaebfba1d6720f24f8d` |
| binary plan | `42cbd64e7aeac9d34824183b2bf27aeeab684a0587e3a02fb67d48054f6451ce` |
| JSON plan | `c354a555992f68bd690d773147b722e76a9750a26c18212d3aa30479efbbaa76` |

`infra/terraform/bootstrap-verification/` is the tracked, backend-free
equivalent. It contains no `resource` blocks and cannot make a provider change.

## Boundary

This receipt creates no EC2 instance, Batch compute environment or job,
container registry/image, AMI, volume, snapshot, model or benchmark download,
GPU allocation, endpoint, reservation, quota change, experiment, or Azure
resource. It is bootstrap/account evidence only, not Step 5B, Step 7B,
one-GPU admission, Step 14 approval, pilot authority, or a scientific result.

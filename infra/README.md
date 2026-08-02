# AWS C160 infrastructure

`terraform/` implements the two-worker `g6e.2xlarge` AWS Batch Spot topology.
The compute environment and queue are created **disabled** with zero desired
vCPUs; applying infrastructure cannot start an experiment by itself.

The stack includes:

- a dedicated VPC with two private, no-public-IP subnets and no inbound worker
  security-group rules;
- private S3, ECR, CloudWatch Logs, and SSM connectivity;
- an immutable, scan-on-push ECR repository;
- a private, versioned, encrypted S3 bucket with bounded lifecycle rules;
- a point-in-time-recoverable encrypted DynamoDB lease table;
- separate worker and watcher identities, with no lease-renew action on the
  worker and tag-bounded EC2 termination authority on the watcher;
- an IMDSv2-only launch template with an encrypted, auto-deleting gp3 volume;
- a disabled, zero-idle-vCPU Batch Spot environment capped at two independent
  `g6e.2xlarge` workers (16 vCPUs total); and
- monthly AWS Budget notifications at forecast 50%, actual 80%, and actual
  100%.

## Prepare and verify

Copy `environments/aws-example.tfvars` to an ignored environment-specific file
and replace every placeholder. The AMI must be the exact GPU-compatible AWS
Batch AMI accepted by the qualification receipt; the bootstrap digest must be
the receipt-bound SHA-256. Never use `-target` to bypass dependencies.

If the artifact bucket already exists, import it before planning:

```powershell
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform import -var-file=environments/aws.tfvars aws_s3_bucket.artifacts BUCKET_NAME
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan -var-file=environments/aws.tfvars -out=c160.tfplan
terraform -chdir=infra/terraform show c160.tfplan
```

An apply creates chargeable interface VPC endpoints even while compute remains
disabled. Applying, enabling the queue/environment, registering a job
definition, submitting a job, and scientific admission are separate actions.
The saved plan, confirmed Budget email, root MFA, AMI/bootstrap receipts, image
digest, and explicit spend authorization are mandatory before apply or launch.

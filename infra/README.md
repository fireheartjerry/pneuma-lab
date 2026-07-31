# Deployment and teardown preparation (Step 12)

The Terraform files are reviewable static declarations only. They pin the AWS
primary controller to one `g6e.2xlarge` (8 vCPUs, one L40S); no TP2 or
multi-GPU compute shape is declared. Environment tfvars carry region/name/tag
inputs, never scientific model, roster, endpoint, or analysis inputs. No
`terraform apply` is authorized in Phase B.

Before any future deployment, run the separately authorized preflight and use
an ownership manifest for teardown. Tags cross-check residuals but are never
deletion authority. The fixed dry-run teardown order is jobs, queue, compute,
instances, volumes/endpoints, registry, then buckets after copy receipts.

region               = "us-east-1"
name_prefix          = "pneuma-c160"
ami_id               = "ami-REPLACE_WITH_PINNED_BATCH_GPU_AMI"
bootstrap_sha256     = "REPLACE_WITH_64_LOWERCASE_HEX"
create_batch_resources = false
artifact_bucket_name = "pneuma-phase-b-REPLACE_ACCOUNT_ID"
artifact_prefix      = "runs"
root_volume_gib      = 3072
monthly_budget_usd   = 1000
budget_alert_email   = "REPLACE_WITH_CONFIRMED_EMAIL"
gpu_worker_image     = "000000000000.dkr.ecr.us-east-1.amazonaws.com/REPLACE@sha256:0000000000000000000000000000000000000000000000000000000000000000"

common_tags = {
  Owner       = "REPLACE"
  Environment = "research"
}

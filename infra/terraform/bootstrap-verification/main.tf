terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.91.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# This is an account-bound, read-only verification module.  It has no resource
# blocks, no backend, and therefore cannot create capacity or mutate AWS state.
data "aws_s3_bucket" "artifact" {
  bucket = var.bucket_name
}

data "aws_dynamodb_table" "lease" {
  name = var.lease_table_name
}

data "aws_security_group" "bootstrap" {
  id = var.security_group_id
}

data "aws_iam_role" "batch_service" {
  name = var.batch_service_role_name
}

data "aws_iam_instance_profile" "ecs_instance" {
  name = var.ecs_instance_profile_name
}

output "artifact_bucket_arn" {
  value = data.aws_s3_bucket.artifact.arn
}

output "lease_table_arn" {
  value = data.aws_dynamodb_table.lease.arn
}

output "security_group_id" {
  value = data.aws_security_group.bootstrap.id
}

output "batch_service_role_arn" {
  value = data.aws_iam_role.batch_service.arn
}

output "ecs_instance_profile_arn" {
  value = data.aws_iam_instance_profile.ecs_instance.arn
}

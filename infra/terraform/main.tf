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

# Static contract only. This module is intentionally never applied in Phase B.
resource "aws_batch_compute_environment" "controller" {
  compute_environment_name = "${var.name_prefix}-controller"
  type                     = "MANAGED"
  state                    = "DISABLED"
  service_role             = var.batch_service_role_arn

  compute_resources {
    type                = "EC2"
    allocation_strategy = "BEST_FIT"
    min_vcpus           = 0
    max_vcpus           = 8
    instance_type       = ["g6e.2xlarge"]
    image_id            = var.ami_id
    instance_role       = var.ecs_instance_profile_arn
    security_group_ids  = [var.security_group_id]
    subnets             = [var.subnet_id]
  }
}

# This is intentionally a single whole-node admission job. The image variable
# may be populated only by a Step 7B immutable digest receipt.
resource "aws_batch_job_definition" "one_gpu_admission" {
  name                  = "${var.name_prefix}-one-gpu-admission"
  type                  = "container"
  platform_capabilities = ["EC2"]

  container_properties = jsonencode({
    image      = var.controller_image
    privileged = true
    resourceRequirements = [
      { type = "GPU", value = "1" },
      { type = "VCPU", value = "8" },
      { type = "MEMORY", value = "60000" },
    ]
  })
}

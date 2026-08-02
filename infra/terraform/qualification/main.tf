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

# This stack is intentionally separate from infra/terraform.  It owns only
# disabled-at-rest qualification control-plane objects; workers appear only
# for the two explicitly submitted admission jobs.
resource "aws_batch_compute_environment" "qualification" {
  compute_environment_name = var.name_prefix
  type                     = "MANAGED"
  state                    = "ENABLED"
  service_role             = var.batch_service_role_arn

  compute_resources {
    type                = "SPOT"
    allocation_strategy = "SPOT_PRICE_CAPACITY_OPTIMIZED"
    min_vcpus           = 0
    desired_vcpus       = 0
    max_vcpus           = 16
    instance_type       = ["g6e.2xlarge"]
    image_id            = var.ami_id
    instance_role       = var.instance_role_arn
    spot_iam_fleet_role = var.spot_fleet_role_arn
    security_group_ids  = var.security_group_ids
    subnets             = var.subnet_ids
  }
}

resource "aws_batch_job_queue" "qualification" {
  name     = var.name_prefix
  state    = "ENABLED"
  priority = 1

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.qualification.arn
  }
}

resource "aws_batch_job_definition" "worker" {
  name                  = "${var.name_prefix}-worker"
  type                  = "container"
  platform_capabilities = ["EC2"]

  container_properties = jsonencode({
    image      = var.gpu_worker_image
    privileged = true
    resourceRequirements = [
      { type = "GPU", value = "1" },
      { type = "VCPU", value = "8" },
    ]
    # The worker entrypoint must run its fixture-only probe and watchdog.
    command = ["qualification-entrypoint", "--watchdog-seconds", "3600", "--max-retries", "0"]
  })

  timeout {
    attempt_duration_seconds = 3600
  }

  retry_strategy {
    attempts = 1
  }
}

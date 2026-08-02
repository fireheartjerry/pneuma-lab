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

locals {
  qualification_tags = {
    QualificationPurpose   = "dual-l40s-admission-only"
    QualificationTopology  = "two-g6e-2xlarge-l40s"
    QualificationManagedBy = "pneuma-ephemeral-runner-v1"
    QualificationAction    = var.name_prefix
  }
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
  tags = local.qualification_tags
}

resource "aws_batch_job_queue" "qualification" {
  name     = var.name_prefix
  state    = "ENABLED"
  priority = 1

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.qualification.arn
  }
  tags = local.qualification_tags
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
    # This image-bound adapter invokes the fixed two-rung probe and binds the
    # Batch array index to worker 0 or 1. Ref:: is resolved by Batch per child.
    command = ["python", "-m", "pneuma_lab.cloud.fixed_admission_probe"]
    environment = [
      { name = "QUALIFICATION_MODEL", value = var.qualification_model },
      { name = "QUALIFICATION_MODEL_REVISION", value = var.qualification_model_revision },
      { name = "QUALIFICATION_PROTOCOL", value = var.protocol_path },
      { name = "QUALIFICATION_ARCHITECTURE", value = var.architecture_path },
      { name = "QUALIFICATION_AUTHORIZATION", value = var.authorization_path },
      { name = "QUALIFICATION_IMAGE", value = var.image_path },
      { name = "QUALIFICATION_INPUT_LOCK", value = var.input_lock_path },
      { name = "QUALIFICATION_OUTPUT", value = var.output_path },
    ]
  })

  timeout {
    attempt_duration_seconds = 3600
  }

  retry_strategy {
    attempts = 1
  }
  tags = local.qualification_tags
}

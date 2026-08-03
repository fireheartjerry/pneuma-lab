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
    QualificationAction    = var.qualification_action_id
    QualificationActionId  = var.qualification_action_id
    QualificationCode      = var.qualification_code
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
    launch_template {
      launch_template_id = aws_launch_template.qualification.id
      version            = aws_launch_template.qualification.latest_version
    }
    tags = local.qualification_tags
  }
  tags = local.qualification_tags
}

resource "aws_launch_template" "qualification" {
  name_prefix = "${var.name_prefix}-worker-"

  tag_specifications {
    resource_type = "instance"
    tags          = local.qualification_tags
  }

  tag_specifications {
    resource_type = "volume"
    tags          = local.qualification_tags
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
      { type = "MEMORY", value = "60000" },
    ]
    # The immutable image ENTRYPOINT dispatches fixed admission mode. No
    # command override is intentional: an empty override would erase it.
    environment = [
      { name = "QUALIFICATION_CODE", value = var.qualification_code },
      { name = "QUALIFICATION_ACTION_ID", value = var.qualification_action_id },
      { name = "QUALIFICATION_ARTIFACT_PREFIX", value = var.output_path },
      { name = "QUALIFICATION_MODEL", value = var.qualification_model },
      { name = "QUALIFICATION_MODEL_REVISION", value = var.qualification_model_revision },
      { name = "QUALIFICATION_PROTOCOL", value = var.protocol_path },
      { name = "QUALIFICATION_ARCHITECTURE", value = var.architecture_path },
      { name = "QUALIFICATION_AUTHORIZATION", value = var.authorization_path },
      { name = "QUALIFICATION_IMAGE", value = var.image_path },
      { name = "QUALIFICATION_INPUT_LOCK", value = var.input_lock_path },
      { name = "QUALIFICATION_OUTPUT_ROOT", value = var.output_path },
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

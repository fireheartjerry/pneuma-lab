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

  default_tags {
    tags = merge(var.common_tags, {
      Project   = "pneuma-lab"
      ManagedBy = "terraform"
      Purpose   = "neurips-2026-resampling-null"
    })
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "experiment" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = "${var.name_prefix}-vpc" }
}

resource "aws_subnet" "private" {
  count                   = 2
  vpc_id                  = aws_vpc.experiment.id
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  cidr_block              = cidrsubnet(aws_vpc.experiment.cidr_block, 8, count.index)
  map_public_ip_on_launch = false
  tags                    = { Name = "${var.name_prefix}-private-${count.index + 1}" }
}

resource "aws_security_group" "worker" {
  name        = "${var.name_prefix}-worker"
  description = "No inbound access; HTTPS egress only"
  vpc_id      = aws_vpc.experiment.id

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.experiment.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_vpc.experiment.main_route_table_id]
}

locals {
  interface_endpoints = toset(["ecr.api", "ecr.dkr", "logs", "ssm", "ssmmessages", "ec2messages"])
}

resource "aws_vpc_endpoint" "interface" {
  for_each            = local.interface_endpoints
  vpc_id              = aws_vpc.experiment.id
  service_name        = "com.amazonaws.${var.region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.endpoint.id]
  private_dns_enabled = true
}

resource "aws_security_group" "endpoint" {
  name        = "${var.name_prefix}-endpoints"
  description = "HTTPS from experiment workers to private AWS endpoints"
  vpc_id      = aws_vpc.experiment.id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.worker.id]
  }
}

resource "aws_ecr_repository" "worker" {
  name                 = "${var.name_prefix}-worker"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  encryption_configuration {
    encryption_type = "AES256"
  }
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "worker" {
  repository = aws_ecr_repository.worker.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Expire untagged images after seven days"
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = 7
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_s3_bucket" "artifacts" {
  bucket = var.artifact_bucket_name
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }

}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    id     = "expire-experiment-artifacts"
    status = "Enabled"
    filter {
      prefix = "${var.artifact_prefix}/"
    }
    expiration {
      days = var.artifact_expiration_days
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  rule {
    id     = "expire-step5b-payloads"
    status = "Enabled"
    filter {
      prefix = "${var.artifact_prefix}/step5b/payloads/"
    }
    expiration {
      days = var.step5b_payload_expiration_days
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_dynamodb_table" "leases" {
  name         = "${var.name_prefix}-leases"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "lease_key"
  attribute {
    name = "lease_key"
    type = "S"
  }
  point_in_time_recovery {
    enabled = true
  }
  server_side_encryption {
    enabled = true
  }
}

resource "aws_cloudwatch_log_group" "batch" {
  name              = "/aws/batch/${var.name_prefix}"
  retention_in_days = 30
}

resource "aws_launch_template" "worker" {
  name_prefix = "${var.name_prefix}-worker-"

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      encrypted             = true
      delete_on_termination = true
      volume_size           = var.root_volume_gib
      volume_type           = "gp3"
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  monitoring {
    enabled = true
  }
  tag_specifications {
    resource_type = "instance"
    tags          = { Name = "${var.name_prefix}-batch-worker" }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_batch_compute_environment" "worker" {
  count                    = var.create_batch_resources ? 1 : 0
  compute_environment_name = "${var.name_prefix}-worker"
  type                     = "MANAGED"
  state                    = "DISABLED"
  service_role             = aws_iam_role.batch_service.arn

  compute_resources {
    type                = "EC2"
    allocation_strategy = "BEST_FIT_PROGRESSIVE"
    min_vcpus           = 0
    max_vcpus           = 8
    desired_vcpus       = 0
    instance_type       = ["g6e.2xlarge"]
    image_id            = var.ami_id
    instance_role       = aws_iam_instance_profile.worker.arn
    security_group_ids  = [aws_security_group.worker.id]
    subnets             = aws_subnet.private[*].id

    launch_template {
      launch_template_id = aws_launch_template.worker.id
      version            = aws_launch_template.worker.latest_version
    }

    tags = { BootstrapSHA256 = var.bootstrap_sha256 }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_batch_job_queue" "worker" {
  count    = var.create_batch_resources ? 1 : 0
  name     = "${var.name_prefix}-worker"
  state    = "DISABLED"
  priority = 1
  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.worker[0].arn
  }
}

# Whole-node admission job. The image may be populated only from the immutable
# Step 7B image receipt; registering it does not enable or submit work.
resource "aws_batch_job_definition" "one_gpu_admission" {
  count                 = var.create_batch_resources ? 1 : 0
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

resource "aws_budgets_budget" "monthly" {
  name         = "${var.name_prefix}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_alert_email]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }
}

output "launch_state" {
  value = "DISABLED"
}
output "batch_compute_environment" {
  value = try(aws_batch_compute_environment.worker[0].arn, null)
}
output "batch_job_queue" {
  value = try(aws_batch_job_queue.worker[0].arn, null)
}
output "ecr_repository_url" {
  value = aws_ecr_repository.worker.repository_url
}
output "artifact_bucket" {
  value = aws_s3_bucket.artifacts.id
}
output "lease_table" {
  value = aws_dynamodb_table.leases.name
}

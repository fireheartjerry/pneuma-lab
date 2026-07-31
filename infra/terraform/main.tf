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
  compute_resources {
    type                = "EC2"
    allocation_strategy = "BEST_FIT"
    min_vcpus           = 0
    max_vcpus           = 48
    instance_type       = ["g6e.12xlarge"]
    image_id            = var.ami_id
  }
}

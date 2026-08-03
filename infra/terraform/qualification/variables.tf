variable "region" {
  type    = string
  default = "us-east-1"
}

variable "vpc_id" {
  type = string
  validation {
    condition     = can(regex("^vpc-[0-9a-f]+$", var.vpc_id))
    error_message = "vpc_id must be a concrete VPC identifier bound to the verified subnets and security group."
  }
}

variable "name_prefix" {
  type = string
}

variable "qualification_action_id" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{2,79}$", var.qualification_action_id))
    error_message = "qualification_action_id must be the signed action identifier."
  }
}

variable "qualification_code" {
  type        = string
  description = "Signed code artifact or literal passed to the fixed probe's required --code argument."
  validation {
    condition     = length(trimspace(var.qualification_code)) > 0 && length(var.qualification_code) <= 256
    error_message = "qualification_code must be a nonempty string of at most 256 characters."
  }
}

variable "gpu_worker_image" {
  type = string
  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.gpu_worker_image))
    error_message = "gpu_worker_image must be an immutable sha256 digest reference."
  }
}

variable "batch_service_role_arn" {
  type = string
}

variable "instance_role_arn" {
  type = string
}

variable "spot_fleet_role_arn" {
  type = string
}

variable "security_group_ids" {
  type = list(string)
  validation {
    condition     = length(var.security_group_ids) == 1
    error_message = "qualification requires exactly one zero-ingress security group."
  }
}

variable "subnet_ids" {
  type = list(string)
  validation {
    condition     = length(var.subnet_ids) == 4 && length(distinct(var.subnet_ids)) == 4
    error_message = "qualification requires four distinct existing subnets; provider validation checks their AZs."
  }
}

variable "qualification_model" {
  type = string
  validation {
    condition     = var.qualification_model == "fixture-only-cuda"
    error_message = "qualification_model must be the fixed fixture-only-cuda probe; subject-model execution is excluded."
  }
}

variable "qualification_model_revision" {
  type = string
  validation {
    condition     = var.qualification_model_revision == "fixture-only-v1"
    error_message = "qualification_model_revision must be the fixed fixture-only-v1 probe revision."
  }
}

variable "protocol_path" {
  type = string
}

variable "architecture_path" {
  type = string
}

variable "authorization_path" {
  type = string
}

variable "image_path" {
  type = string
}

variable "input_lock_path" {
  type = string
}

variable "output_path" {
  type = string
}

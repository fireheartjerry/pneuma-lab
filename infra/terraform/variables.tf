variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9-]{3,32}$", var.name_prefix))
    error_message = "name_prefix must contain 3-32 lowercase letters, digits, or hyphens."
  }
}

variable "qualification_action_id" {
  type        = string
  description = "Exact action identity bound to the signed qualification admission."
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{2,79}$", var.qualification_action_id))
    error_message = "qualification_action_id must be a lowercase action identifier."
  }
}

variable "qualification_code" {
  type        = string
  description = "Opaque code passed by the fixed qualification image to its required --code argument."
  validation {
    condition     = length(trimspace(var.qualification_code)) > 0 && length(var.qualification_code) <= 256
    error_message = "qualification_code must be a nonempty string of at most 256 characters."
  }
}

variable "ami_id" {
  type        = string
  description = "Pinned AWS Batch GPU-compatible AMI verified by the qualification receipt."
}

variable "bootstrap_sha256" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-f]{64}$", var.bootstrap_sha256))
    error_message = "bootstrap_sha256 must be a lowercase SHA-256 digest."
  }
}

variable "create_batch_resources" {
  type        = bool
  default     = false
  description = "Create Batch resources only after Step 14 admission."
}

variable "artifact_bucket_name" {
  type        = string
  description = "Existing or new dedicated artifact bucket. Import an existing bucket before apply."
}

variable "artifact_prefix" {
  type    = string
  default = "runs"
}

variable "artifact_expiration_days" {
  type    = number
  default = 365
}

variable "step5b_payload_expiration_days" {
  type        = number
  default     = 35
  description = "Maximum retention for content-addressed Step 5B payload mirrors."
  validation {
    condition     = var.step5b_payload_expiration_days >= 1 && var.step5b_payload_expiration_days <= 35
    error_message = "Step 5B payload retention must be between 1 and 35 days."
  }
}

variable "root_volume_gib" {
  type    = number
  default = 3072
  validation {
    condition     = var.root_volume_gib >= 100 && var.root_volume_gib <= 16384
    error_message = "root_volume_gib must be between 100 and 16384 GiB."
  }
}

variable "monthly_budget_usd" {
  type    = number
  default = 1000
}

variable "budget_alert_email" {
  type        = string
  description = "Email that must confirm AWS Budget notifications."
}

variable "gpu_worker_image" {
  type        = string
  description = "Immutable one-GPU worker image reference accepted by the Step 7B receipt."
  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.gpu_worker_image))
    error_message = "gpu_worker_image must be an immutable sha256 digest reference."
  }
}

variable "common_tags" {
  type    = map(string)
  default = {}
}

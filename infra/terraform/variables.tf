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
  description = "Create the Batch compute environment and queue only after Step 14 admission."
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

variable "common_tags" {
  type    = map(string)
  default = {}
}

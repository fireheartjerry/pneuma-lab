variable "region" {
  type    = string
  default = "us-east-1"
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
}

variable "subnet_ids" {
  type = list(string)
}

variable "qualification_model" {
  type = string
}

variable "qualification_model_revision" {
  type = string
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

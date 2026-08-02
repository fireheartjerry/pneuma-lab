variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type = string
}

variable "ami_id" {
  type = string
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

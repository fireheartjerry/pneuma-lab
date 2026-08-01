variable "region" {
  type    = string
  default = "us-east-1"
}

variable "bucket_name" { type = string }
variable "lease_table_name" { type = string }
variable "security_group_id" { type = string }
variable "batch_service_role_name" { type = string }
variable "ecs_instance_profile_name" { type = string }

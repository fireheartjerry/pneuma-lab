variable "region" {
  type    = string
  default = "us-east-1"
}
variable "name_prefix" { type = string }
variable "tier" { type = string }
variable "ami_id" { type = string }
variable "root_snapshot_id" { type = string }
variable "bootstrap_sha256" { type = string }
variable "bucket_prefix" { type = string }
variable "bucket_arn" { type = string }
variable "lease_table" { type = string }
variable "lease_table_arn" { type = string }
variable "lease_key" { type = string }
variable "batch_service_role_arn" { type = string }
variable "ecs_instance_profile_arn" { type = string }
variable "security_group_id" { type = string }
variable "subnet_id" { type = string }
variable "controller_image" { type = string }

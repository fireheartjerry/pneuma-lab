# This is a committed static provider-selection lock; Terraform verification is
# intentionally skipped locally when the Terraform binary is unavailable.
provider "registry.terraform.io/hashicorp/aws" {
  version     = "5.91.0"
  constraints = "5.91.0"
}

terraform {
  required_version = ">= 1.10.0"

  # The qualification stack is driven from an ephemeral operator checkout, so
  # local state locking is not sufficient. The existing verified artifact
  # bucket provides encrypted/versioned state storage; Terraform's native S3
  # lockfile serializes apply and destroy across operator hosts.
  backend "s3" {
    bucket       = "pneuma-phase-b-892077329800"
    key          = "terraform/qualification/dual-l40s.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

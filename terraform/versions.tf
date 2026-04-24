terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # S3 backend for remote state.
  # Bucket is created by terraform/bootstrap/.
  # Values can be overridden via -backend-config flags in CI.
  backend "s3" {
    bucket = "evidence-pipeline-chat-app-tf-state"
    key    = "evidence-pipeline-chat-app/terraform.tfstate"
    region = "ap-southeast-1"
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Project name prefix for resource naming"
  type        = string
  default     = "evidence-pipeline-chat-app"
}

variable "evidence_bucket_name" {
  description = "Name of the S3 bucket for evidence artifacts"
  type        = string
  default     = "evidence-pipeline-chat-app-evidence"
}

variable "github_repo" {
  description = "GitHub repository in owner/repo format for OIDC trust"
  type        = string
  default     = "shanicusyee/librechat-fork"
}

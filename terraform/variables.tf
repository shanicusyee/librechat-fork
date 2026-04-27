variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-southeast-1"
}

variable "instance_size" {
  description = "Fargate instance size mapping to CPU/memory (e.g. small, medium, large)"
  type        = string
  default     = "medium"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for evidence artifact storage"
  type        = string
}

variable "project_name" {
  description = "Project name used as a prefix for resource naming and tagging"
  type        = string
  default     = "evidence-pipeline-chat-app"
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the ALB"
  type        = list(string)
  default     = ["58.182.144.93/32"]
}

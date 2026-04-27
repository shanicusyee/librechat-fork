variable "project_name" {
  description = "Project name used as a prefix for resource naming and tagging"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for evidence artifact storage"
  type        = string
}

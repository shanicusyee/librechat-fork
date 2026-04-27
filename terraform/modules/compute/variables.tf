variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "public_subnet_ids" {
  description = "IDs of the public subnets for the ALB"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "IDs of the private subnets for ECS tasks"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group ID for the ALB"
  type        = string
}

variable "ecs_security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

variable "efs_file_system_id" {
  description = "ID of the EFS file system for MongoDB persistence"
  type        = string
}

variable "efs_access_point_id" {
  description = "ID of the EFS access point for MongoDB"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 evidence bucket"
  type        = string
}

variable "project_name" {
  description = "Project name used as a prefix for resource naming and tagging"
  type        = string
}

variable "instance_size" {
  description = "Fargate instance size: small, medium, or large"
  type        = string
  default     = "small"

  validation {
    condition     = contains(["small", "medium", "large"], var.instance_size)
    error_message = "instance_size must be one of: small, medium, large."
  }
}

variable "project_name" {
  description = "Project name used as a prefix for resource naming"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for evidence artifact storage"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC for EFS security group"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs of private subnets for EFS mount targets"
  type        = list(string)
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC for NFS ingress rule"
  type        = string
}

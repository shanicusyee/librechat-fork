output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = var.aws_region
}

output "alb_url" {
  description = "URL of the Application Load Balancer"
  value       = module.compute.alb_url
}

output "s3_bucket_name" {
  description = "Name of the S3 evidence bucket"
  value       = module.storage.s3_bucket_name
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.compute.ecs_cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = module.compute.ecs_service_name
}

output "ecr_repository_url" {
  description = "URL of the ECR repository for the custom LibreChat image"
  value       = module.compute.ecr_repository_url
}

output "alb_security_group_id" {
  description = "Security group ID for the ALB"
  value       = module.networking.alb_security_group_id
}

output "alb_url" {
  description = "DNS name of the Application Load Balancer (app URL)"
  value       = "http://${aws_lb.main.dns_name}"
}

output "alb_dns_name" {
  description = "Raw DNS name of the ALB"
  value       = aws_lb.main.dns_name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.app.name
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecr_repository_url" {
  description = "URL of the ECR repository for the custom LibreChat image"
  value       = data.aws_ecr_repository.librechat.repository_url
}

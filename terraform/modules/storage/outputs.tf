output "s3_bucket_name" {
  description = "Name of the S3 evidence bucket"
  value       = aws_s3_bucket.evidence.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 evidence bucket"
  value       = aws_s3_bucket.evidence.arn
}

output "efs_file_system_id" {
  description = "ID of the EFS file system for MongoDB persistence"
  value       = aws_efs_file_system.mongodb.id
}

output "efs_security_group_id" {
  description = "Security group ID for the EFS mount targets"
  value       = aws_security_group.efs.id
}

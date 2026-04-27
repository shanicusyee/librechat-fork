output "s3_bucket_name" {
  description = "Name of the S3 evidence bucket"
  value       = data.aws_s3_bucket.evidence.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 evidence bucket"
  value       = data.aws_s3_bucket.evidence.arn
}

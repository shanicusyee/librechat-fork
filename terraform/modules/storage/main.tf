# --- S3 Evidence Bucket (created by bootstrap, referenced here) ---

data "aws_s3_bucket" "evidence" {
  bucket = var.s3_bucket_name
}

resource "aws_s3_bucket" "mwaa" {
  bucket_prefix = "servicehub-mwaa-dags-"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "mwaa" {
  bucket = aws_s3_bucket.mwaa.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "mwaa" {
  bucket = aws_s3_bucket.mwaa.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}


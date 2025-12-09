# Sample 001: Nested attributes test
# - S3 Bucket with tags (object)
# - S3 Bucket with cors_rule (array + nested object)
# - IAM Role with timeouts (nested block)

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-northeast-1"
}

# S3 Bucket with CORS configuration
resource "aws_s3_bucket" "cors_bucket" {
  bucket        = "terraform2sheet-cors-bucket-001"
  force_destroy = true

  tags = {
    Name        = "cors-bucket"
    Environment = "development"
    Project     = "terraform2sheet"
    Owner       = "test-user"
  }
}

# S3 Bucket CORS Configuration (separate resource in AWS provider v4+)
resource "aws_s3_bucket_cors_configuration" "cors_bucket" {
  bucket = aws_s3_bucket.cors_bucket.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "POST", "PUT"]
    allowed_origins = ["https://example.com", "https://test.example.com"]
    expose_headers  = ["ETag", "x-amz-request-id"]
    max_age_seconds = 3600
  }

  cors_rule {
    allowed_methods = ["GET"]
    allowed_origins = ["*"]
    max_age_seconds = 3000
  }
}

# IAM Role with timeouts
resource "aws_iam_role" "role_with_timeouts" {
  name        = "role-with-timeouts"
  description = "IAM role to test nested timeouts block"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "role-with-timeouts"
    Environment = "development"
  }
}

# S3 Bucket with versioning
resource "aws_s3_bucket_versioning" "cors_bucket" {
  bucket = aws_s3_bucket.cors_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

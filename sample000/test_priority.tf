# Test priority sorting with multiple resource types in the same sheet

# IAM Policy (should appear second with priority=90)
resource "aws_iam_policy" "sample_policy" {
  name        = "sample-policy"
  description = "Sample IAM policy for testing priority"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:s3:::my-bucket/*"
      }
    ]
  })

  tags = {
    Name        = "sample-policy"
    Environment = "development"
  }
}

# Another IAM Role (should appear first with priority=100)
resource "aws_iam_role" "another_role" {
  name        = "another-lambda-role"
  description = "Another IAM role for testing priority"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "another-role"
  }
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

variable "domain" {
  type        = string
  description = "Domain name"
}

output "lambda_function_arn" {
  value       = aws_lambda_function.basic_auth.qualified_arn
  description = "Lambda function ARN to attach to a CloudFront distribution"
}

data "archive_file" "basic_auth" {
  type        = "zip"
  source_file = "${path.module}/handler.py"
  output_path = "${path.module}/handler.zip"
}

resource "aws_lambda_function" "basic_auth" {
  function_name = "s3pypi-basic-auth-${replace(var.domain, ".", "-")}"

  runtime = "python3.8"
  timeout = 5
  publish = true

  filename         = data.archive_file.basic_auth.output_path
  source_code_hash = data.archive_file.basic_auth.output_base64sha256
  handler          = "handler.handle"

  role = aws_iam_role.basic_auth.arn
}

resource "aws_iam_role" "basic_auth" {
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": [
          "lambda.amazonaws.com",
          "edgelambda.amazonaws.com"
        ]
      }
    }
  ]
}
EOF
}

resource "aws_iam_policy" "basic_auth" {
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": "ssm:GetParameter",
      "Resource": "arn:aws:ssm:*:*:parameter/s3pypi/${var.domain}/users/*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "basic_auth" {
  role       = aws_iam_role.basic_auth.name
  policy_arn = aws_iam_policy.basic_auth.arn
}

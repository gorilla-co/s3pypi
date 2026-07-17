terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "region" {
  type        = string
  description = "AWS region"
}

variable "bucket" {
  type        = string
  description = "S3 bucket name"
}

variable "domain" {
  type        = string
  description = "Domain name"
}

variable "use_wildcard_certificate" {
  type        = bool
  default     = false
  description = "Use a wildcard certificate (*.example.com)"
}

variable "enable_dynamodb_locking" {
  type        = bool
  default     = false
  description = "Create a DynamoDB table for locking"
}

variable "enable_basic_auth" {
  type        = bool
  default     = false
  description = "Enable basic authentication using Lambda@Edge"
}

variable "waf_web_acl_arn" {
  type        = string
  default     = null
  description = "ARN of an AWS WAFv2 Web ACL (scope CLOUDFRONT, must exist in us-east-1) to associate with the CloudFront distribution"
}

provider "aws" {
  region = var.region
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

module "s3pypi" {
  source = "./modules/s3pypi"

  bucket                   = var.bucket
  domain                   = var.domain
  use_wildcard_certificate = var.use_wildcard_certificate
  enable_dynamodb_locking  = var.enable_dynamodb_locking
  enable_basic_auth        = var.enable_basic_auth
  waf_web_acl_arn          = var.waf_web_acl_arn

  providers = {
    aws.us_east_1 = aws.us_east_1
  }
}

output "cloudfront_distribution_id" {
  value       = module.s3pypi.cloudfront_distribution_id
  description = "ID of the CloudFront distribution, e.g. for use with AWS WAF or CloudWatch"
}

output "cloudfront_distribution_arn" {
  value       = module.s3pypi.cloudfront_distribution_arn
  description = "ARN of the CloudFront distribution, e.g. for use with AWS WAF or CloudWatch"
}

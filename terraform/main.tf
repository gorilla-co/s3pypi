terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
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

variable "enable_basic_auth" {
  type        = bool
  default     = false
  description = "Enable basic authentication using Lambda@Edge"
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
  enable_basic_auth        = var.enable_basic_auth

  providers = {
    aws.us_east_1 = aws.us_east_1
  }
}

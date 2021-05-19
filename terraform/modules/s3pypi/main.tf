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

locals {
  hosted_zone = replace(var.domain, "/^[^.]+\\./", "")
}

provider "aws" {
  alias = "us_east_1"
}

data "aws_acm_certificate" "viewer" {
  provider = aws.us_east_1
  domain   = var.use_wildcard_certificate ? "*.${local.hosted_zone}" : var.domain
}

data "aws_route53_zone" "dns" {
  name = local.hosted_zone
}

resource "aws_cloudfront_distribution" "cdn" {
  aliases = [var.domain]
  comment = var.domain

  viewer_certificate {
    acm_certificate_arn      = data.aws_acm_certificate.viewer.arn
    minimum_protocol_version = "TLSv1.1_2016"
    ssl_support_method       = "sni-only"
  }

  price_class     = "PriceClass_100"
  enabled         = true
  is_ipv6_enabled = true

  origin {
    domain_name = aws_s3_bucket.pypi.bucket_regional_domain_name
    origin_id   = "s3"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.oai.cloudfront_access_identity_path
    }
  }

  custom_error_response {
    error_code = 403
    #response_code         = 404
    #response_page_path    = "/404.html"
    error_caching_min_ttl = 0
  }

  default_root_object = "index.html"

  default_cache_behavior {
    target_origin_id       = "s3"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["GET", "HEAD", "OPTIONS"]
    cached_methods  = ["GET", "HEAD"]

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 0

    compress = true

    dynamic "lambda_function_association" {
      for_each = module.basic_auth
      iterator = mod
      content {
        event_type = "viewer-request"
        lambda_arn = mod.value.lambda_function_arn
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
}

resource "aws_route53_record" "alias" {
  zone_id = data.aws_route53_zone.dns.zone_id
  name    = var.domain
  type    = "A"

  alias {
    name    = aws_cloudfront_distribution.cdn.domain_name
    zone_id = aws_cloudfront_distribution.cdn.hosted_zone_id

    evaluate_target_health = false
  }
}

resource "aws_cloudfront_origin_access_identity" "oai" {}

resource "aws_s3_bucket" "pypi" {
  bucket = var.bucket
  acl    = "private"
}

resource "aws_s3_bucket_policy" "s3_policy" {
  bucket = aws_s3_bucket.pypi.id
  policy = data.aws_iam_policy_document.s3_policy.json
}

data "aws_iam_policy_document" "s3_policy" {
  statement {
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = ["${aws_s3_bucket.pypi.arn}/*", aws_s3_bucket.pypi.arn]

    principals {
      type        = "AWS"
      identifiers = [aws_cloudfront_origin_access_identity.oai.iam_arn]
    }
  }
}

module "basic_auth" {
  count = var.enable_basic_auth ? 1 : 0

  source = "./basic_auth"
  domain = var.domain

  providers = {
    aws = aws.us_east_1
  }
}

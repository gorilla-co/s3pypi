# S3PyPI

S3PyPI is a CLI for creating a Python Package Repository in an S3 bucket.


## Why?

The official [Python Package Index (PyPI)](https://pypi.org) is a public
repository of Python software. It's used by `pip` to download packages.

If you work at a company, you may wish to publish your packages somewhere
private instead, and still have them be accessible via `pip install`. This
requires hosting your own repository.

S3PyPI enables hosting a private repository at a low cost. It requires only an
[S3 bucket] for storage, and some way to serve files over HTTPS (e.g. [Amazon
CloudFront]).

Publishing packages and index pages to S3 is done using the `s3pypi` CLI.
Creating the S3 bucket and CloudFront distribution is done using a provided
[Terraform] configuration, which you can tailor to your own needs.

[S3 bucket]: https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
[Amazon CloudFront]: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html
[Terraform]: https://www.terraform.io/


## Alternatives

- [AWS CodeArtifact](https://aws.amazon.com/codeartifact/) is a fully managed
  service that integrates with IAM.


## Getting started

### Installation

Install s3pypi using pip:

```console
$ pip install s3pypi
```


### Setting up S3 and CloudFront

Before you can start using `s3pypi`, you must set up an S3 bucket for storing
packages, and a CloudFront distribution for serving files over HTTPS. Both of
these can be created using the [Terraform] configuration provided in the
`terraform/` directory:

```console
$ git clone https://github.com/gorilla-co/s3pypi.git
$ cd s3pypi/terraform/

$ terraform init
$ terraform apply
```

You will be asked to enter your desired AWS region, S3 bucket name, and domain
name for CloudFront. You can also enter these in a file named
`config.auto.tfvars`:

```terraform
region = "eu-west-1"
bucket = "example-bucket"
domain = "pypi.example.com"
```

#### DNS and HTTPS

The Terraform configuration assumes that a [Route 53 hosted zone] exists for
your domain, with a matching (wildcard) certificate in [AWS Certificate
Manager]. If your certificate is a wildcard certificate, add
`use_wildcard_certificate = true` to `config.auto.tfvars`.

#### Distributed locking with DynamoDB

To ensure that concurrent invocations of `s3pypi` do not overwrite each other's
changes, the objects in S3 can be locked via an optional DynamoDB table (using
the `--lock-indexes` option). To create this table, add `enable_dynamodb_locking
= true` to `config.auto.tfvars`.

#### Basic authentication

To enable basic authentication, add `enable_basic_auth = true` to
`config.auto.tfvars`. This will attach a [Lambda@Edge] function to your
CloudFront distribution that reads user passwords from [AWS Systems Manager
Parameter Store]. Users and passwords can be configured using the `put_user.py`
script:

```console
$ basic_auth/put_user.py pypi.example.com alice
Password:
```

This creates a parameter named `/s3pypi/pypi.example.com/users/alice`. Passwords
are hashed with a random salt, and stored as JSON objects:

```json
{
  "password_hash": "7364151acc6229ec1468f54986a7614a8b215c26",
  "password_salt": "RRoCSRzvYJ1xRra2TWzhqS70wn84Sb_ElKxpl49o3Y0"
}
```

#### Terraform module

The Terraform configuration can also be included in your own project as a
module:

```terraform
provider "aws" {
  region = "eu-west-1"
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

module "s3pypi" {
  source = "github.com/gorilla-co/s3pypi//terraform/modules/s3pypi"

  bucket = "example-bucket"
  domain = "pypi.example.com"

  use_wildcard_certificate = true
  enable_dynamodb_locking  = true
  enable_basic_auth        = true

  providers = {
    aws.us_east_1 = aws.us_east_1
  }
}
```

#### Migrating from s3pypi 0.x to 1.x

Existing resources created using the CloudFormation templates from s3pypi 0.x
can be [imported into Terraform] and [removed from CloudFormation]. For example:

```console
$ terraform init
$ terraform import module.s3pypi.aws_s3_bucket.pypi example-bucket
$ terraform import module.s3pypi.aws_cloudfront_distribution.cdn EDFDVBD6EXAMPLE
$ terraform apply
```

[imported into Terraform]: https://www.terraform.io/docs/import/index.html
[removed from CloudFormation]: https://aws.amazon.com/premiumsupport/knowledge-center/delete-cf-stack-retain-resources/

In this new configuration, CloudFront uses the S3 REST API endpoint as its
origin, not the S3 website endpoint. This allows the bucket to remain private,
with CloudFront accessing it through an [Origin Access Identity (OAI)]. To make
this work with your existing S3 bucket, all `<package>/index.html` objects must
be renamed to `<package>/`. You can do so using the provided script:

```console
$ scripts/migrate-s3-index.py example-bucket
```

To instead keep using the old configuration with a publicly accessible S3
website endpoint, pass the following options when uploading packages:

```console
$ s3pypi upload ... --index.html --s3-put-args='ACL=public-read'
```

[Origin Access Identity (OAI)]: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html


### Example IAM policy

The `s3pypi` CLI requires the following IAM permissions to access S3 and
(optionally) DynamoDB. Replace `example-bucket` by your S3 bucket name.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::example-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::example-bucket"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/example-bucket-locks"
    }
  ]
}
```


## Usage

### Distributing packages

You can now use `s3pypi` to upload packages to S3:

```console
$ cd /path/to/your-project/
$ python setup.py sdist bdist_wheel

$ s3pypi upload dist/* --bucket example-bucket [--prefix PREFIX]
```

See `s3pypi --help` for a description of all options.


### Installing packages

Install your packages using `pip` by pointing the `--extra-index-url` to your
CloudFront domain. If you used `--prefix` while uploading, then add the prefix
here as well:

```console
$ pip install your-project --extra-index-url https://pypi.example.com/PREFIX/
```

Alternatively, you can configure the index URL in `~/.pip/pip.conf`:

```
[global]
extra-index-url = https://pypi.example.com/PREFIX/
```


## Roadmap

Currently there are no plans to add new features to s3pypi. If you have any
ideas for new features, check out our [contributing guidelines](CONTRIBUTING.md)
on how to get these on our roadmap.


## Contact

Got any questions or ideas? We'd love to hear from you. Check out our
[contributing guidelines](CONTRIBUTING.md) for ways to offer feedback and
contribute.


## License

Copyright (c) [Gorillini NV](https://gorilla.co).
All rights reserved.

Licensed under the [MIT](LICENSE) License.


[Route 53 hosted zone]: https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/AboutHZWorkingWith.html
[AWS Certificate Manager]: https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-request-public.html
[Lambda@Edge]: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html
[AWS Systems Manager Parameter Store]: https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html

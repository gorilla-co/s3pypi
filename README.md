# S3PyPI

S3PyPI is a CLI for creating a Python Package Repository in an S3 bucket.

An extended tutorial on this tool can be found
[here](https://novemberfive.co/blog/opensource-pypi-package-repository-tutorial/).


## Getting started

### Installation

Install s3pypi using pip:

```console
$ pip install s3pypi==1.0.0rc1
```


### Setting up S3 and CloudFront

Before you can start using `s3pypi`, you must set up an S3 bucket for storing
packages, and a CloudFront distribution for serving files over HTTPS. Both of
these can be created using the [Terraform](https://www.terraform.io/)
configuration provided in the `terraform/` directory:

```console
$ git clone https://github.com/novemberfiveco/s3pypi.git
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
  source = "github.com/novemberfiveco/s3pypi//terraform/modules/s3pypi"

  bucket = "example-bucket"
  domain = "pypi.example.com"

  use_wildcard_certificate = true
  enable_basic_auth        = true

  providers = {
    aws.us_east_1 = aws.us_east_1
  }
}
```


## Usage

### Distributing packages

You can now use `s3pypi` to upload packages to S3:

```console
$ cd /path/to/your-project/
$ python setup.py sdist bdist_wheel

$ s3pypi dist/* --bucket example-bucket [--prefix PREFIX] [--acl ACL]
```


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

Copyright (c) [November Five BVBA](https://novemberfive.co).
All rights reserved.

Licensed under the [MIT](LICENSE) License.


[Route 53 hosted zone]: https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/AboutHZWorkingWith.html
[AWS Certificate Manager]: https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-request-public.html
[Lambda@Edge]: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html
[AWS Systems Manager Parameter Store]: https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html

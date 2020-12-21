# S3PyPI

S3PyPI is a CLI for creating a Python Package Repository in an S3 bucket.

An extended tutorial on this tool can be found
[here](https://novemberfive.co/blog/opensource-pypi-package-repository-tutorial/).


## Getting started

### Installation

Install s3pypi using pip:

```bash
pip install s3pypi
```


### Setting up S3 and CloudFront

Before you can start using `s3pypi`, you must set up an S3 bucket for storing
packages, and a CloudFront distribution for serving files over HTTPS. Both of
these can be created using the [Terraform](https://www.terraform.io/)
configuration provided in the `terraform/` directory:

```bash
git clone https://github.com/novemberfiveco/s3pypi.git
cd s3pypi/terraform/

terraform init
terraform apply
```

You will be asked to enter your desired AWS region, S3 bucket name, and domain
name for CloudFront. You can also enter these in a file named
`config.auto.tfvars`:

```terraform
region = "eu-west-1"
bucket = "example-bucket"
domain = "pypi.example.com"
```

The Terraform configuration assumes that a [Route 53 hosted zone] exists for
your domain, with a matching (wildcard) certificate in [AWS Certificate
Manager]. If your certificate is a wildcard certificate, add
`use_wildcard_certificate = true` to `config.auto.tfvars`.


## Usage

### Distributing packages

You can now use `s3pypi` to upload packages to S3:

```bash
cd /path/to/your-project/
python setup.py sdist bdist_wheel

s3pypi dist/* --bucket example-bucket [--prefix PREFIX] [--acl ACL]
```


### Installing packages

Install your packages using `pip` by pointing the `--extra-index-url` to your
CloudFront domain. If you used `--prefix` while uploading, then add the prefix
here as well:

```bash
pip install your-project --extra-index-url https://pypi.example.com/PREFIX/
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

# S3PyPI

S3PyPI is a CLI for creating a Python Package Repository in an S3 bucket.

An extended tutorial on this tool can be found [here](https://novemberfive.co/blog/opensource-pypi-package-repository-tutorial/).


## Getting started

### Installation

Install s3pypi using pip:

```bash
pip install s3pypi
```


### Setting up S3 and CloudFront

Before you can start using ``s3pypi``, you must set up an S3 bucket for your Python Package Repository, with static website hosting enabled. Additionally, you need a CloudFront distribution for serving the packages in your S3 bucket to ``pip`` over HTTPS. Both of these resources can be created using the CloudFormation templates provided in the ``cloudformation/`` directory:

```bash
aws cloudformation create-stack --stack-name STACK_NAME \
    --template-body file://cloudformation/s3-pypi.json \
    --parameters ParameterKey=AcmCertificateArn,ParameterValue=ACM_CERT_ARN \
                 ParameterKey=DomainName,ParameterValue=DOMAIN_NAME
```

[Managing Your Server Certificates](http://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_server-certs_manage.html)


## Usage

### Distributing packages

You can now use ``s3pypi`` to create Python packages and upload them to your S3 bucket. To hide packages from the public, you can use the ``--private`` option to prevent the packages from being accessible directly via the S3 bucket (they will only be accessible via Cloudfront and you can use WAF rules to protect them). If switching between private and public is not flexible enough, you can use the ``--acl`` option to directly specify the ACL. Alternatively, you can specify a secret subdirectory using the ``--secret`` option:

```bash
cd /path/to/your-project/
s3pypi --bucket mybucket [--private | --acl ACL] [--secret SECRET]
```


### Installing packages

Install your packages using ``pip`` by pointing the ``--extra-index-url`` to your CloudFront distribution (optionally followed by a secret subdirectory):

```bash
pip install your-project --extra-index-url https://pypi.example.com/SECRET/
```

Alternatively, you can configure the index URL in ``~/.pip/pip.conf``:

```
[global]
extra-index-url = https://pypi.example.com/SECRET/
```


## Roadmap

Currently there are no plans to add new features to s3pypi. If you have any ideas for new features, check out our [contributing guidelines](CONTRIBUTING.md) on how to get these on our roadmap.


## Contact

Got any questions or ideas? We'd love to hear from you. Check out our [contributing guidelines](CONTRIBUTING.md) for ways to offer feedback and contribute.


## License

Copyright (c) [November Five BVBA](https://novemberfive.co). All rights reserved.

Licensed under the [MIT](LICENSE) License.

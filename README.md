S3PyPI
======

S3PyPI is a CLI tool for creating a Python Package Repository in an S3 bucket.

An extended tutorial on using this tool can be found [here](https://novemberfive.co/blog/opensource-pypi-package-repository-tutorial/).


Installation
------------

Install the latest version:

```bash
pip install --upgrade s3pypi
```

Install the development version:

```bash
git clone -b develop git@github.com:novemberfiveco/s3pypi.git
cd s3pypi/ && sudo pip install -e .
```


Setting up S3 and CloudFront
----------------------------

Before you can start using ``s3pypi``, you must set up an S3 bucket for your Python Package Repository, with static website hosting enabled. Additionally, you need a CloudFront distribution for serving the packages in your S3 bucket to ``pip`` over HTTPS. Both of these resources can be created using the CloudFormation templates provided in the ``cloudformation/`` directory:

```bash
aws cloudformation create-stack --stack-name STACK_NAME \
    --template-body file://cloudformation/s3-pypi.json \
    --parameters ParameterKey=AcmCertificateArn,ParameterValue=ACM_CERT_ARN \
                 ParameterKey=DomainName,ParameterValue=DOMAIN_NAME
```

[Managing Your Server Certificates](http://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_server-certs_manage.html)

Distributing packages
---------------------

You can now use ``s3pypi`` to create Python packages and upload them to your S3 bucket. To hide packages from the public, you can use the ``--private`` option to prevent the packages from being accessible directly via the S3 bucket (they will only be accessible via Cloudfront and you can use WAF rules to protect them), or alternatively you can specify a secret subdirectory using the ``--secret`` option:

```bash
cd /path/to/your/awesome-project/
s3pypi --bucket mybucket [--private] [--secret SECRET]
```


Installing packages
-------------------

Install your packages using ``pip`` by pointing the ``--extra-index-url`` to your CloudFront distribution (optionally followed by a secret subdirectory):

```bash
pip install --upgrade awesome-project --extra-index-url https://pypi.example.com/SECRET/
```

Alternatively, you can configure the index URL in ``~/.pip/pip.conf``:

```
[global]
extra-index-url = https://pypi.example.com/SECRET/
```

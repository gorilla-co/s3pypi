S3PyPi
======

S3PyPi is a CLI tool for creating a Python Package Repository in an S3 bucket.


Installation
------------

Install the latest version:

```
pip install --upgrade s3pypi --extra-index-url https://pypi.novemberfive.co/
```

Install the development version:

```
git clone -b develop git@github.com:novemberfiveco/s3pypi.git
cd s3pypi/ && sudo pip install -e .
```


Setting up S3 and CloudFront
----------------------------

First, you must create an S3 bucket for your Python Package Repository, and enable static website hosting:

```
aws s3 mb s3://mybucket
aws s3 website s3://mybucket --index-document index.html
```

Next, in order to serve packages to ``pip`` over HTTPS, you must create a CloudFront distribution. Enter the S3 website endpoint as the origin domain name, and ``index.html`` as the default root object:

```
aws cloudfront create-distribution \
    --origin-domain-name mybucket.s3-website-eu-west-1.amazonaws.com \
    --default-root-object index.html
```

Some additional CloudFront settings must be configured in the [AWS console](https://console.aws.amazon.com/cloudfront/home):

- In the **General** tab, click *Edit*. Enter your desired *Alternate Domain Names* (e.g. ``pypi.example.com``) and configure a *Custom SSL Certificate* for your domain.
- In the **Origins** tab, select the S3 origin and click *Edit*. Set the *Origin Protocol Policy* to **HTTP Only**.
- In the **Behaviors** tab, select the default behavior and click *Edit*. Set the *Viewer Protocol Policy* to **HTTPS Only**.


Distributing packages
---------------------

You can now use ``s3pypi`` to create Python packages and upload them to your S3 bucket. To hide packages from the public, you can specify a secret subdirectory using the ``--secret`` option:

```
cd /path/to/your/awesome-project/
s3pypi --bucket mybucket [--secret SECRET]
```


Installing packages
-------------------

Install your packages using ``pip`` by pointing the ``--extra-index-url`` to your CloudFront distribution (optionally followed by a secret subdirectory):

```
pip install --upgrade awesome-project --extra-index-url https://pypi.example.com/SECRET/
```

Alternatively, you can configure the index URL in ``~/.pip/pip.conf``:

```
[global]
extra-index-url = https://pypi.example.com/SECRET/
```